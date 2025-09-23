"""
URL builder for Zillow sold listings pages with proper pagination and search parameters.
"""

import json
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote, urlencode
from dataclasses import dataclass

from .zipcode_utils import get_zipcode_mapper, ZipcodeInfo


@dataclass
class SoldListingsSearchParams:
    """Parameters for sold listings search"""
    zipcode: str
    page: int = 1
    sort_order: str = "globalrelevanceex"  # Default Zillow sort
    date_range_days: Optional[int] = None  # Days back to search
    max_price: Optional[int] = None
    min_price: Optional[int] = None
    property_types: Optional[list] = None  # ["SINGLE_FAMILY", "CONDO", etc.]


class ZillowSoldURLBuilder:
    """Builds URLs for Zillow sold listings pages with proper pagination"""
    
    def __init__(self):
        self.zipcode_mapper = get_zipcode_mapper()
        
    async def build_sold_listings_url(
        self, 
        zipcode: str, 
        page: int = 1,
        search_params: Optional[SoldListingsSearchParams] = None
    ) -> Optional[str]:
        """Build URL for sold listings page"""
        
        # Get zipcode information
        zipcode_info = await self.zipcode_mapper.resolve_zipcode(zipcode)
        if not zipcode_info:
            logging.error(f"Could not resolve zipcode {zipcode} to city-state format")
            return None
        
        # Build base URL
        base_url = f"https://www.zillow.com/{zipcode_info.zillow_url_format}/sold/"
        
        # Add page parameter to URL path if not page 1
        if page > 1:
            base_url += f"{page}_p/"
        
        # Build search query state
        search_query_state = self._build_search_query_state(
            zipcode_info, 
            page, 
            search_params or SoldListingsSearchParams(zipcode=zipcode, page=page)
        )
        
        # URL encode the search query state
        encoded_query_state = quote(json.dumps(search_query_state, separators=(',', ':')))
        
        # Construct final URL
        final_url = f"{base_url}?searchQueryState={encoded_query_state}"
        
        logging.debug(f"Built sold listings URL for {zipcode}, page {page}: {final_url}")
        return final_url
    
    def _build_search_query_state(
        self, 
        zipcode_info: ZipcodeInfo, 
        page: int,
        search_params: SoldListingsSearchParams
    ) -> Dict[str, Any]:
        """Build the searchQueryState JSON parameter"""
        
        # Base search query state structure
        query_state = {
            "pagination": {
                "currentPage": page
            },
            "isMapVisible": True,
            "mapBounds": {
                # Default bounds - will be adjusted by Zillow based on zipcode
                "west": -74.0,
                "east": -73.9,
                "south": 40.6,
                "north": 40.8
            },
            "regionSelection": [
                {
                    # This will be populated with actual region ID if we can extract it
                    "regionType": 7  # Zipcode region type
                }
            ],
            "filterState": {
                "sort": {"value": search_params.sort_order},
                "rs": {"value": True},  # Recently sold filter - CRITICAL
                
                # Disable other listing types
                "fsba": {"value": False},  # For Sale By Agent
                "fsbo": {"value": False},  # For Sale By Owner
                "nc": {"value": False},    # New Construction
                "cmsn": {"value": False},  # Coming Soon
                "auc": {"value": False},   # Auction
                "fore": {"value": False},  # Foreclosure
                
                # Property type filters (all disabled by default)
                "sf": {"value": False},    # Single Family
                "tow": {"value": False},   # Townhome
                "mf": {"value": False},    # Multi Family
                "land": {"value": False},  # Land
                "manu": {"value": False},  # Manufactured
            },
            "isListVisible": True,
            "mapZoom": 12  # Default zoom level
        }
        
        # Add price filters if specified
        if search_params.min_price:
            query_state["filterState"]["price"] = {"min": search_params.min_price}
        
        if search_params.max_price:
            if "price" not in query_state["filterState"]:
                query_state["filterState"]["price"] = {}
            query_state["filterState"]["price"]["max"] = search_params.max_price
        
        # Add property type filters if specified
        if search_params.property_types:
            for prop_type in search_params.property_types:
                filter_key = self._get_property_type_filter_key(prop_type)
                if filter_key:
                    query_state["filterState"][filter_key] = {"value": True}
        
        # Add date range filter if specified
        if search_params.date_range_days:
            # Calculate date range (this would need to be implemented based on Zillow's date format)
            pass  # TODO: Implement date range filtering
        
        return query_state
    
    def _get_property_type_filter_key(self, property_type: str) -> Optional[str]:
        """Map property type to Zillow filter key"""
        type_mapping = {
            "SINGLE_FAMILY": "sf",
            "TOWNHOUSE": "tow",
            "MULTI_FAMILY": "mf",
            "CONDO": "condo",
            "LAND": "land",
            "MANUFACTURED": "manu",
        }
        return type_mapping.get(property_type.upper())
    
    def build_simple_sold_url(self, zipcode_info: ZipcodeInfo, page: int = 1) -> str:
        """Build a simple sold listings URL without complex search parameters"""
        base_url = f"https://www.zillow.com/{zipcode_info.zillow_url_format}/sold/"
        
        if page > 1:
            base_url += f"{page}_p/"
        
        return base_url
    
    async def test_url_construction(self, zipcode: str) -> Dict[str, Any]:
        """Test URL construction for a zipcode and return diagnostic info"""
        
        results = {
            "zipcode": zipcode,
            "zipcode_resolved": False,
            "zipcode_info": None,
            "urls": {},
            "errors": []
        }
        
        try:
            # Try to resolve zipcode
            zipcode_info = await self.zipcode_mapper.resolve_zipcode(zipcode)
            
            if zipcode_info:
                results["zipcode_resolved"] = True
                results["zipcode_info"] = {
                    "city": zipcode_info.city,
                    "state": zipcode_info.state,
                    "state_abbrev": zipcode_info.state_abbrev,
                    "zillow_format": zipcode_info.zillow_url_format
                }
                
                # Build various URL formats
                results["urls"]["simple_page_1"] = self.build_simple_sold_url(zipcode_info, 1)
                results["urls"]["simple_page_2"] = self.build_simple_sold_url(zipcode_info, 2)
                results["urls"]["complex_page_1"] = await self.build_sold_listings_url(zipcode, 1)
                results["urls"]["complex_page_2"] = await self.build_sold_listings_url(zipcode, 2)
                
            else:
                results["errors"].append(f"Could not resolve zipcode {zipcode}")
                
        except Exception as e:
            results["errors"].append(f"Error testing URL construction: {str(e)}")
        
        return results
    
    def extract_page_from_url(self, url: str) -> int:
        """Extract page number from Zillow sold listings URL"""
        try:
            import re
            # Look for pattern like "/2_p/" or "/10_p/"
            match = re.search(r'/(\d+)_p/', url)
            if match:
                return int(match.group(1))
            return 1  # Default to page 1
        except:
            return 1
    
    def extract_zipcode_from_url(self, url: str) -> Optional[str]:
        """Extract zipcode from Zillow URL"""
        try:
            import re
            # Look for pattern like "-12345/" at the end of city-state part
            match = re.search(r'-(\d{5})/?', url)
            if match:
                return match.group(1)
        except:
            pass
        return None


