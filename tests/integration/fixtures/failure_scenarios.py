"""
Failure Scenario Test Data Generator

Creates realistic failure scenarios for comprehensive testing including
property not found, data mismatches, network failures, and authentication errors.
"""

import json
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, patch
import copy

from scraping.zillow.model import RealEstateContent
from common.data import DataEntity, DataSource, DataLabel
from tests.mocks.zillow_api_client import MockZillowAPIClient


class FailureScenarioGenerator:
    """Generates various failure scenarios for testing"""
    
    def __init__(self, mock_client: MockZillowAPIClient):
        self.mock_client = mock_client
        self.original_data = {}
        self._load_original_data()
    
    def _load_original_data(self):
        """Load original property data for modification"""
        for zpid in list(self.mock_client.get_available_zpids())[:15]:  # Use first 15 for testing
            # Get search data first (which has prices)
            search_data = None
            for zipcode in self.mock_client.get_available_zipcodes():
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        zipcode_data = loop.run_until_complete(
                            self.mock_client.get_property_search(zipcode)
                        )
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        zipcode_data = loop.run_until_complete(
                            self.mock_client.get_property_search(zipcode)
                        )
                        loop.close()
                    
                    for prop in zipcode_data.get('props', []):
                        if str(prop.get('zpid', '')) == zpid:
                            search_data = prop
                            break
                    if search_data:
                        break
                except:
                    continue
            
            if search_data:
                # Store search data as our "property" data for scenarios
                self.original_data[zpid] = {'property': search_data}
    
    def create_property_not_found_scenario(self, zpid: str) -> Dict[str, Any]:
        """Create a 404 property not found scenario"""
        return {
            'scenario_type': 'property_not_found',
            'zpid': zpid,
            'error_code': 404,
            'error_message': 'Property not found',
            'response': None,
            'expected_validation_result': False,
            'expected_reason': 'Property no longer exists'
        }
    
    def create_price_change_scenario(self, zpid: str, price_change_percent: float = 0.1) -> Dict[str, Any]:
        """Create a scenario where property price has changed"""
        if zpid not in self.original_data:
            return None
        
        original = copy.deepcopy(self.original_data[zpid])
        property_info = original.get('property', {})
        
        # Check both 'price' and direct price field
        original_price = property_info.get('price') or property_info.get('priceForHDP')
        if not original_price:
            # If no price in property, check if it's in the search data format
            original_price = property_info.get('price') or 300000  # Use default price for testing
        
        if original_price:
            # Change price by the specified percentage
            new_price = int(original_price * (1 + price_change_percent))
            property_info['price'] = new_price
            
            return {
                'scenario_type': 'price_change',
                'zpid': zpid,
                'original_price': original_price,
                'new_price': new_price,
                'change_percent': price_change_percent,
                'response': original,
                'expected_validation_result': True,  # Should pass with tolerance
                'expected_reason': 'Price change within tolerance'
            }
        
        return None
    
    def create_status_change_scenario(self, zpid: str) -> Dict[str, Any]:
        """Create a scenario where listing status has changed"""
        if zpid not in self.original_data:
            return None
        
        original = copy.deepcopy(self.original_data[zpid])
        property_info = original.get('property', {})
        
        # Define status transitions
        status_transitions = {
            'FOR_SALE': 'SOLD',
            'FOR_RENT': 'RENTED',
            'PENDING': 'SOLD',
            'SOLD': 'FOR_SALE',  # Back on market
        }
        
        current_status = property_info.get('listingStatus', 'FOR_SALE')
        new_status = status_transitions.get(current_status, 'SOLD')
        property_info['listingStatus'] = new_status
        
        return {
            'scenario_type': 'status_change',
            'zpid': zpid,
            'original_status': current_status,
            'new_status': new_status,
            'response': original,
            'expected_validation_result': True,  # Compatible transitions should pass
            'expected_reason': 'Status change is compatible'
        }
    
    def create_data_corruption_scenario(self, zpid: str) -> Dict[str, Any]:
        """Create a scenario with corrupted/malformed data"""
        if zpid not in self.original_data:
            return None
        
        original = copy.deepcopy(self.original_data[zpid])
        property_info = original.get('property', {})
        
        # Introduce various types of corruption
        corruption_types = [
            lambda d: d.update({'price': 'invalid_price'}),  # Invalid data type
            lambda d: d.pop('zpid', None),  # Missing critical field
            lambda d: d.update({'latitude': 999}),  # Invalid coordinate
            lambda d: d.update({'bathrooms': -1}),  # Invalid value
        ]
        
        corruption_type = random.choice(corruption_types)
        corruption_type(property_info)
        
        return {
            'scenario_type': 'data_corruption',
            'zpid': zpid,
            'corruption_applied': True,
            'response': original,
            'expected_validation_result': False,
            'expected_reason': 'Data validation failed due to corruption'
        }
    
    def create_network_timeout_scenario(self, zpid: str) -> Dict[str, Any]:
        """Create a network timeout scenario"""
        return {
            'scenario_type': 'network_timeout',
            'zpid': zpid,
            'timeout_after': 5.0,  # seconds
            'response': None,
            'expected_validation_result': False,
            'expected_reason': 'Network timeout during validation'
        }
    
    def create_partial_response_scenario(self, zpid: str) -> Dict[str, Any]:
        """Create a scenario with incomplete/partial response"""
        if zpid not in self.original_data:
            return None
        
        original = copy.deepcopy(self.original_data[zpid])
        property_info = original.get('property', {})
        
        # Remove optional fields to simulate partial response
        optional_fields = ['zestimate', 'rentZestimate', 'lotAreaValue', 'daysOnZillow']
        for field in optional_fields:
            property_info.pop(field, None)
        
        return {
            'scenario_type': 'partial_response',
            'zpid': zpid,
            'missing_fields': optional_fields,
            'response': original,
            'expected_validation_result': True,  # Should still pass with missing optional fields
            'expected_reason': 'Validation passed despite missing optional fields'
        }
    
    def create_authentication_failure_scenario(self) -> Dict[str, Any]:
        """Create an authentication failure scenario"""
        return {
            'scenario_type': 'auth_failure',
            'error_code': 401,
            'error_message': 'Invalid API key or signature',
            'response': None,
            'expected_validation_result': False,
            'expected_reason': 'Authentication failed'
        }
    
    def create_rate_limit_scenario(self) -> Dict[str, Any]:
        """Create a rate limiting scenario"""
        return {
            'scenario_type': 'rate_limit',
            'error_code': 429,
            'error_message': 'Rate limit exceeded',
            'retry_after': 60,  # seconds
            'response': None,
            'expected_validation_result': False,
            'expected_reason': 'Rate limit exceeded'
        }
    
    def generate_comprehensive_failure_suite(self) -> List[Dict[str, Any]]:
        """Generate a comprehensive suite of failure scenarios"""
        scenarios = []
        available_zpids = list(self.original_data.keys())
        
        if not available_zpids:
            return scenarios
        
        # Property not found scenarios (2 properties)
        for zpid in available_zpids[:2]:
            scenario = self.create_property_not_found_scenario(zpid)
            if scenario:
                scenarios.append(scenario)
        
        # Price change scenarios (3 properties with different change amounts)
        price_changes = [0.05, 0.15, 0.25]  # 5%, 15%, 25%
        for i, change_percent in enumerate(price_changes):
            if i < len(available_zpids):
                zpid = available_zpids[i + 2]  # Offset to avoid overlap
                scenario = self.create_price_change_scenario(zpid, change_percent)
                if scenario:
                    scenarios.append(scenario)
        
        # Status change scenarios (2 properties)
        for zpid in available_zpids[5:7]:
            scenario = self.create_status_change_scenario(zpid)
            if scenario:
                scenarios.append(scenario)
        
        # Data corruption scenarios (2 properties)
        for zpid in available_zpids[7:9]:
            scenario = self.create_data_corruption_scenario(zpid)
            if scenario:
                scenarios.append(scenario)
        
        # Partial response scenario (1 property)
        if len(available_zpids) > 9:
            scenario = self.create_partial_response_scenario(available_zpids[9])
            if scenario:
                scenarios.append(scenario)
        
        # Network and auth scenarios (use different zpids to avoid conflicts)
        if len(available_zpids) > 10:
            scenarios.append(self.create_network_timeout_scenario(available_zpids[10]))
        
        scenarios.extend([
            self.create_authentication_failure_scenario(),
            self.create_rate_limit_scenario()
        ])
        
        return scenarios


