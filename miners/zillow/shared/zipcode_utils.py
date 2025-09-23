"""
Zipcode utility functions for Zillow URL construction and mapping.
"""

import re
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import asyncio
import aiohttp
from urllib.parse import quote


@dataclass
class ZipcodeInfo:
    """Information about a zipcode"""
    zipcode: str
    city: str
    state: str
    state_abbrev: str
    zillow_url_format: str  # e.g., "brooklyn-new-york-ny-11225"
    
    def __post_init__(self):
        """Generate Zillow URL format if not provided"""
        if not self.zillow_url_format:
            self.zillow_url_format = self.generate_zillow_url_format()
    
    def generate_zillow_url_format(self) -> str:
        """Generate Zillow URL format from city/state/zipcode"""
        # Clean and format city name
        city_clean = re.sub(r'[^a-zA-Z\s]', '', self.city.lower())
        city_formatted = '-'.join(city_clean.split())
        
        # Clean and format state name
        state_clean = re.sub(r'[^a-zA-Z\s]', '', self.state.lower())
        state_formatted = '-'.join(state_clean.split())
        
        return f"{city_formatted}-{state_formatted}-{self.state_abbrev.lower()}-{self.zipcode}"


class ZipcodeMapper:
    """Maps zipcodes to city-state information for Zillow URL construction"""
    
    def __init__(self):
        self.cache: Dict[str, ZipcodeInfo] = {}
        self.failed_lookups: set = set()  # Track failed lookups to avoid retrying
        
        # Initialize with some common zipcodes for testing
        self._initialize_common_zipcodes()
    
    def _initialize_common_zipcodes(self):
        """Initialize with commonly used zipcodes for testing"""
        common_zipcodes = [
            ZipcodeInfo("11225", "Brooklyn", "New York", "NY", "brooklyn-new-york-ny-11225"),
            ZipcodeInfo("10001", "New York", "New York", "NY", "new-york-new-york-ny-10001"),
            ZipcodeInfo("90210", "Beverly Hills", "California", "CA", "beverly-hills-california-ca-90210"),
            ZipcodeInfo("94105", "San Francisco", "California", "CA", "san-francisco-california-ca-94105"),
            ZipcodeInfo("60601", "Chicago", "Illinois", "IL", "chicago-illinois-il-60601"),
            ZipcodeInfo("33101", "Miami", "Florida", "FL", "miami-florida-fl-33101"),
            ZipcodeInfo("75201", "Dallas", "Texas", "TX", "dallas-texas-tx-75201"),
            ZipcodeInfo("98101", "Seattle", "Washington", "WA", "seattle-washington-wa-98101"),
            ZipcodeInfo("02101", "Boston", "Massachusetts", "MA", "boston-massachusetts-ma-02101"),
            ZipcodeInfo("30301", "Atlanta", "Georgia", "GA", "atlanta-georgia-ga-30301"),
        ]
        
        for zipcode_info in common_zipcodes:
            self.cache[zipcode_info.zipcode] = zipcode_info
        
        logging.info(f"Initialized zipcode mapper with {len(self.cache)} common zipcodes")
    
    def get_zipcode_info(self, zipcode: str) -> Optional[ZipcodeInfo]:
        """Get zipcode information from cache"""
        return self.cache.get(zipcode)
    
    async def resolve_zipcode(self, zipcode: str) -> Optional[ZipcodeInfo]:
        """Resolve zipcode to city-state information"""
        
        # Check cache first
        if zipcode in self.cache:
            return self.cache[zipcode]
        
        # Skip if we've already failed to resolve this zipcode
        if zipcode in self.failed_lookups:
            logging.debug(f"Skipping zipcode {zipcode} - previous lookup failed")
            return None
        
        # Try to resolve via web scraping (visit a Zillow page to extract city-state)
        zipcode_info = await self._resolve_via_zillow_redirect(zipcode)
        
        if zipcode_info:
            self.cache[zipcode] = zipcode_info
            logging.info(f"Successfully resolved zipcode {zipcode} -> {zipcode_info.zillow_url_format}")
        else:
            self.failed_lookups.add(zipcode)
            logging.warning(f"Failed to resolve zipcode {zipcode}")
        
        return zipcode_info
    
    async def _resolve_via_zillow_redirect(self, zipcode: str) -> Optional[ZipcodeInfo]:
        """Resolve zipcode by visiting Zillow and extracting the city-state from redirect"""
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try a simple search URL that might redirect to the proper format
                search_url = f"https://www.zillow.com/homes/{zipcode}_rb/"
                
                async with session.get(
                    search_url,
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        final_url = str(response.url)
                        return self._extract_zipcode_info_from_url(zipcode, final_url)
                    
        except Exception as e:
            logging.error(f"Error resolving zipcode {zipcode} via Zillow: {e}")
        
        return None
    
    def _extract_zipcode_info_from_url(self, zipcode: str, url: str) -> Optional[ZipcodeInfo]:
        """Extract city-state information from Zillow URL"""
        
        try:
            # Look for patterns like "/city-state-abbrev-zipcode/"
            pattern = r'/([a-z-]+)-([a-z-]+)-([a-z]{2})-(\d{5})/?'
            match = re.search(pattern, url.lower())
            
            if match:
                city_part, state_part, state_abbrev, url_zipcode = match.groups()
                
                # Verify zipcode matches
                if url_zipcode == zipcode:
                    # Convert back to readable format
                    city = city_part.replace('-', ' ').title()
                    state = state_part.replace('-', ' ').title()
                    
                    zillow_format = f"{city_part}-{state_part}-{state_abbrev}-{zipcode}"
                    
                    return ZipcodeInfo(
                        zipcode=zipcode,
                        city=city,
                        state=state,
                        state_abbrev=state_abbrev.upper(),
                        zillow_url_format=zillow_format
                    )
            
        except Exception as e:
            logging.error(f"Error extracting zipcode info from URL {url}: {e}")
        
        return None
    
    def add_custom_zipcode(self, zipcode_info: ZipcodeInfo):
        """Add a custom zipcode mapping"""
        self.cache[zipcode_info.zipcode] = zipcode_info
        logging.info(f"Added custom zipcode mapping: {zipcode_info.zipcode} -> {zipcode_info.zillow_url_format}")
    
    def get_all_cached_zipcodes(self) -> list[str]:
        """Get all cached zipcode strings"""
        return list(self.cache.keys())
    
    def validate_zipcode(self, zipcode: str) -> bool:
        """Validate zipcode format"""
        return bool(re.match(r'^\d{5}$', zipcode))


# Global instance
_zipcode_mapper = ZipcodeMapper()


def get_zipcode_mapper() -> ZipcodeMapper:
    """Get the global zipcode mapper instance"""
    return _zipcode_mapper


async def resolve_zipcode_to_url_format(zipcode: str) -> Optional[str]:
    """Convenience function to resolve zipcode to Zillow URL format"""
    mapper = get_zipcode_mapper()
    zipcode_info = await mapper.resolve_zipcode(zipcode)
    return zipcode_info.zillow_url_format if zipcode_info else None


def get_cached_zipcode_url_format(zipcode: str) -> Optional[str]:
    """Get cached zipcode URL format without async resolution"""
    mapper = get_zipcode_mapper()
    zipcode_info = mapper.get_zipcode_info(zipcode)
    return zipcode_info.zillow_url_format if zipcode_info else None


# Utility functions for testing
def get_test_zipcodes() -> list[str]:
    """Get list of test zipcodes that are pre-cached"""
    return [
        "11225",  # Brooklyn, NY
        "10001",  # Manhattan, NY
        "90210",  # Beverly Hills, CA
        "94105",  # San Francisco, CA
        "60601",  # Chicago, IL
    ]


def format_city_state_for_url(city: str, state: str, state_abbrev: str, zipcode: str) -> str:
    """Format city-state-zipcode for Zillow URL"""
    city_clean = re.sub(r'[^a-zA-Z\s]', '', city.lower())
    city_formatted = '-'.join(city_clean.split())
    
    state_clean = re.sub(r'[^a-zA-Z\s]', '', state.lower())
    state_formatted = '-'.join(state_clean.split())
    
    return f"{city_formatted}-{state_formatted}-{state_abbrev.lower()}-{zipcode}"
