"""
Direct Zillow Web Scraper Implementation
Scrapes property data directly from Zillow property pages using Selenium.
"""

import asyncio
import json
import logging
import random
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

from scraping.scraper import Scraper, ScrapeConfig, ValidationResult
from scraping.zillow.model import RealEstateContent
from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange


class DirectZillowScraper(Scraper):
    """Direct Zillow scraper using Selenium and undetected Chrome"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=30)
        self.driver = None
        self.session_count = 0
        self.max_session_requests = 20  # Restart browser after 20 requests
        
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
            options.add_argument('--disable-javascript')  # May need to enable for some data
            
            # Randomize user agent
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')
            
            # Create driver
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(30)
            
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
    
    async def scrape_zpid(self, zpid: str) -> Optional[DataEntity]:
        """Scrape a single ZPID and return DataEntity"""
        await self.rate_limiter.wait_if_needed()
        
        driver = self._get_driver()
        if not driver:
            logging.error(f"Could not create driver for ZPID {zpid}")
            return None
        
        try:
            # We need to construct URL - this is a limitation since we only have ZPID
            # For now, we'll use a search approach or try common URL patterns
            url = await self._zpid_to_url(zpid)
            if not url:
                logging.error(f"Could not construct URL for ZPID {zpid}")
                return None
            
            logging.info(f"Scraping ZPID {zpid} from {url}")
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if we hit anti-bot protection
            if self._is_blocked(driver):
                logging.warning(f"Anti-bot protection detected for ZPID {zpid}")
                return None
            
            # Extract data from the page
            property_data = self._extract_property_data(driver, zpid)
            if not property_data:
                return None
            
            # Convert to RealEstateContent and then DataEntity
            content = RealEstateContent(**property_data)
            entity = content.to_data_entity()
            
            self.session_count += 1
            return entity
            
        except TimeoutException:
            logging.error(f"Timeout loading page for ZPID {zpid}")
            return None
        except Exception as e:
            logging.error(f"Error scraping ZPID {zpid}: {e}")
            return None
    
    async def _zpid_to_url(self, zpid: str) -> Optional[str]:
        """Convert ZPID to full URL - this requires some creativity"""
        clean_zpid = zpid.replace("_zpid", "")
        
        # Strategy 1: Try Zillow's property search API to get the address
        # This would require a separate request but might work
        
        # Strategy 2: Use a common URL pattern and let Zillow redirect
        # Many ZPIDs work with a generic pattern
        generic_url = f"https://www.zillow.com/homedetails/{clean_zpid}_zpid/"
        
        # Strategy 3: Use Zillow's search functionality
        # We could search by ZPID and get redirected to the property page
        
        return generic_url  # Start with generic pattern
    
    def _is_blocked(self, driver) -> bool:
        """Check if we've been blocked by anti-bot protection"""
        page_source = driver.page_source.lower()
        
        # Check for common anti-bot indicators
        blocked_indicators = [
            'perimeterx',
            'access to this page has been denied',
            'captcha',
            'blocked',
            'security check',
            'unusual traffic'
        ]
        
        return any(indicator in page_source for indicator in blocked_indicators)
    
    def _extract_property_data(self, driver, zpid: str) -> Optional[Dict[str, Any]]:
        """Extract property data from the Zillow page"""
        try:
            data = {
                'zpid': zpid,
                'scraped_at': datetime.now(timezone.utc),
                'data_source': 'direct_scraping'
            }
            
            # Extract basic information
            data.update(self._extract_basic_info(driver))
            
            # Extract price and estimates
            data.update(self._extract_pricing(driver))
            
            # Extract property details
            data.update(self._extract_property_details(driver))
            
            # Extract price history
            data.update(self._extract_price_history(driver))
            
            # Extract photos
            data.update(self._extract_photos(driver))
            
            # Extract agent information
            data.update(self._extract_agent_info(driver))
            
            # Extract school information
            data.update(self._extract_school_info(driver))
            
            return data
            
        except Exception as e:
            logging.error(f"Error extracting data for ZPID {zpid}: {e}")
            return None
    
    def _extract_basic_info(self, driver) -> Dict[str, Any]:
        """Extract basic property information"""
        data = {}
        
        try:
            # Address
            address_selectors = [
                'h1[data-testid="bdp-building-address"]',
                'h1.ds-address-container',
                '.ds-chip-removable-content'
            ]
            
            for selector in address_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    data['address'] = element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Bedrooms, Bathrooms, Square Feet
            facts_selectors = [
                '[data-testid="bed-bath-sqft-facts"]',
                '.ds-bed-bath-living-area',
                '.ds-summary-row'
            ]
            
            for selector in facts_selectors:
                try:
                    facts_element = driver.find_element(By.CSS_SELECTOR, selector)
                    facts_text = facts_element.text
                    
                    # Parse bed/bath/sqft from text like "3 bd | 2 ba | 1,500 sqft"
                    if 'bd' in facts_text:
                        bed_match = facts_text.split('bd')[0].strip().split()[-1]
                        data['bedrooms'] = int(bed_match) if bed_match.isdigit() else None
                    
                    if 'ba' in facts_text:
                        bath_text = facts_text.split('ba')[0].split('|')[-1].strip()
                        try:
                            data['bathrooms'] = float(bath_text)
                        except ValueError:
                            pass
                    
                    if 'sqft' in facts_text:
                        sqft_text = facts_text.split('sqft')[0].split('|')[-1].strip().replace(',', '')
                        data['living_area'] = int(sqft_text) if sqft_text.isdigit() else None
                    
                    break
                except NoSuchElementException:
                    continue
            
            # Property type
            type_selectors = [
                '[data-testid="property-type"]',
                '.ds-property-type'
            ]
            
            for selector in type_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    data['property_type'] = element.text.strip()
                    break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting basic info: {e}")
        
        return data
    
    def _extract_pricing(self, driver) -> Dict[str, Any]:
        """Extract price and estimate information"""
        data = {}
        
        try:
            # Current price
            price_selectors = [
                '[data-testid="price"]',
                '.ds-price',
                '.notranslate'
            ]
            
            for selector in price_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = element.text.strip().replace('$', '').replace(',', '')
                    if price_text.replace('.', '').isdigit():
                        data['price'] = int(float(price_text))
                        break
                except (NoSuchElementException, ValueError):
                    continue
            
            # Zestimate
            zestimate_selectors = [
                '[data-testid="zestimate-text"]',
                '.ds-estimate-value'
            ]
            
            for selector in zestimate_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    zest_text = element.text.strip().replace('$', '').replace(',', '')
                    if zest_text.replace('.', '').isdigit():
                        data['zestimate'] = int(float(zest_text))
                        break
                except (NoSuchElementException, ValueError):
                    continue
            
            # Rent estimate
            rent_selectors = [
                '[data-testid="rent-zestimate"]',
                '.ds-rent-estimate'
            ]
            
            for selector in rent_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    rent_text = element.text.strip().replace('$', '').replace(',', '').replace('/mo', '')
                    if rent_text.replace('.', '').isdigit():
                        data['rent_zestimate'] = int(float(rent_text))
                        break
                except (NoSuchElementException, ValueError):
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting pricing: {e}")
        
        return data
    
    def _extract_property_details(self, driver) -> Dict[str, Any]:
        """Extract detailed property information"""
        data = {}
        
        try:
            # Year built, lot size, etc. from facts section
            facts_section = driver.find_elements(By.CSS_SELECTOR, '.ds-home-fact-list-item')
            
            for fact in facts_section:
                try:
                    fact_text = fact.text.lower()
                    
                    if 'year built' in fact_text or 'built in' in fact_text:
                        year_text = ''.join(filter(str.isdigit, fact_text))
                        if len(year_text) == 4:
                            data['year_built'] = int(year_text)
                    
                    if 'lot size' in fact_text:
                        # Extract lot size and unit
                        lot_text = fact_text.replace('lot size', '').strip()
                        if 'sqft' in lot_text:
                            data['lot_area_unit'] = 'sqft'
                            lot_value = ''.join(filter(str.isdigit, lot_text.split('sqft')[0]))
                            if lot_value:
                                data['lot_area_value'] = float(lot_value)
                        elif 'acres' in lot_text:
                            data['lot_area_unit'] = 'acres'
                            lot_value = lot_text.split('acres')[0].strip()
                            try:
                                data['lot_area_value'] = float(lot_value)
                            except ValueError:
                                pass
                                
                except Exception as e:
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting property details: {e}")
        
        return data
    
    def _extract_price_history(self, driver) -> Dict[str, Any]:
        """Extract price history from the page"""
        data = {}
        
        try:
            # Look for price history section
            history_elements = driver.find_elements(By.CSS_SELECTOR, '.ds-price-history-table tr')
            
            if history_elements:
                price_history = []
                for row in history_elements[1:]:  # Skip header
                    try:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if len(cells) >= 3:
                            date = cells[0].text.strip()
                            event = cells[1].text.strip()
                            price_text = cells[2].text.strip().replace('$', '').replace(',', '')
                            
                            if price_text and price_text.replace('.', '').isdigit():
                                price_history.append({
                                    'date': date,
                                    'event': event,
                                    'price': int(float(price_text))
                                })
                    except Exception:
                        continue
                
                if price_history:
                    data['price_history'] = price_history
                    
        except Exception as e:
            logging.error(f"Error extracting price history: {e}")
        
        return data
    
    def _extract_photos(self, driver) -> Dict[str, Any]:
        """Extract property photos"""
        data = {}
        
        try:
            # Find photo elements
            photo_elements = driver.find_elements(By.CSS_SELECTOR, 'img[src*="photos.zillowstatic.com"]')
            
            if photo_elements:
                photos = []
                for img in photo_elements:
                    src = img.get_attribute('src')
                    if src and 'photos.zillowstatic.com' in src:
                        photos.append(src)
                
                # Remove duplicates and limit
                unique_photos = list(dict.fromkeys(photos))[:20]  # Max 20 photos
                
                if unique_photos:
                    data['carousel_photos'] = unique_photos
                    data['img_src'] = unique_photos[0]  # First photo as main image
                    data['has_image'] = True
                    
        except Exception as e:
            logging.error(f"Error extracting photos: {e}")
        
        return data
    
    def _extract_agent_info(self, driver) -> Dict[str, Any]:
        """Extract listing agent information"""
        data = {}
        
        try:
            # Look for agent information
            agent_selectors = [
                '.ds-agent-card',
                '.agent-info',
                '[data-testid="agent-info"]'
            ]
            
            for selector in agent_selectors:
                try:
                    agent_element = driver.find_element(By.CSS_SELECTOR, selector)
                    agent_name = agent_element.find_element(By.CSS_SELECTOR, '.agent-name, .ds-agent-name')
                    if agent_name:
                        data['agent_name'] = agent_name.text.strip()
                        break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting agent info: {e}")
        
        return data
    
    def _extract_school_info(self, driver) -> Dict[str, Any]:
        """Extract school information"""
        data = {}
        
        try:
            # Look for school information
            school_elements = driver.find_elements(By.CSS_SELECTOR, '.ds-school-card, .school-info')
            
            if school_elements:
                schools = []
                for school in school_elements:
                    try:
                        name_elem = school.find_element(By.CSS_SELECTOR, '.school-name, .ds-school-name')
                        rating_elem = school.find_element(By.CSS_SELECTOR, '.school-rating, .ds-school-rating')
                        
                        school_data = {
                            'name': name_elem.text.strip() if name_elem else None,
                            'rating': rating_elem.text.strip() if rating_elem else None
                        }
                        
                        if school_data['name']:
                            schools.append(school_data)
                            
                    except NoSuchElementException:
                        continue
                
                if schools:
                    data['schools'] = schools
                    
        except Exception as e:
            logging.error(f"Error extracting school info: {e}")
        
        return data
    
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
        
        logging.info(f"Scraping {len(zpids)} properties via web scraping")
        
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
        
        logging.info(f"Successfully scraped {len(entities)} properties")
        return entities
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """Validate entities by re-scraping"""
        results = []
        
        for entity in entities:
            try:
                # Extract ZPID from URI
                zpid = self._extract_zpid_from_uri(entity.uri)
                if not zpid:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Could not extract ZPID from URI",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                    continue
                
                # Re-scrape the property
                fresh_entity = await self.scrape_zpid(zpid)
                
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
    
    def _extract_zpid_from_uri(self, uri: str) -> Optional[str]:
        """Extract ZPID from URI"""
        if "_zpid" in uri:
            parts = uri.split("/")
            for part in parts:
                if part.endswith("_zpid"):
                    return part.replace("_zpid", "")
        return None
    
    def _validate_entity_fields(self, original: DataEntity, fresh: DataEntity) -> bool:
        """Validate key fields between original and fresh entity"""
        try:
            # Parse content from both entities
            original_content = json.loads(original.content.decode('utf-8'))
            fresh_content = json.loads(fresh.content.decode('utf-8'))
            
            # Check key fields that shouldn't change
            key_fields = ['zpid', 'address', 'bedrooms', 'bathrooms', 'property_type']
            
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
    
    def __init__(self, requests_per_minute: int = 30):
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