class MockFailureZillowClient(MockZillowAPIClient):
    """Extended mock client that can simulate failures"""
    
    def __init__(self, data_dir: str, failure_scenarios: List[Dict[str, Any]] = None):
        super().__init__(data_dir)
        # Group scenarios by zpid, handling multiple scenarios per zpid
        self.failure_scenarios = {}
        for s in failure_scenarios or []:
            if 'zpid' in s:
                zpid = s['zpid']
                if zpid not in self.failure_scenarios:
                    self.failure_scenarios[zpid] = []
                self.failure_scenarios[zpid].append(s)
        
        self.global_failures = [s for s in failure_scenarios or [] if 'zpid' not in s]
        self.failure_mode = False
    
    def enable_failure_mode(self):
        """Enable failure mode for testing"""
        self.failure_mode = True
    
    def disable_failure_mode(self):
        """Disable failure mode"""
        self.failure_mode = False
    
    async def get_individual_property(self, zpid: str) -> Optional[Dict[str, Any]]:
        """Override to simulate failures"""
        if not self.failure_mode:
            return await super().get_individual_property(zpid)
        
        # Check for property-specific failures
        if zpid in self.failure_scenarios:
            scenarios = self.failure_scenarios[zpid]
            
            # Use the first scenario for this zpid
            scenario = scenarios[0]
            
            if scenario['scenario_type'] == 'property_not_found':
                return None
            elif scenario['scenario_type'] == 'network_timeout':
                import asyncio
                await asyncio.sleep(scenario['timeout_after'])
                raise TimeoutError("Network timeout")
            else:
                return scenario.get('response')
        
        # Check for global failures
        for scenario in self.global_failures:
            if scenario['scenario_type'] == 'auth_failure':
                raise PermissionError("Authentication failed")
            elif scenario['scenario_type'] == 'rate_limit':
                raise Exception(f"Rate limit exceeded. Retry after {scenario['retry_after']} seconds")
        
        # Default to normal behavior
        return await super().get_individual_property(zpid)


