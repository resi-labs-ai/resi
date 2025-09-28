"""
Tests for the miner factory and overall integration of all platforms.
"""

import pytest
import os
from unittest.mock import patch, Mock

from miners.shared.miner_factory import (
    MinerFactory, MinerPlatform, MinerImplementation, MinerConfig,
    get_scraper, get_scraper_for_source, list_available_implementations
)
from common.data import DataSource


class TestMinerFactory:
    """Test the MinerFactory class"""
    
    def test_factory_initialization(self):
        """Test factory initializes with default scrapers"""
        factory = MinerFactory()
        
        # Should have registered some scrapers
        available = factory.list_available_scrapers()
        assert len(available) > 0
        
        # Should have Zillow web scraping at minimum
        assert "zillow" in available
        assert available["zillow"]["web_scraping"] is True
    
    def test_scraper_registration(self):
        """Test manual scraper registration"""
        factory = MinerFactory()
        
        # Mock scraper class
        class MockScraper:
            pass
        
        # Register mock scraper
        factory.register_scraper(MinerPlatform.ZILLOW, MinerImplementation.API, MockScraper)
        
        # Should be able to create it
        scraper = factory.create_scraper(MinerPlatform.ZILLOW, MinerImplementation.API)
        assert isinstance(scraper, MockScraper)
    
    def test_data_source_mapping(self):
        """Test DataSource to platform mapping"""
        factory = MinerFactory()
        
        assert factory.get_data_source_for_platform(MinerPlatform.ZILLOW) == DataSource.ZILLOW
        assert factory.get_data_source_for_platform(MinerPlatform.REDFIN) == DataSource.REDFIN
        assert factory.get_data_source_for_platform(MinerPlatform.REALTOR_COM) == DataSource.REALTOR_COM
        assert factory.get_data_source_for_platform(MinerPlatform.HOMES_COM) == DataSource.HOMES_COM
    
    def test_scraper_for_source(self):
        """Test getting scraper by DataSource"""
        factory = MinerFactory()
        
        # Should be able to get scraper for each source
        zillow_scraper = factory.get_scraper_for_source(DataSource.ZILLOW)
        assert zillow_scraper is not None
        
        redfin_scraper = factory.get_scraper_for_source(DataSource.REDFIN)
        assert redfin_scraper is not None
    
    def test_invalid_platform_combination(self):
        """Test handling of invalid platform/implementation combinations"""
        factory = MinerFactory()
        
        # Try to get non-existent combination
        scraper = factory.create_scraper(MinerPlatform.ZILLOW, MinerImplementation.API)
        # Should either return None or a scraper depending on what's registered
        # The test is that it doesn't crash
        
    @patch.dict('os.environ', {'MINER_PLATFORM': 'zillow', 'MINER_IMPLEMENTATION': 'web_scraping'})
    def test_environment_configuration(self):
        """Test scraper creation from environment variables"""
        factory = MinerFactory()
        scraper = factory.create_scraper()
        
        assert scraper is not None
    
    @patch.dict('os.environ', {'MINER_PLATFORM': 'invalid_platform'})
    def test_invalid_environment_configuration(self):
        """Test handling of invalid environment configuration"""
        factory = MinerFactory()
        scraper = factory.create_scraper()
        
        # Should handle gracefully (return None or fallback)
        # The test is that it doesn't crash


