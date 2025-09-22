"""
Base schema for all real estate platforms.
Provides a unified interface while allowing platform-specific extensions.
"""

import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod

from common.data import DataEntity, DataLabel, DataSource


class BaseRealEstateContent(BaseModel, ABC):
    """Base schema for all real estate platforms"""
    
    class Config:
        extra = "allow"  # Allow platform-specific fields
    
    # Universal identifiers
    source_id: str = Field(description="Platform-specific ID (ZPID, Redfin ID, etc.)")
    source_platform: str = Field(description="Platform name (zillow, redfin, etc.)")
    address: str = Field(description="Property address")
    detail_url: str = Field(description="URL to property details page")
    
    # Core property information
    price: Optional[int] = Field(None, description="Current listing price")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    living_area: Optional[int] = Field(None, description="Living area in square feet")
    lot_area_value: Optional[float] = Field(None, description="Lot area value")
    lot_area_unit: Optional[str] = Field(None, description="Lot area unit (sqft, acres)")
    
    # Property details
    property_type: str = Field(description="Property type (SINGLE_FAMILY, CONDO, etc.)")
    year_built: Optional[int] = Field(None, description="Year property was built")
    listing_status: str = Field(description="Listing status (FOR_SALE, FOR_RENT, etc.)")
    
    # Location data
    latitude: Optional[float] = Field(None, description="Property latitude")
    longitude: Optional[float] = Field(None, description="Property longitude")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    zipcode: Optional[str] = Field(None, description="ZIP code")
    country: str = Field(default="USA", description="Country")
    currency: str = Field(default="USD", description="Currency")
    
    # Media
    img_src: Optional[str] = Field(None, description="Primary image URL")
    photos: Optional[List[str]] = Field(None, description="List of photo URLs")
    has_virtual_tour: bool = Field(default=False, description="Has virtual tour")
    
    # Listing information
    days_on_market: Optional[int] = Field(None, description="Days on market")
    listing_date: Optional[str] = Field(None, description="Date listed")
    
    # Price history (if available)
    price_history: Optional[List[Dict[str, Any]]] = Field(None, description="Price history")
    
    # Agent/broker information
    agent_name: Optional[str] = Field(None, description="Listing agent name")
    broker_name: Optional[str] = Field(None, description="Broker name")
    
    # Schools (if available)
    schools: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby schools")
    
    # Platform-specific data container
    platform_data: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific fields")
    
    # Metadata
    scraped_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    scraping_method: str = Field(description="Method used for scraping (api, web_scraping)")
    
    @abstractmethod
    def get_platform_source(self) -> DataSource:
        """Return the DataSource enum for this platform"""
        pass
    
    @abstractmethod
    def to_data_entity(self) -> DataEntity:
        """Convert to DataEntity for Bittensor storage"""
        pass
    
    def extract_zipcode_from_address(self) -> Optional[str]:
        """Extract zipcode from address string"""
        if not self.zipcode and self.address:
            import re
            # Look for 5-digit zipcode pattern
            match = re.search(r'\b(\d{5})\b', self.address)
            if match:
                return match.group(1)
        return self.zipcode
    
    def create_data_label(self) -> DataLabel:
        """Create appropriate DataLabel for this property"""
        zipcode = self.extract_zipcode_from_address()
        if zipcode:
            return DataLabel(value=f"zip:{zipcode}")
        else:
            return DataLabel(value="zip:unknown")
    
    def get_price_per_sqft(self) -> Optional[float]:
        """Calculate price per square foot if data is available"""
        if self.price and self.living_area and self.living_area > 0:
            return round(self.price / self.living_area, 2)
        return None
    
    def get_lot_size_sqft(self) -> Optional[float]:
        """Convert lot size to square feet"""
        if not self.lot_area_value:
            return None
        
        if self.lot_area_unit == "acres":
            return self.lot_area_value * 43560  # 1 acre = 43,560 sq ft
        elif self.lot_area_unit == "sqft":
            return self.lot_area_value
        else:
            return None


class PropertyValidationMixin:
    """Mixin for common property validation methods"""
    
    def validate_basic_fields(self) -> List[str]:
        """Validate that basic required fields are present"""
        errors = []
        
        if not self.source_id:
            errors.append("source_id is required")
        if not self.address:
            errors.append("address is required")
        if not self.property_type:
            errors.append("property_type is required")
        if not self.listing_status:
            errors.append("listing_status is required")
            
        return errors
    
    def validate_price_data(self) -> List[str]:
        """Validate price-related fields"""
        errors = []
        
        if self.price is not None and self.price <= 0:
            errors.append("price must be positive")
        if self.bedrooms is not None and self.bedrooms < 0:
            errors.append("bedrooms must be non-negative")
        if self.bathrooms is not None and self.bathrooms < 0:
            errors.append("bathrooms must be non-negative")
        if self.living_area is not None and self.living_area <= 0:
            errors.append("living_area must be positive")
            
        return errors
    
    def validate_location_data(self) -> List[str]:
        """Validate location-related fields"""
        errors = []
        
        if self.latitude is not None and not (-90 <= self.latitude <= 90):
            errors.append("latitude must be between -90 and 90")
        if self.longitude is not None and not (-180 <= self.longitude <= 180):
            errors.append("longitude must be between -180 and 180")
            
        return errors
