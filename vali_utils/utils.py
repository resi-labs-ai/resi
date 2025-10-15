import bittensor as bt
import hashlib
import random
import re
import time
from typing import List, Optional, Tuple, Type, Union
import datetime as dt
from common import constants
from common.data import (
    CompressedMinerIndex,
    DataEntity,
    DataEntityBucket,
    TimeBucket,
)
from common.data_v2 import ScorableMinerIndex
from common.date_range import DateRange
from common.protocol import GetMinerIndex
from scraping.x import utils as x_utils

from random import Random

def choose_data_entity_bucket_to_query(index: ScorableMinerIndex) -> DataEntityBucket:
    """Choose a DataEntityBucket to validate using time-based randomization."""
    total_size = sum(
        scorable_bucket.scorable_bytes
        for scorable_bucket in index.scorable_data_entity_buckets
    )

    seed = time.time_ns()
    rng = Random(seed)
    chosen_byte = rng.uniform(0, total_size)
    
    iterated_bytes = 0
    for scorable_bucket in index.scorable_data_entity_buckets:
        if iterated_bytes + scorable_bucket.scorable_bytes >= chosen_byte:
            return scorable_bucket.to_data_entity_bucket()
        iterated_bytes += scorable_bucket.scorable_bytes
    assert (
        False
    ), "Failed to choose a DataEntityBucket to query... which should never happen"

def choose_entities_to_verify(entities: List[DataEntity]) -> List[DataEntity]:
    """Choose a random set of entities to verify."""
    chosen_entities = []
    total_size = sum(entity.content_size_bytes for entity in entities)

    num_entities_to_choose = min(5, len(entities))
    for _ in range(num_entities_to_choose):
        chosen_byte = random.uniform(0, total_size)
        iterated_bytes = 0
        for entity in entities:
            if entity in chosen_entities:
                continue

            if iterated_bytes + entity.content_size_bytes >= chosen_byte:
                chosen_entities.append(entity)
                total_size -= entity.content_size_bytes
                break

            iterated_bytes += entity.content_size_bytes

    return chosen_entities


def are_entities_valid(
    entities: List[DataEntity], data_entity_bucket: DataEntityBucket
) -> Tuple[bool, str]:
    """Validate entities in a DataEntityBucket."""
    actual_size = 0
    claimed_size = 0
    expected_datetime_range: DateRange = TimeBucket.to_date_range(
        data_entity_bucket.id.time_bucket
    )

    for entity in entities:
        actual_size += len(entity.content or b"")
        claimed_size += entity.content_size_bytes
        if entity.source != data_entity_bucket.id.source:
            return (
                False,
                f"Entity source {entity.source} does not match data_entity_bucket source {data_entity_bucket.id.source}",
            )
        if entity.label != data_entity_bucket.id.label:
            return (
                False,
                f"Entity label {entity.label} does not match data_entity_bucket label {data_entity_bucket.id.label}",
            )

        tz_datetime = entity.datetime
        if tz_datetime.tzinfo is None:
            tz_datetime = tz_datetime.replace(tzinfo=dt.timezone.utc)

        if not expected_datetime_range.contains(tz_datetime):
            return (
                False,
                f"Entity datetime {entity.datetime} is not in the expected range {expected_datetime_range}",
            )

    if actual_size < claimed_size or actual_size < data_entity_bucket.size_bytes:
        return (
            False,
            f"Size mismatch. Actual={actual_size}. Claimed={claimed_size}. Expected={data_entity_bucket.size_bytes}",
        )

    return (True, "")


def _normalize_uri(uri: str) -> str:
    """Normalize a URI for equality comparison."""
    return x_utils.normalize_url(uri)


def normalize_address(address: str) -> str:
    """Normalize property addresses for comparison."""
    if not address:
        return ""

    normalized = address.lower().strip()

    # Remove common city variations that might differ between sources
    city_suffixes = [
        r',\s*manhattan\s*,?\s*ny\s*\d{5}',
        r',\s*new\s+york\s*,?\s*ny\s*\d{5}',
        r',\s*brooklyn\s*,?\s*ny\s*\d{5}',
        r',\s*queens\s*,?\s*ny\s*\d{5}',
        r',\s*bronx\s*,?\s*ny\s*\d{5}',
        r',\s*staten\s+island\s*,?\s*ny\s*\d{5}',
    ]

    for suffix in city_suffixes:
        normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)

    # Standardize apartment/unit formats
    normalized = re.sub(r'\s+apt\s+', ' APT ', normalized)
    normalized = re.sub(r'\s+#', ' #', normalized)
    normalized = re.sub(r'\s+unit\s+', ' UNIT ', normalized)

    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def normalize_property_type(property_type: str) -> Optional[str]:
    """Normalize property types for comparison."""
    if not property_type or property_type.upper() == 'UNKNOWN':
        return None

    type_mapping = {
        'CONDO': 'CONDO',
        'CONDOMINIUM': 'CONDO',
        'TOWNHOUSE': 'TOWNHOUSE',
        'TOWNHOME': 'TOWNHOUSE',
        'SINGLE_FAMILY': 'SINGLE_FAMILY',
        'SINGLE FAMILY': 'SINGLE_FAMILY',
        'MULTI_FAMILY': 'MULTI_FAMILY',
        'MULTI FAMILY': 'MULTI_FAMILY',
        'APARTMENT': 'APARTMENT',
        'CO_OP': 'CO_OP',
        'CO-OP': 'CO_OP',
        'DUPLEX': 'DUPLEX',
        'TRIPLEX': 'TRIPLEX',
    }

    return type_mapping.get(property_type.upper(), property_type.upper())


def are_entities_unique(entities: List[DataEntity]) -> bool:
    """Check that all entities in a DataEntityBucket are unique."""
    entity_content_hash_set = set()
    uris = set()

    for entity in entities:
        entity_content_hash = hashlib.sha1(entity.content).hexdigest()
        normalized_uri = _normalize_uri(entity.uri)
        if entity_content_hash in entity_content_hash_set or normalized_uri in uris:
            return False
        entity_content_hash_set.add(entity_content_hash)
        uris.add(normalized_uri)

    return True


def get_single_successful_response(
    responses: List[bt.Synapse], expected_class: Type
) -> Optional[bt.Synapse]:
    """Extract a single successful response from a list."""
    if (
        responses
        and isinstance(responses, list)
        and len(responses) == 1
        and isinstance(responses[0], expected_class)
        and responses[0].is_success
    ):
        return responses[0]
    return None


def get_miner_index_from_response(response: GetMinerIndex) -> CompressedMinerIndex:
    """Extract MinerIndex from a GetMinerIndex response."""
    assert response.is_success

    if not response.compressed_index_serialized:
        raise ValueError("GetMinerIndex response has no index.")

    return CompressedMinerIndex.model_validate_json(response.compressed_index_serialized)
