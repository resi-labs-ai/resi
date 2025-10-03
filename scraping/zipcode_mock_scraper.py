"""
Mock Zipcode Scraper Implementation

This is a mock implementation of the ZipcodeScraperInterface that generates
realistic synthetic real estate data for testing and development purposes.

Miners should replace this with their own real scraper implementations.
"""

import random
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import bittensor as bt

from scraping.zipcode_scraper_interface import ZipcodeScraperInterface, ZipcodeScraperConfig


class MockZipcodeScraper(ZipcodeScraperInterface):
    """
    Mock implementation that generates synthetic real estate data
    
    This scraper creates realistic-looking property listings for testing.
    It respects the target count and timeout parameters while generating
    data that passes validation checks.
    """
    
    def __init__(self, config: ZipcodeScraperConfig = None):
        """
        Initialize mock scraper
        
        Args:
            config: Scraper configuration (optional)
        """
        self.config = config or ZipcodeScraperConfig()
        
        # Sample data for generating realistic listings
        self.street_names = [
            "Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Cedar Ln", "Elm St",
            "Park Ave", "First St", "Second St", "Third St", "Washington St",
            "Lincoln Ave", "Jefferson Rd", "Madison Dr", "Adams St", "Wilson Ave"
        ]
        
        self.property_types = [
            "SINGLE_FAMILY", "CONDO", "TOWNHOUSE", "MULTI_FAMILY", "MANUFACTURED"
        ]
        
        self.listing_statuses = [
            "FOR_SALE", "PENDING", "CONTINGENT", "SOLD"
        ]
    
    def scrape_zipcode(self, zipcode: str, target_count: int, timeout: int = 300) -> List[Dict]:
        """
        Generate mock real estate listings for a zipcode
        
        Args:
            zipcode: 5-digit US zipcode
            target_count: Number of listings to generate
            timeout: Maximum time to spend (simulated)
            
        Returns:
            List of synthetic listing dictionaries
        """
        bt.logging.info(f"Mock scraper generating {target_count} listings for zipcode {zipcode}")
        
        start_time = time.time()
        listings = []
        
        # Generate listings with some randomness around target count
        actual_count = max(1, target_count + random.randint(-5, 10))
        
        for i in range(actual_count):
            # Check timeout
            if time.time() - start_time > timeout:
                bt.logging.warning(f"Mock scraper timeout after {len(listings)} listings")
                break
            
            # Simulate scraping delay
            time.sleep(self.config.request_delay_seconds * random.uniform(0.5, 1.5))
            
            listing = self._generate_mock_listing(zipcode, i)
            
            if self.validate_listing_data(listing):
                listings.append(listing)
            else:
                bt.logging.warning(f"Generated invalid listing: {listing}")
        
        bt.logging.success(f"Mock scraper generated {len(listings)} valid listings for {zipcode}")
        return listings
    
    def _generate_mock_listing(self, zipcode: str, index: int) -> Dict:
        """Generate a single mock listing"""
        
        # Generate realistic property details (ensure high completeness for testing)
        bedrooms = random.choice([1, 2, 3, 4, 5]) if random.random() > 0.05 else None  # 95% complete
        bathrooms = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]) if random.random() > 0.05 else None  # 95% complete
        sqft = random.randint(800, 4000) if random.random() > 0.05 else None  # 95% complete
        
        # Generate price based on property characteristics
        base_price = 200000
        if bedrooms:
            base_price += bedrooms * 50000
        if sqft:
            base_price += sqft * random.randint(100, 300)
        
        # Add some randomness
        price = int(base_price * random.uniform(0.7, 1.8))
        
        # Generate dates (use timezone-aware datetimes for consistency validation)
        now = datetime.now(timezone.utc)
        listing_date = now - timedelta(days=random.randint(1, 180))
        days_on_market = (now - listing_date).days
        
        # Generate address
        house_number = random.randint(100, 9999)
        street_name = random.choice(self.street_names)
        address = f"{house_number} {street_name}"
        
        # Generate unique IDs
        zpid = f"mock_{zipcode}_{index}_{random.randint(100000, 999999)}"
        mls_id = f"MLS{random.randint(1000000, 9999999)}"
        
        return {
            'zpid': zpid,
            'mls_id': mls_id,
            'address': address,
            'price': price,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'sqft': sqft,
            'listing_date': listing_date.isoformat(),
            'property_type': random.choice(self.property_types),
            'listing_status': random.choice(self.listing_statuses),
            'days_on_market': days_on_market,
            'source_url': f"https://mock-realestate-site.com/property/{zpid}",
            'scraped_timestamp': now.isoformat(),
            'zipcode': zipcode,
            
            # Optional fields that validators might check
            'lot_size': random.randint(5000, 20000) if random.random() > 0.3 else None,
            'year_built': random.randint(1950, 2023) if random.random() > 0.2 else None,
            'garage_spaces': random.choice([0, 1, 2, 3]) if random.random() > 0.3 else None,
            'has_pool': random.choice([True, False]) if random.random() > 0.7 else None,
            'hoa_fee': random.randint(50, 500) if random.random() > 0.6 else None,
            
            # Mock scraper metadata
            'mock_generated': True,
            'mock_index': index
        }
    
    def get_scraper_info(self) -> Dict[str, str]:
        """Get mock scraper information"""
        return {
            'name': 'MockZipcodeScraper',
            'version': '1.0.0',
            'source': 'synthetic_data',
            'description': 'Mock scraper that generates synthetic real estate data for testing'
        }


def create_mock_scraper(config: ZipcodeScraperConfig = None) -> MockZipcodeScraper:
    """
    Factory function to create a mock scraper instance
    
    Args:
        config: Optional scraper configuration
        
    Returns:
        MockZipcodeScraper instance
    """
    return MockZipcodeScraper(config)


# Example usage for miners:
"""
To replace this mock scraper with your own implementation:

1. Create a new class that inherits from ZipcodeScraperInterface
2. Implement the required methods: scrape_zipcode() and get_scraper_info()
3. Replace the mock scraper in your miner configuration

Example:

class MyCustomScraper(ZipcodeScraperInterface):
    def scrape_zipcode(self, zipcode: str, target_count: int, timeout: int = 300) -> List[Dict]:
        # Your scraping logic here
        # Connect to real estate websites
        # Parse HTML/JSON responses
        # Return properly formatted listings
        pass
    
    def get_scraper_info(self) -> Dict[str, str]:
        return {
            'name': 'MyCustomScraper',
            'version': '1.0.0',
            'source': 'zillow.com',
            'description': 'Custom scraper for Zillow data'
        }

# In your miner configuration:
def get_zipcode_scraper():
    return MyCustomScraper()
"""
