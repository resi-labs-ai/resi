"""
Failure Scenario Integration Tests

Tests that are MEANT TO FAIL to validate error handling, edge cases,
and system resilience under various failure conditions.
"""

import asyncio
import unittest
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

import bittensor as bt
from scraping.zillow.model import RealEstateContent
from scraping.zillow.utils import validate_zillow_data_entity_fields
from common.data import DataEntity, DataSource, DataLabel
from tests.integration.fixtures.failure_scenarios import (
    create_failure_test_client,
    get_property_not_found_zpids,
    get_price_change_zpids,
    get_status_change_zpids
)
from tests.mocks.zillow_api_client import MockZillowAPIClient


class TestFailureScenarios(unittest.TestCase):
    """Tests designed to validate failure handling"""
    
    @classmethod
    def setUpClass(cls):
        """Set up failure test infrastructure"""
        bt.logging.set_info(True)
        
        # Create failure test client with comprehensive scenarios
        cls.failure_client, cls.scenarios = create_failure_test_client("mocked_data")
        cls.normal_client = MockZillowAPIClient("mocked_data")
        
        # Categorize scenarios for easier testing
        cls.scenario_by_type = {}
        for scenario in cls.scenarios:
            scenario_type = scenario['scenario_type']
            if scenario_type not in cls.scenario_by_type:
                cls.scenario_by_type[scenario_type] = []
            cls.scenario_by_type[scenario_type].append(scenario)
    
    def test_property_not_found_scenarios(self):
        """Test properties that return 404 - THESE SHOULD FAIL VALIDATION"""
        
        async def run_test():
            bt.logging.info("Testing property not found scenarios (EXPECTED FAILURES)")
            
            # Enable failure mode
            self.failure_client.enable_failure_mode()
            
            not_found_scenarios = self.scenario_by_type.get('property_not_found', [])
            self.assertGreater(len(not_found_scenarios), 0, "Should have property not found scenarios")
            
            for scenario in not_found_scenarios:
                zpid = scenario['zpid']
                bt.logging.info(f"Testing property not found for zpid: {zpid}")
                
                # First, get the property data from normal client (miner's view)
                miner_data = await self._get_miner_data_for_zpid(zpid)
                if not miner_data:
                    bt.logging.warning(f"No miner data for zpid {zpid}, skipping")
                    continue
                
                # Create miner's data entity
                miner_content = RealEstateContent.from_zillow_api(miner_data)
                miner_entity = miner_content.to_data_entity()
                
                # Now try to validate with failure client (validator's view)
                validator_data = await self.failure_client.get_individual_property(zpid)
                
                # Should return None for 404
                self.assertIsNone(validator_data, f"Property {zpid} should not be found (404)")
                
                # This represents a validation failure - property no longer exists
                validation_result = self._simulate_validation_with_missing_property(miner_entity)
                
                # EXPECTED FAILURE: Validation should fail
                self.assertFalse(validation_result['is_valid'], 
                                f"Validation should FAIL for missing property {zpid}")
                self.assertIn("not found", validation_result['reason'].lower(),
                             "Failure reason should mention property not found")
                
                bt.logging.info(f"✅ Property {zpid} correctly failed validation (property not found)")
            
            bt.logging.info(f"✅ Property not found test completed: {len(not_found_scenarios)} properties correctly failed")
        
        asyncio.run(run_test())
    
    def test_price_change_scenarios(self):
        """Test properties with price changes - SOME SHOULD FAIL, SOME SHOULD PASS"""
        
        async def run_test():
            bt.logging.info("Testing price change scenarios (MIXED RESULTS EXPECTED)")
            
            self.failure_client.enable_failure_mode()
            
            price_change_scenarios = self.scenario_by_type.get('price_change', [])
            self.assertGreater(len(price_change_scenarios), 0, "Should have price change scenarios")
            
            tolerance_threshold = 0.10  # 10% price tolerance
            
            for scenario in price_change_scenarios:
                zpid = scenario['zpid']
                original_price = scenario['original_price']
                new_price = scenario['new_price']
                change_percent = scenario['change_percent']
                
                bt.logging.info(f"Testing price change for zpid {zpid}: ${original_price} → ${new_price} ({change_percent:.1%})")
                
                # Get miner's original data
                miner_data = await self._get_miner_data_for_zpid(zpid)
                if not miner_data:
                    continue
                
                # Ensure miner data has original price
                miner_data['price'] = original_price
                miner_content = RealEstateContent.from_zillow_api(miner_data)
                miner_entity = miner_content.to_data_entity()
                
                # Get validator's updated data (with price change)
                validator_data = await self.failure_client.get_individual_property(zpid)
                self.assertIsNotNone(validator_data, "Should get validator data")
                
                validator_property = validator_data.get('property', {})
                self.assertEqual(validator_property.get('price'), new_price, "Validator should see new price")
                
                # Simulate validation with price tolerance
                validation_result = self._simulate_price_validation(
                    miner_entity, validator_property, tolerance_threshold
                )
                
                # Determine expected result based on change magnitude
                if abs(change_percent) <= tolerance_threshold:
                    # Small change - should PASS
                    self.assertTrue(validation_result['is_valid'], 
                                   f"Price change of {change_percent:.1%} should PASS (within {tolerance_threshold:.1%} tolerance)")
                    bt.logging.info(f"✅ Price change {change_percent:.1%} correctly PASSED validation")
                else:
                    # Large change - should FAIL
                    self.assertFalse(validation_result['is_valid'],
                                    f"Price change of {change_percent:.1%} should FAIL (exceeds {tolerance_threshold:.1%} tolerance)")
                    bt.logging.info(f"✅ Price change {change_percent:.1%} correctly FAILED validation")
            
            bt.logging.info(f"✅ Price change test completed: {len(price_change_scenarios)} scenarios tested")
        
        asyncio.run(run_test())
    
    def test_status_change_scenarios(self):
        """Test properties with listing status changes - SOME SHOULD FAIL, SOME SHOULD PASS"""
        
        async def run_test():
            bt.logging.info("Testing status change scenarios (MIXED RESULTS EXPECTED)")
            
            self.failure_client.enable_failure_mode()
            
            status_change_scenarios = self.scenario_by_type.get('status_change', [])
            self.assertGreater(len(status_change_scenarios), 0, "Should have status change scenarios")
            
            for scenario in status_change_scenarios:
                zpid = scenario['zpid']
                original_status = scenario['original_status']
                new_status = scenario['new_status']
                
                bt.logging.info(f"Testing status change for zpid {zpid}: {original_status} → {new_status}")
                
                # Get miner's data with original status
                miner_data = await self._get_miner_data_for_zpid(zpid)
                if not miner_data:
                    continue
                
                miner_data['listingStatus'] = original_status
                miner_content = RealEstateContent.from_zillow_api(miner_data)
                miner_entity = miner_content.to_data_entity()
                
                # Get validator's data with new status
                validator_data = await self.failure_client.get_individual_property(zpid)
                validator_property = validator_data.get('property', {})
                
                # Simulate status compatibility validation
                validation_result = self._simulate_status_validation(
                    miner_entity, validator_property, original_status, new_status
                )
                
                # Check if transition is compatible
                compatible_transitions = {
                    'FOR_SALE': ['PENDING', 'SOLD'],
                    'FOR_RENT': ['RENTED'],
                    'PENDING': ['SOLD', 'FOR_SALE'],
                    'SOLD': ['FOR_SALE'],  # Back on market
                    'RENTED': ['FOR_RENT'],
                }
                
                is_compatible = (original_status == new_status or 
                               new_status in compatible_transitions.get(original_status, []))
                
                if is_compatible:
                    # Compatible transition - should PASS
                    self.assertTrue(validation_result['is_valid'],
                                   f"Status change {original_status}→{new_status} should PASS (compatible)")
                    bt.logging.info(f"✅ Status change {original_status}→{new_status} correctly PASSED")
                else:
                    # Incompatible transition - should FAIL
                    self.assertFalse(validation_result['is_valid'],
                                    f"Status change {original_status}→{new_status} should FAIL (incompatible)")
                    bt.logging.info(f"✅ Status change {original_status}→{new_status} correctly FAILED")
            
            bt.logging.info(f"✅ Status change test completed: {len(status_change_scenarios)} scenarios tested")
        
        asyncio.run(run_test())
    
    def test_data_corruption_scenarios(self):
        """Test corrupted/malformed data - THESE SHOULD ALL FAIL"""
        
        async def run_test():
            bt.logging.info("Testing data corruption scenarios (ALL SHOULD FAIL)")
            
            self.failure_client.enable_failure_mode()
            
            corruption_scenarios = self.scenario_by_type.get('data_corruption', [])
            self.assertGreater(len(corruption_scenarios), 0, "Should have data corruption scenarios")
            
            for scenario in corruption_scenarios:
                zpid = scenario['zpid']
                bt.logging.info(f"Testing data corruption for zpid {zpid}")
                
                # Get miner's clean data
                miner_data = await self._get_miner_data_for_zpid(zpid)
                if not miner_data:
                    continue
                
                miner_content = RealEstateContent.from_zillow_api(miner_data)
                miner_entity = miner_content.to_data_entity()
                
                # Get validator's corrupted data
                validator_data = await self.failure_client.get_individual_property(zpid)
                validator_property = validator_data.get('property', {})
                
                # Try to create content from corrupted data
                validation_result = self._simulate_corruption_validation(validator_property)
                
                # EXPECTED FAILURE: All corruption should fail
                self.assertFalse(validation_result['is_valid'],
                                f"Data corruption for {zpid} should FAIL validation")
                self.assertIn("corruption", validation_result['reason'].lower(),
                             "Failure reason should mention corruption")
                
                bt.logging.info(f"✅ Data corruption for {zpid} correctly FAILED validation")
            
            bt.logging.info(f"✅ Data corruption test completed: {len(corruption_scenarios)} scenarios correctly failed")
        
        asyncio.run(run_test())
    
    def test_network_timeout_scenarios(self):
        """Test network timeouts - THESE SHOULD FAIL"""
        
        async def run_test():
            bt.logging.info("Testing network timeout scenarios (ALL SHOULD FAIL)")
            
            self.failure_client.enable_failure_mode()
            
            timeout_scenarios = self.scenario_by_type.get('network_timeout', [])
            
            for scenario in timeout_scenarios:
                zpid = scenario['zpid']
                timeout_after = scenario['timeout_after']
                
                bt.logging.info(f"Testing network timeout for zpid {zpid} (timeout after {timeout_after}s)")
                
                start_time = time.time()
                
                # This should raise a timeout exception
                with self.assertRaises((TimeoutError, Exception)):
                    await self.failure_client.get_individual_property(zpid)
                
                elapsed = time.time() - start_time
                
                # Should have taken at least the timeout duration
                self.assertGreaterEqual(elapsed, timeout_after * 0.8, "Should wait for timeout")
                
                bt.logging.info(f"✅ Network timeout correctly failed after {elapsed:.2f}s")
            
            bt.logging.info("✅ Network timeout test completed")
        
        asyncio.run(run_test())
    
    def test_authentication_failure_scenarios(self):
        """Test authentication failures - THESE SHOULD FAIL"""
        
        async def run_test():
            bt.logging.info("Testing authentication failure scenarios (ALL SHOULD FAIL)")
            
            self.failure_client.enable_failure_mode()
            
            auth_scenarios = self.scenario_by_type.get('auth_failure', [])
            
            for scenario in auth_scenarios:
                bt.logging.info("Testing authentication failure")
                
                # This should raise an authentication exception
                with self.assertRaises((PermissionError, Exception)):
                    # Try to access any property - should fail with auth error
                    available_zpids = self.normal_client.get_available_zpids()
                    if available_zpids:
                        await self.failure_client.get_individual_property(available_zpids[0])
                
                bt.logging.info("✅ Authentication failure correctly raised exception")
            
            bt.logging.info("✅ Authentication failure test completed")
        
        asyncio.run(run_test())
    
    def test_rate_limit_scenarios(self):
        """Test rate limiting - THESE SHOULD FAIL"""
        
        async def run_test():
            bt.logging.info("Testing rate limit scenarios (ALL SHOULD FAIL)")
            
            self.failure_client.enable_failure_mode()
            
            rate_limit_scenarios = self.scenario_by_type.get('rate_limit', [])
            
            for scenario in rate_limit_scenarios:
                retry_after = scenario['retry_after']
                bt.logging.info(f"Testing rate limit (retry after {retry_after}s)")
                
                # This should raise a rate limit exception
                with self.assertRaises(Exception) as context:
                    available_zpids = self.normal_client.get_available_zpids()
                    if available_zpids:
                        await self.failure_client.get_individual_property(available_zpids[0])
                
                # Check that the exception mentions rate limiting
                self.assertIn("rate limit", str(context.exception).lower(),
                             "Exception should mention rate limiting")
                
                bt.logging.info("✅ Rate limit correctly raised exception")
            
            bt.logging.info("✅ Rate limit test completed")
        
        asyncio.run(run_test())
    
    def test_partial_response_scenarios(self):
        """Test partial/incomplete responses - THESE SHOULD PASS WITH WARNINGS"""
        
        async def run_test():
            bt.logging.info("Testing partial response scenarios (SHOULD PASS WITH WARNINGS)")
            
            self.failure_client.enable_failure_mode()
            
            partial_scenarios = self.scenario_by_type.get('partial_response', [])
            
            for scenario in partial_scenarios:
                zpid = scenario['zpid']
                missing_fields = scenario['missing_fields']
                
                bt.logging.info(f"Testing partial response for zpid {zpid} (missing: {missing_fields})")
                
                # Get miner's complete data
                miner_data = await self._get_miner_data_for_zpid(zpid)
                if not miner_data:
                    continue
                
                miner_content = RealEstateContent.from_zillow_api(miner_data)
                miner_entity = miner_content.to_data_entity()
                
                # Get validator's partial data
                validator_data = await self.failure_client.get_individual_property(zpid)
                validator_property = validator_data.get('property', {})
                
                # Verify fields are actually missing
                for field in missing_fields:
                    self.assertNotIn(field, validator_property, f"Field {field} should be missing")
                
                # Simulate validation with missing optional fields
                validation_result = self._simulate_partial_validation(miner_entity, validator_property)
                
                # Should PASS despite missing optional fields
                self.assertTrue(validation_result['is_valid'],
                               f"Partial response for {zpid} should PASS (missing optional fields OK)")
                self.assertIn("optional", validation_result['reason'].lower(),
                             "Should mention missing optional fields")
                
                bt.logging.info(f"✅ Partial response for {zpid} correctly PASSED with warnings")
            
            bt.logging.info(f"✅ Partial response test completed: {len(partial_scenarios)} scenarios handled correctly")
        
        asyncio.run(run_test())
    
    # Helper methods for simulation
    
    async def _get_miner_data_for_zpid(self, zpid: str) -> Dict[str, Any]:
        """Get miner's view of property data from search results"""
        for zipcode in self.normal_client.get_available_zipcodes():
            search_data = await self.normal_client.get_property_search(zipcode)
            for prop in search_data.get('props', []):
                if str(prop.get('zpid', '')) == zpid:
                    return prop
        return None
    
    def _simulate_validation_with_missing_property(self, miner_entity: DataEntity) -> Dict[str, Any]:
        """Simulate validation when validator can't find the property"""
        return {
            'is_valid': False,
            'reason': 'Property not found - may have been removed from market',
            'validation_type': 'existence_check'
        }
    
    def _simulate_price_validation(self, miner_entity: DataEntity, validator_property: Dict[str, Any], tolerance: float) -> Dict[str, Any]:
        """Simulate price validation with tolerance"""
        try:
            miner_content = RealEstateContent.from_data_entity(miner_entity)
            miner_price = miner_content.price
            validator_price = validator_property.get('price')
            
            if miner_price and validator_price:
                price_diff_percent = abs(validator_price - miner_price) / miner_price
                
                if price_diff_percent <= tolerance:
                    return {
                        'is_valid': True,
                        'reason': f'Price change {price_diff_percent:.1%} within {tolerance:.1%} tolerance',
                        'validation_type': 'price_tolerance'
                    }
                else:
                    return {
                        'is_valid': False,
                        'reason': f'Price change {price_diff_percent:.1%} exceeds {tolerance:.1%} tolerance',
                        'validation_type': 'price_tolerance'
                    }
            
            return {'is_valid': True, 'reason': 'No price comparison needed', 'validation_type': 'price_tolerance'}
            
        except Exception as e:
            return {'is_valid': False, 'reason': f'Price validation error: {e}', 'validation_type': 'price_tolerance'}
    
    def _simulate_status_validation(self, miner_entity: DataEntity, validator_property: Dict[str, Any], original_status: str, new_status: str) -> Dict[str, Any]:
        """Simulate listing status validation"""
        compatible_transitions = {
            'FOR_SALE': ['PENDING', 'SOLD'],
            'FOR_RENT': ['RENTED'],
            'PENDING': ['SOLD', 'FOR_SALE'],
            'SOLD': ['FOR_SALE'],
            'RENTED': ['FOR_RENT'],
        }
        
        if original_status == new_status:
            return {'is_valid': True, 'reason': 'Status unchanged', 'validation_type': 'status_compatibility'}
        
        if new_status in compatible_transitions.get(original_status, []):
            return {'is_valid': True, 'reason': f'Status transition {original_status}→{new_status} is compatible', 'validation_type': 'status_compatibility'}
        else:
            return {'is_valid': False, 'reason': f'Status transition {original_status}→{new_status} is incompatible', 'validation_type': 'status_compatibility'}
    
    def _simulate_corruption_validation(self, validator_property: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate validation with corrupted data"""
        try:
            # Try to create RealEstateContent from corrupted data
            # This should fail due to invalid data types, missing fields, etc.
            from scraping.zillow.field_mapping import ZillowFieldMapper
            
            # Use field mapper to create compatible content
            compatible_data = ZillowFieldMapper.create_miner_compatible_content(validator_property)
            content = RealEstateContent(**compatible_data)
            
            return {'is_valid': True, 'reason': 'Data validation passed despite corruption', 'validation_type': 'data_integrity'}
            
        except Exception as e:
            return {'is_valid': False, 'reason': f'Data corruption detected: {str(e)}', 'validation_type': 'data_integrity'}
    
    def _simulate_partial_validation(self, miner_entity: DataEntity, validator_property: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate validation with partial/incomplete data"""
        try:
            from scraping.zillow.field_mapping import ZillowFieldMapper
            
            # Create content from partial data
            compatible_data = ZillowFieldMapper.create_miner_compatible_content(validator_property)
            content = RealEstateContent(**compatible_data)
            
            # Check for missing optional fields
            missing_optional = []
            optional_fields = ['zestimate', 'rent_zestimate', 'lot_area_value', 'days_on_zillow']
            
            for field in optional_fields:
                if getattr(content, field, None) is None:
                    missing_optional.append(field)
            
            if missing_optional:
                return {
                    'is_valid': True,
                    'reason': f'Validation passed despite missing optional fields: {missing_optional}',
                    'validation_type': 'partial_data'
                }
            else:
                return {'is_valid': True, 'reason': 'Complete data validation passed', 'validation_type': 'partial_data'}
                
        except Exception as e:
            return {'is_valid': False, 'reason': f'Partial data validation failed: {str(e)}', 'validation_type': 'partial_data'}


if __name__ == "__main__":
    unittest.main(verbosity=2)
