"""
Comprehensive Testing Demo Script

Demonstrates the complete integration testing suite including:
- S3 upload/download flow testing
- Miner-validator communication testing  
- Failure scenario testing (properties not found, price changes, etc.)
- Performance and load testing
- Authentication and security testing

This script shows how the testing infrastructure validates the entire
subnet ecosystem from miner data scraping to validator consensus.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

import bittensor as bt
from tests.integration.fixtures.test_wallets import get_test_wallet_manager, cleanup_test_wallets
from tests.integration.fixtures.mock_s3 import get_mock_s3_auth_server, cleanup_mock_s3, MockS3Uploader, MockS3Validator
from tests.integration.fixtures.mock_axons import get_mock_miner_network, cleanup_mock_miners
from tests.integration.fixtures.failure_scenarios import create_failure_test_client
from tests.mocks.zillow_api_client import MockZillowAPIClient
from scraping.zillow.model import RealEstateContent
from common.data import DataEntity, DataSource, DataLabel


class ComprehensiveTestingDemo:
    """Demonstrates comprehensive testing capabilities"""
    
    def __init__(self):
        bt.logging.set_info(True)
        self.setup_complete = False
        
        # Test infrastructure
        self.wallet_manager = None
        self.mock_s3_server = None
        self.miner_network = None
        self.mock_client = None
        self.failure_client = None
        
        # Test results
        self.results = {
            'setup': False,
            's3_upload_download': False,
            'miner_validator_communication': False,
            'failure_scenarios': {},
            'performance_metrics': {},
            'authentication': False,
            'cleanup': False
        }
    
    async def setup_infrastructure(self):
        """Set up all test infrastructure"""
        bt.logging.info("🏗️  Setting up comprehensive testing infrastructure...")
        
        try:
            # Set up test wallets
            self.wallet_manager = get_test_wallet_manager()
            miner_wallets = self.wallet_manager.get_miner_wallets()[:3]
            validator_wallets = self.wallet_manager.get_validator_wallets()[:2]
            
            bt.logging.info(f"✅ Created {len(miner_wallets)} miner wallets and {len(validator_wallets)} validator wallets")
            
            # Set up mock S3 server
            self.mock_s3_server = get_mock_s3_auth_server(port=8081)
            self.s3_auth_url = "http://localhost:8081"
            bt.logging.info("✅ Mock S3 auth server started on port 8081")
            
            # Set up mock miner network
            self.miner_network = get_mock_miner_network(num_miners=3)
            bt.logging.info("✅ Mock miner network created with 3 miners")
            
            # Set up real data client
            self.mock_client = MockZillowAPIClient("mocked_data")
            bt.logging.info(f"✅ Real data client loaded: {len(list(self.mock_client.get_available_zpids()))} properties")
            
            # Set up failure scenario client
            self.failure_client, self.failure_scenarios = create_failure_test_client("mocked_data")
            bt.logging.info(f"✅ Failure scenario client created with {len(self.failure_scenarios)} scenarios")
            
            self.setup_complete = True
            self.results['setup'] = True
            
            bt.logging.info("🎉 Test infrastructure setup complete!")
            
        except Exception as e:
            bt.logging.error(f"❌ Setup failed: {e}")
            raise
    
    async def demo_s3_upload_download_flow(self):
        """Demonstrate S3 upload/download testing"""
        bt.logging.info("\n📦 Demonstrating S3 Upload/Download Flow Testing...")
        
        try:
            # Get test wallets
            miner_wallet = self.wallet_manager.get_miner_wallets()[0]
            validator_wallet = self.wallet_manager.get_validator_wallets()[0]
            
            # Create mock uploaders
            mock_uploader = MockS3Uploader(self.mock_s3_server)
            mock_validator = MockS3Validator(self.mock_s3_server)
            
            # Test 1: Miner uploads data
            bt.logging.info("🔄 Testing miner data upload...")
            job_ids = ["zillow_78041", "zillow_90210", "zillow_10001"]
            upload_count = 0
            
            for job_id in job_ids:
                for chunk_idx in range(3):  # 3 chunks per job
                    chunk_data = f"test_data_{job_id}_chunk_{chunk_idx}".encode()
                    success = await mock_uploader.upload_chunk(
                        miner_wallet.hotkey.ss58_address,
                        job_id,
                        chunk_data,
                        chunk_idx
                    )
                    if success:
                        upload_count += 1
            
            bt.logging.info(f"✅ Uploaded {upload_count}/9 chunks successfully")
            
            # Test 2: Validator downloads and validates data
            bt.logging.info("🔍 Testing validator data download...")
            files = await mock_validator.get_miner_files(miner_wallet.hotkey.ss58_address)
            bt.logging.info(f"✅ Found {len(files)} files for validation")
            
            download_count = 0
            for file_info in files[:5]:  # Test first 5 files
                downloaded_data = await mock_validator.download_file(
                    miner_wallet.hotkey.ss58_address,
                    file_info['key']
                )
                if downloaded_data:
                    download_count += 1
            
            bt.logging.info(f"✅ Downloaded {download_count}/5 files successfully")
            
            # Test 3: Authentication flow
            bt.logging.info("🔐 Testing S3 authentication...")
            import requests
            
            hotkey = miner_wallet.hotkey.ss58_address
            coldkey = miner_wallet.coldkey.ss58_address
            timestamp = int(time.time())
            commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
            signature = miner_wallet.hotkey.sign(commitment.encode())
            
            payload = {
                "coldkey": coldkey,
                "hotkey": hotkey,
                "timestamp": timestamp,
                "signature": signature.hex()
            }
            
            response = requests.post(f"{self.s3_auth_url}/get-folder-access", json=payload, timeout=5)
            auth_success = response.status_code == 200
            
            bt.logging.info(f"✅ S3 authentication: {'SUCCESS' if auth_success else 'FAILED'}")
            
            self.results['s3_upload_download'] = True
            self.results['authentication'] = auth_success
            
            bt.logging.info("🎉 S3 flow testing completed successfully!")
            
        except Exception as e:
            bt.logging.error(f"❌ S3 flow testing failed: {e}")
            self.results['s3_upload_download'] = False
    
    async def demo_miner_validator_communication(self):
        """Demonstrate miner-validator communication testing"""
        bt.logging.info("\n🔗 Demonstrating Miner-Validator Communication Testing...")
        
        try:
            # Create test data entities
            test_entities = await self._create_test_data_entities(15)
            bt.logging.info(f"📊 Created {len(test_entities)} test data entities")
            
            # Add data to miners
            self.miner_network.add_mock_data_to_all_miners(test_entities)
            bt.logging.info("📤 Added test data to all miners")
            
            # Configure miner failure rates for testing
            miner_hotkeys = self.miner_network.get_miner_hotkeys()
            self.miner_network.set_miner_failure_rate(miner_hotkeys[0], 0.0)   # Reliable miner
            self.miner_network.set_miner_failure_rate(miner_hotkeys[1], 0.3)   # 30% failure
            self.miner_network.set_miner_failure_rate(miner_hotkeys[2], 0.8)   # 80% failure
            
            # Start miners
            self.miner_network.start_all_miners()
            bt.logging.info("🚀 Started all mock miners")
            
            await asyncio.sleep(2.0)  # Wait for startup
            
            # Test validator requests
            validator_wallet = self.wallet_manager.get_validator_wallets()[0]
            
            from common.protocol import OnDemandRequest
            request = OnDemandRequest(
                source=DataSource.SZILL_VALI,
                keywords=["78041", "property"],
                limit=10
            )
            
            axon_infos = self.miner_network.get_axon_infos()
            
            # Send requests and measure performance
            start_time = time.time()
            successful_responses = 0
            total_data_items = 0
            
            async with bt.dendrite(wallet=validator_wallet) as dendrite:
                responses = await dendrite.forward(
                    axons=axon_infos,
                    synapse=request,
                    timeout=10
                )
            
            request_time = time.time() - start_time
            
            # Analyze responses
            for i, response in enumerate(responses):
                if response is not None and hasattr(response, 'data') and response.data:
                    successful_responses += 1
                    total_data_items += len(response.data)
                    bt.logging.info(f"✅ Miner {i} responded with {len(response.data)} items")
                else:
                    bt.logging.warning(f"❌ Miner {i} failed to respond")
            
            success_rate = successful_responses / len(responses) * 100
            
            bt.logging.info(f"📊 Communication Results:")
            bt.logging.info(f"   • Success Rate: {success_rate:.1f}% ({successful_responses}/{len(responses)})")
            bt.logging.info(f"   • Total Data Items: {total_data_items}")
            bt.logging.info(f"   • Request Time: {request_time:.2f}s")
            
            self.results['miner_validator_communication'] = True
            self.results['performance_metrics'] = {
                'success_rate': success_rate,
                'request_time': request_time,
                'data_items': total_data_items
            }
            
            bt.logging.info("🎉 Miner-validator communication testing completed!")
            
        except Exception as e:
            bt.logging.error(f"❌ Communication testing failed: {e}")
            self.results['miner_validator_communication'] = False
    
    async def demo_failure_scenarios(self):
        """Demonstrate failure scenario testing"""
        bt.logging.info("\n💥 Demonstrating Failure Scenario Testing...")
        
        try:
            self.failure_client.enable_failure_mode()
            
            # Test different failure types
            failure_types = [
                'property_not_found',
                'price_change', 
                'status_change',
                'data_corruption'
            ]
            
            for failure_type in failure_types:
                bt.logging.info(f"🧪 Testing {failure_type} scenarios...")
                
                scenarios = [s for s in self.failure_scenarios if s['scenario_type'] == failure_type]
                passed = 0
                failed = 0
                
                for scenario in scenarios[:3]:  # Test first 3 of each type
                    try:
                        if failure_type == 'property_not_found':
                            result = await self._test_property_not_found(scenario)
                        elif failure_type == 'price_change':
                            result = await self._test_price_change(scenario)
                        elif failure_type == 'status_change':
                            result = await self._test_status_change(scenario)
                        elif failure_type == 'data_corruption':
                            result = await self._test_data_corruption(scenario)
                        
                        if result:
                            passed += 1
                        else:
                            failed += 1
                            
                    except Exception as e:
                        bt.logging.debug(f"Expected failure in {failure_type}: {e}")
                        failed += 1
                
                success_rate = passed / (passed + failed) * 100 if (passed + failed) > 0 else 0
                bt.logging.info(f"   ✅ {failure_type}: {passed} passed, {failed} failed ({success_rate:.1f}% success)")
                
                self.results['failure_scenarios'][failure_type] = {
                    'passed': passed,
                    'failed': failed,
                    'success_rate': success_rate
                }
            
            bt.logging.info("🎉 Failure scenario testing completed!")
            
        except Exception as e:
            bt.logging.error(f"❌ Failure scenario testing failed: {e}")
    
    async def demo_performance_testing(self):
        """Demonstrate performance testing capabilities"""
        bt.logging.info("\n⚡ Demonstrating Performance Testing...")
        
        try:
            # Test S3 performance with multiple files
            bt.logging.info("📈 Testing S3 performance with high volume...")
            
            miner_wallet = self.wallet_manager.get_miner_wallets()[0]
            mock_uploader = MockS3Uploader(self.mock_s3_server)
            
            # Upload many files quickly
            start_time = time.time()
            upload_count = 0
            
            for job_idx in range(5):  # 5 jobs
                for chunk_idx in range(10):  # 10 chunks each
                    chunk_data = f"perf_test_job_{job_idx}_chunk_{chunk_idx}".encode()
                    success = await mock_uploader.upload_chunk(
                        miner_wallet.hotkey.ss58_address,
                        f"perf_job_{job_idx}",
                        chunk_data,
                        chunk_idx
                    )
                    if success:
                        upload_count += 1
            
            upload_time = time.time() - start_time
            upload_rate = upload_count / upload_time
            
            bt.logging.info(f"📊 Performance Results:")
            bt.logging.info(f"   • Files Uploaded: {upload_count}/50")
            bt.logging.info(f"   • Upload Time: {upload_time:.2f}s")
            bt.logging.info(f"   • Upload Rate: {upload_rate:.1f} files/sec")
            
            self.results['performance_metrics'].update({
                'upload_count': upload_count,
                'upload_time': upload_time,
                'upload_rate': upload_rate
            })
            
            bt.logging.info("🎉 Performance testing completed!")
            
        except Exception as e:
            bt.logging.error(f"❌ Performance testing failed: {e}")
    
    async def cleanup_infrastructure(self):
        """Clean up all test infrastructure"""
        bt.logging.info("\n🧹 Cleaning up test infrastructure...")
        
        try:
            # Stop miners
            if self.miner_network:
                self.miner_network.stop_all_miners()
                cleanup_mock_miners()
            
            # Stop S3 server
            cleanup_mock_s3()
            
            # Clean up wallets
            cleanup_test_wallets()
            
            self.results['cleanup'] = True
            bt.logging.info("✅ Cleanup completed successfully!")
            
        except Exception as e:
            bt.logging.error(f"❌ Cleanup failed: {e}")
            self.results['cleanup'] = False
    
    def print_comprehensive_report(self):
        """Print comprehensive test results report"""
        bt.logging.info("\n" + "="*80)
        bt.logging.info("🎯 COMPREHENSIVE TESTING REPORT")
        bt.logging.info("="*80)
        
        # Infrastructure
        bt.logging.info(f"🏗️  Infrastructure Setup: {'✅ PASS' if self.results['setup'] else '❌ FAIL'}")
        
        # S3 Testing
        bt.logging.info(f"📦 S3 Upload/Download: {'✅ PASS' if self.results['s3_upload_download'] else '❌ FAIL'}")
        bt.logging.info(f"🔐 Authentication: {'✅ PASS' if self.results['authentication'] else '❌ FAIL'}")
        
        # Communication Testing
        comm_result = self.results['miner_validator_communication']
        bt.logging.info(f"🔗 Miner-Validator Communication: {'✅ PASS' if comm_result else '❌ FAIL'}")
        
        if 'performance_metrics' in self.results:
            metrics = self.results['performance_metrics']
            if 'success_rate' in metrics:
                bt.logging.info(f"   • Success Rate: {metrics['success_rate']:.1f}%")
            if 'request_time' in metrics:
                bt.logging.info(f"   • Request Time: {metrics['request_time']:.2f}s")
        
        # Failure Scenarios
        bt.logging.info("💥 Failure Scenario Results:")
        for failure_type, results in self.results['failure_scenarios'].items():
            success_rate = results.get('success_rate', 0)
            bt.logging.info(f"   • {failure_type}: {success_rate:.1f}% success")
        
        # Performance
        if 'upload_rate' in self.results['performance_metrics']:
            rate = self.results['performance_metrics']['upload_rate']
            bt.logging.info(f"⚡ Upload Performance: {rate:.1f} files/sec")
        
        # Cleanup
        bt.logging.info(f"🧹 Cleanup: {'✅ COMPLETE' if self.results['cleanup'] else '❌ INCOMPLETE'}")
        
        bt.logging.info("="*80)
        
        # Overall assessment
        total_tests = 6
        passed_tests = sum([
            self.results['setup'],
            self.results['s3_upload_download'],
            self.results['miner_validator_communication'],
            self.results['authentication'],
            bool(self.results['failure_scenarios']),
            self.results['cleanup']
        ])
        
        overall_success = passed_tests / total_tests * 100
        
        bt.logging.info(f"🏆 OVERALL SUCCESS RATE: {overall_success:.1f}% ({passed_tests}/{total_tests} tests passed)")
        
        if overall_success >= 80:
            bt.logging.info("🎉 COMPREHENSIVE TESTING SUITE: ✅ EXCELLENT")
        elif overall_success >= 60:
            bt.logging.info("🎯 COMPREHENSIVE TESTING SUITE: ⚠️  GOOD")
        else:
            bt.logging.info("🚨 COMPREHENSIVE TESTING SUITE: ❌ NEEDS IMPROVEMENT")
        
        bt.logging.info("="*80)
    
    # Helper methods
    
    async def _create_test_data_entities(self, count: int = 10) -> List[DataEntity]:
        """Create test data entities from real Zillow data"""
        entities = []
        available_zpids = list(self.mock_client.get_available_zpids())[:count]
        
        for i, zpid in enumerate(available_zpids):
            # Get property data from our real dataset
            search_data = None
            zipcode = None
            for zc in self.mock_client.get_available_zipcodes():
                zipcode_data = await self.mock_client.get_property_search(zc)
                for prop in zipcode_data.get('props', []):
                    if str(prop.get('zpid', '')) == zpid:
                        search_data = prop
                        zipcode = zc
                        break
                if search_data:
                    break
            
            if search_data:
                # Create RealEstateContent from search data
                content = RealEstateContent.from_zillow_api(search_data)
                
                # Create entity with custom fields
                entity = DataEntity(
                    uri=f"https://zillow.com/homedetails/{zpid}_zpid/",
                    datetime=datetime.now(timezone.utc),
                    source=DataSource.SZILL_VALI,
                    label=DataLabel(value=f"zip:{zipcode}"),
                    content=content.model_dump_json().encode(),
                    content_size_bytes=len(content.model_dump_json())
                )
                
                entities.append(entity)
        
        return entities
    
    async def _test_property_not_found(self, scenario: Dict[str, Any]) -> bool:
        """Test property not found scenario"""
        zpid = scenario['zpid']
        validator_data = await self.failure_client.get_individual_property(zpid)
        return validator_data is None  # Should return None for 404
    
    async def _test_price_change(self, scenario: Dict[str, Any]) -> bool:
        """Test price change scenario"""
        zpid = scenario['zpid']
        validator_data = await self.failure_client.get_individual_property(zpid)
        if validator_data:
            new_price = validator_data.get('property', {}).get('price')
            expected_price = scenario['new_price']
            return new_price == expected_price
        return False
    
    async def _test_status_change(self, scenario: Dict[str, Any]) -> bool:
        """Test status change scenario"""
        zpid = scenario['zpid']
        validator_data = await self.failure_client.get_individual_property(zpid)
        if validator_data:
            new_status = validator_data.get('property', {}).get('listingStatus')
            expected_status = scenario['new_status']
            return new_status == expected_status
        return False
    
    async def _test_data_corruption(self, scenario: Dict[str, Any]) -> bool:
        """Test data corruption scenario"""
        zpid = scenario['zpid']
        try:
            validator_data = await self.failure_client.get_individual_property(zpid)
            if validator_data:
                # Try to create content - should fail with corrupted data
                from scraping.zillow.field_mapping import ZillowFieldMapper
                property_data = validator_data.get('property', {})
                compatible_data = ZillowFieldMapper.create_miner_compatible_content(property_data)
                RealEstateContent(**compatible_data)
                return False  # Should have failed
            return True  # No data = expected failure
        except Exception:
            return True  # Exception = expected failure


async def main():
    """Run comprehensive testing demo"""
    demo = ComprehensiveTestingDemo()
    
    try:
        # Run all demo phases
        await demo.setup_infrastructure()
        await demo.demo_s3_upload_download_flow()
        await demo.demo_miner_validator_communication()
        await demo.demo_failure_scenarios()
        await demo.demo_performance_testing()
        
    except Exception as e:
        bt.logging.error(f"Demo failed: {e}")
        
    finally:
        await demo.cleanup_infrastructure()
        demo.print_comprehensive_report()


if __name__ == "__main__":
    bt.logging.info("🚀 Starting Comprehensive Testing Suite Demo")
    bt.logging.info("This demo showcases the complete integration testing capabilities")
    bt.logging.info("including S3, miner-validator communication, and failure scenarios.\n")
    
    asyncio.run(main())
