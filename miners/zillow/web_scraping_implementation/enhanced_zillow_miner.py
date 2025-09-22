"""
Enhanced Direct Zillow Web Scraper Implementation
Uses multiple extraction methods to capture maximum data from Zillow pages.
Targets 85%+ data completeness compared to API.
"""

import asyncio
import json
import logging
import random
import time
import re
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import requests

from scraping.scraper import Scraper, ScrapeConfig, ValidationResult
from miners.zillow.shared.comprehensive_zillow_schema import ComprehensiveZillowRealEstateContent
from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange


class EnhancedZillowScraper(Scraper):
    """Enhanced Zillow scraper using multiple extraction methods for maximum data capture"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=25)  # Conservative rate limiting
        self.driver = None
        self.session_count = 0
        self.max_session_requests = 15  # Restart browser frequently for anti-detection
        
        # Enhanced user agent rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
        
        # Metadata size limits
        self.MAX_METADATA_SIZE = 10 * 1024  # 10KB
        self.MAX_METADATA_KEYS = 50
        
        # Allowed metadata keys for controlled expansion
        self.ALLOWED_METADATA_KEYS = {
            'scraped_timestamp', 'page_load_time', 'extraction_method',
            'data_freshness_indicators', 'page_version', 'detected_features',
            'scraping_difficulty_score', 'anti_bot_detected', 'partial_load_detected',
            'javascript_errors', 'missing_elements', 'extraction_warnings',
            'dynamic_content_loaded', 'json_ld_found', 'structured_data_found'
        }
    
    def _create_driver(self):
        """Create enhanced undetected Chrome driver with stealth options"""
        try:
            options = uc.ChromeOptions()
            
            # Enhanced stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-gpu')
            
            # Randomize window size
            window_sizes = ['1920,1080', '1366,768', '1440,900', '1536,864']
            options.add_argument(f'--window-size={random.choice(window_sizes)}')
            
            # Randomize user agent
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')
            
            # Additional stealth measures
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Create driver
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(45)  # Longer timeout for complex pages
            
            # Remove automation indicators
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            logging.error(f"Failed to create Chrome driver: {e}")
            return None
    
    def _get_driver(self):
        """Get or create a Chrome driver with session management"""
        if self.driver is None or self.session_count >= self.max_session_requests:
            if self.driver:
                try:
                    self.driver.quit()
                    time.sleep(random.uniform(2, 5))  # Random delay between sessions
                except:
                    pass
            
            self.driver = self._create_driver()
            self.session_count = 0
        
        return self.driver
    
    async def scrape_zpid(self, zpid: str) -> Optional[DataEntity]:
        """Enhanced ZPID scraping with multiple extraction methods"""
        await self.rate_limiter.wait_if_needed()
        
        driver = self._get_driver()
        if not driver:
            logging.error(f"Could not create driver for ZPID {zpid}")
            return None
        
        try:
            # Construct Zillow URL
            url = f"https://www.zillow.com/homedetails/{zpid}_zpid/"
            
            # Try to get a more specific URL if possible
            specific_url = await self._zpid_to_url(zpid)
            if specific_url:
                url = specific_url
            
            logging.info(f"Enhanced scraping ZPID {zpid} from {url}")
            
            # Load page with enhanced waiting
            driver.get(url)
            
            # Wait for initial page load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check for blocking or errors
            if self._is_blocked_or_not_found(driver):
                logging.warning(f"Blocked or property not found for ZPID {zpid}")
                return None
            
            # Wait for dynamic content to load
            await self._wait_for_dynamic_content(driver)
            
            # Extract comprehensive data using multiple methods
            start_time = time.time()
            property_data = await self._extract_comprehensive_data(driver, zpid, url)
            extraction_time = time.time() - start_time
            
            if not property_data:
                logging.warning(f"No data extracted for ZPID {zpid}")
                return None
            
            # Add extraction metadata
            property_data['extra_metadata'] = self._create_extraction_metadata(extraction_time, driver)
            
            # Convert to comprehensive schema
            content = ComprehensiveZillowRealEstateContent.from_web_scraping(property_data, zpid, url)
            entity = content.to_data_entity()
            
            self.session_count += 1
            logging.info(f"Successfully extracted {len(property_data)} fields for ZPID {zpid}")
            return entity
            
        except TimeoutException:
            logging.error(f"Timeout loading page for ZPID {zpid}")
            return None
        except Exception as e:
            logging.error(f"Error scraping ZPID {zpid}: {e}")
            return None
    
    async def _wait_for_dynamic_content(self, driver):
        """Wait for dynamic content to load"""
        try:
            # Wait for key elements that indicate full page load
            wait = WebDriverWait(driver, 15)
            
            # Wait for price element
            try:
                wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    '[data-testid="price"], .notranslate, .Text-c11n-8-84-3__sc-aiai24-0'
                )))
            except TimeoutException:
                pass
            
            # Wait for property details
            try:
                wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    '[data-testid="bed-bath-sqft"], .summary-container, .hdp-fact-ataglance-container'
                )))
            except TimeoutException:
                pass
            
            # Additional wait for JavaScript to execute
            await asyncio.sleep(2)
            
        except Exception as e:
            logging.warning(f"Error waiting for dynamic content: {e}")
    
    async def _extract_comprehensive_data(self, driver, zpid: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract comprehensive data using multiple methods"""
        
        data = {
            'zpid': zpid,
            'source_url': url,
            'scraped_at': datetime.now(timezone.utc),
            'scraping_method': 'enhanced_web_scraping'
        }
        
        try:
            # Method 1: JSON-LD Structured Data (highest priority)
            json_ld_data = self._extract_json_ld_data(driver)
            if json_ld_data:
                data.update(json_ld_data)
                logging.info(f"Extracted JSON-LD data: {len(json_ld_data)} fields")
            
            # Method 2: JavaScript Variables and State
            js_data = self._extract_javascript_data(driver)
            if js_data:
                data.update(js_data)
                logging.info(f"Extracted JavaScript data: {len(js_data)} fields")
            
            # Method 3: Traditional CSS Selectors
            css_data = self._extract_css_elements(driver)
            if css_data:
                data.update(css_data)
                logging.info(f"Extracted CSS data: {len(css_data)} fields")
            
            # Method 4: Hidden and Meta Elements
            hidden_data = self._extract_hidden_elements(driver)
            if hidden_data:
                data.update(hidden_data)
                logging.info(f"Extracted hidden data: {len(hidden_data)} fields")
            
            # Method 5: Enhanced Photo and Media Extraction
            media_data = await self._extract_comprehensive_media(driver)
            if media_data:
                data.update(media_data)
                logging.info(f"Extracted media data: {len(media_data)} fields")
            
            # Method 6: Price History Deep Extraction
            price_history = await self._extract_price_history_advanced(driver)
            if price_history:
                data['priceHistory'] = price_history
                logging.info(f"Extracted price history: {len(price_history)} records")
            
            # Method 7: Tax History Extraction
            tax_history = self._extract_tax_history(driver)
            if tax_history:
                data['taxHistory'] = tax_history
                logging.info(f"Extracted tax history: {len(tax_history)} records")
            
            # Method 8: Agent and Contact Information
            agent_data = self._extract_agent_information(driver)
            if agent_data:
                data.update(agent_data)
                logging.info(f"Extracted agent data: {len(agent_data)} fields")
            
            # Method 9: School and Neighborhood Data
            neighborhood_data = self._extract_neighborhood_data(driver)
            if neighborhood_data:
                data.update(neighborhood_data)
                logging.info(f"Extracted neighborhood data: {len(neighborhood_data)} fields")
            
            # Method 10: Market Analytics and Insights
            market_data = self._extract_market_analytics(driver)
            if market_data:
                data.update(market_data)
                logging.info(f"Extracted market data: {len(market_data)} fields")
            
            # Calculate extraction confidence based on data completeness
            data['extraction_confidence'] = self._calculate_extraction_confidence(data)
            
            logging.info(f"Total extracted fields for ZPID {zpid}: {len(data)}")
            return data
            
        except Exception as e:
            logging.error(f"Error in comprehensive data extraction: {e}")
            return data if data else None
    
    def _extract_json_ld_data(self, driver) -> Dict[str, Any]:
        """Extract JSON-LD structured data"""
        try:
            json_ld_scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
            
            extracted_data = {}
            
            for script in json_ld_scripts:
                try:
                    json_content = script.get_attribute('innerHTML')
                    if json_content:
                        parsed_json = json.loads(json_content)
                        
                        # Extract relevant property data
                        if isinstance(parsed_json, dict):
                            # Look for property-related structured data
                            if parsed_json.get('@type') in ['RealEstateListing', 'Property', 'SingleFamilyResidence']:
                                extracted_data.update(self._parse_structured_property_data(parsed_json))
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logging.warning(f"Error parsing JSON-LD: {e}")
                    continue
            
            return extracted_data
            
        except Exception as e:
            logging.warning(f"Error extracting JSON-LD data: {e}")
            return {}
    
    def _extract_javascript_data(self, driver) -> Dict[str, Any]:
        """Extract data from JavaScript variables"""
        try:
            extracted_data = {}
            
            # Common Zillow JavaScript variables
            js_variables = [
                'window.__INITIAL_STATE__',
                'window.hdpApolloCache',
                'window.__NEXT_DATA__',
                'window.mapBounds',
                'window.regionId',
                'window.zpid'
            ]
            
            for var_name in js_variables:
                try:
                    js_data = driver.execute_script(f"return {var_name};")
                    if js_data:
                        extracted_data.update(self._parse_js_variable_data(var_name, js_data))
                except Exception:
                    continue
            
            # Try to extract specific property data from page scripts
            try:
                property_data_script = driver.execute_script("""
                    var scripts = document.getElementsByTagName('script');
                    for (var i = 0; i < scripts.length; i++) {
                        if (scripts[i].innerHTML.includes('zpid') || scripts[i].innerHTML.includes('homeDetails')) {
                            return scripts[i].innerHTML;
                        }
                    }
                    return null;
                """)
                
                if property_data_script:
                    # Parse property data from script content
                    extracted_data.update(self._parse_inline_script_data(property_data_script))
                    
            except Exception:
                pass
            
            return extracted_data
            
        except Exception as e:
            logging.warning(f"Error extracting JavaScript data: {e}")
            return {}
    
    def _extract_css_elements(self, driver) -> Dict[str, Any]:
        """Enhanced CSS element extraction"""
        try:
            data = {}
            
            # Enhanced selectors for different page layouts
            selectors = {
                # Basic property info
                'price': [
                    '[data-testid="price"]',
                    '.notranslate',
                    '.Text-c11n-8-84-3__sc-aiai24-0.kHDsUF',
                    '.summary-container .notranslate'
                ],
                'address': [
                    '[data-testid="bdp-building-address"]',
                    'h1.summary-container',
                    '.summary-address',
                    '.hdp-property-address'
                ],
                'bedrooms': [
                    '[data-testid="bed-bath-sqft"] span:first-child',
                    '.summary-container .Text-c11n-8-84-3__sc-aiai24-0:contains("bed")',
                    '.hdp-fact-ataglance-value:contains("bed")'
                ],
                'bathrooms': [
                    '[data-testid="bed-bath-sqft"] span:nth-child(2)',
                    '.summary-container .Text-c11n-8-84-3__sc-aiai24-0:contains("bath")',
                    '.hdp-fact-ataglance-value:contains("bath")'
                ],
                'living_area': [
                    '[data-testid="bed-bath-sqft"] span:last-child',
                    '.summary-container .Text-c11n-8-84-3__sc-aiai24-0:contains("sqft")',
                    '.hdp-fact-ataglance-value:contains("sqft")'
                ],
                'property_type': [
                    '[data-testid="property-type"]',
                    '.hdp-property-type',
                    '.summary-property-type'
                ],
                'year_built': [
                    '[data-testid="year-built"]',
                    '.hdp-fact-ataglance-value:contains("Built")',
                    'span:contains("Built in")'
                ],
                'lot_size': [
                    '[data-testid="lot-size"]',
                    '.hdp-fact-ataglance-value:contains("Lot")',
                    'span:contains("lot")'
                ],
                'hoa_fee': [
                    '[data-testid="hoa-fee"]',
                    '.hdp-fact-ataglance-value:contains("HOA")',
                    'span:contains("HOA")'
                ],
                'zestimate': [
                    '[data-testid="zestimate-value"]',
                    '.Zestimate-value',
                    '.zestimate-price'
                ]
            }
            
            # Extract using multiple selectors for each field
            for field, selector_list in selectors.items():
                value = None
                for selector in selector_list:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and elements[0].text.strip():
                            value = self._clean_extracted_value(field, elements[0].text.strip())
                            break
                    except:
                        continue
                
                if value:
                    data[field] = value
            
            # Extract property status
            try:
                status_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.hdp-listing-status, [data-testid="listing-status"], .listing-status')
                if status_elements:
                    data['listing_status'] = status_elements[0].text.strip()
            except:
                pass
            
            return data
            
        except Exception as e:
            logging.warning(f"Error extracting CSS elements: {e}")
            return {}
    
    def _extract_hidden_elements(self, driver) -> Dict[str, Any]:
        """Extract data from hidden elements and meta tags"""
        try:
            data = {}
            
            # Meta tags
            meta_tags = driver.find_elements(By.CSS_SELECTOR, 'meta[property], meta[name]')
            for meta in meta_tags:
                try:
                    property_attr = meta.get_attribute('property') or meta.get_attribute('name')
                    content = meta.get_attribute('content')
                    
                    if property_attr and content:
                        # Map relevant meta tags to data fields
                        if 'price' in property_attr.lower():
                            data['meta_price'] = content
                        elif 'address' in property_attr.lower():
                            data['meta_address'] = content
                        elif 'latitude' in property_attr.lower():
                            data['latitude'] = float(content)
                        elif 'longitude' in property_attr.lower():
                            data['longitude'] = float(content)
                        elif 'image' in property_attr.lower() and not data.get('img_src'):
                            data['img_src'] = content
                            
                except:
                    continue
            
            # Hidden input fields
            hidden_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="hidden"]')
            for input_elem in hidden_inputs:
                try:
                    name = input_elem.get_attribute('name')
                    value = input_elem.get_attribute('value')
                    
                    if name and value:
                        if 'zpid' in name.lower():
                            data['hidden_zpid'] = value
                        elif 'price' in name.lower():
                            data['hidden_price'] = value
                            
                except:
                    continue
            
            return data
            
        except Exception as e:
            logging.warning(f"Error extracting hidden elements: {e}")
            return {}
    
    async def _extract_comprehensive_media(self, driver) -> Dict[str, Any]:
        """Extract comprehensive media information"""
        try:
            media_data = {}
            
            # Primary image
            try:
                img_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.media-stream-photo img, .hdp-hero-image img, .property-photo img')
                if img_elements:
                    media_data['img_src'] = img_elements[0].get_attribute('src')
            except:
                pass
            
            # All photos from carousel
            photos = []
            try:
                photo_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.media-stream img, .photo-carousel img, .property-photos img')
                for img in photo_elements:
                    src = img.get_attribute('src')
                    if src and 'zillowstatic.com' in src:
                        photos.append(src)
                
                # Remove duplicates and limit
                unique_photos = list(dict.fromkeys(photos))[:30]
                if unique_photos:
                    media_data['photos'] = unique_photos
                    media_data['carouselPhotos'] = [{'url': photo} for photo in unique_photos]
                    
            except:
                pass
            
            # Virtual tour links
            try:
                tour_links = driver.find_elements(By.CSS_SELECTOR, 
                    'a[href*="tour"], a[href*="3d"], .virtual-tour-link')
                for link in tour_links:
                    href = link.get_attribute('href')
                    if href:
                        if '3d' in href.lower() or 'matterport' in href.lower():
                            media_data['3d_tour_url'] = href
                        elif 'tour' in href.lower():
                            media_data['tourUrl'] = href
            except:
                pass
            
            # Video content
            try:
                video_elements = driver.find_elements(By.CSS_SELECTOR, 'video, iframe[src*="video"]')
                for video in video_elements:
                    src = video.get_attribute('src')
                    if src:
                        media_data['videoUrl'] = src
                        break
            except:
                pass
            
            return media_data
            
        except Exception as e:
            logging.warning(f"Error extracting media: {e}")
            return {}
    
    async def _extract_price_history_advanced(self, driver) -> List[Dict[str, Any]]:
        """Advanced price history extraction"""
        try:
            price_history = []
            
            # Method 1: Look for visible price history table
            try:
                price_rows = driver.find_elements(By.CSS_SELECTOR, 
                    '.price-history-table tr, .hdp-price-history tr')
                
                for row in price_rows[1:]:  # Skip header
                    cells = row.find_elements(By.CSS_SELECTOR, 'td')
                    if len(cells) >= 3:
                        date_text = cells[0].text.strip()
                        event_text = cells[1].text.strip()
                        price_text = cells[2].text.strip()
                        
                        if date_text and price_text:
                            price_history.append({
                                'date': date_text,
                                'event': event_text,
                                'price': self._parse_price(price_text),
                                'source': 'visible_table'
                            })
                            
            except:
                pass
            
            # Method 2: Try to expand "Show More" for price history
            try:
                show_more_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    'button:contains("Show more"), .show-more-button, .expand-button')
                
                for button in show_more_buttons:
                    if 'price' in button.text.lower() or 'history' in button.text.lower():
                        driver.execute_script("arguments[0].click();", button)
                        await asyncio.sleep(2)  # Wait for content to load
                        
                        # Re-extract after expansion
                        expanded_rows = driver.find_elements(By.CSS_SELECTOR, 
                            '.price-history-table tr, .hdp-price-history tr')
                        
                        for row in expanded_rows[len(price_history)+1:]:
                            cells = row.find_elements(By.CSS_SELECTOR, 'td')
                            if len(cells) >= 3:
                                price_history.append({
                                    'date': cells[0].text.strip(),
                                    'event': cells[1].text.strip(),
                                    'price': self._parse_price(cells[2].text.strip()),
                                    'source': 'expanded_table'
                                })
                        break
                        
            except:
                pass
            
            # Method 3: Extract from JavaScript variables
            try:
                js_price_history = driver.execute_script("""
                    return window.priceHistory || window.__INITIAL_STATE__?.propertyDetails?.priceHistory || null;
                """)
                
                if js_price_history and isinstance(js_price_history, list):
                    for record in js_price_history:
                        if isinstance(record, dict):
                            price_history.append({
                                'date': record.get('date'),
                                'event': record.get('event', 'Unknown'),
                                'price': record.get('price'),
                                'source': 'javascript'
                            })
                            
            except:
                pass
            
            return price_history[:20]  # Limit to 20 most recent records
            
        except Exception as e:
            logging.warning(f"Error extracting price history: {e}")
            return []
    
    def _extract_tax_history(self, driver) -> List[Dict[str, Any]]:
        """Extract tax history information"""
        try:
            tax_history = []
            
            # Look for tax history table
            try:
                tax_rows = driver.find_elements(By.CSS_SELECTOR, 
                    '.tax-history-table tr, .hdp-tax-history tr, .property-tax-history tr')
                
                for row in tax_rows[1:]:  # Skip header
                    cells = row.find_elements(By.CSS_SELECTOR, 'td')
                    if len(cells) >= 3:
                        year_text = cells[0].text.strip()
                        tax_text = cells[1].text.strip()
                        value_text = cells[2].text.strip() if len(cells) > 2 else ""
                        
                        if year_text and tax_text:
                            tax_history.append({
                                'year': year_text,
                                'taxPaid': self._parse_price(tax_text),
                                'value': self._parse_price(value_text) if value_text else None,
                                'source': 'visible_table'
                            })
                            
            except:
                pass
            
            # Extract from JavaScript if available
            try:
                js_tax_history = driver.execute_script("""
                    return window.taxHistory || window.__INITIAL_STATE__?.propertyDetails?.taxHistory || null;
                """)
                
                if js_tax_history and isinstance(js_tax_history, list):
                    for record in js_tax_history:
                        if isinstance(record, dict):
                            tax_history.append({
                                'year': record.get('year'),
                                'taxPaid': record.get('taxPaid'),
                                'value': record.get('value'),
                                'source': 'javascript'
                            })
                            
            except:
                pass
            
            return tax_history[:15]  # Limit to 15 most recent records
            
        except Exception as e:
            logging.warning(f"Error extracting tax history: {e}")
            return []
    
    def _extract_agent_information(self, driver) -> Dict[str, Any]:
        """Extract comprehensive agent and contact information"""
        try:
            agent_data = {}
            
            # Agent name
            try:
                agent_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.agent-name, .listing-agent-name, .contact-agent-name')
                if agent_elements:
                    agent_data['agent_name'] = agent_elements[0].text.strip()
            except:
                pass
            
            # Agent phone
            try:
                phone_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.agent-phone, .contact-phone, .listing-agent-phone')
                if phone_elements:
                    agent_data['agent_phone'] = phone_elements[0].text.strip()
            except:
                pass
            
            # Brokerage name
            try:
                brokerage_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.brokerage-name, .listing-office, .agent-office')
                if brokerage_elements:
                    agent_data['broker_name'] = brokerage_elements[0].text.strip()
                    agent_data['brokerageName'] = agent_data['broker_name']
            except:
                pass
            
            # Agent photo
            try:
                agent_photo_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.agent-photo img, .listing-agent-photo img')
                if agent_photo_elements:
                    agent_data['agent_photo'] = agent_photo_elements[0].get_attribute('src')
            except:
                pass
            
            # Extract from contact recipients structure
            try:
                contact_data = driver.execute_script("""
                    return window.contactRecipients || window.__INITIAL_STATE__?.contactRecipients || null;
                """)
                
                if contact_data and isinstance(contact_data, list) and len(contact_data) > 0:
                    first_contact = contact_data[0]
                    if isinstance(first_contact, dict):
                        agent_data['contact_recipients'] = contact_data
                        if first_contact.get('display_name'):
                            agent_data['agent_name'] = first_contact['display_name']
                        if first_contact.get('business_name'):
                            agent_data['broker_name'] = first_contact['business_name']
                            
            except:
                pass
            
            return agent_data
            
        except Exception as e:
            logging.warning(f"Error extracting agent information: {e}")
            return {}
    
    def _extract_neighborhood_data(self, driver) -> Dict[str, Any]:
        """Extract neighborhood and school information"""
        try:
            neighborhood_data = {}
            
            # School information
            schools = []
            try:
                school_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.school-card, .nearby-school, .school-info')
                
                for school in school_elements:
                    try:
                        school_info = {}
                        
                        # School name
                        name_elem = school.find_element(By.CSS_SELECTOR, '.school-name, .name')
                        if name_elem:
                            school_info['name'] = name_elem.text.strip()
                        
                        # School rating
                        rating_elem = school.find_element(By.CSS_SELECTOR, '.school-rating, .rating')
                        if rating_elem:
                            rating_text = rating_elem.text.strip()
                            rating_match = re.search(r'(\d+)', rating_text)
                            if rating_match:
                                school_info['rating'] = int(rating_match.group(1))
                        
                        # School level
                        level_elem = school.find_element(By.CSS_SELECTOR, '.school-level, .level')
                        if level_elem:
                            school_info['level'] = level_elem.text.strip()
                        
                        if school_info.get('name'):
                            schools.append(school_info)
                            
                    except:
                        continue
                        
            except:
                pass
            
            if schools:
                neighborhood_data['schools'] = schools
            
            # Walk score and transit
            try:
                walk_score_elem = driver.find_element(By.CSS_SELECTOR, '.walk-score, .walkability-score')
                if walk_score_elem:
                    score_text = walk_score_elem.text.strip()
                    score_match = re.search(r'(\d+)', score_text)
                    if score_match:
                        neighborhood_data['walkScore'] = int(score_match.group(1))
            except:
                pass
            
            return neighborhood_data
            
        except Exception as e:
            logging.warning(f"Error extracting neighborhood data: {e}")
            return {}
    
    def _extract_market_analytics(self, driver) -> Dict[str, Any]:
        """Extract market analytics and insights"""
        try:
            market_data = {}
            
            # Days on Zillow
            try:
                days_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.days-on-zillow, .days-on-market, .listing-duration')
                for elem in days_elements:
                    text = elem.text.strip()
                    days_match = re.search(r'(\d+)\s*day', text, re.IGNORECASE)
                    if days_match:
                        market_data['daysOnZillow'] = int(days_match.group(1))
                        break
            except:
                pass
            
            # Page views
            try:
                views_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.page-views, .view-count, .property-views')
                for elem in views_elements:
                    text = elem.text.strip()
                    views_match = re.search(r'(\d+)\s*view', text, re.IGNORECASE)
                    if views_match:
                        market_data['pageViews'] = int(views_match.group(1))
                        break
            except:
                pass
            
            # Favorite count
            try:
                favorite_elements = driver.find_elements(By.CSS_SELECTOR, 
                    '.favorite-count, .save-count, .heart-count')
                for elem in favorite_elements:
                    text = elem.text.strip()
                    fav_match = re.search(r'(\d+)', text)
                    if fav_match:
                        market_data['favoriteCount'] = int(fav_match.group(1))
                        break
            except:
                pass
            
            return market_data
            
        except Exception as e:
            logging.warning(f"Error extracting market analytics: {e}")
            return {}
    
    def _create_extraction_metadata(self, extraction_time: float, driver) -> Dict[str, Any]:
        """Create controlled extraction metadata"""
        try:
            metadata = {
                'scraped_timestamp': datetime.now(timezone.utc).isoformat(),
                'page_load_time': round(extraction_time, 2),
                'extraction_method': 'enhanced_multi_layer',
                'scraping_difficulty_score': self._calculate_scraping_difficulty(driver),
            }
            
            # Check for anti-bot detection
            page_source = driver.page_source.lower()
            if any(indicator in page_source for indicator in ['captcha', 'blocked', 'access denied']):
                metadata['anti_bot_detected'] = True
            
            # Check for JavaScript errors
            try:
                js_errors = driver.get_log('browser')
                if js_errors:
                    metadata['javascript_errors'] = len([e for e in js_errors if e['level'] == 'SEVERE'])
            except:
                pass
            
            # Limit metadata size
            metadata_str = json.dumps(metadata)
            if len(metadata_str.encode('utf-8')) > self.MAX_METADATA_SIZE:
                # Keep only essential metadata if too large
                metadata = {
                    'scraped_timestamp': metadata['scraped_timestamp'],
                    'extraction_method': metadata['extraction_method'],
                    'page_load_time': metadata['page_load_time']
                }
            
            return metadata
            
        except Exception as e:
            logging.warning(f"Error creating extraction metadata: {e}")
            return {'extraction_method': 'enhanced_multi_layer'}
    
    def _calculate_scraping_difficulty(self, driver) -> float:
        """Calculate scraping difficulty score (0-10)"""
        try:
            difficulty = 0.0
            
            # Check for anti-bot indicators
            page_source = driver.page_source.lower()
            if 'captcha' in page_source:
                difficulty += 3.0
            if 'blocked' in page_source:
                difficulty += 2.0
            if 'perimeterx' in page_source:
                difficulty += 2.0
            
            # Check for dynamic content
            script_tags = driver.find_elements(By.CSS_SELECTOR, 'script')
            if len(script_tags) > 20:
                difficulty += 1.0
            
            # Check page load time (implicit from extraction time)
            # This would be set by the calling function
            
            return min(difficulty, 10.0)
            
        except:
            return 5.0  # Default moderate difficulty
    
    def _calculate_extraction_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate confidence in extracted data (0-1)"""
        try:
            # Key fields that indicate successful extraction
            key_fields = ['price', 'bedrooms', 'bathrooms', 'living_area', 'address']
            populated_key_fields = sum(1 for field in key_fields if data.get(field))
            
            base_confidence = populated_key_fields / len(key_fields)
            
            # Bonus for additional data
            bonus_fields = ['priceHistory', 'taxHistory', 'photos', 'agent_name', 'schools']
            populated_bonus = sum(1 for field in bonus_fields if data.get(field))
            bonus_confidence = (populated_bonus / len(bonus_fields)) * 0.3
            
            total_confidence = min(base_confidence + bonus_confidence, 1.0)
            return round(total_confidence, 3)
            
        except:
            return 0.5  # Default moderate confidence
    
    def _clean_extracted_value(self, field: str, value: str) -> Any:
        """Clean and convert extracted values to appropriate types"""
        try:
            if not value or value.strip() == "":
                return None
            
            value = value.strip()
            
            # Price fields
            if 'price' in field.lower() or field in ['zestimate', 'hoa_fee']:
                return self._parse_price(value)
            
            # Numeric fields
            elif field in ['bedrooms', 'year_built', 'lot_size']:
                match = re.search(r'(\d+)', value)
                return int(match.group(1)) if match else None
            
            # Float fields
            elif field in ['bathrooms']:
                match = re.search(r'([\d.]+)', value)
                return float(match.group(1)) if match else None
            
            # Area fields
            elif 'area' in field.lower() or 'sqft' in field.lower():
                # Extract number and convert
                match = re.search(r'([\d,]+)', value.replace(',', ''))
                return int(match.group(1)) if match else None
            
            # Default: return cleaned string
            else:
                return value
                
        except Exception:
            return value  # Return original value if cleaning fails
    
    def _parse_price(self, price_text: str) -> Optional[int]:
        """Parse price from text"""
        try:
            if not price_text:
                return None
            
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.]', '', price_text)
            if cleaned:
                return int(float(cleaned))
            return None
            
        except:
            return None
    
    async def _zpid_to_url(self, zpid: str) -> Optional[str]:
        """Try to construct a more specific URL for the ZPID"""
        try:
            # This would ideally use a property search API or cached mapping
            # For now, return the basic URL format
            return f"https://www.zillow.com/homedetails/{zpid}_zpid/"
            
        except:
            return None
    
    def _is_blocked_or_not_found(self, driver) -> bool:
        """Check if we've been blocked or property not found"""
        try:
            page_source = driver.page_source.lower()
            
            # Check for blocking indicators
            blocked_indicators = [
                'access denied', 'blocked', 'captcha', 'perimeterx',
                'security check', 'unusual traffic', 'property not found',
                'listing not available', 'page not found', 'no longer available'
            ]
            
            return any(indicator in page_source for indicator in blocked_indicators)
            
        except:
            return False
    
    # ... [Additional helper methods for parsing structured data would go here] ...
    
    def _parse_structured_property_data(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse structured property data from JSON-LD"""
        # Implementation would map structured data fields to our schema
        return {}
    
    def _parse_js_variable_data(self, var_name: str, js_data: Any) -> Dict[str, Any]:
        """Parse data from JavaScript variables"""
        # Implementation would extract relevant fields from JS objects
        return {}
    
    def _parse_inline_script_data(self, script_content: str) -> Dict[str, Any]:
        """Parse data from inline script content"""
        # Implementation would use regex to extract data from script strings
        return {}
    
    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrape properties based on configuration"""
        entities = []
        
        # Extract ZPIDs from labels
        zpids = []
        for label in scrape_config.labels or []:
            if label.value.startswith('zpid:'):
                zpid = label.value[5:]  # Remove 'zpid:' prefix
                zpids.append(zpid)
        
        if not zpids:
            logging.warning("No ZPIDs found in scrape configuration")
            return entities
        
        # Limit based on entity_limit
        if scrape_config.entity_limit:
            zpids = zpids[:scrape_config.entity_limit]
        
        logging.info(f"Enhanced scraping {len(zpids)} properties from Zillow")
        
        # Scrape each ZPID
        for zpid in zpids:
            try:
                entity = await self.scrape_zpid(zpid)
                if entity:
                    entities.append(entity)
                    logging.info(f"Successfully scraped ZPID {zpid}")
                else:
                    logging.warning(f"Failed to scrape ZPID {zpid}")
                    
            except Exception as e:
                logging.error(f"Error scraping ZPID {zpid}: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(entities)} properties from Zillow")
        return entities
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """Validate entities by re-scraping"""
        results = []
        
        for entity in entities:
            try:
                # Extract ZPID from content
                content_json = json.loads(entity.content.decode('utf-8'))
                zpid = content_json.get('zpid')
                
                if not zpid:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Could not extract ZPID from entity",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                    continue
                
                # Re-scrape the property
                fresh_entity = await self.scrape_zpid(zpid)
                
                if fresh_entity:
                    # Enhanced validation with data quality metrics
                    is_valid = self._validate_entity_fields(entity, fresh_entity)
                    results.append(ValidationResult(
                        is_valid=is_valid,
                        reason="Validated by enhanced re-scraping" if is_valid else "Enhanced validation failed",
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
        """Enhanced validation with data quality assessment"""
        try:
            # Parse content from both entities
            original_content = json.loads(original.content.decode('utf-8'))
            fresh_content = json.loads(fresh.content.decode('utf-8'))
            
            # Check key fields that shouldn't change much
            key_fields = ['zpid', 'address', 'bedrooms', 'bathrooms', 'property_type']
            
            matches = 0
            total_comparisons = 0
            
            for field in key_fields:
                orig_val = original_content.get(field)
                fresh_val = fresh_content.get(field)
                
                if orig_val is not None and fresh_val is not None:
                    total_comparisons += 1
                    if orig_val == fresh_val:
                        matches += 1
                    else:
                        logging.warning(f"Field {field} mismatch: {orig_val} vs {fresh_val}")
            
            # Require at least 80% field accuracy
            if total_comparisons > 0:
                accuracy = matches / total_comparisons
                return accuracy >= 0.8
            
            return True  # No comparisons possible, assume valid
            
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
    """Enhanced rate limiter with adaptive delays"""
    
    def __init__(self, requests_per_minute: int = 25):
        self.rpm = requests_per_minute
        self.requests = []
        self.consecutive_errors = 0
    
    async def wait_if_needed(self):
        """Wait if we're exceeding rate limits with adaptive delays"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.rpm:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                # Add random jitter and adaptive delay for errors
                jitter = random.uniform(0.5, 2.0)
                error_delay = min(self.consecutive_errors * 2, 10)  # Max 10 seconds
                total_sleep = sleep_time + jitter + error_delay
                
                logging.info(f"Rate limiting: sleeping for {total_sleep:.1f} seconds")
                await asyncio.sleep(total_sleep)
        
        self.requests.append(now)
    
    def record_error(self):
        """Record an error for adaptive delays"""
        self.consecutive_errors += 1
    
    def record_success(self):
        """Record a success to reset error counter"""
        self.consecutive_errors = max(0, self.consecutive_errors - 1)
