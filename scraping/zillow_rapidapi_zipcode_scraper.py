"""
RapidAPI Zillow Zipcode Scraper for Competitive Mining

This scraper implements the ZipcodeScraperInterface using the RapidAPI Zillow service.
It's designed as a starting point for miners - functional but expensive.
Miners should replace this with custom scrapers for better cost efficiency.
"""

import asyncio
import httpx
import time
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import bittensor as bt

from scraping.zipcode_scraper_interface import ZipcodeScraperInterface, ZipcodeScraperConfig


class RapidAPIZillowZipcodeScraper(ZipcodeScraperInterface):
    """
    RapidAPI Zillow scraper for zipcode-based competitive mining.
    
    WARNING: This scraper uses paid RapidAPI calls and can be expensive.
    It's provided as a functional starting point. For cost efficiency,
    miners should implement custom scrapers using free methods.
    
    Cost Estimate: ~$0.01-0.02 per API call
    For 10,000 listings target: ~50-100 API calls = $0.50-2.00 per epoch
    """
    
    def __init__(self, api_key: str, config: ZipcodeScraperConfig = None, status_type: str = "RecentlySold"):
        """
        Initialize RapidAPI Zillow scraper
        
        Args:
            api_key: RapidAPI key for Zillow API access
            config: Scraper configuration
            status_type: Type of listings to fetch ("RecentlySold", "ForSale", "ForRent", etc.)
        """
        if not api_key:
            raise ValueError("RapidAPI key is required")
        
        self.api_key = api_key
        self.config = config or ZipcodeScraperConfig()
        self.status_type = status_type
        
        # RapidAPI configuration
        self.base_url = "https://zillow-com1.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.config.max_requests_per_minute
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'listings_scraped': 0,
            'errors': 0,
            'cost_estimate': 0.0
        }
    
    async def scrape_zipcode(self, zipcode: str, target_count: int, timeout: int = 300) -> List[Dict]:
        """
        Scrape real estate listings for a specific zipcode using RapidAPI
        
        Args:
            zipcode: 5-digit US zipcode
            target_count: Expected number of listings to find
            timeout: Maximum time to spend scraping (seconds)
            
        Returns:
            List of listing dictionaries with required fields
        """
        bt.logging.info(f"RapidAPI Zillow scraper starting for zipcode {zipcode} (target: {target_count}, status: {self.status_type})")
        
        start_time = time.time()
        all_listings = []
        page = 1
        max_pages = 30  # Limit to prevent excessive API costs
        
        try:
            while len(all_listings) < target_count and page <= max_pages:
                # Check timeout
                if time.time() - start_time > timeout:
                    bt.logging.warning(f"Timeout reached after {len(all_listings)} listings")
                    break
                
                # Rate limiting
                await self._rate_limit()
                
                # Make API request
                page_data = await self._fetch_page(zipcode, page)
                
                if not page_data or 'props' not in page_data:
                    bt.logging.warning(f"No data returned for zipcode {zipcode}, page {page}")
                    break
                
                props = page_data.get('props', [])
                if not props:
                    bt.logging.info(f"No more properties found on page {page}")
                    break
                
                # Convert API data to required format
                page_listings = []
                for prop in props:
                    try:
                        listing = self._convert_api_data_to_listing(prop, zipcode)
                        if listing and self.validate_listing_data(listing):
                            page_listings.append(listing)
                    except Exception as e:
                        bt.logging.warning(f"Error converting property data: {e}")
                        continue
                
                all_listings.extend(page_listings)
                
                bt.logging.info(f"Page {page}: Found {len(page_listings)} valid listings "
                               f"(total: {len(all_listings)}/{target_count})")
                
                # Update statistics
                self.stats['api_calls'] += 1
                self.stats['listings_scraped'] += len(page_listings)
                self.stats['cost_estimate'] += 0.015  # Estimate $0.015 per call
                
                page += 1
                
                # Small delay between pages
                await asyncio.sleep(self.config.request_delay_seconds)
        
        except Exception as e:
            bt.logging.error(f"Error scraping zipcode {zipcode}: {e}")
            self.stats['errors'] += 1
        
        # Log final statistics
        elapsed_time = time.time() - start_time
        bt.logging.success(
            f"RapidAPI scraping complete for {zipcode}: "
            f"{len(all_listings)} listings in {elapsed_time:.1f}s "
            f"(${self.stats['cost_estimate']:.3f} estimated cost)"
        )
        
        return all_listings
    
    async def _rate_limit(self):
        """Apply rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _fetch_page(self, zipcode: str, page: int) -> Optional[Dict]:
        """
        Fetch a page of property data from RapidAPI
        
        Args:
            zipcode: Target zipcode
            page: Page number (1-based)
            
        Returns:
            API response data or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "location": zipcode,
                    "sort": "Newest",
                    "page": page,
                    "status_type": self.status_type
                }
                
                response = await client.get(
                    f"{self.base_url}/propertyExtendedSearch",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    bt.logging.warning("Rate limit exceeded, waiting...")
                    await asyncio.sleep(60)  # Wait 1 minute for rate limit reset
                    return None
                else:
                    bt.logging.error(f"API error {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            bt.logging.error(f"Request failed for zipcode {zipcode}, page {page}: {e}")
            return None
    
    def _convert_api_data_to_listing(self, prop: Dict, zipcode: str) -> Optional[Dict]:
        """
        Convert RapidAPI property data to required listing format
        
        Args:
            prop: Property data from API
            zipcode: Target zipcode
            
        Returns:
            Formatted listing dictionary or None if invalid
        """
        try:
            # Extract required fields with proper mapping
            zpid = str(prop.get('zpid', ''))
            if not zpid:
                return None
            
            # Address handling
            address_obj = prop.get('address', {})
            if isinstance(address_obj, dict):
                street = address_obj.get('streetAddress', '')
                city = address_obj.get('city', '')
                state = address_obj.get('state', '')
                zip_code = address_obj.get('zipcode', zipcode)
                address = f"{street}, {city}, {state} {zip_code}".strip(', ')
                
                # Validate we got a real address, not just city/state
                if not street or street.strip() == '':
                    return None  # Skip properties without proper street address
            else:
                # If address is not a proper dict, skip this property
                return None
            
            # Property details with safe extraction
            bedrooms = prop.get('bedrooms')
            bathrooms = prop.get('bathrooms')
            living_area = prop.get('livingArea') or prop.get('livingAreaValue')
            
            # Price information
            price = prop.get('price')
            if not price:
                return None  # Skip properties without price
            
            # Listing status mapping
            home_status = prop.get('homeStatus', 'UNKNOWN')
            listing_status_map = {
                'FOR_SALE': 'FOR_SALE',
                'FOR_RENT': 'FOR_RENT', 
                'SOLD': 'SOLD',
                'PENDING': 'PENDING',
                'OFF_MARKET': 'OFF_MARKET',
                'OTHER': 'FOR_SALE'  # Default fallback
            }
            listing_status = listing_status_map.get(home_status, 'FOR_SALE')
            
            # Property type mapping
            home_type = prop.get('homeType', 'UNKNOWN')
            property_type_map = {
                'SINGLE_FAMILY': 'SINGLE_FAMILY',
                'CONDO': 'CONDO',
                'TOWNHOUSE': 'TOWNHOUSE',
                'MULTI_FAMILY': 'MULTI_FAMILY',
                'MANUFACTURED': 'MANUFACTURED',
                'LOT': 'LOT',
                'APARTMENT': 'CONDO'  # Map apartment to condo
            }
            property_type = property_type_map.get(home_type, 'SINGLE_FAMILY')
            
            # Dates and market info
            now = datetime.now(timezone.utc)
            days_on_market = prop.get('daysOnZillow') or prop.get('timeOnZillow', 0)
            
            # Try to extract listing date
            if days_on_market and isinstance(days_on_market, (int, float)):
                listing_date = now - timedelta(days=int(days_on_market))
            else:
                listing_date = now  # Fallback to current date
            
            # Generate source URL
            detail_url = prop.get('detailUrl') or prop.get('hdpUrl', '')
            if detail_url:
                if detail_url.startswith('http'):
                    # Already has full URL
                    source_url = detail_url
                else:
                    # Relative path, prepend domain
                    source_url = f"https://www.zillow.com{detail_url}"
            else:
                # No detail_url provided, construct default
                source_url = f"https://www.zillow.com/homedetails/{zpid}_zpid/"
            
            # Create listing dictionary with all required fields
            listing = {
                # Required identifiers
                'zpid': zpid,
                'mls_id': prop.get('mlsid') or f"RAPID_{zpid}",
                
                # Required property info
                'address': address,
                'price': int(price),
                'property_type': property_type,
                'listing_status': listing_status,
                
                # Required metadata
                'listing_date': listing_date.isoformat(),
                'source_url': source_url,
                'scraped_timestamp': now.isoformat(),
                'zipcode': zipcode,
                
                # Optional but commonly available fields
                'bedrooms': int(bedrooms) if bedrooms is not None else None,
                'bathrooms': float(bathrooms) if bathrooms is not None else None,
                'sqft': int(living_area) if living_area else None,
                'days_on_market': int(days_on_market) if days_on_market else None,
                
                # Additional valuable fields
                'lot_size': prop.get('lotAreaValue'),
                'year_built': prop.get('yearBuilt'),
                'zestimate': prop.get('zestimate'),
                'latitude': prop.get('latitude'),
                'longitude': prop.get('longitude'),
                
                # Data source metadata
                'data_source': 'rapidapi_zillow',
                'api_cost_estimate': 0.015
            }
            
            return listing
            
        except Exception as e:
            bt.logging.warning(f"Error converting property data: {e}")
            return None
    
    def get_scraper_info(self) -> Dict[str, str]:
        """Get scraper information"""
        return {
            'name': 'RapidAPIZillowZipcodeScraper',
            'version': '1.1.0',
            'source': 'rapidapi_zillow',
            'description': f'RapidAPI Zillow scraper for zipcode mining (status: {self.status_type})',
            'cost_warning': 'Uses paid API calls - replace with custom scraper for cost efficiency',
            'estimated_cost_per_call': '$0.015',
            'estimated_cost_per_epoch': '$0.50-2.00 (for 10K listings target)',
            'status_type': self.status_type
        }
    
    def get_stats(self) -> Dict:
        """Get scraping statistics"""
        return self.stats.copy()


def create_rapidapi_zillow_scraper(api_key: str, config: ZipcodeScraperConfig = None, status_type: str = "RecentlySold") -> RapidAPIZillowZipcodeScraper:
    """
    Factory function to create RapidAPI Zillow scraper
    
    Args:
        api_key: RapidAPI key for Zillow access
        config: Optional scraper configuration
        status_type: Type of listings to fetch ("RecentlySold", "ForSale", "ForRent", etc.)
        
    Returns:
        Configured RapidAPIZillowZipcodeScraper instance
    """
    return RapidAPIZillowZipcodeScraper(api_key, config, status_type)


# Example usage and cost warning
"""
COST WARNING: This scraper uses RapidAPI which charges per request.

Estimated costs for competitive mining:
- Per API call: ~$0.015
- Per zipcode (2-5 pages): ~$0.03-0.075  
- Per epoch (10-20 zipcodes): ~$0.30-1.50
- Per day (6 epochs): ~$1.80-9.00
- Per month: ~$54-270

For cost-effective mining, replace this scraper with:
1. Direct web scraping (free but requires proxy management)
2. Alternative data sources (MLS feeds, public records)
3. Hybrid approaches (API + scraping)

Usage example:
```python
# In your miner configuration
def get_zipcode_scraper():
    api_key = os.getenv('RAPIDAPI_ZILLOW_KEY')
    if not api_key:
        bt.logging.warning("No RapidAPI key found, using mock scraper")
        return create_mock_scraper()
    
    config = ZipcodeScraperConfig(
        max_requests_per_minute=20,  # Stay within rate limits
        request_delay_seconds=3.0,   # Conservative delay
        max_retries=2
    )
    
    # Get recently sold listings (default)
    return create_rapidapi_zillow_scraper(api_key, config, "RecentlySold")
    
    # Or get for-sale listings
    # return create_rapidapi_zillow_scraper(api_key, config, "ForSale")
```
"""
