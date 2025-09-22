"""
Comprehensive Zillow Schema - Enhanced to match API data structure.
This schema attempts to capture the maximum amount of data available from Zillow pages,
matching the 78+ top-level fields and hundreds of nested fields from the API.
"""

import datetime as dt
from typing import Optional, List, Dict, Any, Union
from pydantic import Field, validator
import json
import re

from common.data import DataEntity, DataLabel, DataSource
from miners.shared.base_schema import BaseRealEstateContent, PropertyValidationMixin


class ZillowContact(BaseRealEstateContent):
    """Zillow contact/agent information"""
    agent_reason: Optional[int] = None
    zpro: Optional[str] = None
    recent_sales: Optional[int] = None
    review_count: Optional[int] = None
    display_name: Optional[str] = None
    badge_type: Optional[str] = None
    business_name: Optional[str] = None
    rating_average: Optional[float] = None
    phone: Optional[Dict[str, str]] = None
    zuid: Optional[str] = None
    image_url: Optional[str] = None


class ZillowAddress(BaseRealEstateContent):
    """Zillow address structure"""
    city: Optional[str] = None
    state: Optional[str] = None
    streetAddress: Optional[str] = None
    zipcode: Optional[str] = None


class ZillowAttributionInfo(BaseRealEstateContent):
    """MLS and broker attribution information"""
    agentPhoneNumber: Optional[str] = None
    trueStatus: Optional[str] = None
    providerLogo: Optional[str] = None
    mlsId: Optional[str] = None
    brokerName: Optional[str] = None
    mlsName: Optional[str] = None
    brokerPhoneNumber: Optional[str] = None
    agentName: Optional[str] = None


class ZillowTaxRecord(BaseRealEstateContent):
    """Individual tax history record"""
    time: Optional[int] = Field(None, description="Timestamp of tax record")
    valueIncreaseRate: Optional[float] = Field(None, description="Property value increase rate")
    taxIncreaseRate: Optional[float] = Field(None, description="Tax increase rate")
    taxPaid: Optional[float] = Field(None, description="Tax amount paid")
    value: Optional[int] = Field(None, description="Assessed property value")


class ZillowPriceRecord(BaseRealEstateContent):
    """Individual price history record"""
    date: Optional[str] = Field(None, description="Date of price event")
    price: Optional[int] = Field(None, description="Price at this event")
    priceChangeRate: Optional[float] = Field(None, description="Price change rate")
    event: Optional[str] = Field(None, description="Type of price event (sale, listing, etc.)")
    source: Optional[str] = Field(None, description="Source of price information")


class ZillowClimateData(BaseRealEstateContent):
    """Climate and environmental risk data"""
    floodRisk: Optional[Dict[str, Any]] = Field(None, description="Flood risk assessment")
    fireRisk: Optional[Dict[str, Any]] = Field(None, description="Fire risk assessment")
    heatRisk: Optional[Dict[str, Any]] = Field(None, description="Heat risk assessment")
    airQuality: Optional[Dict[str, Any]] = Field(None, description="Air quality data")
    environmentalHazards: Optional[List[str]] = Field(None, description="Environmental hazards")


class ZillowHomeInsights(BaseRealEstateContent):
    """Home insights and market analytics"""
    daysOnZillow: Optional[int] = Field(None, description="Days property has been on Zillow")
    pageViews: Optional[int] = Field(None, description="Number of page views")
    favoriteCount: Optional[int] = Field(None, description="Number of times favorited")
    priceHistory: Optional[List[ZillowPriceRecord]] = Field(None, description="Complete price history")
    marketAppreciation: Optional[Dict[str, Any]] = Field(None, description="Market appreciation data")


class ZillowHomeFacts(BaseRealEstateContent):
    """Detailed home facts and features"""
    atAGlanceFacts: Optional[List[Dict[str, Any]]] = Field(None, description="Quick facts")
    categoryDetails: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed categories")
    architecturalStyle: Optional[str] = Field(None, description="Architectural style")
    constructionMaterials: Optional[List[str]] = Field(None, description="Construction materials")
    foundationType: Optional[str] = Field(None, description="Foundation type")
    roofType: Optional[str] = Field(None, description="Roof type")
    heatingType: Optional[str] = Field(None, description="Heating system type")
    coolingType: Optional[str] = Field(None, description="Cooling system type")
    parkingType: Optional[str] = Field(None, description="Parking type")
    parkingSpaces: Optional[int] = Field(None, description="Number of parking spaces")
    garageSpaces: Optional[int] = Field(None, description="Number of garage spaces")
    stories: Optional[int] = Field(None, description="Number of stories")
    fireplaces: Optional[int] = Field(None, description="Number of fireplaces")


