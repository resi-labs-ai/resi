"""
Zillow Sold Listings schema for zipcode-based sold property data.
Extends the base real estate content model with sold-specific fields.
"""

import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import Field
import json

from common.data import DataEntity, DataLabel, DataSource
from miners.shared.base_schema import BaseRealEstateContent


class ZillowSoldListingContent(BaseRealEstateContent):
    """Schema for Zillow sold listings with sale-specific data"""
    
    # Core sold listing data
    zpid: str = Field(description="Zillow Property ID")
    sale_date: Optional[str] = Field(None, description="Date property was sold")
    sale_price: Optional[int] = Field(None, description="Final sale price")
    list_price: Optional[int] = Field(None, description="Original listing price")
    days_on_market: Optional[int] = Field(None, description="Days from listing to sale")
    price_reduction: Optional[int] = Field(None, description="Amount of price reduction")
    
    # Market context
    zipcode: str = Field(description="Zipcode where property is located")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    market_hotness: Optional[str] = Field(None, description="Market competition level")
    
    # Property basics (from listing card)
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, description="Living area in square feet")
    lot_size: Optional[str] = Field(None, description="Lot size description")
    property_type: Optional[str] = Field(None, description="Property type")
    
    # Listing metadata
    listing_source: str = Field(default="zillow_sold", description="Source of listing data")
    scraped_from_page: int = Field(description="Which page this listing was found on")
    total_results_in_zipcode: Optional[int] = Field(None, description="Total sold listings in this zipcode")
    
    # Enhanced data (if individual property page was scraped)
    enhanced_data_available: bool = Field(default=False, description="Whether enhanced data was collected")
    zestimate: Optional[int] = Field(None, description="Zillow's automated valuation")
    price_history: Optional[List[Dict[str, Any]]] = Field(None, description="Price change history")
    tax_history: Optional[List[Dict[str, Any]]] = Field(None, description="Tax payment history")
    schools: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby schools")
    agent_name: Optional[str] = Field(None, description="Listing agent's name")
    agent_phone: Optional[str] = Field(None, description="Listing agent's phone")
    
    # Photos and media
    photos: Optional[List[str]] = Field(None, description="List of photo URLs")
    photo_count: Optional[int] = Field(None, description="Number of photos available")
    has_virtual_tour: bool = Field(default=False, description="Has virtual tour")
    
    # Additional sold listing details
    sale_type: Optional[str] = Field(None, description="Type of sale (regular, foreclosure, etc.)")
    financing_type: Optional[str] = Field(None, description="Financing type if available")
    concessions: Optional[str] = Field(None, description="Seller concessions if available")
    
    def get_platform_source(self) -> DataSource:
        """Return Zillow Sold DataSource"""
        return DataSource.ZILLOW_SOLD
    
    @classmethod
    def from_listing_card(
        cls, 
        card_data: Dict[str, Any], 
        zipcode: str, 
        page_number: int,
        total_results: Optional[int] = None
    ) -> "ZillowSoldListingContent":
        """Create ZillowSoldListingContent from sold listing card data"""
        
        content_data = {
            # Base fields
            "source_id": card_data.get("zpid", ""),
            "source_platform": "zillow",
            "source_url": card_data.get("source_url", f"https://www.zillow.com/homedetails/{card_data.get('zpid', '')}_zpid/"),
            "address": card_data.get("address", ""),
            "detail_url": card_data.get("detail_url", f"https://www.zillow.com/homedetails/{card_data.get('zpid', '')}_zpid/"),
            "price": card_data.get("sale_price"),  # Sale price as main price
            "listing_status": "SOLD",
            "city": card_data.get("city"),
            "state": card_data.get("state"),
            "country": "USA",
            "currency": "USD",
            "img_src": card_data.get("primary_photo"),
            "scraping_method": "web_scraping",
            
            # Sold-specific fields
            "zpid": card_data.get("zpid", ""),
            "sale_date": card_data.get("sale_date"),
            "sale_price": card_data.get("sale_price"),
            "list_price": card_data.get("list_price"),
            "days_on_market": card_data.get("days_on_market"),
            "price_reduction": card_data.get("price_reduction"),
            "zipcode": zipcode,
            "neighborhood": card_data.get("neighborhood"),
            "market_hotness": card_data.get("market_hotness"),
            "bedrooms": card_data.get("bedrooms"),
            "bathrooms": card_data.get("bathrooms"),
            "square_feet": card_data.get("square_feet"),
            "lot_size": card_data.get("lot_size"),
            "property_type": card_data.get("property_type"),
            "scraped_from_page": page_number,
            "total_results_in_zipcode": total_results,
            "photos": card_data.get("photos", []),
            "photo_count": len(card_data.get("photos", [])),
            "has_virtual_tour": card_data.get("has_virtual_tour", False),
            "sale_type": card_data.get("sale_type"),
            
            # Store any additional data from the card
            "extra_metadata": {k: v for k, v in card_data.items() if k not in [
                "zpid", "address", "detail_url", "sale_price", "list_price",
                "days_on_market", "price_reduction", "neighborhood", "bedrooms",
                "bathrooms", "square_feet", "lot_size", "property_type", "photos",
                "has_virtual_tour", "sale_type", "primary_photo", "city", "state"
            ]}
        }
        
        return cls(**content_data)
    
    @classmethod
    def enhance_with_property_data(
        cls, 
        base_listing: "ZillowSoldListingContent",
        property_data: Dict[str, Any]
    ) -> "ZillowSoldListingContent":
        """Enhance sold listing with individual property page data"""
        
        # Convert to dict and update with enhanced data
        enhanced_data = base_listing.model_dump()
        enhanced_data.update({
            "enhanced_data_available": True,
            "zestimate": property_data.get("zestimate"),
            "price_history": property_data.get("price_history"),
            "tax_history": property_data.get("tax_history"),
            "schools": property_data.get("schools"),
            "agent_name": property_data.get("agent_name"),
            "agent_phone": property_data.get("agent_phone"),
            "latitude": property_data.get("latitude"),
            "longitude": property_data.get("longitude"),
            "year_built": property_data.get("year_built"),
            "lot_area_value": property_data.get("lot_area_value"),
            "lot_area_unit": property_data.get("lot_area_unit"),
            "hoa_fee": property_data.get("hoa_fee"),
            "tax_value": property_data.get("tax_value"),
            "tax_year": property_data.get("tax_year"),
            "description": property_data.get("description"),
            
            # Merge additional photos if available
            "photos": list(set((enhanced_data.get("photos") or []) + (property_data.get("photos") or []))),
        })
        
        # Update photo count
        enhanced_data["photo_count"] = len(enhanced_data.get("photos", []))
        
        # Add enhanced data to extra_metadata
        enhanced_data["extra_metadata"].update({
            "enhanced_property_data": {k: v for k, v in property_data.items() if k not in [
                "zestimate", "price_history", "tax_history", "schools", "agent_name",
                "agent_phone", "latitude", "longitude", "year_built", "lot_area_value",
                "lot_area_unit", "hoa_fee", "tax_value", "tax_year", "description", "photos"
            ]}
        })
        
        return cls(**enhanced_data)
    
    def to_data_entity(self) -> DataEntity:
        """Convert to DataEntity for Bittensor storage"""
        
        # Create label based on zipcode
        label = DataLabel(value=f"zip:{self.zipcode}")
        
        # Create URI - use the search page URL where this listing was found
        page_uri = f"https://www.zillow.com/sold/{self.zipcode}/?page={self.scraped_from_page}"
        
        # Serialize content
        content_json = self.model_dump_json()
        content_bytes = content_json.encode('utf-8')
        
        return DataEntity(
            uri=page_uri,
            datetime=self.scraped_at,
            source=self.get_platform_source(),
            label=label,
            content=content_bytes,
            content_size_bytes=len(content_bytes)
        )
    
    def get_sale_metrics(self) -> Dict[str, Any]:
        """Calculate sale-specific metrics"""
        metrics = {}
        
        # Price reduction percentage
        if self.list_price and self.sale_price and self.list_price > 0:
            price_diff = self.list_price - self.sale_price
            metrics["price_reduction_percent"] = round((price_diff / self.list_price) * 100, 2)
            metrics["sold_above_below_list"] = "above" if self.sale_price > self.list_price else "below"
        
        # Price per square foot
        if self.sale_price and self.square_feet and self.square_feet > 0:
            metrics["price_per_sqft"] = round(self.sale_price / self.square_feet, 2)
        
        # Market speed indicator
        if self.days_on_market is not None:
            if self.days_on_market <= 7:
                metrics["market_speed"] = "very_fast"
            elif self.days_on_market <= 30:
                metrics["market_speed"] = "fast"
            elif self.days_on_market <= 90:
                metrics["market_speed"] = "normal"
            else:
                metrics["market_speed"] = "slow"
        
        return metrics
    
    def get_comparable_value_estimate(self, comparable_sales: List["ZillowSoldListingContent"]) -> Optional[float]:
        """Estimate property value based on comparable sales in same zipcode"""
        if not comparable_sales or not self.square_feet:
            return None
        
        # Filter comparables by property type and size (within 20% of square footage)
        size_range = self.square_feet * 0.2
        relevant_comps = [
            comp for comp in comparable_sales
            if comp.property_type == self.property_type
            and comp.square_feet
            and comp.sale_price
            and abs(comp.square_feet - self.square_feet) <= size_range
        ]
        
        if not relevant_comps:
            return None
        
        # Calculate average price per sqft from comparables
        avg_price_per_sqft = sum(
            comp.sale_price / comp.square_feet for comp in relevant_comps
        ) / len(relevant_comps)
        
        return round(avg_price_per_sqft * self.square_feet, 0)