# Convenience functions
async def build_sold_url(zipcode: str, page: int = 1) -> Optional[str]:
    """Convenience function to build sold listings URL"""
    builder = ZillowSoldURLBuilder()
    return await builder.build_sold_listings_url(zipcode, page)


async def test_zipcode_url_construction(zipcode: str) -> Dict[str, Any]:
    """Test URL construction for a zipcode"""
    builder = ZillowSoldURLBuilder()
    return await builder.test_url_construction(zipcode)


# URL validation and testing
def validate_sold_listings_url(url: str) -> Dict[str, Any]:
    """Validate a sold listings URL and extract information"""
    
    validation_result = {
        "is_valid": False,
        "is_sold_listings": False,
        "zipcode": None,
        "page": 1,
        "has_search_params": False,
        "errors": []
    }
    
    try:
        if not url.startswith("https://www.zillow.com/"):
            validation_result["errors"].append("Not a Zillow URL")
            return validation_result
        
        if "/sold/" not in url:
            validation_result["errors"].append("Not a sold listings URL")
            return validation_result
        
        validation_result["is_sold_listings"] = True
        
        # Extract zipcode
        builder = ZillowSoldURLBuilder()
        zipcode = builder.extract_zipcode_from_url(url)
        if zipcode:
            validation_result["zipcode"] = zipcode
        
        # Extract page
        page = builder.extract_page_from_url(url)
        validation_result["page"] = page
        
        # Check for search parameters
        if "searchQueryState=" in url:
            validation_result["has_search_params"] = True
        
        validation_result["is_valid"] = True
        
    except Exception as e:
        validation_result["errors"].append(f"Validation error: {str(e)}")
    
    return validation_result
