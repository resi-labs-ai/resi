"""
Property Data Schema Model

This module defines the standardized schema for property data collection
focusing on SOLD PROPERTIES from the last 3 years for home price trends oracle.
"""

import datetime as dt
from typing import Union, List, Dict, Any
from pydantic import BaseModel, Field


class PropertyMetadata(BaseModel):
    """Metadata about the data collection"""
    version: str = "1.0"
    description: str = "Property data collection schema for real estate data"
    collection_date: str = Field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d"))
    miner_hot_key: Union[str, None] = None


class PropertyIDs(BaseModel):
    """Property identification numbers"""
    parcel_number: Union[str, None] = None
    fips_code: Union[str, None] = None


class ZillowIDs(BaseModel):
    """Zillow-specific identifiers"""
    zpid: Union[int, None] = None  # Changed to int as per spec


class MLSIDS(BaseModel):
    """MLS identifiers"""
    mls_number: Union[str, None] = None


class IDsSection(BaseModel):
    """All property identifiers"""
    property: PropertyIDs = Field(default_factory=PropertyIDs)
    zillow: ZillowIDs = Field(default_factory=ZillowIDs)
    mls: MLSIDS = Field(default_factory=MLSIDS)


class PropertyLocation(BaseModel):
    """Property location information"""
    addresses: Union[str, None] = None
    street_number: Union[str, None] = None
    street_name: Union[str, None] = None
    unit_number: Union[str, None] = None
    city: Union[str, None] = None
    state: Union[str, None] = None
    zip_code: Union[str, None] = None
    zip_code_plus_4: Union[str, None] = None
    county: Union[str, None] = None
    latitude: Union[float, None] = None
    longitude: Union[float, None] = None


class HVACType(BaseModel):
    """HVAC system information"""
    heating: Union[List[str], None] = None
    cooling: Union[List[str], None] = None


class SchoolInfo(BaseModel):
    """School information"""
    name: Union[str, None] = None
    rating: Union[int, None] = None
    distance: Union[float, None] = None
    grades: Union[str, None] = None
    type: Union[str, None] = None


class PropertyFeatures(BaseModel):
    """Property interior and exterior features"""
    interior_features: Union[List[str], None] = None
    bedrooms: Union[int, None] = None
    bathrooms: Union[float, None] = None
    full_bathrooms: Union[int, None] = None
    half_bathrooms: Union[int, None] = None
    exterior_features: Union[List[str], None] = None
    garage_spaces: Union[int, None] = None
    total_parking_spaces: Union[int, None] = None
    pool: Union[str, None] = None
    fireplace: Union[int, None] = None
    stories: Union[int, None] = None
    hvac_type: Union[HVACType, None] = None
    flooring_type: Union[List[str], None] = None


class PropertyCharacteristics(BaseModel):
    """Property type and construction details"""
    property_type: Union[str, None] = None
    property_subtype: Union[List[str], None] = None
    construction_material: Union[List[str], None] = None
    year_built: Union[int, None] = None
    year_renovated: Union[int, None] = None


class PropertySize(BaseModel):
    """Property size information"""
    house_size_sqft: Union[int, None] = None
    lot_size_acres: Union[float, None] = None
    lot_size_sqft: Union[int, None] = None


class PropertyUtilities(BaseModel):
    """Utility information"""
    sewer_type: Union[List[str], None] = None
    water_source: Union[List[str], None] = None


class PropertySchool(BaseModel):
    """School district information"""
    elementary_school: Union[SchoolInfo, None] = None
    middle_school: Union[SchoolInfo, None] = None
    high_school: Union[SchoolInfo, None] = None
    school_district: Union[str, None] = None


class DateValue(BaseModel):
    """Date-value pair for historical data"""
    date: str
    value: Union[float, None] = None


class PropertyHOA(BaseModel):
    """HOA fee information"""
    hoa_fee_monthly: Union[List[DateValue], None] = None
    hoa_fee_annual: Union[List[DateValue], None] = None


class PropertySection(BaseModel):
    """Complete property information section"""
    location: PropertyLocation = Field(default_factory=PropertyLocation)
    features: PropertyFeatures = Field(default_factory=PropertyFeatures)
    characteristics: PropertyCharacteristics = Field(default_factory=PropertyCharacteristics)
    size: PropertySize = Field(default_factory=PropertySize)
    utilities: PropertyUtilities = Field(default_factory=PropertyUtilities)
    school: PropertySchool = Field(default_factory=PropertySchool)
    hoa: PropertyHOA = Field(default_factory=PropertyHOA)


