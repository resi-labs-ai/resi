"""
Field mapping between Zillow API endpoints and validation strategies.
Handles the difference between Property Extended Search (miners) and Individual Property API (validators).
"""

from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass


@dataclass
class FieldValidationConfig:
    """Configuration for how to validate a specific field"""
    field_name: str
    validation_type: str  # 'exact', 'tolerance', 'ignore', 'compatible'
    tolerance_percent: Optional[float] = None
    tolerance_absolute: Optional[int] = None
    is_critical: bool = False  # Critical fields must match exactly
    description: str = ""


class ZillowFieldMapper:
    """Maps fields between different Zillow API endpoints and defines validation strategies"""
    
    # Fields available in Property Extended Search (what miners use)
    MINER_AVAILABLE_FIELDS: Set[str] = {
        'zpid',
        'address', 
        'detailUrl',  # maps to detail_url
        'propertyType',  # maps to property_type
        'bedrooms',
        'bathrooms', 
        'livingArea',  # maps to living_area
        'lotAreaValue',  # maps to lot_area_value
        'lotAreaUnit',  # maps to lot_area_unit
        'price',
        'zestimate',
        'rentZestimate',  # maps to rent_zestimate
        'priceChange',  # maps to price_change
        'datePriceChanged',  # maps to date_price_changed
        'latitude',
        'longitude',
        'country',
        'currency',
        'listingStatus',  # maps to listing_status
        'daysOnZillow',  # maps to days_on_zillow
        'comingSoonOnMarketDate',  # maps to coming_soon_on_market_date
        'imgSrc',  # maps to img_src
        'hasImage',  # maps to has_image
        'hasVideo',  # maps to has_video
        'has3DModel',  # maps to has_3d_model
        'carouselPhotos',  # maps to carousel_photos
        'listingSubType',  # contains is_FSBA, is_openHouse, etc.
        'contingentListingType',  # maps to contingent_listing_type
        'variableData',  # maps to variable_data
    }
    
    # Field mapping from API names to model names
    API_TO_MODEL_MAPPING: Dict[str, str] = {
        'detailUrl': 'detail_url',
        'propertyType': 'property_type', 
        'livingArea': 'living_area',
        'lotAreaValue': 'lot_area_value',
        'lotAreaUnit': 'lot_area_unit',
        'rentZestimate': 'rent_zestimate',
        'priceChange': 'price_change',
        'datePriceChanged': 'date_price_changed',
        'listingStatus': 'listing_status',
        'daysOnZillow': 'days_on_zillow',
        'comingSoonOnMarketDate': 'coming_soon_on_market_date',
        'imgSrc': 'img_src',
        'hasImage': 'has_image',
        'hasVideo': 'has_video',
        'has3DModel': 'has_3d_model',
        'carouselPhotos': 'carousel_photos',
        'contingentListingType': 'contingent_listing_type',
        'variableData': 'variable_data',
    }
    
    # Validation configuration for each field available to miners
    FIELD_VALIDATION_CONFIG: Dict[str, FieldValidationConfig] = {
        # Critical fields - must match exactly
        'zpid': FieldValidationConfig(
            field_name='zpid',
            validation_type='exact',
            is_critical=True,
            description='Zillow Property ID - unique identifier'
        ),
        'address': FieldValidationConfig(
            field_name='address',
            validation_type='exact',
            is_critical=True,
            description='Property address - should not change'
        ),
        'property_type': FieldValidationConfig(
            field_name='property_type',
            validation_type='exact',
            is_critical=True,
            description='Property type (SINGLE_FAMILY, CONDO, etc.)'
        ),
        
        # Stable fields - exact match when both present
        'bedrooms': FieldValidationConfig(
            field_name='bedrooms',
            validation_type='exact',
            description='Number of bedrooms'
        ),
        'bathrooms': FieldValidationConfig(
            field_name='bathrooms',
            validation_type='exact',
            description='Number of bathrooms'
        ),
        'living_area': FieldValidationConfig(
            field_name='living_area',
            validation_type='exact',
            description='Living area in square feet'
        ),
        'lot_area_value': FieldValidationConfig(
            field_name='lot_area_value',
            validation_type='tolerance',
            tolerance_percent=0.01,  # 1% tolerance for measurement differences
            description='Lot area value'
        ),
        'lot_area_unit': FieldValidationConfig(
            field_name='lot_area_unit',
            validation_type='exact',
            description='Lot area unit (sqft, acres)'
        ),
        'latitude': FieldValidationConfig(
            field_name='latitude',
            validation_type='tolerance',
            tolerance_absolute=0.0001,  # Small tolerance for GPS precision
            description='Property latitude'
        ),
        'longitude': FieldValidationConfig(
            field_name='longitude',
            validation_type='tolerance', 
            tolerance_absolute=0.0001,  # Small tolerance for GPS precision
            description='Property longitude'
        ),
        'country': FieldValidationConfig(
            field_name='country',
            validation_type='exact',
            description='Country (usually USA)'
        ),
        'currency': FieldValidationConfig(
            field_name='currency',
            validation_type='exact',
            description='Currency (usually USD)'
        ),
        'detail_url': FieldValidationConfig(
            field_name='detail_url',
            validation_type='exact',
            description='Zillow detail page URL'
        ),
        
        # Time-sensitive fields - tolerance allowed
        'price': FieldValidationConfig(
            field_name='price',
            validation_type='tolerance',
            tolerance_percent=0.05,  # 5% tolerance
            description='Current listing price'
        ),
        'zestimate': FieldValidationConfig(
            field_name='zestimate',
            validation_type='tolerance',
            tolerance_percent=0.10,  # 10% tolerance
            description='Zillow estimated value'
        ),
        'rent_zestimate': FieldValidationConfig(
            field_name='rent_zestimate',
            validation_type='tolerance',
            tolerance_percent=0.10,  # 10% tolerance
            description='Zillow estimated rental value'
        ),
        'days_on_zillow': FieldValidationConfig(
            field_name='days_on_zillow',
            validation_type='tolerance',
            tolerance_absolute=7,  # 7 days tolerance
            description='Days property has been listed'
        ),
        'listing_status': FieldValidationConfig(
            field_name='listing_status',
            validation_type='compatible',  # Uses status transition logic
            description='Current listing status'
        ),
        
        # Volatile fields - more tolerance or ignore
        'price_change': FieldValidationConfig(
            field_name='price_change',
            validation_type='ignore',  # Price changes happen frequently
            description='Recent price change amount'
        ),
        'date_price_changed': FieldValidationConfig(
            field_name='date_price_changed',
            validation_type='ignore',  # Timestamp will be different
            description='Date of last price change'
        ),
        'coming_soon_on_market_date': FieldValidationConfig(
            field_name='coming_soon_on_market_date',
            validation_type='ignore',  # Timing-dependent
            description='Coming soon date'
        ),
        'img_src': FieldValidationConfig(
            field_name='img_src',
            validation_type='ignore',  # Images may be updated
            description='Primary image URL'
        ),
        'carousel_photos': FieldValidationConfig(
            field_name='carousel_photos',
            validation_type='ignore',  # Photo arrays change frequently
            description='Array of photo URLs'
        ),
        
        # Boolean flags - exact match
        'has_image': FieldValidationConfig(
            field_name='has_image',
            validation_type='exact',
            description='Property has images'
        ),
        'has_video': FieldValidationConfig(
            field_name='has_video',
            validation_type='exact',
            description='Property has video'
        ),
        'has_3d_model': FieldValidationConfig(
            field_name='has_3d_model',
            validation_type='exact',
            description='Property has 3D model'
        ),
        
        # Listing subtype flags
        'is_fsba': FieldValidationConfig(
            field_name='is_fsba',
            validation_type='exact',
            description='For Sale By Agent flag'
        ),
        'is_open_house': FieldValidationConfig(
            field_name='is_open_house',
            validation_type='ignore',  # Open house status changes frequently
            description='Open house scheduled flag'
        ),
        
        # Optional/variable data
        'contingent_listing_type': FieldValidationConfig(
            field_name='contingent_listing_type',
            validation_type='exact',
            description='Contingent listing type'
        ),
        'variable_data': FieldValidationConfig(
            field_name='variable_data',
            validation_type='ignore',  # Variable data by definition
            description='Additional variable data'
        ),
    }
    
    @classmethod
    def get_miner_available_fields(cls) -> Set[str]:
        """Get set of fields available to miners from Property Extended Search"""
        return cls.MINER_AVAILABLE_FIELDS.copy()
    
    @classmethod
    def get_validation_config(cls, field_name: str) -> Optional[FieldValidationConfig]:
        """Get validation configuration for a field"""
        return cls.FIELD_VALIDATION_CONFIG.get(field_name)
    
    @classmethod
    def get_critical_fields(cls) -> List[str]:
        """Get list of critical fields that must match exactly"""
        return [
            field_name for field_name, config in cls.FIELD_VALIDATION_CONFIG.items()
            if config.is_critical
        ]
    
    @classmethod
    def get_fields_by_validation_type(cls, validation_type: str) -> List[str]:
        """Get list of fields with specific validation type"""
        return [
            field_name for field_name, config in cls.FIELD_VALIDATION_CONFIG.items()
            if config.validation_type == validation_type
        ]
    
    @classmethod
    def should_validate_field(cls, field_name: str) -> bool:
        """Check if field should be validated (not ignored)"""
        config = cls.get_validation_config(field_name)
        return config is not None and config.validation_type != 'ignore'
    
    @classmethod
    def map_api_field_name(cls, api_field_name: str) -> str:
        """Map API field name to model field name"""
        return cls.API_TO_MODEL_MAPPING.get(api_field_name, api_field_name)
    
    @classmethod
    def create_miner_compatible_content(cls, full_api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a RealEstateContent-compatible dict using only fields available to miners.
        This simulates what a miner would have scraped from Property Extended Search.
        """
        compatible_data = {}
        
        # Map basic fields
        for api_field in cls.MINER_AVAILABLE_FIELDS:
            if api_field in full_api_data:
                model_field = cls.map_api_field_name(api_field)
                compatible_data[model_field] = full_api_data[api_field]
        
        # Handle special cases
        
        # Extract listing subtype flags
        if 'listingSubType' in full_api_data:
            listing_sub_type = full_api_data['listingSubType']
            compatible_data['is_fsba'] = listing_sub_type.get('is_FSBA')
            compatible_data['is_open_house'] = listing_sub_type.get('is_openHouse') 
            compatible_data['is_new_home'] = listing_sub_type.get('is_newHome')
            compatible_data['is_coming_soon'] = listing_sub_type.get('is_comingSoon')
        
        # Set defaults for fields not in search API
        compatible_data.setdefault('country', 'USA')
        compatible_data.setdefault('currency', 'USD')
        compatible_data.setdefault('data_source', 'zillow_rapidapi')
        
        return compatible_data
    
    @classmethod
    def get_validation_summary(cls) -> Dict[str, int]:
        """Get summary of validation strategy by type"""
        summary = {}
        for config in cls.FIELD_VALIDATION_CONFIG.values():
            validation_type = config.validation_type
            summary[validation_type] = summary.get(validation_type, 0) + 1
        
        return summary


# Export commonly used field sets
CRITICAL_FIELDS = ZillowFieldMapper.get_critical_fields()
EXACT_MATCH_FIELDS = ZillowFieldMapper.get_fields_by_validation_type('exact')
TOLERANCE_FIELDS = ZillowFieldMapper.get_fields_by_validation_type('tolerance')
IGNORE_FIELDS = ZillowFieldMapper.get_fields_by_validation_type('ignore')
COMPATIBLE_FIELDS = ZillowFieldMapper.get_fields_by_validation_type('compatible')
