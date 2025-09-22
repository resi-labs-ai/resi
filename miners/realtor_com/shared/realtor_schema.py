"""
Realtor.com-specific schema extending the base real estate content model.
"""

import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import Field
import json
import hashlib

from common.data import DataEntity, DataLabel, DataSource
from miners.shared.base_schema import BaseRealEstateContent, PropertyValidationMixin


class RealtorRealEstateContent(BaseRealEstateContent, PropertyValidationMixin):
    """Realtor.com-specific real estate content model"""
    
    # Realtor.com-specific identifiers
    realtor_id: Optional[str] = Field(None, description="Realtor.com internal property ID")
    mls_id: Optional[str] = Field(None, description="MLS listing ID")
    listing_id: Optional[str] = Field(None, description="Realtor.com listing ID")
    
    # Realtor.com pricing and market data
    list_price: Optional[int] = Field(None, description="Current list price")
    price_per_sqft: Optional[float] = Field(None, description="Price per square foot")
    estimated_monthly_payment: Optional[int] = Field(None, description="Estimated monthly payment")
    
    # Property details specific to Realtor.com
    square_feet: Optional[int] = Field(None, description="Total square footage")
    lot_sqft: Optional[int] = Field(None, description="Lot size in square feet")
    lot_acres: Optional[float] = Field(None, description="Lot size in acres")
    stories: Optional[int] = Field(None, description="Number of stories")
    garage_spaces: Optional[int] = Field(None, description="Number of garage spaces")
    parking_spaces: Optional[int] = Field(None, description="Total parking spaces")
    
    # Realtor.com listing information
    days_on_market: Optional[int] = Field(None, description="Days on market")
    listing_date: Optional[str] = Field(None, description="Date property was listed")
    status: Optional[str] = Field(None, description="Listing status")
    
    # Property features
    cooling_type: Optional[str] = Field(None, description="Type of cooling system")
    heating_type: Optional[str] = Field(None, description="Type of heating system")
    flooring: Optional[List[str]] = Field(None, description="Types of flooring")
    appliances: Optional[List[str]] = Field(None, description="Included appliances")
    
    # Community and location
    subdivision: Optional[str] = Field(None, description="Subdivision name")
    school_district: Optional[str] = Field(None, description="School district")
    county: Optional[str] = Field(None, description="County")
    
    # Financial information
    hoa_fee: Optional[int] = Field(None, description="Monthly HOA fee")
    property_tax: Optional[int] = Field(None, description="Annual property tax")
    tax_year: Optional[int] = Field(None, description="Tax assessment year")
    
    # Realtor.com-specific features
    virtual_tour_available: bool = Field(default=False, description="Has virtual tour")
    open_house_scheduled: bool = Field(default=False, description="Has scheduled open house")
    new_construction: bool = Field(default=False, description="New construction property")
    foreclosure: bool = Field(default=False, description="Foreclosure property")
    
    # Agent and office information
    listing_office: Optional[str] = Field(None, description="Listing office name")
    listing_agent_name: Optional[str] = Field(None, description="Listing agent name")
    listing_agent_phone: Optional[str] = Field(None, description="Listing agent phone")
    
    # Additional Realtor.com data
    description: Optional[str] = Field(None, description="Property description")
    features: Optional[List[str]] = Field(None, description="Property features list")
    nearby_schools: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby schools with ratings")
    
    def get_platform_source(self) -> DataSource:
        """Return Realtor.com DataSource"""
        return DataSource.REALTOR_COM
    
    @classmethod
    def from_web_scraping(cls, scraped_data: Dict[str, Any], address: str) -> "RealtorRealEstateContent":
        """Create RealtorRealEstateContent from web scraping data"""
        
        # Generate a consistent ID from address
        address_hash = hashlib.md5(address.encode()).hexdigest()[:10]
        
        content_data = {
            # Base fields
            "source_id": scraped_data.get("realtor_id", address_hash),
            "source_platform": "realtor_com",
            "address": address,
            "detail_url": scraped_data.get("detail_url", ""),
            "price": scraped_data.get("price") or scraped_data.get("list_price"),
            "bedrooms": scraped_data.get("bedrooms"),
            "bathrooms": scraped_data.get("bathrooms"),
            "living_area": scraped_data.get("living_area") or scraped_data.get("square_feet"),
            "lot_area_value": scraped_data.get("lot_area_value") or scraped_data.get("lot_sqft"),
            "lot_area_unit": scraped_data.get("lot_area_unit", "sqft"),
            "property_type": scraped_data.get("property_type", "UNKNOWN"),
            "year_built": scraped_data.get("year_built"),
            "listing_status": scraped_data.get("listing_status") or scraped_data.get("status", "UNKNOWN"),
            "latitude": scraped_data.get("latitude"),
            "longitude": scraped_data.get("longitude"),
            "city": scraped_data.get("city"),
            "state": scraped_data.get("state"),
            "zipcode": scraped_data.get("zipcode"),
            "img_src": scraped_data.get("primary_photo"),
            "photos": scraped_data.get("photos"),
            "scraping_method": "web_scraping",
            
            # Realtor.com-specific fields
            "realtor_id": scraped_data.get("realtor_id"),
            "mls_id": scraped_data.get("mls_id"),
            "listing_id": scraped_data.get("listing_id"),
            "list_price": scraped_data.get("list_price"),
            "price_per_sqft": scraped_data.get("price_per_sqft"),
            "estimated_monthly_payment": scraped_data.get("estimated_monthly_payment"),
            "square_feet": scraped_data.get("square_feet"),
            "lot_sqft": scraped_data.get("lot_sqft"),
            "lot_acres": scraped_data.get("lot_acres"),
            "stories": scraped_data.get("stories"),
            "garage_spaces": scraped_data.get("garage_spaces"),
            "parking_spaces": scraped_data.get("parking_spaces"),
            "days_on_market": scraped_data.get("days_on_market"),
            "listing_date": scraped_data.get("listing_date"),
            "status": scraped_data.get("status"),
            "cooling_type": scraped_data.get("cooling_type"),
            "heating_type": scraped_data.get("heating_type"),
            "flooring": scraped_data.get("flooring"),
            "appliances": scraped_data.get("appliances"),
            "subdivision": scraped_data.get("subdivision"),
            "school_district": scraped_data.get("school_district"),
            "county": scraped_data.get("county"),
            "hoa_fee": scraped_data.get("hoa_fee"),
            "property_tax": scraped_data.get("property_tax"),
            "tax_year": scraped_data.get("tax_year"),
            "virtual_tour_available": bool(scraped_data.get("virtual_tour_available", False)),
            "open_house_scheduled": bool(scraped_data.get("open_house_scheduled", False)),
            "new_construction": bool(scraped_data.get("new_construction", False)),
            "foreclosure": bool(scraped_data.get("foreclosure", False)),
            "listing_office": scraped_data.get("listing_office"),
            "listing_agent_name": scraped_data.get("listing_agent_name"),
            "listing_agent_phone": scraped_data.get("listing_agent_phone"),
            "description": scraped_data.get("description"),
            "features": scraped_data.get("features"),
            "nearby_schools": scraped_data.get("nearby_schools"),
            "schools": scraped_data.get("schools") or scraped_data.get("nearby_schools"),
            "agent_name": scraped_data.get("listing_agent_name"),
            "broker_name": scraped_data.get("listing_office"),
            
            # Store remaining scraped data
            "platform_data": {k: v for k, v in scraped_data.items() if k not in [
                "realtor_id", "address", "detail_url", "price", "bedrooms", "bathrooms",
                "living_area", "square_feet", "lot_area_value", "lot_sqft", "lot_area_unit",
                "property_type", "year_built", "listing_status", "status", "latitude",
                "longitude", "city", "state", "zipcode", "primary_photo", "photos",
                "mls_id", "listing_id", "list_price", "price_per_sqft", "estimated_monthly_payment",
                "lot_acres", "stories", "garage_spaces", "parking_spaces", "days_on_market",
                "listing_date", "cooling_type", "heating_type", "flooring", "appliances",
                "subdivision", "school_district", "county", "hoa_fee", "property_tax",
                "tax_year", "virtual_tour_available", "open_house_scheduled", "new_construction",
                "foreclosure", "listing_office", "listing_agent_name", "listing_agent_phone",
                "description", "features", "nearby_schools", "schools"
            ]}
        }
        
        return cls(**content_data)
    
    def to_data_entity(self) -> DataEntity:
        """Convert to DataEntity for Bittensor storage"""
        
        # Create label based on zipcode
        label = self.create_data_label()
        
        # Serialize content
        content_json = self.model_dump_json()
        content_bytes = content_json.encode('utf-8')
        
        return DataEntity(
            uri=self.detail_url,
            datetime=self.scraped_at,
            source=self.get_platform_source(),
            label=label,
            content=content_bytes,
            content_size_bytes=len(content_bytes)
        )
    
    def get_property_features_summary(self) -> Dict[str, Any]:
        """Get a summary of key property features"""
        summary = {}
        
        # Basic metrics
        if self.price and self.living_area:
            summary["price_per_sqft"] = round(self.price / self.living_area, 2)
        
        # Lot information
        if self.lot_sqft:
            summary["lot_size_sqft"] = self.lot_sqft
        elif self.lot_acres:
            summary["lot_size_sqft"] = self.lot_acres * 43560
        
        # Monthly costs estimate
        if self.estimated_monthly_payment:
            summary["estimated_monthly_payment"] = self.estimated_monthly_payment
        elif self.price:
            # Rough estimate: 4% down, 30-year, 7% interest + taxes + insurance
            loan_amount = self.price * 0.96
            monthly_rate = 0.07 / 12
            num_payments = 30 * 12
            
            if monthly_rate > 0:
                mortgage = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
                
                # Add estimates for taxes and insurance
                monthly_tax = (self.property_tax or (self.price * 0.012)) / 12
                monthly_insurance = self.price * 0.0035 / 12
                monthly_hoa = self.hoa_fee or 0
                
                summary["estimated_monthly_payment"] = round(mortgage + monthly_tax + monthly_insurance + monthly_hoa, 2)
        
        # Property condition indicators
        summary["new_construction"] = self.new_construction
        summary["foreclosure"] = self.foreclosure
        summary["has_virtual_tour"] = self.virtual_tour_available
        
        return summary
    
    def get_location_info(self) -> Dict[str, Optional[str]]:
        """Get location information"""
        return {
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zipcode": self.zipcode,
            "county": self.county,
            "subdivision": self.subdivision,
            "school_district": self.school_district
        }
