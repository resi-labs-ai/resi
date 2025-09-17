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
    
    # Fields available in Property Extended Search (basic fields available to miners)
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
    
    # All fields available in Individual Property API (full field set)
    INDIVIDUAL_PROPERTY_FIELDS: Set[str] = MINER_AVAILABLE_FIELDS.union({
        # Enhanced address information
        'streetAddress',  # maps to street_address
        'city',
        'state', 
        'zipcode',  # maps to zip_code
        'county',
        'countyFIPS',  # maps to county_fips
        
        # Enhanced property details
        'propertySubType',  # maps to property_sub_type
        'homeType',  # maps to home_type
        'livingAreaValue',  # maps to living_area_value
        'yearBuilt',  # maps to year_built
        'lotSize',  # maps to lot_size
        'parkingSpaces',  # maps to parking_spaces
        'garageSpaces',  # maps to garage_spaces
        
        # Financial data
        'hoaFee',  # maps to hoa_fee
        'monthlyHoaFee',  # maps to monthly_hoa_fee
        'propertyTaxes',  # maps to property_taxes
        'taxAssessedValue',  # maps to tax_assessed_value
        
        # Historical data arrays
        'taxHistory',  # maps to tax_history
        'priceHistory',  # maps to price_history
        
        # Enhanced location data
        'timeZone',  # maps to time_zone
        'dateSold',  # maps to date_sold
        
        # Enhanced media
        'photoCount',  # maps to photo_count
        
        # Building information
        'buildingName',  # maps to building_name
        
        # Property features (from resoFacts)
        'resoFacts',  # maps to reso_facts
        'appliances',
        'architecturalStyle',  # maps to architectural_style
        'basement',
        'cooling',
        'exterior',
        'fireplace',
        'flooring',
        'foundation',
        'heating',
        'laundry',
        'roof',
        'sewer',
        'waterSource',  # maps to water_source
        
        # School information
        'schoolDistrict',  # maps to school_district
        'elementarySchool',  # maps to elementary_school
        'middleSchool',  # maps to middle_school
        'highSchool',  # maps to high_school
        
        # Neighborhood data
        'neighborhood',
        'walkScore',  # maps to walk_score
        'transitScore',  # maps to transit_score
        'bikeScore',  # maps to bike_score
        
        # Climate risk data
        'climateRisk',  # maps to climate_risk
        'floodRisk',  # maps to flood_risk
        'fireRisk',  # maps to fire_risk
        'windRisk',  # maps to wind_risk
        'heatRisk',  # maps to heat_risk
        
        # Contact information
        'contact_recipients',
        'listingAgent',  # maps to listing_agent
        
        # Legal information
        'buildingPermits',  # maps to building_permits
        'zoning',
        'parcelId',  # maps to parcel_id
    })
    
    # Field mapping from API names to model names
    API_TO_MODEL_MAPPING: Dict[str, str] = {
        # Basic fields (Property Extended Search)
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
        
        # Enhanced fields (Individual Property API)
        'streetAddress': 'street_address',
        'zipcode': 'zip_code',
        'countyFIPS': 'county_fips',
        'propertySubType': 'property_sub_type',
        'homeType': 'home_type',
        'livingAreaValue': 'living_area_value',
        'yearBuilt': 'year_built',
        'lotSize': 'lot_size',
        'parkingSpaces': 'parking_spaces',
        'garageSpaces': 'garage_spaces',
        'hoaFee': 'hoa_fee',
        'monthlyHoaFee': 'monthly_hoa_fee',
        'propertyTaxes': 'property_taxes',
        'taxAssessedValue': 'tax_assessed_value',
        'taxHistory': 'tax_history',
        'priceHistory': 'price_history',
        'timeZone': 'time_zone',
        'dateSold': 'date_sold',
        'photoCount': 'photo_count',
        'buildingName': 'building_name',
        'resoFacts': 'reso_facts',
        'architecturalStyle': 'architectural_style',
        'waterSource': 'water_source',
        'schoolDistrict': 'school_district',
        'elementarySchool': 'elementary_school',
        'middleSchool': 'middle_school',
        'highSchool': 'high_school',
        'walkScore': 'walk_score',
        'transitScore': 'transit_score',
        'bikeScore': 'bike_score',
        'climateRisk': 'climate_risk',
        'floodRisk': 'flood_risk',
        'fireRisk': 'fire_risk',
        'windRisk': 'wind_risk',
        'heatRisk': 'heat_risk',
        'listingAgent': 'listing_agent',
        'buildingPermits': 'building_permits',
        'parcelId': 'parcel_id',
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
        
        # Enhanced fields from Individual Property API
        # Enhanced address fields
        'street_address': FieldValidationConfig(
            field_name='street_address',
            validation_type='exact',
            description='Street address component'
        ),
        'city': FieldValidationConfig(
            field_name='city',
            validation_type='exact',
            description='City name'
        ),
        'state': FieldValidationConfig(
            field_name='state',
            validation_type='exact',
            description='State abbreviation'
        ),
        'zip_code': FieldValidationConfig(
            field_name='zip_code',
            validation_type='exact',
            description='ZIP code'
        ),
        'county': FieldValidationConfig(
            field_name='county',
            validation_type='exact',
            description='County name'
        ),
        
        # Enhanced property details
        'year_built': FieldValidationConfig(
            field_name='year_built',
            validation_type='exact',
            description='Year property was built'
        ),
        'property_sub_type': FieldValidationConfig(
            field_name='property_sub_type',
            validation_type='exact',
            description='Property sub-type classification'
        ),
        'home_type': FieldValidationConfig(
            field_name='home_type',
            validation_type='exact',
            description='Home type classification'
        ),
        'living_area_value': FieldValidationConfig(
            field_name='living_area_value',
            validation_type='exact',
            description='Living area value (alternative field)'
        ),
        'lot_size': FieldValidationConfig(
            field_name='lot_size',
            validation_type='tolerance',
            tolerance_percent=0.01,  # 1% tolerance for measurement differences
            description='Lot size'
        ),
        'parking_spaces': FieldValidationConfig(
            field_name='parking_spaces',
            validation_type='exact',
            description='Number of parking spaces'
        ),
        'garage_spaces': FieldValidationConfig(
            field_name='garage_spaces',
            validation_type='exact',
            description='Number of garage spaces'
        ),
        
        # Financial data
        'hoa_fee': FieldValidationConfig(
            field_name='hoa_fee',
            validation_type='tolerance',
            tolerance_percent=0.05,  # 5% tolerance for fee changes
            description='HOA fee amount'
        ),
        'monthly_hoa_fee': FieldValidationConfig(
            field_name='monthly_hoa_fee',
            validation_type='tolerance',
            tolerance_percent=0.05,  # 5% tolerance for fee changes
            description='Monthly HOA fee'
        ),
        'property_taxes': FieldValidationConfig(
            field_name='property_taxes',
            validation_type='tolerance',
            tolerance_percent=0.10,  # 10% tolerance for tax changes
            description='Property taxes'
        ),
        'tax_assessed_value': FieldValidationConfig(
            field_name='tax_assessed_value',
            validation_type='tolerance',
            tolerance_percent=0.05,  # 5% tolerance for assessment changes
            description='Tax assessed value'
        ),
        
        # Historical data arrays - validate presence but not exact content
        'tax_history': FieldValidationConfig(
            field_name='tax_history',
            validation_type='compatible',  # Validate structure but allow differences
            description='Tax history array'
        ),
        'price_history': FieldValidationConfig(
            field_name='price_history',
            validation_type='compatible',  # Validate structure but allow differences
            description='Price history array'
        ),
        
        # Enhanced location data
        'time_zone': FieldValidationConfig(
            field_name='time_zone',
            validation_type='exact',
            description='Property time zone'
        ),
        'date_sold': FieldValidationConfig(
            field_name='date_sold',
            validation_type='exact',
            description='Date property was sold'
        ),
        
        # Enhanced media
        'photo_count': FieldValidationConfig(
            field_name='photo_count',
            validation_type='tolerance',
            tolerance_absolute=5,  # Allow up to 5 photo difference
            description='Number of photos'
        ),
        
        # Enhanced listing flags
        'is_foreclosure': FieldValidationConfig(
            field_name='is_foreclosure',
            validation_type='exact',
            description='Foreclosure status flag'
        ),
        'is_bank_owned': FieldValidationConfig(
            field_name='is_bank_owned',
            validation_type='exact',
            description='Bank owned status flag'
        ),
        
        # Building information
        'building_name': FieldValidationConfig(
            field_name='building_name',
            validation_type='exact',
            description='Building or complex name'
        ),
        
        # Property features - validate presence but allow some variation
        'reso_facts': FieldValidationConfig(
            field_name='reso_facts',
            validation_type='compatible',  # Complex nested object
            description='RESO property facts'
        ),
        'appliances': FieldValidationConfig(
            field_name='appliances',
            validation_type='compatible',  # Array of appliances
            description='Property appliances list'
        ),
        'architectural_style': FieldValidationConfig(
            field_name='architectural_style',
            validation_type='exact',
            description='Architectural style'
        ),
        'basement': FieldValidationConfig(
            field_name='basement',
            validation_type='exact',
            description='Basement information'
        ),
        'cooling': FieldValidationConfig(
            field_name='cooling',
            validation_type='exact',
            description='Cooling system type'
        ),
        'heating': FieldValidationConfig(
            field_name='heating',
            validation_type='exact',
            description='Heating system type'
        ),
        'exterior': FieldValidationConfig(
            field_name='exterior',
            validation_type='exact',
            description='Exterior materials'
        ),
        'flooring': FieldValidationConfig(
            field_name='flooring',
            validation_type='exact',
            description='Flooring types'
        ),
        'roof': FieldValidationConfig(
            field_name='roof',
            validation_type='exact',
            description='Roof type/material'
        ),
        
        # School information - can change periodically
        'school_district': FieldValidationConfig(
            field_name='school_district',
            validation_type='compatible',  # Complex object with ratings
            description='School district information'
        ),
        'elementary_school': FieldValidationConfig(
            field_name='elementary_school',
            validation_type='exact',
            description='Elementary school name'
        ),
        'middle_school': FieldValidationConfig(
            field_name='middle_school',
            validation_type='exact',
            description='Middle school name'
        ),
        'high_school': FieldValidationConfig(
            field_name='high_school',
            validation_type='exact',
            description='High school name'
        ),
        
        # Neighborhood and walkability scores - can change
        'neighborhood': FieldValidationConfig(
            field_name='neighborhood',
            validation_type='compatible',  # Complex neighborhood data
            description='Neighborhood information'
        ),
        'walk_score': FieldValidationConfig(
            field_name='walk_score',
            validation_type='tolerance',
            tolerance_absolute=5,  # Walk scores can vary slightly
            description='Walk score rating'
        ),
        'transit_score': FieldValidationConfig(
            field_name='transit_score',
            validation_type='tolerance',
            tolerance_absolute=5,  # Transit scores can vary slightly
            description='Transit score rating'
        ),
        'bike_score': FieldValidationConfig(
            field_name='bike_score',
            validation_type='tolerance',
            tolerance_absolute=5,  # Bike scores can vary slightly
            description='Bike score rating'
        ),
        
        # Climate risk data - relatively stable but can be updated
        'climate_risk': FieldValidationConfig(
            field_name='climate_risk',
            validation_type='compatible',  # Complex risk assessment data
            description='Climate risk assessment'
        ),
        'flood_risk': FieldValidationConfig(
            field_name='flood_risk',
            validation_type='exact',
            description='Flood risk level'
        ),
        'fire_risk': FieldValidationConfig(
            field_name='fire_risk',
            validation_type='exact',
            description='Fire risk level'
        ),
        'wind_risk': FieldValidationConfig(
            field_name='wind_risk',
            validation_type='exact',
            description='Wind risk level'
        ),
        'heat_risk': FieldValidationConfig(
            field_name='heat_risk',
            validation_type='exact',
            description='Heat risk level'
        ),
        
        # Contact information - can change frequently
        'contact_recipients': FieldValidationConfig(
            field_name='contact_recipients',
            validation_type='ignore',  # Agent contacts change frequently
            description='Contact recipients array'
        ),
        'listing_agent': FieldValidationConfig(
            field_name='listing_agent',
            validation_type='ignore',  # Agent information changes
            description='Listing agent information'
        ),
        
        # Legal information - stable
        'building_permits': FieldValidationConfig(
            field_name='building_permits',
            validation_type='compatible',  # Array of permits
            description='Building permits array'
        ),
        'zoning': FieldValidationConfig(
            field_name='zoning',
            validation_type='exact',
            description='Zoning classification'
        ),
        'parcel_id': FieldValidationConfig(
            field_name='parcel_id',
            validation_type='exact',
            description='Property parcel ID'
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
    def create_full_property_content(cls, full_api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a RealEstateContent-compatible dict using ALL fields from Individual Property API.
        This is what miners will now collect when using the upgraded two-phase scraping.
        """
        content_data = {}
        
        # Map all available fields from Individual Property API
        for api_field in cls.INDIVIDUAL_PROPERTY_FIELDS:
            if api_field in full_api_data:
                # Skip complex fields that need special handling
                if api_field == 'address' and isinstance(full_api_data[api_field], dict):
                    continue  # Will be handled specially below
                if api_field == 'taxHistory' and isinstance(full_api_data[api_field], dict):
                    continue  # Will be handled specially below
                if api_field == 'listingSubType':
                    continue  # Will be handled specially below
                    
                model_field = cls.map_api_field_name(api_field)
                
                # Special handling for zpid - ensure it's a string
                if api_field == 'zpid':
                    content_data[model_field] = str(full_api_data[api_field])
                else:
                    content_data[model_field] = full_api_data[api_field]
        
        # Handle special cases for nested data
        
        # Handle complex address field from Individual Property API
        if 'address' in full_api_data and isinstance(full_api_data['address'], dict):
            address_obj = full_api_data['address']
            # Create a formatted address string from the complex object
            street_address = address_obj.get('streetAddress', '')
            city = address_obj.get('city', '')
            state = address_obj.get('state', '')
            zipcode = address_obj.get('zipcode', '')
            
            # Format as standard address string
            address_parts = [part for part in [street_address, city, state, zipcode] if part]
            content_data['address'] = ', '.join(address_parts)
            
            # Also populate the individual address components
            content_data['street_address'] = street_address
            content_data['city'] = city
            content_data['state'] = state
            content_data['zip_code'] = zipcode
        
        # Handle tax history - ensure it's a list or None
        if 'taxHistory' in full_api_data:
            tax_history = full_api_data['taxHistory']
            if isinstance(tax_history, dict) and not tax_history:
                # Empty dict should be None
                content_data['tax_history'] = None
            elif isinstance(tax_history, list):
                content_data['tax_history'] = tax_history
            else:
                content_data['tax_history'] = None
        
        # Extract listing subtype flags
        if 'listingSubType' in full_api_data:
            listing_sub_type = full_api_data['listingSubType']
            content_data['is_fsba'] = listing_sub_type.get('is_FSBA')
            content_data['is_open_house'] = listing_sub_type.get('is_openHouse') 
            content_data['is_new_home'] = listing_sub_type.get('is_newHome')
            content_data['is_coming_soon'] = listing_sub_type.get('is_comingSoon')
            content_data['is_foreclosure'] = listing_sub_type.get('is_foreclosure')
            content_data['is_bank_owned'] = listing_sub_type.get('is_bankOwned')
        
        # Set defaults for required fields
        content_data.setdefault('country', 'USA')
        content_data.setdefault('currency', 'USD')
        content_data.setdefault('data_source', 'zillow_rapidapi')
        
        # Handle missing required fields that may not be in Individual Property API
        if 'detail_url' not in content_data or not content_data['detail_url']:
            # Construct detail URL from zpid if missing
            zpid = content_data.get('zpid', '')
            if zpid:
                content_data['detail_url'] = f"/homedetails/property/{zpid}_zpid/"
            else:
                content_data['detail_url'] = ""
        
        if 'property_type' not in content_data or not content_data['property_type']:
            # Use homeType or propertySubType as fallback
            content_data['property_type'] = (full_api_data.get('homeType') or 
                                           full_api_data.get('propertySubType') or 
                                           'UNKNOWN')
        
        if 'listing_status' not in content_data or not content_data['listing_status']:
            # Default listing status
            content_data['listing_status'] = 'UNKNOWN'
        
        return content_data

    @classmethod
    def create_miner_compatible_content(cls, full_api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a RealEstateContent-compatible dict using only fields available to miners.
        This simulates what a miner would have scraped from Property Extended Search.
        
        NOTE: This method will be DEPRECATED after the upgrade is complete and miners
        start using the full Individual Property API data via create_full_property_content().
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
