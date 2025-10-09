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
    Get response using ScrapingBee API
    
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
        
        params = {
            'url': url,
            'premium_proxy': premium_proxy,
            'stealth_proxy': stealth_proxy,
            'render_js': True,  # Set to True if JavaScript rendering is needed
            'country_code': 'US',  # Target US properties
        }
        
        if headers:
            params['custom_headers'] = headers
            
        response = client.get(**params)
        
        return {
            'content': response.content,
            'status_code': response.status_code,
            'success': response.status_code == 200
        }
        
    except Exception as e:
        return {
            'content': None,
            'status_code': None,
            'success': False,
            'error': str(e)
        }

#TODO: Add more custom proxy implementations here
