from html import unescape
from json import loads
from typing import Any, Optional
import re
from datetime import datetime

from bs4 import BeautifulSoup  # type: ignore

from .utils import remove_space, get_nested_value


def parse_body_home(body: bytes) -> dict[str, Any]:
    """Parse HTML content to retrieve JSON data for a property

    Args:
        body (bytes): HTML content of web page

    Returns:
        dict[str, Any]: filtered property information matching schema or error dict
    """
    componentProps = parse_body(body)
    if not componentProps:
        return {"error": "Could not parse component props"}

    data_raw = get_nested_value(componentProps, "gdpClientCache")
    if not data_raw:
        return {"error": "Could not find gdpClientCache"}

    property_json = loads(data_raw)
    parsed_data = {}
    for data in property_json.values():
        if "property" in str(data):
            parsed_data = data.get("property", {})
            break

    if not parsed_data:
        return {"error": "Could not extract property data"}

    # Filter the data to match schema requirements
    return filter_property_data(parsed_data)

def parse_body(body: bytes) -> dict[str, Any]:
    """parse HTML content to retrieve JSON data

    Args:
        body (bytes): HTML content of web page

    Returns:
        dict[str, Any]: parsed property information
    """
    soup = BeautifulSoup(body, "html.parser")
    selection = soup.select_one("#__NEXT_DATA__")
    if not selection:
        return {}

    htmlData = selection.getText()
    htmlData = remove_space(unescape(htmlData))
    data = loads(htmlData)
    return get_nested_value(data, "props.pageProps.componentProps") or {}


