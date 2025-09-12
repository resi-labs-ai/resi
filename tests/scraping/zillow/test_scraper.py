"""
Unit tests for ZillowRapidAPIScraper.
Tests the enhanced validation functionality including existence checks,
content validation, and error handling.
"""

import unittest
import asyncio
import json
import datetime as dt
from unittest.mock import AsyncMock, patch, MagicMock

from common.data import DataEntity, DataLabel, DataSource
from scraping.scraper import ValidationResult
from scraping.zillow.rapid_zillow_scraper import ZillowRapidAPIScraper
from scraping.zillow.model import RealEstateContent


class TestZillowRapidAPIScraper(unittest.TestCase):
    """Test suite for ZillowRapidAPIScraper validation functionality"""
    
    def setUp(self):
        """Set up test data and mocks"""
        self.base_datetime = dt.datetime(2025, 9, 11, 13, 12, 29, 637069, tzinfo=dt.timezone.utc)
        
        # Sample property data
        self.sample_property_data = {
            "zpid": "70982473",
            "address": "7622 R W Emerson Loop, Laredo, TX 78041",
            "detail_url": "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
            "property_type": "SINGLE_FAMILY",
            "bedrooms": 4,
            "bathrooms": 3.0,
            "living_area": 2464,
            "price": 465000,
            "zestimate": 460900,
            "listing_status": "FOR_SALE",
            "days_on_zillow": 15,
            "latitude": 27.576675,
            "longitude": -99.453316,
            "scraped_at": self.base_datetime,
            "data_source": "zillow_rapidapi"
        }
        
        # Create test content and entity
        self.test_content = RealEstateContent(**self.sample_property_data)
        self.test_entity = self.test_content.to_data_entity()
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'RAPIDAPI_KEY': 'test_api_key',
            'RAPIDAPI_HOST': 'zillow-com1.p.rapidapi.com'
        })
        self.env_patcher.start()
        
        # Create scraper instance
        self.scraper = ZillowRapidAPIScraper()
    
    def tearDown(self):
        """Clean up patches"""
        self.env_patcher.stop()
    
    def test_extract_zpid_from_uri_success(self):
        """Test successful zpid extraction from URI"""
        test_uris = [
            "https://zillow.com/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
            "/homedetails/property-address/12345678_zpid/",
            "https://www.zillow.com/homedetails/some-property/99999999_zpid/more-stuff/",
        ]
        
        expected_zpids = ["70982473", "12345678", "99999999"]
        
        for uri, expected_zpid in zip(test_uris, expected_zpids):
            zpid = self.scraper._extract_zpid_from_uri(uri)
            self.assertEqual(zpid, expected_zpid, f"Failed for URI: {uri}")
    
    def test_extract_zpid_from_uri_failure(self):
        """Test zpid extraction failure scenarios"""
        invalid_uris = [
            "https://zillow.com/property/12345/",  # No homedetails
            "https://zillow.com/homedetails/property-address/",  # No zpid
            "https://example.com/different-site/",  # Different site
            "",  # Empty string
        ]
        
        for uri in invalid_uris:
            zpid = self.scraper._extract_zpid_from_uri(uri)
            self.assertIsNone(zpid, f"Should have failed for URI: {uri}")
    
    @patch('httpx.AsyncClient')
    async def test_check_property_existence_success(self, mock_client_class):
        """Test successful property existence check"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await self.scraper._check_property_existence(mock_client, "70982473", self.test_entity)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "Property exists via Zillow API")
        self.assertEqual(result.content_size_bytes_validated, self.test_entity.content_size_bytes)
    
    @patch('httpx.AsyncClient')
    async def test_check_property_existence_not_found(self, mock_client_class):
        """Test property existence check when property not found"""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await self.scraper._check_property_existence(mock_client, "70982473", self.test_entity)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "Property not found (may have been sold/removed)")
    
    @patch('httpx.AsyncClient')
    @patch('asyncio.sleep', new_callable=AsyncMock)
    async def test_check_property_existence_rate_limited(self, mock_sleep, mock_client_class):
        """Test property existence check when rate limited"""
        # Mock 429 response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await self.scraper._check_property_existence(mock_client, "70982473", self.test_entity)
        
        self.assertTrue(result.is_valid)  # Should assume valid on rate limit
        self.assertIn("Rate limited", result.reason)
        mock_sleep.assert_called_once_with(60)  # Should wait 60 seconds
    
    @patch('httpx.AsyncClient')
    async def test_check_property_existence_api_error(self, mock_client_class):
        """Test property existence check with API error"""
        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await self.scraper._check_property_existence(mock_client, "70982473", self.test_entity)
        
        self.assertTrue(result.is_valid)  # Should assume valid on API errors
        self.assertIn("API error during validation (500)", result.reason)
    
    @patch('httpx.AsyncClient')
    async def test_fetch_property_content_success(self, mock_client_class):
        """Test successful property content fetching"""
        # Mock API response with property data
        api_response_data = {
            "property": {
                "zpid": "70982473",
                "address": "7622 R W Emerson Loop, Laredo, TX 78041",
                "detailUrl": "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
                "propertyType": "SINGLE_FAMILY",
                "bedrooms": 4,
                "bathrooms": 3.0,
                "price": 465000,
                "listingStatus": "FOR_SALE",
                "listingSubType": {"is_FSBA": True}
            }
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        content = await self.scraper._fetch_property_content(mock_client, "70982473")
        
        self.assertIsNotNone(content)
        self.assertIsInstance(content, RealEstateContent)
        self.assertEqual(content.zpid, "70982473")
        self.assertEqual(content.property_type, "SINGLE_FAMILY")
    
    @patch('httpx.AsyncClient')
    async def test_fetch_property_content_no_property_data(self, mock_client_class):
        """Test property content fetching when no property data in response"""
        # Mock API response without property data
        api_response_data = {"error": "No property found"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        content = await self.scraper._fetch_property_content(mock_client, "70982473")
        
        self.assertIsNone(content)
    
    @patch('httpx.AsyncClient')
    async def test_fetch_property_content_api_error(self, mock_client_class):
        """Test property content fetching with API error"""
        # Mock API error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        content = await self.scraper._fetch_property_content(mock_client, "70982473")
        
        self.assertIsNone(content)
    
    @patch('scraping.zillow.rapid_zillow_scraper.validate_zillow_data_entity_fields')
    @patch('httpx.AsyncClient')
    async def test_validate_success_with_content_validation(self, mock_client_class, mock_validate_fields):
        """Test successful validation with content validation"""
        # Mock successful existence check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "property": {
                "zpid": "70982473",
                "address": "7622 R W Emerson Loop, Laredo, TX 78041",
                "detailUrl": "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
                "propertyType": "SINGLE_FAMILY",
                "listingStatus": "FOR_SALE",
                "listingSubType": {}
            }
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful content validation
        mock_validate_fields.return_value = ValidationResult(
            is_valid=True,
            reason="Valid Zillow property data",
            content_size_bytes_validated=self.test_entity.content_size_bytes
        )
        
        results = await self.scraper.validate([self.test_entity])
        
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_valid)
        self.assertEqual(results[0].reason, "Valid Zillow property data")
        mock_validate_fields.assert_called_once()
    
    @patch('scraping.zillow.rapid_zillow_scraper.validate_zillow_data_entity_fields')
    @patch('httpx.AsyncClient')
    async def test_validate_content_validation_failure(self, mock_client_class, mock_validate_fields):
        """Test validation failure during content validation"""
        # Mock successful existence check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "property": {
                "zpid": "70982473",
                "address": "Different Address",  # This will cause validation failure
                "detailUrl": "/homedetails/different/70982473_zpid/",
                "propertyType": "SINGLE_FAMILY",
                "listingStatus": "FOR_SALE",
                "listingSubType": {}
            }
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock failed content validation
        mock_validate_fields.return_value = ValidationResult(
            is_valid=False,
            reason="Critical field 'address' mismatch",
            content_size_bytes_validated=self.test_entity.content_size_bytes
        )
        
        results = await self.scraper.validate([self.test_entity])
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)
        self.assertEqual(results[0].reason, "Critical field 'address' mismatch")
    
    @patch('httpx.AsyncClient')
    async def test_validate_property_not_found(self, mock_client_class):
        """Test validation when property is not found"""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        results = await self.scraper.validate([self.test_entity])
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)
        self.assertEqual(results[0].reason, "Property not found (may have been sold/removed)")
    
    async def test_validate_invalid_uri(self):
        """Test validation with invalid URI (no zpid)"""
        # Create entity with invalid URI
        invalid_entity = DataEntity(
            uri="https://example.com/invalid-property/",
            datetime=self.test_entity.datetime,
            source=self.test_entity.source,
            label=self.test_entity.label,
            content=self.test_entity.content,
            content_size_bytes=self.test_entity.content_size_bytes
        )
        
        results = await self.scraper.validate([invalid_entity])
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)
        self.assertEqual(results[0].reason, "Could not extract zpid from URI")
    
    @patch('httpx.AsyncClient')
    async def test_validate_content_fetch_failure_fallback(self, mock_client_class):
        """Test validation fallback when content fetch fails"""
        # Mock successful existence check but failed content fetch
        mock_client = AsyncMock()
        
        # First call (existence check) succeeds
        # Second call (content fetch) fails
        mock_responses = [
            MagicMock(status_code=200),  # Existence check
            MagicMock(status_code=500)   # Content fetch
        ]
        mock_client.get.side_effect = mock_responses
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        results = await self.scraper.validate([self.test_entity])
        
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_valid)  # Should fallback to existence check result
        self.assertEqual(results[0].reason, "Property exists via Zillow API")
    
    @patch('httpx.AsyncClient')
    async def test_validate_multiple_entities(self, mock_client_class):
        """Test validation of multiple entities"""
        # Create second test entity
        second_data = self.sample_property_data.copy()
        second_data["zpid"] = "12345678"
        second_data["address"] = "123 Test St, Austin, TX 78701"
        second_content = RealEstateContent(**second_data)
        second_entity = second_content.to_data_entity()
        
        # Mock responses for both properties
        mock_responses = [
            MagicMock(status_code=200),  # First property exists
            MagicMock(status_code=404),  # Second property not found
        ]
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = mock_responses
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        results = await self.scraper.validate([self.test_entity, second_entity])
        
        self.assertEqual(len(results), 2)
        
        # First property should pass existence check
        self.assertTrue(results[0].is_valid)
        
        # Second property should fail (not found)
        self.assertFalse(results[1].is_valid)
        self.assertIn("not found", results[1].reason)
    
    @patch('httpx.AsyncClient')
    async def test_validate_exception_handling(self, mock_client_class):
        """Test validation exception handling"""
        # Mock client to raise exception
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        results = await self.scraper.validate([self.test_entity])
        
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_valid)  # Should assume valid on exceptions
        self.assertIn("Validation exception - assumed valid", results[0].reason)
        self.assertIn("Network error", results[0].reason)
    
    @patch('scraping.zillow.rapid_zillow_scraper.asyncio.sleep', new_callable=AsyncMock)
    async def test_rate_limiting(self, mock_sleep):
        """Test rate limiting functionality"""
        scraper = ZillowRapidAPIScraper()
        
        # First call should not sleep (enough time has passed)
        await scraper._rate_limit()
        mock_sleep.assert_not_called()
        
        # Immediate second call should sleep
        await scraper._rate_limit()
        mock_sleep.assert_called_once()
        
        # Sleep duration should be close to REQUEST_DELAY (0.5 seconds)
        sleep_duration = mock_sleep.call_args[0][0]
        self.assertGreaterEqual(sleep_duration, 0.0)
        self.assertLessEqual(sleep_duration, 0.5)


class TestZillowScraperIntegration(unittest.TestCase):
    """Integration tests for ZillowRapidAPIScraper"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'RAPIDAPI_KEY': 'test_api_key',
            'RAPIDAPI_HOST': 'zillow-com1.p.rapidapi.com'
        })
        self.env_patcher.start()
        
        self.scraper = ZillowRapidAPIScraper()
    
    def tearDown(self):
        """Clean up patches"""
        self.env_patcher.stop()
    
    @patch('httpx.AsyncClient')
    async def test_realistic_validation_scenario(self, mock_client_class):
        """Test realistic validation scenario with actual property data"""
        # Create realistic property entity
        property_data = {
            "zpid": "70982473",
            "address": "7622 R W Emerson Loop, Laredo, TX 78041",
            "detail_url": "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
            "property_type": "SINGLE_FAMILY",
            "bedrooms": 4,
            "bathrooms": 3.0,
            "living_area": 2464,
            "price": 465000,
            "zestimate": 460900,
            "listing_status": "FOR_SALE",
            "days_on_zillow": 15,
            "latitude": 27.576675,
            "longitude": -99.453316,
            "scraped_at": dt.datetime.now(dt.timezone.utc),
            "data_source": "zillow_rapidapi"
        }
        
        content = RealEstateContent(**property_data)
        entity = content.to_data_entity()
        
        # Mock API responses
        api_response_data = {
            "property": {
                "zpid": "70982473",
                "address": "7622 R W Emerson Loop, Laredo, TX 78041",
                "detailUrl": "/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
                "propertyType": "SINGLE_FAMILY",
                "bedrooms": 4,
                "bathrooms": 3.0,
                "price": 467000,  # Slightly different price (within tolerance)
                "zestimate": 462000,  # Slightly different zestimate
                "listingStatus": "FOR_SALE",
                "daysOnZillow": 16,  # One day increment
                "listingSubType": {"is_FSBA": True}
            }
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Run validation
        results = await self.scraper.validate([entity])
        
        # Should pass validation despite small differences
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_valid)


if __name__ == '__main__':
    unittest.main()
