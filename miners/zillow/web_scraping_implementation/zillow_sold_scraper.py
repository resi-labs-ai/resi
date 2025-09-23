"""
Zillow Sold Listings Scraper - Specialized scraper for sold listings by zipcode.
Extends EnhancedZillowScraper with sold-specific functionality.
"""

import asyncio
import json
import logging
import random
import re
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from .enhanced_zillow_miner import EnhancedZillowScraper, RateLimiter
from miners.zillow.shared.zillow_sold_schema import ZillowSoldListingContent
from miners.zillow.shared.sold_url_builder import ZillowSoldURLBuilder, SoldListingsSearchParams
from miners.zillow.shared.zipcode_utils import get_zipcode_mapper
from scraping.scraper import ScrapeConfig, ValidationResult
from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange


class ZillowSoldListingsScraper(EnhancedZillowScraper):
    """Specialized scraper for Zillow sold listings by zipcode"""
    
    def __init__(self):
        super().__init__()
        self.url_builder = ZillowSoldURLBuilder()
        self.zipcode_mapper = get_zipcode_mapper()
        
        # More conservative rate limiting for search pages
        self.rate_limiter = RateLimiter(requests_per_minute=15)
        self.max_session_requests = 8  # Restart browser more frequently
        
        # Sold listings specific settings
        self.default_max_listings_per_zipcode = 100
        self.enhance_with_property_pages = True  # Whether to visit individual property pages
        self.enhancement_sample_rate = 0.3  # Only enhance 30% of listings to save time
        
    async def scrape(self, config: ScrapeConfig) -> List[DataEntity]:
        """Main scrape method - extracts zipcodes from labels and scrapes sold listings"""
        
        try:
            # Extract zipcodes from labels
            zipcodes = self._extract_zipcodes_from_config(config)
            
            if not zipcodes:
                logging.warning("No zipcodes found in scrape config")
                return []
            
            logging.info(f"Scraping sold listings for {len(zipcodes)} zipcodes: {zipcodes}")
            
            all_entities = []
            
            for zipcode in zipcodes:
                try:
                    # Determine max listings for this zipcode
                    max_listings = min(
                        config.entity_limit // len(zipcodes),
                        self.default_max_listings_per_zipcode
                    )
                    
                    zipcode_entities = await self.scrape_zipcode_sold_listings(
                        zipcode, 
                        max_listings
                    )
                    
                    all_entities.extend(zipcode_entities)
                    
                    # Rate limiting between zipcodes
                    if len(zipcodes) > 1:
                        await asyncio.sleep(random.uniform(3, 7))
                    
                except Exception as e:
                    logging.error(f"Error scraping zipcode {zipcode}: {e}")
                    continue
            
            logging.info(f"Successfully scraped {len(all_entities)} sold listings")
            return all_entities[:config.entity_limit]
            
        except Exception as e:
            logging.error(f"Error in sold listings scraper: {e}")
            return []
    
    def _extract_zipcodes_from_config(self, config: ScrapeConfig) -> List[str]:
        """Extract zipcodes from ScrapeConfig labels"""
        zipcodes = []
        
        for label in config.labels:
            if label.value.startswith("zip:"):
                zipcode = label.value[4:]  # Remove "zip:" prefix
                if self.zipcode_mapper.validate_zipcode(zipcode):
                    zipcodes.append(zipcode)
                else:
                    logging.warning(f"Invalid zipcode format: {zipcode}")
        
        return zipcodes
    
    async def scrape_zipcode_sold_listings(
        self, 
        zipcode: str, 
        max_listings: int = 100
    ) -> List[DataEntity]:
        """Scrape sold listings for a specific zipcode"""
        
        logging.info(f"Scraping sold listings for zipcode {zipcode}, max {max_listings} listings")
        
        try:
            # Get total results and determine pagination strategy
            page_1_url = await self.url_builder.build_sold_listings_url(zipcode, 1)
            if not page_1_url:
                logging.error(f"Could not build URL for zipcode {zipcode}")
                return []
            
            # Scrape first page and get total results
            await self._ensure_driver()
            await self.rate_limiter.wait_if_needed()
            
            first_page_data = await self._scrape_sold_listings_page(
                page_1_url, zipcode, 1
            )
            
            if not first_page_data:
                logging.warning(f"No data found on first page for zipcode {zipcode}")
                return []
            
            all_listings = first_page_data["listings"]
            total_results = first_page_data["total_results"]
            
            logging.info(f"Zipcode {zipcode}: Found {total_results} total sold listings, "
                        f"got {len(all_listings)} from page 1")
            
            # Determine if we need more pages
            if len(all_listings) < max_listings and total_results > len(all_listings):
                additional_pages = await self._scrape_additional_pages(
                    zipcode, 
                    total_results,
                    max_listings - len(all_listings),
                    len(all_listings)  # listings per page
                )
                all_listings.extend(additional_pages)
            
            # Limit results
            all_listings = all_listings[:max_listings]
            
            # Enhance selected listings with property page data
            if self.enhance_with_property_pages and all_listings:
                enhanced_listings = await self._enhance_selected_listings(all_listings)
                all_listings = enhanced_listings
            
            # Convert to DataEntity objects
            entities = []
            for listing in all_listings:
                try:
                    entity = listing.to_data_entity()
                    entities.append(entity)
                except Exception as e:
                    logging.error(f"Error converting listing to DataEntity: {e}")
                    continue
            
            logging.info(f"Successfully processed {len(entities)} sold listings for zipcode {zipcode}")
            return entities
            
        except Exception as e:
            logging.error(f"Error scraping zipcode {zipcode}: {e}")
            return []
    
    async def _scrape_sold_listings_page(
        self, 
        page_url: str, 
        zipcode: str, 
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single sold listings page"""
        
        try:
            logging.debug(f"Scraping sold listings page: {page_url}")
            
            self.driver.get(page_url)
            
            # Wait for listings to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="property-card"]'))
                )
            except TimeoutException:
                # Try alternative selectors
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.ListItem-c11n-8-84-3'))
                    )
                except TimeoutException:
                    logging.warning(f"No property cards found on page {page_url}")
                    return None
            
            # Extract total results count
            total_results = self._extract_total_results()
            
            # Extract listing cards
            listings = await self._extract_listing_cards_from_page(zipcode, page_number)
            
            return {
                "listings": listings,
                "total_results": total_results,
                "page_number": page_number,
                "zipcode": zipcode
            }
            
        except Exception as e:
            logging.error(f"Error scraping page {page_url}: {e}")
            return None
    
    def _extract_total_results(self) -> Optional[int]:
        """Extract total results count from page"""
        
        try:
            # Look for text like "595 results"
            result_selectors = [
                'h1[data-testid="search-title"]',
                '.search-title',
                'h1:contains("results")',
                '[data-testid="total-results"]',
                '.result-count'
            ]
            
            for selector in result_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.lower()
                        # Look for patterns like "595 results" or "1,234 recently sold homes"
                        match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:results|homes)', text)
                        if match:
                            count_str = match.group(1).replace(',', '')
                            return int(count_str)
                except:
                    continue
            
            # Try extracting from page source
            page_source = self.driver.page_source
            match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:results|recently sold homes)', 
                            page_source, re.IGNORECASE)
            if match:
                count_str = match.group(1).replace(',', '')
                return int(count_str)
            
        except Exception as e:
            logging.debug(f"Error extracting total results: {e}")
        
        return None
    
    async def _extract_listing_cards_from_page(
        self, 
        zipcode: str, 
        page_number: int
    ) -> List[ZillowSoldListingContent]:
        """Extract sold listing data from property cards on current page"""
        
        listings = []
        
        try:
            # Find property cards using multiple selectors
            card_selectors = [
                '[data-testid="property-card"]',
                '.ListItem-c11n-8-84-3',
                '.list-card',
                '.property-card'
            ]
            
            property_cards = []
            for selector in card_selectors:
                cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    property_cards = cards
                    logging.debug(f"Found {len(cards)} property cards using selector: {selector}")
                    break
            
            if not property_cards:
                logging.warning(f"No property cards found on page {page_number}")
                return listings
            
            for i, card in enumerate(property_cards):
                try:
                    listing_data = await self._extract_card_data(card, zipcode, page_number)
                    if listing_data:
                        listings.append(listing_data)
                    
                    # Small delay between cards
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logging.debug(f"Error extracting card {i}: {e}")
                    continue
            
            logging.info(f"Extracted {len(listings)} listings from page {page_number}")
            
        except Exception as e:
            logging.error(f"Error extracting listing cards: {e}")
        
        return listings
    
    async def _extract_card_data(
        self, 
        card_element, 
        zipcode: str, 
        page_number: int
    ) -> Optional[ZillowSoldListingContent]:
        """Extract data from a single property card"""
        
        try:
            card_data = {}
            
            # Extract address
            address_selectors = [
                '[data-testid="property-card-addr"]',
                '.list-card-addr',
                '.property-address',
                'address'
            ]
            address = self._extract_text_by_selectors(card_element, address_selectors)
            if address:
                card_data["address"] = address.strip()
            
            # Extract price (sale price)
            price_selectors = [
                '[data-testid="property-card-price"]',
                '.list-card-price',
                '.property-price',
                '.price'
            ]
            price_text = self._extract_text_by_selectors(card_element, price_selectors)
            if price_text:
                price = self._parse_price(price_text)
                if price:
                    card_data["sale_price"] = price
            
            # Extract property details (beds, baths, sqft)
            details_selectors = [
                '[data-testid="property-card-details"]',
                '.list-card-details',
                '.property-details'
            ]
            details_text = self._extract_text_by_selectors(card_element, details_selectors)
            if details_text:
                details = self._parse_property_details(details_text)
                card_data.update(details)
            
            # Extract ZPID from link
            link_selectors = ['a[href*="homedetails"]', 'a[href*="zpid"]']
            zpid = self._extract_zpid_from_card(card_element, link_selectors)
            if zpid:
                card_data["zpid"] = zpid
            
            # Extract primary photo
            img_selectors = ['img', '[data-testid="property-card-img"]']
            img_url = self._extract_image_url(card_element, img_selectors)
            if img_url:
                card_data["primary_photo"] = img_url
            
            # Extract sale date if visible
            date_selectors = ['.list-card-date', '.sold-date', '.sale-date']
            sale_date = self._extract_text_by_selectors(card_element, date_selectors)
            if sale_date:
                card_data["sale_date"] = sale_date.strip()
            
            # Set source URL
            if zpid:
                card_data["source_url"] = f"https://www.zillow.com/homedetails/{zpid}_zpid/"
            
            # Create ZillowSoldListingContent object
            if card_data.get("address") and (card_data.get("sale_price") or card_data.get("zpid")):
                return ZillowSoldListingContent.from_listing_card(
                    card_data=card_data,
                    zipcode=zipcode,
                    page_number=page_number
                )
            
        except Exception as e:
            logging.debug(f"Error extracting card data: {e}")
        
        return None
    
    def _extract_text_by_selectors(self, parent_element, selectors: List[str]) -> Optional[str]:
        """Extract text using multiple CSS selectors"""
        for selector in selectors:
            try:
                element = parent_element.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
            except:
                continue
        return None
    
    def _extract_zpid_from_card(self, card_element, link_selectors: List[str]) -> Optional[str]:
        """Extract ZPID from property card links"""
        for selector in link_selectors:
            try:
                link_element = card_element.find_element(By.CSS_SELECTOR, selector)
                href = link_element.get_attribute('href')
                if href:
                    # Extract ZPID from URL like "/homedetails/123456_zpid/"
                    match = re.search(r'/(\d+)_zpid/', href)
                    if match:
                        return match.group(1)
            except:
                continue
        return None
    
    def _extract_image_url(self, card_element, img_selectors: List[str]) -> Optional[str]:
        """Extract primary image URL"""
        for selector in img_selectors:
            try:
                img_element = card_element.find_element(By.CSS_SELECTOR, selector)
                src = img_element.get_attribute('src')
                if src and 'http' in src:
                    return src
            except:
                continue
        return None
    
    def _parse_price(self, price_text: str) -> Optional[int]:
        """Parse price text to integer"""
        try:
            # Remove currency symbols and commas
            clean_price = re.sub(r'[^\d]', '', price_text)
            if clean_price:
                return int(clean_price)
        except:
            pass
        return None
    
    def _parse_property_details(self, details_text: str) -> Dict[str, Any]:
        """Parse property details like '3 bd, 2 ba, 1,500 sqft'"""
        details = {}
        
        try:
            # Extract bedrooms
            bed_match = re.search(r'(\d+)\s*bd', details_text, re.IGNORECASE)
            if bed_match:
                details["bedrooms"] = int(bed_match.group(1))
            
            # Extract bathrooms
            bath_match = re.search(r'(\d+(?:\.\d+)?)\s*ba', details_text, re.IGNORECASE)
            if bath_match:
                details["bathrooms"] = float(bath_match.group(1))
            
            # Extract square feet
            sqft_match = re.search(r'([\d,]+)\s*sqft', details_text, re.IGNORECASE)
            if sqft_match:
                sqft_str = sqft_match.group(1).replace(',', '')
                details["square_feet"] = int(sqft_str)
        
        except Exception as e:
            logging.debug(f"Error parsing property details '{details_text}': {e}")
        
        return details
    
    async def _scrape_additional_pages(
        self, 
        zipcode: str, 
        total_results: int,
        remaining_needed: int,
        listings_per_page: int
    ) -> List[ZillowSoldListingContent]:
        """Scrape additional pages to reach desired listing count"""
        
        additional_listings = []
        
        try:
            # Calculate pages needed
            pages_needed = min(
                (remaining_needed // listings_per_page) + 1,
                5  # Limit to 5 additional pages for performance
            )
            
            logging.info(f"Scraping {pages_needed} additional pages for zipcode {zipcode}")
            
            for page_num in range(2, pages_needed + 2):  # Start from page 2
                try:
                    page_url = await self.url_builder.build_sold_listings_url(zipcode, page_num)
                    if not page_url:
                        break
                    
                    await self.rate_limiter.wait_if_needed()
                    
                    page_data = await self._scrape_sold_listings_page(
                        page_url, zipcode, page_num
                    )
                    
                    if page_data and page_data["listings"]:
                        additional_listings.extend(page_data["listings"])
                        logging.debug(f"Page {page_num}: Added {len(page_data['listings'])} listings")
                        
                        # Stop if we have enough
                        if len(additional_listings) >= remaining_needed:
                            break
                    else:
                        logging.debug(f"Page {page_num}: No listings found, stopping pagination")
                        break
                    
                    # Random delay between pages
                    await asyncio.sleep(random.uniform(2, 5))
                    
                except Exception as e:
                    logging.error(f"Error scraping page {page_num} for zipcode {zipcode}: {e}")
                    break
        
        except Exception as e:
            logging.error(f"Error in additional pages scraping: {e}")
        
        return additional_listings[:remaining_needed]
    
    async def _enhance_selected_listings(
        self, 
        listings: List[ZillowSoldListingContent]
    ) -> List[ZillowSoldListingContent]:
        """Enhance selected listings with individual property page data"""
        
        if not listings:
            return listings
        
        # Select listings to enhance based on sample rate
        sample_size = max(1, int(len(listings) * self.enhancement_sample_rate))
        selected_listings = random.sample(listings, min(sample_size, len(listings)))
        
        logging.info(f"Enhancing {len(selected_listings)} out of {len(listings)} listings")
        
        enhanced_listings = []
        
        for listing in listings:
            if listing in selected_listings and listing.zpid:
                try:
                    # Get enhanced data from individual property page
                    property_url = f"https://www.zillow.com/homedetails/{listing.zpid}_zpid/"
                    
                    await self.rate_limiter.wait_if_needed()
                    enhanced_data = await self._scrape_individual_property_basic(property_url)
                    
                    if enhanced_data:
                        enhanced_listing = ZillowSoldListingContent.enhance_with_property_data(
                            listing, enhanced_data
                        )
                        enhanced_listings.append(enhanced_listing)
                    else:
                        enhanced_listings.append(listing)
                    
                    await asyncio.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    logging.debug(f"Error enhancing listing {listing.zpid}: {e}")
                    enhanced_listings.append(listing)
            else:
                enhanced_listings.append(listing)
        
        return enhanced_listings
    
    async def _scrape_individual_property_basic(self, property_url: str) -> Optional[Dict[str, Any]]:
        """Basic property page scraping for enhancement data"""
        
        try:
            self.driver.get(property_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            enhanced_data = {}
            
            # Extract key fields that are commonly available
            try:
                # Zestimate
                zestimate_selectors = ['[data-testid="zestimate-value"]', '.zestimate-value']
                zestimate_text = self._extract_text_by_selectors(self.driver, zestimate_selectors)
                if zestimate_text:
                    zestimate = self._parse_price(zestimate_text)
                    if zestimate:
                        enhanced_data["zestimate"] = zestimate
                
                # Agent information
                agent_selectors = ['.agent-name', '[data-testid="agent-name"]']
                agent_name = self._extract_text_by_selectors(self.driver, agent_selectors)
                if agent_name:
                    enhanced_data["agent_name"] = agent_name.strip()
                
                # Year built
                year_selectors = ['[data-testid="year-built"]', '.year-built']
                year_text = self._extract_text_by_selectors(self.driver, year_selectors)
                if year_text:
                    year_match = re.search(r'\d{4}', year_text)
                    if year_match:
                        enhanced_data["year_built"] = int(year_match.group())
                
            except Exception as e:
                logging.debug(f"Error extracting enhanced data: {e}")
            
            return enhanced_data if enhanced_data else None
            
        except Exception as e:
            logging.debug(f"Error scraping individual property {property_url}: {e}")
            return None
    
    def validate(self, entities: List[DataEntity]) -> ValidationResult:
        """Validate scraped sold listings data"""
        
        if not entities:
            return ValidationResult(
                is_valid=False,
                reason="No entities scraped"
            )
        
        # Check that entities are from ZILLOW_SOLD source
        valid_entities = [
            e for e in entities 
            if e.source == DataSource.ZILLOW_SOLD
        ]
        
        if len(valid_entities) != len(entities):
            return ValidationResult(
                is_valid=False,
                reason=f"Found {len(entities) - len(valid_entities)} entities with wrong DataSource"
            )
        
        # Validate that entities have proper zipcode labels
        entities_with_zip_labels = [
            e for e in entities
            if e.label and e.label.value.startswith("zip:")
        ]
        
        if len(entities_with_zip_labels) < len(entities) * 0.8:  # Allow some flexibility
            return ValidationResult(
                is_valid=False,
                reason="Too few entities have proper zipcode labels"
            )
        
        return ValidationResult(is_valid=True)


# Rate limiter class (if not already imported)
class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0
    
    async def wait_if_needed(self):
        """Wait if necessary to maintain rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
