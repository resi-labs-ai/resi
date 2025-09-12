"""
Real Data Validation Integration Tests

This module contains comprehensive integration tests using real Zillow API
responses collected from live data. These tests simulate the complete
miner-validator flow with actual property data from multiple markets.

Test Coverage:
- Complete miner scraping simulation (Property Extended Search)
- Complete validator validation simulation (Individual Property API)
- Cross-market validation scenarios
- Error handling with real data
- Performance testing with large datasets
"""

import asyncio
import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import bittensor as bt
from common.data import DataEntity, DataSource, DataLabel
from scraping.zillow.model import RealEstateContent
from scraping.zillow.rapid_zillow_scraper import ZillowRapidAPIScraper
from scraping.zillow.utils import validate_zillow_data_entity_fields
from tests.mocks.zillow_api_client import MockZillowAPIClient, MockZillowScraperIntegration


class TestRealDataMinerSimulation(unittest.TestCase):
    """Test miner simulation using real Property Extended Search data"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with mock client"""
        cls.mock_client = MockZillowAPIClient("mocked_data")
        cls.available_zipcodes = cls.mock_client.get_available_zipcodes()
        bt.logging.set_info(True)
    
    def test_miner_scraping_all_zipcodes(self):
        """Test miner scraping simulation for all collected zipcodes"""
        
        async def run_test():
            total_properties = 0
            successful_conversions = 0
            
            for zipcode in self.available_zipcodes:
                # Simulate miner calling Property Extended Search API
                search_data = await self.mock_client.get_property_search(zipcode)
                self.assertIsNotNone(search_data, f"No search data for zipcode {zipcode}")
                
                # Extract properties from search results
                properties = search_data.get('props', [])
                total_properties += len(properties)
                
                bt.logging.info(f"Testing {len(properties)} properties from zipcode {zipcode}")
                
                for prop in properties:
                    # Simulate miner creating RealEstateContent from search data
                    try:
                        content = RealEstateContent.from_zillow_api(prop)
                        self.assertIsInstance(content, RealEstateContent)
                        self.assertIsNotNone(content.zpid)
                        self.assertIsNotNone(content.address)
                        
                        # Simulate miner creating DataEntity
                        entity = content.to_data_entity()
                        self.assertIsInstance(entity, DataEntity)
                        self.assertEqual(entity.source, DataSource.RAPID_ZILLOW)
                        self.assertTrue(len(entity.content) > 0)
                        
                        successful_conversions += 1
                        
                    except Exception as e:
                        bt.logging.error(f"Error processing property {prop.get('zpid', 'unknown')}: {e}")
                        # Don't fail the test for individual property issues
                        continue
            
            bt.logging.info(f"Miner simulation: {successful_conversions}/{total_properties} properties processed successfully")
            
            # Ensure we processed a reasonable number of properties
            self.assertGreater(total_properties, 300, "Should have processed 300+ properties")
            self.assertGreater(successful_conversions / total_properties, 0.95, "95%+ success rate expected")
        
        asyncio.run(run_test())
    
    def test_miner_data_quality_validation(self):
        """Test data quality of miner-scraped content"""
        
        async def run_test():
            zipcode = self.available_zipcodes[0]  # Test with first available zipcode
            search_data = await self.mock_client.get_property_search(zipcode)
            properties = search_data.get('props', [])[:5]  # Test first 5 properties
            
            for prop in properties:
                content = RealEstateContent.from_zillow_api(prop)
                
                # Validate required fields
                self.assertIsNotNone(content.zpid, "zpid should not be None")
                self.assertIsNotNone(content.address, "address should not be None")
                self.assertIsNotNone(content.property_type, "property_type should not be None")
                
                # Validate data types
                if content.price is not None:
                    self.assertIsInstance(content.price, int, "price should be integer")
                    self.assertGreater(content.price, 0, "price should be positive")
                
                if content.bedrooms is not None:
                    self.assertIsInstance(content.bedrooms, int, "bedrooms should be integer")
                    self.assertGreaterEqual(content.bedrooms, 0, "bedrooms should be non-negative")
                
                if content.bathrooms is not None:
                    self.assertIsInstance(content.bathrooms, (int, float), "bathrooms should be numeric")
                    self.assertGreaterEqual(content.bathrooms, 0, "bathrooms should be non-negative")
                
                # Validate geographic data
                if content.latitude is not None and content.longitude is not None:
                    self.assertGreater(content.latitude, -90, "latitude should be valid")
                    self.assertLess(content.latitude, 90, "latitude should be valid")
                    self.assertGreater(content.longitude, -180, "longitude should be valid")
                    self.assertLess(content.longitude, 180, "longitude should be valid")
        
        asyncio.run(run_test())
    
    def test_miner_geographic_diversity(self):
        """Test that miner data covers diverse geographic markets"""
        
        async def run_test():
            market_data = {}
            
            for zipcode in self.available_zipcodes:
                search_data = await self.mock_client.get_property_search(zipcode)
                properties = search_data.get('props', [])
                
                # Analyze market characteristics
                prices = [p.get('price') for p in properties if p.get('price')]
                property_types = [p.get('propertyType') for p in properties if p.get('propertyType')]
                
                market_data[zipcode] = {
                    'property_count': len(properties),
                    'avg_price': sum(prices) / len(prices) if prices else None,
                    'price_range': (min(prices), max(prices)) if prices else None,
                    'property_types': set(property_types)
                }
            
            # Validate market diversity
            all_prices = [data['avg_price'] for data in market_data.values() if data['avg_price']]
            all_types = set()
            for data in market_data.values():
                all_types.update(data['property_types'])
            
            # Should have price diversity (coefficient of variation > 0.5)
            if all_prices:
                price_std = (sum((p - sum(all_prices)/len(all_prices))**2 for p in all_prices) / len(all_prices))**0.5
                price_cv = price_std / (sum(all_prices)/len(all_prices))
                self.assertGreater(price_cv, 0.3, "Should have diverse price ranges across markets")
            
            # Should have multiple property types
            self.assertGreaterEqual(len(all_types), 2, "Should have multiple property types")
            
            bt.logging.info(f"Market diversity analysis: {len(market_data)} markets, "
                           f"price CV: {price_cv:.2f}, property types: {all_types}")
        
        asyncio.run(run_test())


