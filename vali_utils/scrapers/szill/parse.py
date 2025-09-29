from html import unescape
from json import loads
from typing import Any, Optional

from bs4 import BeautifulSoup  # type: ignore

from .utils import remove_space, get_nested_value


def parse_body_home(body: bytes) -> dict[str, Any]:
    """parse HTML content to retrieve JSON data

    Args:
        body (bytes): HTML content of web page

    Returns:
        dict[str, Any]: filtered property information matching schema
    """
    componentProps = parse_body(body)
    data_raw = get_nested_value(componentProps,"gdpClientCache")
    property_json = loads(data_raw)
    parsed_data={}
    for data in property_json.values():
        if "property" in str(data):
            parsed_data = data.get("property")
    
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
    if selection:
        htmlData = selection.getText()
        htmlData = remove_space(unescape(htmlData))
        data = loads(htmlData)
        return get_nested_value(data,"props.pageProps.componentProps")


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