def filter_property_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Filter the raw scraped data to match the schema requirements
    
    Args:
        raw_data: Raw property data from Zillow
        
    Returns:
        dict: Filtered property data matching the schema
    """
    filtered = {}
    
    # Metadata
    from datetime import datetime
    filtered["metadata"] = {
        "version": "1.0",
        "description": "Property data collection schema for real estate data",
        "collection_date": datetime.now().strftime("%Y-%m-%d"),
        "miner_hot_key": None
    }
    
    # IDs
    filtered["ids"] = {
        "property": {
            "parcel_number": None,
            "fips_code": None
        },
        "zillow": {
            "zpid": raw_data.get("zpid")
        },
        "mls": {
            "mls_number": raw_data.get("mlsid")
        }
    }
    
    # Property location
    address_data = raw_data.get("address", {})
    filtered["property"] = {
        "location": {
            "addresses": address_data.get("streetAddress"),
            "street_number": None,
            "street_name": None,
            "unit_number": None,
            "city": raw_data.get("city"),
            "state": raw_data.get("state"),
            "zip_code": raw_data.get("zipcode"),
            "zip_code_plus_4": None,
            "county": None,
            "latitude": raw_data.get("latitude"),
            "longitude": raw_data.get("longitude")
        },
        "features": {
            "interior_features": None,
            "bedrooms": raw_data.get("bedrooms"),
            "bathrooms": raw_data.get("bathrooms"),
            "full_bathrooms": get_nested_value(raw_data, "resoFacts.bathroomsFull"),
            "half_bathrooms": get_nested_value(raw_data, "resoFacts.bathroomsHalf"),
            "exterior_features": None,
            "garage_spaces": get_nested_value(raw_data, "resoFacts.garageParkingCapacity"),
            "total_parking_spaces": get_nested_value(raw_data, "resoFacts.parkingCapacity"),
            "pool": None,
            "fireplace": None,
            "stories": None,
            "hvac_type": None,
            "flooring_type": None
        },
        "characteristics": {
            "property_type": raw_data.get("homeType"),
            "property_subtype": get_nested_value(raw_data, "resoFacts.propertySubType"),
            "construction_material": None,
            "year_built": get_nested_value(raw_data, "resoFacts.yearBuilt"),
            "year_renovated": None
        },
        "size": {
            "house_size_sqft": raw_data.get("livingArea"),
            "lot_size_acres": None,
            "lot_size_sqft": raw_data.get("lotSize")
        },
        "utilities": {
            "sewer_type": None,
            "water_source": None
        },
        "school": {
            "elementary_school": None,
            "middle_school": None,
            "high_school": None,
            "school_district": None
        },
        "hoa": {
            "hoa_fee_monthly": [{"date": datetime.now().strftime("%Y-%m-%d"), "value": raw_data.get("monthlyHoaFee")}] if raw_data.get("monthlyHoaFee") else None,
            "hoa_fee_annual": None
        }
    }
    
    # Valuation
    filtered["valuation"] = {
        "assessment": {
            "assessor_tax_values": None,
            "assessor_market_values": None
        },
        "market": {
            "zestimate_current": raw_data.get("zestimate"),
            "zestimate_history": None,
            "price_per_sqft": [{"date": datetime.now().strftime("%Y-%m-%d"), "value": get_nested_value(raw_data, "resoFacts.pricePerSquareFoot")}] if get_nested_value(raw_data, "resoFacts.pricePerSquareFoot") else None,
            "comparable_sales": None
        },
        "rental": {
            "rent_estimate": [{"date": datetime.now().strftime("%Y-%m-%d"), "value": raw_data.get("rentZestimate")}] if raw_data.get("rentZestimate") else None
        }
    }
    
    # Market data
    filtered["market_data"] = {
        "trends": {
            "days_on_market": [{"date": datetime.now().strftime("%Y-%m-%d"), "value": raw_data.get("daysOnZillow")}] if raw_data.get("daysOnZillow") else None
        }
    }
    
    # Home sales - this would need more complex parsing of price history if available
    filtered["home_sales"] = {
        "sales_history": None  # Would need to extract from price history data if available
    }
    
    # Market context
    filtered["market_context"] = {
        "sale_date": None,  # Would need to be extracted from sales history
        "final_sale_price": raw_data.get("price"),
        "listing_timeline": None,
        "days_on_market": raw_data.get("daysOnZillow"),
        "price_changes": None
    }
    
    # Neighborhood context  
    filtered["neighborhood_context"] = {
        "recent_comparable_sales": None,
        "market_trends": {
            "median_sale_price_trend": None
        }
    }
    
    # Tax assessment
    filtered["tax_assessment"] = {
        "current_assessment": None,
        "assessment_history": None,
        "annual_taxes": None
    }
    
    return filtered


def parse_html_response(html_content: str, zipcode: str) -> list[dict[str, Any]]:
    """
    Parse HTML response to extract property listings
    
    Args:
        html_content: HTML content from response
        zipcode: Target zipcode
        
    Returns:
        List of formatted property dictionaries
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        properties = []
        
        # Try multiple selectors as Zillow may use different ones
        selectors_to_try = [
            'article[data-test="property-card"]',
            'div[data-test="property-card"]',
            '.list-card',
            'article.list-card',
            '.property-card'
        ]
        
        listings = []
        for selector in selectors_to_try:
            listings = soup.select(selector)
            if listings:
                break
        
        if not listings:
            return []
        
        for listing in listings:
            property_data = extract_property_from_html(listing, zipcode)
            if property_data:
                properties.append(property_data)
        
        return properties
        
    except Exception as e:
        return []


