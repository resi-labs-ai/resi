"""
Unit tests for Zillow RealEstateContent model.
Tests the data model functionality including API data conversion,
DataEntity conversion, and utility methods.
"""

import unittest
import datetime as dt
import json

from common.data import DataEntity, DataLabel, DataSource
from scraping.zillow.model import RealEstateContent


class TestRealEstateContent(unittest.TestCase):
    """Test suite for RealEstateContent model"""
    
    def setUp(self):
        """Set up test data"""
        self.base_datetime = dt.datetime(2025, 9, 11, 13, 12, 29, 637069, tzinfo=dt.timezone.utc)
        
        # Sample Zillow API response data
        self.api_data = {
            "zpid": "70982473",
            "address": "7622 R W Emerson Loop, Laredo, TX 78041",
            "detailUrl": "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
            "propertyType": "SINGLE_FAMILY",
            "bedrooms": 4,
            "bathrooms": 3.0,
            "livingArea": 2464,
            "lotAreaValue": 10000.0,
            "lotAreaUnit": "sqft",
            "price": 465000,
            "zestimate": 460900,
            "rentZestimate": 2340,
            "priceChange": None,
            "datePriceChanged": None,
            "latitude": 27.576675,
            "longitude": -99.453316,
            "country": "USA",
            "currency": "USD",
            "listingStatus": "FOR_SALE",
            "daysOnZillow": 15,
            "comingSoonOnMarketDate": None,
            "imgSrc": "https://photos.zillowstatic.com/fp/6fc45481ebf6159294cc45cb84cf464d-p_e.jpg",
            "hasImage": True,
            "hasVideo": False,
            "has3DModel": False,
            "carouselPhotos": None,
            "listingSubType": {
                "is_FSBA": True,
                "is_openHouse": None,
                "is_newHome": None,
                "is_comingSoon": None
            },
            "newConstructionType": None,
            "unit": None,
            "contingentListingType": None,
            "variableData": None
        }
        
        # Expected RealEstateContent data
        self.expected_content_data = {
            "zpid": "70982473",
            "address": "7622 R W Emerson Loop, Laredo, TX 78041",
            "detail_url": "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
            "property_type": "SINGLE_FAMILY",
            "bedrooms": 4,
            "bathrooms": 3.0,
            "living_area": 2464,
            "lot_area_value": 10000.0,
            "lot_area_unit": "sqft",
            "price": 465000,
            "zestimate": 460900,
            "rent_zestimate": 2340,
            "price_change": None,
            "date_price_changed": None,
            "latitude": 27.576675,
            "longitude": -99.453316,
            "country": "USA",
            "currency": "USD",
            "listing_status": "FOR_SALE",
            "days_on_zillow": 15,
            "coming_soon_on_market_date": None,
            "img_src": "https://photos.zillowstatic.com/fp/6fc45481ebf6159294cc45cb84cf464d-p_e.jpg",
            "has_image": True,
            "has_video": False,
            "has_3d_model": False,
            "carousel_photos": None,
            "is_fsba": True,
            "is_open_house": None,
            "is_new_home": None,
            "is_coming_soon": None,
            "new_construction_type": None,
            "unit": None,
            "contingent_listing_type": None,
            "variable_data": None,
            "data_source": "zillow_rapidapi"
        }
    
    def test_from_zillow_api_success(self):
        """Test successful creation from Zillow API data"""
        content = RealEstateContent.from_zillow_api(self.api_data)
        
        # Test core identifiers
        self.assertEqual(content.zpid, "70982473")
        self.assertEqual(content.address, "7622 R W Emerson Loop, Laredo, TX 78041")
        self.assertEqual(content.detail_url, "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/")
        
        # Test property details
        self.assertEqual(content.property_type, "SINGLE_FAMILY")
        self.assertEqual(content.bedrooms, 4)
        self.assertEqual(content.bathrooms, 3.0)
        self.assertEqual(content.living_area, 2464)
        
        # Test pricing
        self.assertEqual(content.price, 465000)
        self.assertEqual(content.zestimate, 460900)
        self.assertEqual(content.rent_zestimate, 2340)
        
        # Test location
        self.assertEqual(content.latitude, 27.576675)
        self.assertEqual(content.longitude, -99.453316)
        
        # Test listing status
        self.assertEqual(content.listing_status, "FOR_SALE")
        self.assertEqual(content.days_on_zillow, 15)
        
        # Test flags
        self.assertTrue(content.is_fsba)
        self.assertIsNone(content.is_open_house)
        
        # Test metadata
        self.assertEqual(content.data_source, "zillow_rapidapi")
    
    def test_from_zillow_api_minimal_data(self):
        """Test creation with minimal required data"""
        minimal_data = {
            "zpid": "12345",
            "address": "123 Test St, Test City, TX 12345",
            "detailUrl": "/homedetails/123-Test-St/12345_zpid/",
            "propertyType": "CONDO",
            "listingStatus": "FOR_RENT",
            "listingSubType": {}
        }
        
        content = RealEstateContent.from_zillow_api(minimal_data)
        
        self.assertEqual(content.zpid, "12345")
        self.assertEqual(content.property_type, "CONDO")
        self.assertEqual(content.listing_status, "FOR_RENT")
        self.assertEqual(content.country, "USA")  # Default value
        self.assertEqual(content.currency, "USD")  # Default value
        self.assertFalse(content.has_image)  # Default value
    
    def test_to_data_entity_success(self):
        """Test successful conversion to DataEntity"""
        content = RealEstateContent(**self.expected_content_data)
        entity = content.to_data_entity()
        
        # Test DataEntity fields
        self.assertEqual(entity.uri, "https://zillow.com/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/")
        self.assertEqual(entity.source, DataSource.RAPID_ZILLOW)
        self.assertIsInstance(entity.label, DataLabel)
        self.assertEqual(entity.label.value, "zip:78041")
        
        # Test content serialization
        self.assertIsInstance(entity.content, bytes)
        self.assertEqual(entity.content_size_bytes, len(entity.content))
        
        # Verify content can be deserialized
        content_dict = json.loads(entity.content.decode('utf-8'))
        self.assertEqual(content_dict['zpid'], "70982473")
        self.assertEqual(content_dict['address'], "7622 R W Emerson Loop, Laredo, TX 78041")
    
    def test_to_data_entity_zipcode_extraction(self):
        """Test zipcode extraction from address for labeling"""
        test_addresses = [
            ("123 Main St, Austin, TX 78701", "zip:78701"),
            ("456 Oak Ave, Dallas, TX 75201", "zip:75201"),
            ("789 Pine Rd, Houston TX 77001", "zip:77001"),  # No comma before state
            ("321 Elm St, San Antonio, Texas 78201", "zip:78201"),  # Full state name
            ("654 Maple Dr, Invalid Address", "zip:unknown"),  # No zipcode found
        ]
        
        for address, expected_label in test_addresses:
            content_data = self.expected_content_data.copy()
            content_data["address"] = address
            content = RealEstateContent(**content_data)
            entity = content.to_data_entity()
            
            self.assertEqual(entity.label.value, expected_label, 
                           f"Failed for address: {address}")
    
    def test_to_data_entity_uri_formatting(self):
        """Test URI formatting for different detail_url formats"""
        test_cases = [
            # Relative URL (starts with /)
            ("/homedetails/test-property/12345_zpid/", 
             "https://zillow.com/homedetails/test-property/12345_zpid/"),
            # Absolute URL (already complete)
            ("https://zillow.com/homedetails/test-property/12345_zpid/", 
             "https://zillow.com/homedetails/test-property/12345_zpid/"),
        ]
        
        for detail_url, expected_uri in test_cases:
            content_data = self.expected_content_data.copy()
            content_data["detail_url"] = detail_url
            content = RealEstateContent(**content_data)
            entity = content.to_data_entity()
            
            self.assertEqual(entity.uri, expected_uri, 
                           f"Failed for detail_url: {detail_url}")
    
    def test_get_price_per_sqft_success(self):
        """Test price per square foot calculation"""
        content = RealEstateContent(**self.expected_content_data)
        price_per_sqft = content.get_price_per_sqft()
        
        expected = round(465000 / 2464, 2)  # price / living_area
        self.assertEqual(price_per_sqft, expected)
        self.assertAlmostEqual(price_per_sqft, 188.72, places=2)
    
    def test_get_price_per_sqft_missing_data(self):
        """Test price per square foot with missing data"""
        # Test with no price
        content_data = self.expected_content_data.copy()
        content_data["price"] = None
        content = RealEstateContent(**content_data)
        self.assertIsNone(content.get_price_per_sqft())
        
        # Test with no living area
        content_data = self.expected_content_data.copy()
        content_data["living_area"] = None
        content = RealEstateContent(**content_data)
        self.assertIsNone(content.get_price_per_sqft())
        
        # Test with zero living area
        content_data = self.expected_content_data.copy()
        content_data["living_area"] = 0
        content = RealEstateContent(**content_data)
        self.assertIsNone(content.get_price_per_sqft())
    
    def test_get_lot_size_sqft_acres(self):
        """Test lot size conversion from acres to square feet"""
        content_data = self.expected_content_data.copy()
        content_data["lot_area_value"] = 0.5
        content_data["lot_area_unit"] = "acres"
        content = RealEstateContent(**content_data)
        
        lot_size = content.get_lot_size_sqft()
        expected = 0.5 * 43560  # 0.5 acres * 43560 sq ft/acre
        self.assertEqual(lot_size, expected)
    
    def test_get_lot_size_sqft_sqft(self):
        """Test lot size when already in square feet"""
        content = RealEstateContent(**self.expected_content_data)
        lot_size = content.get_lot_size_sqft()
        
        self.assertEqual(lot_size, 10000.0)
    
    def test_get_lot_size_sqft_unknown_unit(self):
        """Test lot size with unknown unit"""
        content_data = self.expected_content_data.copy()
        content_data["lot_area_unit"] = "hectares"
        content = RealEstateContent(**content_data)
        
        self.assertIsNone(content.get_lot_size_sqft())
    
    def test_get_lot_size_sqft_missing_data(self):
        """Test lot size with missing data"""
        content_data = self.expected_content_data.copy()
        content_data["lot_area_value"] = None
        content = RealEstateContent(**content_data)
        
        self.assertIsNone(content.get_lot_size_sqft())
    
    def test_is_high_value_property_default_threshold(self):
        """Test high value property detection with default threshold"""
        # Test property above $1M threshold
        content_data = self.expected_content_data.copy()
        content_data["price"] = 1200000
        content = RealEstateContent(**content_data)
        self.assertTrue(content.is_high_value_property())
        
        # Test property below $1M threshold
        content = RealEstateContent(**self.expected_content_data)  # $465k
        self.assertFalse(content.is_high_value_property())
        
        # Test property exactly at $1M threshold
        content_data = self.expected_content_data.copy()
        content_data["price"] = 1000000
        content = RealEstateContent(**content_data)
        self.assertTrue(content.is_high_value_property())
    
    def test_is_high_value_property_custom_threshold(self):
        """Test high value property detection with custom threshold"""
        content = RealEstateContent(**self.expected_content_data)  # $465k
        
        # Custom threshold below property price
        self.assertTrue(content.is_high_value_property(threshold=400000))
        
        # Custom threshold above property price
        self.assertFalse(content.is_high_value_property(threshold=500000))
    
    def test_is_high_value_property_no_price(self):
        """Test high value property detection with no price"""
        content_data = self.expected_content_data.copy()
        content_data["price"] = None
        content = RealEstateContent(**content_data)
        
        self.assertFalse(content.is_high_value_property())
    
    def test_get_location_summary(self):
        """Test location summary generation"""
        content = RealEstateContent(**self.expected_content_data)
        summary = content.get_location_summary()
        
        # Should return "City, State ZIP"
        self.assertEqual(summary, "Laredo, TX 78041")
    
    def test_get_location_summary_short_address(self):
        """Test location summary with short address"""
        content_data = self.expected_content_data.copy()
        content_data["address"] = "Short Address"
        content = RealEstateContent(**content_data)
        
        summary = content.get_location_summary()
        self.assertEqual(summary, "Short Address")  # Should return full address
    
    def test_model_validation_extra_forbid(self):
        """Test that extra fields are forbidden"""
        invalid_data = self.expected_content_data.copy()
        invalid_data["extra_field"] = "should_not_be_allowed"
        
        with self.assertRaises(ValueError):
            RealEstateContent(**invalid_data)
    
    def test_datetime_field_handling(self):
        """Test datetime field handling"""
        content_data = self.expected_content_data.copy()
        content_data["scraped_at"] = self.base_datetime
        content = RealEstateContent(**content_data)
        
        self.assertEqual(content.scraped_at, self.base_datetime)
        self.assertIsInstance(content.scraped_at, dt.datetime)
    
    def test_optional_fields_none_values(self):
        """Test handling of optional fields with None values"""
        content_data = {
            "zpid": "12345",
            "address": "123 Test St, Test City, TX 12345",
            "detail_url": "/test/",
            "property_type": "SINGLE_FAMILY",
            "listing_status": "FOR_SALE",
            "data_source": "zillow_rapidapi",
            # All other fields will be None by default
        }
        
        content = RealEstateContent(**content_data)
        
        # Test that optional fields can be None
        self.assertIsNone(content.bedrooms)
        self.assertIsNone(content.bathrooms)
        self.assertIsNone(content.price)
        self.assertIsNone(content.zestimate)
        self.assertIsNone(content.latitude)
        self.assertIsNone(content.longitude)
        
        # Test that required fields are present
        self.assertEqual(content.zpid, "12345")
        self.assertEqual(content.property_type, "SINGLE_FAMILY")
        self.assertEqual(content.listing_status, "FOR_SALE")


if __name__ == '__main__':
    unittest.main()
