import os
from re import compile
from typing import Tuple
from dotenv import load_dotenv
from urllib.parse import quote
from scrapingbee import ScrapingBeeClient
import requests as standard_requests
import json

regex_space = compile(r"[\s ]+")
regx_price = compile(r"\d+")


def remove_space(value: str) -> str:
    """remove unwanted spaces in given string

    Args:
        value (str): input string with unwanted spaces

    Returns:
        str: string with single spaces
    """
    return regex_space.sub(" ", value.strip())


def get_nested_value(dic, key_path, default=None):
    keys = key_path.split(".")
    current = dic
    for key in keys:
        current = current.get(key, {})
        if current == {} or current is None:
            return default
    return current

def parse_proxy(ip_or_domain: str,port: str, username: str, password: str) -> (str):
    encoded_username = quote(username)
    encoded_password = quote(password)
    proxy_url = f"http://{encoded_username}:{encoded_password}@{ip_or_domain}:{port}"
    return proxy_url

def scrapingbee_proxy():
    load_dotenv()
    client = ScrapingBeeClient(api_key=os.getenv("SCRAPINGBEE_API_KEY"))
    return client

def get_scrapingbee_response(url: str, headers: dict = None, premium_proxy: bool = False, stealth_proxy: bool = True) -> dict:
    """
    Get response using ScrapingBee API with improved error handling and retry logic
    
    Args:
        url (str): URL to scrape
        headers (dict, optional): Headers to use for the request
        premium_proxy (bool): Use premium proxy for better success rate
        stealth_proxy (bool): Use stealth proxy to avoid detection
        
    Returns:
        dict: Response data with content and status
    """
    try:
        client = scrapingbee_proxy()
        
        # ScrapingBee client expects params as a dict passed to the params argument
        scrapingbee_params = {
            'premium_proxy': premium_proxy,
            'stealth_proxy': stealth_proxy,
            'render_js': True,  # Set to True if JavaScript rendering is needed
            'country_code': 'us',  # Target US properties (lowercase)
            'wait_browser': 'load',  # Wait for page to load completely
        }
        
        # Use the correct API: client.get(url, params=dict, headers=dict)
        response = client.get(
            url=url,
            params=scrapingbee_params,
            headers=headers
        )
        
        # Check if response is successful
        if response.status_code != 200:
            error_msg = f"Status {response.status_code}"
            try:
                # Try to get error details from response
                if hasattr(response, 'text'):
                    error_text = response.text[:200]
                    error_msg += f": {error_text}"
                    
                    # Check for specific error patterns
                    if 'headers' in error_text.lower():
                        error_msg += " (Response header limit exceeded - likely Zillow blocking)"
                    elif 'timeout' in error_text.lower():
                        error_msg += " (Request timeout)"
                    elif 'api key' in error_text.lower():
                        error_msg += " (Invalid or missing API key)"
            except:
                pass
            return {
                'content': None,
                'status_code': response.status_code,
                'success': False,
                'error': error_msg
            }
        
        return {
            'content': response.content,
            'status_code': response.status_code,
            'success': True
        }
        
    except Exception as e:
        # Provide more detailed error information
        error_detail = str(e)
        
        # Check for specific error types
        if 'headers' in error_detail.lower():
            error_detail += " (Response header limit exceeded - likely Zillow blocking)"
        elif 'timeout' in error_detail.lower():
            error_detail += " (Request timeout)"
        elif 'api key' in error_detail.lower():
            error_detail += " (Invalid or missing API key)"
        elif 'connection' in error_detail.lower():
            error_detail += " (Connection error)"
        
        if hasattr(e, 'response'):
            try:
                error_detail += f" (Response: {e.response.text[:200]})"
            except:
                pass
        
        return {
            'content': None,
            'status_code': None,
            'success': False,
            'error': error_detail
        }

def get_brightdata_response(url: str) -> dict:
    """
    Get response using BrightData API with error handling
    
    Args:
        url (str): URL to scrape
        
    Returns:
        dict: Response data with content and status
    """
    try:
        
        load_dotenv()
        api_key = os.getenv("BRIGHTDATA_API_KEY")
        
        if not api_key:
            return {
                'content': None,
                'status_code': None,
                'success': False,
                'error': 'BRIGHTDATA_API_KEY not found in environment variables'
            }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        data = json.dumps({
            "input": [{"url": url}],
        })
        
        api_url = (
            "https://api.brightdata.com/datasets/v3/scrape"
            "?dataset_id=gd_lfqkr8wm13ixtbd8f5"
            "&custom_output_fields=zpid%2Caddress%2Ccity%2Cstate%2ChomeStatus%2CstreetAddress%2Czipcode%2Cbedrooms%2Cbathrooms%2Cprice%2CyearBuilt%2ClivingArea%2ClivingAreaValue%2ClivingAreaUnits%2ClivingAreaUnitsShort%2ChomeType%2ClotSize%2ClotAreaValue%2ClotAreaUnits%2Clatitude%2Clongitude%2Czestimate%2CrentZestimate%2Ccurrency%2ChideZestimate%2CdateSoldString%2CdateSold%2CtaxAssessedValue%2CtaxAssessedYear%2Ccountry%2CpropertyTaxRate%2CphotoCount%2ChdpUrl%2Cdescription%2CparcelId%2CtaxHistory%2CpriceHistory%2Cschools%2CnearbyHomes%2CnearbyCities%2CnearbyNeighborhoods%2CnearbyZipcodes%2Cphotos%2Cutilities%2Cinterior%2Cinterior_full%2Cproperty%2Cconstruction%2Cgetting_around%2Cother%2CdaysOnZillow%2CabbreviatedAddress%2CcountyFIPS%2CcountyID%2Ccounty%2CtimeZone%2Curl%2Ctimestamp%2Cinput"
            "&notify=false"
            "&include_errors=true"
        )
        
        response = standard_requests.post(
            api_url,
            headers=headers,
            data=data,
            timeout=150
        )
        
        if response.status_code != 200:
            error_msg = f"Status {response.status_code}"
            try:
                if hasattr(response, 'text'):
                    error_text = response.text[:200]
                    error_msg += f": {error_text}"
                    
                    if 'authorization' in error_text.lower() or 'api key' in error_text.lower():
                        error_msg += " (Invalid or missing API key)"
                    elif 'timeout' in error_text.lower():
                        error_msg += " (Request timeout)"
            except:
                pass
            return {
                'content': None,
                'status_code': response.status_code,
                'success': False,
                'error': error_msg
            }
        
        response_content = response.content
        
        return {
            'content': response_content,
            'status_code': response.status_code,
            'success': True
        }
        
    except Exception as e:
        error_detail = str(e)
        
        if 'authorization' in error_detail.lower() or 'api key' in error_detail.lower():
            error_detail += " (Invalid or missing API key)"
        elif 'timeout' in error_detail.lower():
            error_detail += " (Request timeout)"
        elif 'connection' in error_detail.lower():
            error_detail += " (Connection error)"
        
        if hasattr(e, 'response'):
            try:
                error_detail += f" (Response: {e.response.text[:200]})"
            except:
                pass
        
        return {
            'content': None,
            'status_code': None,
            'success': False,
            'error': error_detail
        }

#TODO: Add more custom proxy implementations here
