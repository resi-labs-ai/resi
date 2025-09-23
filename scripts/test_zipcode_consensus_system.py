#!/usr/bin/env python3
"""
Test script for the complete Zipcode Consensus Validation System
Tests both mock API server and S3-integrated consensus validation
"""

import asyncio
import sys
import os
import argparse
import subprocess
import time
import requests
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.zipcode_consensus_config import (
    ZipcodeConsensusConfig, 
    MOCK_SERVER_CONFIG, 
    PRODUCTION_S3_CONSENSUS_CONFIG,
    TESTNET_CONFIG
)
from vali_utils.zipcode_assignment_manager import ZipcodeAssignmentManager
from vali_utils.s3_consensus_validator import S3ConsensusValidator
from vali_utils.validator_data_api import ValidatorDataAPI
from common.protocol import DataAssignmentRequest
import bittensor as bt


class ZipcodeConsensusSystemTester:
    """Test the complete zipcode consensus validation system"""
    
    def __init__(self, config: ZipcodeConsensusConfig):
        self.config = config
        self.mock_server_process = None
        
        # Initialize minimal components for testing
        self.wallet = None  # Would need proper initialization
        self.metagraph = None  # Would need proper initialization
        
    async def run_complete_system_test(self) -> dict:
        """Run end-to-end test of the zipcode consensus system"""
        print("🚀 Starting Complete Zipcode Consensus System Test")
        print(f"Configuration: {self.config.data_api_url}")
        print(f"Sources: {self.config.enabled_sources}")
        print(f"S3 Integration: {self.config.use_s3_consensus}")
        
        test_results = {}
        
        try:
            # Step 1: Start mock API server if needed
            if 'localhost' in self.config.data_api_url:
                await self._start_mock_server()
                test_results['mock_server'] = {'status': 'started'}
            
            # Step 2: Test API connectivity and authentication
            api_test = await self._test_api_connectivity()
            test_results['api_connectivity'] = api_test
            
            if not api_test['success']:
                return test_results
            
            # Step 3: Test zipcode block retrieval
            block_test = await self._test_zipcode_block_retrieval()
            test_results['zipcode_blocks'] = block_test
            
            if not block_test['success']:
                return test_results
            
            # Step 4: Test zipcode assignment creation
            assignment_test = await self._test_zipcode_assignment_creation(block_test['data_blocks'])
            test_results['zipcode_assignments'] = assignment_test
            
            # Step 5: Test miner assignment formatting
            miner_test = await self._test_miner_assignment_formatting(assignment_test['assignments'])
            test_results['miner_assignments'] = miner_test
            
            # Step 6: Test S3 consensus validation (if enabled)
            if self.config.use_s3_consensus:
                s3_test = await self._test_s3_consensus_validation()
                test_results['s3_consensus'] = s3_test
            else:
                test_results['s3_consensus'] = {'status': 'disabled', 'success': True}
            
            # Step 7: Test behavioral analysis
            behavior_test = await self._test_behavioral_analysis()
            test_results['behavioral_analysis'] = behavior_test
            
            print("\n✅ Complete system test finished successfully!")
            return test_results
            
        except Exception as e:
            print(f"\n❌ System test failed: {e}")
            test_results['error'] = str(e)
            return test_results
            
        finally:
            # Cleanup
            if self.mock_server_process:
                self._stop_mock_server()

    async def _start_mock_server(self):
        """Start the mock API server"""
        print("\n📡 Starting Mock API Server...")
        
        server_script = Path(__file__).parent.parent / "mock_data_api_server.py"
        
        try:
            self.mock_server_process = subprocess.Popen([
                sys.executable, str(server_script),
                '--host', 'localhost',
                '--port', '8000'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            for i in range(10):
                try:
                    response = requests.get('http://localhost:8000/health', timeout=1)
                    if response.status_code == 200:
                        print("✅ Mock API server started successfully")
                        return
                except:
                    await asyncio.sleep(1)
            
            raise Exception("Mock server failed to start within 10 seconds")
            
        except Exception as e:
            print(f"❌ Failed to start mock server: {e}")
            raise

    def _stop_mock_server(self):
        """Stop the mock API server"""
        if self.mock_server_process:
            print("\n🛑 Stopping Mock API Server...")
            self.mock_server_process.terminate()
            self.mock_server_process.wait()

    async def _test_api_connectivity(self) -> dict:
        """Test API connectivity and authentication"""
        print("\n🔐 Testing API Connectivity and Authentication...")
        
        try:
            # Test health endpoint
            health_response = requests.get(f"{self.config.data_api_url}/health", timeout=5)
            
            if health_response.status_code != 200:
                return {'success': False, 'error': f'Health check failed: {health_response.status_code}'}
            
            health_data = health_response.json()
            print(f"   📊 Server Status: {health_data.get('status')}")
            print(f"   📊 Total Zipcodes: {health_data.get('total_zipcodes')}")
            
            # Test authentication
            auth_payload = {
                "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
                "timestamp": int(time.time()),
                "signature": "mock_signature_for_testing",
                "sources": ",".join(self.config.enabled_sources)
            }
            
            auth_response = requests.post(
                f"{self.config.data_api_url}/get-validator-access",
                json=auth_payload,
                timeout=5
            )
            
            if auth_response.status_code != 200:
                return {'success': False, 'error': f'Authentication failed: {auth_response.status_code}'}
            
            auth_data = auth_response.json()
            access_token = auth_data.get('access_token')
            
            print(f"   🔑 Authentication successful")
            print(f"   🔑 Access token: {access_token[:20]}...")
            print(f"   🔑 Authorized sources: {auth_data.get('sources_authorized')}")
            
            return {
                'success': True,
                'health_data': health_data,
                'auth_data': auth_data,
                'access_token': access_token
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _test_zipcode_block_retrieval(self) -> dict:
        """Test zipcode block retrieval from API"""
        print("\n📋 Testing Zipcode Block Retrieval...")
        
        try:
            # Get authentication first
            api_test = await self._test_api_connectivity()
            if not api_test['success']:
                return api_test
            
            access_token = api_test['access_token']
            
            # Request zipcode blocks
            headers = {'Authorization': f'Bearer {access_token}'}
            params = {
                'sources': ','.join(self.config.enabled_sources),
                'block_size': self.config.zipcodes_per_batch,
                'format': 'json'
            }
            
            response = requests.get(
                f"{self.config.data_api_url}/api/v1/validator-data",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return {'success': False, 'error': f'Block retrieval failed: {response.status_code}'}
            
            data_blocks = response.json()
            
            print(f"   📦 Request ID: {data_blocks.get('request_id')}")
            print(f"   📦 Total Batches: {data_blocks.get('total_batches')}")
            print(f"   📦 Total Zipcodes: {data_blocks.get('total_zipcodes')}")
            
            # Show sample batch
            sample_batches = list(data_blocks.get('data_blocks', {}).items())[:2]
            for batch_id, batch_data in sample_batches:
                print(f"   📦 {batch_id}: {len(batch_data['zipcodes'])} zipcodes, {batch_data['expected_properties']} expected properties")
                print(f"      Zipcodes: {batch_data['zipcodes'][:5]}{'...' if len(batch_data['zipcodes']) > 5 else ''}")
            
            return {
                'success': True,
                'data_blocks': data_blocks,
                'total_batches': data_blocks.get('total_batches', 0),
                'total_zipcodes': data_blocks.get('total_zipcodes', 0)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _test_zipcode_assignment_creation(self, data_blocks: dict) -> dict:
        """Test zipcode assignment creation using ZipcodeAssignmentManager"""
        print("\n🎯 Testing Zipcode Assignment Creation...")
        
        try:
            # Create mock metagraph for testing
            mock_metagraph = self._create_mock_metagraph()
            
            # Initialize assignment manager
            assignment_manager = ZipcodeAssignmentManager(mock_metagraph, self.config.to_dict())
            
            # Extract zipcodes from API blocks
            all_zipcodes = []
            for batch_data in data_blocks.get('data_blocks', {}).values():
                all_zipcodes.extend(batch_data['zipcodes'])
            
            # Create mock available miners
            available_miners = list(range(20))  # 20 mock miners
            
            # Create assignments
            assignments = assignment_manager.create_zipcode_assignments(
                available_zipcodes=all_zipcodes[:50],  # Limit for testing
                available_miners=available_miners,
                sources=self.config.enabled_sources
            )
            
            print(f"   🎯 Total Assignments: {len(assignments['miner_assignments'])}")
            print(f"   🎯 Total Miners Assigned: {assignments['total_miners_assigned']}")
            print(f"   🎯 Total Zipcodes: {assignments['total_zipcodes']}")
            print(f"   🎯 Zipcode Batches: {len(assignments['zipcode_batches'])}")
            
            # Show assignment statistics
            stats = assignment_manager.get_assignment_statistics(assignments)
            print(f"   📊 Unique Miners: {stats['total_unique_miners']}")
            print(f"   📊 Cold Key Diversity: {stats['coldkey_diversity_ratio']:.2f}")
            print(f"   📊 Avg Assignments per Batch: {stats['average_assignments_per_batch']:.1f}")
            
            return {
                'success': True,
                'assignments': assignments,
                'statistics': stats
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _test_miner_assignment_formatting(self, assignments: dict) -> dict:
        """Test formatting assignments for individual miners"""
        print("\n⚙️ Testing Miner Assignment Formatting...")
        
        try:
            assignment_manager = ZipcodeAssignmentManager(self._create_mock_metagraph(), self.config.to_dict())
            
            # Test formatting for a few miners
            sample_miners = [0, 1, 2]
            formatted_assignments = {}
            
            for miner_uid in sample_miners:
                # Find an assignment this miner is part of
                for assignment_key, assignment_data in assignments['miner_assignments'].items():
                    if miner_uid in assignment_data['miners']:
                        formatted = assignment_manager.format_assignment_for_miner(
                            miner_uid, assignment_key, assignments
                        )
                        
                        if formatted:
                            formatted_assignments[miner_uid] = formatted
                            print(f"   ⚙️ Miner {miner_uid}: {len(formatted.get('zipcode_assignments', {}).get('ZILLOW_SOLD', []))} zipcodes assigned")
                            print(f"      Batch ID: {formatted.get('zipcode_batch_id')}")
                            print(f"      Overlap Group: {formatted.get('overlap_group')}")
                        break
            
            return {
                'success': True,
                'formatted_assignments': formatted_assignments,
                'sample_count': len(formatted_assignments)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _test_s3_consensus_validation(self) -> dict:
        """Test S3-integrated consensus validation"""
        print("\n🗄️ Testing S3 Consensus Validation...")
        
        try:
            # Create mock components
            mock_metagraph = self._create_mock_metagraph()
            mock_scorer = self._create_mock_scorer()
            mock_scraper_provider = self._create_mock_scraper_provider()
            
            # Initialize S3 consensus validator
            s3_validator = S3ConsensusValidator(
                config=self.config,
                wallet=self.wallet,
                metagraph=mock_metagraph,
                scorer=mock_scorer,
                scraper_provider=mock_scraper_provider,
                s3_reader=None  # Mock S3 reader
            )
            
            # Create mock assignment data
            mock_assignments = {
                'batch_001_group_0': {
                    'batch_id': 'batch_001',
                    'overlap_group': 0,
                    'zipcodes': ['77494', '78701', '90210'],
                    'miners': [0, 1, 2, 3, 4],
                    'sources': ['ZILLOW_SOLD']
                },
                'batch_001_group_1': {
                    'batch_id': 'batch_001',
                    'overlap_group': 1,
                    'zipcodes': ['77494', '78701', '90210'],
                    'miners': [5, 6, 7, 8, 9],
                    'sources': ['ZILLOW_SOLD']
                }
            }
            
            # Test consensus validation
            validation_results = await s3_validator.process_s3_consensus_validation(
                'test_assignment_001',
                mock_assignments
            )
            
            print(f"   🗄️ Validation Status: {validation_results.get('status')}")
            print(f"   🗄️ S3 Data Sources: {validation_results.get('s3_data_sources', 0)}")
            print(f"   🗄️ Anomalies Detected: {validation_results.get('anomalies_detected', 0)}")
            print(f"   🗄️ Validation Method: {validation_results.get('validation_method')}")
            
            return {
                'success': validation_results.get('status') == 'completed',
                'validation_results': validation_results
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _test_behavioral_analysis(self) -> dict:
        """Test behavioral analysis for anomaly detection"""
        print("\n🕵️ Testing Behavioral Analysis...")
        
        try:
            # Create mock responses with some anomalies
            mock_responses = []
            
            # Normal responses
            for i in range(8):
                response = DataAssignmentRequest(
                    request_id=f"test_assignment_miner_{i}",
                    assignment_mode="zipcodes",
                    zipcode_assignments={"ZILLOW_SOLD": ["77494", "78701"]},
                    completion_status="completed",
                    submission_timestamp="2025-01-15T10:45:00Z",
                    scrape_timestamp="2025-01-15T10:30:00Z"
                )
                setattr(response, 'miner_uid', i)
                mock_responses.append(response)
            
            # Anomalous responses (synchronized)
            sync_time = "2025-01-15T10:44:59Z"
            for i in range(8, 12):
                response = DataAssignmentRequest(
                    request_id=f"test_assignment_miner_{i}",
                    assignment_mode="zipcodes",
                    zipcode_assignments={"ZILLOW_SOLD": ["77494", "78701"]},
                    completion_status="completed",
                    submission_timestamp=sync_time,  # Synchronized!
                    scrape_timestamp="2025-01-15T10:30:00Z"
                )
                setattr(response, 'miner_uid', i)
                mock_responses.append(response)
            
            # Test anomaly detection
            mock_metagraph = self._create_mock_metagraph()
            mock_scorer = self._create_mock_scorer()
            mock_scraper_provider = self._create_mock_scraper_provider()
            
            s3_validator = S3ConsensusValidator(
                config=self.config,
                wallet=self.wallet,
                metagraph=mock_metagraph,
                scorer=mock_scorer,
                scraper_provider=mock_scraper_provider
            )
            
            # Simulate anomaly detection
            anomalies = s3_validator._detect_s3_behavioral_anomalies({
                'batch_001': [
                    {
                        'miner_uid': i,
                        's3_data': [None] * (50 + i),  # Varying data amounts
                        'zipcodes': ['77494', '78701']
                    }
                    for i in range(12)
                ]
            })
            
            print(f"   🕵️ Anomalies Detected: {len(anomalies)} miners")
            print(f"   🕵️ Anomalous Miners: {anomalies[:5]}{'...' if len(anomalies) > 5 else ''}")
            print(f"   🕵️ Anomaly Rate: {len(anomalies)/12:.1%}")
            
            return {
                'success': True,
                'anomalies_detected': len(anomalies),
                'anomaly_rate': len(anomalies) / 12,
                'anomalous_miners': anomalies
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _create_mock_metagraph(self):
        """Create mock metagraph for testing"""
        class MockMetagraph:
            def __init__(self):
                # Create mock coldkeys (20 unique cold keys)
                self.coldkeys = [f"coldkey_{i//2}" for i in range(20)]  # 2 miners per cold key
                self.hotkeys = [f"hotkey_{i}" for i in range(20)]
        
        return MockMetagraph()

    def _create_mock_scorer(self):
        """Create mock scorer for testing"""
        class MockScorer:
            def __init__(self):
                # Mock credibility scores for 20 miners
                self.miner_credibility = {i: 0.8 + (i * 0.01) for i in range(20)}
            
            def _update_credibility(self, miner_uid, validation_results):
                # Mock credibility update
                pass
        
        return MockScorer()

    def _create_mock_scraper_provider(self):
        """Create mock scraper provider for testing"""
        class MockScraperProvider:
            def get(self, scraper_id):
                return None  # Mock scraper
        
        return MockScraperProvider()

    def print_test_summary(self, results: dict):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("🏁 ZIPCODE CONSENSUS SYSTEM TEST SUMMARY")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, test_result in results.items():
            if isinstance(test_result, dict) and 'success' in test_result:
                total_tests += 1
                status = "✅ PASS" if test_result['success'] else "❌ FAIL"
                print(f"{status} {test_name.replace('_', ' ').title()}")
                
                if test_result['success']:
                    passed_tests += 1
                else:
                    error = test_result.get('error', 'Unknown error')
                    print(f"      Error: {error}")
        
        print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! System is ready for deployment.")
        else:
            print("⚠️  Some tests failed. Please review and fix issues before deployment.")


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Test Zipcode Consensus Validation System')
    parser.add_argument('--config', choices=['mock', 'testnet', 'production'], 
                       default='mock', help='Configuration to use')
    parser.add_argument('--enable-s3', action='store_true', 
                       help='Enable S3 consensus validation')
    parser.add_argument('--enable-spot-checks', action='store_true', 
                       help='Enable validator spot checks')
    
    args = parser.parse_args()
    
    # Select configuration
    if args.config == 'mock':
        config = MOCK_SERVER_CONFIG
    elif args.config == 'testnet':
        config = TESTNET_CONFIG
    elif args.config == 'production':
        config = PRODUCTION_S3_CONSENSUS_CONFIG
    else:
        config = MOCK_SERVER_CONFIG
    
    # Override settings if specified
    if args.enable_s3:
        config.use_s3_consensus = True
    if args.enable_spot_checks:
        config.enable_validator_spot_checks = True
    
    # Create tester and run tests
    tester = ZipcodeConsensusSystemTester(config)
    
    try:
        results = await tester.run_complete_system_test()
        tester.print_test_summary(results)
        
        # Return appropriate exit code
        failed_tests = sum(1 for r in results.values() 
                          if isinstance(r, dict) and not r.get('success', True))
        return 0 if failed_tests == 0 else 1
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
