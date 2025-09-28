"""
Tests for Realtor.com and Homes.com miner implementations.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from miners.realtor_com.shared.realtor_schema import RealtorRealEstateContent
from miners.homes_com.shared.homes_schema import HomesRealEstateContent
from miners.shared.miner_factory import MinerFactory, MinerPlatform, MinerImplementation
from common.data import DataEntity, DataSource, DataLabel
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig


class TestRealtorSchema:
    """Test Realtor.com-specific schema"""
    
    def test_realtor_schema_creation(self):
        """Test creating RealtorRealEstateContent from web scraping data"""
        scraped_data = {
            "address": "789 Elm St, Austin, TX 78701",
            "detail_url": "https://www.realtor.com/realestateandhomes-detail/789-Elm-St_Austin_TX",
            "price": 450000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "square_feet": 1600,
            "property_type": "SINGLE_FAMILY",
            "year_built": 2005,
            "list_price": 450000,
            "price_per_sqft": 281.25,
            "days_on_market": 8,
            "mls_id": "MLS12345",
            "garage_spaces": 2,
            "hoa_fee": 150,
            "property_tax": 6500,
            "virtual_tour_available": True,
            "listing_agent_name": "Jane Smith",
            "listing_office": "Austin Realty Group"
        }
        
        content = RealtorRealEstateContent.from_web_scraping(scraped_data, scraped_data["address"])
        
        assert content.source_platform == "realtor_com"
        assert content.scraping_method == "web_scraping"
        assert content.price == 450000
        assert content.bedrooms == 3
        assert content.square_feet == 1600
        assert content.mls_id == "MLS12345"
        assert content.garage_spaces == 2
        assert content.virtual_tour_available is True
        assert content.get_platform_source() == DataSource.REALTOR_COM
    
    def test_realtor_to_data_entity(self):
        """Test converting RealtorRealEstateContent to DataEntity"""
        content = RealtorRealEstateContent(
            source_id="test_id",
            source_platform="realtor_com",
            address="789 Elm St, Austin, TX 78701",
            detail_url="https://www.realtor.com/realestateandhomes-detail/789-Elm-St_Austin_TX",
            price=450000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        entity = content.to_data_entity()
        
        assert isinstance(entity, DataEntity)
        assert entity.source == DataSource.REALTOR_COM
        assert entity.content_size_bytes > 0
        
        # Test content can be decoded
        decoded_content = json.loads(entity.content.decode('utf-8'))
        assert decoded_content["address"] == "789 Elm St, Austin, TX 78701"
        assert decoded_content["price"] == 450000
    
    def test_realtor_property_features_summary(self):
        """Test property features summary"""
        content = RealtorRealEstateContent(
            source_id="test_id",
            source_platform="realtor_com",
            address="789 Elm St, Austin, TX 78701",
            detail_url="https://www.realtor.com/test",
            price=450000,
            living_area=1600,
            estimated_monthly_payment=2500,
            new_construction=True,
            virtual_tour_available=True,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        summary = content.get_property_features_summary()
        
        assert "price_per_sqft" in summary
        assert summary["price_per_sqft"] == 281.25  # 450000 / 1600
        assert summary["estimated_monthly_payment"] == 2500
        assert summary["new_construction"] is True
        assert summary["has_virtual_tour"] is True


class TestHomesSchema:
    """Test Homes.com-specific schema"""
    
    def test_homes_schema_creation(self):
        """Test creating HomesRealEstateContent from web scraping data"""
        scraped_data = {
            "address": "321 Oak Dr, Denver, CO 80202",
            "detail_url": "https://www.homes.com/property/321-Oak-Dr-Denver-CO/abc123def/",
            "price": 550000,
            "bedrooms": 4,
            "bathrooms": 3,
            "total_sqft": 2000,
            "property_type": "SINGLE_FAMILY",
            "year_built": 1998,
            "asking_price": 550000,
            "estimated_payment": 3200,
            "lot_size_sqft": 8000,
            "garage_spaces": 2,
            "levels": 2,
            "hoa_fee": 75,
            "property_taxes": 7500,
            "virtual_tour": True,
            "new_construction": False,
            "listing_agent": "Bob Johnson",
            "listing_office": "Denver Home Sales"
        }
        
        content = HomesRealEstateContent.from_web_scraping(scraped_data, scraped_data["address"])
        
        assert content.source_platform == "homes_com"
        assert content.scraping_method == "web_scraping"
        assert content.price == 550000
        assert content.bedrooms == 4
        assert content.total_sqft == 2000
        assert content.garage_spaces == 2
        assert content.levels == 2
        assert content.virtual_tour is True
        assert content.get_platform_source() == DataSource.HOMES_COM
    
    def test_homes_to_data_entity(self):
        """Test converting HomesRealEstateContent to DataEntity"""
        content = HomesRealEstateContent(
            source_id="test_id",
            source_platform="homes_com",
            address="321 Oak Dr, Denver, CO 80202",
            detail_url="https://www.homes.com/property/321-Oak-Dr-Denver-CO/abc123def/",
            price=550000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        entity = content.to_data_entity()
        
        assert isinstance(entity, DataEntity)
        assert entity.source == DataSource.HOMES_COM
        assert entity.content_size_bytes > 0
        
        # Test content can be decoded
        decoded_content = json.loads(entity.content.decode('utf-8'))
        assert decoded_content["address"] == "321 Oak Dr, Denver, CO 80202"
        assert decoded_content["price"] == 550000
    
    def test_homes_financial_breakdown(self):
        """Test financial breakdown calculation"""
        content = HomesRealEstateContent(
            source_id="test_id",
            source_platform="homes_com",
            address="321 Oak Dr, Denver, CO 80202",
            detail_url="https://www.homes.com/test",
            price=550000,
            estimated_payment=3200,
            down_payment=110000,  # 20%
            property_taxes=7500,  # Annual
            hoa_fee=75,  # Monthly
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        breakdown = content.get_financial_breakdown()
        
        assert breakdown["listing_price"] == 550000
        assert breakdown["down_payment"] == 110000
        assert breakdown["down_payment_percent"] == 20.0
        assert breakdown["monthly_payment"] == 3200
        assert breakdown["monthly_tax"] == 625.0  # 7500 / 12
        assert breakdown["monthly_hoa"] == 75
        assert "total_monthly_cost" in breakdown


class TestAddressBasedMinerFactory:
    """Test address-based miner factory integration"""
    
    def test_realtor_web_scraping_factory(self):
        """Test creating Realtor.com web scraping miner via factory"""
        factory = MinerFactory()
        scraper = factory.create_scraper(MinerPlatform.REALTOR_COM, MinerImplementation.WEB_SCRAPING)
        
        assert scraper is not None
        assert hasattr(scraper, 'scrape')
        assert hasattr(scraper, 'validate')
    
    def test_homes_web_scraping_factory(self):
        """Test creating Homes.com web scraping miner via factory"""
        factory = MinerFactory()
        scraper = factory.create_scraper(MinerPlatform.HOMES_COM, MinerImplementation.WEB_SCRAPING)
        
        assert scraper is not None
        assert hasattr(scraper, 'scrape')
        assert hasattr(scraper, 'validate')
    
    @patch.dict('os.environ', {'MINER_PLATFORM': 'realtor_com', 'MINER_IMPLEMENTATION': 'web_scraping'})
    def test_realtor_environment_config(self):
        """Test Realtor.com miner creation from environment variables"""
        factory = MinerFactory()
        scraper = factory.create_scraper()
        
        assert scraper is not None
    
    @patch.dict('os.environ', {'MINER_PLATFORM': 'homes_com', 'MINER_IMPLEMENTATION': 'web_scraping'})
    def test_homes_environment_config(self):
        """Test Homes.com miner creation from environment variables"""
        factory = MinerFactory()
        scraper = factory.create_scraper()
        
        assert scraper is not None


@pytest.mark.asyncio
class TestRealtorWebScraper:
    """Test Realtor.com web scraper implementation"""
    
    @patch('miners.realtor_com.web_scraping_implementation.direct_realtor_miner.uc.Chrome')
    async def test_realtor_scraper_initialization(self, mock_chrome):
        """Test Realtor.com scraper initialization"""
        from miners.realtor_com.web_scraping_implementation.direct_realtor_miner import DirectRealtorScraper
        
        scraper = DirectRealtorScraper()
        
        assert scraper.rate_limiter is not None
        assert scraper.max_session_requests == 10
        assert len(scraper.user_agents) > 0
    
    def test_realtor_address_cleaning(self):
        """Test address cleaning for search"""
        from miners.realtor_com.web_scraping_implementation.direct_realtor_miner import DirectRealtorScraper
        
        scraper = DirectRealtorScraper()
        
        # Test address cleaning
        address = "123 Main St Apt 2B, New York, NY 10001"
        cleaned = scraper._clean_address_for_search(address)
        
        assert "Apt 2B" not in cleaned  # Should remove apartment numbers
        assert "123 Main St" in cleaned
    
    def test_realtor_address_parsing(self):
        """Test address parsing into components"""
        from miners.realtor_com.web_scraping_implementation.direct_realtor_miner import DirectRealtorScraper
        
        scraper = DirectRealtorScraper()
        
        address = "123 Main St, New York, NY 10001"
        parts = scraper._parse_address(address)
        
        assert parts["street"] == "123 Main St"
        assert parts["city"] == "New York"
        assert parts["state"] == "NY"
        assert parts["zip"] == "10001"
    
    def test_realtor_address_matching(self):
        """Test address matching logic"""
        from miners.realtor_com.web_scraping_implementation.direct_realtor_miner import DirectRealtorScraper
        
        scraper = DirectRealtorScraper()
        
        search_address = "123 Main Street, New York, NY"
        card_address = "123 Main St, New York, New York"
        
        assert scraper._addresses_match(search_address, card_address) is True
        
        # Test non-matching addresses
        different_address = "456 Oak Avenue, Los Angeles, CA"
        assert scraper._addresses_match(search_address, different_address) is False


@pytest.mark.asyncio
class TestHomesWebScraper:
    """Test Homes.com web scraper implementation"""
    
    @patch('miners.homes_com.web_scraping_implementation.direct_homes_miner.uc.Chrome')
    async def test_homes_scraper_initialization(self, mock_chrome):
        """Test Homes.com scraper initialization"""
        from miners.homes_com.web_scraping_implementation.direct_homes_miner import DirectHomesScraper
        
        scraper = DirectHomesScraper()
        
        assert scraper.rate_limiter is not None
        assert scraper.max_session_requests == 8  # More conservative
        assert len(scraper.user_agents) > 0
    
    def test_homes_address_cleaning(self):
        """Test address cleaning for search"""
        from miners.homes_com.web_scraping_implementation.direct_homes_miner import DirectHomesScraper
        
        scraper = DirectHomesScraper()
        
        # Test address cleaning
        address = "456 Oak Ave Unit 5, Los Angeles, CA 90210"
        cleaned = scraper._clean_address_for_search(address)
        
        assert "Unit 5" not in cleaned  # Should remove unit numbers
        assert "456 Oak Ave" in cleaned
    
    @patch('miners.homes_com.web_scraping_implementation.direct_homes_miner.uc.Chrome')
    async def test_homes_scrape_configuration(self, mock_chrome):
        """Test Homes.com scrape method with configuration"""
        from miners.homes_com.web_scraping_implementation.direct_homes_miner import DirectHomesScraper
        
        # Mock the driver
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        scraper = DirectHomesScraper()
        
        # Mock the scrape_address method to return a test entity
        test_content = HomesRealEstateContent(
            source_id="test_id",
            source_platform="homes_com",
            address="456 Test Ave, Test City, TS 12345",
            detail_url="https://homes.com/test",
            price=400000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        test_entity = test_content.to_data_entity()
        
        with patch.object(scraper, 'scrape_address', return_value=test_entity):
            config = ScrapeConfig(
                entity_limit=1,
                date_range=DateRange(
                    start=datetime.now(timezone.utc),
                    end=datetime.now(timezone.utc)
                ),
                labels=[DataLabel(value="address:456 Test Ave, Test City, TS 12345")]
            )
            
            entities = await scraper.scrape(config)
            
            assert len(entities) == 1
            assert entities[0].source == DataSource.HOMES_COM


class TestAddressBasedProtocolIntegration:
    """Test address-based platforms integration with unified protocol"""
    
    def test_address_label_creation(self):
        """Test creating address labels for scraping"""
        addresses = [
            "123 Main St, New York, NY 10001",
            "456 Oak Ave, Los Angeles, CA 90210",
            "789 Pine St, Chicago, IL 60601"
        ]
        labels = [DataLabel(value=f"address:{addr}") for addr in addresses]
        
        assert len(labels) == 3
        assert labels[0].value == "address:123 Main St, New York, NY 10001"
        assert labels[1].value == "address:456 Oak Ave, Los Angeles, CA 90210"
        assert labels[2].value == "address:789 Pine St, Chicago, IL 60601"
    
    def test_realtor_request_validation(self):
        """Test Realtor.com request validation"""
        from miners.shared.protocol import RequestValidator, MultiSourceRequest
        
        # Valid request
        valid_request = MultiSourceRequest(
            source=DataSource.REALTOR_COM,
            addresses=["123 Main St, New York, NY 10001", "456 Oak Ave, Los Angeles, CA 90210"]
        )
        
        errors = RequestValidator.validate_request(valid_request)
        assert len(errors) == 0
        
        # Invalid request (no addresses)
        invalid_request = MultiSourceRequest(
            source=DataSource.REALTOR_COM,
            addresses=[]
        )
        
        errors = RequestValidator.validate_request(invalid_request)
        assert len(errors) > 0
        assert "Addresses required" in errors[0]
    
    def test_homes_request_validation(self):
        """Test Homes.com request validation"""
        from miners.shared.protocol import RequestValidator, MultiSourceRequest
        
        # Valid request
        valid_request = MultiSourceRequest(
            source=DataSource.HOMES_COM,
            addresses=["123 Main St, New York, NY 10001"]
        )
        
        errors = RequestValidator.validate_request(valid_request)
        assert len(errors) == 0
        
        # Invalid request (invalid address)
        invalid_request = MultiSourceRequest(
            source=DataSource.HOMES_COM,
            addresses=["123"]  # Too short
        )
        
        errors = RequestValidator.validate_request(invalid_request)
        assert len(errors) > 0
        assert "Invalid addresses" in errors[0]
    
    def test_address_validation(self):
        """Test address validation function"""
        from miners.shared.protocol import is_valid_address
        
        # Valid addresses
        assert is_valid_address("123 Main St, New York, NY 10001") is True
        assert is_valid_address("456 Oak Avenue, Los Angeles, CA 90210") is True
        assert is_valid_address("789 Pine Street, Chicago, IL 60601") is True
        
        # Invalid addresses
        assert is_valid_address("") is False
        assert is_valid_address("123") is False  # Too short
        assert is_valid_address("Main Street") is False  # No numbers
        assert is_valid_address("123 NoStreetType") is False  # No street type


class TestCrossValidationCapability:
    """Test cross-platform validation capabilities"""
    
    def test_address_normalization(self):
        """Test address normalization for cross-validation"""
        from miners.shared.protocol import normalize_address
        
        address1 = "123 Main Street, New York, NY 10001"
        address2 = "123 Main St, New York, NY 10001"
        
        normalized1 = normalize_address(address1)
        normalized2 = normalize_address(address2)
        
        # Both should normalize to the same format
        assert "Main St" in normalized1
        assert "Main St" in normalized2
    
    def test_multi_platform_data_comparison(self):
        """Test comparing same property across platforms"""
        address = "123 Main St, New York, NY 10001"
        
        # Create same property from different platforms
        realtor_content = RealtorRealEstateContent(
            source_id="realtor_123",
            source_platform="realtor_com",
            address=address,
            detail_url="https://realtor.com/test",
            price=500000,
            bedrooms=3,
            bathrooms=2,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        homes_content = HomesRealEstateContent(
            source_id="homes_123",
            source_platform="homes_com",
            address=address,
            detail_url="https://homes.com/test",
            price=505000,  # Slightly different price
            bedrooms=3,
            bathrooms=2,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        # Both should have same basic properties
        assert realtor_content.address == homes_content.address
        assert realtor_content.bedrooms == homes_content.bedrooms
        assert realtor_content.bathrooms == homes_content.bathrooms
        assert realtor_content.property_type == homes_content.property_type
        
        # Prices might differ slightly between platforms
        price_diff = abs(realtor_content.price - homes_content.price)
        assert price_diff < 20000  # Within reasonable range


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
