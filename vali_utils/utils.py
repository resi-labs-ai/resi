import bittensor as bt
import hashlib
import json
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

from random import Random

def choose_data_entity_bucket_to_query(index: ScorableMinerIndex) -> DataEntityBucket:
    """Choose a DataEntityBucket to validate using time-based randomization."""
    # Handle edge case: no buckets available
    if not index.scorable_data_entity_buckets:
        raise ValueError("No scorable data entity buckets available to query")
    
    total_size = sum(
        scorable_bucket.scorable_bytes
        for scorable_bucket in index.scorable_data_entity_buckets
    )
    
    # Handle edge case: all buckets have 0 bytes
    if total_size == 0:
        raise ValueError("All scorable data entity buckets have 0 bytes")

    seed = time.time_ns()
    rng = Random(seed)
    chosen_byte = rng.uniform(0, total_size)
    # Clamp to slightly less than total_size to guarantee a bucket is found
    chosen_byte = min(chosen_byte, total_size * 0.999999)
    
    iterated_bytes = 0
    for scorable_bucket in index.scorable_data_entity_buckets:
        iterated_bytes += scorable_bucket.scorable_bytes
        if iterated_bytes > chosen_byte:
            return scorable_bucket.to_data_entity_bucket()
    
    # This should never happen with the clamped chosen_byte
    raise RuntimeError("Failed to choose a DataEntityBucket despite having valid buckets")

def choose_entities_to_verify(entities: List[DataEntity]) -> List[DataEntity]:
    """Choose a random set of entities to verify."""
    chosen_entities = []
    total_size = sum(entity.content_size_bytes for entity in entities)

    num_entities_to_choose = min(2, len(entities))  # Reduced from 5 to 1 to minimize scraping
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
    # RESI only handles real estate data - simple URL normalization
    return uri


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

    # Standardize common abbreviations
    normalized = re.sub(r'\s+street\s+', ' ST ', normalized)
    normalized = re.sub(r'\s+avenue\s+', ' AVE ', normalized)
    normalized = re.sub(r'\s+boulevard\s+', ' BLVD ', normalized)
    normalized = re.sub(r'\s+drive\s+', ' DR ', normalized)
    normalized = re.sub(r'\s+road\s+', ' RD ', normalized)
    normalized = re.sub(r'\s+lane\s+', ' LN ', normalized)
    normalized = re.sub(r'\s+place\s+', ' PL ', normalized)
    normalized = re.sub(r'\s+way\s+', ' WAY ', normalized)
    normalized = re.sub(r'\s+circle\s+', ' CIR ', normalized)
    normalized = re.sub(r'\s+court\s+', ' CT ', normalized)
    normalized = re.sub(r'\s+terrace\s+', ' TER ', normalized)
    normalized = re.sub(r'\s+trail\s+', ' TRL ', normalized)

    # Standardize directions
    normalized = re.sub(r'\s+north\s+', ' N ', normalized)
    normalized = re.sub(r'\s+south\s+', ' S ', normalized)
    normalized = re.sub(r'\s+east\s+', ' E ', normalized)
    normalized = re.sub(r'\s+west\s+', ' W ', normalized)
    normalized = re.sub(r'\s+northeast\s+', ' NE ', normalized)
    normalized = re.sub(r'\s+northwest\s+', ' NW ', normalized)
    normalized = re.sub(r'\s+southeast\s+', ' SE ', normalized)
    normalized = re.sub(r'\s+southwest\s+', ' SW ', normalized)

    # Remove extra whitespace and clean up
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # Remove trailing commas and periods
    normalized = re.sub(r'[,.]+$', '', normalized)

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


def _extract_zpid_from_uri(uri: str) -> Optional[str]:
    """
    Extract zpid from URI.
    Supports multiple URI formats used by Zillow scrapers.
    """
    try:
        # Format 1: szill://244790245 (zpid directly after protocol)
        if uri.startswith("szill://"):
            zpid = uri.replace("szill://", "").strip("/").split("/")[0]
            if zpid.isdigit():
                return zpid
        
        # Format 2: URL with _zpid suffix (e.g., /12345_zpid/)
        if "_zpid" in uri:
            return uri.split("_zpid")[0].split("/")[-1]
        
        # Format 3: URL with zpid query parameter (e.g., ?zpid=12345)
        if "zpid=" in uri:
            return uri.split("zpid=")[1].split("&")[0]
        
        # Format 4: Extract numeric ID from path (zpids are typically 8-9 digits)
        parts = uri.replace("://", "/").split("/")
        for part in parts:
            if part.isdigit() and len(part) >= 6:
                return part
        
        return None
    except Exception:
        return None


def are_entities_unique(entities: List[DataEntity]) -> bool:
    """
    Check that all entities in a DataEntityBucket are unique.
    
    Uses four independent checks:
    1. Content hash - Detects exact content duplicates
    2. URI - Detects same listing URLs
    3. zpid - Detects same property with modified data
    4. URI-zpid consistency - Detects fake zpid (content vs URI mismatch)
    
    Returns False if ANY check detects a duplicate or data inconsistency.
    """
    entity_content_hash_set = set()
    uris = set()
    zpids = set()

    for entity in entities:
        # Check 1: Full content hash (existing)
        entity_content_hash = hashlib.sha1(entity.content).hexdigest()
        
        # Check 2: Normalized URI (existing)
        normalized_uri = _normalize_uri(entity.uri)
        
        # Check 3 & 4: Extract zpid and verify consistency
        zpid = None
        try:
            # Parse JSON content
            content_str = entity.content.decode('utf-8')
            content_dict = json.loads(content_str)
            
            # Extract zpid from content (property identifier)
            zpid = content_dict.get('zpid')
            
            # Convert to string for consistent comparison
            if zpid is not None:
                zpid = str(zpid)
                
                # Check 4: Verify zpid in content matches zpid in URI
                uri_zpid = _extract_zpid_from_uri(entity.uri)
                if uri_zpid and zpid != uri_zpid:
                    bt.logging.warning(
                        f"zpid mismatch detected - Content zpid: '{zpid}', URI zpid: '{uri_zpid}'. "
                        f"This indicates data manipulation or fake zpid."
                    )
                    return False  # Inconsistent data = invalid!
                
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            # If parsing fails, zpid check is skipped (falls back to other checks)
            # This handles non-JSON content or malformed data gracefully
            pass
        
        # Duplicate detection: Check all three conditions
        is_hash_duplicate = entity_content_hash in entity_content_hash_set
        is_uri_duplicate = normalized_uri in uris
        is_zpid_duplicate = zpid and zpid in zpids
        
        if is_hash_duplicate or is_uri_duplicate or is_zpid_duplicate:
            # Enhanced logging for debugging
            if is_zpid_duplicate:
                bt.logging.debug(f"Duplicate zpid detected: {zpid}")
            return False
        
        # Add to tracking sets
        entity_content_hash_set.add(entity_content_hash)
        uris.add(normalized_uri)
        if zpid:
            zpids.add(zpid)

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
