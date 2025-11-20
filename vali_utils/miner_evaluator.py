import os
import copy
import asyncio
import datetime
import traceback
import threading
import time

from common import constants
from common.data_v2 import ScorableMinerIndex
from common.metagraph_syncer import MetagraphSyncer
import common.utils as utils
import datetime as dt
import bittensor as bt
from common.data import (
    CompressedMinerIndex,
    DataEntityBucket,
    DataEntity,
    DataSource,
)
from common.protocol import GetDataEntityBucket, GetMinerIndex
from rewards.data_value_calculator import DataValueCalculator
from vali_utils.scrapers import ValidatorScraperProvider
from scraping.scraper import ScraperId, ValidationResult
from storage.validator.sqlite_memory_validator_storage import (
    SqliteMemoryValidatorStorage,
)
from storage.validator.s3_validator_storage import S3ValidationStorage

from vali_utils.miner_iterator import MinerIterator
from vali_utils import metrics, utils as vali_utils

from typing import List, Optional, Tuple
from vali_utils.validator_s3_access import ValidatorS3Access
from vali_utils.s3_utils import validate_s3_miner_data, get_s3_validation_summary, S3ValidationResult

from rewards.miner_scorer import MinerScorer

# Import multi-tier validation components
from scraping.custom.model import RealEstateContent
import json
import re
from typing import Optional, Set, Dict, Any


