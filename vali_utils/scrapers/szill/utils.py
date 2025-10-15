import os
from re import compile
from typing import Tuple
from dotenv import load_dotenv
from urllib.parse import quote
from scrapingbee import ScrapingBeeClient

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

#TODO: Add more custom proxy implementations here