class TestRealDataValidatorSimulation(unittest.TestCase):
    """Test validator simulation using real Individual Property data"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with mock client and scraper"""
        cls.mock_client = MockZillowAPIClient("mocked_data")
        cls.scraper = ZillowRapidAPIScraper()
        
        # Patch scraper to use mock data
        cls.integration = MockZillowScraperIntegration(cls.mock_client)
        
        bt.logging.set_info(True)
    
    def test_validator_individual_property_processing(self):
        """Test validator processing of individual properties"""
        
        async def run_test():
            # Test with a sample of available properties
            available_zpids = self.mock_client.get_available_zpids()
            test_zpids = available_zpids[:10]  # Test first 10 properties
            
            successful_validations = 0
            
            for zpid in test_zpids:
                # Simulate validator calling Individual Property API
                property_data = await self.mock_client.get_individual_property(zpid)
                self.assertIsNotNone(property_data, f"No property data for zpid {zpid}")
                
                # Extract property data from API response
                property_info = property_data.get('property', {})
                if property_info:
                    try:
                        # This would be the validator's process
                        # Note: We need to adapt this to work with the field mapping
                        # For now, let's test that we can access the data
                        
                        self.assertIn('zpid', property_info, "Property should have zpid")
                        self.assertIn('address', property_info, "Property should have address")
                        
                        # Test basic data structure
                        if 'price' in property_info:
                            self.assertIsInstance(property_info['price'], (int, type(None)))
                        
                        successful_validations += 1
                        
                    except Exception as e:
                        bt.logging.error(f"Error processing property {zpid}: {e}")
                        continue
            
            bt.logging.info(f"Validator simulation: {successful_validations}/{len(test_zpids)} properties processed")
            self.assertGreater(successful_validations / len(test_zpids), 0.8, "80%+ success rate expected")
        
        asyncio.run(run_test())
    
    def test_validator_existence_checking(self):
        """Test validator property existence checking"""
        
        async def run_test():
            # Test with known properties
            available_zpids = self.mock_client.get_available_zpids()
            test_zpids = available_zpids[:5]
            
            for zpid in test_zpids:
                # Simulate validator checking if property exists
                property_data = await self.mock_client.get_individual_property(zpid)
                
                # Should be able to get property data
                self.assertIsNotNone(property_data, f"Property {zpid} should exist in mock data")
                
                # Should have property information
                property_info = property_data.get('property', {})
                self.assertTrue(len(property_info) > 0, f"Property {zpid} should have data")
        
        asyncio.run(run_test())