class TestMinerConfig:
    """Test MinerConfig helper class"""
    
    @patch.dict('os.environ', {
        'MINER_PLATFORM': 'redfin',
        'MINER_IMPLEMENTATION': 'web_scraping',
        'MINER_RATE_LIMIT': '25',
        'MINER_MAX_BATCH_SIZE': '30'
    })
    def test_config_from_environment(self):
        """Test loading configuration from environment variables"""
        config = MinerConfig.from_environment()
        
        assert config['platform'] == 'redfin'
        assert config['implementation'] == 'web_scraping'
        assert config['rate_limit'] == 25
        assert config['max_batch_size'] == 30
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid configuration
        valid_config = {
            'platform': 'zillow',
            'implementation': 'web_scraping',
            'rate_limit': 30,
            'max_batch_size': 50,
            'timeout_seconds': 30
        }
        
        errors = MinerConfig.validate_config(valid_config)
        assert len(errors) == 0
        
        # Invalid configuration
        invalid_config = {
            'platform': 'invalid_platform',
            'implementation': 'invalid_implementation',
            'rate_limit': -5,
            'max_batch_size': 0
        }
        
        errors = MinerConfig.validate_config(invalid_config)
        assert len(errors) > 0
        assert any('platform' in error for error in errors)
        assert any('implementation' in error for error in errors)
        assert any('rate limit' in error for error in errors)
    
    def test_config_from_args(self):
        """Test loading configuration from command line arguments"""
        # Mock args object
        class MockArgs:
            miner_platform = 'homes_com'
            miner_implementation = 'web_scraping'
            miner_rate_limit = 15
        
        config = MinerConfig.from_args(MockArgs())
        
        assert config['platform'] == 'homes_com'
        assert config['implementation'] == 'web_scraping'
        assert config['rate_limit'] == 15


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_scraper_function(self):
        """Test get_scraper convenience function"""
        scraper = get_scraper('zillow', 'web_scraping')
        assert scraper is not None
        
        # Test with invalid parameters
        invalid_scraper = get_scraper('invalid_platform', 'web_scraping')
        assert invalid_scraper is None
    
    def test_get_scraper_for_source_function(self):
        """Test get_scraper_for_source convenience function"""
        scraper = get_scraper_for_source(DataSource.ZILLOW, 'web_scraping')
        assert scraper is not None
        
        scraper = get_scraper_for_source(DataSource.REDFIN, 'web_scraping')
        assert scraper is not None
    
    def test_list_available_implementations_function(self):
        """Test list_available_implementations convenience function"""
        available = list_available_implementations()
        
        assert isinstance(available, dict)
        assert 'zillow' in available
        assert 'redfin' in available
        assert 'realtor_com' in available
        assert 'homes_com' in available
        
        # Each platform should have implementation info
        for platform in available.values():
            assert 'web_scraping' in platform
            assert 'api' in platform


class TestPlatformEnumeration:
    """Test platform and implementation enumerations"""
    
    def test_miner_platform_enum(self):
        """Test MinerPlatform enum"""
        platforms = list(MinerPlatform)
        
        assert MinerPlatform.ZILLOW in platforms
        assert MinerPlatform.REDFIN in platforms
        assert MinerPlatform.REALTOR_COM in platforms
        assert MinerPlatform.HOMES_COM in platforms
        
        # Test string values
        assert MinerPlatform.ZILLOW.value == 'zillow'
        assert MinerPlatform.REDFIN.value == 'redfin'
        assert MinerPlatform.REALTOR_COM.value == 'realtor_com'
        assert MinerPlatform.HOMES_COM.value == 'homes_com'
    
    def test_miner_implementation_enum(self):
        """Test MinerImplementation enum"""
        implementations = list(MinerImplementation)
        
        assert MinerImplementation.WEB_SCRAPING in implementations
        assert MinerImplementation.API in implementations
        
        # Test string values
        assert MinerImplementation.WEB_SCRAPING.value == 'web_scraping'
        assert MinerImplementation.API.value == 'api'


