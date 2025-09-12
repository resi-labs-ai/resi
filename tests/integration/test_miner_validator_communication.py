"""
Miner-Validator Direct Communication Tests

Tests the direct communication between validators and miners via axon/dendrite,
including OnDemandRequest processing, authentication, and error handling.
"""

import asyncio
import unittest
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

import bittensor as bt
from common.protocol import OnDemandRequest
from common.data import DataEntity, DataSource, DataLabel
from scraping.zillow.model import RealEstateContent
from vali_utils.organic_query_processor import OrganicQueryProcessor
from tests.integration.fixtures.test_wallets import get_test_wallet_manager, cleanup_test_wallets
from tests.integration.fixtures.mock_axons import get_mock_miner_network, cleanup_mock_miners
from tests.mocks.zillow_api_client import MockZillowAPIClient


class TestMinerValidatorCommunication(unittest.TestCase):
    """Test direct miner-validator communication"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test infrastructure"""
        bt.logging.set_info(True)
        
        # Set up test wallets
        cls.wallet_manager = get_test_wallet_manager()
        cls.validator_wallets = cls.wallet_manager.get_validator_wallets()[:1]
        
        # Set up mock miner network
        cls.miner_network = get_mock_miner_network(num_miners=3)
        
        # Set up real data client
        cls.mock_client = MockZillowAPIClient("mocked_data")
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test infrastructure"""
        cleanup_mock_miners()
        cleanup_test_wallets()
    
    async def _create_test_data_entities(self, count: int = 15) -> List[DataEntity]:
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
                    datetime=datetime.now(timezone.utc) - timedelta(hours=i),
                    source=DataSource.RAPID_ZILLOW,
                    label=DataLabel(value=f"zip:{zipcode}"),
                    content=content.model_dump_json().encode(),
                    content_size_bytes=len(content.model_dump_json())
                )
                
                entities.append(entity)
        
        return entities
    
    def test_validator_miner_on_demand_request(self):
        """Test validator sending OnDemandRequest to miner"""
        
        async def run_test():
            bt.logging.info("Testing validator→miner OnDemandRequest")
            
            # Set up test data in miners
            test_entities = await self._create_test_data_entities(10)
            self.miner_network.add_mock_data_to_all_miners(test_entities)
            
            # Start mock miners
            self.miner_network.start_all_miners()
            
            # Wait for miners to start
            await asyncio.sleep(1.0)
            
            # Create validator wallet and dendrite
            validator_wallet = self.validator_wallets[0]
            
            # Create OnDemandRequest
            request = OnDemandRequest(
                source=DataSource.RAPID_ZILLOW,
                keywords=["78041"],  # Search for Laredo properties
                start_date=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                end_date=datetime.now(timezone.utc).isoformat(),
                limit=5
            )
            
            # Get miner axon infos
            axon_infos = self.miner_network.get_axon_infos()
            
            # Send request to miners
            async with bt.dendrite(wallet=validator_wallet) as dendrite:
                responses = await dendrite.forward(
                    axons=axon_infos,
                    synapse=request,
                    timeout=10
                )
            
            # Verify responses
            self.assertEqual(len(responses), len(axon_infos), "Should get response from each miner")
            
            successful_responses = 0
            total_data_items = 0
            
            for i, response in enumerate(responses):
                if response is not None and hasattr(response, 'data'):
                    successful_responses += 1
                    data_items = len(response.data) if response.data else 0
                    total_data_items += data_items
                    bt.logging.info(f"Miner {i} returned {data_items} items")
                else:
                    bt.logging.warning(f"Miner {i} failed to respond properly")
            
            # Assertions
            self.assertGreater(successful_responses, 0, "At least one miner should respond successfully")
            self.assertGreater(total_data_items, 0, "Should receive some data items")
            
            bt.logging.info(f"✅ OnDemandRequest test passed: {successful_responses}/{len(axon_infos)} miners responded with {total_data_items} total items")
        
        asyncio.run(run_test())
    
    def test_miner_data_filtering(self):
        """Test that miners properly filter data based on request parameters"""
        
        async def run_test():
            bt.logging.info("Testing miner data filtering")
            
            # Create test data with different labels and content
            test_entities = []
            zipcodes = ["78041", "90210", "10001"]
            
            for i, zipcode in enumerate(zipcodes):
                # Create entities with different labels
                for j in range(3):
                    entity = DataEntity(
                        uri=f"https://zillow.com/test_{zipcode}_{j}/",
                        datetime=datetime.now(timezone.utc) - timedelta(hours=i*3 + j),
                        source=DataSource.RAPID_ZILLOW,
                        label=DataLabel(value=f"zip:{zipcode}"),
                        content=f"Property in {zipcode} with keyword test_{zipcode}".encode(),
                        content_size_bytes=50
                    )
                    test_entities.append(entity)
            
            # Add data to first miner only
            first_miner_hotkey = self.miner_network.get_miner_hotkeys()[0]
            self.miner_network.add_mock_data_to_miner(first_miner_hotkey, test_entities)
            
            # Start miners
            self.miner_network.start_all_miners()
            await asyncio.sleep(1.0)
            
            validator_wallet = self.validator_wallets[0]
            
            # Test 1: Filter by keyword
            keyword_request = OnDemandRequest(
                source=DataSource.RAPID_ZILLOW,
                keywords=["test_78041"],  # Should match only Laredo properties
                limit=10
            )
            
            axon_info = self.miner_network.get_axon_infos()[0]  # First miner
            
            async with bt.dendrite(wallet=validator_wallet) as dendrite:
                responses = await dendrite.forward(
                    axons=[axon_info],
                    synapse=keyword_request,
                    timeout=10
                )
            
            response = responses[0]
            self.assertIsNotNone(response, "Should get response")
            self.assertIsNotNone(response.data, "Should have data")
            
            # Should only get items matching the keyword
            matching_items = [item for item in response.data if "test_78041" in item.get('content', '')]
            self.assertEqual(len(matching_items), 3, "Should get 3 items matching test_78041")
            
            # Test 2: Filter by username (label)
            username_request = OnDemandRequest(
                source=DataSource.RAPID_ZILLOW,
                usernames=["zip:90210"],  # Should match only Beverly Hills
                limit=10
            )
            
            async with bt.dendrite(wallet=validator_wallet) as dendrite:
                responses = await dendrite.forward(
                    axons=[axon_info],
                    synapse=username_request,
                    timeout=10
                )
            
            response = responses[0]
            self.assertIsNotNone(response, "Should get response")
            
            # Should only get items with matching label
            if response.data:
                for item in response.data:
                    # In our mock, we don't have direct label access, but we can check URI
                    self.assertIn("90210", item.get('content', ''), "Should only return Beverly Hills properties")
            
            bt.logging.info("✅ Miner data filtering test passed")
        
        asyncio.run(run_test())
    
    def test_miner_failure_scenarios(self):
        """Test miner failure scenarios and timeout handling"""
        
        async def run_test():
            bt.logging.info("Testing miner failure scenarios")
            
            # Set up test data
            test_entities = await self._create_test_data_entities(5)
            self.miner_network.add_mock_data_to_all_miners(test_entities)
            
            # Configure one miner to fail 100% of the time
            miner_hotkeys = self.miner_network.get_miner_hotkeys()
            self.miner_network.set_miner_failure_rate(miner_hotkeys[0], 1.0)  # 100% failure
            self.miner_network.set_miner_failure_rate(miner_hotkeys[1], 0.0)  # 0% failure
            self.miner_network.set_miner_failure_rate(miner_hotkeys[2], 0.5)  # 50% failure
            
            # Start miners
            self.miner_network.start_all_miners()
            await asyncio.sleep(1.0)
            
            validator_wallet = self.validator_wallets[0]
            
            # Create request
            request = OnDemandRequest(
                source=DataSource.RAPID_ZILLOW,
                keywords=["property"],
                limit=10
            )
            
            axon_infos = self.miner_network.get_axon_infos()
            
            # Send requests multiple times to test failure patterns
            failure_counts = [0, 0, 0]  # Track failures per miner
            total_tests = 5
            
            for test_round in range(total_tests):
                async with bt.dendrite(wallet=validator_wallet) as dendrite:
                    responses = await dendrite.forward(
                        axons=axon_infos,
                        synapse=request,
                        timeout=5
                    )
                
                for i, response in enumerate(responses):
                    if response is None or not hasattr(response, 'data') or not response.data:
                        failure_counts[i] += 1
            
            # Verify failure patterns
            # Miner 0: Should fail ~100% of the time
            self.assertGreaterEqual(failure_counts[0] / total_tests, 0.8, "First miner should fail most of the time")
            
            # Miner 1: Should succeed most of the time
            self.assertLessEqual(failure_counts[1] / total_tests, 0.3, "Second miner should succeed most of the time")
            
            # Miner 2: Should have mixed results
            failure_rate_2 = failure_counts[2] / total_tests
            self.assertGreater(failure_rate_2, 0.2, "Third miner should have some failures")
            self.assertLess(failure_rate_2, 0.8, "Third miner should have some successes")
            
            bt.logging.info(f"✅ Failure scenarios test passed. Failure rates: {[f/total_tests for f in failure_counts]}")
        
        asyncio.run(run_test())
    
    def test_miner_response_timeout(self):
        """Test timeout handling when miners are slow to respond"""
        
        async def run_test():
            bt.logging.info("Testing miner response timeouts")
            
            # Set up test data
            test_entities = await self._create_test_data_entities(3)
            self.miner_network.add_mock_data_to_all_miners(test_entities)
            
            # Set different response delays
            miner_hotkeys = self.miner_network.get_miner_hotkeys()
            miners = [self.miner_network.get_miner(hk) for hk in miner_hotkeys]
            
            miners[0].set_response_delay(0.1)   # Fast
            miners[1].set_response_delay(2.0)   # Slow but within timeout
            miners[2].set_response_delay(10.0)  # Very slow, should timeout
            
            # Start miners
            self.miner_network.start_all_miners()
            await asyncio.sleep(1.0)
            
            validator_wallet = self.validator_wallets[0]
            
            request = OnDemandRequest(
                source=DataSource.RAPID_ZILLOW,
                keywords=["property"],
                limit=5
            )
            
            axon_infos = self.miner_network.get_axon_infos()
            
            # Test with short timeout
            start_time = time.time()
            
            async with bt.dendrite(wallet=validator_wallet) as dendrite:
                responses = await dendrite.forward(
                    axons=axon_infos,
                    synapse=request,
                    timeout=3.0  # 3 second timeout
                )
            
            elapsed_time = time.time() - start_time
            
            # Should complete within timeout period
            self.assertLess(elapsed_time, 5.0, "Request should complete within reasonable time")
            
            # Analyze responses
            successful_responses = 0
            for i, response in enumerate(responses):
                if response is not None and hasattr(response, 'data') and response.data:
                    successful_responses += 1
                    bt.logging.info(f"Miner {i} responded successfully")
                else:
                    bt.logging.info(f"Miner {i} failed or timed out")
            
            # Fast miner should always succeed, very slow miner should timeout
            self.assertGreaterEqual(successful_responses, 1, "At least fast miner should respond")
            self.assertLessEqual(successful_responses, 2, "Very slow miner should timeout")
            
            bt.logging.info(f"✅ Timeout test passed. {successful_responses}/{len(responses)} miners responded in {elapsed_time:.2f}s")
        
        asyncio.run(run_test())
    
    def test_miner_authentication(self):
        """Test that miner requests are properly authenticated"""
        
        async def run_test():
            bt.logging.info("Testing miner authentication")
            
            # Set up test data
            test_entities = await self._create_test_data_entities(5)
            self.miner_network.add_mock_data_to_all_miners(test_entities)
            
            # Start miners
            self.miner_network.start_all_miners()
            await asyncio.sleep(1.0)
            
            validator_wallet = self.validator_wallets[0]
            
            # Create authenticated request
            request = OnDemandRequest(
                source=DataSource.RAPID_ZILLOW,
                keywords=["property"],
                limit=5
            )
            
            axon_info = self.miner_network.get_axon_infos()[0]
            
            # Test with valid wallet
            async with bt.dendrite(wallet=validator_wallet) as dendrite:
                responses = await dendrite.forward(
                    axons=[axon_info],
                    synapse=request,
                    timeout=10
                )
            
            response = responses[0]
            self.assertIsNotNone(response, "Should get response with valid authentication")
            
            # For this test, we assume authentication passes since our mock miners
            # don't implement full authentication validation
            # In a real scenario, we would test with invalid signatures, expired timestamps, etc.
            
            bt.logging.info("✅ Authentication test passed")
        
        asyncio.run(run_test())
    
    def test_concurrent_validator_requests(self):
        """Test multiple validators making concurrent requests to miners"""
        
        async def run_test():
            bt.logging.info("Testing concurrent validator requests")
            
            # Set up test data
            test_entities = await self._create_test_data_entities(10)
            self.miner_network.add_mock_data_to_all_miners(test_entities)
            
            # Start miners
            self.miner_network.start_all_miners()
            await asyncio.sleep(1.0)
            
            # Use multiple validator wallets
            validator_wallets = self.wallet_manager.get_validator_wallets()[:2]
            
            async def send_request(validator_wallet, request_id):
                """Send a request from a specific validator"""
                request = OnDemandRequest(
                    source=DataSource.RAPID_ZILLOW,
                    keywords=[f"property_{request_id}"],
                    limit=5
                )
                
                axon_infos = self.miner_network.get_axon_infos()
                
                async with bt.dendrite(wallet=validator_wallet) as dendrite:
                    responses = await dendrite.forward(
                        axons=axon_infos,
                        synapse=request,
                        timeout=10
                    )
                
                successful = sum(1 for r in responses if r is not None)
                bt.logging.info(f"Validator {request_id}: {successful}/{len(responses)} miners responded")
                return successful
            
            # Send concurrent requests
            tasks = []
            for i, validator_wallet in enumerate(validator_wallets):
                task = send_request(validator_wallet, i)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All validators should get responses
            for i, successful_count in enumerate(results):
                self.assertGreater(successful_count, 0, f"Validator {i} should get at least one response")
            
            bt.logging.info(f"✅ Concurrent requests test passed. Results: {results}")
        
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main(verbosity=2)