class MinerEvaluator:
    """MinerEvaluator is responsible for evaluating miners and updating their scores."""

    SCORER_FILENAME = "scorer.pickle"

    # Mapping of scrapers to use based on the data source to validate
    PREFERRED_SCRAPERS = {
        DataSource.SZILL_VALI: "Szill.zillow"
    }

    def __init__(self, config: bt.config, uid: int, metagraph_syncer: MetagraphSyncer, s3_reader: ValidatorS3Access):
        self.config = config
        self.uid = uid
        self.metagraph_syncer = metagraph_syncer
        self.metagraph = self.metagraph_syncer.get_metagraph(config.netuid)
        self.metagraph_syncer.register_listener(
            self._on_metagraph_updated, netuids=[config.netuid]
        )
        self.vpermit_rao_limit = self.config.vpermit_rao_limit
        self.wallet = bt.wallet(config=self.config)

        # Set up initial scoring weights for validation
        self.scorer = MinerScorer(self.metagraph.n, DataValueCalculator())

        # Setup dependencies.
        self.miner_iterator = MinerIterator(
            utils.get_miner_uids(self.metagraph, self.vpermit_rao_limit)
        )
        
        # Configure scraper provider with proxy, ScrapingBee, and BrightData settings from config
        proxy_url = getattr(self.config, 'proxy_url', None)
        use_scrapingbee = getattr(self.config, 'use_scrapingbee', False)
        use_brightdata = getattr(self.config, 'use_brightdata', False)
        
        bt.logging.info(f"Initializing scraper provider - proxy: {bool(proxy_url)}, scrapingbee: {use_scrapingbee}, brightdata: {use_brightdata}")
        self.scraper_provider = ValidatorScraperProvider(
            proxy_url=proxy_url,
            use_scrapingbee=use_scrapingbee,
            use_brightdata=use_brightdata
        )
        
        self.storage = SqliteMemoryValidatorStorage()
        self.s3_storage = S3ValidationStorage(self.config.s3_results_path)
        self.s3_reader = s3_reader
        # Instantiate runners
        self.should_exit: bool = False
        self.is_running: bool = False
        self.lock = threading.RLock()
        self.is_setup = False
        
        # Epoch winner tracking
        self.epoch_baseline_scores = {}
        self.epoch_miners_evaluated = set()
        self.epoch_start_block = None
        self.epoch_complete = False

    def get_scorer(self) -> MinerScorer:
        """Returns the scorer used by the evaluator."""
        return self.scorer

    def eval_miner_sync(self, uid: int) -> None:
        """Synchronous version of eval_miner."""
        asyncio.run(self.eval_miner(uid))

    async def eval_miner(self, uid: int) -> None:
        """Evaluates a miner and updates their score.

        Specifically:
            1. Gets the latest index from the miner
            2. Chooses a random data entity bucket to query
            3. Performs basic validation on the data entity bucket (right labels, matching size, etc.)
            4. Samples data from the data entity bucket and verifies the data is correct
            5. Passes the validation result to the scorer to update the miner's score.
        """
        t_start = time.perf_counter()

        axon_info = None
        hotkey = None
        with self.lock:
            axon_info = self.metagraph.axons[uid]
            hotkey = self.metagraph.hotkeys[uid]

        bt.logging.info(f"{hotkey}: Evaluating miner.")

        # Query the miner for the latest index.
        index = await self._update_and_get_miner_index(hotkey, uid, axon_info)
        if not index:
            # The miner hasn't provided an index yet, so we can't validate them. Count as a failed validation.
            bt.logging.info(
                f"{hotkey}: Failed to get an index for miner. Counting as a failed validation."
            )
            self.scorer.on_miner_evaluated(
                uid,
                None,
                [
                    ValidationResult(
                        is_valid=False,
                        reason="No available miner index.",
                        content_size_bytes_validated=0,  # Since there is just one failed result size doesn't matter.
                    )
                ]
            )

            metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address, miner_hotkey=hotkey, status='unavailable miner index').observe(time.perf_counter() - t_start)
            return

        ##########
        #  Perform S3 validation (only if enabled by date)
        current_block = int(self.metagraph.block)
        s3_validation_info = self.s3_storage.get_validation_info(hotkey)
        s3_validation_result = None

        bt.logging.info(f"{hotkey}: Checking if S3 validation needed. Current block: {current_block}, S3 validation info: {s3_validation_info}")
        
        if s3_validation_info is None or (current_block - s3_validation_info['block']) > 1200:  # 4 hrs (aligned with regular validation)
            bt.logging.info(f"{hotkey}: Triggering S3 validation (validation_info: {s3_validation_info}, block diff: {(current_block - s3_validation_info['block']) if s3_validation_info else 'N/A'})")
            s3_validation_result = await self._perform_s3_validation(hotkey, current_block)
            bt.logging.info(f"{hotkey}: S3 validation completed. Result: {s3_validation_result}")
        else:
            bt.logging.info(f"{hotkey}: Skipping S3 validation (last validated {current_block - s3_validation_info['block']} blocks ago)")
        ##########

        # Check if the miner has any scorable buckets to query
        if not index.scorable_data_entity_buckets or sum(
            scorable_bucket.scorable_bytes
            for scorable_bucket in index.scorable_data_entity_buckets
        ) == 0:
            bt.logging.info(
                f"{hotkey}: Miner has no scorable buckets. Counting as a failed validation."
            )
            self.scorer.on_miner_evaluated(
                uid,
                None,
                [
                    ValidationResult(
                        is_valid=False,
                        reason="No scorable data entity buckets.",
                        content_size_bytes_validated=0,
                    )
                ]
            )

            metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address, miner_hotkey=hotkey, status='no scorable buckets').observe(time.perf_counter() - t_start)
            return

        # From that index, find a data entity bucket to sample and get it from the miner.
        chosen_data_entity_bucket: DataEntityBucket = (
            vali_utils.choose_data_entity_bucket_to_query(index)
        )
        bt.logging.info(
            f"{hotkey} Querying miner for Bucket ID: {chosen_data_entity_bucket.id}."
        )

        responses = None
        async with bt.dendrite(wallet=self.wallet) as dendrite:
            responses = await dendrite.forward(
                axons=[axon_info],
                synapse=GetDataEntityBucket(
                    data_entity_bucket_id=chosen_data_entity_bucket.id,
                    version=constants.PROTOCOL_VERSION,
                ),
                timeout=140,
            )
        
        data_entity_bucket = vali_utils.get_single_successful_response(
            responses, GetDataEntityBucket
        )

        # Treat a failed response the same way we treat a failed validation.
        # If we didn't, the miner could just not respond to queries for data entity buckets it doesn't have.
        if data_entity_bucket is None:
            bt.logging.info(
                f"{hotkey}: Miner returned an invalid/failed response for Bucket ID: {chosen_data_entity_bucket.id}."
            )
            self.scorer.on_miner_evaluated(
                uid,
                index,
                [
                    ValidationResult(
                        is_valid=False,
                        reason="Response failed or is invalid.",
                        content_size_bytes_validated=0,  # Since there is just one failed result size doesn't matter.
                    )
                ]
            )

            metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address, miner_hotkey=hotkey, status='invalid response').observe(time.perf_counter() - t_start)
            return

        # Perform basic validation on the entities.
        bt.logging.info(
            f"{hotkey}: Performing basic validation on Bucket ID: {chosen_data_entity_bucket.id} containing "
            + f"{chosen_data_entity_bucket.size_bytes} bytes across {len(data_entity_bucket.data_entities)} entities."
        )

        data_entities: List[DataEntity] = data_entity_bucket.data_entities
        (valid, reason) = vali_utils.are_entities_valid(
            data_entities, chosen_data_entity_bucket
        )
        if not valid:
            bt.logging.info(
                f"{hotkey}: Failed basic entity validation on Bucket ID: {chosen_data_entity_bucket.id} with reason: {reason}"
            )
            self.scorer.on_miner_evaluated(
                uid,
                index,
                [
                    ValidationResult(
                        is_valid=False,
                        reason=reason,
                        content_size_bytes_validated=0,  # Since there is just one failed result size doesn't matter.
                    )
                ]
            )

            metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address, miner_hotkey=hotkey, status='invalid data entity bucket').observe(time.perf_counter() - t_start)
            return

        # Perform uniqueness validation on the entity contents.
        # If we didn't, the miner could just return the same data over and over again.
        unique = vali_utils.are_entities_unique(data_entities)
        if not unique:
            bt.logging.info(
                f"{hotkey}: Failed enitity uniqueness checks on Bucket ID: {chosen_data_entity_bucket.id}."
            )
            self.scorer.on_miner_evaluated(
                uid,
                index,
                [
                    ValidationResult(
                        is_valid=False,
                        reason="Duplicate entities found.",
                        content_size_bytes_validated=0,  # Since there is just one failed result size doesn't matter.
                    )
                ]
            )

            metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address, miner_hotkey=hotkey, status='duplicate entities').observe(time.perf_counter() - t_start)
            return

        # MULTI-TIER VALIDATION 
        bt.logging.info(f"{hotkey}: Starting multi-tier validation on {len(data_entities)} entities")
        
        # TIER 1: Quantity Validation
        # Get expected listings AND zipcodes from the most recently completed epoch
        expected_listings, epoch_zipcodes = self._get_expected_listings_and_zipcodes()
        if expected_listings:
            bt.logging.debug(f"{hotkey}: Expected {expected_listings} listings from completed epoch")
        else:
            bt.logging.debug(f"{hotkey}: No epoch assignment found, using fallback validation")
        
        tier1_passes, tier1_reason, tier1_metrics = self._apply_tier1_quantity_validation(
            data_entities, 
            expected_count=expected_listings
        )
        bt.logging.info(f"{hotkey}: Tier 1 - {tier1_reason}")
        
        if not tier1_passes:
            bt.logging.warning(f"{hotkey}: Failed Tier 1 (Quantity) validation")
            self.scorer.on_miner_evaluated(
                uid, 
                index,
                [ValidationResult(
                    is_valid=False,
                    reason=f"Multi-tier validation failed at Tier 1: {tier1_reason}",
                    content_size_bytes_validated=0
                )]
            )
            metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(
                hotkey=self.wallet.hotkey.ss58_address, 
                miner_hotkey=hotkey, 
                status='tier1_failed'
            ).observe(time.perf_counter() - t_start)
            return
        
        # TIER 2: Quality Validation
        # Pass epoch_zipcodes from Tier 1 
        tier2_passes, tier2_reason, tier2_metrics = self._apply_tier2_quality_validation(
            data_entities,
            epoch_zipcodes=epoch_zipcodes
        )
        bt.logging.info(f"{hotkey}: Tier 2 - {tier2_reason}")
        
        if not tier2_passes:
            bt.logging.warning(f"{hotkey}: Failed Tier 2 (Quality) validation")
            # Apply reduced score for partial completion
            self.scorer.on_miner_evaluated(
                uid,
                index,
                [ValidationResult(
                    is_valid=False,
                    reason=f"Multi-tier validation failed at Tier 2: {tier2_reason}",
                    content_size_bytes_validated=chosen_data_entity_bucket.size_bytes // 2  # Partial credit
                )]
            )
            metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(
                hotkey=self.wallet.hotkey.ss58_address,
                miner_hotkey=hotkey,
                status='tier2_failed'
            ).observe(time.perf_counter() - t_start)
            return
        
        # TIER 3: Spot-check Validation (data correctness)
        # Sample some entities for data correctness verification
        entities_to_validate: List[DataEntity] = vali_utils.choose_entities_to_verify(
            data_entities
        )

        entity_uris = [entity.uri for entity in entities_to_validate]

        bt.logging.info(
            f"{hotkey}: Tier 3 - Spot-checking {len(entities_to_validate)} entities: {entity_uris}"
        )

        # Skip unsupported data sources
        data_source = chosen_data_entity_bucket.id.source
        if data_source in [DataSource.X, DataSource.REDDIT, DataSource.YOUTUBE]:
            bt.logging.info(f"{hotkey}: Data source not supported - skipping")
            validation_results = [ValidationResult(
                is_valid=False, 
                reason=f"Data source not supported", 
                content_size_bytes_validated=0
            ) for _ in entities_to_validate]
        else:
            scraper = self.scraper_provider.get(
                MinerEvaluator.PREFERRED_SCRAPERS[data_source]
            )
            validation_results = await scraper.validate(entities_to_validate)

        # Apply Tier 3 validation
        tier3_passes, tier3_reason, tier3_metrics = self._apply_tier3_spot_check_validation(
            entities_to_validate,
            validation_results
        )
        bt.logging.info(f"{hotkey}: Tier 3 - {tier3_reason}")
        
        # Log comprehensive multi-tier results
        bt.logging.success(
            f"{hotkey}: Multi-tier validation complete - "
            f"Tier1: PASS, "
            f"Tier2: PASS, "
            f"Tier3: {'PASS' if tier3_passes else 'FAIL'}"
        )

        # Update scorer with validation results
        # Even if Tier 3 fails, miner gets partial credit for passing Tier 1 & 2
        self.scorer.on_miner_evaluated(uid, index, validation_results)

        metrics.MINER_EVALUATOR_EVAL_MINER_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address, miner_hotkey=hotkey, status='ok').observe(time.perf_counter() - t_start)

        if s3_validation_result:
            if s3_validation_result.is_valid:
                bt.logging.info(
                    f"{hotkey}: Miner {uid} passed S3 validation. Validation: {s3_validation_result.validation_percentage:.1f}%, Jobs: {s3_validation_result.job_count}, Files: {s3_validation_result.total_files}")
            else:
                bt.logging.info(f"{hotkey}: Miner {uid} did not pass S3 validation. Reason: {s3_validation_result.reason}")

            self.scorer.update_s3_boost_and_cred(uid, s3_validation_result.validation_percentage)

    async def _perform_s3_validation(
            self, hotkey: str, current_block: int
    ) -> Optional[S3ValidationResult]:
        """
        Performs comprehensive S3 validation using metadata analysis and statistical methods.
        Validates file structure, job alignment, data quality, and temporal patterns.
        
        Can use enhanced validation with real scrapers if enabled in configuration.

        Returns:
            An S3ValidationResult with validation details or None if no S3 data is found.
        """
        bt.logging.info(f"{hotkey}: Starting comprehensive S3 validation")

        try:
            # Use S3 auth URL from config
            s3_auth_url = self.config.s3_auth_url
            
            s3_validation_result = await validate_s3_miner_data(
                self.wallet, s3_auth_url, hotkey, 
                use_enhanced_validation=False, config=self.config
            )
            
            # Log results
            summary = get_s3_validation_summary(s3_validation_result)
            bt.logging.info(f"{hotkey}: {summary}")
            
            if not s3_validation_result.is_valid and s3_validation_result.issues:
                bt.logging.debug(f"{hotkey}: S3 validation issues: {', '.join(s3_validation_result.issues[:3])}")

        except Exception as e:
            bt.logging.error(f"{hotkey}: Error in S3 validation: {str(e)}")
            s3_validation_result = S3ValidationResult(
                is_valid=False,
                validation_percentage=0.0,
                job_count=0,
                total_files=0,
                total_size_bytes=0,
                valid_jobs=0,
                recent_files=0,
                quality_metrics={},
                issues=[f"Validation error: {str(e)}"],
                reason=f"S3 validation failed: {str(e)}"
            )

        # Update S3 validation storage
        if s3_validation_result:
            self.s3_storage.update_validation_info(hotkey, s3_validation_result.job_count, current_block)

        return s3_validation_result


    async def run_next_eval_batch(self) -> int:
        """Asynchronously runs the next synchronized batch of miner evaluations.
        
        NEW APPROACH: Evaluates 100 miners per 4-hour cycle in synchronized batches.
        All validators evaluate the same miners simultaneously.
        
        Optimizations:
        - 7x faster evaluation (every ~10.4 hours vs ~68 hours)
        - 94% API utilization (186k calls/month vs 27.9k)
        - Eliminates stale score variance
        - Fair miner treatment
        
        Returns:
            Number of seconds to wait until next evaluation cycle
        """

        # Grab a snapshot of the metagraph
        metagraph = None
        with self.lock:
            metagraph = copy.deepcopy(self.metagraph)

        current_block = int(metagraph.block.item())
        
        # Initialize epoch tracking
        if self.epoch_start_block is None:
            self.epoch_start_block = current_block
            
            # Capture baseline scores at epoch start
            with self.scorer.lock:
                self.epoch_baseline_scores = self.scorer.scores.clone()
            
            self.epoch_miners_evaluated = set()
            total_miners = len(self.miner_iterator.miner_uids)
            
            bt.logging.info(
                f"🔄 Starting epoch at block {current_block} | "
                f"baseline_captured={total_miners} miners"
            )
        
        # Get synchronized batch of miners to evaluate (100 miners per cycle)
        uids_to_eval = self.miner_iterator.get_synchronized_evaluation_batch(current_block)
        
        if not uids_to_eval:
            bt.logging.info("No miners to evaluate in current synchronized batch.")
            return 3600  # Wait 1 hour before checking again
        
        # Log progress
        total_miners = len(self.miner_iterator.miner_uids)
        bt.logging.success(
            f"🔄 SYNCHRONIZED EVALUATION: Running validation on {len(uids_to_eval)} miners "
            f"at block {current_block}. Progress: {len(self.epoch_miners_evaluated)}/{total_miners}"
        )

        # Check if we need to wait for the evaluation period
        # For synchronized evaluation, we check the first miner in the batch
        first_uid = uids_to_eval[0]
        first_hotkey = metagraph.hotkeys[first_uid]
        last_evaluated = self.storage.read_miner_last_updated(first_hotkey)
        now = dt.datetime.utcnow()
        
        # Calculate when this batch was last evaluated
        due_update = (
            last_evaluated is None
            or (now - last_evaluated) >= constants.MIN_EVALUATION_PERIOD
        )

        if not due_update:
            # Calculate time until next 4-hour cycle
            blocks_per_cycle = 1200  # 4 hours
            # blocks_per_cycle = 360
            blocks_until_next_cycle = blocks_per_cycle - (current_block % blocks_per_cycle)
            seconds_until_next_cycle = blocks_until_next_cycle * 12  # 12 seconds per block
            
            bt.logging.info(
                f"Synchronized batch not due for evaluation yet. "
                f"Waiting {seconds_until_next_cycle/60:.1f} minutes until next cycle."
            )
            return seconds_until_next_cycle

        t_start = time.perf_counter()

        bt.logging.info(
            f"🚀 Evaluating synchronized batch of {len(uids_to_eval)} miners: {uids_to_eval}"
        )
        
        # Create threads for concurrent evaluation (increased timeout for larger batches)
        threads = [
            threading.Thread(target=self.eval_miner_sync, args=(uid,))
            for uid in uids_to_eval
        ]
        for thread in threads:
            thread.start()

        bt.logging.trace(f"Waiting for {len(threads)} synchronized miner evaluations to finish.")
        
        # Conservative timeout for 100 parallel threads (25 minutes for safety)
        end = datetime.datetime.now() + datetime.timedelta(seconds=1500)
        for t in threads:
            # Compute the timeout, so that all threads are waited for a total of 25 minutes.
            timeout = max(0, (end - datetime.datetime.now()).total_seconds())
            t.join(timeout=timeout)

        duration = time.perf_counter() - t_start
        metrics.MINER_EVALUATOR_EVAL_BATCH_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address).observe(duration)

        # Track evaluated miners for epoch completion
        self.epoch_miners_evaluated.update(uids_to_eval)
        
        # Check if epoch is complete
        total_miners = len(self.miner_iterator.miner_uids)
        if len(self.epoch_miners_evaluated) >= total_miners:
            bt.logging.success(f"🎯 Epoch complete! Evaluated {len(self.epoch_miners_evaluated)}/{total_miners} miners")
            self.epoch_complete = True
        else:
            bt.logging.success(
                f"✅ Completed synchronized evaluation of {len(uids_to_eval)} miners in {duration:.1f}s. "
                f"Progress: {len(self.epoch_miners_evaluated)}/{total_miners}"
            )

        # Run the next evaluation batch immediately.
        return 0 if self.epoch_complete else 3600

    def save_state(self):
        """Saves the state of the validator to a file."""
        bt.logging.trace("Saving evaluator state.")

        if not os.path.exists(self.config.neuron.full_path):
            os.makedirs(self.config.neuron.full_path)

        # Save the state of the validator to file.
        self.scorer.save_state(
            os.path.join(self.config.neuron.full_path, MinerEvaluator.SCORER_FILENAME)
        )

    def load_state(self):
        """Loads the state of the validator from a file."""
        bt.logging.info("Loading evaluator state.")

        with self.lock:
            # Load the state of the validator from file.
            filepath = os.path.join(
                self.config.neuron.full_path, MinerEvaluator.SCORER_FILENAME
            )
            if not os.path.exists(filepath):
                bt.logging.warning("No scorer state file found. Starting from scratch.")
                return

            try:
                self.scorer.load_state(filepath)
                bt.logging.success(f"Loaded scorer state from: {filepath}.")
            except Exception as e:
                bt.logging.warning(
                    f"Failed to load scorer state. Reason: {e}. Starting from scratch."
                )

            # Resize the scorer in case the loaded state is old and missing newly added neurons.
            self.scorer.resize(len(self.metagraph.hotkeys))

    async def collect_epoch_winner_data(self) -> Optional[Dict]:
        """
        Identify the single winner for this epoch and collect their data from S3.
        
        Winner = Miner with highest epoch score delta
        
        Returns:
            Validation result with winner's complete data, or None if no winners
        """
        try:
            bt.logging.info("🏆 Identifying epoch winner...")
            
            # Calculate epoch score deltas for all evaluated miners
            epoch_scores = {}
            
            with self.scorer.lock:
                current_scores = self.scorer.scores.clone()
            
            # Calculate scores for all evaluated miners
            for uid in self.epoch_miners_evaluated:
                baseline_score = float(self.epoch_baseline_scores[uid])
                current_score = float(current_scores[uid])
                epoch_score_delta = current_score - baseline_score
                
                bt.logging.debug(
                    f"UID {uid}: baseline={baseline_score:.2f}, "
                    f"current={current_score:.2f}, delta={epoch_score_delta:.2f}"
                )
                
                # Use current absolute score to pick winner
                epoch_scores[uid] = current_score
            
            if not epoch_scores:
                bt.logging.warning(
                    f"No miners evaluated this epoch."
                )
                return None
            
            # Find winner (highest current score)
            winner_uid = max(epoch_scores.items(), key=lambda x: x[1])[0]
            winner_current_score = epoch_scores[winner_uid]
            winner_hotkey = self.metagraph.hotkeys[winner_uid]
            
            bt.logging.info(f"🥇 Epoch Winner: UID {winner_uid} ({winner_hotkey[:8]}...) | score={winner_current_score:.2f}")
            
            # Store S3 reference to winner's data
            current_block = int(self.metagraph.block)
            
            # Use timestamp-based epoch ID
            epoch_id = self._get_previous_epoch_id(epoch_duration_hours=4)
            
            bt.logging.debug(
                f"Epoch block range: start={self.epoch_start_block}, "
                f"end={current_block}, duration={current_block - self.epoch_start_block} blocks | "
                f"epoch_id={epoch_id}"
            )
            
            # Determine S3 bucket
            if self.config.netuid == 428:  # Testnet
                s3_bucket = 'api-staging-miner'
            else:  # Mainnet
                s3_bucket = '4000-resilabs-prod-bittensor-sn46-datacollection'
            
            # Create S3 data reference for the winner
            s3_data_reference = {
                's3_bucket': s3_bucket,
                's3_path': f"data/hotkey={winner_hotkey}/epoch={epoch_id}/",
                'access_method': 'Use S3 auth API with miner hotkey to get presigned URLs',
                's3_auth_url': self.config.s3_auth_url,
                'miner_hotkey': winner_hotkey,
                'network': 'testnet' if self.config.netuid == 428 else 'mainnet',
                'note': 'Data stored by miner in epoch-based structure: data/hotkey={miner}/epoch={epoch_id}/zipcode={zipcode}/data_*.json'
            }
            
            bt.logging.info(f"Winner's data location: s3://{s3_bucket}/{s3_data_reference['s3_path']}")
            
            # Create validation result with S3 reference
            validation_result = {
                'epoch_id': epoch_id,
                'validator_hotkey': self.wallet.hotkey.ss58_address,
                'block_range': {
                    'start_block': self.epoch_start_block,
                    'end_block': current_block,
                    'total_blocks': current_block - self.epoch_start_block
                },
                'timestamp': dt.datetime.utcnow().isoformat(),
                'winner': {
                    'uid': winner_uid,
                    'hotkey': winner_hotkey,
                    'current_score': winner_current_score,
                    'cumulative_score': float(current_scores[winner_uid]),
                    'credibility': float(self.scorer.miner_credibility[winner_uid]),
                    's3_data_reference': s3_data_reference
                },
                'epoch_summary': {
                    'total_miners_evaluated': len(self.epoch_miners_evaluated),
                    'miners_evaluated': len(epoch_scores),
                    'winner_current_score': winner_current_score,
                    'runner_up_score': sorted(epoch_scores.values(), reverse=True)[1] if len(epoch_scores) > 1 else 0
                },
                'validation_metadata': {
                    'validation_type': 'epoch_winner',
                    'includes_winning_listings': False,
                    'data_storage_method': 's3_reference',
                    'note': 'Winner data stored in miner S3',
                    'retention_days': 180
                }
            }
            
            bt.logging.success(
                f"🎉 Epoch winner: UID {winner_uid} | "
                f"score={winner_current_score:.2f} | "
                f"data_path={s3_data_reference['s3_path']}"
            )
            
            # Reset for next epoch
            self.epoch_baseline_scores = {}
            self.epoch_miners_evaluated = set()
            self.epoch_start_block = None
            self.epoch_complete = False
            
            return validation_result
            
        except Exception as e:
            bt.logging.error(f"Error collecting epoch winner data: {e}")
            bt.logging.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def _update_and_get_miner_index(
        self, hotkey: str, uid: int, miner_axon: bt.AxonInfo
    ) -> Optional[ScorableMinerIndex]:
        """Updates the index for the specified miner, and returns the latest known index or None if the miner hasn't yet provided an index."""

        bt.logging.info(f"{hotkey}: Getting MinerIndex from miner.")

        try:
            responses: List[GetMinerIndex] = None
            async with bt.dendrite(wallet=self.wallet) as dendrite:
                responses = await dendrite.forward(
                    axons=[miner_axon],
                    synapse=GetMinerIndex(version=constants.PROTOCOL_VERSION),
                    timeout=120,
                )

            response = vali_utils.get_single_successful_response(
                responses, GetMinerIndex
            )
            if not response:
                stored_index = self.storage.read_miner_index(hotkey)
                if stored_index:
                    bt.logging.info(
                        f"{hotkey}: Miner failed to respond with an index. Using last known index."
                    )
                else:
                    bt.logging.warning(
                        f"{hotkey}: Miner failed to respond with an index and has no stored index. "
                        f"Check if miner is properly configured and running."
                    )
                # Miner failed to update the index. Use the latest index, if present.
                return stored_index

            # Validate the index.
            miner_index = None
            try:
                miner_index = vali_utils.get_miner_index_from_response(response)
            except ValueError as e:
                stored_index = self.storage.read_miner_index(hotkey)
                if stored_index:
                    bt.logging.warning(
                        f"{hotkey}: Miner returned an invalid index. Reason: {e}. Using last known index."
                    )
                else:
                    bt.logging.error(
                        f"{hotkey}: Miner returned an invalid index and has no stored index. Reason: {e}. "
                        f"Miner may need to be restarted or reconfigured."
                    )
                # Miner returned an invalid index. Use the latest index, if present.
                return stored_index

            assert miner_index is not None, "Miner index should not be None."

            # Miner replied with a valid index. Store it and return it.
            miner_credibility = self.scorer.get_miner_credibility(uid)
            bt.logging.success(
                f"{hotkey}: Got new compressed miner index of {CompressedMinerIndex.size_bytes(miner_index)} bytes "
                + f"across {CompressedMinerIndex.bucket_count(miner_index)} buckets."
            )
            self.storage.upsert_compressed_miner_index(
                miner_index, hotkey, miner_credibility
            )

            return self.storage.read_miner_index(hotkey)
        except Exception:
            bt.logging.error(
                f"{hotkey} Failed to update and get miner index.",
                traceback.format_exc(),
            )
            return None

    def _on_metagraph_updated(self, metagraph: bt.metagraph, netuid: int):
        """Handles an update to a metagraph."""
        bt.logging.info(
            f"Evaluator processing an update to metagraph on subnet {netuid}."
        )

        with self.lock:
            bt.logging.info(
                "Evaluator: Metagraph updated, re-syncing hotkeys, and moving averages."
            )
            # Zero out all hotkeys that have been replaced.
            old_hotkeys = self.metagraph.hotkeys
            for uid, hotkey in enumerate(old_hotkeys):
                if hotkey != metagraph.hotkeys[uid] or (
                    not utils.is_miner(uid, metagraph, self.vpermit_rao_limit)
                    and not utils.is_validator(uid, metagraph, self.vpermit_rao_limit)
                ):
                    bt.logging.info(
                        f"Hotkey {hotkey} w/ UID {uid} has been unregistered or does not qualify to mine/validate."
                    )
                    self.scorer.reset(uid)  # hotkey has been replaced
                    try:
                        self.storage.delete_miner(hotkey)
                    except Exception:
                        bt.logging.error(
                            f"{hotkey} Failed to delete miner index.",
                            traceback.format_exc(),
                        )
            # Update the iterator. It will keep its current position if possible.
            self.miner_iterator.set_miner_uids(
                #utils.get_miner_uids(self.metagraph, self.vpermit_rao_limit) # uses cached/stale self.metagraph --> iterator may miss new miners and keep removed ones.
                utils.get_miner_uids(metagraph, self.vpermit_rao_limit) # use fresh metagraph --> iterator gets latest eligible UIDs immediately
            )

            # Check to see if the metagraph has changed size.
            # If so, we need to add new hotkeys and moving averages.
            if len(self.metagraph.hotkeys) < len(metagraph.hotkeys):
                self.scorer.resize(len(metagraph.hotkeys))

            self.metagraph = copy.deepcopy(metagraph)

    def exit(self):
        self.should_exit = True
    
    def _get_previous_epoch_id(self, epoch_duration_hours: int = 4) -> str:
        """
        Calculate the most recently completed epoch ID.
        Validators always validate completed epochs, never the active one.
        
        Args:
            epoch_duration_hours: Duration of each epoch in hours (default: 4)
            
        Returns:
            Previous (completed) epoch ID in format "YYYY-MM-DDTHH-00-00"
        """
        import datetime as dt
        
        now_utc = dt.datetime.now(dt.timezone.utc)
        previous_time = now_utc - dt.timedelta(hours=epoch_duration_hours)
        
        epoch_start_hour = (previous_time.hour // epoch_duration_hours) * epoch_duration_hours
        epoch_start = previous_time.replace(hour=epoch_start_hour, minute=0, second=0, microsecond=0)
        
        epoch_id = epoch_start.strftime("%Y-%m-%dT%H-00-00")
        return epoch_id
    
    def _get_expected_total_listings(self) -> Optional[int]:
        """
        Get the total expected listings for the most recently completed epoch.
        Validators always validate completed epochs to ensure miners had time to scrape.
        All miners compete on the same set of zipcodes in each epoch.
        
        Returns:
            Total expected listings, or None if unavailable
        """
        try:
            from common.resi_api_client import create_api_client
            api_client = create_api_client(self.config, self.wallet)
            
            # Get the most recently completed epoch
            epoch_id = self._get_previous_epoch_id()
            
            # Fetch epoch assignments from API
            epoch_data = api_client.get_epoch_assignments(epoch_id)
            
            if not epoch_data or not epoch_data.get('success'):
                bt.logging.debug(f"Failed to fetch assignments for completed epoch {epoch_id}")
                return None
            
            # Sum up expected listings across all zipcodes
            zipcodes_list = epoch_data.get('zipcodes', [])
            if not zipcodes_list:
                bt.logging.debug(f"No zipcodes found for epoch {epoch_id}")
                return None
            
            total_expected = sum(
                z.get('expectedListings', 0) for z in zipcodes_list
            )
            
            if total_expected > 0:
                bt.logging.debug(
                    f"Validating against completed epoch {epoch_id}: Expected {total_expected} "
                    f"total listings across {len(zipcodes_list)} zipcodes"
                )
                return total_expected
            else:
                bt.logging.debug(f"Epoch {epoch_id}: 0 expected listings")
                return None
                
        except Exception as e:
            bt.logging.debug(f"Error getting expected listings: {e}")
            return None
    
    def _get_expected_listings_and_zipcodes(self) -> Tuple[Optional[int], Optional[Set[str]]]:
        """
        Get both the total expected listings AND zipcode set for the most recently completed epoch.
        Fetches data once to avoid duplicate API calls between Tier 1 and Tier 2 validation.
        
        Returns:
            Tuple of (total_expected_listings, zipcode_set) where either can be None if unavailable
        """
        try:
            from common.resi_api_client import create_api_client
            api_client = create_api_client(self.config, self.wallet)
            
            # Get the most recently completed epoch
            epoch_id = self._get_previous_epoch_id()
            
            # Fetch epoch assignments from API
            epoch_data = api_client.get_epoch_assignments(epoch_id)
            
            if not epoch_data or not epoch_data.get('success'):
                bt.logging.debug(f"Failed to fetch assignments for completed epoch {epoch_id}")
                return None, None
            
            # Extract zipcodes list
            zipcodes_list = epoch_data.get('zipcodes', [])
            if not zipcodes_list:
                bt.logging.debug(f"No zipcodes found for epoch {epoch_id}")
                return None, None
            
            # Calculate total expected listings
            total_expected = sum(
                z.get('expectedListings', 0) for z in zipcodes_list
            )
            
            # Extract zipcode set
            zipcode_set = set()
            for z in zipcodes_list:
                zipcode = z.get('zipcode') or z.get('code') or z.get('zip')
                if zipcode:
                    zipcode_set.add(str(zipcode))
            
            if total_expected > 0:
                bt.logging.debug(
                    f"Validating against completed epoch {epoch_id}: Expected {total_expected} "
                    f"total listings across {len(zipcodes_list)} zipcodes ({len(zipcode_set)} unique zipcodes)"
                )
            
            return (total_expected if total_expected > 0 else None, 
                    zipcode_set if zipcode_set else None)
                
        except Exception as e:
            bt.logging.debug(f"Error getting epoch data: {e}")
            return None, None
    
    # Multi-Tier Validation Methods
    
    def _apply_tier1_quantity_validation(self, entities: List[DataEntity], expected_count: Optional[int] = None) -> Tuple[bool, str, dict]:
        """
        Tier 1: Quantity validation - ensure miner has appropriate data quantity
        Validates against ±15% of expected count from zipcode server.
        
        Args:
            entities: List of data entities from miner
            expected_count: Expected listing count from zipcode server (None = use fallback)
            
        Returns:
            Tuple of (passes, reason, metrics)
        """
        actual_count = len(entities)
        
        # If we have expected count from API, use ±15% range
        if expected_count is not None and expected_count > 0:
            expected_min = int(expected_count * 0.85)  # -15%
            expected_max = int(expected_count * 1.15)  # +15%
            
            # Ensure minimum is at least 1
            expected_min = max(1, expected_min)
            
            passes_min = actual_count >= expected_min
            passes_max = actual_count <= expected_max
            passes = passes_min and passes_max
            
            metrics_data = {
                'actual_count': actual_count,
                'expected_count': expected_count,
                'expected_min': expected_min,
                'expected_max': expected_max,
                'passes_min': passes_min,
                'passes_max': passes_max,
                'tier': 1,
                'has_api_data': True
            }
            
            # Build reason message
            if not passes_min and not passes_max:
                reason = f"Quantity check: {actual_count} entities (expected: {expected_count} ±15% = {expected_min}-{expected_max}) - FAIL"
            elif not passes_min:
                reason = f"Quantity check: {actual_count} entities below min {expected_min} (expected: {expected_count} -15%) - FAIL"
            elif not passes_max:
                reason = f"Quantity check: {actual_count} entities exceeds max {expected_max} (expected: {expected_count} +15%) - FAIL"
            else:
                reason = f"Quantity check: {actual_count} entities (expected: {expected_count} ±15% = {expected_min}-{expected_max}) - PASS"
        
        else:
            # Fallback: Use simple minimum check if no API data
            expected_min = 1
            passes = actual_count >= expected_min
            
            metrics_data = {
                'actual_count': actual_count,
                'expected_count': None,
                'expected_min': expected_min,
                'expected_max': None,
                'passes_min': passes,
                'passes_max': True,
                'tier': 1,
                'has_api_data': False
            }
            
            reason = f"Quantity check: {actual_count} entities (min: {expected_min}, no API data) - {'PASS' if passes else 'FAIL'}"
        
        return passes, reason, metrics_data
    
    def _apply_tier2_quality_validation(self, entities: List[DataEntity], epoch_zipcodes: Optional[Set[str]] = None) -> Tuple[bool, str, dict]:
        """
        Tier 2: Data quality validation - field completeness, reasonable values, and epoch zipcode compliance
        
        Args:
            entities: List of data entities
            epoch_zipcodes: Optional set of zipcodes from completed epoch (passed from Tier 1 to avoid duplicate API calls)
            
        Returns:
            Tuple of (passes, reason, metrics)
        """
        if not entities:
            return False, "No entities to validate", {'tier': 2}
        
        # Parse real estate data from entities
        listings = []
        parse_failures = 0
        
        for entity in entities:
            try:
                content_str = entity.content.decode('utf-8')
                listing_data = json.loads(content_str)
                listings.append(listing_data)
            except Exception as e:
                parse_failures += 1
                bt.logging.debug(f"Failed to parse entity: {e}")
        
        if not listings:
            return False, "Failed to parse any entities", {'tier': 2, 'parse_failures': parse_failures}
        
        # Required fields for real estate listings
        required_fields = [
            'zpid', 'address', 'price', 'property_type', 'listing_status'
        ]
        
        # Use epoch zipcodes passed from Tier 1 
        current_epoch_zipcodes = epoch_zipcodes
        
        # Quality metrics
        complete_count = 0
        reasonable_count = 0
        epoch_compliant_count = 0
        
        for listing in listings:
            # Check field completeness
            has_all_fields = all(
                field in listing and listing[field] is not None 
                for field in required_fields
            )
            
            if has_all_fields:
                complete_count += 1
                
                # Check reasonable values
                is_reasonable = True
                
                # Validate price range
                price = listing.get('price')
                if price:
                    try:
                        price_val = int(price)
                        if not (10000 <= price_val <= 50000000):  # $10K to $50M
                            is_reasonable = False
                    except (ValueError, TypeError):
                        is_reasonable = False
                
                # Validate bedrooms
                bedrooms = listing.get('bedrooms')
                if bedrooms is not None:
                    try:
                        bed_val = int(bedrooms)
                        if not (0 <= bed_val <= 20):
                            is_reasonable = False
                    except (ValueError, TypeError):
                        is_reasonable = False
                
                # Validate bathrooms
                bathrooms = listing.get('bathrooms')
                if bathrooms is not None:
                    try:
                        bath_val = float(bathrooms)
                        if not (0 <= bath_val <= 20):
                            is_reasonable = False
                    except (ValueError, TypeError):
                        is_reasonable = False
                
                if is_reasonable:
                    reasonable_count += 1
            
            # Check epoch zipcode compliance (if epoch zipcodes available)
            if current_epoch_zipcodes is not None:
                # Extract zipcode from listing
                listing_zipcode = listing.get('zipcode')
                if not listing_zipcode:
                    # Try to extract from address
                    address = listing.get('address', '')
                    zipcode_match = re.search(r'\b\d{5}\b', address)
                    if zipcode_match:
                        listing_zipcode = zipcode_match.group(0)
                
                # Check if zipcode is in current epoch's assigned zipcodes
                if listing_zipcode and listing_zipcode in current_epoch_zipcodes:
                    epoch_compliant_count += 1
        
        # Calculate quality scores
        completeness_rate = complete_count / len(listings)
        reasonable_rate = reasonable_count / len(listings) if complete_count > 0 else 0
        epoch_compliance_rate = epoch_compliant_count / len(listings) if current_epoch_zipcodes else 1.0
        
        # Thresholds
        completeness_threshold = 0.70  # 70% must have all required fields
        reasonable_threshold = 0.80    # 80% of complete listings must have reasonable values
        epoch_compliance_threshold = 0.60  # 60% of listings must be from current epoch zipcodes (if available)
        
        # Base quality checks (always required)
        passes_basic = (completeness_rate >= completeness_threshold and 
                       reasonable_rate >= reasonable_threshold)
        
        # Epoch compliance check (if epoch zipcodes available)
        passes_epoch = True
        if current_epoch_zipcodes is not None:
            passes_epoch = epoch_compliance_rate >= epoch_compliance_threshold
        
        passes = passes_basic and passes_epoch
        
        metrics_data = {
            'tier': 2,
            'total_listings': len(listings),
            'complete_count': complete_count,
            'reasonable_count': reasonable_count,
            'epoch_compliant_count': epoch_compliant_count,
            'completeness_rate': completeness_rate,
            'reasonable_rate': reasonable_rate,
            'epoch_compliance_rate': epoch_compliance_rate,
            'parse_failures': parse_failures,
            'epoch_check_enabled': current_epoch_zipcodes is not None,
            'current_epoch_zipcode_count': len(current_epoch_zipcodes) if current_epoch_zipcodes else 0
        }
        
        # Build reason message
        if current_epoch_zipcodes is not None:
            reason = (f"Quality: {completeness_rate:.1%} complete, "
                     f"{reasonable_rate:.1%} reasonable, "
                     f"{epoch_compliance_rate:.1%} epoch-compliant "
                     f"({'PASS' if passes else 'FAIL'})")
        else:
            reason = (f"Quality: {completeness_rate:.1%} complete, "
                     f"{reasonable_rate:.1%} reasonable "
                     f"({'PASS' if passes else 'FAIL'}, epoch check N/A)")
        
        return passes, reason, metrics_data
    
    def _apply_tier3_spot_check_validation(
        self, 
        entities: List[DataEntity], 
        validation_results: List[ValidationResult]
    ) -> Tuple[bool, str, dict]:
        """
        Tier 3: Spot-check validation - verify accuracy against real sources
        
        Args:
            entities: List of data entities
            validation_results: Results from scraper validation
            
        Returns:
            Tuple of (passes, reason, metrics)
        """
        if not validation_results:
            return False, "No validation results", {'tier': 3}
        
        # Calculate pass rate
        valid_count = sum(1 for result in validation_results if result.is_valid)
        pass_rate = valid_count / len(validation_results)
        
        # Threshold: 60% of spot checks must pass (relaxed from 80% for real-world conditions)
        spot_check_threshold = 0.60
        passes = pass_rate >= spot_check_threshold
        
        # Calculate total bytes validated
        total_bytes = sum(result.content_size_bytes_validated for result in validation_results)
        
        metrics_data = {
            'tier': 3,
            'total_checks': len(validation_results),
            'valid_count': valid_count,
            'pass_rate': pass_rate,
            'total_bytes_validated': total_bytes,
            'threshold': spot_check_threshold
        }
        
        reason = (f"Spot-check: {valid_count}/{len(validation_results)} passed "
                 f"({pass_rate:.1%}, threshold: {spot_check_threshold:.0%})")
        
        return passes, reason, metrics_data
