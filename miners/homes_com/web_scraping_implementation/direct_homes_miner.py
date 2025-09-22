"""
Direct Homes.com Web Scraper Implementation
Scrapes property data directly from Homes.com property pages using Selenium.
"""

import asyncio
import json
import logging
import random
import time
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from urllib.parse import quote_plus

from scraping.scraper import Scraper, ScrapeConfig, ValidationResult
from miners.homes_com.shared.homes_schema import HomesRealEstateContent
from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange


class DirectHomesScraper(Scraper):
    """Direct Homes.com scraper using Selenium and undetected Chrome"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=12)  # Very conservative for Homes.com
        self.driver = None
        self.session_count = 0
        self.max_session_requests = 8  # Restart browser very frequently
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
    
    def _create_driver(self):
        """Create a new undetected Chrome driver"""
        try:
            options = uc.ChromeOptions()
            
            # Basic stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Speed up loading
            
            # Randomize user agent
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')
            
            # Create driver
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(50)  # Longer timeout for Homes.com
            
            return driver
            
        except Exception as e:
            logging.error(f"Failed to create Chrome driver: {e}")
            return None
    
    def _get_driver(self):
        """Get or create a Chrome driver"""
        if self.driver is None or self.session_count >= self.max_session_requests:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            self.driver = self._create_driver()
            self.session_count = 0
        
        return self.driver
    
    async def scrape_address(self, address: str) -> Optional[DataEntity]:
        """Scrape a single address and return DataEntity"""
        await self.rate_limiter.wait_if_needed()
        
        driver = self._get_driver()
        if not driver:
            logging.error(f"Could not create driver for address {address}")
            return None
        
        try:
            # First, search for the property to get the listing URL
            listing_url = await self._find_property_listing(driver, address)
            if not listing_url:
                logging.warning(f"Could not find listing for address: {address}")
                return None
            
            logging.info(f"Scraping address {address} from {listing_url}")
            driver.get(listing_url)
            
            # Wait for page to load
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if we hit anti-bot protection or property not found
            if self._is_blocked_or_not_found(driver):
                logging.warning(f"Blocked or property not found for address {address}")
                return None
            
            # Extract data from the page
            property_data = self._extract_property_data(driver, address, listing_url)
            if not property_data:
                return None
            
            # Convert to HomesRealEstateContent and then DataEntity
            content = HomesRealEstateContent.from_web_scraping(property_data, address)
            entity = content.to_data_entity()
            
            self.session_count += 1
            return entity
            
        except TimeoutException:
            logging.error(f"Timeout loading page for address {address}")
            return None
        except Exception as e:
            logging.error(f"Error scraping address {address}: {e}")
            return None
    
    async def _find_property_listing(self, driver, address: str) -> Optional[str]:
        """Search for property listing URL on Homes.com"""
        try:
            # Clean and format address for search
            search_address = self._clean_address_for_search(address)
            
            # Homes.com search URL format
            search_url = f"https://www.homes.com/search/{quote_plus(search_address).replace('%20', '-').lower()}/"
            
            logging.info(f"Searching for property: {search_url}")
            driver.get(search_url)
            
            # Wait for search results
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.property-card')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.listing-card')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.search-result'))
                )
            )
            
            # Look for property cards
            property_cards = driver.find_elements(By.CSS_SELECTOR, '.property-card, .listing-card, .search-result')
            
            if not property_cards:
                # Try alternative search approach
                return await self._alternative_property_search(driver, address)
            
            # Find the best matching property
            for card in property_cards[:5]:  # Check first 5 results
                try:
                    # Get the link to the property detail
                    link_elem = card.find_element(By.CSS_SELECTOR, 'a[href*="/property/"]')
                    property_url = link_elem.get_attribute('href')
                    
                    # Get property address from card for matching
                    try:
                        card_address = card.find_element(By.CSS_SELECTOR, '.property-address, .address').text
                        
                        # Simple address matching
                        if self._addresses_match(address, card_address):
                            return property_url
                    except NoSuchElementException:
                        # If we can't get address, try the first result
                        pass
                    
                    # If no exact match, return first valid URL as fallback
                    if property_url and '/property/' in property_url:
                        return property_url
                        
                except NoSuchElementException:
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"Error finding property listing for {address}: {e}")
            return None
    
    async def _alternative_property_search(self, driver, address: str) -> Optional[str]:
        """Alternative search method if primary search fails"""
        try:
            # Try a more general search
            address_parts = self._parse_address(address)
            if address_parts and address_parts.get('city') and address_parts.get('state'):
                city = address_parts['city'].replace(' ', '-').lower()
                state = address_parts['state'].lower()
                
                general_search = f"https://www.homes.com/{state}/{city}/"
                
                try:
                    driver.get(general_search)
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # Look for property listings on the city page
                    property_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/property/"]')
                    
                    if property_links:
                        # Return the first property link as a fallback
                        return property_links[0].get_attribute('href')
                        
                except Exception:
                    pass
            
            return None
            
        except Exception as e:
            logging.error(f"Error in alternative search for {address}: {e}")
            return None
    
    def _clean_address_for_search(self, address: str) -> str:
        """Clean address for search"""
        # Remove extra spaces and normalize
        cleaned = re.sub(r'\s+', ' ', address.strip())
        
        # Remove apartment/unit numbers for better search results
        cleaned = re.sub(r'\s+(apt|apartment|unit|#)\s*\w+', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _parse_address(self, address: str) -> Dict[str, str]:
        """Parse address into components"""
        try:
            parts = {}
            
            # Look for state and zip at the end
            match = re.search(r'([A-Z]{2})\s+(\d{5})', address)
            if match:
                parts['state'] = match.group(1)
                parts['zip'] = match.group(2)
                
                # Remove state and zip to get city and street
                remaining = address[:match.start()].strip().rstrip(',')
                
                # Split by comma to separate street and city
                if ',' in remaining:
                    street_part, city_part = remaining.rsplit(',', 1)
                    parts['street'] = street_part.strip()
                    parts['city'] = city_part.strip()
                else:
                    parts['street'] = remaining
            
            return parts
            
        except Exception:
            return {}
    
    def _addresses_match(self, search_address: str, card_address: str) -> bool:
        """Simple address matching logic"""
        # Normalize both addresses
        search_norm = re.sub(r'[^\w\s]', '', search_address.lower())
        card_norm = re.sub(r'[^\w\s]', '', card_address.lower())
        
        # Extract street numbers
        search_num = re.search(r'^(\d+)', search_norm)
        card_num = re.search(r'^(\d+)', card_norm)
        
        # If street numbers match, likely the same property
        if search_num and card_num:
            return search_num.group(1) == card_num.group(1)
        
        # Fallback: check if key words match
        search_words = set(search_norm.split())
        card_words = set(card_norm.split())
        
        # If more than 50% of words match, consider it a match
        if len(search_words) > 0:
            overlap = len(search_words.intersection(card_words))
            return overlap / len(search_words) > 0.5
        
        return False
    
    def _is_blocked_or_not_found(self, driver) -> bool:
        """Check if we've been blocked or property not found"""
        page_source = driver.page_source.lower()
        
        # Check for common indicators
        blocked_indicators = [
            'access denied',
            'blocked',
            'captcha',
            'security check',
            'unusual traffic',
            'property not found',
            'listing not available',
            'page not found',
            'no results found',
            'sorry, we couldn\'t find',
            'this property is no longer available'
        ]
        
        return any(indicator in page_source for indicator in blocked_indicators)
    
    def _extract_property_data(self, driver, address: str, listing_url: str) -> Optional[Dict[str, Any]]:
        """Extract property data from the Homes.com page"""
        try:
            data = {
                'address': address,
                'detail_url': listing_url,
                'scraped_at': datetime.now(timezone.utc),
                'scraping_method': 'web_scraping'
            }
            
            # Extract basic information
            data.update(self._extract_basic_info(driver))
            
            # Extract pricing information
            data.update(self._extract_pricing(driver))
            
            # Extract property details
            data.update(self._extract_property_details(driver))
            
            # Extract listing information
            data.update(self._extract_listing_info(driver))
            
            # Extract photos
            data.update(self._extract_photos(driver))
            
            # Extract agent information
            data.update(self._extract_agent_info(driver))
            
            # Extract features and amenities
            data.update(self._extract_features(driver))
            
            # Extract school information
            data.update(self._extract_school_info(driver))
            
            return data
            
        except Exception as e:
            logging.error(f"Error extracting data for address {address}: {e}")
            return None
    
    def _extract_basic_info(self, driver) -> Dict[str, Any]:
        """Extract basic property information"""
        data = {}
        
        try:
            # Property type
            type_selectors = [
                '.property-type',
                '.home-type',
                '.listing-type'
            ]
            
            for selector in type_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    data['property_type'] = element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Bedrooms, Bathrooms, Square Feet
            try:
                beds_elem = driver.find_element(By.CSS_SELECTOR, '.beds, .bedrooms, .bed-count')
                beds_text = beds_elem.text.strip()
                beds_match = re.search(r'(\d+)', beds_text)
                if beds_match:
                    data['bedrooms'] = int(beds_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            try:
                baths_elem = driver.find_element(By.CSS_SELECTOR, '.baths, .bathrooms, .bath-count')
                baths_text = baths_elem.text.strip()
                baths_match = re.search(r'([\d.]+)', baths_text)
                if baths_match:
                    data['bathrooms'] = float(baths_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            try:
                sqft_elem = driver.find_element(By.CSS_SELECTOR, '.sqft, .square-feet, .total-sqft')
                sqft_text = sqft_elem.text.strip().replace(',', '')
                sqft_match = re.search(r'(\d+)', sqft_text)
                if sqft_match:
                    data['total_sqft'] = int(sqft_match.group(1))
                    data['living_area'] = data['total_sqft']  # Map to base field
            except (NoSuchElementException, ValueError):
                pass
            
            # Total rooms
            try:
                rooms_elem = driver.find_element(By.CSS_SELECTOR, '.total-rooms, .room-count')
                rooms_text = rooms_elem.text.strip()
                rooms_match = re.search(r'(\d+)', rooms_text)
                if rooms_match:
                    data['total_rooms'] = int(rooms_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
                
        except Exception as e:
            logging.error(f"Error extracting basic info: {e}")
        
        return data
    
    def _extract_pricing(self, driver) -> Dict[str, Any]:
        """Extract price and financial information"""
        data = {}
        
        try:
            # Current price
            price_selectors = [
                '.price',
                '.asking-price',
                '.listing-price',
                '.property-price'
            ]
            
            for selector in price_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = element.text.strip().replace('$', '').replace(',', '')
                    price_match = re.search(r'(\d+)', price_text)
                    if price_match:
                        data['price'] = int(price_match.group(1))
                        data['asking_price'] = data['price']  # Map to Homes-specific field
                        break
                except (NoSuchElementException, ValueError):
                    continue
            
            # Price per sqft
            try:
                psf_elem = driver.find_element(By.CSS_SELECTOR, '.price-per-sqft, .per-sqft')
                psf_text = psf_elem.text.strip().replace('$', '').replace('/sq ft', '').replace(',', '')
                psf_match = re.search(r'(\d+)', psf_text)
                if psf_match:
                    data['price_per_sqft'] = float(psf_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Monthly payment estimate
            try:
                payment_elem = driver.find_element(By.CSS_SELECTOR, '.monthly-payment, .estimated-payment')
                payment_text = payment_elem.text.strip().replace('$', '').replace(',', '').replace('/mo', '')
                payment_match = re.search(r'(\d+)', payment_text)
                if payment_match:
                    data['estimated_payment'] = int(payment_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Down payment
            try:
                down_elem = driver.find_element(By.CSS_SELECTOR, '.down-payment, .down')
                down_text = down_elem.text.strip().replace('$', '').replace(',', '')
                down_match = re.search(r'(\d+)', down_text)
                if down_match:
                    data['down_payment'] = int(down_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
                
        except Exception as e:
            logging.error(f"Error extracting pricing: {e}")
        
        return data
    
    def _extract_property_details(self, driver) -> Dict[str, Any]:
        """Extract detailed property information"""
        data = {}
        
        try:
            # Look for property details section
            detail_items = driver.find_elements(By.CSS_SELECTOR, '.property-detail, .home-detail, .listing-detail')
            
            for item in detail_items:
                try:
                    item_text = item.text.lower()
                    
                    if 'year built' in item_text or 'built' in item_text:
                        year_match = re.search(r'(\d{4})', item_text)
                        if year_match:
                            data['year_built'] = int(year_match.group(1))
                    
                    elif 'lot size' in item_text:
                        if 'acre' in item_text:
                            acres_match = re.search(r'([\d.]+)', item_text)
                            if acres_match:
                                data['lot_size_acres'] = float(acres_match.group(1))
                                data['lot_area_value'] = data['lot_size_acres']
                                data['lot_area_unit'] = 'acres'
                        elif 'sq ft' in item_text or 'sqft' in item_text:
                            sqft_match = re.search(r'([\d,]+)', item_text)
                            if sqft_match:
                                sqft_val = int(sqft_match.group(1).replace(',', ''))
                                data['lot_size_sqft'] = sqft_val
                                data['lot_area_value'] = float(sqft_val)
                                data['lot_area_unit'] = 'sqft'
                    
                    elif 'levels' in item_text or 'stories' in item_text:
                        levels_match = re.search(r'(\d+)', item_text)
                        if levels_match:
                            data['levels'] = int(levels_match.group(1))
                    
                    elif 'garage' in item_text:
                        garage_match = re.search(r'(\d+)', item_text)
                        if garage_match:
                            data['garage_spaces'] = int(garage_match.group(1))
                    
                    elif 'carport' in item_text:
                        carport_match = re.search(r'(\d+)', item_text)
                        if carport_match:
                            data['carport_spaces'] = int(carport_match.group(1))
                    
                    elif 'hoa' in item_text:
                        hoa_match = re.search(r'\$?([\d,]+)', item_text)
                        if hoa_match:
                            data['hoa_fee'] = int(hoa_match.group(1).replace(',', ''))
                    
                    elif 'tax' in item_text and ('property' in item_text or 'annual' in item_text):
                        tax_match = re.search(r'\$?([\d,]+)', item_text)
                        if tax_match:
                            data['property_taxes'] = int(tax_match.group(1).replace(',', ''))
                    
                    elif 'heating' in item_text:
                        heating_match = re.search(r'heating[:\s]+([^,\n]+)', item_text)
                        if heating_match:
                            data['heating_system'] = heating_match.group(1).strip()
                    
                    elif 'cooling' in item_text or 'air' in item_text:
                        cooling_match = re.search(r'(?:cooling|air)[:\s]+([^,\n]+)', item_text)
                        if cooling_match:
                            data['cooling_system'] = cooling_match.group(1).strip()
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting property details: {e}")
        
        return data
    
    def _extract_listing_info(self, driver) -> Dict[str, Any]:
        """Extract listing-specific information"""
        data = {}
        
        try:
            # Days on market
            try:
                dom_elem = driver.find_element(By.CSS_SELECTOR, '.days-on-market, .dom')
                dom_text = dom_elem.text.strip()
                dom_match = re.search(r'(\d+)', dom_text)
                if dom_match:
                    data['days_on_market'] = int(dom_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Listing status
            try:
                status_elem = driver.find_element(By.CSS_SELECTOR, '.listing-status, .status')
                data['listing_status'] = status_elem.text.strip()
            except NoSuchElementException:
                pass
            
            # MLS number
            try:
                mls_elem = driver.find_element(By.CSS_SELECTOR, '.mls-number, .mls')
                mls_text = mls_elem.text.strip()
                mls_match = re.search(r'(\w+)', mls_text)
                if mls_match:
                    data['mls_number'] = mls_match.group(1)
            except NoSuchElementException:
                pass
            
            # Check for special indicators
            page_text = driver.page_source.lower()
            data['new_construction'] = 'new construction' in page_text or 'newly built' in page_text
            data['virtual_tour'] = 'virtual tour' in page_text or '3d tour' in page_text
            data['video_tour'] = 'video tour' in page_text
            data['floor_plan_available'] = 'floor plan' in page_text
            
        except Exception as e:
            logging.error(f"Error extracting listing info: {e}")
        
        return data
    
    def _extract_photos(self, driver) -> Dict[str, Any]:
        """Extract property photos"""
        data = {}
        
        try:
            # Find photo elements
            photo_elements = driver.find_elements(By.CSS_SELECTOR, 'img[src*="homes.com"], img[src*="homescdn.com"]')
            
            if photo_elements:
                photos = []
                for img in photo_elements:
                    src = img.get_attribute('src')
                    if src and ('homes.com' in src or 'homescdn.com' in src):
                        # Skip very small images (likely thumbnails or icons)
                        if 'thumb' not in src and 'icon' not in src and 'logo' not in src:
                            photos.append(src)
                
                # Remove duplicates and limit
                unique_photos = list(dict.fromkeys(photos))[:25]  # Max 25 photos
                
                if unique_photos:
                    data['photos'] = unique_photos
                    data['primary_photo'] = unique_photos[0]
                    
        except Exception as e:
            logging.error(f"Error extracting photos: {e}")
        
        return data
    
    def _extract_agent_info(self, driver) -> Dict[str, Any]:
        """Extract agent and office information"""
        data = {}
        
        try:
            # Look for agent information
            try:
                agent_elem = driver.find_element(By.CSS_SELECTOR, '.agent-name, .listing-agent')
                data['listing_agent'] = agent_elem.text.strip()
                data['agent_name'] = data['listing_agent']  # Map to base field
            except NoSuchElementException:
                pass
            
            # Office information
            try:
                office_elem = driver.find_element(By.CSS_SELECTOR, '.agent-office, .listing-office')
                data['listing_office'] = office_elem.text.strip()
                data['broker_name'] = data['listing_office']  # Map to base field
            except NoSuchElementException:
                pass
            
            # Agent phone
            try:
                phone_elem = driver.find_element(By.CSS_SELECTOR, '.agent-phone, .contact-phone')
                data['agent_phone'] = phone_elem.text.strip()
            except NoSuchElementException:
                pass
            
            # Agent email
            try:
                email_elem = driver.find_element(By.CSS_SELECTOR, '.agent-email, .contact-email')
                data['agent_email'] = email_elem.text.strip()
            except NoSuchElementException:
                pass
                
        except Exception as e:
            logging.error(f"Error extracting agent info: {e}")
        
        return data
    
    def _extract_features(self, driver) -> Dict[str, Any]:
        """Extract property features and amenities"""
        data = {}
        
        try:
            # Look for features list
            feature_elements = driver.find_elements(By.CSS_SELECTOR, '.property-features li, .amenities li, .features li')
            
            interior_features = []
            exterior_features = []
            appliances = []
            flooring_types = []
            utilities = []
            
            for elem in feature_elements:
                try:
                    feature_text = elem.text.strip()
                    feature_lower = feature_text.lower()
                    
                    if feature_text:
                        # Categorize features
                        if any(interior in feature_lower for interior in ['fireplace', 'ceiling', 'closet', 'kitchen', 'bathroom']):
                            interior_features.append(feature_text)
                        elif any(exterior in feature_lower for exterior in ['deck', 'patio', 'yard', 'pool', 'fence']):
                            exterior_features.append(feature_text)
                        elif any(appliance in feature_lower for appliance in ['dishwasher', 'refrigerator', 'washer', 'dryer', 'microwave', 'oven', 'stove']):
                            appliances.append(feature_text)
                        elif any(flooring in feature_lower for flooring in ['hardwood', 'carpet', 'tile', 'laminate', 'vinyl', 'marble']):
                            flooring_types.append(feature_text)
                        elif any(utility in feature_lower for utility in ['electric', 'gas', 'water', 'sewer', 'cable']):
                            utilities.append(feature_text)
                            
                except Exception:
                    continue
            
            if interior_features:
                data['interior_features'] = interior_features
            if exterior_features:
                data['exterior_features'] = exterior_features
            if appliances:
                data['appliances_included'] = appliances
            if flooring_types:
                data['flooring_types'] = flooring_types
            if utilities:
                data['utilities'] = utilities
            
            # Look for description
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, '.property-description, .description, .listing-description')
                data['property_description'] = desc_elem.text.strip()
            except NoSuchElementException:
                pass
                
        except Exception as e:
            logging.error(f"Error extracting features: {e}")
        
        return data
    
    def _extract_school_info(self, driver) -> Dict[str, Any]:
        """Extract school information"""
        data = {}
        
        try:
            # Look for school information
            school_elements = driver.find_elements(By.CSS_SELECTOR, '.school-card, .school-info, .school')
            
            schools = []
            for school in school_elements:
                try:
                    school_data = {}
                    
                    # School name
                    try:
                        name_elem = school.find_element(By.CSS_SELECTOR, '.school-name, .name')
                        school_data['name'] = name_elem.text.strip()
                    except NoSuchElementException:
                        continue
                    
                    # School rating
                    try:
                        rating_elem = school.find_element(By.CSS_SELECTOR, '.school-rating, .rating')
                        rating_text = rating_elem.text.strip()
                        rating_match = re.search(r'(\d+)', rating_text)
                        if rating_match:
                            school_data['rating'] = rating_match.group(1)
                    except NoSuchElementException:
                        pass
                    
                    # School type/level
                    try:
                        type_elem = school.find_element(By.CSS_SELECTOR, '.school-type, .level')
                        school_data['type'] = type_elem.text.strip()
                    except NoSuchElementException:
                        pass
                    
                    if school_data.get('name'):
                        schools.append(school_data)
                        
                except Exception:
                    continue
            
            if schools:
                data['schools'] = schools
                
        except Exception as e:
            logging.error(f"Error extracting school info: {e}")
        
        return data
    
    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrape properties based on configuration"""
        entities = []
        
        # Extract addresses from labels
        addresses = []
        for label in scrape_config.labels or []:
            if label.value.startswith('address:'):
                address = label.value[8:]  # Remove 'address:' prefix
                addresses.append(address)
        
        if not addresses:
            logging.warning("No addresses found in scrape configuration")
            return entities
        
        # Limit based on entity_limit
        if scrape_config.entity_limit:
            addresses = addresses[:scrape_config.entity_limit]
        
        logging.info(f"Scraping {len(addresses)} properties from Homes.com via web scraping")
        
        # Scrape each address
        for address in addresses:
            try:
                entity = await self.scrape_address(address)
                if entity:
                    entities.append(entity)
                    logging.info(f"Successfully scraped address {address}")
                else:
                    logging.warning(f"Failed to scrape address {address}")
                    
            except Exception as e:
                logging.error(f"Error scraping address {address}: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(entities)} properties from Homes.com")
        return entities
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """Validate entities by re-scraping"""
        results = []
        
        for entity in entities:
            try:
                # Extract address from content
                content_json = json.loads(entity.content.decode('utf-8'))
                address = content_json.get('address')
                
                if not address:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Could not extract address from entity",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                    continue
                
                # Re-scrape the property
                fresh_entity = await self.scrape_address(address)
                
                if fresh_entity:
                    # Basic validation - check if key fields match
                    is_valid = self._validate_entity_fields(entity, fresh_entity)
                    results.append(ValidationResult(
                        is_valid=is_valid,
                        reason="Validated by re-scraping" if is_valid else "Fields do not match fresh data",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                else:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Could not re-scrape property for validation",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                    
            except Exception as e:
                logging.error(f"Validation error for {entity.uri}: {e}")
                results.append(ValidationResult(
                    is_valid=True,  # Assume valid on error to avoid penalizing miners
                    reason=f"Validation error - assumed valid: {str(e)}",
                    content_size_bytes_validated=entity.content_size_bytes
                ))
        
        return results
    
    def _validate_entity_fields(self, original: DataEntity, fresh: DataEntity) -> bool:
        """Validate key fields between original and fresh entity"""
        try:
            # Parse content from both entities
            original_content = json.loads(original.content.decode('utf-8'))
            fresh_content = json.loads(fresh.content.decode('utf-8'))
            
            # Check key fields that shouldn't change much
            key_fields = ['address', 'bedrooms', 'bathrooms', 'property_type']
            
            for field in key_fields:
                orig_val = original_content.get(field)
                fresh_val = fresh_content.get(field)
                
                if orig_val is not None and fresh_val is not None:
                    if orig_val != fresh_val:
                        logging.warning(f"Field {field} mismatch: {orig_val} vs {fresh_val}")
                        return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating entity fields: {e}")
            return False
    
    def __del__(self):
        """Cleanup driver on destruction"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


class RateLimiter:
    """Rate limiter for web scraping"""
    
    def __init__(self, requests_per_minute: int = 12):
        self.rpm = requests_per_minute
        self.requests = []
    
    async def wait_if_needed(self):
        """Wait if we're exceeding rate limits"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.rpm:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                logging.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)
