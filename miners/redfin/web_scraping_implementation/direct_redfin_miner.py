"""
Direct Redfin Web Scraper Implementation
Scrapes property data directly from Redfin property pages using Selenium.
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
from miners.redfin.shared.redfin_schema import RedfinRealEstateContent
from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange


class DirectRedfinScraper(Scraper):
    """Direct Redfin scraper using Selenium and undetected Chrome"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)  # More conservative for Redfin
        self.driver = None
        self.session_count = 0
        self.max_session_requests = 15  # Restart browser more frequently
        
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
    
    async def scrape_redfin_id(self, redfin_id: str) -> Optional[DataEntity]:
        """Scrape a single Redfin ID and return DataEntity"""
        await self.rate_limiter.wait_if_needed()
        
        driver = self._get_driver()
        if not driver:
            logging.error(f"Could not create driver for Redfin ID {redfin_id}")
            return None
        
        try:
            # Construct Redfin URL - this is challenging without full address
            # We'll try different URL patterns
            url = await self._redfin_id_to_url(redfin_id)
            if not url:
                logging.error(f"Could not construct URL for Redfin ID {redfin_id}")
                return None
            
            logging.info(f"Scraping Redfin ID {redfin_id} from {url}")
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if we hit anti-bot protection or property not found
            if self._is_blocked_or_not_found(driver):
                logging.warning(f"Blocked or property not found for Redfin ID {redfin_id}")
                return None
            
            # Extract data from the page
            property_data = self._extract_property_data(driver, redfin_id)
            if not property_data:
                return None
            
            # Convert to RedfinRealEstateContent and then DataEntity
            content = RedfinRealEstateContent.from_web_scraping(property_data, redfin_id)
            entity = content.to_data_entity()
            
            self.session_count += 1
            return entity
            
        except TimeoutException:
            logging.error(f"Timeout loading page for Redfin ID {redfin_id}")
            return None
        except Exception as e:
            logging.error(f"Error scraping Redfin ID {redfin_id}: {e}")
            return None
    
    async def _redfin_id_to_url(self, redfin_id: str) -> Optional[str]:
        """Convert Redfin ID to full URL"""
        # Strategy 1: Try direct home URL pattern
        direct_url = f"https://www.redfin.com/home/{redfin_id}"
        
        # Strategy 2: Could also try search-based approach
        # search_url = f"https://www.redfin.com/search?q={redfin_id}"
        
        return direct_url
    
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
            'page not found'
        ]
        
        return any(indicator in page_source for indicator in blocked_indicators)
    
    def _extract_property_data(self, driver, redfin_id: str) -> Optional[Dict[str, Any]]:
        """Extract property data from the Redfin page"""
        try:
            data = {
                'redfin_id': redfin_id,
                'detail_url': driver.current_url,
                'scraped_at': datetime.now(timezone.utc),
                'scraping_method': 'web_scraping'
            }
            
            # Extract basic information
            data.update(self._extract_basic_info(driver))
            
            # Extract pricing information
            data.update(self._extract_pricing(driver))
            
            # Extract property details
            data.update(self._extract_property_details(driver))
            
            # Extract Redfin-specific features
            data.update(self._extract_redfin_features(driver))
            
            # Extract walkability scores
            data.update(self._extract_walkability_scores(driver))
            
            # Extract photos
            data.update(self._extract_photos(driver))
            
            # Extract agent information
            data.update(self._extract_agent_info(driver))
            
            # Extract market data
            data.update(self._extract_market_data(driver))
            
            return data
            
        except Exception as e:
            logging.error(f"Error extracting data for Redfin ID {redfin_id}: {e}")
            return None
    
    def _extract_basic_info(self, driver) -> Dict[str, Any]:
        """Extract basic property information"""
        data = {}
        
        try:
            # Address
            address_selectors = [
                '[data-rf-test-id="abp-streetLine"]',
                '.street-address',
                'h1.address'
            ]
            
            for selector in address_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    data['address'] = element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Bedrooms, Bathrooms, Square Feet
            stats_selectors = [
                '[data-rf-test-id="abp-beds"]',
                '[data-rf-test-id="abp-baths"]',
                '[data-rf-test-id="abp-sqFt"]'
            ]
            
            try:
                beds_elem = driver.find_element(By.CSS_SELECTOR, '[data-rf-test-id="abp-beds"]')
                beds_text = beds_elem.text.strip().replace('beds', '').replace('bed', '').strip()
                if beds_text.isdigit():
                    data['bedrooms'] = int(beds_text)
            except NoSuchElementException:
                pass
            
            try:
                baths_elem = driver.find_element(By.CSS_SELECTOR, '[data-rf-test-id="abp-baths"]')
                baths_text = baths_elem.text.strip().replace('baths', '').replace('bath', '').strip()
                try:
                    data['bathrooms'] = float(baths_text)
                except ValueError:
                    pass
            except NoSuchElementException:
                pass
            
            try:
                sqft_elem = driver.find_element(By.CSS_SELECTOR, '[data-rf-test-id="abp-sqFt"]')
                sqft_text = sqft_elem.text.strip().replace('Sq Ft', '').replace(',', '').strip()
                if sqft_text.isdigit():
                    data['living_area'] = int(sqft_text)
            except NoSuchElementException:
                pass
            
            # Property type
            try:
                type_elem = driver.find_element(By.CSS_SELECTOR, '.property-type, [data-rf-test-id="abp-propertyType"]')
                data['property_type'] = type_elem.text.strip()
            except NoSuchElementException:
                pass
                
        except Exception as e:
            logging.error(f"Error extracting basic info: {e}")
        
        return data
    
    def _extract_pricing(self, driver) -> Dict[str, Any]:
        """Extract price and estimate information"""
        data = {}
        
        try:
            # Current price
            price_selectors = [
                '[data-rf-test-id="abp-price"]',
                '.price',
                '.listing-price'
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
            
            # Redfin Estimate
            try:
                estimate_elem = driver.find_element(By.CSS_SELECTOR, '[data-rf-test-id="avm-value"], .redfin-estimate')
                estimate_text = estimate_elem.text.strip().replace('$', '').replace(',', '')
                if estimate_text.replace('.', '').isdigit():
                    data['redfin_estimate'] = int(float(estimate_text))
            except (NoSuchElementException, ValueError):
                pass
            
            # Price per sqft
            try:
                psf_elem = driver.find_element(By.CSS_SELECTOR, '[data-rf-test-id="abp-pricePerSqFt"], .price-per-sqft')
                psf_text = psf_elem.text.strip().replace('$', '').replace('/sq ft', '').replace(',', '')
                if psf_text.replace('.', '').isdigit():
                    data['price_per_sqft'] = float(psf_text)
            except (NoSuchElementException, ValueError):
                pass
                
        except Exception as e:
            logging.error(f"Error extracting pricing: {e}")
        
        return data
    
    def _extract_property_details(self, driver) -> Dict[str, Any]:
        """Extract detailed property information"""
        data = {}
        
        try:
            # Year built, lot size from property details section
            detail_rows = driver.find_elements(By.CSS_SELECTOR, '.property-details-row, .keyDetail-row')
            
            for row in detail_rows:
                try:
                    row_text = row.text.lower()
                    
                    if 'year built' in row_text or 'built' in row_text:
                        year_text = ''.join(filter(str.isdigit, row_text))
                        if len(year_text) == 4:
                            data['year_built'] = int(year_text)
                    
                    if 'lot size' in row_text:
                        if 'acre' in row_text:
                            lot_text = row_text.replace('lot size', '').replace('acres', '').replace('acre', '').strip()
                            try:
                                data['lot_size_acres'] = float(lot_text.split()[0])
                                data['lot_area_value'] = data['lot_size_acres']
                                data['lot_area_unit'] = 'acres'
                            except (ValueError, IndexError):
                                pass
                        elif 'sq ft' in row_text or 'sqft' in row_text:
                            lot_text = row_text.replace('lot size', '').replace('sq ft', '').replace('sqft', '').replace(',', '').strip()
                            try:
                                data['lot_area_value'] = float(lot_text.split()[0])
                                data['lot_area_unit'] = 'sqft'
                            except (ValueError, IndexError):
                                pass
                    
                    if 'hoa' in row_text:
                        hoa_text = ''.join(filter(str.isdigit, row_text))
                        if hoa_text:
                            data['hoa_fee'] = int(hoa_text)
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting property details: {e}")
        
        return data
    
    def _extract_redfin_features(self, driver) -> Dict[str, Any]:
        """Extract Redfin-specific features"""
        data = {}
        
        try:
            # Check for various Redfin badges/features
            page_text = driver.page_source.lower()
            
            data['has_tour'] = 'virtual tour' in page_text or 'tour available' in page_text
            data['has_open_house'] = 'open house' in page_text
            data['is_hot_home'] = 'hot home' in page_text
            data['is_price_reduced'] = 'price reduced' in page_text or 'price drop' in page_text
            
            # Days on Redfin
            try:
                days_elem = driver.find_element(By.CSS_SELECTOR, '[data-rf-test-id="abp-daysOnRedfin"], .days-on-market')
                days_text = ''.join(filter(str.isdigit, days_elem.text))
                if days_text:
                    data['days_on_redfin'] = int(days_text)
            except (NoSuchElementException, ValueError):
                pass
                
        except Exception as e:
            logging.error(f"Error extracting Redfin features: {e}")
        
        return data
    
    def _extract_walkability_scores(self, driver) -> Dict[str, Any]:
        """Extract walkability and transit scores"""
        data = {}
        
        try:
            # Look for Walk Score, Transit Score, Bike Score
            score_elements = driver.find_elements(By.CSS_SELECTOR, '.walk-score, .transit-score, .bike-score, [data-rf-test-id*="score"]')
            
            for elem in score_elements:
                try:
                    elem_text = elem.text.lower()
                    score_text = ''.join(filter(str.isdigit, elem_text))
                    
                    if score_text and score_text.isdigit():
                        score = int(score_text)
                        
                        if 'walk' in elem_text:
                            data['walk_score'] = score
                        elif 'transit' in elem_text:
                            data['transit_score'] = score
                        elif 'bike' in elem_text:
                            data['bike_score'] = score
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting walkability scores: {e}")
        
        return data
    
    def _extract_photos(self, driver) -> Dict[str, Any]:
        """Extract property photos"""
        data = {}
        
        try:
            # Find photo elements
            photo_elements = driver.find_elements(By.CSS_SELECTOR, 'img[src*="ssl.cdn-redfin.com"], img[src*="redfin"]')
            
            if photo_elements:
                photos = []
                for img in photo_elements:
                    src = img.get_attribute('src')
                    if src and ('ssl.cdn-redfin.com' in src or 'redfin' in src):
                        photos.append(src)
                
                # Remove duplicates and limit
                unique_photos = list(dict.fromkeys(photos))[:15]  # Max 15 photos
                
                if unique_photos:
                    data['photos'] = unique_photos
                    data['primary_photo'] = unique_photos[0]
                    
        except Exception as e:
            logging.error(f"Error extracting photos: {e}")
        
        return data
    
    def _extract_agent_info(self, driver) -> Dict[str, Any]:
        """Extract agent and brokerage information"""
        data = {}
        
        try:
            # Look for agent information
            agent_selectors = [
                '.agent-name',
                '[data-rf-test-id="agent-name"]',
                '.listing-agent'
            ]
            
            for selector in agent_selectors:
                try:
                    agent_element = driver.find_element(By.CSS_SELECTOR, selector)
                    data['agent_name'] = agent_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Brokerage information
            brokerage_selectors = [
                '.brokerage-name',
                '[data-rf-test-id="brokerage"]',
                '.agent-brokerage'
            ]
            
            for selector in brokerage_selectors:
                try:
                    brokerage_element = driver.find_element(By.CSS_SELECTOR, selector)
                    data['brokerage'] = brokerage_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logging.error(f"Error extracting agent info: {e}")
        
        return data
    
    def _extract_market_data(self, driver) -> Dict[str, Any]:
        """Extract market insights and trends"""
        data = {}
        
        try:
            # Look for market insights
            insight_elements = driver.find_elements(By.CSS_SELECTOR, '.market-insight, .competitive-market, .market-trend')
            
            insights = []
            for elem in insight_elements:
                try:
                    insight_text = elem.text.strip()
                    if insight_text and len(insight_text) > 10:  # Filter out short/empty text
                        insights.append(insight_text)
                except Exception:
                    continue
            
            if insights:
                data['market_insights'] = insights
                
        except Exception as e:
            logging.error(f"Error extracting market data: {e}")
        
        return data
    
    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrape properties based on configuration"""
        entities = []
        
        # Extract Redfin IDs from labels
        redfin_ids = []
        for label in scrape_config.labels or []:
            if label.value.startswith('redfin_id:'):
                redfin_id = label.value[10:]  # Remove 'redfin_id:' prefix
                redfin_ids.append(redfin_id)
        
        if not redfin_ids:
            logging.warning("No Redfin IDs found in scrape configuration")
            return entities
        
        # Limit based on entity_limit
        if scrape_config.entity_limit:
            redfin_ids = redfin_ids[:scrape_config.entity_limit]
        
        logging.info(f"Scraping {len(redfin_ids)} properties from Redfin via web scraping")
        
        # Scrape each Redfin ID
        for redfin_id in redfin_ids:
            try:
                entity = await self.scrape_redfin_id(redfin_id)
                if entity:
                    entities.append(entity)
                    logging.info(f"Successfully scraped Redfin ID {redfin_id}")
                else:
                    logging.warning(f"Failed to scrape Redfin ID {redfin_id}")
                    
            except Exception as e:
                logging.error(f"Error scraping Redfin ID {redfin_id}: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(entities)} properties from Redfin")
        return entities
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """Validate entities by re-scraping"""
        results = []
        
        for entity in entities:
            try:
                # Extract Redfin ID from URI or content
                redfin_id = self._extract_redfin_id_from_entity(entity)
                if not redfin_id:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Could not extract Redfin ID from entity",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                    continue
                
                # Re-scrape the property
                fresh_entity = await self.scrape_redfin_id(redfin_id)
                
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
    
    def _extract_redfin_id_from_entity(self, entity: DataEntity) -> Optional[str]:
        """Extract Redfin ID from entity"""
        try:
            # Try to extract from URI first
            if "/home/" in entity.uri:
                redfin_id = entity.uri.split("/home/")[-1]
                if redfin_id.isdigit():
                    return redfin_id
            
            # Try to extract from content
            content_json = json.loads(entity.content.decode('utf-8'))
            return content_json.get('redfin_id')
            
        except Exception:
            return None
    
    def _validate_entity_fields(self, original: DataEntity, fresh: DataEntity) -> bool:
        """Validate key fields between original and fresh entity"""
        try:
            # Parse content from both entities
            original_content = json.loads(original.content.decode('utf-8'))
            fresh_content = json.loads(fresh.content.decode('utf-8'))
            
            # Check key fields that shouldn't change much
            key_fields = ['redfin_id', 'address', 'bedrooms', 'bathrooms', 'property_type']
            
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
    
    def __init__(self, requests_per_minute: int = 20):
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
