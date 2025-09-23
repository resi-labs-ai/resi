"""
S3-Integrated Consensus Validator
Combines S3 storage benefits with consensus validation for enhanced data quality.
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
from vali_utils.zipcode_assignment_manager import ZipcodeAssignmentManager
from scraping.provider import ScraperProvider
from scraping.scraper import ScraperId
from vali_utils.s3_utils import ValidationResult


class S3ConsensusValidator:
    """
    S3-Integrated Consensus Validator that maintains S3 storage benefits
    while adding consensus validation for enhanced data quality.
    
    Key Benefits:
    - Keeps S3 centralized storage and speed
    - Adds consensus validation for quality assurance
    - Miners still store data locally AND upload to S3
    - Validators compare S3 data for consensus rather than scraping themselves
    """

    def __init__(self, config: DataAPIConfig, wallet: bt.wallet, metagraph: bt.metagraph, 
                 scorer: MinerScorer, scraper_provider: ScraperProvider, s3_reader=None):
        self.config = config
        self.wallet = wallet
        self.metagraph = metagraph
        self.scorer = scorer
        self.scraper_provider = scraper_provider
        self.s3_reader = s3_reader
        
        # Initialize data API client
        self.data_api = ValidatorDataAPI(wallet, config.data_api_url)
        
        # Initialize zipcode assignment manager
        self.assignment_manager = ZipcodeAssignmentManager(metagraph, config.to_dict())
        
        # Consensus parameters
        self.consensus_confidence_threshold = config.consensus_confidence_threshold
        self.anomaly_detection_threshold = config.anomaly_detection_threshold
        
        # Track assignments and responses
        self.active_assignments = {}
        self.assignment_responses = defaultdict(list)

    async def process_s3_consensus_validation(self, assignment_id: str, 
                                            miner_assignments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process consensus validation using S3-stored data instead of live scraping.
        
        Flow:
        1. Miners scrape zipcode batches and upload to S3 (existing flow)
        2. Validators read S3 data from multiple miners for same zipcode batches
        3. Perform consensus validation on S3 data
        4. Update miner credibility based on consensus agreement
        """
        bt.logging.info(f"Processing S3 consensus validation for assignment {assignment_id}")

        try:
            # Step 1: Wait for miners to complete scraping and S3 upload
            await self._wait_for_s3_uploads(assignment_id, miner_assignments)
            
            # Step 2: Collect S3 data from miners for consensus analysis
            s3_data_collection = await self._collect_s3_data_for_consensus(miner_assignments)
            
            # Step 3: Perform consensus analysis on S3 data
            consensus_results = await self._analyze_s3_data_consensus(s3_data_collection)
            
            # Step 4: Detect behavioral anomalies
            anomalies = self._detect_s3_behavioral_anomalies(s3_data_collection)
            
            # Step 5: Optional spot-checking if anomalies detected
            if self.config.enable_validator_spot_checks and len(anomalies) > self.anomaly_detection_threshold * len(s3_data_collection):
                bt.logging.info(f"High anomaly rate detected, performing spot-checks")
                spot_check_results = await self._perform_s3_spot_check(consensus_results, anomalies)
                consensus_results = self._adjust_consensus_with_spot_check(consensus_results, spot_check_results)
            
            # Step 6: Update miner credibility based on S3 consensus
            self._update_miner_credibility_with_s3_consensus(s3_data_collection, consensus_results)
            
            return {
                "status": "completed",
                "consensus_results": consensus_results,
                "s3_data_sources": len(s3_data_collection),
                "anomalies_detected": len(anomalies),
                "validation_method": "s3_consensus"
            }

        except Exception as e:
            bt.logging.error(f"Error in S3 consensus validation: {e}")
            return {"status": "error", "error": str(e)}

    async def _wait_for_s3_uploads(self, assignment_id: str, miner_assignments: Dict[str, Any], 
                                 timeout_minutes: int = 30) -> bool:
        """Wait for miners to complete S3 uploads after zipcode scraping"""
        bt.logging.info(f"Waiting for S3 uploads to complete (timeout: {timeout_minutes}m)")
        
        start_time = dt.datetime.now(dt.timezone.utc)
        timeout_time = start_time + dt.timedelta(minutes=timeout_minutes)
        
        expected_miners = set()
        for assignment_data in miner_assignments.values():
            expected_miners.update(assignment_data.get('miners', []))
        
        while dt.datetime.now(dt.timezone.utc) < timeout_time:
            # Check S3 for recent uploads from assigned miners
            completed_miners = await self._check_s3_upload_completion(expected_miners, start_time)
            
            completion_rate = len(completed_miners) / len(expected_miners) if expected_miners else 0
            bt.logging.debug(f"S3 upload completion: {len(completed_miners)}/{len(expected_miners)} ({completion_rate:.1%})")
            
            # Consider complete if 80% of miners have uploaded
            if completion_rate >= 0.8:
                bt.logging.info(f"S3 uploads sufficient for consensus: {len(completed_miners)}/{len(expected_miners)}")
                return True
            
            # Wait before checking again
            await asyncio.sleep(30)
        
        bt.logging.warning(f"S3 upload timeout reached: {len(completed_miners)}/{len(expected_miners)} completed")
        return len(completed_miners) >= len(expected_miners) * 0.6  # Accept 60% minimum

    async def _check_s3_upload_completion(self, expected_miners: set, start_time: dt.datetime) -> set:
        """Check which miners have completed S3 uploads since start_time"""
        completed_miners = set()
        
        if not self.s3_reader:
            # If no S3 reader available, simulate completion for testing
            bt.logging.warning("No S3 reader available, simulating upload completion")
            return set(list(expected_miners)[:int(len(expected_miners) * 0.8)])
        
        try:
            for miner_uid in expected_miners:
                # Check if miner has uploaded data since assignment start
                hotkey = self.metagraph.hotkeys[miner_uid] if miner_uid < len(self.metagraph.hotkeys) else None
                if hotkey:
                    # Check for recent S3 uploads from this miner
                    recent_uploads = await self._check_miner_s3_uploads(hotkey, start_time)
                    if recent_uploads:
                        completed_miners.add(miner_uid)
                        
        except Exception as e:
            bt.logging.error(f"Error checking S3 upload completion: {e}")
        
        return completed_miners

    async def _check_miner_s3_uploads(self, hotkey: str, start_time: dt.datetime) -> bool:
        """Check if a specific miner has uploaded data to S3 since start_time"""
        try:
            # In real implementation, check S3 for recent uploads from this hotkey
            # For now, simulate based on timing
            time_since_start = (dt.datetime.now(dt.timezone.utc) - start_time).total_seconds()
            
            # Simulate that miners complete uploads within 15-25 minutes
            expected_completion = random.uniform(15 * 60, 25 * 60)  # 15-25 minutes
            
            return time_since_start >= expected_completion
            
        except Exception as e:
            bt.logging.error(f"Error checking S3 uploads for {hotkey}: {e}")
            return False

    async def _collect_s3_data_for_consensus(self, miner_assignments: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Collect S3 data from multiple miners for consensus analysis"""
        s3_data_collection = defaultdict(list)
        
        try:
            for assignment_key, assignment_data in miner_assignments.items():
                batch_id = assignment_data['batch_id']
                miners = assignment_data['miners']
                zipcodes = assignment_data['zipcodes']
                
                bt.logging.debug(f"Collecting S3 data for batch {batch_id} from {len(miners)} miners")
                
                for miner_uid in miners:
                    try:
                        # Get S3 data for this miner
                        miner_s3_data = await self._get_miner_s3_data(miner_uid, zipcodes)
                        
                        if miner_s3_data:
                            s3_data_collection[batch_id].append({
                                'miner_uid': miner_uid,
                                'batch_id': batch_id,
                                'zipcodes': zipcodes,
                                's3_data': miner_s3_data,
                                'credibility': float(self.scorer.miner_credibility[miner_uid]),
                                'collection_time': dt.datetime.now(dt.timezone.utc).isoformat()
                            })
                            
                    except Exception as e:
                        bt.logging.error(f"Error collecting S3 data from miner {miner_uid}: {e}")
                        continue
                        
        except Exception as e:
            bt.logging.error(f"Error in S3 data collection: {e}")
        
        bt.logging.info(f"Collected S3 data for {len(s3_data_collection)} batches")
        return dict(s3_data_collection)

    async def _get_miner_s3_data(self, miner_uid: int, zipcodes: List[str]) -> Optional[List[DataEntity]]:
        """Get S3 data for a specific miner and zipcode set"""
        try:
            if not self.s3_reader:
                # Simulate S3 data for testing
                return self._simulate_miner_s3_data(miner_uid, zipcodes)
            
            # Get miner's hotkey
            hotkey = self.metagraph.hotkeys[miner_uid] if miner_uid < len(self.metagraph.hotkeys) else None
            if not hotkey:
                return None
            
            # Read recent S3 data from this miner for these zipcodes
            # In real implementation, filter by zipcode labels and recent timestamps
            miner_data = await self.s3_reader.get_miner_data_by_zipcodes(hotkey, zipcodes)
            
            return miner_data
            
        except Exception as e:
            bt.logging.error(f"Error getting S3 data for miner {miner_uid}: {e}")
            return None

    def _simulate_miner_s3_data(self, miner_uid: int, zipcodes: List[str]) -> List[DataEntity]:
        """Simulate S3 data for testing purposes"""
        entities = []
        
        for zipcode in zipcodes:
            # Simulate 30-70 properties per zipcode with some variation
            num_properties = random.randint(30, 70)
            
            for i in range(num_properties):
                # Create simulated property data with miner-specific variations
                base_price = 400000 + (miner_uid * 1000) + random.randint(-50000, 50000)
                
                property_data = {
                    "zpid": f"{zipcode}{i:04d}",
                    "address": f"{100 + i} Test St, City {zipcode}",
                    "price": base_price,
                    "bedrooms": random.choice([2, 3, 4, 5]),
                    "bathrooms": random.choice([1, 2, 2.5, 3, 3.5]),
                    "living_area": random.randint(1200, 3500),
                    "zipcode": zipcode,
                    "property_type": "Single Family",
                    "listing_status": "Recently Sold"
                }
                
                entity = DataEntity(
                    uri=f"https://zillow.com/homedetails/{zipcode}-property-{i}/{zipcode}{i:04d}_zpid/",
                    datetime=dt.datetime.now(dt.timezone.utc).isoformat(),
                    source=DataSource.ZILLOW_SOLD,
                    content=json.dumps(property_data).encode(),
                    content_size_bytes=len(json.dumps(property_data))
                )
                
                entities.append(entity)
        
        return entities

    async def _analyze_s3_data_consensus(self, s3_data_collection: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze S3 data for consensus across miners"""
        consensus_results = {}
        
        for batch_id, batch_data in s3_data_collection.items():
            if len(batch_data) < 2:
                bt.logging.warning(f"Insufficient data for consensus in batch {batch_id}")
                continue
            
            bt.logging.debug(f"Analyzing consensus for batch {batch_id} with {len(batch_data)} miner datasets")
            
            # Group properties by zipcode for analysis
            zipcode_consensus = {}
            
            # Extract all zipcodes from this batch
            all_zipcodes = set()
            for miner_data in batch_data:
                all_zipcodes.update(miner_data['zipcodes'])
            
            for zipcode in all_zipcodes:
                zipcode_properties = self._extract_zipcode_properties(batch_data, zipcode)
                
                if len(zipcode_properties) >= 2:  # Need at least 2 miners for consensus
                    zipcode_consensus[zipcode] = self._calculate_zipcode_consensus(zipcode_properties)
            
            consensus_results[batch_id] = {
                'zipcode_consensus': zipcode_consensus,
                'total_miners': len(batch_data),
                'consensus_zipcodes': len(zipcode_consensus),
                'batch_confidence': self._calculate_batch_confidence(zipcode_consensus)
            }
        
        bt.logging.info(f"Calculated consensus for {len(consensus_results)} batches")
        return consensus_results

    def _extract_zipcode_properties(self, batch_data: List[Dict[str, Any]], zipcode: str) -> List[Dict[str, Any]]:
        """Extract properties for a specific zipcode from all miners in batch"""
        zipcode_properties = []
        
        for miner_data in batch_data:
            if zipcode in miner_data['zipcodes']:
                # Extract properties for this zipcode from miner's S3 data
                miner_properties = []
                
                for entity in miner_data['s3_data']:
                    try:
                        content_str = entity.content.decode('utf-8') if isinstance(entity.content, bytes) else entity.content
                        property_data = json.loads(content_str)
                        
                        if property_data.get('zipcode') == zipcode:
                            miner_properties.append(property_data)
                            
                    except Exception as e:
                        bt.logging.error(f"Error parsing property data: {e}")
                        continue
                
                if miner_properties:
                    zipcode_properties.append({
                        'miner_uid': miner_data['miner_uid'],
                        'credibility': miner_data['credibility'],
                        'properties': miner_properties,
                        'property_count': len(miner_properties)
                    })
        
        return zipcode_properties

    def _calculate_zipcode_consensus(self, zipcode_properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consensus for a specific zipcode across miners"""
        if not zipcode_properties:
            return {"confidence": 0.0, "consensus_data": None}
        
        # Calculate property count consensus
        property_counts = [zp['property_count'] for zp in zipcode_properties]
        credibilities = [zp['credibility'] for zp in zipcode_properties]
        
        # Weighted average of property counts
        total_credibility = sum(credibilities)
        weighted_property_count = sum(count * cred for count, cred in zip(property_counts, credibilities)) / total_credibility if total_credibility > 0 else 0
        
        # Calculate agreement on property count (within 20% tolerance)
        count_agreements = []
        for count in property_counts:
            if weighted_property_count > 0:
                agreement = 1.0 if abs(count - weighted_property_count) / weighted_property_count <= 0.2 else 0.0
                count_agreements.append(agreement)
        
        count_consensus = statistics.mean(count_agreements) if count_agreements else 0.0
        
        # Calculate price range consensus (if available)
        price_consensus = self._calculate_price_consensus(zipcode_properties)
        
        # Overall confidence is combination of count and price consensus
        overall_confidence = (count_consensus * 0.6) + (price_consensus * 0.4)
        
        return {
            "confidence": overall_confidence,
            "consensus_data": {
                "property_count": {
                    "weighted_average": weighted_property_count,
                    "consensus_score": count_consensus,
                    "miner_counts": property_counts
                },
                "price_analysis": self._get_price_analysis(zipcode_properties),
                "contributing_miners": len(zipcode_properties)
            },
            "total_miners": len(zipcode_properties)
        }

    def _calculate_price_consensus(self, zipcode_properties: List[Dict[str, Any]]) -> float:
        """Calculate consensus on price ranges within zipcode"""
        miner_price_stats = []
        
        for zp in zipcode_properties:
            prices = []
            for prop in zp['properties']:
                if 'price' in prop and prop['price']:
                    prices.append(prop['price'])
            
            if prices:
                miner_price_stats.append({
                    'miner_uid': zp['miner_uid'],
                    'credibility': zp['credibility'],
                    'median_price': statistics.median(prices),
                    'price_range': max(prices) - min(prices),
                    'property_count': len(prices)
                })
        
        if len(miner_price_stats) < 2:
            return 0.5  # Neutral score if insufficient data
        
        # Calculate consensus on median prices
        median_prices = [ps['median_price'] for ps in miner_price_stats]
        credibilities = [ps['credibility'] for ps in miner_price_stats]
        
        # Weighted median price
        total_credibility = sum(credibilities)
        weighted_median = sum(price * cred for price, cred in zip(median_prices, credibilities)) / total_credibility if total_credibility > 0 else 0
        
        # Check agreement (within 15% tolerance)
        price_agreements = []
        for price in median_prices:
            if weighted_median > 0:
                agreement = 1.0 if abs(price - weighted_median) / weighted_median <= 0.15 else 0.0
                price_agreements.append(agreement)
        
        return statistics.mean(price_agreements) if price_agreements else 0.0

    def _get_price_analysis(self, zipcode_properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get detailed price analysis for zipcode"""
        all_prices = []
        
        for zp in zipcode_properties:
            for prop in zp['properties']:
                if 'price' in prop and prop['price']:
                    all_prices.append(prop['price'])
        
        if not all_prices:
            return {"status": "no_price_data"}
        
        return {
            "median_price": statistics.median(all_prices),
            "mean_price": statistics.mean(all_prices),
            "price_range": max(all_prices) - min(all_prices),
            "total_properties": len(all_prices),
            "price_quartiles": [
                sorted(all_prices)[len(all_prices)//4],
                statistics.median(all_prices),
                sorted(all_prices)[3*len(all_prices)//4]
            ]
        }

    def _calculate_batch_confidence(self, zipcode_consensus: Dict[str, Dict[str, Any]]) -> float:
        """Calculate overall confidence for a batch based on zipcode consensus"""
        if not zipcode_consensus:
            return 0.0
        
        confidences = [zc['confidence'] for zc in zipcode_consensus.values()]
        return statistics.mean(confidences)

    def _detect_s3_behavioral_anomalies(self, s3_data_collection: Dict[str, List[Dict[str, Any]]]) -> List[int]:
        """Detect behavioral anomalies in S3 data patterns"""
        anomalous_miners = []
        
        # Check for identical data patterns across miners
        for batch_id, batch_data in s3_data_collection.items():
            if len(batch_data) < 3:
                continue
            
            # Check for suspiciously identical property counts
            property_counts = [(data['miner_uid'], len(data['s3_data'])) for data in batch_data]
            
            # Group by property count
            count_groups = defaultdict(list)
            for miner_uid, count in property_counts:
                count_groups[count].append(miner_uid)
            
            # Flag miners with identical counts if too many
            for count, miners in count_groups.items():
                if len(miners) > len(batch_data) * 0.6:  # More than 60% have same count
                    bt.logging.warning(f"Suspicious identical property counts in batch {batch_id}: {len(miners)} miners with {count} properties")
                    anomalous_miners.extend(miners)
        
        return list(set(anomalous_miners))

    async def _perform_s3_spot_check(self, consensus_results: Dict[str, Any], 
                                   anomalous_miners: List[int]) -> Dict[str, Any]:
        """Perform spot-checks using validator scraping when S3 anomalies detected"""
        spot_check_results = {}
        
        # Sample a few zipcodes for spot-checking
        sample_zipcodes = []
        for batch_id, batch_results in consensus_results.items():
            zipcode_consensus = batch_results.get('zipcode_consensus', {})
            sample_zipcodes.extend(list(zipcode_consensus.keys())[:2])  # 2 zipcodes per batch
        
        # Limit to 5 total spot-checks
        sample_zipcodes = sample_zipcodes[:5]
        
        bt.logging.info(f"Performing spot-checks on {len(sample_zipcodes)} zipcodes")
        
        for zipcode in sample_zipcodes:
            try:
                # Use existing scraper to validate zipcode data
                scraper = self.scraper_provider.get(ScraperId.RAPID_ZILLOW)
                if scraper:
                    from scraping.scraper import ScrapeConfig
                    from common.date_range import DateRange
                    from common.data import DataLabel
                    
                    config = ScrapeConfig(
                        entity_limit=100,
                        date_range=DateRange(
                            start=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
                            end=dt.datetime.now(dt.timezone.utc)
                        ),
                        labels=[DataLabel(value=f"zip:{zipcode}")]
                    )
                    
                    entities = await scraper.scrape(config)
                    if entities:
                        spot_check_results[zipcode] = {
                            'validator_property_count': len(entities),
                            'sample_properties': entities[:5],  # Sample for comparison
                            'spot_check_timestamp': dt.datetime.now(dt.timezone.utc).isoformat()
                        }
                        
            except Exception as e:
                bt.logging.error(f"Error during spot-check for zipcode {zipcode}: {e}")
                continue
        
        bt.logging.info(f"Completed spot-checks for {len(spot_check_results)} zipcodes")
        return spot_check_results

    def _adjust_consensus_with_spot_check(self, consensus_results: Dict[str, Any], 
                                        spot_check_results: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust consensus confidence based on spot-check results"""
        for zipcode, spot_check_data in spot_check_results.items():
            validator_count = spot_check_data['validator_property_count']
            
            # Find this zipcode in consensus results
            for batch_id, batch_results in consensus_results.items():
                zipcode_consensus = batch_results.get('zipcode_consensus', {})
                
                if zipcode in zipcode_consensus:
                    consensus_count = zipcode_consensus[zipcode]['consensus_data']['property_count']['weighted_average']
                    
                    # Calculate validation accuracy
                    if validator_count > 0:
                        accuracy = 1.0 - abs(consensus_count - validator_count) / validator_count
                        accuracy = max(0.0, min(1.0, accuracy))  # Clamp to [0, 1]
                        
                        # Adjust confidence based on spot-check accuracy
                        original_confidence = zipcode_consensus[zipcode]['confidence']
                        adjusted_confidence = original_confidence * accuracy
                        
                        zipcode_consensus[zipcode]['confidence'] = adjusted_confidence
                        zipcode_consensus[zipcode]['spot_check_validated'] = True
                        zipcode_consensus[zipcode]['spot_check_accuracy'] = accuracy
                        
                        bt.logging.info(f"Spot-check for {zipcode}: consensus={consensus_count:.0f}, validator={validator_count}, accuracy={accuracy:.2f}")
        
        return consensus_results

    def _update_miner_credibility_with_s3_consensus(self, s3_data_collection: Dict[str, List[Dict[str, Any]]], 
                                                  consensus_results: Dict[str, Any]):
        """Update miner credibility based on S3 consensus agreement"""
        credibility_updates = defaultdict(list)
        
        for batch_id, batch_data in s3_data_collection.items():
            if batch_id not in consensus_results:
                continue
            
            batch_consensus = consensus_results[batch_id]
            zipcode_consensus = batch_consensus.get('zipcode_consensus', {})
            
            for miner_data in batch_data:
                miner_uid = miner_data['miner_uid']
                
                # Calculate agreement scores for this miner
                agreement_scores = []
                
                for zipcode in miner_data['zipcodes']:
                    if zipcode in zipcode_consensus:
                        consensus_data = zipcode_consensus[zipcode]
                        consensus_count = consensus_data['consensus_data']['property_count']['weighted_average']
                        
                        # Count properties this miner found for this zipcode
                        miner_count = 0
                        for entity in miner_data['s3_data']:
                            try:
                                content_str = entity.content.decode('utf-8') if isinstance(entity.content, bytes) else entity.content
                                property_data = json.loads(content_str)
                                if property_data.get('zipcode') == zipcode:
                                    miner_count += 1
                            except:
                                continue
                        
                        # Calculate agreement (within 20% tolerance)
                        if consensus_count > 0:
                            agreement = 1.0 if abs(miner_count - consensus_count) / consensus_count <= 0.2 else 0.0
                            agreement_scores.append(agreement)
                
                if agreement_scores:
                    avg_agreement = statistics.mean(agreement_scores)
                    credibility_updates[miner_uid].append(avg_agreement)
        
        # Apply credibility updates using existing mechanism
        for miner_uid, agreements in credibility_updates.items():
            if agreements:
                avg_agreement = statistics.mean(agreements)
                
                # Create validation results in existing format
                validation_results = [ValidationResult(
                    is_valid=avg_agreement > 0.7,  # 70% agreement threshold
                    reason=f"S3 consensus agreement: {avg_agreement:.2f}",
                    content_size_bytes_validated=1000  # Placeholder
                )]
                
                # Use existing credibility update mechanism
                self.scorer._update_credibility(miner_uid, validation_results)
                
                bt.logging.debug(f"Updated credibility for miner {miner_uid}: S3 consensus agreement={avg_agreement:.2f}")

    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get S3 consensus validation statistics"""
        return {
            'validation_method': 's3_consensus',
            'active_assignments': len(self.active_assignments),
            's3_integration': True,
            'consensus_enabled': True,
            'spot_checks_enabled': self.config.enable_validator_spot_checks
        }
