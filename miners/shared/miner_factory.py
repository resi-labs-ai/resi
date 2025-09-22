"""
Miner factory for runtime selection of different real estate scraping implementations.
Enables plug-and-play architecture for different platforms and methods.
"""

import os
import logging
from typing import Optional, Dict, Any, Type
from enum import Enum

from common.data import DataSource
from scraping.scraper import Scraper


class MinerImplementation(Enum):
    """Available miner implementation types"""
    WEB_SCRAPING = "web_scraping"
    API = "api"


class MinerPlatform(Enum):
    """Available real estate platforms"""
    ZILLOW = "zillow"
    REDFIN = "redfin"
    REALTOR_COM = "realtor_com"
    HOMES_COM = "homes_com"


class MinerFactory:
    """Factory for creating appropriate miner implementations"""
    
    def __init__(self):
        self._scrapers: Dict[tuple, Type[Scraper]] = {}
        self._register_default_scrapers()
    
    def _register_default_scrapers(self):
        """Register default scraper implementations"""
        try:
            # Zillow implementations
            from miners.zillow.web_scraping_implementation.direct_zillow_miner import DirectZillowScraper
            self.register_scraper(MinerPlatform.ZILLOW, MinerImplementation.WEB_SCRAPING, DirectZillowScraper)
            
            try:
                from miners.zillow.api_implementation.rapid_zillow_miner import ZillowRapidAPIScraper
                self.register_scraper(MinerPlatform.ZILLOW, MinerImplementation.API, ZillowRapidAPIScraper)
            except ImportError:
                logging.warning("Zillow API implementation not available")
            
            # Redfin implementations
            try:
                from miners.redfin.web_scraping_implementation.direct_redfin_miner import DirectRedfinScraper
                self.register_scraper(MinerPlatform.REDFIN, MinerImplementation.WEB_SCRAPING, DirectRedfinScraper)
            except ImportError:
                logging.warning("Redfin web scraping implementation not available")
            
            # Realtor.com implementations
            try:
                from miners.realtor_com.web_scraping_implementation.direct_realtor_miner import DirectRealtorScraper
                self.register_scraper(MinerPlatform.REALTOR_COM, MinerImplementation.WEB_SCRAPING, DirectRealtorScraper)
            except ImportError:
                logging.warning("Realtor.com web scraping implementation not available")
            
            # Homes.com implementations
            try:
                from miners.homes_com.web_scraping_implementation.direct_homes_miner import DirectHomesScraper
                self.register_scraper(MinerPlatform.HOMES_COM, MinerImplementation.WEB_SCRAPING, DirectHomesScraper)
            except ImportError:
                logging.warning("Homes.com web scraping implementation not available")
            
        except Exception as e:
            logging.error(f"Error registering default scrapers: {e}")
    
    def register_scraper(self, platform: MinerPlatform, implementation: MinerImplementation, scraper_class: Type[Scraper]):
        """Register a scraper implementation"""
        key = (platform, implementation)
        self._scrapers[key] = scraper_class
        logging.info(f"Registered scraper: {platform.value} - {implementation.value}")
    
    def create_scraper(self, platform: Optional[MinerPlatform] = None, implementation: Optional[MinerImplementation] = None) -> Optional[Scraper]:
        """Create a scraper instance based on configuration"""
        
        # Get configuration from environment or parameters
        if platform is None:
            platform = self._get_platform_from_config()
        
        if implementation is None:
            implementation = self._get_implementation_from_config()
        
        if not platform or not implementation:
            logging.error("Platform and implementation must be specified")
            return None
        
        # Get scraper class
        key = (platform, implementation)
        scraper_class = self._scrapers.get(key)
        
        if not scraper_class:
            logging.error(f"No scraper registered for {platform.value} - {implementation.value}")
            return None
        
        try:
            scraper = scraper_class()
            logging.info(f"Created scraper: {platform.value} - {implementation.value}")
            return scraper
        except Exception as e:
            logging.error(f"Error creating scraper {platform.value} - {implementation.value}: {e}")
            return None
    
    def _get_platform_from_config(self) -> Optional[MinerPlatform]:
        """Get platform from environment configuration"""
        platform_str = os.getenv("MINER_PLATFORM", "zillow").lower()
        
        platform_map = {
            "zillow": MinerPlatform.ZILLOW,
            "redfin": MinerPlatform.REDFIN,
            "realtor_com": MinerPlatform.REALTOR_COM,
            "realtor.com": MinerPlatform.REALTOR_COM,
            "homes_com": MinerPlatform.HOMES_COM,
            "homes.com": MinerPlatform.HOMES_COM,
        }
        
        return platform_map.get(platform_str)
    
    def _get_implementation_from_config(self) -> Optional[MinerImplementation]:
        """Get implementation from environment configuration"""
        impl_str = os.getenv("MINER_IMPLEMENTATION", "web_scraping").lower()
        
        impl_map = {
            "web_scraping": MinerImplementation.WEB_SCRAPING,
            "web": MinerImplementation.WEB_SCRAPING,
            "scraping": MinerImplementation.WEB_SCRAPING,
            "api": MinerImplementation.API,
            "rapid_api": MinerImplementation.API,
        }
        
        return impl_map.get(impl_str)
    
    def get_data_source_for_platform(self, platform: MinerPlatform) -> DataSource:
        """Get the appropriate DataSource enum for a platform"""
        platform_to_source = {
            MinerPlatform.ZILLOW: DataSource.ZILLOW,
            MinerPlatform.REDFIN: DataSource.REDFIN,
            MinerPlatform.REALTOR_COM: DataSource.REALTOR_COM,
            MinerPlatform.HOMES_COM: DataSource.HOMES_COM,
        }
        
        return platform_to_source.get(platform, DataSource.ZILLOW)
    
    def list_available_scrapers(self) -> Dict[str, Dict[str, bool]]:
        """List all available scraper implementations"""
        available = {}
        
        for platform in MinerPlatform:
            available[platform.value] = {}
            for implementation in MinerImplementation:
                key = (platform, implementation)
                available[platform.value][implementation.value] = key in self._scrapers
        
        return available
    
    def get_scraper_for_source(self, source: DataSource, implementation: Optional[MinerImplementation] = None) -> Optional[Scraper]:
        """Get scraper for a specific DataSource"""
        source_to_platform = {
            DataSource.ZILLOW: MinerPlatform.ZILLOW,
            DataSource.REDFIN: MinerPlatform.REDFIN,
            DataSource.REALTOR_COM: MinerPlatform.REALTOR_COM,
            DataSource.HOMES_COM: MinerPlatform.HOMES_COM,
        }
        
        platform = source_to_platform.get(source)
        if not platform:
            logging.error(f"No platform mapping for source: {source}")
            return None
        
        return self.create_scraper(platform, implementation)


