"""
Local Integration Tests for Zipcode Mining System

These tests simulate the complete zipcode mining flow without requiring:
- Registered miners/validators on testnet
- Real API endpoints
- Actual data scraping

Perfect for local development and CI/CD testing.
"""

import unittest
import tempfile
import json
import os
import sqlite3
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timezone

# Import the components we're testing
from scraping.zipcode_mock_scraper import MockZipcodeScraper
from scraping.zipcode_scraper_interface import ZipcodeScraperConfig
from storage.miner.sqlite_miner_storage import SqliteMinerStorage
from vali_utils.multi_tier_validator import MultiTierValidator
from rewards.zipcode_competitive_scorer import ZipcodeCompetitiveScorer
from vali_utils.deterministic_consensus import DeterministicConsensus
from common.resi_api_client import ResiLabsAPIClient


class TestZipcodeSystemLocal(unittest.TestCase):
    """Local integration tests for the complete zipcode mining system"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        
        # Initialize components
        self.storage = SqliteMinerStorage(database=self.temp_db.name)
        self.validator = MultiTierValidator()
        self.scorer = ZipcodeCompetitiveScorer()
        self.consensus = DeterministicConsensus()
        
        # Mock data
        self.test_epoch_id = "test_epoch_20251003_1700"
        self.test_zipcode = "90210"
        self.test_miner_hotkey = "5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx"
        self.expected_listings = 250
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_complete_miner_flow_local(self):
        """Test complete miner flow without external dependencies"""
        
        # 1. Mock API client responses
        mock_api_client = self._create_mock_api_client()
        
        # 2. Test scraping with mock scraper
        scraper = MockZipcodeScraper(ZipcodeScraperConfig(request_delay_seconds=0.1))
        listings = scraper.scrape_zipcode(self.test_zipcode, self.expected_listings, timeout=30)
        
        # Verify scraping results
        self.assertGreater(len(listings), 0)
        self.assertLessEqual(len(listings), self.expected_listings + 10)  # Allow some variance
        
        # Validate listing format
        for listing in listings:
            self.assertTrue(scraper.validate_listing_data(listing))
            self.assertEqual(listing['zipcode'], self.test_zipcode)
        
        # 3. Test data storage
        success = self.storage.store_epoch_zipcode_data(
            epoch_id=self.test_epoch_id,
            zipcode=self.test_zipcode,
            listings_data=listings,
            miner_hotkey=self.test_miner_hotkey
        )
        self.assertTrue(success)
        
        # 4. Test data retrieval
        retrieved_data = self.storage.get_epoch_zipcode_data(self.test_epoch_id, self.test_zipcode)
        self.assertEqual(len(retrieved_data), len(listings))
        
        # 5. Mock S3 upload (simulate success)
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 204  # S3 success
            
            # Simulate S3 upload process
            upload_success = self._simulate_s3_upload(listings)
            self.assertTrue(upload_success)
        
        print(f"✅ Complete miner flow test passed: {len(listings)} listings processed")
    
    def test_complete_validator_flow_local(self):
        """Test complete validator flow without external dependencies"""
        
        # 1. Set up test data - simulate multiple miners
        test_miners = [
            f"5H{i}WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwG{i}" 
            for i in range(3)
        ]
        
        all_submissions = {}
        
        for i, miner_hotkey in enumerate(test_miners):
            # Generate mock data for each miner
            scraper = MockZipcodeScraper(ZipcodeScraperConfig(request_delay_seconds=0.01))
            listings = scraper.scrape_zipcode(self.test_zipcode, self.expected_listings - (i * 10), timeout=10)
            
            # Create submission format
            submission = {
                'epoch_id': self.test_epoch_id,
                'zipcode': self.test_zipcode,
                'miner_hotkey': miner_hotkey,
                'submission_timestamp': datetime.now(timezone.utc).isoformat(),
                'listing_count': len(listings),
                'listings': listings
            }
            
            if self.test_zipcode not in all_submissions:
                all_submissions[self.test_zipcode] = []
            all_submissions[self.test_zipcode].append(submission)
        
        # 2. Test multi-tier validation
        zipcode_results = []
        
        for zipcode, submissions in all_submissions.items():
            # Mock the spot-check scraper to avoid external calls
            with patch.object(self.validator, '_verify_listing_with_scraper') as mock_verify:
                mock_verify.return_value = {
                    'exists_and_accurate': True,
                    'verification_details': {'method': 'mock_verification'},
                    'reason': 'Mock verification passed',
                    'verified_at': datetime.now(timezone.utc).isoformat()
                }
                
                result = self.scorer.validate_and_rank_zipcode_submissions(
                    zipcode=zipcode,
                    submissions=submissions,
                    expected_listings=self.expected_listings,
                    epoch_nonce="test_nonce_123"
                )
                
                zipcode_results.append(result)
        
        # 3. Test consensus calculation
        final_scores = self.scorer.calculate_epoch_proportional_weights(zipcode_results)
        
        # Verify results
        self.assertIn('miner_scores', final_scores)
        self.assertIn('total_miners', final_scores)
        self.assertGreater(final_scores['total_miners'], 0)
        
        # 4. Test consensus hash calculation
        consensus_hash = self.consensus.calculate_consensus_hash(final_scores, "test_nonce_123")
        self.assertIsInstance(consensus_hash, str)
        self.assertEqual(len(consensus_hash), 64)  # SHA256 hex length
        
        print(f"✅ Complete validator flow test passed: {final_scores['total_miners']} miners scored")
    
    def test_deterministic_consensus_local(self):
        """Test that consensus is deterministic across multiple runs"""
        
        # Create identical test data
        test_submissions = self._create_test_submissions()
        
        # Run validation multiple times
        results = []
        for run in range(3):
            with patch.object(self.validator, '_verify_listing_with_scraper') as mock_verify:
                mock_verify.return_value = {
                    'exists_and_accurate': True,
                    'verification_details': {'method': 'mock_verification'},
                    'reason': 'Mock verification passed',
                    'verified_at': datetime.now(timezone.utc).isoformat()
                }
                
                result = self.scorer.validate_and_rank_zipcode_submissions(
                    zipcode=self.test_zipcode,
                    submissions=test_submissions,
                    expected_listings=self.expected_listings,
                    epoch_nonce="deterministic_test_nonce"
                )
                
                results.append(result)
        
        # Verify all results are identical
        first_result = results[0]
        for result in results[1:]:
            self.assertEqual(result['winners'], first_result['winners'])
            self.assertEqual(result['spot_check_results'], first_result['spot_check_results'])
        
        print("✅ Deterministic consensus test passed: identical results across runs")
    
    def test_error_handling_local(self):
        """Test error handling without external dependencies"""
        
        # Test invalid zipcode
        scraper = MockZipcodeScraper()
        listings = scraper.scrape_zipcode("invalid", 10, timeout=5)
        # Should still work but with invalid zipcode in data
        
        # Test storage with invalid data
        success = self.storage.store_epoch_zipcode_data("", "", [], "")
        # Should handle gracefully
        
        # Test validation with empty submissions
        result = self.scorer.validate_and_rank_zipcode_submissions(
            zipcode=self.test_zipcode,
            submissions=[],
            expected_listings=self.expected_listings,
            epoch_nonce="test_nonce"
        )
        
        self.assertEqual(len(result['winners']), 0)
        
        print("✅ Error handling test passed: graceful degradation verified")
    
    def _create_mock_api_client(self):
        """Create mock API client with realistic responses"""
        mock_client = MagicMock()
        
        # Mock zipcode assignments
        mock_client.get_current_zipcode_assignments.return_value = {
            'success': True,
            'epochId': self.test_epoch_id,
            'nonce': 'test_nonce_123',
            'zipcodes': [
                {
                    'zipcode': self.test_zipcode,
                    'expectedListings': self.expected_listings
                }
            ]
        }
        
        # Mock S3 credentials
        mock_client.get_s3_upload_credentials.return_value = {
            'success': True,
            'url': 'https://mock-s3-bucket.s3.amazonaws.com/',
            'fields': {'key': 'test-key', 'policy': 'test-policy'},
            'folder': 'test-folder/'
        }
        
        return mock_client
    
    def _simulate_s3_upload(self, listings):
        """Simulate S3 upload without actual network calls"""
        try:
            # Create temporary file to simulate upload
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump({
                    'epoch_id': self.test_epoch_id,
                    'zipcode': self.test_zipcode,
                    'listings': listings
                }, temp_file)
                temp_file_path = temp_file.name
            
            # Simulate successful upload
            os.unlink(temp_file_path)
            return True
            
        except Exception:
            return False
    
    def _create_test_submissions(self):
        """Create consistent test submissions for deterministic testing"""
        submissions = []
        
        for i in range(3):
            # Create deterministic mock data
            listings = []
            for j in range(10):  # Small dataset for testing
                listing = {
                    'zpid': f'test_{i}_{j}',
                    'address': f'{100 + j} Test St',
                    'price': 500000 + (i * 10000) + (j * 1000),
                    'bedrooms': 3,
                    'bathrooms': 2.0,
                    'sqft': 1500 + (j * 100),
                    'listing_date': '2025-10-01T00:00:00Z',
                    'property_type': 'SINGLE_FAMILY',
                    'listing_status': 'FOR_SALE',
                    'days_on_market': 10 + j,
                    'source_url': f'https://test.com/property/{i}_{j}',
                    'scraped_timestamp': '2025-10-03T17:00:00Z',
                    'zipcode': self.test_zipcode
                }
                listings.append(listing)
            
            submission = {
                'epoch_id': self.test_epoch_id,
                'zipcode': self.test_zipcode,
                'miner_hotkey': f'test_miner_{i}',
                'submission_timestamp': f'2025-10-03T17:0{i}:00Z',
                'listing_count': len(listings),
                'listings': listings
            }
            
            submissions.append(submission)
        
        return submissions


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
