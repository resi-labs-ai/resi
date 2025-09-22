"""
Unified protocol definitions for multi-source real estate scraping.
Supports Zillow, Redfin, Realtor.com, and Homes.com platforms.
"""

import bittensor as bt
from pydantic import Field, ConfigDict, field_validator
from typing import List, Optional
from common.data import DataEntity, DataSource


class MultiSourceRequest(bt.Synapse):
    """Unified protocol for multi-source real estate scraping requests"""
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )

    # Source selection
    source: DataSource = Field(
        description="Target real estate platform (ZILLOW, REDFIN, REALTOR_COM, HOMES_COM)"
    )
    
    # ID-based requests (Zillow, Redfin)
    zpids: List[str] = Field(
        default_factory=list,
        description="List of Zillow Property IDs to scrape",
        max_length=50
    )
    
    redfin_ids: List[str] = Field(
        default_factory=list,
        description="List of Redfin Property IDs to scrape",
        max_length=50
    )
    
    # Address-based requests (Realtor.com, Homes.com)
    addresses: List[str] = Field(
        default_factory=list,
        description="List of addresses to scrape from address-based platforms",
        max_length=50
    )
    
    # Request metadata
    priority: Optional[float] = Field(
        default=1.0,
        description="Priority weight for this request"
    )
    
    # Response fields
    scraped_properties: List[DataEntity] = Field(
        default_factory=list,
        description="Successfully scraped property data entities"
    )
    
    success_count: int = Field(
        default=0,
        description="Number of successfully scraped properties"
    )
    
    failed_items: List[str] = Field(
        default_factory=list,
        description="IDs or addresses that failed to scrape"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages for failed scrapes"
    )
    
    version: Optional[int] = Field(
        default=None,
        description="Protocol version"
    )
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        """Validate that source is a real estate platform"""
        real_estate_sources = {DataSource.ZILLOW, DataSource.REDFIN, DataSource.REALTOR_COM, DataSource.HOMES_COM}
        if v not in real_estate_sources:
            raise ValueError(f"Source must be one of: {real_estate_sources}")
        return v
    
    @field_validator('zpids', 'redfin_ids', 'addresses')
    @classmethod
    def validate_non_empty_items(cls, v):
        """Validate that items are non-empty strings"""
        if v:
            for item in v:
                if not item or not isinstance(item, str) or not item.strip():
                    raise ValueError("All items must be non-empty strings")
        return v


# Platform-specific validation functions
def is_valid_zpid(zpid: str) -> bool:
    """Validate ZPID format"""
    if not zpid:
        return False
    
    # Remove _zpid suffix if present
    clean_zpid = zpid.replace("_zpid", "")
    
    # Should be numeric and reasonable length (6-10 digits)
    return clean_zpid.isdigit() and 6 <= len(clean_zpid) <= 10


def is_valid_redfin_id(redfin_id: str) -> bool:
    """Validate Redfin ID format"""
    if not redfin_id:
        return False
    
    # Redfin IDs are typically 8-digit numbers
    return redfin_id.isdigit() and 6 <= len(redfin_id) <= 10


def is_valid_address(address: str) -> bool:
    """Validate address format for address-based platforms"""
    if not address or len(address.strip()) < 10:
        return False
    
    # Basic checks for address components
    address_lower = address.lower().strip()
    
    # Should contain some common address components
    street_indicators = ['st', 'street', 'ave', 'avenue', 'rd', 'road', 'dr', 'drive', 'ln', 'lane', 'ct', 'court', 'blvd', 'boulevard']
    has_street = any(indicator in address_lower for indicator in street_indicators)
    
    # Should have numbers (house number)
    has_numbers = any(char.isdigit() for char in address)
    
    return has_street and has_numbers


def normalize_zpid(zpid: str) -> str:
    """Normalize ZPID to consistent format"""
    clean_zpid = zpid.replace("_zpid", "").strip()
    return clean_zpid if clean_zpid.isdigit() else zpid


def normalize_redfin_id(redfin_id: str) -> str:
    """Normalize Redfin ID to consistent format"""
    return redfin_id.strip()


def normalize_address(address: str) -> str:
    """Normalize address to consistent format"""
    # Basic normalization
    normalized = address.strip()
    
    # Standardize common abbreviations
    replacements = {
        ' Street': ' St',
        ' Avenue': ' Ave',
        ' Road': ' Rd',
        ' Drive': ' Dr',
        ' Lane': ' Ln',
        ' Court': ' Ct',
        ' Boulevard': ' Blvd'
    }
    
    for full, abbrev in replacements.items():
        normalized = normalized.replace(full, abbrev)
    
    return normalized