class AssessmentData(BaseModel):
    """Tax assessment information"""
    assessor_tax_values: Union[List[DateValue], None] = None
    assessor_market_values: Union[List[DateValue], None] = None


class MarketData(BaseModel):
    """Market valuation information"""
    zestimate_current: Union[float, None] = None
    zestimate_history: Union[List[DateValue], None] = None
    price_per_sqft: Union[List[DateValue], None] = None
    comparable_sales: Union[List[Dict[str, Any]], None] = None


class RentalData(BaseModel):
    """Rental market information"""
    rent_estimate: Union[List[DateValue], None] = None


class ValuationSection(BaseModel):
    """Property valuation information"""
    assessment: AssessmentData = Field(default_factory=AssessmentData)
    market: MarketData = Field(default_factory=MarketData)
    rental: RentalData = Field(default_factory=RentalData)


class TrendsData(BaseModel):
    """Market trend information"""
    days_on_market: Union[List[DateValue], None] = None


class MarketDataSection(BaseModel):
    """Market data and trends"""
    trends: TrendsData = Field(default_factory=TrendsData)


class SaleRecord(BaseModel):
    """Individual sale record"""
    date: str
    value: Union[float, None] = None
    transaction_type: Union[str, None] = None
    source: Union[str, None] = None


class HomeSalesSection(BaseModel):
    """Home sales history"""
    sales_history: Union[List[SaleRecord], None] = None


class ListingEvent(BaseModel):
    """Listing timeline event"""
    date: str
    event: str
    price: Union[float, None] = None


class PriceChange(BaseModel):
    """Price change record"""
    date: str
    old_price: Union[float, None] = None
    new_price: Union[float, None] = None
    change_percent: Union[float, None] = None


class MarketContextSection(BaseModel):
    """Market context information"""
    sale_date: Union[str, None] = None
    final_sale_price: Union[float, None] = None
    listing_timeline: Union[List[ListingEvent], None] = None
    days_on_market: Union[int, None] = None
    price_changes: Union[List[PriceChange], None] = None


class ComparableSale(BaseModel):
    """Comparable sale information"""
    address: Union[str, None] = None
    sale_date: Union[str, None] = None
    sale_price: Union[float, None] = None
    sqft: Union[int, None] = None


class MedianPriceTrend(BaseModel):
    """Monthly median price trend"""
    month: str
    median_price: Union[float, None] = None


class MarketTrends(BaseModel):
    """Neighborhood market trends"""
    median_sale_price_trend: Union[List[MedianPriceTrend], None] = None


class NeighborhoodContextSection(BaseModel):
    """Neighborhood context information"""
    recent_comparable_sales: Union[List[ComparableSale], None] = None
    market_trends: MarketTrends = Field(default_factory=MarketTrends)


class TaxRecord(BaseModel):
    """Tax record with year and amount"""
    year: int
    amount: Union[float, None] = None


class TaxAssessmentSection(BaseModel):
    """Tax assessment information"""
    current_assessment: Union[float, None] = None
    assessment_history: Union[List[DateValue], None] = None
    annual_taxes: Union[List[TaxRecord], None] = None


class PropertyDataSchema(BaseModel):
    """
    Complete property data schema for SOLD PROPERTIES from the last 3 years.
    Focus on properties that have SOLD in the last 3 years (2022-2025).
    Skip active listings or rental properties.
    """
    
    metadata: PropertyMetadata = Field(default_factory=PropertyMetadata)
    ids: IDsSection = Field(default_factory=IDsSection)
    property: PropertySection = Field(default_factory=PropertySection)
    valuation: ValuationSection = Field(default_factory=ValuationSection)
    market_data: MarketDataSection = Field(default_factory=MarketDataSection)
    home_sales: HomeSalesSection = Field(default_factory=HomeSalesSection)
    market_context: MarketContextSection = Field(default_factory=MarketContextSection)
    neighborhood_context: NeighborhoodContextSection = Field(default_factory=NeighborhoodContextSection)
    tax_assessment: TaxAssessmentSection = Field(default_factory=TaxAssessmentSection)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format with null values"""
        return self.model_dump(exclude_unset=False, exclude_none=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PropertyDataSchema":
        """Create from dictionary data"""
        return cls.model_validate(data) 