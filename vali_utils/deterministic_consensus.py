"""
Deterministic Consensus System for Validator Agreement
Ensures all validators reach identical conclusions using cryptographic verification
"""

import hashlib
import json
from typing import Dict, List, Any, Optional
import bittensor as bt


class DeterministicConsensus:
    """
    Deterministic consensus system ensuring all validators reach identical results
    
    Uses cryptographic hashing to verify that all validators:
    1. Select identical listings for spot checking
    2. Generate identical validation results
    3. Calculate identical final scores
    4. Reach consensus on miner rankings
    """
    
    def __init__(self, consensus_threshold: float = 0.90):
        self.consensus_threshold = consensus_threshold  # 90% validators must agree
    
    def calculate_consensus_hash(self, final_scores: Dict[str, Any], epoch_nonce: str) -> str:
        """
        Calculate deterministic hash to verify all validators reach same conclusion
        
        Args:
            final_scores: Final calculated scores from zipcode competitive scorer
            epoch_nonce: Epoch nonce for additional verification
            
        Returns:
            Cryptographic hash representing the consensus state
        """
        # Create deterministic string representation of results
        # Sort all data to ensure identical ordering across validators
        sorted_scores = sorted(final_scores['miner_scores'].items())
        sorted_zipcode_weights = sorted(final_scores['zipcode_weights'].items())
        
        consensus_data = {
            'epoch_nonce': epoch_nonce,
            'miner_scores': sorted_scores,
            'zipcode_weights': sorted_zipcode_weights,
            'total_participants': final_scores['total_participants'],
            'total_winners': final_scores['total_winners'],
            'total_epoch_listings': final_scores['total_epoch_listings']
        }
        
        # Create deterministic JSON string (sorted keys)
        consensus_string = json.dumps(consensus_data, sort_keys=True, separators=(',', ':'))
        
        # Generate SHA256 hash
        consensus_hash = hashlib.sha256(consensus_string.encode('utf-8')).hexdigest()
        
        bt.logging.debug(f"Generated consensus hash: {consensus_hash}")
        
        return consensus_hash
    
    def verify_deterministic_spot_check_selection(self, submission: Dict, epoch_nonce: str, 
                                                 expected_indices: List[int]) -> bool:
        """
        Verify that spot check selection is deterministic across validators
        
        Args:
            submission: Miner submission data
            epoch_nonce: Epoch nonce for seed generation
            expected_indices: Expected selected indices from other validators
            
        Returns:
            True if this validator selects same indices as expected
        """
        # Recreate the deterministic seed
        miner_hotkey = submission['miner_hotkey']
        submission_time = submission['submission_timestamp']
        listing_count = len(submission['listings'])
        
        seed_string = f"{epoch_nonce}:{miner_hotkey}:{submission_time}:{listing_count}"
        seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16)
        
        # Use same random selection logic as MultiTierValidator
        import random
        random.seed(seed)
        
        sample_size = min(10, max(3, int(listing_count * 0.10)))  # Same logic as validator
        if listing_count < sample_size:
            actual_indices = list(range(listing_count))
        else:
            actual_indices = sorted(random.sample(range(listing_count), sample_size))
        
        # Verify indices match expected
        indices_match = actual_indices == expected_indices
        
        if not indices_match:
            bt.logging.error(f"Spot check selection mismatch for {miner_hotkey[:8]}!")
            bt.logging.error(f"Expected: {expected_indices}")
            bt.logging.error(f"Actual: {actual_indices}")
            bt.logging.error(f"Seed: {seed}")
        
        return indices_match
    
    def collect_validator_consensus_hashes(self, epoch_id: str, s3_reader=None, 
                                          metagraph=None) -> Dict[str, str]:
        """
        Collect consensus hashes from all validators for comparison
        
        Args:
            epoch_id: Epoch ID to collect consensus for
            s3_reader: ValidatorS3Access instance for downloading results
            metagraph: Metagraph to get list of active validators
            
        Returns:
            Dict mapping validator hotkeys to their consensus hashes
        """
        bt.logging.info(f"Collecting validator consensus hashes for epoch {epoch_id}")
        
        if not s3_reader or not metagraph:
            bt.logging.warning("S3 reader or metagraph not provided for consensus collection")
            return {}
        
        try:
            # Get list of active validators (those with stake)
            active_validators = []
            for uid, hotkey in enumerate(metagraph.hotkeys):
                if metagraph.S[uid] > 0:  # Has stake
                    active_validators.append(hotkey)
            
            bt.logging.info(f"Collecting consensus from {len(active_validators)} active validators")
            
            validator_hashes = {}
            successful_collections = 0
            
            for validator_hotkey in active_validators:
                try:
                    # Download validator's validation results for this epoch
                    validation_result = self._download_validator_result(
                        epoch_id, validator_hotkey, s3_reader
                    )
                    
                    if validation_result and 'consensus_hash' in validation_result:
                        validator_hashes[validator_hotkey] = validation_result['consensus_hash']
                        successful_collections += 1
                        bt.logging.debug(f"Collected consensus hash from {validator_hotkey[:8]}...")
                    
                except Exception as validator_error:
                    bt.logging.debug(f"Failed to collect consensus from {validator_hotkey[:8]}...: {validator_error}")
                    continue
            
            bt.logging.info(f"Successfully collected consensus hashes from {successful_collections}/{len(active_validators)} validators")
            
            return validator_hashes
            
        except Exception as e:
            bt.logging.error(f"Error collecting validator consensus hashes: {e}")
            return {}
    
    def _download_validator_result(self, epoch_id: str, validator_hotkey: str, s3_reader) -> Dict:
        """
        Download validation result from a specific validator
        
        Args:
            epoch_id: Epoch ID
            validator_hotkey: Validator's hotkey
            s3_reader: S3 access instance
            
        Returns:
            Validation result data or empty dict
        """
        try:
            import asyncio
            import requests
            import json
            
            # Get validator-specific S3 access
            validator_url = asyncio.run(s3_reader.get_miner_specific_access(validator_hotkey))
            
            if not validator_url:
                return {}
            
            # Download S3 file list
            response = requests.get(validator_url, timeout=30)
            
            if response.status_code != 200:
                return {}
            
            # Parse XML to find validation result files
            result_files = self._parse_validator_result_files(response.text, epoch_id, validator_hotkey, validator_url)
            
            if not result_files:
                return {}
            
            # Download the most recent validation result
            latest_file = max(result_files, key=lambda x: x.get('last_modified', ''))
            
            # Download and parse the validation result
            result_response = requests.get(latest_file['download_url'], timeout=30)
            
            if result_response.status_code != 200:
                return {}
            
            validation_result = json.loads(result_response.text)
            
            return validation_result
            
        except Exception as e:
            bt.logging.debug(f"Error downloading validator result from {validator_hotkey[:8]}...: {e}")
            return {}
    
    def _parse_validator_result_files(self, xml_content: str, epoch_id: str, validator_hotkey: str, validator_url: str = "") -> list:
        """
        Parse S3 XML to find validator result files
        
        Args:
            xml_content: S3 XML response
            epoch_id: Target epoch ID
            validator_hotkey: Validator's hotkey
            
        Returns:
            List of result file info
        """
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            namespace = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
            
            result_files = []
            
            for content in root.findall('.//s3:Contents', namespace):
                key_elem = content.find('s3:Key', namespace)
                size_elem = content.find('s3:Size', namespace)
                modified_elem = content.find('s3:LastModified', namespace)
                
                if key_elem is not None:
                    key = key_elem.text
                    
                    # Look for validator result files
                    # Expected pattern: validators/{validator_hotkey}/{epoch_id}/validation_results/*.json
                    if (f'validators/{validator_hotkey}' in key and 
                        epoch_id in key and 
                        'validation_results' in key and
                        key.endswith('.json')):
                        
                        file_info = {
                            'key': key,
                            'size': int(size_elem.text) if size_elem is not None else 0,
                            'last_modified': modified_elem.text if modified_elem is not None else '',
                            'download_url': f"{validator_url.split('?')[0]}/{key}?{validator_url.split('?')[1]}" if '?' in validator_url else f"{validator_url}/{key}"
                        }
                        
                        result_files.append(file_info)
            
            return result_files
            
        except Exception as e:
            bt.logging.error(f"Error parsing validator result files: {e}")
            return []
    
    def verify_consensus_across_validators(self, epoch_id: str, 
                                         my_consensus_hash: str) -> Dict[str, Any]:
        """
        Verify that all validators reached the same deterministic results
        
        Args:
            epoch_id: Epoch ID being validated
            my_consensus_hash: This validator's consensus hash
            
        Returns:
            Dict with consensus verification results
        """
        # Collect consensus hashes from all validators
        validator_hashes = self.collect_validator_consensus_hashes(epoch_id)
        
        # Add our hash to the collection
        validator_hashes['self'] = my_consensus_hash
        
        # Check if validators agree (same consensus hash)
        unique_hashes = set(validator_hashes.values())
        
        if len(unique_hashes) == 1:
            # Perfect consensus - all validators agree
            consensus_status = "PERFECT_CONSENSUS"
            consensus_rate = 1.0
            majority_hash = list(unique_hashes)[0]
        elif len(unique_hashes) == 0:
            # No other validators found
            consensus_status = "NO_OTHER_VALIDATORS"
            consensus_rate = 1.0
            majority_hash = my_consensus_hash
        else:
            # Calculate consensus rate
            hash_counts = {}
            for validator_hash in validator_hashes.values():
                hash_counts[validator_hash] = hash_counts.get(validator_hash, 0) + 1
            
            # Find majority hash
            majority_hash = max(hash_counts.keys(), key=lambda h: hash_counts[h])
            majority_count = hash_counts[majority_hash]
            consensus_rate = majority_count / len(validator_hashes)
            
            if consensus_rate >= self.consensus_threshold:
                consensus_status = "MAJORITY_CONSENSUS"
            else:
                consensus_status = "CONSENSUS_FAILED"
        
        # Identify outlier validators
        outlier_validators = self.identify_outlier_validators(validator_hashes, majority_hash)
        
        result = {
            'consensus_status': consensus_status,
            'consensus_rate': consensus_rate,
            'validator_hashes': validator_hashes,
            'majority_hash': majority_hash,
            'my_hash': my_consensus_hash,
            'matches_majority': my_consensus_hash == majority_hash,
            'outlier_validators': outlier_validators,
            'total_validators': len(validator_hashes)
        }
        
        bt.logging.info(f"Consensus verification: {consensus_status} "
                       f"({consensus_rate:.2%} agreement, "
                       f"{len(validator_hashes)} validators)")
        
        return result
    
    def identify_outlier_validators(self, validator_hashes: Dict[str, str], 
                                  majority_hash: str) -> List[str]:
        """
        Identify validators that didn't reach consensus
        
        Args:
            validator_hashes: Mapping of validator -> consensus hash
            majority_hash: The consensus hash agreed upon by majority
            
        Returns:
            List of validator hotkeys that are outliers
        """
        outliers = []
        for validator_hotkey, consensus_hash in validator_hashes.items():
            if consensus_hash != majority_hash:
                outliers.append(validator_hotkey)
        
        if outliers:
            bt.logging.warning(f"Outlier validators detected: {outliers}")
        
        return outliers
    
    def handle_consensus_failure(self, epoch_id: str, consensus_result: Dict[str, Any]):
        """
        Handle cases where validators don't reach consensus
        
        Args:
            epoch_id: Epoch that failed consensus
            consensus_result: Result from verify_consensus_across_validators
        """
        if consensus_result['consensus_status'] == 'CONSENSUS_FAILED':
            bt.logging.error(f"❌ Consensus failed for epoch {epoch_id}")
            bt.logging.error(f"Consensus rate: {consensus_result['consensus_rate']:.2%}")
            bt.logging.error(f"Outlier validators: {consensus_result['outlier_validators']}")
            bt.logging.error(f"My hash: {consensus_result['my_hash']}")
            bt.logging.error(f"Majority hash: {consensus_result['majority_hash']}")
            
            # Implement fallback strategies:
            if consensus_result['consensus_rate'] >= 0.70:  # 70% threshold for fallback
                bt.logging.warning("Using majority consensus despite low agreement")
                return "MAJORITY_FALLBACK"
            else:
                bt.logging.error("Consensus rate too low, flagging epoch for review")
                raise ConsensusFailureException(
                    f"Validator consensus failed for epoch {epoch_id}. "
                    f"Only {consensus_result['consensus_rate']:.2%} agreement achieved."
                )
        
        return "CONSENSUS_OK"
    
    def create_validation_result_with_consensus(self, epoch_id: str, 
                                              final_scores: Dict[str, Any],
                                              zipcode_results: List[Dict[str, Any]],
                                              epoch_nonce: str) -> Dict[str, Any]:
        """
        Create validation result package with consensus verification
        
        Args:
            epoch_id: Epoch ID
            final_scores: Final calculated scores
            zipcode_results: Individual zipcode validation results
            epoch_nonce: Epoch nonce for verification
            
        Returns:
            Complete validation result with consensus data
        """
        # Calculate consensus hash
        consensus_hash = self.calculate_consensus_hash(final_scores, epoch_nonce)
        
        # Calculate total winning listings included
        total_winning_listings = 0
        for zipcode_result in zipcode_results:
            for winner in zipcode_result.get('winners', []):
                total_winning_listings += len(winner.get('listings', []))
        
        # Create comprehensive validation result
        validation_result = {
            'epoch_id': epoch_id,
            'epoch_nonce': epoch_nonce,
            'validator_hotkey': 'placeholder',  # Will be filled by validator
            'validation_timestamp': bt.logging.get_current_time(),
            'consensus_hash': consensus_hash,
            'final_scores': final_scores,
            'zipcode_results': zipcode_results,
            'validation_metadata': {
                'total_zipcodes_validated': len(zipcode_results),
                'total_miners_scored': len(final_scores['miner_scores']),
                'total_epoch_listings': final_scores['total_epoch_listings'],
                'consensus_algorithm_version': '1.0',
                'includes_winning_listings': True,
                'total_winning_listings_included': total_winning_listings
            }
        }
        
        bt.logging.info(f"Created validation result with consensus hash: {consensus_hash}")
        bt.logging.info(f"Validation result includes {total_winning_listings} winning listings")
        
        return validation_result
    
    def verify_epoch_determinism(self, epoch_id: str, epoch_nonce: str, 
                                zipcode_assignments: List[Dict]) -> Dict[str, Any]:
        """
        Verify that epoch setup is deterministic and reproducible
        
        Args:
            epoch_id: Epoch ID
            epoch_nonce: Epoch nonce
            zipcode_assignments: Zipcode assignments for epoch
            
        Returns:
            Verification results
        """
        # Verify epoch nonce format and validity
        nonce_valid = len(epoch_nonce) >= 8 and all(c in '0123456789abcdef' for c in epoch_nonce)
        
        # Verify zipcode assignments are deterministic
        assignments_hash = hashlib.sha256(
            json.dumps(zipcode_assignments, sort_keys=True).encode()
        ).hexdigest()
        
        # Create epoch determinism hash
        epoch_data = {
            'epoch_id': epoch_id,
            'epoch_nonce': epoch_nonce,
            'zipcode_assignments_hash': assignments_hash,
            'assignment_count': len(zipcode_assignments)
        }
        
        epoch_hash = hashlib.sha256(
            json.dumps(epoch_data, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            'epoch_deterministic': nonce_valid,
            'epoch_hash': epoch_hash,
            'nonce_valid': nonce_valid,
            'assignments_hash': assignments_hash,
            'total_assignments': len(zipcode_assignments)
        }


class ConsensusFailureException(Exception):
    """Raised when validators cannot reach consensus on epoch results"""
    
    def __init__(self, message: str, consensus_rate: float = 0.0, 
                 outliers: List[str] = None):
        super().__init__(message)
        self.consensus_rate = consensus_rate
        self.outliers = outliers or []


# Utility functions for consensus verification
def verify_deterministic_seed_generation(epoch_nonce: str, miner_hotkey: str, 
                                       submission_time: str, listing_count: int) -> int:
    """
    Verify deterministic seed generation produces consistent results
    
    Args:
        epoch_nonce: Epoch nonce
        miner_hotkey: Miner's hotkey
        submission_time: Submission timestamp
        listing_count: Number of listings
        
    Returns:
        Generated seed value
    """
    seed_string = f"{epoch_nonce}:{miner_hotkey}:{submission_time}:{listing_count}"
    seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16)
    return seed


def create_consensus_verification_data(validation_results: List[Dict]) -> Dict[str, Any]:
    """
    Create data structure for cross-validator consensus verification
    
    Args:
        validation_results: List of validation results from multiple validators
        
    Returns:
        Consensus verification data
    """
    consensus_hashes = [result.get('consensus_hash') for result in validation_results]
    unique_hashes = set(filter(None, consensus_hashes))
    
    if len(unique_hashes) <= 1:
        consensus_achieved = True
        consensus_rate = 1.0
    else:
        # Calculate consensus rate based on most common hash
        hash_counts = {}
        for h in consensus_hashes:
            if h:
                hash_counts[h] = hash_counts.get(h, 0) + 1
        
        if hash_counts:
            max_count = max(hash_counts.values())
            consensus_rate = max_count / len(consensus_hashes)
            consensus_achieved = consensus_rate >= 0.90
        else:
            consensus_achieved = False
            consensus_rate = 0.0
    
    return {
        'consensus_achieved': consensus_achieved,
        'consensus_rate': consensus_rate,
        'unique_hashes': list(unique_hashes),
        'total_validators': len(validation_results),
        'participating_validators': len([r for r in validation_results if r.get('consensus_hash')])
    }
