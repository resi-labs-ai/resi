"""
Unit tests for Zillow validation utilities.
Tests the validation logic for real estate data including timestamp tolerance,
field-specific validation, and time-sensitive data handling.
"""

import unittest
import datetime as dt
import json
from unittest.mock import patch, MagicMock

from common.data import DataEntity, DataLabel, DataSource
from scraping.scraper import ValidationResult
from scraping.zillow.model import RealEstateContent
from scraping.zillow.utils import (
    validate_zillow_data_entity_fields,
    validate_zillow_content_fields,
    validate_time_sensitive_fields,
    are_listing_statuses_compatible,
    RealEstateContentExtended
)


class TestZillowValidationUtils(unittest.TestCase):
    """Test suite for Zillow validation utilities"""
    
    def setUp(self):
        """Set up test data"""
        self.base_datetime = dt.datetime(2025, 9, 11, 13, 12, 29, 637069, tzinfo=dt.timezone.utc)
        self.later_datetime = dt.datetime(2025, 9, 11, 13, 15, 45, 123456, tzinfo=dt.timezone.utc)
        
        # Sample property data
        self.sample_property_data = {
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
            "latitude": 27.576675,
            "longitude": -99.453316,
            "country": "USA",
            "currency": "USD",
            "listing_status": "FOR_SALE",
            "days_on_zillow": 15,
            "img_src": "https://photos.zillowstatic.com/fp/6fc45481ebf6159294cc45cb84cf464d-p_e.jpg",
            "has_image": True,
            "has_video": False,
            "has_3d_model": False,
            "is_fsba": True,
            "scraped_at": self.base_datetime,
            "data_source": "zillow_rapidapi"
        }
        
        # Create test content instances
        self.test_content = RealEstateContent(**self.sample_property_data)
        self.test_entity = self.test_content.to_data_entity()
    
    def test_validate_zillow_data_entity_fields_success(self):
        """Test successful validation with identical content"""
        result = validate_zillow_data_entity_fields(self.test_content, self.test_entity)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "Valid Zillow property data")
        self.assertEqual(result.content_size_bytes_validated, self.test_entity.content_size_bytes)
    
    def test_validate_zillow_data_entity_fields_timestamp_tolerance(self):
        """Test that validation succeeds despite different timestamps"""
        # Create content with different timestamp
        modified_data = self.sample_property_data.copy()
        modified_data["scraped_at"] = self.later_datetime
        modified_content = RealEstateContent(**modified_data)
        
        # Validation should still pass due to timestamp tolerance
        result = validate_zillow_data_entity_fields(modified_content, self.test_entity)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "Valid Zillow property data")
    
    def test_validate_zillow_data_entity_fields_content_size_validation(self):
        """Test content size validation"""
        # Create entity with inflated content size
        oversized_entity = DataEntity(
            uri=self.test_entity.uri,
            datetime=self.test_entity.datetime,
            source=self.test_entity.source,
            label=self.test_entity.label,
            content=self.test_entity.content,
            content_size_bytes=self.test_entity.content_size_bytes + 100  # Too big
        )
        
        result = validate_zillow_data_entity_fields(self.test_content, oversized_entity)
        
        self.assertFalse(result.is_valid)
        self.assertIn("claimed bytes must not exceed", result.reason)
    
    def test_validate_zillow_data_entity_fields_uri_mismatch(self):
        """Test validation failure with URI mismatch"""
        # Create entity with different URI
        wrong_uri_entity = DataEntity(
            uri="https://zillow.com/different-property/",
            datetime=self.test_entity.datetime,
            source=self.test_entity.source,
            label=self.test_entity.label,
            content=self.test_entity.content,
            content_size_bytes=self.test_entity.content_size_bytes
        )
        
        result = validate_zillow_data_entity_fields(self.test_content, wrong_uri_entity)
        
        self.assertFalse(result.is_valid)
        self.assertIn("DataEntity fields are incorrect", result.reason)
    
    def test_validate_critical_fields_success(self):
        """Test validation of critical fields that must match exactly"""
        result = validate_zillow_content_fields(self.test_content, self.test_entity)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "Zillow content fields validated successfully")
    
    def test_validate_critical_fields_zpid_mismatch(self):
        """Test validation failure when zpid doesn't match"""
        # Create content with different zpid
        modified_data = self.sample_property_data.copy()
        modified_data["zpid"] = "12345678"
        modified_content = RealEstateContent(**modified_data)
        
        result = validate_zillow_content_fields(modified_content, self.test_entity)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Critical field 'zpid' mismatch", result.reason)
    
    def test_validate_critical_fields_address_mismatch(self):
        """Test validation failure when address doesn't match"""
        # Create content with different address
        modified_data = self.sample_property_data.copy()
        modified_data["address"] = "123 Different Street, Austin, TX 78701"
        modified_content = RealEstateContent(**modified_data)
        
        result = validate_zillow_content_fields(modified_content, self.test_entity)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Critical field 'address' mismatch", result.reason)
    
    def test_validate_stable_fields_mismatch(self):
        """Test validation failure when stable fields don't match"""
        # Create content with different bedroom count
        modified_data = self.sample_property_data.copy()
        modified_data["bedrooms"] = 5  # Changed from 4
        modified_content = RealEstateContent(**modified_data)
        
        result = validate_zillow_content_fields(modified_content, self.test_entity)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Stable field 'bedrooms' mismatch", result.reason)
    
    def test_validate_time_sensitive_fields_price_tolerance(self):
        """Test price validation with acceptable tolerance"""
        # Create content with slightly different price (within 5% tolerance)
        miner_content = self.test_content
        actual_data = self.sample_property_data.copy()
        actual_data["price"] = 475000  # ~2% increase from 465000
        actual_content = RealEstateContent(**actual_data)
        
        result = validate_time_sensitive_fields(actual_content, miner_content)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "Time-sensitive fields validated successfully")
    
    def test_validate_time_sensitive_fields_price_too_different(self):
        """Test price validation failure when difference exceeds tolerance"""
        # Create content with price difference > 5%
        miner_content = self.test_content
        actual_data = self.sample_property_data.copy()
        actual_data["price"] = 500000  # ~7.5% increase from 465000
        actual_content = RealEstateContent(**actual_data)
        
        result = validate_time_sensitive_fields(actual_content, miner_content)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Price difference too large", result.reason)
    
    def test_validate_time_sensitive_fields_zestimate_tolerance(self):
        """Test zestimate validation with acceptable tolerance"""
        # Create content with zestimate difference within 10% tolerance
        miner_content = self.test_content
        actual_data = self.sample_property_data.copy()
        actual_data["zestimate"] = 485000  # ~5% increase from 460900
        actual_content = RealEstateContent(**actual_data)
        
        result = validate_time_sensitive_fields(actual_content, miner_content)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_time_sensitive_fields_zestimate_too_different(self):
        """Test zestimate validation failure when difference exceeds tolerance"""
        # Create content with zestimate difference > 10%
        miner_content = self.test_content
        actual_data = self.sample_property_data.copy()
        actual_data["zestimate"] = 520000  # ~12.8% increase from 460900
        actual_content = RealEstateContent(**actual_data)
        
        result = validate_time_sensitive_fields(actual_content, miner_content)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Zestimate difference too large", result.reason)
    
    def test_validate_time_sensitive_fields_days_on_zillow_tolerance(self):
        """Test days on Zillow validation with acceptable tolerance"""
        # Create content with days difference within 7-day tolerance
        miner_content = self.test_content
        actual_data = self.sample_property_data.copy()
        actual_data["days_on_zillow"] = 20  # 5 days difference from 15
        actual_content = RealEstateContent(**actual_data)
        
        result = validate_time_sensitive_fields(actual_content, miner_content)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_time_sensitive_fields_days_on_zillow_too_different(self):
        """Test days on Zillow validation failure when difference exceeds tolerance"""
        # Create content with days difference > 7
        miner_content = self.test_content
        actual_data = self.sample_property_data.copy()
        actual_data["days_on_zillow"] = 25  # 10 days difference from 15
        actual_content = RealEstateContent(**actual_data)
        
        result = validate_time_sensitive_fields(actual_content, miner_content)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Days on Zillow difference too large", result.reason)
    
    def test_are_listing_statuses_compatible_exact_match(self):
        """Test listing status compatibility with exact match"""
        self.assertTrue(are_listing_statuses_compatible("FOR_SALE", "FOR_SALE"))
        self.assertTrue(are_listing_statuses_compatible("SOLD", "SOLD"))
    
    def test_are_listing_statuses_compatible_valid_transitions(self):
        """Test valid listing status transitions"""
        # FOR_SALE can transition to PENDING or SOLD
        self.assertTrue(are_listing_statuses_compatible("PENDING", "FOR_SALE"))
        self.assertTrue(are_listing_statuses_compatible("SOLD", "FOR_SALE"))
        
        # FOR_RENT can transition to RENTED
        self.assertTrue(are_listing_statuses_compatible("RENTED", "FOR_RENT"))
        
        # PENDING can transition to SOLD or back to FOR_SALE
        self.assertTrue(are_listing_statuses_compatible("SOLD", "PENDING"))
        self.assertTrue(are_listing_statuses_compatible("FOR_SALE", "PENDING"))
    
    def test_are_listing_statuses_compatible_invalid_transitions(self):
        """Test invalid listing status transitions"""
        # Invalid transitions should return False
        self.assertFalse(are_listing_statuses_compatible("FOR_SALE", "FOR_RENT"))
        self.assertFalse(are_listing_statuses_compatible("SOLD", "FOR_RENT"))
        self.assertFalse(are_listing_statuses_compatible("RENTED", "SOLD"))
    
    def test_real_estate_content_extended_from_data_entity(self):
        """Test RealEstateContentExtended.from_data_entity method"""
        # Test successful conversion
        extracted_content = RealEstateContentExtended.from_data_entity(self.test_entity)
        
        self.assertEqual(extracted_content.zpid, self.test_content.zpid)
        self.assertEqual(extracted_content.address, self.test_content.address)
        self.assertEqual(extracted_content.price, self.test_content.price)
        self.assertEqual(extracted_content.property_type, self.test_content.property_type)
    
    def test_real_estate_content_extended_from_data_entity_invalid(self):
        """Test RealEstateContentExtended.from_data_entity with invalid data"""
        # Create entity with invalid JSON content
        invalid_entity = DataEntity(
            uri=self.test_entity.uri,
            datetime=self.test_entity.datetime,
            source=self.test_entity.source,
            label=self.test_entity.label,
            content=b"invalid json content",
            content_size_bytes=len(b"invalid json content")
        )
        
        with self.assertRaises(ValueError) as context:
            RealEstateContentExtended.from_data_entity(invalid_entity)
        
        self.assertIn("Invalid DataEntity content", str(context.exception))
    
    def test_get_validation_summary(self):
        """Test validation summary generation"""
        extended_content = RealEstateContentExtended(**self.sample_property_data)
        summary = extended_content.get_validation_summary()
        
        expected_fields = ['zpid', 'address', 'price', 'listing_status', 'days_on_zillow', 'scraped_at']
        for field in expected_fields:
            self.assertIn(field, summary)
        
        self.assertEqual(summary['zpid'], "70982473")
        self.assertEqual(summary['price'], 465000)
        self.assertEqual(summary['listing_status'], "FOR_SALE")
    
    @patch('scraping.zillow.utils.bt.logging')
    def test_validation_error_handling(self, mock_logging):
        """Test error handling in validation functions"""
        # Create a mock entity that will cause an exception
        mock_entity = MagicMock()
        mock_entity.content_size_bytes = 1000
        mock_entity.content.decode.side_effect = Exception("Decode error")
        
        result = validate_zillow_data_entity_fields(self.test_content, mock_entity)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Validation error", result.reason)
        mock_logging.error.assert_called()