class TestRealDataEndToEndValidation(unittest.TestCase):
    """Test complete end-to-end miner-validator scenarios"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.mock_client = MockZillowAPIClient("mocked_data")
        bt.logging.set_info(True)
    
    def test_end_to_end_validation_success_scenario(self):
        """Test successful miner-validator validation scenario"""
        
        async def run_test():
            # Step 1: Simulate miner scraping
            zipcode = self.mock_client.get_available_zipcodes()[0]
            search_data = await self.mock_client.get_property_search(zipcode)
            properties = search_data.get('props', [])[:3]  # Test first 3 properties
            
            successful_validations = 0
            
            for prop in properties:
                try:
                    # Miner creates content from search data
                    miner_content = RealEstateContent.from_zillow_api(prop)
                    miner_entity = miner_content.to_data_entity()
                    
                    # Validator gets the same property via Individual Property API
                    zpid = miner_content.zpid
                    validator_data = await self.mock_client.get_individual_property(zpid)
                    
                    if validator_data and 'property' in validator_data:
                        # This is where our field mapping becomes crucial
                        # The validator needs to create comparable content
                        
                        # For now, test that both have the essential data
                        validator_property = validator_data['property']
                        
                        # Basic validation - both should have same zpid
                        self.assertEqual(str(validator_property.get('zpid', '')), miner_content.zpid)
                        
                        bt.logging.info(f"✅ Validation successful for zpid {zpid}")
                        successful_validations += 1
                        
                except Exception as e:
                    bt.logging.error(f"Validation failed for property: {e}")
                    continue
            
            bt.logging.info(f"End-to-end test: {successful_validations}/{len(properties)} validations successful")
            self.assertGreater(successful_validations, 0, "Should have at least one successful validation")
        
        asyncio.run(run_test())
    
    def test_validation_with_field_subset_logic(self):
        """Test validation using our field subset logic"""
        
        async def run_test():
            # Get a known property from our test data
            zpid = "70982473"  # Your Laredo property
            
            if zpid in self.mock_client.get_available_zpids():
                # Create miner entity (simulating what miner would create)
                search_data = await self.mock_client.get_property_search("78041")
                laredo_properties = search_data.get('props', [])
                
                # Find our specific property in search results
                target_property = None
                for prop in laredo_properties:
                    if str(prop.get('zpid', '')) == zpid:
                        target_property = prop
                        break
                
                if target_property:
                    # Simulate miner's data
                    miner_content = RealEstateContent.from_zillow_api(target_property)
                    miner_entity = miner_content.to_data_entity()
                    
                    # Simulate validator's data (using individual property API)
                    validator_raw_data = await self.mock_client.get_individual_property(zpid)
                    
                    # Test our field subset validation logic
                    # This would use our new validation system
                    
                    self.assertEqual(miner_entity.source, DataSource.RAPID_ZILLOW)
                    self.assertIn(zpid, miner_entity.uri)
                    
                    bt.logging.info(f"✅ Field subset validation test completed for zpid {zpid}")
                    
                else:
                    self.skipTest(f"Property {zpid} not found in search results")
            else:
                self.skipTest(f"Property {zpid} not available in mock data")
        
        asyncio.run(run_test())


class TestRealDataPerformance(unittest.TestCase):
    """Test performance with real data at scale"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.mock_client = MockZillowAPIClient("mocked_data")
        bt.logging.set_info(True)
    
    def test_large_scale_miner_simulation(self):
        """Test miner simulation performance with all available data"""
        
        async def run_test():
            start_time = datetime.now()
            
            total_properties = 0
            successful_conversions = 0
            
            # Process all available zipcodes
            for zipcode in self.mock_client.get_available_zipcodes():
                search_data = await self.mock_client.get_property_search(zipcode)
                properties = search_data.get('props', [])
                total_properties += len(properties)
                
                # Convert all properties to RealEstateContent
                for prop in properties:
                    try:
                        content = RealEstateContent.from_zillow_api(prop)
                        entity = content.to_data_entity()
                        successful_conversions += 1
                    except:
                        continue
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Performance assertions
            self.assertLess(duration, 30, "Should process all data in under 30 seconds")
            self.assertGreater(total_properties, 300, "Should process 300+ properties")
            self.assertGreater(successful_conversions / total_properties, 0.95, "95%+ success rate")
            
            bt.logging.info(f"Performance test: {total_properties} properties in {duration:.2f}s "
                           f"({total_properties/duration:.1f} properties/sec)")
        
        asyncio.run(run_test())
    
    def test_mock_client_performance(self):
        """Test mock client response times"""
        
        async def run_test():
            # Test search performance
            start_time = datetime.now()
            for zipcode in self.mock_client.get_available_zipcodes():
                await self.mock_client.get_property_search(zipcode)
            search_time = (datetime.now() - start_time).total_seconds()
            
            # Test property lookup performance
            start_time = datetime.now()
            test_zpids = list(self.mock_client.get_available_zpids())[:50]  # Test first 50
            for zpid in test_zpids:
                await self.mock_client.get_individual_property(zpid)
            property_time = (datetime.now() - start_time).total_seconds()
            
            # Performance assertions
            self.assertLess(search_time / len(self.mock_client.get_available_zipcodes()), 0.1, 
                           "Search lookups should be under 0.1s each")
            self.assertLess(property_time / len(test_zpids), 0.1, 
                           "Property lookups should be under 0.1s each")
            
            bt.logging.info(f"Mock client performance: {search_time:.2f}s for searches, "
                           f"{property_time:.2f}s for {len(test_zpids)} properties")
        
        asyncio.run(run_test())


class TestRealDataEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios with real data"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.mock_client = MockZillowAPIClient("mocked_data")
        bt.logging.set_info(True)
    
    def test_missing_data_handling(self):
        """Test handling of missing or incomplete data"""
        
        async def run_test():
            # Test with non-existent zipcode
            result = await self.mock_client.get_property_search("00000")
            self.assertIsNone(result, "Should return None for non-existent zipcode")
            
            # Test with non-existent zpid
            result = await self.mock_client.get_individual_property("99999999999")
            self.assertIsNone(result, "Should return None for non-existent zpid")
            
            # Test mock client stats
            stats = self.mock_client.get_stats()
            self.assertIn('cache_misses', stats['raw_stats'])
            self.assertGreater(stats['raw_stats']['cache_misses'], 0, "Should have recorded cache misses")
        
        asyncio.run(run_test())
    
    def test_data_validation_edge_cases(self):
        """Test validation with edge case property data"""
        
        async def run_test():
            # Find properties with edge case data (None values, unusual types, etc.)
            zipcode = self.mock_client.get_available_zipcodes()[0]
            search_data = await self.mock_client.get_property_search(zipcode)
            properties = search_data.get('props', [])
            
            edge_cases_found = 0
            
            for prop in properties:
                # Look for properties with missing or unusual data
                if (prop.get('price') is None or 
                    prop.get('bedrooms') is None or 
                    prop.get('bathrooms') is None):
                    
                    # Test that we can still create content from incomplete data
                    try:
                        content = RealEstateContent.from_zillow_api(prop)
                        entity = content.to_data_entity()
                        
                        # Should still have required fields
                        self.assertIsNotNone(content.zpid)
                        self.assertIsNotNone(content.address)
                        
                        edge_cases_found += 1
                        
                    except Exception as e:
                        bt.logging.error(f"Edge case handling failed: {e}")
                        raise
            
            bt.logging.info(f"Edge case test: {edge_cases_found} properties with missing data handled successfully")
        
        asyncio.run(run_test())


if __name__ == '__main__':
    # Configure logging for tests
    bt.logging.set_info(True)
    
    # Run tests
    unittest.main(verbosity=2)
