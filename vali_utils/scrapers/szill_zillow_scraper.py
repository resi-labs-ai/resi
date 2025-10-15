import asyncio
import bittensor as bt
import datetime as dt
from typing import List, Optional, Union
import traceback
import random
import json

from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig, Scraper, ValidationResult
from scraping.custom.schema import PropertyDataSchema
from scraping.custom.model import RealEstateContent
from vali_utils.utils import normalize_address, normalize_property_type

# Import the szill library from the moved location
try:
    from .szill import get_from_home_id, get_from_home_url
    from .szill.utils import parse_proxy
    SZILL_AVAILABLE = True
except ImportError as e:
    bt.logging.error(f"Szill library not available: {e}")
    SZILL_AVAILABLE = False


class SzillZillowScraper(Scraper):
    """Scraper using the szill library with concurrent processing and ScrapingBee integration."""

    def __init__(
        self, 
        proxy_url: Optional[str] = None, 
        use_scrapingbee: bool = False,
        max_concurrent: int = 5
    ):
        if not SZILL_AVAILABLE:
            raise ImportError("Szill library not available.")
        
        self.proxy_url = proxy_url
        self.use_scrapingbee = use_scrapingbee
        self.max_concurrent = max_concurrent
        
        # Configuration for concurrent processing
        self.min_delay_seconds = 1.0
        self.max_delay_seconds = 3.0
        self.request_timeout = 120
        self.max_retries = 3
        self.enable_fallback = True

        # Semaphore for controlling concurrent requests
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        bt.logging.info(
            f"Szill Zillow scraper initialized with {max_concurrent} concurrent requests, "
            f"ScrapingBee: {use_scrapingbee}, Proxy: {bool(proxy_url)}"
        )

    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrape method implementation."""
        return []

    async def validate(self, entities: Union[DataEntity, List[DataEntity]]) -> Union[ValidationResult, List[ValidationResult]]:
        """Validate DataEntity(ies) using the szill scraper with concurrent processing."""
        if not SZILL_AVAILABLE:
            error_result = ValidationResult(
                is_valid=False,
                reason="Szill library not available for validation",
                content_size_bytes_validated=0,
            )
            if isinstance(entities, list):
                return [error_result for _ in entities]
            return error_result

        # Handle single entity
        if isinstance(entities, DataEntity):
            return await self._validate_single_entity_with_semaphore(entities)

        # Handle list of entities with concurrent processing
        if not entities:
            return []
            
        bt.logging.info(
            f"Starting concurrent validation of {len(entities)} entities "
            f"({self.max_concurrent} concurrent requests)"
        )
        
        # Create validation tasks with semaphore control and random delays
        import random
        tasks = []
        for i, entity in enumerate(entities):
            delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
            tasks.append(self._validate_single_entity_with_delay(entity, delay))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to validation results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                bt.logging.error(f"Error validating entity {i+1}: {str(result)}")
                final_results.append(ValidationResult(
                    is_valid=False,
                    reason=f"Validation error: {str(result)}",
                    content_size_bytes_validated=entities[i].content_size_bytes,
                ))
            else:
                final_results.append(result)

        # Log summary
        valid_count = sum(1 for r in final_results if r.is_valid)
        bt.logging.info(
            f"Completed concurrent validation: {valid_count}/{len(entities)} valid"
        )
        
        return final_results

    async def _validate_single_entity_with_semaphore(
        self,
        entity: DataEntity
    ) -> ValidationResult:
        """Validate single entity with semaphore for concurrency control."""
        async with self.semaphore:
            return await self._validate_single_entity(entity)

    async def _validate_single_entity_with_delay(
        self,
        entity: DataEntity,
        delay: float
    ) -> ValidationResult:
        """Validate single entity with random delay for human-like behavior."""
        # Add random delay before processing
        await asyncio.sleep(delay)
        return await self._validate_single_entity_with_semaphore(entity)

    async def _validate_single_entity(self, entity: DataEntity) -> ValidationResult:
        """Validate a single DataEntity using the szill scraper."""
        try:
            # Extract zpid from the entity URI
            zpid = self._extract_zpid_from_uri(entity.uri)
            if not zpid:
                return ValidationResult(
                    is_valid=False,
                    reason="Could not extract zpid from URI",
                    content_size_bytes_validated=entity.content_size_bytes,
                )

            # Use szill to fetch fresh property data with timeout
            fresh_data = await asyncio.wait_for(
                self._fetch_property_with_szill(zpid),
                timeout=self.request_timeout
            )
            
            if not fresh_data:
                return ValidationResult(
                    is_valid=False,
                    reason="Property not found or could not be scraped with szill",
                    content_size_bytes_validated=entity.content_size_bytes,
                )

            # Convert fresh data to PropertyDataSchema for validation
            fresh_content = self._convert_szill_to_schema(fresh_data)
            if not fresh_content:
                return ValidationResult(
                    is_valid=False,
                    reason="Could not convert szill data to PropertyDataSchema",
                    content_size_bytes_validated=entity.content_size_bytes,
                )

            # Validate the entity against fresh data
            return self._validate_entity_content(entity, fresh_content)

        except asyncio.TimeoutError:
            bt.logging.error(f"Timeout validating entity: {entity.uri}")
            return ValidationResult(
                is_valid=False,
                reason="Request timeout - Zillow may be blocking requests",
                content_size_bytes_validated=entity.content_size_bytes,
            )
        except Exception as e:
            bt.logging.error(f"Error validating entity with szill: {str(e)}")
            bt.logging.error(traceback.format_exc())
            return ValidationResult(
                is_valid=False,
                reason=f"Validation error: {str(e)}",
                content_size_bytes_validated=entity.content_size_bytes,
            )

    def _extract_zpid_from_uri(self, uri: str) -> Optional[str]:
        """Extract zpid from Zillow URI"""
        try:
            # Handle different URI formats
            # Format 1: szill://244790245 (zpid is directly after protocol)
            if uri.startswith("szill://"):
                zpid = uri.replace("szill://", "").strip("/").split("/")[0]
                if zpid.isdigit():
                    return zpid
            # Format 2: URL with _zpid suffix
            if "_zpid" in uri:
                return uri.split("_zpid")[0].split("/")[-1]
            # Format 3: URL with zpid query parameter
            elif "zpid=" in uri:
                return uri.split("zpid=")[1].split("&")[0]
            # Format 4: Try to extract any numeric ID from the path
            parts = uri.replace("://", "/").split("/")
            for part in parts:
                if part.isdigit() and len(part) >= 6:  # zpids are typically 8-9 digits
                    return part
            
            bt.logging.warning(f"Could not extract zpid from URI: {uri}")
            return None
        except Exception as e:
            bt.logging.error(f"Error extracting zpid from URI {uri}: {str(e)}")
            return None

    async def _fetch_property_with_szill(self, zpid: str) -> Optional[dict]:
        """Fetch property data using szill library with retry logic and fallback"""
        try:
            # Convert zpid to int for szill
            property_id = int(zpid)
            
            # Attempt with retries
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    # Run szill in a thread since it's synchronous
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(
                        None, 
                        lambda: get_from_home_id(property_id, self.proxy_url, self.use_scrapingbee)
                    )
                    
                    if data:
                        if attempt > 0:
                            bt.logging.info(f"Successfully fetched property {zpid} on attempt {attempt + 1}")
                        return data
                    
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a ScrapingBee error that we can fallback from
                    if self.use_scrapingbee and self.enable_fallback and attempt == 0:
                        if 'scrapingbee' in error_msg or 'headers' in error_msg or 'connection' in error_msg:
                            if self.proxy_url:
                                bt.logging.warning(f"ScrapingBee failed for {zpid}: {str(e)}. Attempting fallback to proxy method.")
                                # Try with traditional proxy on next attempt
                                try:
                                    loop = asyncio.get_event_loop()
                                    data = await loop.run_in_executor(
                                        None, 
                                        lambda: get_from_home_id(property_id, self.proxy_url, use_scrapingbee=False)
                                    )
                                    if data:
                                        bt.logging.info(f"Successfully fetched property {zpid} using fallback proxy method")
                                        return data
                                except Exception as fallback_error:
                                    bt.logging.warning(f"Fallback proxy also failed: {str(fallback_error)}")
                                    last_error = fallback_error
                            else:
                                bt.logging.warning(f"ScrapingBee failed for {zpid}: {str(e)}. No proxy_url configured for fallback. Consider adding --proxy_url option.")
                    
                    # Log retry attempt
                    if attempt < self.max_retries:
                        retry_delay = (attempt + 1) * 2  # Linear backoff: 2s, 4s, 6s
                        bt.logging.warning(f"Attempt {attempt + 1} failed for {zpid}: {str(e)}. Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        bt.logging.error(f"All {self.max_retries + 1} attempts failed for {zpid}: {str(e)}")
            
            # If we get here, all attempts failed
            if last_error:
                bt.logging.error(f"Error fetching property with szill after {self.max_retries + 1} attempts: {str(last_error)}")
            return None
            
        except ValueError:
            bt.logging.error(f"Invalid zpid format: {zpid}")
            return None
        except Exception as e:
            bt.logging.error(f"Unexpected error fetching property with szill: {str(e)}")
            return None

    def _convert_szill_to_schema(self, szill_data: dict) -> Optional[PropertyDataSchema]:
        """Convert szill data format to PropertyDataSchema"""
        try:
            # Szill data already matches our schema structure
            # Just validate and return as PropertyDataSchema
            return PropertyDataSchema.from_dict(szill_data)
            
        except Exception as e:
            bt.logging.error(f"Error converting szill data to PropertyDataSchema: {str(e)}")
            return None

    def _validate_entity_content(self, entity: DataEntity, fresh_content: PropertyDataSchema) -> ValidationResult:
        """Validate entity content against fresh data"""
        try:
            # Parse the entity's content as PropertyDataSchema
            if isinstance(entity.content, dict):
                entity_content_dict = entity.content
            elif isinstance(entity.content, bytes):
                # Decode bytes to string first, then parse as JSON
                try:
                    content_str = entity.content.decode('utf-8')
                    entity_content_dict = json.loads(content_str)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    bt.logging.error(f"Failed to decode/parse bytes content: {str(e)}")
                    return ValidationResult(
                        is_valid=False,
                        reason=f"Invalid bytes content format: {str(e)}",
                        content_size_bytes_validated=entity.content_size_bytes,
                    )
            else:
                # Handle string content, safely parsing with null handling
                content_str = str(entity.content)
                try:
                    # First try direct JSON parsing
                    entity_content_dict = json.loads(content_str)
                except json.JSONDecodeError:
                    # If JSON fails, try replacing JavaScript null/true/false with Python equivalents
                    content_str = content_str.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                    try:
                        # Try eval with safer null handling
                        entity_content_dict = eval(content_str)
                    except (NameError, SyntaxError) as e:
                        bt.logging.error(f"Failed to parse entity content: {str(e)}")
                        return ValidationResult(
                            is_valid=False,
                            reason=f"Invalid content format: {str(e)}",
                            content_size_bytes_validated=entity.content_size_bytes,
                        )
            
            # Try to parse as PropertyDataSchema, handle both old and new formats
            try:
                entity_content = PropertyDataSchema.from_dict(entity_content_dict)
            except Exception as e:
                bt.logging.warning(f"Failed to parse as PropertyDataSchema, attempting compatibility mode: {str(e)}")
                # If parsing fails, create a minimal PropertyDataSchema for compatibility
                entity_content = PropertyDataSchema()
            
            is_sold_property = False
            sold_indicators = []
            
            # Check for RealEstateContent format
            if not is_sold_property and 'listing_status' in entity_content_dict:
                listing_status = entity_content_dict.get('listing_status', '').upper()
                if listing_status in ['SOLD', 'RECENTLY_SOLD']:
                    is_sold_property = True
                    sold_indicators.append(f"listing_status: {listing_status}")

            # final_sale_price in market_context
            if (hasattr(entity_content, 'market_context') and 
                entity_content.market_context and 
                hasattr(entity_content.market_context, 'final_sale_price') and 
                entity_content.market_context.final_sale_price is not None):
                is_sold_property = True
                sold_indicators.append(f"final_sale_price: ${entity_content.market_context.final_sale_price}")
            
            # sale_date in market_context
            if (hasattr(entity_content, 'market_context') and 
                entity_content.market_context and 
                hasattr(entity_content.market_context, 'sale_date') and 
                entity_content.market_context.sale_date is not None):
                is_sold_property = True
                sold_indicators.append(f"sale_date: {entity_content.market_context.sale_date}")
            
            
            # Check for sales history
            if (not is_sold_property and 
                hasattr(entity_content, 'home_sales') and 
                entity_content.home_sales and 
                hasattr(entity_content.home_sales, 'sales_history') and 
                entity_content.home_sales.sales_history):
                is_sold_property = True
                sold_indicators.append("sales_history: present")
            
            # Only reward sold properties
            if not is_sold_property:
                bt.logging.info("Property is not identified as sold. Only sold properties are rewarded.")
                return ValidationResult(
                    is_valid=False,
                    reason="Only sold properties are rewarded. No sold property indicators found.",
                    content_size_bytes_validated=0,  # No reward for non-sold properties
                )
            
            # Log successful validation
            bt.logging.info(f"Property validated as SOLD - Indicators: {', '.join(sold_indicators)}")
            
            # Basic validation - check key fields match
            validation_errors = []
            
            # Critical fields that must match exactly
            # Handle both PropertyDataSchema format (ids.zillow.zpid) and RealEstateContent format (zpid at root)
            entity_zpid = None
            if hasattr(entity_content, 'ids') and entity_content.ids and hasattr(entity_content.ids, 'zillow'):
                entity_zpid = entity_content.ids.zillow.zpid
            
            # If zpid is None, try to get it from the root level (RealEstateContent format)
            if entity_zpid is None and 'zpid' in entity_content_dict:
                entity_zpid = entity_content_dict.get('zpid')
                bt.logging.debug(f"Using RealEstateContent format - extracted zpid from root level: {entity_zpid}")
                # Convert string zpid to int if necessary
                if isinstance(entity_zpid, str):
                    try:
                        entity_zpid = int(entity_zpid)
                    except (ValueError, TypeError):
                        pass
            elif entity_zpid is not None:
                bt.logging.debug(f"Using PropertyDataSchema format - extracted zpid from ids.zillow.zpid: {entity_zpid}")
            
            fresh_zpid = fresh_content.ids.zillow.zpid
            if entity_zpid != fresh_zpid:
                validation_errors.append(f"zpid mismatch: {entity_zpid} vs {fresh_zpid}")
            
            # Address validation (allow some flexibility)
            # Handle both PropertyDataSchema format and RealEstateContent format
            entity_address = None
            if (hasattr(entity_content, 'property') and entity_content.property and 
                hasattr(entity_content.property, 'location') and entity_content.property.location):
                entity_address = entity_content.property.location.addresses
            
            # If address is None, try to get it from the root level (RealEstateContent format)
            if entity_address is None and 'address' in entity_content_dict:
                entity_address = entity_content_dict.get('address')
            
            fresh_address = fresh_content.property.location.addresses
            if entity_address and fresh_address:
                normalized_entity_address = normalize_address(entity_address)
                normalized_fresh_address = normalize_address(fresh_address)
                if normalized_entity_address != normalized_fresh_address:
                    validation_errors.append(f"address mismatch: {entity_address} vs {fresh_address} (normalized: {normalized_entity_address} vs {normalized_fresh_address})")
            
            # Property type validation
            # Handle both PropertyDataSchema format and RealEstateContent format
            entity_type = None
            if (hasattr(entity_content, 'property') and entity_content.property and 
                hasattr(entity_content.property, 'characteristics') and entity_content.property.characteristics):
                entity_type = entity_content.property.characteristics.property_type
            
            # If property_type is None, try to get it from the root level (RealEstateContent format)
            if entity_type is None and 'property_type' in entity_content_dict:
                entity_type = entity_content_dict.get('property_type')
            
            fresh_type = fresh_content.property.characteristics.property_type
            if entity_type and fresh_type:
                normalized_entity_type = normalize_property_type(entity_type)
                normalized_fresh_type = normalize_property_type(fresh_type)

                # Only compare if both are not None (not unknown)
                if normalized_entity_type is not None and normalized_fresh_type is not None:
                    if normalized_entity_type != normalized_fresh_type:
                        validation_errors.append(f"property_type mismatch: {entity_type} vs {fresh_type} (normalized: {normalized_entity_type} vs {normalized_fresh_type})")
                elif normalized_entity_type != normalized_fresh_type:
                    # One is known, one is unknown - this is a mismatch
                    validation_errors.append(f"property_type mismatch: {entity_type} vs {fresh_type} (one is unknown, other is {normalized_entity_type or normalized_fresh_type})")
            
            # If there are validation errors, return invalid
            if validation_errors:
                return ValidationResult(
                    is_valid=False,
                    reason=f"Content validation failed: {'; '.join(validation_errors)}",
                    content_size_bytes_validated=entity.content_size_bytes,
                )
            
            # Validation passed
            return ValidationResult(
                is_valid=True,
                reason="Content validation passed using szill scraper",
                content_size_bytes_validated=entity.content_size_bytes,
            )
            
        except Exception as e:
            bt.logging.error(f"Error validating entity content: {str(e)}")
            return ValidationResult(
                is_valid=False,
                reason=f"Content validation error: {str(e)}",
                content_size_bytes_validated=entity.content_size_bytes,
            ) 