class ZillowNeighborhoodData(BaseRealEstateContent):
    """Neighborhood information"""
    neighborhoodName: Optional[str] = Field(None, description="Neighborhood name")
    walkScore: Optional[int] = Field(None, description="Walk score")
    transitScore: Optional[int] = Field(None, description="Transit score")
    bikeScore: Optional[int] = Field(None, description="Bike score")
    demographics: Optional[Dict[str, Any]] = Field(None, description="Neighborhood demographics")
    amenities: Optional[List[str]] = Field(None, description="Nearby amenities")


class ZillowSchool(BaseRealEstateContent):
    """School information"""
    name: Optional[str] = Field(None, description="School name")
    rating: Optional[int] = Field(None, description="School rating")
    level: Optional[str] = Field(None, description="School level (elementary, middle, high)")
    type: Optional[str] = Field(None, description="School type (public, private)")
    distance: Optional[float] = Field(None, description="Distance from property")
    grades: Optional[str] = Field(None, description="Grades served")
    enrollment: Optional[int] = Field(None, description="Student enrollment")


class ZillowMortgageRates(BaseRealEstateContent):
    """Mortgage rate information"""
    thirtyYearFixedRate: Optional[float] = Field(None, description="30-year fixed rate")
    fifteenYearFixedRate: Optional[float] = Field(None, description="15-year fixed rate")
    fiveOneArmRate: Optional[float] = Field(None, description="5/1 ARM rate")
    jumboRate: Optional[float] = Field(None, description="Jumbo loan rate")


