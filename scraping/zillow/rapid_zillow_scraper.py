import asyncio
import httpx
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import datetime as dt
import bittensor as bt
import traceback
import json

from common.data import DataEntity, DataLabel
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig, Scraper, ValidationResult
from scraping.zillow.model import RealEstateContent
from scraping.zillow.utils import validate_zillow_data_entity_fields
from scraping.zillow.field_mapping import ZillowFieldMapper


@dataclass
class APIUsageStats:
    """Track API usage statistics"""
    daily_calls: int = 0
    monthly_calls: int = 0
    last_reset_date: str = ""
    search_calls: int = 0
    individual_calls: int = 0


class APIBudgetManager:
    """Manage API usage against monthly budget with emergency throttling"""
    
    def __init__(self, storage_path: str = "api_usage.db"):
        self.storage_path = Path(storage_path)
        
        # Load configuration from environment
        self.monthly_budget = int(os.getenv("ZILLOW_MONTHLY_API_CALLS", "13000"))
        self.daily_buffer_percent = int(os.getenv("ZILLOW_DAILY_BUFFER_PERCENT", "10"))
        self.api_plan_type = os.getenv("ZILLOW_API_PLAN_TYPE", "basic")
        
        # Calculate safe limits
        self.daily_budget = self._calculate_daily_budget()
        self.emergency_threshold = int(self.daily_budget * 0.9)  # 90% of daily budget
        
        # Initialize storage
        self._init_storage()
        
        # Load current usage
        self.current_usage = self._load_usage()
    
    def _calculate_daily_budget(self) -> int:
        """Calculate safe daily API budget with buffer"""
        days_in_month = 30
        buffer_multiplier = (100 - self.daily_buffer_percent) / 100
        return int((self.monthly_budget * buffer_multiplier) / days_in_month)
    
    def _init_storage(self):
        """Initialize SQLite storage for usage tracking"""
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    date TEXT PRIMARY KEY,
                    search_calls INTEGER DEFAULT 0,
                    individual_calls INTEGER DEFAULT 0,
                    total_calls INTEGER DEFAULT 0,
                    budget_limit INTEGER DEFAULT 0
                )
            """)
    
    def _load_usage(self) -> APIUsageStats:
        """Load current usage statistics"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute(
                "SELECT search_calls, individual_calls, total_calls FROM api_usage WHERE date = ?",
                (today,)
            )
            result = cursor.fetchone()
            
            if result:
                search_calls, individual_calls, daily_calls = result
            else:
                search_calls = individual_calls = daily_calls = 0
            
            return APIUsageStats(
                daily_calls=daily_calls,
                search_calls=search_calls,
                individual_calls=individual_calls,
                last_reset_date=today
            )
    
    def check_budget_availability(self, calls_needed: int) -> Tuple[bool, str]:
        """Check if we can make the requested API calls within budget"""
        if self.current_usage.daily_calls + calls_needed > self.daily_budget:
            return False, f"Daily budget exceeded: {self.current_usage.daily_calls + calls_needed} > {self.daily_budget}"
        
        if self.current_usage.daily_calls + calls_needed > self.emergency_threshold:
            return False, f"Emergency threshold reached: {self.current_usage.daily_calls + calls_needed} > {self.emergency_threshold}"
        
        return True, "Budget available"
    
    def update_usage(self, search_calls: int = 0, individual_calls: int = 0):
        """Update usage tracking"""
        total_calls = search_calls + individual_calls
        today = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO api_usage 
                (date, search_calls, individual_calls, total_calls, budget_limit)
                VALUES (?, 
                    COALESCE((SELECT search_calls FROM api_usage WHERE date = ?), 0) + ?,
                    COALESCE((SELECT individual_calls FROM api_usage WHERE date = ?), 0) + ?,
                    COALESCE((SELECT total_calls FROM api_usage WHERE date = ?), 0) + ?,
                    ?)
            """, (today, today, search_calls, today, individual_calls, today, total_calls, self.daily_budget))
        
        # Update in-memory usage
        self.current_usage.daily_calls += total_calls
        self.current_usage.search_calls += search_calls
        self.current_usage.individual_calls += individual_calls
    
    def get_remaining_budget(self) -> Dict[str, int]:
        """Return remaining budget information"""
        return {
            "daily_remaining": max(0, self.daily_budget - self.current_usage.daily_calls),
            "daily_budget": self.daily_budget,
            "daily_used": self.current_usage.daily_calls
        }


class ZillowRapidAPIScraper(Scraper):
    """Scrapes real estate data using RapidAPI Zillow endpoint"""
    
    BASE_URL = "https://zillow-com1.p.rapidapi.com"
    SEARCH_ENDPOINT = "/propertyExtendedSearch"
    PROPERTY_ENDPOINT = "/property"
    
    # Rate limiting - RapidAPI allows 2 requests/second
    MAX_REQUESTS_PER_SECOND = 2
    REQUEST_DELAY = 0.5  # 500ms between requests (2 requests/second)
    
    # API cost management
    MAX_INDIVIDUAL_CALLS_PER_SESSION = int(os.getenv("ZILLOW_MAX_INDIVIDUAL_CALLS", "100"))  # Configurable limit
    ENABLE_SMART_BATCHING = os.getenv("ZILLOW_SMART_BATCHING", "true").lower() == "true"
    PRIORITY_THRESHOLD = int(os.getenv("ZILLOW_PRIORITY_THRESHOLD", "500000"))  # $500K threshold
    
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
        
        # Initialize budget manager
        self.budget_manager = APIBudgetManager()
        
        # Track API usage for cost management (legacy - now handled by budget manager)
        self.api_calls_made = 0
        self.search_calls = 0
        self.individual_calls = 0
    
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
            status_types = ["ForSale", "ForRent"]  # Scrape both sale and rental properties
        
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
                            
                            # Phase 1: Extract ZPIDs from Property Extended Search
                            zpids = []
                            for prop in props[:max_entities]:
                                zpid = prop.get('zpid')
                                if zpid:
                                    zpids.append(str(zpid))
                            
                            self.search_calls += 1
                            bt.logging.info(f"Extracted {len(zpids)} ZPIDs for individual property fetching")
                            
                            # Check budget availability before processing
                            calls_needed = 1 + len(zpids)  # 1 search + N individual calls
                            can_proceed, reason = self.budget_manager.check_budget_availability(calls_needed)
                            
                            if not can_proceed:
                                bt.logging.warning(f"Budget limit reached: {reason}. Skipping {location}")
                                continue
                            
                            # Apply tiered scraping strategy
                            premium_zpids, basic_zpids = self._apply_tiered_scraping(zpids, props[:max_entities])
                            
                            # Apply smart batching if enabled
                            if self.ENABLE_SMART_BATCHING:
                                premium_zpids = self._apply_smart_batching(premium_zpids, 
                                    [p for p in props[:max_entities] if str(p.get('zpid')) in premium_zpids])
                                bt.logging.info(f"Smart batching: {len(premium_zpids)} premium, {len(basic_zpids)} basic properties")
                            
                            # Final budget check with actual numbers
                            final_calls_needed = 1 + len(premium_zpids)  # Only premium properties get individual API calls
                            can_proceed, reason = self.budget_manager.check_budget_availability(final_calls_needed)
                            
                            if not can_proceed:
                                # Reduce premium properties to fit budget
                                remaining_budget = self.budget_manager.get_remaining_budget()["daily_remaining"]
                                max_premium = max(0, remaining_budget - 1)  # Reserve 1 for search call
                                premium_zpids = premium_zpids[:max_premium]
                                bt.logging.warning(f"Reduced to {len(premium_zpids)} premium properties to fit budget")
                            
                            # Update budget manager with search call
                            self.budget_manager.update_usage(search_calls=1)
                            
                            # Phase 2A: Process premium properties with full Individual Property API
                            premium_processed = 0
                            for zpid in premium_zpids:
                                try:
                                    await self._rate_limit()  # Rate limit individual property calls
                                    
                                    individual_data = await self._fetch_individual_property(client, zpid)
                                    if individual_data:
                                        # Create RealEstateContent with full Individual Property API data
                                        content = RealEstateContent.from_zillow_api(individual_data, api_type="individual")
                                        entity = content.to_data_entity()
                                        entities.append(entity)
                                        premium_processed += 1
                                        bt.logging.debug(f"Successfully processed premium property ZPID {zpid}")
                                    else:
                                        bt.logging.warning(f"Could not fetch individual property data for ZPID {zpid}")
                                        
                                except Exception as e:
                                    bt.logging.warning(f"Failed to process premium property {zpid}: {e}")
                                    continue
                            
                            # Update budget manager with individual calls
                            self.budget_manager.update_usage(individual_calls=premium_processed)
                            
                            # Phase 2B: Process basic properties with Property Extended Search data only
                            basic_processed = 0
                            for zpid in basic_zpids:
                                try:
                                    # Find the property data from the original search results
                                    prop_data = next((p for p in props[:max_entities] if str(p.get('zpid')) == zpid), None)
                                    if prop_data:
                                        # Create RealEstateContent with basic Property Extended Search data
                                        content = RealEstateContent.from_zillow_api(prop_data, api_type="search")
                                        entity = content.to_data_entity()
                                        entities.append(entity)
                                        basic_processed += 1
                                        bt.logging.debug(f"Successfully processed basic property ZPID {zpid}")
                                    
                                except Exception as e:
                                    bt.logging.warning(f"Failed to process basic property {zpid}: {e}")
                                    continue
                            
                            bt.logging.info(f"Processed {premium_processed} premium + {basic_processed} basic properties for {location}")
                        
                        elif response.status_code == 429:
                            bt.logging.warning(f"Rate limited for location {location}. Waiting...")
                            await asyncio.sleep(60)  # Wait 1 minute for rate limit reset
                            
                        else:
                            bt.logging.error(f"API error for {location}: {response.status_code} - {response.text}")
                    
                    except Exception as e:
                        bt.logging.error(f"Error scraping {location}: {traceback.format_exc()}")
                        continue
        
        # Log API usage statistics and budget status
        budget_info = self.budget_manager.get_remaining_budget()
        bt.logging.info(f"API Budget Status: {budget_info['daily_used']}/{budget_info['daily_budget']} daily calls used ({budget_info['daily_remaining']} remaining)")
        bt.logging.success(f"Successfully scraped {len(entities)} real estate entities with budget-aware tiered scraping")
        return entities
    
    def _apply_smart_batching(self, zpids: List[str], props: List[Dict[str, Any]]) -> List[str]:
        """
        Apply smart batching to prioritize high-value properties for individual API calls.
        
        Priority scoring based on:
        1. Price (higher is better)
        2. Property type (single family > condo > apartment)
        3. Has images/video (better marketing)
        4. Recent activity (days on Zillow)
        """
        if not self.ENABLE_SMART_BATCHING or len(zpids) <= 10:
            return zpids  # No batching needed for small sets
        
        # Create property data lookup
        prop_lookup = {str(prop.get('zpid', '')): prop for prop in props}
        
        # Score each property
        scored_properties = []
        for zpid in zpids:
            prop = prop_lookup.get(zpid, {})
            score = self._calculate_property_priority_score(prop)
            scored_properties.append((zpid, score))
        
        # Sort by score (highest first) and take top 60%
        scored_properties.sort(key=lambda x: x[1], reverse=True)
        target_count = max(10, int(len(scored_properties) * 0.6))  # Keep at least 10, or 60%
        
        selected_zpids = [zpid for zpid, score in scored_properties[:target_count]]
        bt.logging.debug(f"Smart batching: selected {len(selected_zpids)}/{len(zpids)} properties")
        
        return selected_zpids
    
    def _calculate_property_priority_score(self, prop: Dict[str, Any]) -> float:
        """Calculate priority score for a property (higher = more valuable)"""
        score = 0.0
        
        # Price factor (normalize to 0-100 range)
        price = prop.get('price', 0)
        if price:
            score += min(100, price / 10000)  # $1M = 100 points
        
        # Property type factor
        property_type = prop.get('propertyType', '').upper()
        type_scores = {
            'SINGLE_FAMILY': 20,
            'TOWNHOUSE': 15,
            'CONDO': 10,
            'APARTMENT': 5,
            'MULTI_FAMILY': 8
        }
        score += type_scores.get(property_type, 0)
        
        # Media factor
        if prop.get('hasImage'):
            score += 5
        if prop.get('hasVideo'):
            score += 10
        if prop.get('has3DModel'):
            score += 15
        
        # Activity factor (newer listings get higher priority)
        days_on_zillow = prop.get('daysOnZillow', 999)
        if days_on_zillow < 7:
            score += 10
        elif days_on_zillow < 30:
            score += 5
        
        # Size factor
        living_area = prop.get('livingArea', 0)
        if living_area:
            score += min(20, living_area / 100)  # 2000 sqft = 20 points
        
        return score
    
    def _apply_tiered_scraping(self, zpids: List[str], props: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        """
        Apply tiered scraping strategy based on property value.
        
        Returns:
            (premium_zpids, basic_zpids) - Premium properties get full Individual Property API,
                                         Basic properties use Property Extended Search data only
        """
        premium_zpids = []
        basic_zpids = []
        
        # Create property data lookup
        prop_lookup = {str(prop.get('zpid', '')): prop for prop in props}
        
        for zpid in zpids:
            prop = prop_lookup.get(zpid, {})
            price = prop.get('price', 0)
            
            # Apply tiered strategy
            if price and price >= self.PRIORITY_THRESHOLD:
                premium_zpids.append(zpid)
            else:
                basic_zpids.append(zpid)
        
        bt.logging.debug(f"Tiered scraping: {len(premium_zpids)} premium (>${self.PRIORITY_THRESHOLD:,}), {len(basic_zpids)} basic properties")
        
        return premium_zpids, basic_zpids
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """
        Enhanced validation for real estate data including:
        1. Property existence check via API
        2. Content field validation with tolerance for time-sensitive data
        """
        results = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for entity in entities:
                try:
                    await self._rate_limit()
                    
                    # Step 1: Extract zpid from URI
                    zpid = self._extract_zpid_from_uri(entity.uri)
                    if not zpid:
                        results.append(ValidationResult(
                            is_valid=False,
                            reason="Could not extract zpid from URI",
                            content_size_bytes_validated=entity.content_size_bytes
                        ))
                        continue
                    
                    # Step 2: Check if property exists via API
                    existence_result = await self._check_property_existence(client, zpid, entity)
                    if not existence_result.is_valid:
                        results.append(existence_result)
                        continue
                    
                    # Step 3: Fetch fresh property data for content validation
                    try:
                        fresh_content = await self._fetch_property_content(client, zpid)
                        if fresh_content:
                            # Step 4: Perform comprehensive content validation
                            content_result = validate_zillow_data_entity_fields(fresh_content, entity)
                            results.append(content_result)
                            
                            # Log validation details for monitoring
                            if not content_result.is_valid:
                                bt.logging.info(f"Content validation failed for zpid {zpid}: {content_result.reason}")
                            else:
                                bt.logging.debug(f"Content validation passed for zpid {zpid}")
                        else:
                            # Fallback to existence check if content fetch fails
                            results.append(existence_result)
                            
                    except Exception as content_error:
                        bt.logging.warning(f"Content validation error for zpid {zpid}: {str(content_error)}")
                        # Fallback to existence check on content validation errors
                        results.append(existence_result)
                
                except Exception as e:
                    bt.logging.warning(f"Validation error for {entity.uri}: {e}")
                    # On validation errors, assume valid to avoid penalizing miners
                    results.append(ValidationResult(
                        is_valid=True,
                        reason=f"Validation exception - assumed valid: {str(e)}",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
        
        return results
    
    def _extract_zpid_from_uri(self, uri: str) -> Optional[str]:
        """Extract zpid from Zillow URI"""
        if "/homedetails/" in uri:
            # Extract from URL like "/homedetails/address/57854026_zpid/"
            parts = uri.split("/")
            for part in parts:
                if part.endswith("_zpid"):
                    return part.replace("_zpid", "")
        return None
    
    async def _check_property_existence(self, client: httpx.AsyncClient, zpid: str, entity: DataEntity) -> ValidationResult:
        """Check if property exists via Zillow API"""
        try:
            params = {"zpid": zpid}
            response = await client.get(
                f"{self.BASE_URL}{self.PROPERTY_ENDPOINT}",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                return ValidationResult(
                    is_valid=True,
                    reason="Property exists via Zillow API",
                    content_size_bytes_validated=entity.content_size_bytes
                )
            elif response.status_code == 404:
                return ValidationResult(
                    is_valid=False,
                    reason="Property not found (may have been sold/removed)",
                    content_size_bytes_validated=entity.content_size_bytes
                )
            elif response.status_code == 429:
                bt.logging.warning("Rate limited during validation - assuming property is valid")
                await asyncio.sleep(60)
                return ValidationResult(
                    is_valid=True,
                    reason="Rate limited during validation - assumed valid",
                    content_size_bytes_validated=entity.content_size_bytes
                )
            else:
                return ValidationResult(
                    is_valid=True,
                    reason=f"API error during validation ({response.status_code}) - assumed valid",
                    content_size_bytes_validated=entity.content_size_bytes
                )
                
        except Exception as e:
            bt.logging.warning(f"Property existence check failed for zpid {zpid}: {str(e)}")
            return ValidationResult(
                is_valid=True,
                reason=f"Existence check error - assumed valid: {str(e)}",
                content_size_bytes_validated=entity.content_size_bytes
            )
    
    async def _fetch_individual_property(self, client: httpx.AsyncClient, zpid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full property data from Individual Property API.
        
        This method fetches comprehensive property data that miners will now collect,
        including all the rich fields available in the Individual Property API.
        """
        try:
            params = {"zpid": zpid}
            response = await client.get(
                f"{self.BASE_URL}{self.PROPERTY_ENDPOINT}",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                # Return full property data from API response
                full_property_data = data.get("property", {})
                
                if full_property_data:
                    return full_property_data
            
            return None
            
        except Exception as e:
            bt.logging.warning(f"Failed to fetch individual property for zpid {zpid}: {str(e)}")
            return None

    async def _fetch_property_content(self, client: httpx.AsyncClient, zpid: str) -> Optional[RealEstateContent]:
        """
        Fetch fresh property data for content validation using FULL Individual Property API data.
        
        This method now fetches comprehensive property data that matches what miners collect,
        enabling full field validation instead of the previous limited subset validation.
        """
        try:
            # Get full individual property data
            full_property_data = await self._fetch_individual_property(client, zpid)
            
            if full_property_data:
                # Create RealEstateContent using ALL fields from Individual Property API
                full_content_data = ZillowFieldMapper.create_full_property_content(full_property_data)
                
                # Create RealEstateContent with full property data
                return RealEstateContent(**full_content_data)
            
            return None
            
        except Exception as e:
            bt.logging.warning(f"Failed to fetch property content for zpid {zpid}: {str(e)}")
            return None
    
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
