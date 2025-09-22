"""
Tests for Zillow miner implementations (both API and web scraping).
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from miners.zillow.shared.zillow_schema import ZillowRealEstateContent
from miners.shared.miner_factory import MinerFactory, MinerPlatform, MinerImplementation
from common.data import DataEntity, DataSource, DataLabel
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig


class TestZillowSchema:
    """Test Zillow-specific schema"""
    
    def test_zillow_schema_creation(self):
        """Test creating ZillowRealEstateContent from API data"""
        api_data = {
            "zpid": "98970000",
            "address": "123 Main St, New York, NY 10001",
            "detailUrl": "https://zillow.com/homedetails/123-Main-St/98970000_zpid/",
            "price": 500000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "livingArea": 1500,
            "propertyType": "SINGLE_FAMILY",
            "yearBuilt": 2000,
            "listingStatus": "FOR_SALE",
            "zestimate": 485000,
            "rentZestimate": 3200,
            "daysOnZillow": 15,
            "hasImage": True,
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        
        content = ZillowRealEstateContent.from_zillow_api(api_data)
        
        assert content.zpid == "98970000"
        assert content.source_platform == "zillow"
        assert content.price == 500000
        assert content.bedrooms == 3
        assert content.bathrooms == 2.5
        assert content.zestimate == 485000
        assert content.days_on_zillow == 15
        assert content.get_platform_source() == DataSource.ZILLOW
    
    def test_zillow_web_scraping_schema(self):
        """Test creating ZillowRealEstateContent from web scraping data"""
        scraped_data = {
            "address": "456 Oak Ave, Los Angeles, CA 90210",
            "price": 750000,
            "bedrooms": 4,
            "bathrooms": 3,
            "living_area": 2000,
            "zestimate": 740000,
            "photos": ["https://photos.zillowstatic.com/1.jpg", "https://photos.zillowstatic.com/2.jpg"],
            "agent_name": "John Doe"
        }
        
        content = ZillowRealEstateContent.from_web_scraping(scraped_data, "98970001")
        
        assert content.zpid == "98970001"
        assert content.source_platform == "zillow"
        assert content.scraping_method == "web_scraping"
        assert content.price == 750000
        assert content.bedrooms == 4
        assert content.carousel_photos == scraped_data["photos"]
        assert content.agent_name == "John Doe"
    
    def test_zillow_to_data_entity(self):
        """Test converting ZillowRealEstateContent to DataEntity"""
        content = ZillowRealEstateContent(
            source_id="98970000",
            source_platform="zillow",
            zpid="98970000",
            address="123 Main St, New York, NY 10001",
            detail_url="https://zillow.com/homedetails/123-Main-St/98970000_zpid/",
            price=500000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="api"
        )
        
        entity = content.to_data_entity()
        
        assert isinstance(entity, DataEntity)
        assert entity.source == DataSource.ZILLOW
        assert entity.uri == "https://zillow.com/homedetails/123-Main-St/98970000_zpid/"
        assert entity.content_size_bytes > 0
        
        # Test content can be decoded
        decoded_content = json.loads(entity.content.decode('utf-8'))
        assert decoded_content["zpid"] == "98970000"
        assert decoded_content["price"] == 500000
    
    def test_zillow_investment_metrics(self):
        """Test investment metrics calculation"""
        content = ZillowRealEstateContent(
            source_id="98970000",
            source_platform="zillow",
            zpid="98970000",
            address="123 Main St, New York, NY 10001",
            detail_url="https://zillow.com/homedetails/123-Main-St/98970000_zpid/",
            price=500000,
            living_area=1500,
            rent_zestimate=3000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="api"
        )
        
        metrics = content.get_investment_metrics()
        
        assert "price_per_sqft" in metrics
        assert metrics["price_per_sqft"] == 333.33  # 500000 / 1500
        assert "price_to_rent_ratio" in metrics
        assert "gross_rental_yield" in metrics
    
    def test_zillow_zestimate_accuracy(self):
        """Test Zestimate accuracy calculation"""
        content = ZillowRealEstateContent(
            source_id="98970000",
            source_platform="zillow",
            zpid="98970000",
            address="123 Main St, New York, NY 10001",
            detail_url="https://zillow.com/homedetails/123-Main-St/98970000_zpid/",
            price=500000,
            zestimate=485000,  # 3% difference
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="api"
        )
        
        accuracy = content.get_zestimate_accuracy()
        assert accuracy == "Very Accurate"  # < 5% difference


class TestZillowMinerFactory:
    """Test Zillow miner factory integration"""
    
    def test_zillow_web_scraping_factory(self):
        """Test creating Zillow web scraping miner via factory"""
        factory = MinerFactory()
        scraper = factory.create_scraper(MinerPlatform.ZILLOW, MinerImplementation.WEB_SCRAPING)
        
        assert scraper is not None
        assert hasattr(scraper, 'scrape')
        assert hasattr(scraper, 'validate')
    
    @patch.dict('os.environ', {'MINER_PLATFORM': 'zillow', 'MINER_IMPLEMENTATION': 'web_scraping'})
    def test_zillow_environment_config(self):
        """Test Zillow miner creation from environment variables"""
        factory = MinerFactory()
        scraper = factory.create_scraper()
        
        assert scraper is not None
    
    def test_zillow_data_source_mapping(self):
        """Test DataSource mapping for Zillow"""
        factory = MinerFactory()
        source = factory.get_data_source_for_platform(MinerPlatform.ZILLOW)
        
        assert source == DataSource.ZILLOW


@pytest.mark.asyncio
class TestZillowWebScraper:
    """Test Zillow web scraper implementation"""
    
    @patch('miners.zillow.web_scraping_implementation.direct_zillow_miner.uc.Chrome')
    async def test_scraper_initialization(self, mock_chrome):
        """Test scraper initialization"""
        from miners.zillow.web_scraping_implementation.direct_zillow_miner import DirectZillowScraper
        
        scraper = DirectZillowScraper()
        
        assert scraper.rate_limiter is not None
        assert scraper.max_session_requests == 20
        assert len(scraper.user_agents) > 0
    
    @patch('miners.zillow.web_scraping_implementation.direct_zillow_miner.uc.Chrome')
    async def test_zpid_url_construction(self, mock_chrome):
        """Test ZPID to URL conversion"""
        from miners.zillow.web_scraping_implementation.direct_zillow_miner import DirectZillowScraper
        
        scraper = DirectZillowScraper()
        
        # Mock the URL construction method
        url = await scraper._zpid_to_url("98970000")
        
        assert url is not None
        assert "98970000" in url
        assert "zillow.com" in url
    
    @patch('miners.zillow.web_scraping_implementation.direct_zillow_miner.uc.Chrome')
    async def test_scrape_configuration(self, mock_chrome):
        """Test scrape method with configuration"""
        from miners.zillow.web_scraping_implementation.direct_zillow_miner import DirectZillowScraper
        
        # Mock the driver and its methods
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        scraper = DirectZillowScraper()
        
        # Mock the scrape_zpid method to return a test entity
        test_content = ZillowRealEstateContent(
            source_id="98970000",
            source_platform="zillow",
            zpid="98970000",
            address="123 Test St, Test City, TS 12345",
            detail_url="https://zillow.com/test",
            price=400000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        test_entity = test_content.to_data_entity()
        
        with patch.object(scraper, 'scrape_zpid', return_value=test_entity):
            config = ScrapeConfig(
                entity_limit=1,
                date_range=DateRange(
                    start=datetime.now(timezone.utc),
                    end=datetime.now(timezone.utc)
                ),
                labels=[DataLabel(value="zpid:98970000")]
            )
            
            entities = await scraper.scrape(config)
            
            assert len(entities) == 1
            assert entities[0].source == DataSource.ZILLOW
    
    def test_zpid_extraction_from_uri(self):
        """Test ZPID extraction from URI"""
        from miners.zillow.web_scraping_implementation.direct_zillow_miner import DirectZillowScraper
        
        scraper = DirectZillowScraper()
        
        uri = "https://zillow.com/homedetails/123-Main-St/98970000_zpid/"
        zpid = scraper._extract_zpid_from_uri(uri)
        
        assert zpid == "98970000"
    
    @patch('miners.zillow.web_scraping_implementation.direct_zillow_miner.uc.Chrome')
    async def test_validation_process(self, mock_chrome):
        """Test entity validation process"""
        from miners.zillow.web_scraping_implementation.direct_zillow_miner import DirectZillowScraper
        
        scraper = DirectZillowScraper()
        
        # Create test entity
        test_content = ZillowRealEstateContent(
            source_id="98970000",
            source_platform="zillow",
            zpid="98970000",
            address="123 Test St, Test City, TS 12345",
            detail_url="https://zillow.com/homedetails/123-Test-St/98970000_zpid/",
            price=400000,
            bedrooms=3,
            bathrooms=2,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        test_entity = test_content.to_data_entity()
        
        # Mock scrape_zpid to return the same entity for validation
        with patch.object(scraper, 'scrape_zpid', return_value=test_entity):
            results = await scraper.validate([test_entity])
            
            assert len(results) == 1
            assert results[0].is_valid is True


class TestZillowProtocolIntegration:
    """Test Zillow integration with the unified protocol"""
    
    def test_zpid_label_creation(self):
        """Test creating ZPID labels for scraping"""
        zpids = ["98970000", "98970001", "98970002"]
        labels = [DataLabel(value=f"zpid:{zpid}") for zpid in zpids]
        
        assert len(labels) == 3
        assert labels[0].value == "zpid:98970000"
        assert labels[1].value == "zpid:98970001"
        assert labels[2].value == "zpid:98970002"
    
    def test_zillow_request_validation(self):
        """Test Zillow request validation"""
        from miners.shared.protocol import RequestValidator, MultiSourceRequest
        
        # Valid request
        valid_request = MultiSourceRequest(
            source=DataSource.ZILLOW,
            zpids=["98970000", "98970001"]
        )
        
        errors = RequestValidator.validate_request(valid_request)
        assert len(errors) == 0
        
        # Invalid request (no ZPIDs)
        invalid_request = MultiSourceRequest(
            source=DataSource.ZILLOW,
            zpids=[]
        )
        
        errors = RequestValidator.validate_request(invalid_request)
        assert len(errors) > 0
        assert "ZPIDs required" in errors[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