def extract_property_from_html(listing_element, zipcode: str) -> Optional[dict[str, Any]]:
    """
    Extract property data from HTML listing element
    
    Args:
        listing_element: BeautifulSoup element containing listing
        zipcode: Target zipcode
        
    Returns:
        Formatted property dict or None
    """
    try:
        # Extract basic information with multiple selector attempts
        address_elem = (listing_element.select_one('address') or 
                      listing_element.select_one('[data-test="property-card-addr"]') or
                      listing_element.select_one('.list-card-addr'))
        
        price_elem = (listing_element.select_one('[data-test="property-card-price"]') or
                    listing_element.select_one('.list-card-price') or
                    listing_element.select_one('.price'))
        
        details_elem = (listing_element.select_one('[data-test="property-card-details"]') or
                      listing_element.select_one('.list-card-details'))
        
        link_elem = (listing_element.select_one('a[data-test="property-card-link"]') or
                   listing_element.select_one('a.list-card-link') or
                   listing_element.select_one('a'))
        
        # Extract zpid from URL if available
        zpid = None
        property_url = None
        if link_elem and link_elem.get('href'):
            property_url = link_elem.get('href')
            if not property_url.startswith('http'):
                property_url = f"https://www.zillow.com{property_url}"
            
            # Extract zpid from URL using regex
            zpid_match = re.search(r'(\d+)_zpid', property_url)
            if zpid_match:
                zpid = zpid_match.group(1)
        
        # Extract address
        address = address_elem.get_text(strip=True) if address_elem else "N/A"
        
        # Extract and clean price
        price_text = price_elem.get_text(strip=True) if price_elem else "0"
        price = parse_price(price_text)
        
        # Extract bed/bath info from details
        beds, baths, sqft = parse_details(details_elem.get_text(strip=True) if details_elem else "")
        
        # Skip if no zpid found (can't validate without it)
        if not zpid:
            return None
        
        # Extract property type from listing attributes or data attributes
        property_type = None
        type_elem = (listing_element.select_one('[data-test="property-card-type"]') or
                    listing_element.get('data-property-type'))
        if type_elem:
            if isinstance(type_elem, str):
                property_type = type_elem.upper()
            else:
                property_type = type_elem.get_text(strip=True).upper() if hasattr(type_elem, 'get_text') else None
        
        # If no type found, try to infer from listing classes or text
        if not property_type:
            listing_text = listing_element.get_text().upper()
            if 'CONDO' in listing_text or 'CONDOMINIUM' in listing_text:
                property_type = 'CONDO'
            elif 'TOWNHOUSE' in listing_text or 'TOWNHOME' in listing_text:
                property_type = 'TOWNHOUSE'
            elif 'MULTI' in listing_text or 'MULTI-FAMILY' in listing_text:
                property_type = 'MULTI_FAMILY'
            elif 'APARTMENT' in listing_text:
                property_type = 'APARTMENT'
            elif 'LOT' in listing_text or 'LAND' in listing_text:
                property_type = 'LOT'
            else:
                # Default to SINGLE_FAMILY as most common type
                property_type = 'SINGLE_FAMILY'
        
        # Build formatted listing
        formatted_listing = {
            'zpid': zpid,
            'mls_id': None,
            'address': address,
            'price': price,
            'bedrooms': beds,
            'bathrooms': baths,
            'sqft': sqft,
            'listing_date': datetime.now().isoformat(),
            'property_type': property_type,
            'listing_status': 'SOLD',
            'days_on_market': None,
            'source_url': property_url or f"https://www.zillow.com/homedetails/{zpid}_zpid/",
            'scraped_timestamp': datetime.now().isoformat(),
            'zipcode': zipcode,
            'latitude': None,
            'longitude': None,
            'lot_size': None,
            'year_built': None,
            'home_status': 'SOLD',
            'price_per_sqft': None,
            'zestimate': None,
            'rent_zestimate': None,
            'search_strategy': 'html_scraping'
        }

        return formatted_listing
        
    except Exception as e:
        return None


def parse_price(price_text: str) -> int:
    """
    Parse price from text string
    
    Args:
        price_text: Price text (e.g., "$1,200,000")
        
    Returns:
        Price as integer
    """
    try:
        # Remove $ and commas, extract numbers
        price_numbers = re.findall(r'[\d,]+', price_text.replace('$', '').replace(',', ''))
        if price_numbers:
            return int(price_numbers[0])
        return 0
    except (ValueError, IndexError):
        return 0


def parse_details(details_text: str) -> tuple[Optional[int], Optional[float], Optional[int]]:
    """
    Parse bed/bath/sqft from details text
    
    Args:
        details_text: Details text (e.g., "3 bed, 2 bath, 1,200 sqft")
        
    Returns:
        Tuple of (beds, baths, sqft)
    """
    beds = None
    baths = None
    sqft = None
    
    try:
        # Look for patterns like "3 bed", "2 bath", "1,200 sqft"
        bed_match = re.search(r'(\d+)\s*(?:bed|bd)', details_text, re.IGNORECASE)
        bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba)', details_text, re.IGNORECASE)
        sqft_match = re.search(r'([\d,]+)\s*(?:sqft|sq ft)', details_text, re.IGNORECASE)
        
        if bed_match:
            beds = int(bed_match.group(1))
        if bath_match:
            baths = float(bath_match.group(1))
        if sqft_match:
            sqft = int(sqft_match.group(1).replace(',', ''))
            
    except (ValueError, AttributeError):
        pass
    
    return beds, baths, sqft