class TestIntegrationScenarios:
    """Test various integration scenarios"""
    
    def test_all_platforms_web_scraping_available(self):
        """Test that web scraping is available for all platforms"""
        factory = MinerFactory()
        available = factory.list_available_scrapers()
        
        expected_platforms = ['zillow', 'redfin', 'realtor_com', 'homes_com']
        
        for platform in expected_platforms:
            assert platform in available
            assert available[platform]['web_scraping'] is True
    
    def test_platform_switching(self):
        """Test switching between different platforms"""
        factory = MinerFactory()
        
        # Should be able to create scrapers for different platforms
        zillow_scraper = factory.create_scraper(MinerPlatform.ZILLOW, MinerImplementation.WEB_SCRAPING)
        redfin_scraper = factory.create_scraper(MinerPlatform.REDFIN, MinerImplementation.WEB_SCRAPING)
        
        assert zillow_scraper is not None
        assert redfin_scraper is not None
        assert type(zillow_scraper) != type(redfin_scraper)  # Different classes
    
    @patch.dict('os.environ', {'MINER_PLATFORM': 'zillow'})
    def test_runtime_platform_detection(self):
        """Test runtime platform detection from environment"""
        factory = MinerFactory()
        
        # Should detect platform from environment
        platform = factory._get_platform_from_config()
        assert platform == MinerPlatform.ZILLOW
    
    @patch.dict('os.environ', {'MINER_IMPLEMENTATION': 'web_scraping'})
    def test_runtime_implementation_detection(self):
        """Test runtime implementation detection from environment"""
        factory = MinerFactory()
        
        # Should detect implementation from environment
        implementation = factory._get_implementation_from_config()
        assert implementation == MinerImplementation.WEB_SCRAPING
    
    def test_factory_error_handling(self):
        """Test factory error handling for various edge cases"""
        factory = MinerFactory()
        
        # Test with None parameters
        scraper = factory.create_scraper(None, None)
        assert scraper is None
        
        # Test with invalid DataSource
        scraper = factory.get_scraper_for_source(999)  # Invalid enum value
        assert scraper is None


class TestScraperInterfaceCompliance:
    """Test that all scrapers comply with the expected interface"""
    
    def test_all_scrapers_have_required_methods(self):
        """Test that all registered scrapers have required methods"""
        factory = MinerFactory()
        available = factory.list_available_scrapers()
        
        required_methods = ['scrape', 'validate']
        
        for platform_name, implementations in available.items():
            for impl_name, is_available in implementations.items():
                if is_available:
                    try:
                        platform = MinerPlatform(platform_name)
                        implementation = MinerImplementation(impl_name)
                        scraper = factory.create_scraper(platform, implementation)
                        
                        if scraper:
                            for method in required_methods:
                                assert hasattr(scraper, method), f"{platform_name}:{impl_name} missing {method}"
                    except ValueError:
                        # Skip invalid enum values
                        pass
    
    def test_scraper_async_compliance(self):
        """Test that scraper methods are properly async"""
        factory = MinerFactory()
        scraper = factory.create_scraper(MinerPlatform.ZILLOW, MinerImplementation.WEB_SCRAPING)
        
        if scraper:
            import asyncio
            import inspect
            
            # scrape method should be async
            assert inspect.iscoroutinefunction(scraper.scrape)
            
            # validate method should be async
            assert inspect.iscoroutinefunction(scraper.validate)


class TestDocumentationExamples:
    """Test examples that would be in documentation"""
    
    def test_basic_usage_example(self):
        """Test basic usage example from documentation"""
        # This is what a user would do
        factory = MinerFactory()
        scraper = factory.create_scraper(MinerPlatform.ZILLOW, MinerImplementation.WEB_SCRAPING)
        
        assert scraper is not None
        assert hasattr(scraper, 'scrape')
        assert hasattr(scraper, 'validate')
    
    @patch.dict('os.environ', {'MINER_PLATFORM': 'redfin', 'MINER_IMPLEMENTATION': 'web_scraping'})
    def test_environment_usage_example(self):
        """Test environment-based usage example"""
        # This is what a user would do with environment variables
        scraper = get_scraper()
        
        assert scraper is not None
    
    def test_source_based_usage_example(self):
        """Test DataSource-based usage example"""
        # This is how the main miner.py would use it
        scraper = get_scraper_for_source(DataSource.ZILLOW)
        
        assert scraper is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
