import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json

from common.data import DataEntity, DataLabel, DataSource
from scraping import utils


class RealEstateContent(BaseModel):
    """Content model for real estate listings collected by a custom scraper"""
    
    class Config:
        extra = "forbid"

    # Core identifiers
    # TODO: Replace with your custom primary identifier if not using zpid
    zpid: str = Field(description="Primary Property ID")
    address: str
    detail_url: str
    
    # Property details
    property_type: str  # SINGLE_FAMILY, CONDO, etc.
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    living_area: Optional[int] = Field(None, description="Living area in sq ft")
    
    # Lot information
    lot_area_value: Optional[float] = None
    lot_area_unit: Optional[str] = None  # "acres" or "sqft"
    
    # Pricing and estimates
    price: Optional[int] = None
    zestimate: Optional[int] = None
    rent_zestimate: Optional[int] = None
    price_change: Optional[int] = None
    date_price_changed: Optional[int] = None  # timestamp
    
    # Location data
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: str = "USA"
    currency: str = "USD"
    
    # Listing status
    listing_status: str  # FOR_SALE, FOR_RENT, etc.
    days_on_zillow: Optional[int] = None
    coming_soon_on_market_date: Optional[int] = None
    
    # Media and features
    img_src: Optional[str] = None
    has_image: bool = False
    has_video: bool = False
    has_3d_model: bool = False
    carousel_photos: Optional[List[str]] = None
    
    # Listing subtypes (flags)
    is_fsba: Optional[bool] = None  # For Sale By Agent
    is_open_house: Optional[bool] = None
    is_new_home: Optional[bool] = None
    is_coming_soon: Optional[bool] = None
    
    # Construction info
    new_construction_type: Optional[str] = None
    unit: Optional[str] = None  # For condos/apartments
    
    # Additional data
    contingent_listing_type: Optional[str] = None
    variable_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    scraped_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    data_source: str = "custom"

    @classmethod
    def from_zillow_api(cls, api_data: Dict[str, Any]) -> "RealEstateContent":
        """Create RealEstateContent from a Zillow-like API response (example mapping)."""
        
        # Extract listing subtype flags
        listing_sub_type = api_data.get("listingSubType", {})
        
        return cls(
            zpid=str(api_data.get("zpid", "")),
            address=api_data.get("address", ""),
            detail_url=api_data.get("detailUrl", ""),
            property_type=api_data.get("propertyType", "UNKNOWN"),
            bedrooms=api_data.get("bedrooms"),
            bathrooms=api_data.get("bathrooms"),
            living_area=api_data.get("livingArea"),
            lot_area_value=api_data.get("lotAreaValue"),
            lot_area_unit=api_data.get("lotAreaUnit"),
            price=api_data.get("price"),
            zestimate=api_data.get("zestimate"),
            rent_zestimate=api_data.get("rentZestimate"),
            price_change=api_data.get("priceChange"),
            date_price_changed=api_data.get("datePriceChanged"),
            latitude=api_data.get("latitude"),
            longitude=api_data.get("longitude"),
            country=api_data.get("country", "USA"),
            currency=api_data.get("currency", "USD"),
            listing_status=api_data.get("listingStatus", "UNKNOWN"),
            days_on_zillow=api_data.get("daysOnZillow"),
            coming_soon_on_market_date=api_data.get("comingSoonOnMarketDate"),
            img_src=api_data.get("imgSrc"),
            has_image=bool(api_data.get("hasImage", False)),
            has_video=bool(api_data.get("hasVideo", False)),
            has_3d_model=bool(api_data.get("has3DModel", False)),
            carousel_photos=api_data.get("carouselPhotos"),
            is_fsba=listing_sub_type.get("is_FSBA"),
            is_open_house=listing_sub_type.get("is_openHouse"),
            is_new_home=listing_sub_type.get("is_newHome"),
            is_coming_soon=listing_sub_type.get("is_comingSoon"),
            new_construction_type=api_data.get("newConstructionType"),
            unit=api_data.get("unit"),
            contingent_listing_type=api_data.get("contingentListingType"),
            variable_data=api_data.get("variableData"),
        )

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
        
        # TODO: Create URI using your site's detail URL format
        uri = self.detail_url
        
        # Serialize content
        content_json = self.model_dump_json()
        content_bytes = content_json.encode('utf-8')
        
        return DataEntity(
            uri=uri,
            datetime=self.scraped_at,
            source=DataSource.UNKNOWN_4,
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
