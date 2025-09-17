#!/usr/bin/env python3
"""
Simple test script for the data model upgrade.

This script tests the core data model and field mapping changes without requiring
external dependencies like httpx.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scraping.zillow.model import RealEstateContent
from scraping.zillow.field_mapping import ZillowFieldMapper


class DataModelUpgradeTest:
    """Test the data model upgrade functionality"""
    
    def __init__(self):
        self.mocked_data_dir = project_root / "mocked_data"
        self.individual_properties_dir = self.mocked_data_dir / "individual_properties"
        self.search_results_dir = self.mocked_data_dir / "property_extended_search"
        
        # Test statistics
        self.stats = {
            'properties_tested': 0,
            'successful_conversions': 0,
            'field_count_basic': 0,
            'field_count_full': 0,
            'errors': []
        }
    
    def run_tests(self):
        """Run all data model tests"""
        print("🚀 Starting Data Model Upgrade Tests")
        
        try:
            # Test 1: Field mapping functionality
            self._test_field_mapping()
            
            # Test 2: Data model expansion
            self._test_data_model_expansion()
            
            # Test 3: Backwards compatibility
            self._test_backwards_compatibility()
            
            # Print results
            self._print_results()
            
        except Exception as e:
            print(f"❌ Test suite failed: {str(e)}")
            self.stats['errors'].append(f"Test suite error: {str(e)}")
    
    def _test_field_mapping(self):
        """Test the field mapping functionality"""
        print("\n🗺️  Test 1: Field Mapping Functionality")
        
        # Load sample individual property data
        sample_files = list(self.individual_properties_dir.glob("*.json"))
        if not sample_files:
            raise Exception("No individual property files found for testing")
        
        sample_file = sample_files[0]
        print(f"Testing with: {sample_file.name}")
        
        with open(sample_file, 'r') as f:
            individual_data = json.load(f)
        
        try:
            # Test full property content creation
            full_content_data = ZillowFieldMapper.create_full_property_content(individual_data)
            full_field_count = len([k for k, v in full_content_data.items() if v is not None])
            
            print(f"Full property content: {full_field_count} populated fields")
            self.stats['field_count_full'] = full_field_count
            
            # Test backwards compatible miner content creation
            miner_content_data = ZillowFieldMapper.create_miner_compatible_content(individual_data)
            miner_field_count = len([k for k, v in miner_content_data.items() if v is not None])
            
            print(f"Miner compatible content: {miner_field_count} populated fields")
            self.stats['field_count_basic'] = miner_field_count
            
            improvement = full_field_count - miner_field_count
            print(f"✅ Field mapping upgrade: +{improvement} additional fields")
            
            # Test field sets
            miner_fields = len(ZillowFieldMapper.MINER_AVAILABLE_FIELDS)
            individual_fields = len(ZillowFieldMapper.INDIVIDUAL_PROPERTY_FIELDS)
            validation_configs = len(ZillowFieldMapper.FIELD_VALIDATION_CONFIG)
            
            print(f"Field sets: {miner_fields} basic → {individual_fields} full")
            print(f"Validation configurations: {validation_configs}")
            
        except Exception as e:
            print(f"❌ Field mapping test failed: {str(e)}")
            self.stats['errors'].append(f"Field mapping: {str(e)}")
    
    def _test_data_model_expansion(self):
        """Test the expanded RealEstateContent model"""
        print("\n📊 Test 2: Data Model Expansion")
        
        # Load multiple sample files
        sample_files = list(self.individual_properties_dir.glob("*.json"))[:3]  # Test first 3
        
        for sample_file in sample_files:
            try:
                with open(sample_file, 'r') as f:
                    individual_data = json.load(f)
                
                # Test creating RealEstateContent with full Individual Property API data
                content = RealEstateContent.from_zillow_api(individual_data, api_type="individual")
                
                # Count populated fields
                populated_fields = sum(1 for field_name, field_value in content.dict().items() 
                                     if field_value is not None)
                
                self.stats['properties_tested'] += 1
                self.stats['successful_conversions'] += 1
                
                print(f"✅ {sample_file.name}: {populated_fields} populated fields")
                
                # Test specific enhanced fields
                enhanced_fields = ['tax_history', 'price_history', 'year_built', 'county', 
                                 'time_zone', 'living_area_value', 'contact_recipients']
                
                found_enhanced = []
                for field in enhanced_fields:
                    if hasattr(content, field) and getattr(content, field) is not None:
                        found_enhanced.append(field)
                
                if found_enhanced:
                    print(f"   Enhanced fields found: {', '.join(found_enhanced)}")
                
            except Exception as e:
                print(f"❌ {sample_file.name}: {str(e)}")
                self.stats['errors'].append(f"Data model {sample_file.name}: {str(e)}")
    
    def _test_backwards_compatibility(self):
        """Test backwards compatibility with basic Property Extended Search data"""
        print("\n🔄 Test 3: Backwards Compatibility")
        
        # Load a search result file
        search_files = list(self.search_results_dir.glob("*.json"))
        if not search_files:
            print("⚠️  No search result files found for backwards compatibility test")
            return
        
        search_file = search_files[0]
        with open(search_file, 'r') as f:
            search_data = json.load(f)
        
        props = search_data.get("props", [])[:2]  # Test first 2 properties
        
        for prop in props:
            try:
                # Test creating RealEstateContent with basic Property Extended Search data
                content = RealEstateContent.from_zillow_api(prop, api_type="search")
                
                populated_fields = sum(1 for field_name, field_value in content.dict().items() 
                                     if field_value is not None)
                
                zpid = prop.get('zpid', 'unknown')
                print(f"✅ ZPID {zpid}: {populated_fields} fields (backwards compatible)")
                
            except Exception as e:
                print(f"❌ Backwards compatibility failed for ZPID {prop.get('zpid', 'unknown')}: {str(e)}")
                self.stats['errors'].append(f"Backwards compatibility: {str(e)}")
    
    def _print_results(self):
        """Print test results"""
        print("\n" + "="*60)
        print("🎯 DATA MODEL UPGRADE - TEST RESULTS")
        print("="*60)
        
        print(f"Properties Tested: {self.stats['properties_tested']}")
        print(f"Successful Conversions: {self.stats['successful_conversions']}")
        
        print(f"\nField Count Analysis:")
        print(f"  Basic (Property Extended Search): {self.stats['field_count_basic']} fields")
        print(f"  Full (Individual Property API): {self.stats['field_count_full']} fields")
        
        if self.stats['field_count_full'] > 0 and self.stats['field_count_basic'] > 0:
            improvement = ((self.stats['field_count_full'] - self.stats['field_count_basic']) / 
                          self.stats['field_count_basic'] * 100)
            print(f"  Data Richness Improvement: +{improvement:.1f}%")
        
        # Field set comparison
        miner_fields = len(ZillowFieldMapper.MINER_AVAILABLE_FIELDS)
        individual_fields = len(ZillowFieldMapper.INDIVIDUAL_PROPERTY_FIELDS)
        new_fields = individual_fields - miner_fields
        
        print(f"\nField Set Expansion:")
        print(f"  Basic field set: {miner_fields} fields")
        print(f"  Full field set: {individual_fields} fields")
        print(f"  New fields added: {new_fields} fields")
        
        if self.stats['errors']:
            print(f"\n⚠️  Errors Encountered ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                print(f"  - {error}")
        else:
            print("\n🎉 ALL TESTS PASSED - DATA MODEL UPGRADE SUCCESSFUL!")
        
        print("="*60)


def main():
    """Run the data model upgrade test"""
    test_suite = DataModelUpgradeTest()
    test_suite.run_tests()


if __name__ == "__main__":
    main()
