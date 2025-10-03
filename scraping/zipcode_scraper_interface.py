"""
Zipcode Scraper Interface for Competitive Mining

This module defines the interface that miners must implement for zipcode-based
competitive real estate data mining. Miners can replace the mock implementation
with their own custom scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import bittensor as bt


class ZipcodeScraperInterface(ABC):
    """
    Abstract base class for zipcode-based real estate scrapers
    
    Miners must implement this interface to participate in zipcode mining.
    The scraper should return data in the format expected by validators.
    """
    
    @abstractmethod
    def scrape_zipcode(self, zipcode: str, target_count: int, timeout: int = 300) -> List[Dict]:
        """
        Scrape real estate listings for a specific zipcode
        
        Args:
            zipcode: 5-digit US zipcode to scrape
            target_count: Expected number of listings to find
            timeout: Maximum time to spend scraping (seconds)
            
        Returns:
            List of listing dictionaries with required fields
            
        Required fields in each listing:
            - zpid or mls_id: Unique property identifier
            - address: Full property address
            - price: Listing price (integer)
            - bedrooms: Number of bedrooms (integer or None)
            - bathrooms: Number of bathrooms (float or None)
            - sqft: Living area in square feet (integer or None)
            - listing_date: Date property was listed (ISO format string)
            - property_type: Type of property (e.g., "SINGLE_FAMILY", "CONDO")
            - listing_status: Current status (e.g., "FOR_SALE", "FOR_RENT")
            - days_on_market: Days since listing (integer or None)
            - source_url: URL where data was scraped from
            - scraped_timestamp: When data was scraped (ISO format string)
            - zipcode: Zipcode (should match input parameter)
        """
        pass
    
    @abstractmethod
    def get_scraper_info(self) -> Dict[str, str]:
        """
        Get information about this scraper implementation
        
        Returns:
            Dict with scraper metadata:
            - name: Scraper name
            - version: Scraper version
            - source: Data source (e.g., "zillow", "realtor.com")
            - description: Brief description
        """
        pass
    
    def validate_listing_data(self, listing: Dict) -> bool:
        """
        Validate that a listing has all required fields
        
        Args:
            listing: Listing dictionary to validate
            
        Returns:
            True if listing is valid, False otherwise
        """
        required_fields = [
            'address', 'price', 'listing_date', 'property_type', 
            'listing_status', 'source_url', 'scraped_timestamp', 'zipcode'
        ]
        
        # Check required fields exist and are not empty
        for field in required_fields:
            if field not in listing or listing[field] is None or listing[field] == '':
                bt.logging.warning(f"Listing missing required field: {field}")
                return False
        
        # Check that at least one ID field exists
        if not (listing.get('zpid') or listing.get('mls_id')):
            bt.logging.warning("Listing missing both zpid and mls_id")
            return False
        
        # Validate price is reasonable
        try:
            price = float(listing['price'])
            if price < 1000 or price > 100000000:
                bt.logging.warning(f"Listing price unreasonable: {price}")
                return False
        except (ValueError, TypeError):
            bt.logging.warning(f"Invalid price format: {listing['price']}")
            return False
        
        # Validate zipcode format
        zipcode = str(listing['zipcode'])
        if not zipcode.isdigit() or len(zipcode) != 5:
            bt.logging.warning(f"Invalid zipcode format: {zipcode}")
            return False
        
        return True


class ZipcodeScraperConfig:
    """Configuration class for zipcode scrapers"""
    
    def __init__(self, 
                 max_requests_per_minute: int = 30,
                 request_delay_seconds: float = 2.0,
                 max_retries: int = 3,
                 user_agent: str = None,
                 proxy_url: str = None):
        """
        Initialize scraper configuration
        
        Args:
            max_requests_per_minute: Rate limit for requests
            request_delay_seconds: Delay between requests
            max_retries: Maximum retry attempts for failed requests
            user_agent: Custom user agent string
            proxy_url: Proxy URL for requests
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.request_delay_seconds = request_delay_seconds
        self.max_retries = max_retries
        self.user_agent = user_agent or "ResiLabs-Miner/1.0"
        self.proxy_url = proxy_url
