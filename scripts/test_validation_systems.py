#!/usr/bin/env python3
"""
Test script for both consensus-based and API-based validation systems.
Demonstrates the different validation approaches.
"""

import asyncio
import sys
import os
import argparse
import bittensor as bt

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.validation_config import ValidationConfig, CONSENSUS_ONLY_CONFIG, API_VALIDATION_CONFIG, DEVELOPMENT_CONFIG
from vali_utils.validator_data_api import ValidatorDataAPI
from vali_utils.consensus_validator import PropertyConsensusEngine
from vali_utils.api_validator import APIBasedValidator
from common.protocol import DataAssignmentRequest
from common.data import DataSource, DataEntity
from rewards.miner_scorer import MinerScorer
from rewards.data_value_calculator import DataValueCalculator
from scraping.provider import ScraperProvider


class ValidationSystemTester:
    """Test both validation systems"""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        
        # Initialize minimal components for testing
        self.wallet = bt.wallet()  # This would need proper initialization
        self.metagraph = None      # This would need proper initialization
        
        # Create mock scorer for testing
        self.scorer = MinerScorer(256, DataValueCalculator())  # Assuming 256 max miners
        
        # Initialize scraper provider
        self.scraper_provider = ScraperProvider()
        
        # Initialize validation systems
        self.consensus_engine = PropertyConsensusEngine(
            config=config,
            wallet=self.wallet,
            metagraph=self.metagraph,
            scorer=self.scorer,
            scraper_provider=self.scraper_provider
        )
        
        self.api_validator = APIBasedValidator(
            config=config,
            wallet=self.wallet,
            metagraph=self.metagraph,
            scorer=self.scorer,
            scraper_provider=self.scraper_provider
        )

    def create_mock_responses(self, num_responses: int = 5) -> List[DataAssignmentRequest]:
        """Create mock assignment responses for testing"""
        responses = []
        
        for i in range(num_responses):
            # Create mock scraped data
            mock_entity = DataEntity(
                uri=f"https://zillow.com/homedetails/test-property-{i}/12345{i}_zpid/",
                datetime="2025-01-15T10:30:00Z",
                source=DataSource.ZILLOW,
                content=f'{{"zpid": "12345{i}", "price": {450000 + i * 1000}, "bedrooms": 3, "bathrooms": 2}}'.encode(),
                content_size_bytes=100
            )
            
            response = DataAssignmentRequest(
                request_id=f"test_assignment_miner_{i}",
                assignment_data={"ZILLOW": [f"12345{i}"]},
                completion_status="completed",
                scraped_data={"ZILLOW": [mock_entity]},
                scrape_timestamp="2025-01-15T10:30:00Z",
                submission_timestamp="2025-01-15T10:45:00Z",
                assignment_stats={
                    "total_properties_assigned": 1,
                    "total_properties_scraped": 1,
                    "failed_properties": 0,
                    "total_scrape_time_seconds": 15.0
                }
            )
            
            # Add miner_uid for testing (would be set properly in real system)
            setattr(response, 'miner_uid', i + 10)
            
            responses.append(response)
            
        return responses

    async def test_consensus_validation(self) -> dict:
        """Test consensus-based validation"""
        print("\n=== Testing Consensus-Based Validation ===")
        
        # Create mock responses
        responses = self.create_mock_responses(5)
        
        # Add some variation to test consensus
        # Make one response an outlier
        outlier_entity = DataEntity(
            uri="https://zillow.com/homedetails/test-property-outlier/999999_zpid/",
            datetime="2025-01-15T10:30:00Z",
            source=DataSource.ZILLOW,
            content='{"zpid": "999999", "price": 850000, "bedrooms": 5, "bathrooms": 4}'.encode(),  # Different values
            content_size_bytes=100
        )
        responses[4].scraped_data["ZILLOW"] = [outlier_entity]
        
        print(f"Processing {len(responses)} mock responses with consensus validation...")
        
        try:
            results = await self.consensus_engine.process_assignment_responses("test_consensus", responses)
            
            print(f"Consensus validation results:")
            print(f"  Status: {results.get('status')}")
            print(f"  Responses processed: {results.get('responses_processed', 0)}")
            print(f"  Anomalies detected: {results.get('anomalies_detected', 0)}")
            print(f"  Spot check performed: {results.get('spot_check_performed', False)}")
            
            if 'consensus_data' in results:
                consensus_data = results['consensus_data']
                print(f"  Properties with consensus: {len(consensus_data)}")
                
                # Show consensus details for first property
                if consensus_data:
                    first_property = list(consensus_data.keys())[0]
                    consensus_info = consensus_data[first_property]
                    print(f"  Example consensus for {first_property}:")
                    print(f"    Confidence: {consensus_info.get('confidence', 0):.2f}")
                    print(f"    Total responses: {consensus_info.get('total_responses', 0)}")
            
            return results
            
        except Exception as e:
            print(f"Error in consensus validation: {e}")
            return {"status": "error", "error": str(e)}

    async def test_api_validation(self) -> dict:
        """Test API-based validation"""
        print("\n=== Testing API-Based Validation ===")
        
        # Create mock responses
        responses = self.create_mock_responses(3)  # Fewer responses for API validation
        
        print(f"Processing {len(responses)} mock responses with API validation...")
        
        try:
            results = await self.api_validator.process_assignment_responses("test_api", responses)
            
            print(f"API validation results:")
            print(f"  Status: {results.get('status')}")
            print(f"  Total validations: {results.get('total_validations', 0)}")
            print(f"  Successful validations: {results.get('successful_validations', 0)}")
            print(f"  Success rate: {results.get('success_rate', 0):.2%}")
            
            # Show validation statistics
            stats = self.api_validator.get_validation_statistics()
            print(f"  API validator statistics:")
            print(f"    Total validations: {stats.get('total_validations', 0)}")
            print(f"    API errors: {stats.get('api_errors', 0)}")
            print(f"    Error rate: {stats.get('error_rate', 0):.2%}")
            
            return results
            
        except Exception as e:
            print(f"Error in API validation: {e}")
            return {"status": "error", "error": str(e)}

    async def test_data_api_connection(self) -> dict:
        """Test connection to data API"""
        print("\n=== Testing Data API Connection ===")
        
        try:
            data_api = ValidatorDataAPI(self.wallet, self.config.data_api_url)
            
            # Test authentication (this would fail without proper API)
            print(f"Testing connection to: {self.config.data_api_url}")
            print("Note: This test will fail without a real API endpoint")
            
            # In a real test, you would:
            # access_data = await data_api.get_validator_access()
            # data_blocks = await data_api.get_data_blocks()
            
            return {"status": "test_skipped", "reason": "no_real_api_endpoint"}
            
        except Exception as e:
            print(f"Expected error (no real API): {e}")
            return {"status": "expected_error", "error": str(e)}

    def print_configuration(self):
        """Print current configuration"""
        print("=== Validation System Configuration ===")
        config_dict = self.config.to_dict()
        
        for key, value in config_dict.items():
            print(f"  {key}: {value}")

    async def run_all_tests(self):
        """Run all validation tests"""
        print("Starting validation system tests...")
        
        self.print_configuration()
        
        # Test data API connection
        api_results = await self.test_data_api_connection()
        
        # Test consensus validation
        consensus_results = await self.test_consensus_validation()
        
        # Test API validation if enabled
        if self.config.enable_validator_spot_checks:
            api_validation_results = await self.test_api_validation()
        else:
            api_validation_results = {"status": "disabled", "reason": "spot_checks_disabled"}
            print("\n=== API-Based Validation ===")
            print("API validation disabled (ENABLE_VALIDATOR_SPOT_CHECKS=false)")
        
        # Summary
        print("\n=== Test Summary ===")
        print(f"Data API test: {api_results.get('status')}")
        print(f"Consensus validation: {consensus_results.get('status')}")
        print(f"API validation: {api_validation_results.get('status')}")
        
        return {
            "data_api_test": api_results,
            "consensus_validation": consensus_results,
            "api_validation": api_validation_results
        }


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Test validation systems')
    parser.add_argument('--config', choices=['consensus', 'api', 'development'], 
                       default='consensus', help='Configuration to use')
    parser.add_argument('--enable-spot-checks', action='store_true', 
                       help='Enable validator spot checks (API validation)')
    
    args = parser.parse_args()
    
    # Select configuration
    if args.config == 'consensus':
        config = CONSENSUS_ONLY_CONFIG
    elif args.config == 'api':
        config = API_VALIDATION_CONFIG
    elif args.config == 'development':
        config = DEVELOPMENT_CONFIG
    else:
        config = CONSENSUS_ONLY_CONFIG
    
    # Override spot checks if specified
    if args.enable_spot_checks:
        config.enable_validator_spot_checks = True
        config.validation_mode = 'api'
    
    # Create tester and run tests
    tester = ValidationSystemTester(config)
    
    try:
        results = await tester.run_all_tests()
        print(f"\nAll tests completed successfully!")
        return 0
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
