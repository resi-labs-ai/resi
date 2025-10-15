from typing import Any
from curl_cffi import requests
from .parse import parse_body_home
from .utils import get_scrapingbee_response

def get_from_home_id(
    property_id: int, proxy_url: str | None = None, use_scrapingbee: bool = False
) -> dict[str, Any]:
    """Scrape data for property based on property ID from zillow"""
    home_url = f"https://www.zillow.com/homedetails/any-title/{property_id}_zpid/"
    data = get_from_home_url(home_url, proxy_url, use_scrapingbee)
    return data

def get_from_home_url(home_url: str, proxy_url: str | None = None, use_scrapingbee: bool = False) -> dict[str, Any]:
    """Scrape given URL and parse home detail"""
    if use_scrapingbee:
        scrapingbee_response = get_scrapingbee_response(home_url, stealth_proxy=True, premium_proxy=False)
        if not scrapingbee_response['success']:
            error_detail = scrapingbee_response.get('error', 'Unknown error')
            # Provide more helpful error messages for common issues
            if 'headers' in str(error_detail).lower():
                raise Exception(f"ScrapingBee request failed: Response header limit exceeded (likely Zillow blocking)")
            elif 'timeout' in str(error_detail).lower():
                raise Exception(f"ScrapingBee request failed: Request timeout")
            elif 'api key' in str(error_detail).lower():
                raise Exception(f"ScrapingBee request failed: Invalid or missing API key")
            else:
                raise Exception(f"ScrapingBee request failed: {error_detail}")

        response_content = scrapingbee_response['content']
    else:
        # Use traditional proxy method
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        try:
            # Enhanced headers for better browser simulation
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'dnt': '1',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Linux"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'cache-control': 'max-age=0',
                'referer': 'https://www.google.com/'
            }

            response = requests.get(
                url=home_url,
                proxies=proxies,
                impersonate="chrome124",
                timeout=30,
                headers=headers
            )
            response.raise_for_status()
            response_content = response.content
        except Exception as e:
            error_str = str(e).lower()
            # Handle timeout errors
            if 'timeout' in error_str or 'timed out' in error_str:
                raise Exception("Request timeout - Zillow may be slow or blocking requests")
            # Handle proxy errors
            elif 'proxy' in error_str:
                raise Exception("Proxy connection failed - Check proxy configuration")
            # Handle HTTP errors by checking response status if available
            elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
                if status_code == 403:
                    raise Exception("403 Forbidden - Zillow is blocking requests (proxy may be needed)")
                elif status_code == 429:
                    raise Exception("429 Too Many Requests - Rate limited by Zillow")
                else:
                    raise Exception(f"HTTP {status_code} error: {str(e)}")
            # Re-raise if we can't categorize it
            else:
                raise
    
    data = parse_body_home(response_content)
    return data


def get_from_home_url_with_html_fallback(home_url: str, proxy_url: str | None = None, use_scrapingbee: bool = False) -> dict[str, Any]:
    """Scrape given URL with enhanced HTML element extraction as fallback
    
    This function demonstrates the enhanced parsing capabilities that can extract
    property data from both JSON and HTML elements.

    Args:
        home_url (str): URL for the property
        proxy_url (str | None, optional): proxy URL for masking the request. Defaults to None.
        use_scrapingbee (bool): Use ScrapingBee API instead of direct requests. Defaults to False.

    Returns:
        dict[str, Any]: parsed property information with enhanced extraction
    """
    if use_scrapingbee:
        # Use ScrapingBee API
        scrapingbee_response = get_scrapingbee_response(home_url, stealth_proxy=True, premium_proxy=False)
        if not scrapingbee_response['success']:
            error_detail = scrapingbee_response.get('error', 'Unknown error')
            # Provide more helpful error messages for common issues
            if 'headers' in str(error_detail).lower():
                raise Exception(f"ScrapingBee request failed: Response header limit exceeded (likely Zillow blocking)")
            elif 'timeout' in str(error_detail).lower():
                raise Exception(f"ScrapingBee request failed: Request timeout")
            elif 'api key' in str(error_detail).lower():
                raise Exception(f"ScrapingBee request failed: Invalid or missing API key")
            else:
                raise Exception(f"ScrapingBee request failed: {error_detail}")
        
        response_content = scrapingbee_response['content']
    else:
        # Use traditional proxy method
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        try:
            # Enhanced headers for better browser simulation
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Linux"',
            }

            response = requests.get(
                url=home_url,
                proxies=proxies,
                impersonate="chrome124",
                timeout=30,
                headers=headers
            )
            response.raise_for_status()
            response_content = response.content
        except Exception as e:
            error_str = str(e).lower()
            # Handle timeout errors
            if 'timeout' in error_str or 'timed out' in error_str:
                raise Exception("Request timeout - Zillow may be slow or blocking requests")
            # Handle proxy errors
            elif 'proxy' in error_str:
                raise Exception("Proxy connection failed - Check proxy configuration")
            # Handle HTTP errors by checking response status if available
            elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
                if status_code == 403:
                    raise Exception("403 Forbidden - Zillow is blocking requests (proxy may be needed)")
                elif status_code == 429:
                    raise Exception("429 Too Many Requests - Rate limited by Zillow")
                else:
                    raise Exception(f"HTTP {status_code} error: {str(e)}")
            # Re-raise if we can't categorize it
            else:
                raise
    
    # Use the enhanced parsing that includes HTML element extraction
    data = parse_body_home(response_content)
    return data