def create_failure_test_client(data_dir: str = "mocked_data") -> Tuple[MockFailureZillowClient, List[Dict[str, Any]]]:
    """Create a mock client with comprehensive failure scenarios"""
    # First create a regular client to load data
    regular_client = MockZillowAPIClient(data_dir)
    
    # Generate failure scenarios
    scenario_generator = FailureScenarioGenerator(regular_client)
    scenarios = scenario_generator.generate_comprehensive_failure_suite()
    
    # Create failure client
    failure_client = MockFailureZillowClient(data_dir, scenarios)
    
    return failure_client, scenarios


# Convenience functions for testing
def get_property_not_found_zpids() -> List[str]:
    """Get ZPIDs that should return 404 in failure mode"""
    _, scenarios = create_failure_test_client()
    return [s['zpid'] for s in scenarios if s['scenario_type'] == 'property_not_found']

def get_price_change_zpids() -> List[str]:
    """Get ZPIDs with price changes in failure mode"""
    _, scenarios = create_failure_test_client()
    return [s['zpid'] for s in scenarios if s['scenario_type'] == 'price_change']

def get_status_change_zpids() -> List[str]:
    """Get ZPIDs with status changes in failure mode"""
    _, scenarios = create_failure_test_client()
    return [s['zpid'] for s in scenarios if s['scenario_type'] == 'status_change']
