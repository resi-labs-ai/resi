"""
Redfin-specific schema extending the base real estate content model.
"""

import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import Field
import json

from common.data import DataEntity, DataLabel, DataSource
from miners.shared.base_schema import BaseRealEstateContent, PropertyValidationMixin


class RedfinRealEstateContent(BaseRealEstateContent, PropertyValidationMixin):
    """Redfin-specific real estate content model"""
    
    # Redfin-specific identifiers
    redfin_id: str = Field(description="Redfin Property ID")
    mls_number: Optional[str] = Field(None, description="MLS listing number")
    
    # Redfin estimates and pricing
    redfin_estimate: Optional[int] = Field(None, description="Redfin's automated valuation")
    rent_estimate: Optional[int] = Field(None, description="Redfin's rental estimate")
    price_per_sqft: Optional[float] = Field(None, description="Price per square foot")
    
    # Redfin-specific listing info
    days_on_redfin: Optional[int] = Field(None, description="Days listed on Redfin")
    listing_id: Optional[str] = Field(None, description="Redfin listing ID")
    tour_count: Optional[int] = Field(None, description="Number of tours")
    
    # Redfin walkability and transit
    walk_score: Optional[int] = Field(None, description="Walk Score (0-100)")
    transit_score: Optional[int] = Field(None, description="Transit Score (0-100)")
    bike_score: Optional[int] = Field(None, description="Bike Score (0-100)")
    
    # Redfin market data
    market_competition: Optional[str] = Field(None, description="Market competition level")
    price_trend: Optional[str] = Field(None, description="Price trend direction")
    market_insights: Optional[List[str]] = Field(None, description="Market insights")
    
    # Redfin-specific features
    has_tour: bool = Field(default=False, description="Has virtual tour")
    has_open_house: bool = Field(default=False, description="Has scheduled open house")
    is_hot_home: bool = Field(default=False, description="Marked as hot home")
    is_price_reduced: bool = Field(default=False, description="Price recently reduced")
    
    # Redfin neighborhood data
    neighborhood_name: Optional[str] = Field(None, description="Neighborhood name")
    school_district: Optional[str] = Field(None, description="School district")
    
    # Property details specific to Redfin
    lot_size_acres: Optional[float] = Field(None, description="Lot size in acres")
    parking_spaces: Optional[int] = Field(None, description="Number of parking spaces")
    garage_spaces: Optional[int] = Field(None, description="Number of garage spaces")
    
    # Redfin financial information
    hoa_fee: Optional[int] = Field(None, description="Monthly HOA fee")
    property_taxes: Optional[int] = Field(None, description="Annual property taxes")
    insurance_cost: Optional[int] = Field(None, description="Annual insurance cost")
    
    # Redfin agent information
    listing_agent: Optional[Dict[str, Any]] = Field(None, description="Listing agent details")
    brokerage: Optional[str] = Field(None, description="Listing brokerage")
    
    def get_platform_source(self) -> DataSource:
        """Return Redfin DataSource"""
        return DataSource.REDFIN
    
    @classmethod
    def from_web_scraping(cls, scraped_data: Dict[str, Any], redfin_id: str) -> "RedfinRealEstateContent":
        """Create RedfinRealEstateContent from web scraping data"""
        
        content_data = {
            # Base fields
            "source_id": redfin_id,
            "source_platform": "redfin",
            "address": scraped_data.get("address", ""),
            "detail_url": scraped_data.get("detail_url", f"https://www.redfin.com/home/{redfin_id}"),
            "price": scraped_data.get("price"),
            "bedrooms": scraped_data.get("bedrooms"),
            "bathrooms": scraped_data.get("bathrooms"),
            "living_area": scraped_data.get("living_area"),
            "lot_area_value": scraped_data.get("lot_area_value"),
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
            
            # Redfin-specific fields
            "redfin_id": redfin_id,
            "mls_number": scraped_data.get("mls_number"),
            "redfin_estimate": scraped_data.get("redfin_estimate"),
            "rent_estimate": scraped_data.get("rent_estimate"),
            "price_per_sqft": scraped_data.get("price_per_sqft"),
            "days_on_redfin": scraped_data.get("days_on_redfin"),
            "listing_id": scraped_data.get("listing_id"),
            "tour_count": scraped_data.get("tour_count"),
            "walk_score": scraped_data.get("walk_score"),
            "transit_score": scraped_data.get("transit_score"),
            "bike_score": scraped_data.get("bike_score"),
            "market_competition": scraped_data.get("market_competition"),
            "price_trend": scraped_data.get("price_trend"),
            "market_insights": scraped_data.get("market_insights"),
            "has_tour": bool(scraped_data.get("has_tour", False)),
            "has_open_house": bool(scraped_data.get("has_open_house", False)),
            "is_hot_home": bool(scraped_data.get("is_hot_home", False)),
            "is_price_reduced": bool(scraped_data.get("is_price_reduced", False)),
            "neighborhood_name": scraped_data.get("neighborhood_name"),
            "school_district": scraped_data.get("school_district"),
            "lot_size_acres": scraped_data.get("lot_size_acres"),
            "parking_spaces": scraped_data.get("parking_spaces"),
            "garage_spaces": scraped_data.get("garage_spaces"),
            "hoa_fee": scraped_data.get("hoa_fee"),
            "property_taxes": scraped_data.get("property_taxes"),
            "insurance_cost": scraped_data.get("insurance_cost"),
            "listing_agent": scraped_data.get("listing_agent"),
            "brokerage": scraped_data.get("brokerage"),
            "schools": scraped_data.get("schools"),
            "agent_name": scraped_data.get("agent_name"),
            "broker_name": scraped_data.get("brokerage"),
            "days_on_market": scraped_data.get("days_on_redfin"),
            "price_history": scraped_data.get("price_history"),
            
            # Store remaining scraped data
            "platform_data": {k: v for k, v in scraped_data.items() if k not in [
                "address", "detail_url", "price", "bedrooms", "bathrooms", "living_area",
                "lot_area_value", "lot_area_unit", "property_type", "year_built",
                "listing_status", "latitude", "longitude", "city", "state", "zipcode",
                "primary_photo", "photos", "mls_number", "redfin_estimate", "rent_estimate",
                "price_per_sqft", "days_on_redfin", "listing_id", "tour_count",
                "walk_score", "transit_score", "bike_score", "market_competition",
                "price_trend", "market_insights", "has_tour", "has_open_house",
                "is_hot_home", "is_price_reduced", "neighborhood_name", "school_district",
                "lot_size_acres", "parking_spaces", "garage_spaces", "hoa_fee",
                "property_taxes", "insurance_cost", "listing_agent", "brokerage",
                "schools", "agent_name", "price_history"
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
    
    def get_walkability_rating(self) -> str:
        """Get walkability rating description"""
        if not self.walk_score:
            return "Unknown"
        
        if self.walk_score >= 90:
            return "Walker's Paradise"
        elif self.walk_score >= 70:
            return "Very Walkable"
        elif self.walk_score >= 50:
            return "Somewhat Walkable"
        elif self.walk_score >= 25:
            return "Car-Dependent"
        else:
            return "Car-Required"
    
    def get_market_competitiveness(self) -> Optional[str]:
        """Get market competitiveness assessment"""
        return self.market_competition
    
    def calculate_total_monthly_cost(self) -> Optional[float]:
        """Calculate estimated total monthly cost"""
        if not self.price:
            return None
        
        # Rough mortgage calculation (assuming 20% down, 30-year, 7% interest)
        loan_amount = self.price * 0.8
        monthly_rate = 0.07 / 12
        num_payments = 30 * 12
        
        if monthly_rate > 0:
            mortgage_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        else:
            mortgage_payment = loan_amount / num_payments
        
        # Add other monthly costs
        total_monthly = mortgage_payment
        
        if self.property_taxes:
            total_monthly += self.property_taxes / 12
        
        if self.insurance_cost:
            total_monthly += self.insurance_cost / 12
        
        if self.hoa_fee:
            total_monthly += self.hoa_fee
        
        return round(total_monthly, 2)
