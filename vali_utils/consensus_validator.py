"""
Consensus-based validation system for property data.
Uses statistical consensus instead of synthetic validation.
"""

import asyncio
import random
import statistics
import datetime as dt
from typing import Dict, List, Tuple, Optional, Any
import bittensor as bt
from collections import defaultdict
import hashlib
import json

from common.data import DataEntity, DataSource
from common.protocol import DataAssignmentRequest
from rewards.miner_scorer import MinerScorer
from vali_utils.validator_data_api import ValidatorDataAPI, DataAPIConfig
from scraping.provider import ScraperProvider
from scraping.scraper import ScraperId


class PropertyConsensusEngine:
    """
    Statistical consensus engine for property data validation.
    Extends existing OrganicQueryProcessor patterns.
    """

    def __init__(self, config: DataAPIConfig, wallet: bt.wallet, metagraph: bt.metagraph, 
                 scorer: MinerScorer, scraper_provider: ScraperProvider):
        self.config = config
        self.wallet = wallet
        self.metagraph = metagraph
        self.scorer = scorer
        self.scraper_provider = scraper_provider
        
        # Initialize data API client
        self.data_api = ValidatorDataAPI(wallet, config.data_api_url)
        
        # Consensus parameters
        self.consensus_confidence_threshold = config.consensus_confidence_threshold
        self.anomaly_detection_threshold = config.anomaly_detection_threshold
        
        # Track assignments and responses
        self.active_assignments = {}
        self.assignment_responses = defaultdict(list)

    async def process_assignment_responses(self, assignment_id: str, responses: List[DataAssignmentRequest]) -> Dict[str, Any]:
        """
        Process miner responses using statistical consensus.
        Builds on existing OrganicQueryProcessor patterns.
        """
        bt.logging.info(f"Processing {len(responses)} responses for assignment {assignment_id}")

        # Step 1: Filter valid responses (reuse existing pattern)
        valid_responses = self._filter_valid_responses(responses)
        
        if len(valid_responses) < 2:
            bt.logging.warning(f"Insufficient valid responses ({len(valid_responses)}) for consensus")
            return {"status": "insufficient_responses", "responses": valid_responses}

        # Step 2: Calculate statistical consensus using existing credibility
        consensus_data = self._calculate_consensus_with_existing_credibility(valid_responses)
        
        # Step 3: Detect behavioral anomalies (extend existing anomaly detection)
        anomalies = self._detect_behavioral_anomalies(valid_responses)
        
        # Step 4: Optional spot-checking (configurable)
        if self.config.enable_validator_spot_checks and len(anomalies) > self.anomaly_detection_threshold * len(valid_responses):
            bt.logging.info(f"High anomaly rate ({len(anomalies)}/{len(valid_responses)}), performing spot-checks")
            spot_check_results = await self._perform_strategic_spot_check(consensus_data, anomalies)
            consensus_data = self._adjust_consensus_with_spot_check(consensus_data, spot_check_results)
        elif len(anomalies) > self.anomaly_detection_threshold * len(valid_responses):
            bt.logging.info(f"High anomaly rate ({len(anomalies)}/{len(valid_responses)}), applying confidence penalty")
            consensus_data = self._apply_anomaly_confidence_penalty(consensus_data, anomalies)

        # Step 5: Update miner credibility based on consensus agreement
        self._update_miner_credibility_with_consensus(valid_responses, consensus_data)

        return {
            "status": "completed",
            "consensus_data": consensus_data,
            "anomalies_detected": len(anomalies),
            "responses_processed": len(valid_responses),
            "spot_check_performed": self.config.enable_validator_spot_checks and len(anomalies) > self.anomaly_detection_threshold * len(valid_responses)
        }

    def _filter_valid_responses(self, responses: List[DataAssignmentRequest]) -> List[DataAssignmentRequest]:
        """Filter out invalid responses (reuse existing pattern)"""
        valid_responses = []
        
        for response in responses:
            # Check completion status
            if response.completion_status != "completed":
                bt.logging.debug(f"Skipping incomplete response from assignment {response.request_id}")
                continue
                
            # Check if response has data
            if not response.scraped_data or not any(response.scraped_data.values()):
                bt.logging.debug(f"Skipping empty response from assignment {response.request_id}")
                continue
                
            # Check timestamp validity (reuse existing timestamp validation)
            if not self._validate_response_timestamps(response):
                bt.logging.debug(f"Skipping response with invalid timestamps from assignment {response.request_id}")
                continue
                
            valid_responses.append(response)

        bt.logging.info(f"Filtered {len(valid_responses)} valid responses from {len(responses)} total")
        return valid_responses

    def _validate_response_timestamps(self, response: DataAssignmentRequest) -> bool:
        """Validate response timestamps (reuse existing timestamp validation pattern)"""
        try:
            if not response.scrape_timestamp or not response.submission_timestamp:
                return False
                
            scrape_time = dt.datetime.fromisoformat(response.scrape_timestamp.replace('Z', '+00:00'))
            submission_time = dt.datetime.fromisoformat(response.submission_timestamp.replace('Z', '+00:00'))
            
            # Reasonable scraping time: 5 minutes to 2 hours
            scrape_duration = submission_time - scrape_time
            
            if scrape_duration < dt.timedelta(minutes=5):
                bt.logging.warning("Suspiciously fast scraping detected")
                return False
            elif scrape_duration > dt.timedelta(hours=2):
                bt.logging.warning("Data too stale")
                return False
                
            return True
            
        except Exception as e:
            bt.logging.error(f"Error validating timestamps: {e}")
            return False

    def _calculate_consensus_with_existing_credibility(self, responses: List[DataAssignmentRequest]) -> Dict[str, Any]:
        """Calculate consensus using existing MinerScorer credibility values"""
        consensus_results = {}
        
        # Group responses by property
        property_responses = defaultdict(list)
        
        for response in responses:
            # Extract miner UID from response (would need to be added to protocol)
            miner_uid = getattr(response, 'miner_uid', None)
            if miner_uid is None:
                continue
                
            for source, entities in response.scraped_data.items():
                for entity in entities:
                    property_key = self._extract_property_key(entity)
                    if property_key:
                        property_responses[property_key].append({
                            'miner_uid': miner_uid,
                            'entity': entity,
                            'credibility': float(self.scorer.miner_credibility[miner_uid])
                        })

        # Calculate consensus for each property
        for property_key, prop_responses in property_responses.items():
            if len(prop_responses) < 2:
                continue
                
            consensus_results[property_key] = self._calculate_property_consensus(prop_responses)

        bt.logging.info(f"Calculated consensus for {len(consensus_results)} properties")
        return consensus_results

    def _extract_property_key(self, entity: DataEntity) -> Optional[str]:
        """Extract unique property key from DataEntity"""
        try:
            # Parse URI to extract property identifier
            uri = entity.uri
            if 'zillow.com' in uri and '_zpid' in uri:
                zpid = uri.split('/')[-1].replace('_zpid', '').split('?')[0]
                return f"zillow:{zpid}"
            elif 'redfin.com' in uri:
                # Extract Redfin property ID from URI
                prop_id = uri.split('/')[-1].split('?')[0]
                return f"redfin:{prop_id}"
            # Add more property key extraction logic for other sources
            
        except Exception as e:
            bt.logging.error(f"Error extracting property key from {entity.uri}: {e}")
            
        return None

    def _calculate_property_consensus(self, responses: List[Dict]) -> Dict[str, Any]:
        """Calculate consensus for a single property using credibility weighting"""
        if not responses:
            return {"confidence": 0.0, "consensus_data": None}

        # Extract property data from each response
        property_data = []
        total_credibility = 0
        
        for response in responses:
            try:
                entity = response['entity']
                credibility = response['credibility']
                miner_uid = response['miner_uid']
                
                # Decode property data
                content_str = entity.content.decode('utf-8') if isinstance(entity.content, bytes) else entity.content
                prop_data = json.loads(content_str)
                
                property_data.append({
                    'data': prop_data,
                    'credibility': credibility,
                    'miner_uid': miner_uid,
                    'timestamp': entity.datetime
                })
                total_credibility += credibility
                
            except Exception as e:
                bt.logging.error(f"Error parsing property data: {e}")
                continue

        if not property_data:
            return {"confidence": 0.0, "consensus_data": None}

        # Calculate field-level consensus
        field_consensus = {}
        key_fields = ['price', 'bedrooms', 'bathrooms', 'living_area', 'address']
        
        for field in key_fields:
            field_values = {}
            
            for prop in property_data:
                value = prop['data'].get(field)
                if value is not None:
                    value_key = str(value)
                    if value_key not in field_values:
                        field_values[value_key] = {
                            'weight': 0,
                            'miners': [],
                            'value': value
                        }
                    
                    field_values[value_key]['weight'] += prop['credibility']
                    field_values[value_key]['miners'].append(prop['miner_uid'])

            # Find consensus value (highest weighted)
            if field_values:
                consensus_item = max(field_values.items(), key=lambda x: x[1]['weight'] * len(x[1]['miners']))
                field_consensus[field] = {
                    'value': consensus_item[1]['value'],
                    'confidence': consensus_item[1]['weight'] / total_credibility if total_credibility > 0 else 0,
                    'supporting_miners': len(consensus_item[1]['miners']),
                    'total_miners': len(property_data)
                }

        # Calculate overall confidence
        field_confidences = [fc['confidence'] for fc in field_consensus.values()]
        overall_confidence = statistics.mean(field_confidences) if field_confidences else 0.0

        return {
            "confidence": overall_confidence,
            "consensus_data": field_consensus,
            "total_responses": len(property_data),
            "credibility_weighted": True
        }

    def _detect_behavioral_anomalies(self, responses: List[DataAssignmentRequest]) -> List[int]:
        """Detect behavioral anomalies (extend existing anomaly detection)"""
        anomalous_miners = []
        
        # Check for synchronized submissions
        submission_times = []
        miner_uids = []
        
        for response in responses:
            if response.submission_timestamp:
                try:
                    submit_time = dt.datetime.fromisoformat(response.submission_timestamp.replace('Z', '+00:00'))
                    submission_times.append(submit_time)
                    miner_uid = getattr(response, 'miner_uid', None)
                    if miner_uid:
                        miner_uids.append(miner_uid)
                except Exception:
                    continue

        # Detect synchronized submissions (within 30 seconds of each other)
        if len(submission_times) >= 3:
            time_diffs = []
            for i in range(1, len(submission_times)):
                diff = abs((submission_times[i] - submission_times[i-1]).total_seconds())
                time_diffs.append(diff)
            
            # If most submissions are within 30 seconds, flag as synchronized
            synchronized_count = sum(1 for diff in time_diffs if diff < 30)
            if synchronized_count > len(time_diffs) * 0.7:  # 70% synchronized
                bt.logging.warning(f"Detected synchronized submissions: {synchronized_count}/{len(time_diffs)}")
                anomalous_miners.extend(miner_uids)

        # Check for identical content hashes
        content_hashes = defaultdict(list)
        
        for response in responses:
            miner_uid = getattr(response, 'miner_uid', None)
            if not miner_uid:
                continue
                
            for source, entities in response.scraped_data.items():
                for entity in entities:
                    content_hash = hashlib.md5(entity.content).hexdigest()
                    content_hashes[content_hash].append(miner_uid)

        # Flag miners with identical content
        for content_hash, miners in content_hashes.items():
            if len(miners) > 1:
                bt.logging.warning(f"Identical content detected from miners: {miners}")
                anomalous_miners.extend(miners)

        # Remove duplicates
        anomalous_miners = list(set(anomalous_miners))
        
        if anomalous_miners:
            bt.logging.info(f"Detected {len(anomalous_miners)} anomalous miners: {anomalous_miners}")

        return anomalous_miners

    async def _perform_strategic_spot_check(self, consensus_data: Dict[str, Any], 
                                          anomalous_miners: List[int]) -> Dict[str, Any]:
        """Perform spot-checks using existing scraper infrastructure"""
        spot_check_results = {}
        
        # Sample properties for spot-checking (max 5)
        properties_to_check = list(consensus_data.keys())[:5]
        
        bt.logging.info(f"Performing spot-checks on {len(properties_to_check)} properties")
        
        for property_key in properties_to_check:
            try:
                source, prop_id = property_key.split(':', 1)
                
                if source == 'zillow':
                    scraper = self.scraper_provider.get(ScraperId.RAPID_ZILLOW)
                    if scraper:
                        # Create a minimal scrape config for single property
                        from scraping.scraper import ScrapeConfig
                        from common.date_range import DateRange
                        from common.data import DataLabel
                        
                        config = ScrapeConfig(
                            entity_limit=1,
                            date_range=DateRange(
                                start=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
                                end=dt.datetime.now(dt.timezone.utc)
                            ),
                            labels=[DataLabel(value=f"zpid:{prop_id}")]
                        )
                        
                        entities = await scraper.scrape(config)
                        if entities:
                            spot_check_results[property_key] = entities[0]
                            
            except Exception as e:
                bt.logging.error(f"Error during spot-check for {property_key}: {e}")
                continue

        bt.logging.info(f"Completed spot-checks for {len(spot_check_results)} properties")
        return spot_check_results

    def _adjust_consensus_with_spot_check(self, consensus_data: Dict[str, Any], 
                                        spot_check_results: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust consensus based on spot-check results"""
        for property_key, spot_check_entity in spot_check_results.items():
            if property_key in consensus_data:
                try:
                    # Compare spot-check result with consensus
                    spot_check_content = json.loads(spot_check_entity.content.decode('utf-8'))
                    consensus_fields = consensus_data[property_key].get('consensus_data', {})
                    
                    # Validate key fields
                    validation_score = 0
                    total_fields = 0
                    
                    for field, consensus_info in consensus_fields.items():
                        if field in spot_check_content:
                            total_fields += 1
                            consensus_value = consensus_info['value']
                            actual_value = spot_check_content[field]
                            
                            # Allow some tolerance for numerical fields
                            if isinstance(consensus_value, (int, float)) and isinstance(actual_value, (int, float)):
                                if abs(consensus_value - actual_value) / max(consensus_value, actual_value) < 0.1:  # 10% tolerance
                                    validation_score += 1
                            elif consensus_value == actual_value:
                                validation_score += 1

                    # Adjust confidence based on validation
                    if total_fields > 0:
                        validation_ratio = validation_score / total_fields
                        original_confidence = consensus_data[property_key]['confidence']
                        adjusted_confidence = original_confidence * validation_ratio
                        consensus_data[property_key]['confidence'] = adjusted_confidence
                        consensus_data[property_key]['spot_check_validated'] = True
                        consensus_data[property_key]['validation_ratio'] = validation_ratio
                        
                        bt.logging.info(f"Spot-check for {property_key}: {validation_score}/{total_fields} fields validated")

                except Exception as e:
                    bt.logging.error(f"Error adjusting consensus with spot-check for {property_key}: {e}")

        return consensus_data

    def _apply_anomaly_confidence_penalty(self, consensus_data: Dict[str, Any], 
                                        anomalous_miners: List[int]) -> Dict[str, Any]:
        """Apply confidence penalty when anomalies detected but spot-checks disabled"""
        penalty_factor = 0.8  # Reduce confidence by 20%
        
        for property_key, consensus_info in consensus_data.items():
            original_confidence = consensus_info['confidence']
            penalized_confidence = original_confidence * penalty_factor
            consensus_data[property_key]['confidence'] = penalized_confidence
            consensus_data[property_key]['anomaly_penalty_applied'] = True
            
        bt.logging.info(f"Applied anomaly confidence penalty to {len(consensus_data)} properties")
        return consensus_data

    def _update_miner_credibility_with_consensus(self, responses: List[DataAssignmentRequest], 
                                               consensus_data: Dict[str, Any]):
        """Update miner credibility based on consensus agreement"""
        credibility_updates = defaultdict(list)
        
        # Calculate agreement scores for each miner
        for response in responses:
            miner_uid = getattr(response, 'miner_uid', None)
            if not miner_uid:
                continue
                
            agreement_scores = []
            
            for source, entities in response.scraped_data.items():
                for entity in entities:
                    property_key = self._extract_property_key(entity)
                    if property_key and property_key in consensus_data:
                        # Calculate how well this miner's data matches consensus
                        try:
                            content_str = entity.content.decode('utf-8') if isinstance(entity.content, bytes) else entity.content
                            miner_data = json.loads(content_str)
                            consensus_fields = consensus_data[property_key].get('consensus_data', {})
                            
                            field_agreements = []
                            for field, consensus_info in consensus_fields.items():
                                if field in miner_data:
                                    miner_value = miner_data[field]
                                    consensus_value = consensus_info['value']
                                    
                                    # Check agreement
                                    if isinstance(consensus_value, (int, float)) and isinstance(miner_value, (int, float)):
                                        # Allow 5% tolerance for numerical fields
                                        agreement = 1.0 if abs(consensus_value - miner_value) / max(consensus_value, miner_value) < 0.05 else 0.0
                                    else:
                                        agreement = 1.0 if consensus_value == miner_value else 0.0
                                    
                                    field_agreements.append(agreement)
                            
                            if field_agreements:
                                property_agreement = statistics.mean(field_agreements)
                                agreement_scores.append(property_agreement)
                                
                        except Exception as e:
                            bt.logging.error(f"Error calculating agreement for miner {miner_uid}: {e}")
                            continue

            if agreement_scores:
                avg_agreement = statistics.mean(agreement_scores)
                credibility_updates[miner_uid].append(avg_agreement)

        # Apply credibility updates using existing EMA pattern
        for miner_uid, agreements in credibility_updates.items():
            if agreements:
                avg_agreement = statistics.mean(agreements)
                
                # Create validation results in existing format
                from vali_utils.s3_utils import ValidationResult
                
                validation_results = [ValidationResult(
                    is_valid=avg_agreement > 0.8,  # 80% agreement threshold
                    reason=f"Consensus agreement: {avg_agreement:.2f}",
                    content_size_bytes_validated=1000  # Placeholder
                )]
                
                # Use existing credibility update mechanism
                self.scorer._update_credibility(miner_uid, validation_results)
                
                bt.logging.debug(f"Updated credibility for miner {miner_uid}: agreement={avg_agreement:.2f}")
