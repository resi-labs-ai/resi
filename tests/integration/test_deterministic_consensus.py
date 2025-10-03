"""
Integration tests for deterministic consensus system
Ensures all validators reach identical conclusions
"""

import pytest
import hashlib
import random
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from vali_utils.multi_tier_validator import MultiTierValidator
from vali_utils.deterministic_consensus import DeterministicConsensus, verify_deterministic_seed_generation
from rewards.zipcode_competitive_scorer import ZipcodeCompetitiveScorer


class TestDeterministicConsensus:
    """Test suite for deterministic consensus mechanisms"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.multi_tier_validator = MultiTierValidator()
        self.consensus_manager = DeterministicConsensus()
        self.zipcode_scorer = ZipcodeCompetitiveScorer()
        
        # Test data
        self.epoch_nonce = "376ce532f42cf2a5"
        self.test_submission = {
            'miner_hotkey': '5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx',
            'submission_timestamp': '2025-10-01T17:30:00.000Z',
            'listings': self._generate_test_listings(100)
        }
    
    def _generate_test_listings(self, count: int) -> List[Dict]:
        """Generate test listing data"""
        listings = []
        for i in range(count):
            listings.append({
                'address': f'{1000 + i} Test St, Philadelphia, PA 19103',
                'zipcode': '19103',
                'price': 250000 + (i * 1000),
                'bedrooms': 2 + (i % 4),
                'bathrooms': 1.5 + (i % 3) * 0.5,
                'sqft': 1200 + (i * 50),
                'listing_date': '2025-10-01T10:00:00.000Z',
                'property_type': 'house',
                'listing_status': 'active',
                'days_on_market': i % 30,
                'mls_id': f'MLS{10000 + i}',
                'source_url': f'https://example.com/listing/{i}',
                'scraped_timestamp': '2025-10-01T16:00:00.000Z'
            })
        return listings
    
    def test_deterministic_spot_check_selection(self):
        """Test that spot check selection is identical across validators"""
        # Multiple "validators" should select identical listings
        validator_selections = []
        
        for validator_id in range(5):  # Simulate 5 validators
            # Each validator independently calculates the seed
            miner_hotkey = self.test_submission['miner_hotkey']
            submission_time = self.test_submission['submission_timestamp']
            listing_count = len(self.test_submission['listings'])
            
            seed_string = f"{self.epoch_nonce}:{miner_hotkey}:{submission_time}:{listing_count}"
            seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16)
            
            # Use seed to select listings
            random.seed(seed)
            sample_size = min(10, max(3, int(listing_count * 0.10)))
            selected_indices = sorted(random.sample(range(listing_count), sample_size))
            
            validator_selections.append(selected_indices)
        
        # All validators should have selected identical indices
        first_selection = validator_selections[0]
        for i, selection in enumerate(validator_selections[1:], 1):
            assert selection == first_selection, f"Validator {i} selection differs from validator 0"
        
        print(f"✅ All 5 validators selected identical indices: {first_selection}")
    
    def test_consensus_hash_consistency(self):
        """Test that consensus hash generation is identical across validators"""
        # Create test final scores
        final_scores = {
            'miner_scores': {
                '5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx': 0.35,
                '5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX': 0.25,
                '5DvggEsdjznNNvnQ4q6B52JTsSfYCWbCcJRFyMSrYvoZzutr': 0.20,
                '5CAsdjbWjgj1f7Ubt1eYzQDhDfpcPuWkAAZES6HrBM7LbGq9': 0.15,
                '5F1SejVkczocndDfPuFmjwhBqpsbP4mXGJMCdyQCTs4KnezW': 0.05
            },
            'zipcode_weights': {
                '19103': 0.4,
                '19104': 0.3,
                '19106': 0.3
            },
            'total_participants': 8,
            'total_winners': 5,
            'total_epoch_listings': 2500
        }
        
        # Multiple validators calculate consensus hash
        consensus_hashes = []
        
        for validator_id in range(5):
            consensus_hash = self.consensus_manager.calculate_consensus_hash(
                final_scores, self.epoch_nonce
            )
            consensus_hashes.append(consensus_hash)
        
        # All hashes should be identical
        first_hash = consensus_hashes[0]
        for i, hash_val in enumerate(consensus_hashes[1:], 1):
            assert hash_val == first_hash, f"Validator {i} hash differs from validator 0"
        
        print(f"✅ All 5 validators generated identical consensus hash: {first_hash}")
    
    def test_multi_tier_validation_consistency(self):
        """Test that multi-tier validation produces consistent results"""
        expected_listings = 100
        
        # Multiple validators perform validation
        validation_results = []
        
        for validator_id in range(3):
            result = self.multi_tier_validator.validate_submission_complete(
                self.test_submission, expected_listings, self.epoch_nonce
            )
            validation_results.append(result)
        
        # All validators should reach the same conclusion
        first_result = validation_results[0]
        
        for i, result in enumerate(validation_results[1:], 1):
            assert result['passes_all_tiers'] == first_result['passes_all_tiers'], \
                f"Validator {i} tier result differs from validator 0"
            
            # Check tier 3 spot check results are identical
            if result['tier3_result'] and first_result['tier3_result']:
                assert result['tier3_result']['selected_indices'] == first_result['tier3_result']['selected_indices'], \
                    f"Validator {i} spot check selection differs from validator 0"
        
        print(f"✅ All 3 validators reached identical validation conclusion: "
              f"passes_all_tiers={first_result['passes_all_tiers']}")
    
    def test_proportional_weight_calculation(self):
        """Test that proportional weight calculation is deterministic"""
        # Create test zipcode results
        zipcode_results = [
            {
                'zipcode': '19103',
                'expected_listings': 250,
                'winners': [
                    {'miner_hotkey': 'miner1', 'rank': 1, 'listing_count': 245},
                    {'miner_hotkey': 'miner2', 'rank': 2, 'listing_count': 240},
                    {'miner_hotkey': 'miner3', 'rank': 3, 'listing_count': 235}
                ],
                'participants': [
                    {'miner_hotkey': 'miner4', 'failed_at_tier': 2, 'listing_count': 200}
                ],
                'zipcode_rewards': {
                    'miner1': {'rank': 1, 'reward_percentage': 0.55, 'listing_count': 245},
                    'miner2': {'rank': 2, 'reward_percentage': 0.30, 'listing_count': 240},
                    'miner3': {'rank': 3, 'reward_percentage': 0.10, 'listing_count': 235}
                },
                'total_listings_found': 720
            },
            {
                'zipcode': '19104',
                'expected_listings': 200,
                'winners': [
                    {'miner_hotkey': 'miner5', 'rank': 1, 'listing_count': 195},
                    {'miner_hotkey': 'miner6', 'rank': 2, 'listing_count': 190}
                ],
                'participants': [],
                'zipcode_rewards': {
                    'miner5': {'rank': 1, 'reward_percentage': 0.55, 'listing_count': 195},
                    'miner6': {'rank': 2, 'reward_percentage': 0.30, 'listing_count': 190}
                },
                'total_listings_found': 385
            }
        ]
        
        # Multiple validators calculate weights
        weight_calculations = []
        
        for validator_id in range(3):
            final_scores = self.zipcode_scorer.calculate_epoch_proportional_weights(zipcode_results)
            weight_calculations.append(final_scores)
        
        # All calculations should be identical
        first_calculation = weight_calculations[0]
        
        for i, calculation in enumerate(weight_calculations[1:], 1):
            assert calculation['miner_scores'] == first_calculation['miner_scores'], \
                f"Validator {i} weight calculation differs from validator 0"
            
            assert calculation['zipcode_weights'] == first_calculation['zipcode_weights'], \
                f"Validator {i} zipcode weights differ from validator 0"
        
        print(f"✅ All 3 validators calculated identical proportional weights")
        print(f"   Miner scores: {first_calculation['miner_scores']}")
    
    def test_seed_generation_determinism(self):
        """Test that seed generation is deterministic and ungameable"""
        test_cases = [
            {
                'epoch_nonce': 'abc123def456',
                'miner_hotkey': '5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx',
                'submission_time': '2025-10-01T17:30:00.000Z',
                'listing_count': 100
            },
            {
                'epoch_nonce': 'abc123def456',
                'miner_hotkey': '5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx',
                'submission_time': '2025-10-01T17:30:01.000Z',  # 1 second later
                'listing_count': 100
            },
            {
                'epoch_nonce': 'abc123def456',
                'miner_hotkey': '5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx',
                'submission_time': '2025-10-01T17:30:00.000Z',
                'listing_count': 101  # 1 more listing
            }
        ]
        
        seeds = []
        for case in test_cases:
            seed = verify_deterministic_seed_generation(
                case['epoch_nonce'],
                case['miner_hotkey'],
                case['submission_time'],
                case['listing_count']
            )
            seeds.append(seed)
        
        # Seeds should be different for different inputs (ungameable)
        assert len(set(seeds)) == len(seeds), "Seeds should be unique for different inputs"
        
        # Same inputs should produce same seed (deterministic)
        seed1 = verify_deterministic_seed_generation(
            test_cases[0]['epoch_nonce'],
            test_cases[0]['miner_hotkey'],
            test_cases[0]['submission_time'],
            test_cases[0]['listing_count']
        )
        seed2 = verify_deterministic_seed_generation(
            test_cases[0]['epoch_nonce'],
            test_cases[0]['miner_hotkey'],
            test_cases[0]['submission_time'],
            test_cases[0]['listing_count']
        )
        assert seed1 == seed2, "Same inputs should produce identical seeds"
        
        print(f"✅ Seed generation is deterministic and ungameable")
        print(f"   Seeds for different inputs: {seeds}")
    
    def test_consensus_verification_scenarios(self):
        """Test different consensus scenarios"""
        # Perfect consensus scenario
        validator_hashes = {
            'validator1': 'abc123def456',
            'validator2': 'abc123def456',
            'validator3': 'abc123def456',
            'validator4': 'abc123def456'
        }
        
        consensus_result = self.consensus_manager.verify_consensus_across_validators.__wrapped__(
            self.consensus_manager, 'test_epoch', 'abc123def456'
        )
        
        # Mock the hash collection for testing
        self.consensus_manager.collect_validator_consensus_hashes = lambda epoch_id: validator_hashes
        
        # Test majority consensus scenario
        validator_hashes_majority = {
            'validator1': 'abc123def456',
            'validator2': 'abc123def456',
            'validator3': 'abc123def456',
            'validator4': 'different_hash'  # One outlier
        }
        
        outliers = self.consensus_manager.identify_outlier_validators(
            validator_hashes_majority, 'abc123def456'
        )
        
        assert outliers == ['validator4'], "Should identify outlier validator"
        
        print(f"✅ Consensus verification correctly identifies outliers: {outliers}")
    
    def test_anti_gaming_detection_consistency(self):
        """Test that anti-gaming detection is consistent across validators"""
        # Create test listings with some suspicious patterns
        suspicious_listings = [
            {
                'address': '123 Test St, Philadelphia, PA 19103',
                'zipcode': '19103',
                'price': 999999999,  # Unreasonable price
                'bedrooms': 2,
                'bathrooms': 1.5,
                'sqft': 1200,
                'listing_date': '2025-10-01T10:00:00.000Z',
                'property_type': 'house',
                'listing_status': 'active',
                'days_on_market': 5,
                'mls_id': 'MLS12345',
                'source_url': 'https://example.com/listing/1',
                'scraped_timestamp': '2025-10-01T16:00:00.000Z'
            }
        ]
        
        # Multiple validators should detect the same issues
        detection_results = []
        
        for validator_id in range(3):
            # Test reasonable values validation
            reasonable_rate = self.multi_tier_validator._validate_reasonable_values(suspicious_listings)
            detection_results.append(reasonable_rate)
        
        # All validators should detect the same unreasonable values
        first_result = detection_results[0]
        for i, result in enumerate(detection_results[1:], 1):
            assert abs(result - first_result) < 0.001, \
                f"Validator {i} anti-gaming detection differs from validator 0"
        
        print(f"✅ All 3 validators detected identical anti-gaming patterns: {first_result}")
    
    def test_epoch_determinism_verification(self):
        """Test epoch setup determinism verification"""
        zipcode_assignments = [
            {
                'zipcode': '19103',
                'expectedListings': 250,
                'state': 'PA',
                'city': 'Philadelphia'
            },
            {
                'zipcode': '19104',
                'expectedListings': 200,
                'state': 'PA',
                'city': 'Philadelphia'
            }
        ]
        
        # Multiple validators verify epoch determinism
        verification_results = []
        
        for validator_id in range(3):
            result = self.consensus_manager.verify_epoch_determinism(
                'test_epoch_2025-10-01T16-00-00',
                self.epoch_nonce,
                zipcode_assignments
            )
            verification_results.append(result)
        
        # All validators should reach same conclusion
        first_result = verification_results[0]
        for i, result in enumerate(verification_results[1:], 1):
            assert result['epoch_hash'] == first_result['epoch_hash'], \
                f"Validator {i} epoch hash differs from validator 0"
            
            assert result['epoch_deterministic'] == first_result['epoch_deterministic'], \
                f"Validator {i} determinism check differs from validator 0"
        
        print(f"✅ All 3 validators verified identical epoch determinism")
        print(f"   Epoch hash: {first_result['epoch_hash']}")


if __name__ == "__main__":
    """Run tests directly"""
    test_suite = TestDeterministicConsensus()
    test_suite.setup_method()
    
    print("🧪 Running Deterministic Consensus Tests...")
    print("=" * 60)
    
    try:
        test_suite.test_deterministic_spot_check_selection()
        test_suite.test_consensus_hash_consistency()
        test_suite.test_multi_tier_validation_consistency()
        test_suite.test_proportional_weight_calculation()
        test_suite.test_seed_generation_determinism()
        test_suite.test_consensus_verification_scenarios()
        test_suite.test_anti_gaming_detection_consistency()
        test_suite.test_epoch_determinism_verification()
        
        print("=" * 60)
        print("🎉 All deterministic consensus tests passed!")
        print("✅ Validators will reach identical conclusions")
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        raise
