"""
Enhanced Miner Evaluator that integrates coordinated data distribution
with both consensus-based and API-based validation systems.
"""

import asyncio
import random
import datetime as dt
from typing import Dict, List, Optional, Any
import bittensor as bt
import uuid

from common.data import DataEntity, DataSource
from common.protocol import DataAssignmentRequest
from rewards.miner_scorer import MinerScorer
from vali_utils.validator_data_api import ValidatorDataAPI, DataAPIConfig
from vali_utils.consensus_validator import PropertyConsensusEngine
from vali_utils.api_validator import APIBasedValidator
from vali_utils.miner_evaluator import MinerEvaluator
from scraping.provider import ScraperProvider
from common import utils


class EnhancedMinerEvaluator:
    """
    Enhanced evaluator that extends existing MinerEvaluator with coordinated
    data distribution and configurable validation strategies.
    """

    def __init__(self, config: bt.config, uid: int, metagraph_syncer, s3_reader):
        # Initialize base evaluator
        self.base_evaluator = MinerEvaluator(config, uid, metagraph_syncer, s3_reader)
        
        # Enhanced configuration
        self.data_api_config = DataAPIConfig()
        
        # Initialize validation systems
        self.consensus_engine = PropertyConsensusEngine(
            config=self.data_api_config,
            wallet=self.base_evaluator.wallet,
            metagraph=self.base_evaluator.metagraph,
            scorer=self.base_evaluator.scorer,
            scraper_provider=self.base_evaluator.scraper_provider
        )
        
        self.api_validator = APIBasedValidator(
            config=self.data_api_config,
            wallet=self.base_evaluator.wallet,
            metagraph=self.base_evaluator.metagraph,
            scorer=self.base_evaluator.scorer,
            scraper_provider=self.base_evaluator.scraper_provider
        )
        
        # Track active assignments
        self.active_assignments = {}
        self.assignment_responses = {}
        
        # Statistics
        self.stats = {
            'assignments_created': 0,
            'assignments_completed': 0,
            'consensus_validations': 0,
            'api_validations': 0,
            'total_properties_assigned': 0,
            'total_properties_validated': 0
        }

    def get_scorer(self) -> MinerScorer:
        """Returns the scorer used by the evaluator."""
        return self.base_evaluator.scorer

    async def run_coordinated_evaluation_cycle(self) -> Dict[str, Any]:
        """
        Run a coordinated evaluation cycle that distributes data assignments
        and validates responses using the configured validation strategy.
        """
        bt.logging.info("Starting coordinated evaluation cycle")
        
        try:
            # Step 1: Get data blocks from API
            data_blocks = await self.consensus_engine.data_api.get_data_blocks()
            if not data_blocks:
                bt.logging.error("Failed to get data blocks from API")
                return {"status": "failed", "reason": "api_unavailable"}

            # Step 2: Get available miners
            available_miners = utils.get_miner_uids(
                self.base_evaluator.metagraph, 
                self.base_evaluator.vpermit_rao_limit
            )
            
            if len(available_miners) < 3:
                bt.logging.warning(f"Insufficient miners for coordinated evaluation: {len(available_miners)}")
                return {"status": "insufficient_miners", "available_miners": len(available_miners)}

            # Step 3: Create miner assignments
            assignments = self.consensus_engine.data_api.create_miner_assignments(
                data_blocks, 
                available_miners, 
                self.data_api_config.miners_per_property
            )

            # Step 4: Distribute assignments to miners
            assignment_id = f"assignment_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            distribution_results = await self._distribute_assignments(assignment_id, assignments, data_blocks)

            # Step 5: Wait for responses (with timeout)
            timeout_hours = self.data_api_config.assignment_timeout_hours
            responses = await self._collect_assignment_responses(assignment_id, timeout_hours)

            # Step 6: Validate responses using configured strategy
            validation_results = await self._validate_assignment_responses(assignment_id, responses)

            # Step 7: Update statistics
            self._update_statistics(assignment_id, assignments, responses, validation_results)

            bt.logging.info(f"Coordinated evaluation cycle completed: {len(responses)} responses processed")

            return {
                "status": "completed",
                "assignment_id": assignment_id,
                "miners_assigned": len(distribution_results.get('successful_assignments', [])),
                "responses_received": len(responses),
                "validation_results": validation_results,
                "statistics": self.get_statistics()
            }

        except Exception as e:
            bt.logging.error(f"Error in coordinated evaluation cycle: {e}")
            return {"status": "error", "error": str(e)}

    async def _distribute_assignments(self, assignment_id: str, assignments: Dict[str, List[int]], 
                                    data_blocks: Dict[str, Any]) -> Dict[str, Any]:
        """Distribute data assignments to miners"""
        bt.logging.info(f"Distributing assignments for {assignment_id}")
        
        successful_assignments = []
        failed_assignments = []
        
        # Group assignments by miner
        miner_assignments = {}
        for property_id, miner_uids in assignments.items():
            for miner_uid in miner_uids:
                if miner_uid not in miner_assignments:
                    miner_assignments[miner_uid] = []
                miner_assignments[miner_uid].append(property_id)

        # Create and send assignment requests
        for miner_uid, property_list in miner_assignments.items():
            try:
                # Format assignment data for this miner
                assignment_data = self.consensus_engine.data_api.format_assignment_for_miner(
                    miner_uid, data_blocks, assignments
                )

                # Create assignment request
                assignment_request = DataAssignmentRequest(
                    request_id=f"{assignment_id}_miner_{miner_uid}",
                    assignment_data=assignment_data,
                    expires_at=(dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=self.data_api_config.assignment_timeout_hours)).isoformat(),
                    expected_completion=(dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)).isoformat(),
                    assignment_type="property_scraping",
                    block_id=data_blocks.get('request_id', assignment_id),
                    priority=1
                )

                # Send assignment to miner
                bt.logging.debug(f"Sending assignment to miner {miner_uid}: {len(property_list)} properties")
                
                # Use existing dendrite infrastructure
                response = await self.base_evaluator.dendrite(
                    axons=[self.base_evaluator.metagraph.axons[miner_uid]],
                    synapse=assignment_request,
                    timeout=30
                )

                if response and len(response) > 0:
                    successful_assignments.append(miner_uid)
                    # Store assignment for tracking
                    self.active_assignments[f"{assignment_id}_miner_{miner_uid}"] = {
                        'miner_uid': miner_uid,
                        'assignment_request': assignment_request,
                        'sent_at': dt.datetime.now(dt.timezone.utc),
                        'status': 'sent'
                    }
                else:
                    failed_assignments.append(miner_uid)
                    bt.logging.warning(f"Failed to send assignment to miner {miner_uid}")

            except Exception as e:
                bt.logging.error(f"Error sending assignment to miner {miner_uid}: {e}")
                failed_assignments.append(miner_uid)

        self.stats['assignments_created'] += len(successful_assignments)

        return {
            "successful_assignments": successful_assignments,
            "failed_assignments": failed_assignments,
            "total_miners": len(miner_assignments)
        }

    async def _collect_assignment_responses(self, assignment_id: str, timeout_hours: int) -> List[DataAssignmentRequest]:
        """Collect responses from miners within timeout period"""
        bt.logging.info(f"Collecting responses for {assignment_id} (timeout: {timeout_hours}h)")
        
        responses = []
        timeout_time = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=timeout_hours)
        
        # In a real implementation, this would collect responses as they come in
        # For now, we'll simulate the collection process
        
        while dt.datetime.now(dt.timezone.utc) < timeout_time:
            # Check for completed assignments
            completed_assignments = []
            
            for assignment_key, assignment_info in self.active_assignments.items():
                if assignment_key.startswith(assignment_id) and assignment_info['status'] == 'sent':
                    try:
                        # In real implementation, check if miner has responded
                        # For now, simulate response collection
                        miner_uid = assignment_info['miner_uid']
                        
                        # Query miner for response (this would be done differently in practice)
                        # Here we're simulating the response collection
                        bt.logging.debug(f"Checking response from miner {miner_uid}")
                        
                        # Mark as completed (in real implementation, check actual response)
                        assignment_info['status'] = 'completed'
                        completed_assignments.append(assignment_key)
                        
                    except Exception as e:
                        bt.logging.error(f"Error collecting response from assignment {assignment_key}: {e}")

            # Break if all assignments completed
            if len(completed_assignments) == len([k for k in self.active_assignments.keys() if k.startswith(assignment_id)]):
                break

            # Wait before checking again
            await asyncio.sleep(30)

        # Clean up completed assignments
        for assignment_key in completed_assignments:
            if assignment_key in self.active_assignments:
                del self.active_assignments[assignment_key]

        bt.logging.info(f"Collected {len(responses)} responses for {assignment_id}")
        return responses

    async def _validate_assignment_responses(self, assignment_id: str, responses: List[DataAssignmentRequest]) -> Dict[str, Any]:
        """Validate assignment responses using configured strategy"""
        if not responses:
            return {"status": "no_responses", "validation_method": "none"}

        bt.logging.info(f"Validating {len(responses)} responses using {'consensus' if not self.data_api_config.enable_validator_spot_checks else 'api'} validation")

        if self.data_api_config.enable_validator_spot_checks:
            # Use API-based validation
            self.stats['api_validations'] += 1
            return await self.api_validator.process_assignment_responses(assignment_id, responses)
        else:
            # Use consensus-based validation
            self.stats['consensus_validations'] += 1
            return await self.consensus_engine.process_assignment_responses(assignment_id, responses)

    def _update_statistics(self, assignment_id: str, assignments: Dict[str, List[int]], 
                          responses: List[DataAssignmentRequest], validation_results: Dict[str, Any]):
        """Update evaluation statistics"""
        self.stats['assignments_completed'] += 1
        self.stats['total_properties_assigned'] += len(assignments)
        
        # Count validated properties
        if validation_results.get('status') == 'completed':
            if 'validation_results' in validation_results:
                # API validation results
                total_validations = validation_results.get('total_validations', 0)
                self.stats['total_properties_validated'] += total_validations
            elif 'consensus_data' in validation_results:
                # Consensus validation results
                consensus_properties = len(validation_results.get('consensus_data', {}))
                self.stats['total_properties_validated'] += consensus_properties

    def get_statistics(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        return {
            **self.stats,
            'validation_mode': 'api' if self.data_api_config.enable_validator_spot_checks else 'consensus',
            'api_validator_stats': self.api_validator.get_validation_statistics() if self.data_api_config.enable_validator_spot_checks else None,
            'configuration': self.data_api_config.to_dict()
        }

    def reset_statistics(self):
        """Reset evaluation statistics"""
        self.stats = {
            'assignments_created': 0,
            'assignments_completed': 0,
            'consensus_validations': 0,
            'api_validations': 0,
            'total_properties_assigned': 0,
            'total_properties_validated': 0
        }
        
        if self.data_api_config.enable_validator_spot_checks:
            self.api_validator.reset_statistics()

    # Delegate other methods to base evaluator for backward compatibility
    def __getattr__(self, name):
        """Delegate unknown methods to base evaluator"""
        return getattr(self.base_evaluator, name)
