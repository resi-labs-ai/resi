import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json

from common.data import DataEntity, DataLabel, DataSource
from scraping import utils


class RealEstateContent(BaseModel):
    """Content model for real estate listings from Zillow RapidAPI with full Individual Property API support"""
    
    class Config:
        extra = "ignore"  # Allow extra fields from Individual Property API

    # Core identifiers
    zpid: str = Field(description="Zillow Property ID")
    address: str
    detail_url: str
    
    # Enhanced address fields from Individual Property API
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    county_fips: Optional[str] = None
    
    # Property details
    property_type: str  # SINGLE_FAMILY, CONDO, etc.
    property_sub_type: Optional[str] = None
    home_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    living_area: Optional[int] = Field(None, description="Living area in sq ft")
    living_area_value: Optional[int] = None  # Alternative field name from Individual API
    
    # Enhanced property details from Individual Property API
    year_built: Optional[int] = None
    lot_size: Optional[float] = None
    lot_area_value: Optional[float] = None
    lot_area_unit: Optional[str] = None  # "acres" or "sqft"
    parking_spaces: Optional[int] = None
    garage_spaces: Optional[int] = None
    
    # Pricing and estimates
    price: Optional[int] = None
    zestimate: Optional[int] = None
    rent_zestimate: Optional[int] = None
    price_change: Optional[int] = None
    date_price_changed: Optional[int] = None  # timestamp
    
    # Enhanced financial data from Individual Property API
    hoa_fee: Optional[float] = None
    monthly_hoa_fee: Optional[float] = None
    property_taxes: Optional[float] = None
    tax_assessed_value: Optional[int] = None
    
    # Historical data arrays from Individual Property API
    tax_history: Optional[List[Dict[str, Any]]] = None
    price_history: Optional[List[Dict[str, Any]]] = None
    
    # Location data
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: str = "USA"
    currency: str = "USD"
    time_zone: Optional[str] = None
    
    # Listing status
    listing_status: str  # FOR_SALE, FOR_RENT, etc.
    days_on_zillow: Optional[int] = None
    coming_soon_on_market_date: Optional[int] = None
    date_sold: Optional[int] = None
    
    # Media and features
    img_src: Optional[str] = None
    has_image: bool = False
    has_video: bool = False
    has_3d_model: bool = False
    carousel_photos: Optional[List[str]] = None
    photo_count: Optional[int] = None
    
    # Listing subtypes (flags)
    is_fsba: Optional[bool] = None  # For Sale By Agent
    is_open_house: Optional[bool] = None
    is_new_home: Optional[bool] = None
    is_coming_soon: Optional[bool] = None
    is_foreclosure: Optional[bool] = None
    is_bank_owned: Optional[bool] = None
    
    # Construction info
    new_construction_type: Optional[str] = None
    unit: Optional[str] = None  # For condos/apartments
    building_name: Optional[str] = None
    
    # Enhanced property features from Individual Property API (resoFacts)
    reso_facts: Optional[Dict[str, Any]] = None
    appliances: Optional[List[str]] = None
    architectural_style: Optional[str] = None
    basement: Optional[str] = None
    cooling: Optional[str] = None
    exterior: Optional[str] = None
    fireplace: Optional[str] = None
    flooring: Optional[str] = None
    foundation: Optional[str] = None
    heating: Optional[str] = None
    laundry: Optional[str] = None
    roof: Optional[str] = None
    sewer: Optional[str] = None
    water_source: Optional[str] = None
    
    # School information from Individual Property API
    school_district: Optional[Dict[str, Any]] = None
    elementary_school: Optional[str] = None
    middle_school: Optional[str] = None
    high_school: Optional[str] = None
    
    # Neighborhood and market data from Individual Property API
    neighborhood: Optional[Dict[str, Any]] = None
    walk_score: Optional[int] = None
    transit_score: Optional[int] = None
    bike_score: Optional[int] = None
    
    # Climate risk data from Individual Property API
    climate_risk: Optional[Dict[str, Any]] = None
    flood_risk: Optional[str] = None
    fire_risk: Optional[str] = None
    wind_risk: Optional[str] = None
    heat_risk: Optional[str] = None
    
    # Agent/contact information from Individual Property API
    contact_recipients: Optional[List[Dict[str, Any]]] = None
    listing_agent: Optional[Dict[str, Any]] = None
    
    # Building permits and legal information
    building_permits: Optional[List[Dict[str, Any]]] = None
    zoning: Optional[str] = None
    parcel_id: Optional[str] = None
    
    # Additional data
    contingent_listing_type: Optional[str] = None
    variable_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    scraped_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    data_source: str = "zillow_rapidapi"

    @classmethod
    def from_zillow_api(cls, api_data: Dict[str, Any], api_type: str = "search") -> "RealEstateContent":
        """Create RealEstateContent from Zillow API response
        
        Args:
            api_data: Raw API response data
            api_type: Type of API response ('search' for Property Extended Search, 'individual' for Individual Property API)
        """
        # Import here to avoid circular import
        from scraping.zillow.field_mapping import ZillowFieldMapper
        
        # Use the appropriate field mapper based on API type
        if api_type == "individual":
            # Use full property content mapping for Individual Property API
            mapped_data = ZillowFieldMapper.create_full_property_content(api_data)
        else:
            # Use miner-compatible mapping for Property Extended Search
            mapped_data = ZillowFieldMapper.create_miner_compatible_content(api_data)
        
        return cls(**mapped_data)

    def to_data_entity(self) -> DataEntity:
        """Convert to DataEntity for Bittensor storage"""
        
        # Extract zipcode from address for consistent labeling
        # Address format is typically: "123 Main St, City, State ZIP"
        zipcode = None
        address_parts = self.address.split(", ")
        
        # Try to extract 5-digit zipcode from the last part
        if address_parts:
            last_part = address_parts[-1].strip()
            # Look for 5-digit zipcode pattern
            import re
            zipcode_match = re.search(r'\b(\d{5})\b', last_part)
            if zipcode_match:
                zipcode = zipcode_match.group(1)
        
        # Create label using consistent format matching scraping config
        if zipcode:
            # Use format that matches scraping config: "zip:12345"
            label_value = f"zip:{zipcode}"
        else:
            # Fallback to unknown zipcode - this should be rare with good address data
            label_value = "zip:unknown"
        
        label = DataLabel(value=label_value)
        
        # Create URI using Zillow's format
        uri = f"https://zillow.com{self.detail_url}" if self.detail_url.startswith("/") else self.detail_url
        
        # Serialize content
        content_json = self.model_dump_json()
        content_bytes = content_json.encode('utf-8')
        
        return DataEntity(
            uri=uri,
            datetime=self.scraped_at,
            source=DataSource.RAPID_ZILLOW,
            label=label,
            content=content_bytes,
            content_size_bytes=len(content_bytes)
        )

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

    def is_high_value_property(self, threshold: int = 1000000) -> bool:
        """Check if property is above a certain value threshold"""
        return self.price is not None and self.price >= threshold

    def get_location_summary(self) -> str:
        """Get a summary of the property location"""
        parts = self.address.split(", ")
        if len(parts) >= 2:
            return f"{parts[-2]}, {parts[-1]}"  # City, State ZIP
        return self.address
