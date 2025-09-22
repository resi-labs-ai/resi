"""
Zillow-specific schema extending the base real estate content model.
"""

import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import Field
import json

from common.data import DataEntity, DataLabel, DataSource
from miners.shared.base_schema import BaseRealEstateContent, PropertyValidationMixin


class ZillowRealEstateContent(BaseRealEstateContent, PropertyValidationMixin):
    """Zillow-specific real estate content model"""
    
    # Zillow-specific identifiers
    zpid: str = Field(description="Zillow Property ID")
    
    # Zillow estimates and pricing
    zestimate: Optional[int] = Field(None, description="Zillow's automated valuation")
    rent_zestimate: Optional[int] = Field(None, description="Zillow's rental estimate")
    price_change: Optional[int] = Field(None, description="Recent price change amount")
    date_price_changed: Optional[int] = Field(None, description="Date price changed (timestamp)")
    
    # Zillow-specific listing info
    days_on_zillow: Optional[int] = Field(None, description="Days listed on Zillow")
    coming_soon_on_market_date: Optional[int] = Field(None, description="Coming soon date")
    page_view_count: Optional[int] = Field(None, description="Number of page views")
    favorite_count: Optional[int] = Field(None, description="Number of favorites")
    
    # Zillow media
    has_image: bool = Field(default=False, description="Has images")
    has_video: bool = Field(default=False, description="Has video tour")
    has_3d_model: bool = Field(default=False, description="Has 3D model/tour")
    carousel_photos: Optional[List[str]] = Field(None, description="Carousel photo URLs")
    photo_count: Optional[int] = Field(None, description="Total number of photos")
    
    # Zillow listing subtypes
    is_fsba: Optional[bool] = Field(None, description="For Sale By Agent")
    is_open_house: Optional[bool] = Field(None, description="Has open house")
    is_new_home: Optional[bool] = Field(None, description="New construction")
    is_coming_soon: Optional[bool] = Field(None, description="Coming soon listing")
    is_foreclosure: Optional[bool] = Field(None, description="Foreclosure listing")
    
    # Zillow-specific details
    monthly_hoa_fee: Optional[int] = Field(None, description="Monthly HOA fee")
    property_tax_rate: Optional[float] = Field(None, description="Property tax rate")
    annual_homeowners_insurance: Optional[int] = Field(None, description="Annual insurance cost")
    
    # Zillow tax and price history
    tax_history: Optional[List[Dict[str, Any]]] = Field(None, description="Tax payment history")
    
    # Zillow neighborhood data
    neighborhood_region: Optional[Dict[str, Any]] = Field(None, description="Neighborhood info")
    nearby_homes: Optional[List[Dict[str, Any]]] = Field(None, description="Comparable properties")
    
    # Zillow climate data (if available from API)
    climate_data: Optional[Dict[str, Any]] = Field(None, description="Climate risk data")
    
    # Construction details
    new_construction_type: Optional[str] = Field(None, description="New construction type")
    unit: Optional[str] = Field(None, description="Unit number (condos/apartments)")
    
    # Additional Zillow fields
    contingent_listing_type: Optional[str] = Field(None, description="Contingent listing type")
    time_zone: Optional[str] = Field(None, description="Property time zone")
    
    def get_platform_source(self) -> DataSource:
        """Return Zillow DataSource"""
        return DataSource.ZILLOW
    
    @classmethod
    def from_zillow_api(cls, api_data: Dict[str, Any]) -> "ZillowRealEstateContent":
        """Create ZillowRealEstateContent from Zillow API response"""
        
        # Extract listing subtype flags
        listing_sub_type = api_data.get("listingSubType", {})
        
        # Build the content object
        content_data = {
            # Base fields
            "source_id": str(api_data.get("zpid", "")),
            "source_platform": "zillow",
            "address": api_data.get("address", ""),
            "detail_url": api_data.get("detailUrl", ""),
            "price": api_data.get("price"),
            "bedrooms": api_data.get("bedrooms"),
            "bathrooms": api_data.get("bathrooms"),
            "living_area": api_data.get("livingArea"),
            "lot_area_value": api_data.get("lotAreaValue"),
            "lot_area_unit": api_data.get("lotAreaUnit"),
            "property_type": api_data.get("propertyType", "UNKNOWN"),
            "year_built": api_data.get("yearBuilt"),
            "listing_status": api_data.get("listingStatus", "UNKNOWN"),
            "latitude": api_data.get("latitude"),
            "longitude": api_data.get("longitude"),
            "city": api_data.get("city"),
            "state": api_data.get("state"),
            "zipcode": api_data.get("zipcode"),
            "country": api_data.get("country", "USA"),
            "currency": api_data.get("currency", "USD"),
            "img_src": api_data.get("imgSrc"),
            "scraping_method": "api",
            
            # Zillow-specific fields
            "zpid": str(api_data.get("zpid", "")),
            "zestimate": api_data.get("zestimate"),
            "rent_zestimate": api_data.get("rentZestimate"),
            "price_change": api_data.get("priceChange"),
            "date_price_changed": api_data.get("datePriceChanged"),
            "days_on_zillow": api_data.get("daysOnZillow"),
            "coming_soon_on_market_date": api_data.get("comingSoonOnMarketDate"),
            "page_view_count": api_data.get("pageViewCount"),
            "favorite_count": api_data.get("favoriteCount"),
            "has_image": bool(api_data.get("hasImage", False)),
            "has_video": bool(api_data.get("hasVideo", False)),
            "has_3d_model": bool(api_data.get("has3DModel", False)),
            "carousel_photos": api_data.get("carouselPhotos"),
            "photo_count": api_data.get("photoCount"),
            "is_fsba": listing_sub_type.get("is_FSBA"),
            "is_open_house": listing_sub_type.get("is_openHouse"),
            "is_new_home": listing_sub_type.get("is_newHome"),
            "is_coming_soon": listing_sub_type.get("is_comingSoon"),
            "is_foreclosure": listing_sub_type.get("is_foreclosure"),
            "monthly_hoa_fee": api_data.get("monthlyHoaFee"),
            "property_tax_rate": api_data.get("propertyTaxRate"),
            "annual_homeowners_insurance": api_data.get("annualHomeownersInsurance"),
            "tax_history": api_data.get("taxHistory"),
            "price_history": api_data.get("priceHistory"),
            "neighborhood_region": api_data.get("neighborhoodRegion"),
            "nearby_homes": api_data.get("nearbyHomes"),
            "climate_data": api_data.get("climate"),
            "new_construction_type": api_data.get("newConstructionType"),
            "unit": api_data.get("unit"),
            "contingent_listing_type": api_data.get("contingentListingType"),
            "time_zone": api_data.get("timeZone"),
            "schools": api_data.get("schools"),
            "agent_name": api_data.get("listed_by", {}).get("display_name") if api_data.get("listed_by") else None,
            "broker_name": api_data.get("brokerageName"),
            "days_on_market": api_data.get("daysOnZillow"),  # Map to base field
            
            # Store any additional data
            "platform_data": {k: v for k, v in api_data.items() if k not in [
                "zpid", "address", "detailUrl", "price", "bedrooms", "bathrooms", 
                "livingArea", "lotAreaValue", "lotAreaUnit", "propertyType", 
                "yearBuilt", "listingStatus", "latitude", "longitude", "city", 
                "state", "zipcode", "country", "currency", "imgSrc", "zestimate",
                "rentZestimate", "priceChange", "datePriceChanged", "daysOnZillow",
                "comingSoonOnMarketDate", "pageViewCount", "favoriteCount",
                "hasImage", "hasVideo", "has3DModel", "carouselPhotos", "photoCount",
                "listingSubType", "monthlyHoaFee", "propertyTaxRate",
                "annualHomeownersInsurance", "taxHistory", "priceHistory",
                "neighborhoodRegion", "nearbyHomes", "climate", "newConstructionType",
                "unit", "contingentListingType", "timeZone", "schools", "listed_by",
                "brokerageName"
            ]}
        }
        
        return cls(**content_data)
    
    @classmethod
    def from_web_scraping(cls, scraped_data: Dict[str, Any], zpid: str) -> "ZillowRealEstateContent":
        """Create ZillowRealEstateContent from web scraping data"""
        
        content_data = {
            # Base fields
            "source_id": zpid,
            "source_platform": "zillow",
            "address": scraped_data.get("address", ""),
            "detail_url": f"https://www.zillow.com/homedetails/ADDRESS/{zpid}_zpid/",
            "price": scraped_data.get("price"),
            "bedrooms": scraped_data.get("bedrooms"),
            "bathrooms": scraped_data.get("bathrooms"),
            "living_area": scraped_data.get("living_area"),
            "lot_area_value": scraped_data.get("lot_area_value"),
            "lot_area_unit": scraped_data.get("lot_area_unit"),
            "property_type": scraped_data.get("property_type", "UNKNOWN"),
            "year_built": scraped_data.get("year_built"),
            "listing_status": scraped_data.get("listing_status", "UNKNOWN"),
            "scraping_method": "web_scraping",
            
            # Zillow-specific fields (from web scraping)
            "zpid": zpid,
            "zestimate": scraped_data.get("zestimate"),
            "rent_zestimate": scraped_data.get("rent_zestimate"),
            "has_image": bool(scraped_data.get("photos")),
            "carousel_photos": scraped_data.get("photos"),
            "img_src": scraped_data.get("photos", [None])[0] if scraped_data.get("photos") else None,
            "price_history": scraped_data.get("price_history"),
            "schools": scraped_data.get("schools"),
            "agent_name": scraped_data.get("agent_name"),
            "days_on_market": scraped_data.get("days_on_market"),
            
            # Store remaining scraped data
            "platform_data": {k: v for k, v in scraped_data.items() if k not in [
                "address", "price", "bedrooms", "bathrooms", "living_area",
                "lot_area_value", "lot_area_unit", "property_type", "year_built",
                "listing_status", "zestimate", "rent_zestimate", "photos",
                "price_history", "schools", "agent_name", "days_on_market"
            ]}
        }
        
        return cls(**content_data)
    
    def to_data_entity(self) -> DataEntity:
        """Convert to DataEntity for Bittensor storage"""
        
        # Create label based on zipcode
        label = self.create_data_label()
        
        # Create URI
        uri = f"https://zillow.com{self.detail_url}" if self.detail_url.startswith("/") else self.detail_url
        
        # Serialize content
        content_json = self.model_dump_json()
        content_bytes = content_json.encode('utf-8')
        
        return DataEntity(
            uri=uri,
            datetime=self.scraped_at,
            source=self.get_platform_source(),
            label=label,
            content=content_bytes,
            content_size_bytes=len(content_bytes)
        )
    
    def get_zestimate_accuracy(self) -> Optional[str]:
        """Get Zestimate accuracy description"""
        if not self.zestimate or not self.price:
            return None
        
        diff_percent = abs(self.zestimate - self.price) / self.price * 100
        
        if diff_percent < 5:
            return "Very Accurate"
        elif diff_percent < 10:
            return "Accurate"
        elif diff_percent < 20:
            return "Somewhat Accurate"
        else:
            return "Less Accurate"
    
    def get_investment_metrics(self) -> Dict[str, Optional[float]]:
        """Calculate basic investment metrics"""
        metrics = {}
        
        # Price to rent ratio
        if self.price and self.rent_zestimate:
            monthly_rent = self.rent_zestimate
            annual_rent = monthly_rent * 12
            metrics["price_to_rent_ratio"] = round(self.price / annual_rent, 2)
            metrics["gross_rental_yield"] = round((annual_rent / self.price) * 100, 2)
        
        # Price per sqft
        metrics["price_per_sqft"] = self.get_price_per_sqft()
        
        # Lot size metrics
        metrics["lot_size_sqft"] = self.get_lot_size_sqft()
        
        return metrics