class MinerConfig:
    """Configuration helper for miner setup"""
    
    @staticmethod
    def from_environment() -> Dict[str, Any]:
        """Load miner configuration from environment variables"""
        return {
            'platform': os.getenv('MINER_PLATFORM', 'zillow'),
            'implementation': os.getenv('MINER_IMPLEMENTATION', 'web_scraping'),
            'rate_limit': int(os.getenv('MINER_RATE_LIMIT', '30')),
            'max_batch_size': int(os.getenv('MINER_MAX_BATCH_SIZE', '50')),
            'timeout_seconds': int(os.getenv('MINER_TIMEOUT_SECONDS', '30')),
            'use_proxy': os.getenv('MINER_USE_PROXY', 'false').lower() == 'true',
            'proxy_url': os.getenv('MINER_PROXY_URL'),
            'user_agent_rotation': os.getenv('MINER_USER_AGENT_ROTATION', 'true').lower() == 'true',
        }
    
    @staticmethod
    def from_args(args) -> Dict[str, Any]:
        """Load miner configuration from command line arguments"""
        config = MinerConfig.from_environment()
        
        # Override with command line arguments if provided
        if hasattr(args, 'miner_platform') and args.miner_platform:
            config['platform'] = args.miner_platform
        
        if hasattr(args, 'miner_implementation') and args.miner_implementation:
            config['implementation'] = args.miner_implementation
        
        if hasattr(args, 'miner_rate_limit') and args.miner_rate_limit:
            config['rate_limit'] = args.miner_rate_limit
        
        return config
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """Validate miner configuration"""
        errors = []
        
        # Validate platform
        valid_platforms = [p.value for p in MinerPlatform]
        if config.get('platform') not in valid_platforms:
            errors.append(f"Invalid platform. Must be one of: {valid_platforms}")
        
        # Validate implementation
        valid_implementations = [i.value for i in MinerImplementation]
        if config.get('implementation') not in valid_implementations:
            errors.append(f"Invalid implementation. Must be one of: {valid_implementations}")
        
        # Validate numeric values
        if config.get('rate_limit', 0) <= 0:
            errors.append("Rate limit must be positive")
        
        if config.get('max_batch_size', 0) <= 0:
            errors.append("Max batch size must be positive")
        
        if config.get('timeout_seconds', 0) <= 0:
            errors.append("Timeout must be positive")
        
        return errors


# Global factory instance
miner_factory = MinerFactory()


def get_scraper(platform: Optional[str] = None, implementation: Optional[str] = None) -> Optional[Scraper]:
    """Convenience function to get a scraper instance"""
    
    platform_enum = None
    if platform:
        try:
            platform_enum = MinerPlatform(platform.lower())
        except ValueError:
            logging.error(f"Invalid platform: {platform}")
            return None
    
    implementation_enum = None
    if implementation:
        try:
            implementation_enum = MinerImplementation(implementation.lower())
        except ValueError:
            logging.error(f"Invalid implementation: {implementation}")
            return None
    
    return miner_factory.create_scraper(platform_enum, implementation_enum)


def get_scraper_for_source(source: DataSource, implementation: Optional[str] = None) -> Optional[Scraper]:
    """Convenience function to get scraper for a DataSource"""
    
    implementation_enum = None
    if implementation:
        try:
            implementation_enum = MinerImplementation(implementation.lower())
        except ValueError:
            logging.error(f"Invalid implementation: {implementation}")
            return None
    
    return miner_factory.get_scraper_for_source(source, implementation_enum)


def list_available_implementations() -> Dict[str, Dict[str, bool]]:
    """List all available scraper implementations"""
    return miner_factory.list_available_scrapers()