def zpid_to_url(zpid: str, address: Optional[str] = None) -> str:
    """Convert ZPID to Zillow URL format"""
    clean_zpid = normalize_zpid(zpid)
    if address:
        # Create URL with address slug
        address_slug = address.replace(' ', '-').replace(',', '').lower()
        return f"https://www.zillow.com/homedetails/{address_slug}/{clean_zpid}_zpid/"
    else:
        # Generic URL pattern (may redirect)
        return f"https://www.zillow.com/homedetails/{clean_zpid}_zpid/"


def redfin_id_to_url(redfin_id: str, address: Optional[str] = None) -> str:
    """Convert Redfin ID to Redfin URL format"""
    clean_id = normalize_redfin_id(redfin_id)
    
    if address:
        # Try to construct full URL with address
        # This is complex as Redfin URLs include state/city/address structure
        return f"https://www.redfin.com/home/{clean_id}"
    else:
        # Direct home URL
        return f"https://www.redfin.com/home/{clean_id}"


def address_to_realtor_url(address: str) -> str:
    """Convert address to Realtor.com search URL"""
    normalized_address = normalize_address(address)
    # This would typically require a search first to get the actual listing URL
    search_query = normalized_address.replace(' ', '+')
    return f"https://www.realtor.com/realestateandhomes-search/{search_query}"


def address_to_homes_url(address: str) -> str:
    """Convert address to Homes.com search URL"""
    normalized_address = normalize_address(address)
    # This would typically require a search first to get the actual listing URL
    search_query = normalized_address.replace(' ', '-').lower()
    return f"https://www.homes.com/search/{search_query}"


class RequestBuilder:
    """Helper class to build multi-source requests"""
    
    @staticmethod
    def create_zillow_request(zpids: List[str], priority: float = 1.0) -> MultiSourceRequest:
        """Create a Zillow-specific request"""
        return MultiSourceRequest(
            source=DataSource.ZILLOW,
            zpids=zpids,
            priority=priority
        )
    
    @staticmethod
    def create_redfin_request(redfin_ids: List[str], priority: float = 1.0) -> MultiSourceRequest:
        """Create a Redfin-specific request"""
        return MultiSourceRequest(
            source=DataSource.REDFIN,
            redfin_ids=redfin_ids,
            priority=priority
        )
    
    @staticmethod
    def create_realtor_request(addresses: List[str], priority: float = 1.0) -> MultiSourceRequest:
        """Create a Realtor.com-specific request"""
        return MultiSourceRequest(
            source=DataSource.REALTOR_COM,
            addresses=addresses,
            priority=priority
        )
    
    @staticmethod
    def create_homes_request(addresses: List[str], priority: float = 1.0) -> MultiSourceRequest:
        """Create a Homes.com-specific request"""
        return MultiSourceRequest(
            source=DataSource.HOMES_COM,
            addresses=addresses,
            priority=priority
        )


class RequestValidator:
    """Helper class to validate requests"""
    
    @staticmethod
    def validate_request(request: MultiSourceRequest) -> List[str]:
        """Validate a multi-source request and return any errors"""
        errors = []
        
        # Check that appropriate fields are populated for the source
        if request.source == DataSource.ZILLOW:
            if not request.zpids:
                errors.append("ZPIDs required for Zillow requests")
            else:
                invalid_zpids = [zpid for zpid in request.zpids if not is_valid_zpid(zpid)]
                if invalid_zpids:
                    errors.append(f"Invalid ZPIDs: {invalid_zpids}")
        
        elif request.source == DataSource.REDFIN:
            if not request.redfin_ids:
                errors.append("Redfin IDs required for Redfin requests")
            else:
                invalid_ids = [rid for rid in request.redfin_ids if not is_valid_redfin_id(rid)]
                if invalid_ids:
                    errors.append(f"Invalid Redfin IDs: {invalid_ids}")
        
        elif request.source in [DataSource.REALTOR_COM, DataSource.HOMES_COM]:
            if not request.addresses:
                errors.append(f"Addresses required for {request.source.name} requests")
            else:
                invalid_addresses = [addr for addr in request.addresses if not is_valid_address(addr)]
                if invalid_addresses:
                    errors.append(f"Invalid addresses: {invalid_addresses}")
        
        # Check for conflicting fields
        populated_fields = sum([
            bool(request.zpids),
            bool(request.redfin_ids),
            bool(request.addresses)
        ])
        
        if populated_fields > 1:
            errors.append("Only one type of identifier should be provided per request")
        
        if populated_fields == 0:
            errors.append("At least one identifier must be provided")
        
        return errors