class TestZillowValidationIntegration(unittest.TestCase):
    """Integration tests for Zillow validation with realistic scenarios"""
    
    def setUp(self):
        """Set up integration test data"""
        self.base_datetime = dt.datetime(2025, 9, 11, 13, 12, 29, 637069, tzinfo=dt.timezone.utc)
        
        # Realistic property data based on your example
        self.laredo_property = {
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
            "scraped_at": self.base_datetime,
            "data_source": "zillow_rapidapi"
        }
    
    def test_realistic_miner_validator_scenario_success(self):
        """Test realistic scenario where miner and validator scrape similar data"""
        # Miner's data
        miner_content = RealEstateContent(**self.laredo_property)
        miner_entity = miner_content.to_data_entity()
        
        # Validator's data with slight differences (realistic API variations)
        validator_data = self.laredo_property.copy()
        validator_data.update({
            "scraped_at": self.base_datetime + dt.timedelta(minutes=3),  # 3 minutes later
            "zestimate": 462000,  # Slight zestimate change (~0.2%)
            "days_on_zillow": 16,  # One day increment
            "img_src": "https://photos.zillowstatic.com/fp/different-image-id.jpg"  # Different image
        })
        validator_content = RealEstateContent(**validator_data)
        
        result = validate_zillow_data_entity_fields(validator_content, miner_entity)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "Valid Zillow property data")
    
    def test_realistic_miner_validator_scenario_price_change(self):
        """Test scenario where property price changed significantly"""
        # Miner's data
        miner_content = RealEstateContent(**self.laredo_property)
        miner_entity = miner_content.to_data_entity()
        
        # Validator's data with significant price change (> 5% tolerance)
        validator_data = self.laredo_property.copy()
        validator_data.update({
            "price": 490000,  # ~5.4% increase - should fail
            "scraped_at": self.base_datetime + dt.timedelta(hours=1)
        })
        validator_content = RealEstateContent(**validator_data)
        
        result = validate_zillow_data_entity_fields(validator_content, miner_entity)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Price difference too large", result.reason)
    
    def test_realistic_miner_validator_scenario_property_sold(self):
        """Test scenario where property status changed from FOR_SALE to SOLD"""
        # Miner's data (FOR_SALE)
        miner_content = RealEstateContent(**self.laredo_property)
        miner_entity = miner_content.to_data_entity()
        
        # Validator's data (property sold)
        validator_data = self.laredo_property.copy()
        validator_data.update({
            "listing_status": "SOLD",
            "scraped_at": self.base_datetime + dt.timedelta(days=1)
        })
        validator_content = RealEstateContent(**validator_data)
        
        result = validate_zillow_data_entity_fields(validator_content, miner_entity)
        
        # Should pass because FOR_SALE -> SOLD is a valid transition
        self.assertTrue(result.is_valid)


if __name__ == '__main__':
    unittest.main()
