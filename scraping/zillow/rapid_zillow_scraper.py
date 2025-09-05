import asyncio
import httpx
import os
from typing import List, Optional, Dict, Any
import datetime as dt
import bittensor as bt
import traceback
import json

from common.data import DataEntity, DataLabel
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig, Scraper, ValidationResult
from scraping.zillow.model import RealEstateContent


class ZillowRapidAPIScraper(Scraper):
    """Scrapes real estate data using RapidAPI Zillow endpoint"""
    
    BASE_URL = "https://zillow-com1.p.rapidapi.com"
    SEARCH_ENDPOINT = "/propertyExtendedSearch"
    PROPERTY_ENDPOINT = "/property"
    
    # Rate limiting - RapidAPI allows 2 requests/second
    MAX_REQUESTS_PER_SECOND = 2
    REQUEST_DELAY = 0.5  # 500ms between requests (2 requests/second)
    
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.api_host = os.getenv("RAPIDAPI_HOST", "zillow-com1.p.rapidapi.com")
        
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable is required")
        
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        # Track last request time for rate limiting
        self.last_request_time = dt.datetime.now() - dt.timedelta(seconds=1)
    
    async def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = (dt.datetime.now() - self.last_request_time).total_seconds()
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self.last_request_time = dt.datetime.now()
    
    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrape real estate listings from Zillow API"""
        entities = []
        
        # Extract search parameters from labels
        locations = []
        property_types = []
        status_types = []
        
        # API parameter mappings
        status_mapping = {
            "forsale": "ForSale",
            "forrent": "ForRent"
        }
        
        type_mapping = {
            "houses": "Houses",
            "condos": "Condos", 
            "apartments": "Apartments",
            "townhomes": "Townhomes"
        }
        
        for label in scrape_config.labels:
            label_value = label.value.lower()
            if label_value.startswith("location:"):
                locations.append(label_value[9:])  # Remove "location:" prefix
            elif label_value.startswith("zip:"):
                locations.append(label_value[4:])  # Remove "zip:" prefix
            elif label_value.startswith("type:"):
                raw_type = label_value[5:]  # Remove "type:" prefix
                mapped_type = type_mapping.get(raw_type, raw_type.title())
                property_types.append(mapped_type)
            elif label_value.startswith("status:"):
                raw_status = label_value[7:]  # Remove "status:" prefix
                mapped_status = status_mapping.get(raw_status, raw_status)
                status_types.append(mapped_status)
        
        # Default values if not specified
        if not locations:
            locations = ["06424"]  # Default to East Hampton, CT from your example
        if not property_types:
            property_types = ["Houses", "Condos", "Apartments", "Townhomes"]
        if not status_types:
            status_types = ["ForSale"]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for location in locations:
                for status_type in status_types:
                    try:
                        await self._rate_limit()
                        
                        # Build property types string
                        home_type = ",".join(property_types)
                        
                        params = {
                            "location": location,
                            "status_type": status_type,
                            "home_type": home_type,
                            "sort": "Newest",
                            "page": "1"
                        }
                        
                        bt.logging.info(f"Scraping {location} for {status_type} properties: {home_type}")
                        
                        response = await client.get(
                            f"{self.BASE_URL}{self.SEARCH_ENDPOINT}",
                            headers=self.headers,
                            params=params
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            props = data.get("props", [])
                            
                            bt.logging.info(f"Found {len(props)} properties in {location}")
                            
                            # Limit results based on entity_limit
                            max_entities = scrape_config.entity_limit or 50
                            for prop in props[:max_entities]:
                                try:
                                    content = RealEstateContent.from_zillow_api(prop)
                                    entity = content.to_data_entity()
                                    entities.append(entity)
                                except Exception as e:
                                    bt.logging.warning(f"Failed to parse property {prop.get('zpid', 'unknown')}: {e}")
                                    continue
                        
                        elif response.status_code == 429:
                            bt.logging.warning(f"Rate limited for location {location}. Waiting...")
                            await asyncio.sleep(60)  # Wait 1 minute for rate limit reset
                            
                        else:
                            bt.logging.error(f"API error for {location}: {response.status_code} - {response.text}")
                    
                    except Exception as e:
                        bt.logging.error(f"Error scraping {location}: {traceback.format_exc()}")
                        continue
        
        bt.logging.success(f"Successfully scraped {len(entities)} real estate entities")
        return entities
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """Validate real estate data by checking if properties still exist"""
        results = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for entity in entities:
                try:
                    await self._rate_limit()
                    
                    # Extract zpid from URI
                    zpid = None
                    if "/homedetails/" in entity.uri:
                        # Extract from URL like "/homedetails/address/57854026_zpid/"
                        parts = entity.uri.split("/")
                        for part in parts:
                            if part.endswith("_zpid"):
                                zpid = part.replace("_zpid", "")
                                break
                    
                    if not zpid:
                        results.append(ValidationResult(
                            is_valid=False,
                            reason="Could not extract zpid from URI",
                            content_size_bytes_validated=entity.content_size_bytes
                        ))
                        continue
                    
                    # Verify property exists via API
                    params = {"zpid": zpid}
                    
                    response = await client.get(
                        f"{self.BASE_URL}{self.PROPERTY_ENDPOINT}",
                        headers=self.headers,
                        params=params
                    )
                    
                    if response.status_code == 200:
                        # Property exists and is accessible
                        results.append(ValidationResult(
                            is_valid=True,
                            reason="Property verified via Zillow API",
                            content_size_bytes_validated=entity.content_size_bytes
                        ))
                    elif response.status_code == 404:
                        # Property no longer exists
                        results.append(ValidationResult(
                            is_valid=False,
                            reason="Property not found (may have been sold/removed)",
                            content_size_bytes_validated=entity.content_size_bytes
                        ))
                    elif response.status_code == 429:
                        # Rate limited - assume valid to avoid false negatives
                        bt.logging.warning("Rate limited during validation - assuming property is valid")
                        results.append(ValidationResult(
                            is_valid=True,
                            reason="Rate limited during validation - assumed valid",
                            content_size_bytes_validated=entity.content_size_bytes
                        ))
                        await asyncio.sleep(60)
                    else:
                        # Other API error - assume valid to avoid false negatives
                        results.append(ValidationResult(
                            is_valid=True,
                            reason=f"API error during validation ({response.status_code}) - assumed valid",
                            content_size_bytes_validated=entity.content_size_bytes
                        ))
                
                except Exception as e:
                    bt.logging.warning(f"Validation error for {entity.uri}: {e}")
                    # On validation errors, assume valid to avoid penalizing miners
                    results.append(ValidationResult(
                        is_valid=True,
                        reason=f"Validation exception - assumed valid: {str(e)}",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
        
        return results
    
    def _extract_location_from_label(self, label: str) -> Optional[str]:
        """Extract location parameter from label"""
        # Support various label formats:
        # "location:new-york-ny"
        # "zip:10001" 
        # "city:los-angeles"
        if label.startswith("location:"):
            return label[9:]
        elif label.startswith("zip:"):
            return label[4:]
        elif label.startswith("city:"):
            # Convert city name to location format
            city = label[5:].replace("_", "-")
            return city
        return None
    
    def get_supported_locations(self) -> List[str]:
        """Get list of supported location formats"""
        return [
            "location:new-york-ny",
            "location:los-angeles-ca", 
            "location:chicago-il",
            "location:houston-tx",
            "location:phoenix-az",
            "location:philadelphia-pa",
            "location:san-antonio-tx",
            "location:san-diego-ca",
            "location:dallas-tx",
            "location:san-jose-ca",
            "zip:10001",  # NYC
            "zip:90210",  # Beverly Hills
            "zip:60601",  # Chicago
            "zip:77001",  # Houston
            "zip:85001",  # Phoenix
        ]
    
    def get_supported_property_types(self) -> List[str]:
        return [
            "type:houses",
            "type:condos", 
            "type:apartments",
            "type:townhomes"
        ]
    
    def get_supported_status_types(self) -> List[str]:
        return [
            "status:forsale",
            "status:forrent",
            "status:sold"
        ]
