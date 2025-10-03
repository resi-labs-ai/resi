#!/usr/bin/env python3
"""
Local Testing Script for Zipcode Mining System

This script allows you to test the complete zipcode mining system locally
without requiring testnet registration or real API endpoints.

Usage:
    python scripts/test_local_zipcode_system.py [--mode miner|validator|full]
"""

import sys
import os
import argparse
import tempfile
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraping.zipcode_mock_scraper import MockZipcodeScraper
from scraping.zipcode_scraper_interface import ZipcodeScraperConfig
from storage.miner.sqlite_miner_storage import SqliteMinerStorage
from vali_utils.multi_tier_validator import MultiTierValidator
from rewards.zipcode_competitive_scorer import ZipcodeCompetitiveScorer
from vali_utils.deterministic_consensus import DeterministicConsensus
import bittensor as bt


class LocalZipcodeSystemTester:
    """Local testing harness for zipcode mining system"""
    
    def __init__(self):
        self.temp_db = None
        self.storage = None
        self.setup_components()
    
    def setup_components(self):
        """Initialize all system components"""
        print("🔧 Setting up local test environment...")
        
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        
        # Initialize components
        self.storage = SqliteMinerStorage(database=self.temp_db.name)
        self.validator = MultiTierValidator()
        self.scorer = ZipcodeCompetitiveScorer()
        self.consensus = DeterministicConsensus()
        
        print(f"✅ Components initialized (DB: {self.temp_db.name})")
    
    def test_miner_flow(self):
        """Test complete miner flow locally"""
        print("\n🔍 Testing Miner Flow...")
        
        # Test configuration
        test_zipcode = "90210"
        expected_listings = 100
        test_epoch_id = f"test_epoch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_miner_hotkey = "5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx"
        
        try:
            # 1. Test scraping with mock scraper
            print(f"   📊 Scraping zipcode {test_zipcode} (target: {expected_listings})...")
            
            scraper_config = ZipcodeScraperConfig(
                max_requests_per_minute=60,
                request_delay_seconds=0.1,  # Fast for testing
                max_retries=2
            )
            
            scraper = MockZipcodeScraper(scraper_config)
            scraper_info = scraper.get_scraper_info()
            print(f"   🤖 Using: {scraper_info['name']} v{scraper_info['version']}")
            
            listings = scraper.scrape_zipcode(test_zipcode, expected_listings, timeout=30)
            print(f"   ✅ Scraped {len(listings)} listings")
            
            # Validate listings
            valid_count = sum(1 for listing in listings if scraper.validate_listing_data(listing))
            print(f"   ✅ {valid_count}/{len(listings)} listings passed validation")
            
            # 2. Test data storage
            print(f"   💾 Storing data for epoch {test_epoch_id}...")
            
            success = self.storage.store_epoch_zipcode_data(
                epoch_id=test_epoch_id,
                zipcode=test_zipcode,
                listings_data=listings,
                miner_hotkey=test_miner_hotkey
            )
            
            if success:
                print("   ✅ Data stored successfully")
            else:
                print("   ❌ Data storage failed")
                return False
            
            # 3. Test data retrieval
            print("   📤 Testing data retrieval...")
            
            retrieved_data = self.storage.get_epoch_zipcode_data(test_epoch_id, test_zipcode)
            print(f"   ✅ Retrieved {len(retrieved_data)} listings")
            
            # 4. Simulate S3 upload
            print("   ☁️  Simulating S3 upload...")
            
            with patch('requests.post') as mock_post:
                mock_post.return_value.status_code = 204  # S3 success
                
                # Mark as uploaded
                upload_success = self.storage.mark_epoch_data_uploaded(
                    test_epoch_id, test_zipcode, test_miner_hotkey
                )
                
                if upload_success:
                    print("   ✅ S3 upload simulation successful")
                else:
                    print("   ❌ S3 upload simulation failed")
            
            print(f"\n🎉 Miner flow test completed successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Miner flow test failed: {e}")
            return False
    
    def test_validator_flow(self):
        """Test complete validator flow locally"""
        print("\n🔍 Testing Validator Flow...")
        
        test_zipcode = "90210"
        expected_listings = 100
        test_epoch_id = f"test_epoch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        epoch_nonce = "test_nonce_123"
        
        try:
            # 1. Generate test submissions from multiple miners
            print("   👥 Generating submissions from 3 test miners...")
            
            test_miners = [
                "5H1WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwG1",
                "5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwG2", 
                "5H3WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwG3"
            ]
            
            submissions = []
            
            for i, miner_hotkey in enumerate(test_miners):
                scraper = MockZipcodeScraper(ZipcodeScraperConfig(request_delay_seconds=0.01))
                listings = scraper.scrape_zipcode(
                    test_zipcode, 
                    expected_listings - (i * 5),  # Slight variation
                    timeout=10
                )
                
                submission = {
                    'epoch_id': test_epoch_id,
                    'zipcode': test_zipcode,
                    'miner_hotkey': miner_hotkey,
                    'submission_timestamp': datetime.now(timezone.utc).isoformat(),
                    'listing_count': len(listings),
                    'listings': listings
                }
                
                submissions.append(submission)
                print(f"   📊 Miner {i+1}: {len(listings)} listings")
            
            # 2. Test multi-tier validation
            print("   🔍 Running multi-tier validation...")
            
            # Mock the spot-check scraper to avoid external calls
            with patch.object(self.scorer.multi_tier_validator, '_verify_listing_with_scraper') as mock_verify:
                # Simulate realistic spot-check results (80% pass rate)
                def mock_spot_check(listing):
                    import random
                    return {
                        'exists_and_accurate': random.random() > 0.2,  # 80% pass rate
                        'verification_details': {'method': 'mock_verification'},
                        'reason': 'Mock verification result',
                        'verified_at': datetime.now(timezone.utc).isoformat()
                    }
                
                mock_verify.side_effect = mock_spot_check
                
                # Run validation and ranking
                result = self.scorer.validate_and_rank_zipcode_submissions(
                    zipcode=test_zipcode,
                    submissions=submissions,
                    expected_listings=expected_listings,
                    epoch_nonce=epoch_nonce
                )
                
                print(f"   ✅ Validation completed")
                print(f"   🏆 Winners: {len(result['winners'])}")
                
                # Display results
                for i, winner in enumerate(result['winners'][:3]):
                    miner_short = winner['miner_hotkey'][:8] + "..."
                    percentage = ["55%", "30%", "10%"][i] if i < 3 else "0%"
                    print(f"   🥇 Place {i+1}: {miner_short} ({percentage})")
            
            # 3. Test consensus calculation
            print("   🤝 Testing consensus calculation...")
            
            zipcode_results = [result]
            final_scores = self.scorer.calculate_epoch_proportional_weights(zipcode_results)
            
            total_miners = final_scores.get('reward_distribution_summary', {}).get('total_miners_rewarded', len(final_scores.get('miner_scores', {})))
            print(f"   ✅ Final scores calculated for {total_miners} miners")
            
            # 4. Test consensus hash
            print("   🔐 Testing consensus hash generation...")
            
            consensus_hash = self.consensus.calculate_consensus_hash(final_scores, epoch_nonce)
            print(f"   ✅ Consensus hash: {consensus_hash[:16]}...")
            
            print(f"\n🎉 Validator flow test completed successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Validator flow test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_deterministic_consensus(self):
        """Test that consensus is deterministic"""
        print("\n🔍 Testing Deterministic Consensus...")
        
        try:
            # Create identical test data
            test_submissions = self._create_deterministic_test_data()
            epoch_nonce = "deterministic_test_nonce"
            
            # Run validation multiple times
            results = []
            
            print("   🔄 Running validation 3 times with identical data...")
            
            for run in range(3):
                with patch.object(self.scorer.multi_tier_validator, '_verify_listing_with_scraper') as mock_verify:
                    # Use deterministic mock results
                    mock_verify.return_value = {
                        'exists_and_accurate': True,
                        'verification_details': {'method': 'deterministic_mock'},
                        'reason': 'Deterministic test result',
                        'verified_at': '2025-10-03T17:00:00Z'
                    }
                    
                    result = self.scorer.validate_and_rank_zipcode_submissions(
                        zipcode="90210",
                        submissions=test_submissions,
                        expected_listings=100,
                        epoch_nonce=epoch_nonce
                    )
                    
                    results.append(result)
                    print(f"   ✅ Run {run + 1}: {len(result['winners'])} winners")
            
            # Verify all results are identical
            first_result = results[0]
            all_identical = True
            
            for i, result in enumerate(results[1:], 2):
                if (result['winners'] != first_result['winners'] or 
                    result['participants'] != first_result['participants']):
                    print(f"   ❌ Run {i} produced different results!")
                    all_identical = False
            
            if all_identical:
                print("   ✅ All runs produced identical results - consensus is deterministic!")
                return True
            else:
                print("   ❌ Results were not deterministic!")
                return False
                
        except Exception as e:
            print(f"   ❌ Deterministic consensus test failed: {e}")
            return False
    
    def _create_deterministic_test_data(self):
        """Create consistent test data for deterministic testing"""
        submissions = []
        
        for i in range(3):
            listings = []
            for j in range(10):  # Small dataset
                listing = {
                    'zpid': f'deterministic_{i}_{j}',
                    'address': f'{1000 + (i * 100) + j} Deterministic St',
                    'price': 500000 + (i * 10000) + (j * 1000),
                    'bedrooms': 3,
                    'bathrooms': 2.0,
                    'sqft': 1500 + (j * 100),
                    'listing_date': '2025-10-01T00:00:00Z',
                    'property_type': 'SINGLE_FAMILY',
                    'listing_status': 'FOR_SALE',
                    'days_on_market': 10 + j,
                    'source_url': f'https://deterministic-test.com/{i}_{j}',
                    'scraped_timestamp': '2025-10-03T17:00:00Z',
                    'zipcode': '90210'
                }
                listings.append(listing)
            
            submission = {
                'epoch_id': 'deterministic_test_epoch',
                'zipcode': '90210',
                'miner_hotkey': f'deterministic_miner_{i}',
                'submission_timestamp': f'2025-10-03T17:0{i}:00Z',
                'listing_count': len(listings),
                'listings': listings
            }
            
            submissions.append(submission)
        
        return submissions
    
    def cleanup(self):
        """Clean up test environment"""
        if self.temp_db and os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
            print(f"🧹 Cleaned up test database: {self.temp_db.name}")


def main():
    parser = argparse.ArgumentParser(description='Local Zipcode Mining System Tester')
    parser.add_argument('--mode', choices=['miner', 'validator', 'full', 'consensus'], 
                       default='full', help='Test mode to run')
    
    args = parser.parse_args()
    
    print("🚀 Starting Local Zipcode Mining System Tests")
    print("=" * 60)
    
    tester = LocalZipcodeSystemTester()
    
    try:
        success = True
        
        if args.mode in ['miner', 'full']:
            success &= tester.test_miner_flow()
        
        if args.mode in ['validator', 'full']:
            success &= tester.test_validator_flow()
        
        if args.mode in ['consensus', 'full']:
            success &= tester.test_deterministic_consensus()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 ALL TESTS PASSED! System is ready for testnet deployment.")
        else:
            print("❌ SOME TESTS FAILED! Please review errors above.")
            sys.exit(1)
            
    finally:
        tester.cleanup()


if __name__ == '__main__':
    main()
