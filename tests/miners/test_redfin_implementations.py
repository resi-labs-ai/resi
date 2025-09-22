"""
Tests for Redfin miner implementations.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from miners.redfin.shared.redfin_schema import RedfinRealEstateContent
from miners.shared.miner_factory import MinerFactory, MinerPlatform, MinerImplementation
from common.data import DataEntity, DataSource, DataLabel
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig


class TestRedfinSchema:
    """Test Redfin-specific schema"""
    
    def test_redfin_schema_creation(self):
        """Test creating RedfinRealEstateContent from web scraping data"""
        scraped_data = {
            "address": "456 Pine St, Seattle, WA 98101",
            "detail_url": "https://www.redfin.com/WA/Seattle/456-Pine-St/home/20635864",
            "price": 650000,
            "bedrooms": 3,
            "bathrooms": 2,
            "living_area": 1800,
            "property_type": "SINGLE_FAMILY",
            "year_built": 1995,
            "redfin_estimate": 635000,
            "walk_score": 85,
            "transit_score": 72,
            "bike_score": 68,
            "days_on_redfin": 12,
            "market_competition": "High",
            "has_tour": True,
            "is_hot_home": True
        }
        
        content = RedfinRealEstateContent.from_web_scraping(scraped_data, "20635864")
        
        assert content.redfin_id == "20635864"
        assert content.source_platform == "redfin"
        assert content.scraping_method == "web_scraping"
        assert content.price == 650000
        assert content.bedrooms == 3
        assert content.redfin_estimate == 635000
        assert content.walk_score == 85
        assert content.days_on_redfin == 12
        assert content.has_tour is True
        assert content.get_platform_source() == DataSource.REDFIN
    
    def test_redfin_to_data_entity(self):
        """Test converting RedfinRealEstateContent to DataEntity"""
        content = RedfinRealEstateContent(
            source_id="20635864",
            source_platform="redfin",
            redfin_id="20635864",
            address="456 Pine St, Seattle, WA 98101",
            detail_url="https://www.redfin.com/WA/Seattle/456-Pine-St/home/20635864",
            price=650000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        entity = content.to_data_entity()
        
        assert isinstance(entity, DataEntity)
        assert entity.source == DataSource.REDFIN
        assert entity.uri == "https://www.redfin.com/WA/Seattle/456-Pine-St/home/20635864"
        assert entity.content_size_bytes > 0
        
        # Test content can be decoded
        decoded_content = json.loads(entity.content.decode('utf-8'))
        assert decoded_content["redfin_id"] == "20635864"
        assert decoded_content["price"] == 650000
    
    def test_redfin_walkability_rating(self):
        """Test walkability rating description"""
        content = RedfinRealEstateContent(
            source_id="20635864",
            source_platform="redfin",
            redfin_id="20635864",
            address="456 Pine St, Seattle, WA 98101",
            detail_url="https://www.redfin.com/WA/Seattle/456-Pine-St/home/20635864",
            walk_score=85,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        rating = content.get_walkability_rating()
        assert rating == "Very Walkable"  # 70-89 range
    
    def test_redfin_monthly_cost_calculation(self):
        """Test total monthly cost calculation"""
        content = RedfinRealEstateContent(
            source_id="20635864",
            source_platform="redfin",
            redfin_id="20635864",
            address="456 Pine St, Seattle, WA 98101",
            detail_url="https://www.redfin.com/WA/Seattle/456-Pine-St/home/20635864",
            price=500000,
            property_taxes=8000,  # Annual
            insurance_cost=1200,  # Annual
            hoa_fee=200,  # Monthly
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        
        monthly_cost = content.calculate_total_monthly_cost()
        
        assert monthly_cost is not None
        assert monthly_cost > 0
        # Should include mortgage + taxes + insurance + HOA
        # Property taxes: 8000/12 = 666.67
        # Insurance: 1200/12 = 100
        # HOA: 200
        # Plus mortgage payment (estimated)


class TestRedfinMinerFactory:
    """Test Redfin miner factory integration"""
    
    def test_redfin_web_scraping_factory(self):
        """Test creating Redfin web scraping miner via factory"""
        factory = MinerFactory()
        scraper = factory.create_scraper(MinerPlatform.REDFIN, MinerImplementation.WEB_SCRAPING)
        
        assert scraper is not None
        assert hasattr(scraper, 'scrape')
        assert hasattr(scraper, 'validate')
    
    @patch.dict('os.environ', {'MINER_PLATFORM': 'redfin', 'MINER_IMPLEMENTATION': 'web_scraping'})
    def test_redfin_environment_config(self):
        """Test Redfin miner creation from environment variables"""
        factory = MinerFactory()
        scraper = factory.create_scraper()
        
        assert scraper is not None
    
    def test_redfin_data_source_mapping(self):
        """Test DataSource mapping for Redfin"""
        factory = MinerFactory()
        source = factory.get_data_source_for_platform(MinerPlatform.REDFIN)
        
        assert source == DataSource.REDFIN


@pytest.mark.asyncio
class TestRedfinWebScraper:
    """Test Redfin web scraper implementation"""
    
    @patch('miners.redfin.web_scraping_implementation.direct_redfin_miner.uc.Chrome')
    async def test_scraper_initialization(self, mock_chrome):
        """Test scraper initialization"""
        from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
        
        scraper = DirectRedfinScraper()
        
        assert scraper.rate_limiter is not None
        assert scraper.max_session_requests == 15
        assert len(scraper.user_agents) > 0
    
    @patch('miners.redfin.web_scraping_implementation.direct_redfin_miner.uc.Chrome')
    async def test_redfin_id_url_construction(self, mock_chrome):
        """Test Redfin ID to URL conversion"""
        from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
        
        scraper = DirectRedfinScraper()
        
        # Mock the URL construction method
        url = await scraper._redfin_id_to_url("20635864")
        
        assert url is not None
        assert "20635864" in url
        assert "redfin.com" in url
    
    @patch('miners.redfin.web_scraping_implementation.direct_redfin_miner.uc.Chrome')
    async def test_scrape_configuration(self, mock_chrome):
        """Test scrape method with configuration"""
        from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
        
        # Mock the driver and its methods
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        scraper = DirectRedfinScraper()
        
        # Mock the scrape_redfin_id method to return a test entity
        test_content = RedfinRealEstateContent(
            source_id="20635864",
            source_platform="redfin",
            redfin_id="20635864",
            address="456 Test St, Test City, TS 12345",
            detail_url="https://redfin.com/test",
            price=500000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        test_entity = test_content.to_data_entity()
        
        with patch.object(scraper, 'scrape_redfin_id', return_value=test_entity):
            config = ScrapeConfig(
                entity_limit=1,
                date_range=DateRange(
                    start=datetime.now(timezone.utc),
                    end=datetime.now(timezone.utc)
                ),
                labels=[DataLabel(value="redfin_id:20635864")]
            )
            
            entities = await scraper.scrape(config)
            
            assert len(entities) == 1
            assert entities[0].source == DataSource.REDFIN
    
    def test_redfin_id_extraction_from_entity(self):
        """Test Redfin ID extraction from entity"""
        from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
        
        scraper = DirectRedfinScraper()
        
        # Test URI extraction
        test_content = RedfinRealEstateContent(
            source_id="20635864",
            source_platform="redfin",
            redfin_id="20635864",
            address="456 Test St, Test City, TS 12345",
            detail_url="https://www.redfin.com/home/20635864",
            price=500000,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        test_entity = test_content.to_data_entity()
        
        redfin_id = scraper._extract_redfin_id_from_entity(test_entity)
        assert redfin_id == "20635864"
    
    @patch('miners.redfin.web_scraping_implementation.direct_redfin_miner.uc.Chrome')
    async def test_validation_process(self, mock_chrome):
        """Test entity validation process"""
        from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
        
        scraper = DirectRedfinScraper()
        
        # Create test entity
        test_content = RedfinRealEstateContent(
            source_id="20635864",
            source_platform="redfin",
            redfin_id="20635864",
            address="456 Test St, Test City, TS 12345",
            detail_url="https://www.redfin.com/home/20635864",
            price=500000,
            bedrooms=3,
            bathrooms=2,
            property_type="SINGLE_FAMILY",
            listing_status="FOR_SALE",
            scraping_method="web_scraping"
        )
        test_entity = test_content.to_data_entity()
        
        # Mock scrape_redfin_id to return the same entity for validation
        with patch.object(scraper, 'scrape_redfin_id', return_value=test_entity):
            results = await scraper.validate([test_entity])
            
            assert len(results) == 1
            assert results[0].is_valid is True


class TestRedfinProtocolIntegration:
    """Test Redfin integration with the unified protocol"""
    
    def test_redfin_id_label_creation(self):
        """Test creating Redfin ID labels for scraping"""
        redfin_ids = ["20635864", "20635865", "20635866"]
        labels = [DataLabel(value=f"redfin_id:{rid}") for rid in redfin_ids]
        
        assert len(labels) == 3
        assert labels[0].value == "redfin_id:20635864"
        assert labels[1].value == "redfin_id:20635865"
        assert labels[2].value == "redfin_id:20635866"
    
    def test_redfin_request_validation(self):
        """Test Redfin request validation"""
        from miners.shared.protocol import RequestValidator, MultiSourceRequest
        
        # Valid request
        valid_request = MultiSourceRequest(
            source=DataSource.REDFIN,
            redfin_ids=["20635864", "20635865"]
        )
        
        errors = RequestValidator.validate_request(valid_request)
        assert len(errors) == 0
        
        # Invalid request (no Redfin IDs)
        invalid_request = MultiSourceRequest(
            source=DataSource.REDFIN,
            redfin_ids=[]
        )
        
        errors = RequestValidator.validate_request(invalid_request)
        assert len(errors) > 0
        assert "Redfin IDs required" in errors[0]


class TestRedfinDataExtraction:
    """Test Redfin-specific data extraction features"""
    
    @patch('miners.redfin.web_scraping_implementation.direct_redfin_miner.uc.Chrome')
    def test_walkability_score_extraction(self, mock_chrome):
        """Test walkability score extraction from page"""
        from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
        
        scraper = DirectRedfinScraper()
        
        # Mock driver with walkability score elements
        mock_driver = Mock()
        mock_score_elem = Mock()
        mock_score_elem.text = "Walk Score: 85"
        mock_driver.find_elements.return_value = [mock_score_elem]
        
        data = scraper._extract_walkability_scores(mock_driver)
        
        assert "walk_score" in data
        assert data["walk_score"] == 85
    
    @patch('miners.redfin.web_scraping_implementation.direct_redfin_miner.uc.Chrome')
    def test_redfin_features_extraction(self, mock_chrome):
        """Test Redfin-specific features extraction"""
        from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
        
        scraper = DirectRedfinScraper()
        
        # Mock driver with page source containing features
        mock_driver = Mock()
        mock_driver.page_source = "virtual tour available hot home price reduced"
        
        data = scraper._extract_redfin_features(mock_driver)
        
        assert data.get("has_tour") is True
        assert data.get("is_hot_home") is True
        assert data.get("is_price_reduced") is True
    
    def test_redfin_id_validation(self):
        """Test Redfin ID validation"""
        from miners.shared.protocol import is_valid_redfin_id
        
        # Valid Redfin IDs
        assert is_valid_redfin_id("20635864") is True
        assert is_valid_redfin_id("1234567") is True
        
        # Invalid Redfin IDs
        assert is_valid_redfin_id("") is False
        assert is_valid_redfin_id("abc123") is False
        assert is_valid_redfin_id("12345") is False  # Too short
        assert is_valid_redfin_id("12345678901") is False  # Too long


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