class ComprehensiveZillowRealEstateContent(BaseRealEstateContent, PropertyValidationMixin):
    """
    Comprehensive Zillow real estate content model that attempts to capture
    the maximum amount of data available from Zillow, matching API structure.
    
    This schema includes 78+ top-level fields and hundreds of nested fields.
    """
    
    # === CORE ZILLOW IDENTIFIERS ===
    zpid: str = Field(description="Zillow Property ID")
    
    # === BASIC PROPERTY INFO ===
    homeType: Optional[str] = Field(None, description="Home type (SINGLE_FAMILY, CONDO, etc.)")
    homeStatus: Optional[str] = Field(None, description="Home status (FOR_SALE, FOR_RENT, etc.)")
    listingStatus: Optional[str] = Field(None, description="Listing status")
    
    # === PRICING AND ESTIMATES ===
    zestimate: Optional[int] = Field(None, description="Zillow's automated valuation")
    rentZestimate: Optional[int] = Field(None, description="Zillow's rental estimate")
    zestimateHighPercent: Optional[float] = Field(None, description="Zestimate high range percentage")
    zestimateLowPercent: Optional[float] = Field(None, description="Zestimate low range percentage")
    
    # === PROPERTY MEASUREMENTS ===
    livingAreaValue: Optional[int] = Field(None, description="Living area in square feet")
    livingAreaUnits: Optional[str] = Field(None, description="Living area units")
    lotSize: Optional[int] = Field(None, description="Lot size")
    lotAreaValue: Optional[float] = Field(None, description="Lot area value")
    lotAreaUnits: Optional[str] = Field(None, description="Lot area units")
    
    # === FINANCIAL INFORMATION ===
    monthlyHoaFee: Optional[int] = Field(None, description="Monthly HOA fee")
    annualHomeownersInsurance: Optional[int] = Field(None, description="Annual homeowners insurance")
    propertyTaxRate: Optional[float] = Field(None, description="Property tax rate")
    
    # === LOCATION DATA ===
    countyFIPS: Optional[str] = Field(None, description="County FIPS code")
    timeZone: Optional[str] = Field(None, description="Property timezone")
    
    # === LISTING INFORMATION ===
    datePosted: Optional[int] = Field(None, description="Date posted timestamp")
    dateSold: Optional[int] = Field(None, description="Date sold timestamp")
    daysOnZillow: Optional[int] = Field(None, description="Days on Zillow")
    isListedByOwner: Optional[bool] = Field(None, description="Listed by owner flag")
    isShowcaseListing: Optional[bool] = Field(None, description="Showcase listing flag")
    comingSoonOnMarketDate: Optional[int] = Field(None, description="Coming soon date")
    
    # === MEDIA AND PHOTOS ===
    imgSrc: Optional[str] = Field(None, description="Primary image URL")
    carouselPhotos: Optional[List[Dict[str, Any]]] = Field(None, description="All carousel photos")
    tourUrl: Optional[str] = Field(None, description="Virtual tour URL")
    videoUrl: Optional[str] = Field(None, description="Property video URL")
    
    # === COMPLEX NESTED DATA ===
    contact_recipients: Optional[List[ZillowContact]] = Field(None, description="Contact information")
    attributionInfo: Optional[ZillowAttributionInfo] = Field(None, description="MLS attribution")
    taxHistory: Optional[List[ZillowTaxRecord]] = Field(None, description="Tax history")
    priceHistory: Optional[List[ZillowPriceRecord]] = Field(None, description="Price history")
    climate: Optional[ZillowClimateData] = Field(None, description="Climate data")
    homeInsights: Optional[ZillowHomeInsights] = Field(None, description="Home insights")
    homeFacts: Optional[ZillowHomeFacts] = Field(None, description="Home facts")
    nearbyHomes: Optional[List[Dict[str, Any]]] = Field(None, description="Nearby comparable homes")
    neighborhoodData: Optional[ZillowNeighborhoodData] = Field(None, description="Neighborhood information")
    schools: Optional[List[ZillowSchool]] = Field(None, description="School information")
    mortgageRates: Optional[ZillowMortgageRates] = Field(None, description="Current mortgage rates")
    
    # === BUILDING AND COMPLEX INFO ===
    buildingId: Optional[str] = Field(None, description="Building ID for condos/apartments")
    building: Optional[Dict[str, Any]] = Field(None, description="Building information")
    buildingPermits: Optional[List[Dict[str, Any]]] = Field(None, description="Building permits")
    
    # === LISTING DETAILS ===
    listingProvider: Optional[str] = Field(None, description="Listing provider")
    listingSubType: Optional[Dict[str, Any]] = Field(None, description="Listing sub-type flags")
    mlsid: Optional[str] = Field(None, description="MLS ID")
    brokerId: Optional[str] = Field(None, description="Broker ID")
    brokerageName: Optional[str] = Field(None, description="Brokerage name")
    
    # === MARKET AND ANALYTICS ===
    favoriteCount: Optional[int] = Field(None, description="Number of favorites")
    pageViews: Optional[int] = Field(None, description="Page view count")
    marketTrends: Optional[Dict[str, Any]] = Field(None, description="Market trend data")
    
    # === OPEN HOUSE AND SCHEDULE ===
    openHouseSchedule: Optional[List[Dict[str, Any]]] = Field(None, description="Open house schedule")
    
    # === NEIGHBORHOOD AMENITIES ===
    neighborhoodRegion: Optional[Dict[str, Any]] = Field(None, description="Neighborhood region data")
    
    # === METADATA AND EXTRAS ===
    _metadata: Optional[Dict[str, Any]] = Field(None, description="Zillow internal metadata")
    
    # === DATA QUALITY INDICATORS ===
    data_completeness_score: Optional[float] = Field(None, description="Percentage of fields populated")
    extraction_confidence: Optional[float] = Field(None, description="Confidence in extracted data")
    
    def get_platform_source(self) -> DataSource:
        """Return Zillow DataSource"""
        return DataSource.ZILLOW
    
    @classmethod
    def from_zillow_api(cls, api_data: Dict[str, Any]) -> "ComprehensiveZillowRealEstateContent":
        """Create from Zillow API response (for reference/comparison)"""
        
        # Map API data to schema
        mapped_data = {
            "source_id": str(api_data.get("zpid", "")),
            "source_platform": "zillow",
            "source_url": api_data.get("hdpUrl", ""),
            "zpid": str(api_data.get("zpid", "")),
            "address": api_data.get("address", {}).get("streetAddress", "") or api_data.get("streetAddress", ""),
            "detail_url": api_data.get("hdpUrl", ""),
            "scraping_method": "api",
            
            # Basic info
            "price": api_data.get("price"),
            "bedrooms": api_data.get("bedrooms"),
            "bathrooms": api_data.get("bathrooms"),
            "living_area": api_data.get("livingAreaValue") or api_data.get("livingArea"),
            "property_type": api_data.get("homeType", "UNKNOWN"),
            "year_built": api_data.get("yearBuilt"),
            "listing_status": api_data.get("homeStatus", "UNKNOWN"),
            
            # Location
            "latitude": api_data.get("latitude"),
            "longitude": api_data.get("longitude"),
            "city": api_data.get("city") or (api_data.get("address", {}).get("city") if api_data.get("address") else None),
            "state": api_data.get("state") or (api_data.get("address", {}).get("state") if api_data.get("address") else None),
            "zipcode": api_data.get("zipcode") or (api_data.get("address", {}).get("zipcode") if api_data.get("address") else None),
            
            # Zillow-specific
            "homeType": api_data.get("homeType"),
            "homeStatus": api_data.get("homeStatus"),
            "zestimate": api_data.get("zestimate"),
            "rentZestimate": api_data.get("rentZestimate"),
            "livingAreaValue": api_data.get("livingAreaValue"),
            "livingAreaUnits": api_data.get("livingAreaUnits"),
            "lotSize": api_data.get("lotSize"),
            "lotAreaValue": api_data.get("lotAreaValue"),
            "lotAreaUnits": api_data.get("lotAreaUnits"),
            "monthlyHoaFee": api_data.get("monthlyHoaFee"),
            "annualHomeownersInsurance": api_data.get("annualHomeownersInsurance"),
            "countyFIPS": api_data.get("countyFIPS"),
            "timeZone": api_data.get("timeZone"),
            "datePosted": api_data.get("datePosted"),
            "dateSold": api_data.get("dateSold"),
            "daysOnZillow": api_data.get("daysOnZillow"),
            "isListedByOwner": api_data.get("isListedByOwner"),
            "isShowcaseListing": api_data.get("isShowcaseListing"),
            "imgSrc": api_data.get("imgSrc"),
            "favoriteCount": api_data.get("favoriteCount"),
            "mlsid": api_data.get("mlsid"),
            "brokerId": api_data.get("brokerId"),
            "brokerageName": api_data.get("brokerageName"),
            
            # Complex nested data
            "contact_recipients": api_data.get("contact_recipients"),
            "attributionInfo": api_data.get("attributionInfo"),
            "taxHistory": api_data.get("taxHistory"),
            "priceHistory": api_data.get("priceHistory"),
            "climate": api_data.get("climate"),
            "homeInsights": api_data.get("homeInsights"),
            "homeFacts": api_data.get("homeFacts"),
            "nearbyHomes": api_data.get("nearbyHomes"),
            "schools": api_data.get("schools"),
            "mortgageRates": api_data.get("mortgageRates"),
            "building": api_data.get("building"),
            "buildingPermits": api_data.get("buildingPermits"),
            "listingSubType": api_data.get("listingSubType"),
            "openHouseSchedule": api_data.get("openHouseSchedule"),
            "_metadata": api_data.get("_metadata"),
            
            # Photos and media
            "img_src": api_data.get("imgSrc"),
            "photos": [photo.get("url") for photo in api_data.get("carouselPhotos", []) if photo.get("url")],
            "carouselPhotos": api_data.get("carouselPhotos"),
            
            # Agent info
            "agent_name": None,
            "broker_name": api_data.get("brokerageName"),
        }
        
        # Extract agent name from contact_recipients
        if api_data.get("contact_recipients") and len(api_data["contact_recipients"]) > 0:
            mapped_data["agent_name"] = api_data["contact_recipients"][0].get("display_name")
        
        # Store all remaining API data in platform_data
        mapped_data["platform_data"] = {k: v for k, v in api_data.items() if k not in mapped_data}
        
        return cls(**mapped_data)
    
    @classmethod
    def from_web_scraping(cls, scraped_data: Dict[str, Any], zpid: str, source_url: str) -> "ComprehensiveZillowRealEstateContent":
        """Create from web scraping data with comprehensive field mapping"""
        
        # Calculate data completeness score
        total_fields = len(cls.__fields__)
        populated_fields = len([k for k, v in scraped_data.items() if v is not None and v != ""])
        completeness_score = (populated_fields / total_fields) * 100
        
        mapped_data = {
            # Required fields
            "source_id": zpid,
            "source_platform": "zillow",
            "source_url": source_url,
            "zpid": zpid,
            "address": scraped_data.get("address", ""),
            "detail_url": scraped_data.get("detail_url", source_url),
            "property_type": scraped_data.get("property_type", "UNKNOWN"),
            "listing_status": scraped_data.get("listing_status", "UNKNOWN"),
            "scraping_method": "web_scraping",
            
            # Data quality indicators
            "data_completeness_score": completeness_score,
            "extraction_confidence": scraped_data.get("extraction_confidence", 0.8),
            
            # Map all scraped data to corresponding fields
            **{k: v for k, v in scraped_data.items() if k in cls.__fields__}
        }
        
        # Store unmapped data in platform_data
        unmapped_data = {k: v for k, v in scraped_data.items() if k not in cls.__fields__}
        if unmapped_data:
            mapped_data["platform_data"] = unmapped_data
        
        return cls(**mapped_data)
    
    def to_data_entity(self) -> DataEntity:
        """Convert to DataEntity for Bittensor storage"""
        
        # Create label based on zipcode
        label = self.create_data_label()
        
        # Serialize content
        content_json = self.model_dump_json()
        content_bytes = content_json.encode('utf-8')
        
        return DataEntity(
            uri=self.source_url,
            datetime=self.scraped_at,
            source=self.get_platform_source(),
            label=label,
            content=content_bytes,
            content_size_bytes=len(content_bytes)
        )
    
    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Get data quality metrics for this property"""
        
        # Count populated fields
        total_fields = len(self.__fields__)
        populated_fields = 0
        
        for field_name, field_value in self.__dict__.items():
            if field_value is not None and field_value != "" and field_value != []:
                populated_fields += 1
        
        completeness = (populated_fields / total_fields) * 100
        
        # Assess critical field coverage
        critical_fields = ["zpid", "address", "price", "bedrooms", "bathrooms", "living_area"]
        critical_populated = sum(1 for field in critical_fields if getattr(self, field, None) is not None)
        critical_completeness = (critical_populated / len(critical_fields)) * 100
        
        return {
            "total_fields": total_fields,
            "populated_fields": populated_fields,
            "completeness_percentage": round(completeness, 2),
            "critical_completeness_percentage": round(critical_completeness, 2),
            "extraction_confidence": self.extraction_confidence,
            "scraping_method": self.scraping_method,
            "has_price_history": bool(self.priceHistory),
            "has_tax_history": bool(self.taxHistory),
            "has_photos": bool(self.photos and len(self.photos) > 0),
            "has_agent_info": bool(self.contact_recipients),
            "has_climate_data": bool(self.climate),
            "data_freshness": (dt.datetime.now(dt.timezone.utc) - self.scraped_at).total_seconds() / 3600  # hours
        }
    
    def validate_against_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scraped data against known API data"""
        
        validation_results = {
            "matches": {},
            "mismatches": {},
            "missing_in_scraped": {},
            "extra_in_scraped": {},
            "overall_accuracy": 0.0
        }
        
        # Key fields to validate
        key_fields = ["price", "bedrooms", "bathrooms", "living_area", "property_type", "year_built"]
        
        matches = 0
        total_comparisons = 0
        
        for field in key_fields:
            scraped_value = getattr(self, field, None)
            api_value = api_data.get(field)
            
            if scraped_value is not None and api_value is not None:
                total_comparisons += 1
                if scraped_value == api_value:
                    matches += 1
                    validation_results["matches"][field] = {"scraped": scraped_value, "api": api_value}
                else:
                    validation_results["mismatches"][field] = {"scraped": scraped_value, "api": api_value}
            elif api_value is not None and scraped_value is None:
                validation_results["missing_in_scraped"][field] = api_value
            elif scraped_value is not None and api_value is None:
                validation_results["extra_in_scraped"][field] = scraped_value
        
        if total_comparisons > 0:
            validation_results["overall_accuracy"] = (matches / total_comparisons) * 100
        
        return validation_results
