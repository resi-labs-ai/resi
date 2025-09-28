"""
Homes.com-specific schema extending the base real estate content model.
"""

import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import Field
import json
import hashlib

from common.data import DataEntity, DataLabel, DataSource
from miners.shared.base_schema import BaseRealEstateContent, PropertyValidationMixin


class HomesRealEstateContent(BaseRealEstateContent, PropertyValidationMixin):
    """Homes.com-specific real estate content model"""
    
    # Homes.com-specific identifiers
    homes_id: Optional[str] = Field(None, description="Homes.com internal property ID")
    listing_key: Optional[str] = Field(None, description="Homes.com listing key")
    mls_number: Optional[str] = Field(None, description="MLS listing number")
    
    # Homes.com pricing and estimates
    asking_price: Optional[int] = Field(None, description="Current asking price")
    price_per_sqft: Optional[float] = Field(None, description="Price per square foot")
    estimated_payment: Optional[int] = Field(None, description="Estimated monthly payment")
    down_payment: Optional[int] = Field(None, description="Estimated down payment")
    
    # Property measurements
    total_sqft: Optional[int] = Field(None, description="Total square footage")
    lot_size_sqft: Optional[int] = Field(None, description="Lot size in square feet")
    lot_size_acres: Optional[float] = Field(None, description="Lot size in acres")
    
    # Property characteristics
    levels: Optional[int] = Field(None, description="Number of levels/floors")
    total_rooms: Optional[int] = Field(None, description="Total number of rooms")
    garage_spaces: Optional[int] = Field(None, description="Number of garage spaces")
    carport_spaces: Optional[int] = Field(None, description="Number of carport spaces")
    
    # Homes.com listing details
    listing_date: Optional[str] = Field(None, description="Date property was listed")
    days_on_market: Optional[int] = Field(None, description="Days on market")
    listing_status: Optional[str] = Field(None, description="Current listing status")
    listing_type: Optional[str] = Field(None, description="Type of listing")
    
    # Property condition and features
    condition: Optional[str] = Field(None, description="Property condition")
    construction_type: Optional[str] = Field(None, description="Construction type")
    roof_type: Optional[str] = Field(None, description="Roof type")
    foundation_type: Optional[str] = Field(None, description="Foundation type")
    heating_system: Optional[str] = Field(None, description="Heating system type")
    cooling_system: Optional[str] = Field(None, description="Cooling system type")
    
    # Interior features
    flooring_types: Optional[List[str]] = Field(None, description="Types of flooring")
    appliances_included: Optional[List[str]] = Field(None, description="Included appliances")
    interior_features: Optional[List[str]] = Field(None, description="Interior features")
    
    # Exterior features
    exterior_features: Optional[List[str]] = Field(None, description="Exterior features")
    landscaping: Optional[str] = Field(None, description="Landscaping description")
    fencing: Optional[str] = Field(None, description="Fencing type")
    
    # Location and community
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    subdivision: Optional[str] = Field(None, description="Subdivision name")
    school_district: Optional[str] = Field(None, description="School district")
    county: Optional[str] = Field(None, description="County")
    
    # Financial details
    hoa_fee: Optional[int] = Field(None, description="Monthly HOA fee")
    hoa_frequency: Optional[str] = Field(None, description="HOA fee frequency")
    property_taxes: Optional[int] = Field(None, description="Annual property taxes")
    tax_year: Optional[int] = Field(None, description="Tax assessment year")
    
    # Homes.com specific features
    virtual_tour: bool = Field(default=False, description="Has virtual tour")
    video_tour: bool = Field(default=False, description="Has video tour")
    floor_plan_available: bool = Field(default=False, description="Floor plan available")
    new_construction: bool = Field(default=False, description="New construction")
    
    # Agent and contact information
    listing_agent: Optional[str] = Field(None, description="Listing agent name")
    listing_office: Optional[str] = Field(None, description="Listing office")
    agent_phone: Optional[str] = Field(None, description="Agent phone number")
    agent_email: Optional[str] = Field(None, description="Agent email")
    
    # Additional information
    property_description: Optional[str] = Field(None, description="Detailed property description")
    amenities: Optional[List[str]] = Field(None, description="Community amenities")
    utilities: Optional[List[str]] = Field(None, description="Available utilities")
    
    def get_platform_source(self) -> DataSource:
        """Return Homes.com DataSource"""
        return DataSource.HOMES_COM
    
    @classmethod
    def from_web_scraping(cls, scraped_data: Dict[str, Any], address: str) -> "HomesRealEstateContent":
        """Create HomesRealEstateContent from web scraping data"""
        
        # Generate a consistent ID from address
        address_hash = hashlib.md5(address.encode()).hexdigest()[:10]
        
        content_data = {
            # Base fields
            "source_id": scraped_data.get("homes_id", address_hash),
            "source_platform": "homes_com",
            "address": address,
            "detail_url": scraped_data.get("detail_url", ""),
            "price": scraped_data.get("price") or scraped_data.get("asking_price"),
            "bedrooms": scraped_data.get("bedrooms"),
            "bathrooms": scraped_data.get("bathrooms"),
            "living_area": scraped_data.get("living_area") or scraped_data.get("total_sqft"),
            "lot_area_value": scraped_data.get("lot_area_value") or scraped_data.get("lot_size_sqft"),
            "lot_area_unit": scraped_data.get("lot_area_unit", "sqft"),
            "property_type": scraped_data.get("property_type", "UNKNOWN"),
            "year_built": scraped_data.get("year_built"),
            "listing_status": scraped_data.get("listing_status", "UNKNOWN"),
            "latitude": scraped_data.get("latitude"),
            "longitude": scraped_data.get("longitude"),
            "city": scraped_data.get("city"),
            "state": scraped_data.get("state"),
            "zipcode": scraped_data.get("zipcode"),
            "img_src": scraped_data.get("primary_photo"),
            "photos": scraped_data.get("photos"),
            "scraping_method": "web_scraping",
            
            # Homes.com-specific fields
            "homes_id": scraped_data.get("homes_id"),
            "listing_key": scraped_data.get("listing_key"),
            "mls_number": scraped_data.get("mls_number"),
            "asking_price": scraped_data.get("asking_price"),
            "price_per_sqft": scraped_data.get("price_per_sqft"),
            "estimated_payment": scraped_data.get("estimated_payment"),
            "down_payment": scraped_data.get("down_payment"),
            "total_sqft": scraped_data.get("total_sqft"),
            "lot_size_sqft": scraped_data.get("lot_size_sqft"),
            "lot_size_acres": scraped_data.get("lot_size_acres"),
            "levels": scraped_data.get("levels"),
            "total_rooms": scraped_data.get("total_rooms"),
            "garage_spaces": scraped_data.get("garage_spaces"),
            "carport_spaces": scraped_data.get("carport_spaces"),
            "listing_date": scraped_data.get("listing_date"),
            "days_on_market": scraped_data.get("days_on_market"),
            "listing_type": scraped_data.get("listing_type"),
            "condition": scraped_data.get("condition"),
            "construction_type": scraped_data.get("construction_type"),
            "roof_type": scraped_data.get("roof_type"),
            "foundation_type": scraped_data.get("foundation_type"),
            "heating_system": scraped_data.get("heating_system"),
            "cooling_system": scraped_data.get("cooling_system"),
            "flooring_types": scraped_data.get("flooring_types"),
            "appliances_included": scraped_data.get("appliances_included"),
            "interior_features": scraped_data.get("interior_features"),
            "exterior_features": scraped_data.get("exterior_features"),
            "landscaping": scraped_data.get("landscaping"),
            "fencing": scraped_data.get("fencing"),
            "neighborhood": scraped_data.get("neighborhood"),
            "subdivision": scraped_data.get("subdivision"),
            "school_district": scraped_data.get("school_district"),
            "county": scraped_data.get("county"),
            "hoa_fee": scraped_data.get("hoa_fee"),
            "hoa_frequency": scraped_data.get("hoa_frequency"),
            "property_taxes": scraped_data.get("property_taxes"),
            "tax_year": scraped_data.get("tax_year"),
            "virtual_tour": bool(scraped_data.get("virtual_tour", False)),
            "video_tour": bool(scraped_data.get("video_tour", False)),
            "floor_plan_available": bool(scraped_data.get("floor_plan_available", False)),
            "new_construction": bool(scraped_data.get("new_construction", False)),
            "listing_agent": scraped_data.get("listing_agent"),
            "listing_office": scraped_data.get("listing_office"),
            "agent_phone": scraped_data.get("agent_phone"),
            "agent_email": scraped_data.get("agent_email"),
            "property_description": scraped_data.get("property_description"),
            "amenities": scraped_data.get("amenities"),
            "utilities": scraped_data.get("utilities"),
            "schools": scraped_data.get("schools"),
            "agent_name": scraped_data.get("listing_agent"),
            "broker_name": scraped_data.get("listing_office"),
            
            # Store remaining scraped data
            "platform_data": {k: v for k, v in scraped_data.items() if k not in [
                "homes_id", "address", "detail_url", "price", "asking_price", "bedrooms",
                "bathrooms", "living_area", "total_sqft", "lot_area_value", "lot_size_sqft",
                "lot_area_unit", "property_type", "year_built", "listing_status", "latitude",
                "longitude", "city", "state", "zipcode", "primary_photo", "photos",
                "listing_key", "mls_number", "price_per_sqft", "estimated_payment",
                "down_payment", "lot_size_acres", "levels", "total_rooms", "garage_spaces",
                "carport_spaces", "listing_date", "days_on_market", "listing_type",
                "condition", "construction_type", "roof_type", "foundation_type",
                "heating_system", "cooling_system", "flooring_types", "appliances_included",
                "interior_features", "exterior_features", "landscaping", "fencing",
                "neighborhood", "subdivision", "school_district", "county", "hoa_fee",
                "hoa_frequency", "property_taxes", "tax_year", "virtual_tour", "video_tour",
                "floor_plan_available", "new_construction", "listing_agent", "listing_office",
                "agent_phone", "agent_email", "property_description", "amenities", "utilities",
                "schools"
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
    
    def get_property_summary(self) -> Dict[str, Any]:
        """Get a summary of key property information"""
        summary = {}
        
        # Basic metrics
        if self.price and self.living_area:
            summary["price_per_sqft"] = round(self.price / self.living_area, 2)
        
        # Lot information
        if self.lot_size_sqft:
            summary["lot_size_sqft"] = self.lot_size_sqft
        elif self.lot_size_acres:
            summary["lot_size_sqft"] = self.lot_size_acres * 43560
        
        # Payment information
        if self.estimated_payment:
            summary["estimated_monthly_payment"] = self.estimated_payment
        
        # Property features
        summary["total_rooms"] = self.total_rooms
        summary["garage_spaces"] = self.garage_spaces
        summary["levels"] = self.levels
        
        # Special features
        summary["virtual_tour"] = self.virtual_tour
        summary["video_tour"] = self.video_tour
        summary["new_construction"] = self.new_construction
        
        return summary
    
    def get_financial_breakdown(self) -> Dict[str, Any]:
        """Get financial information breakdown"""
        breakdown = {}
        
        if self.price:
            breakdown["listing_price"] = self.price
        
        if self.down_payment:
            breakdown["down_payment"] = self.down_payment
            if self.price:
                breakdown["down_payment_percent"] = round((self.down_payment / self.price) * 100, 1)
        
        if self.estimated_payment:
            breakdown["monthly_payment"] = self.estimated_payment
        
        # Calculate additional monthly costs
        monthly_extras = 0
        if self.property_taxes:
            monthly_tax = self.property_taxes / 12
            breakdown["monthly_tax"] = round(monthly_tax, 2)
            monthly_extras += monthly_tax
        
        if self.hoa_fee:
            breakdown["monthly_hoa"] = self.hoa_fee
            monthly_extras += self.hoa_fee
        
        if monthly_extras > 0:
            breakdown["monthly_extras"] = round(monthly_extras, 2)
            if self.estimated_payment:
                breakdown["total_monthly_cost"] = round(self.estimated_payment + monthly_extras, 2)
        
        return breakdown
    
    def get_construction_details(self) -> Dict[str, Any]:
        """Get construction and building details"""
        details = {}
        
        details["construction_type"] = self.construction_type
        details["roof_type"] = self.roof_type
        details["foundation_type"] = self.foundation_type
        details["heating_system"] = self.heating_system
        details["cooling_system"] = self.cooling_system
        details["condition"] = self.condition
        
        if self.flooring_types:
            details["flooring_types"] = self.flooring_types
        
        if self.appliances_included:
            details["appliances_included"] = self.appliances_included
        
        return {k: v for k, v in details.items() if v is not None}
