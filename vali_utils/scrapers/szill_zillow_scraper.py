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

# Import the szill library from the moved location
try:
    from .szill import get_from_home_id, get_from_home_url
    from .szill.utils import parse_proxy
    SZILL_AVAILABLE = True
except ImportError as e:
    bt.logging.error(f"Szill library not available: {e}")
    SZILL_AVAILABLE = False


class SzillZillowScraper(Scraper):
    """Scraper using the szill library with sequential processing to avoid Zillow blocking."""

    def __init__(self, proxy_url: Optional[str] = None):
        if not SZILL_AVAILABLE:
            raise ImportError("Szill library not available.")
        
        self.proxy_url = proxy_url
        # Configuration for sequential processing with short delays
        self.min_delay_seconds = 1   # Minimum delay between requests
        self.max_delay_seconds = 5   # Maximum delay between requests
        self.request_timeout = 120   # Timeout for individual requests

    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrape method implementation."""
        return []

    async def validate(self, entities: Union[DataEntity, List[DataEntity]]) -> Union[ValidationResult, List[ValidationResult]]:
        """
        Validate DataEntity(ies) using the szill scraper with sequential processing.
        
        Args:
            entities: Single DataEntity or List of DataEntities to validate
            
        Returns:
            Single ValidationResult or List of ValidationResults
        """
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
            return await self._validate_single_entity(entities)
        
        # Handle list of entities with sequential processing
        if not entities:
            return []
            
        bt.logging.info(f"Starting sequential validation of {len(entities)} entities to avoid Zillow blocking")
        
        results = []
        for i, entity in enumerate(entities):
            bt.logging.info(f"Validating entity {i+1}/{len(entities)}: {entity.uri}")
            
            try:
                result = await self._validate_single_entity(entity)
                results.append(result)
                
                # Add short delay between requests to avoid Zillow blocking
                if i < len(entities) - 1:  # Don't delay after the last entity
                    delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
                    bt.logging.info(f"Waiting {delay:.1f} seconds before next request to avoid Zillow blocking")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                bt.logging.error(f"Error validating entity {i+1}: {str(e)}")
                results.append(ValidationResult(
                    is_valid=False,
                    reason=f"Validation error: {str(e)}",
                    content_size_bytes_validated=entity.content_size_bytes,
                ))
        
        bt.logging.info(f"Completed sequential validation of {len(entities)} entities")
        return results

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
            if "_zpid" in uri:
                return uri.split("_zpid")[0].split("/")[-1]
            elif "zpid=" in uri:
                return uri.split("zpid=")[1].split("&")[0]
            else:
                bt.logging.warning(f"Could not extract zpid from URI: {uri}")
                return None
        except Exception as e:
            bt.logging.error(f"Error extracting zpid from URI {uri}: {str(e)}")
            return None

    async def _fetch_property_with_szill(self, zpid: str) -> Optional[dict]:
        """Fetch property data using szill library"""
        try:
            # Convert zpid to int for szill
            property_id = int(zpid)
            
            # Run szill in a thread since it's synchronous
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                lambda: get_from_home_id(property_id, self.proxy_url)
            )
            
            return data
            
        except ValueError:
            bt.logging.error(f"Invalid zpid format: {zpid}")
            return None
        except Exception as e:
            bt.logging.error(f"Error fetching property with szill: {str(e)}")
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
            
            entity_content = PropertyDataSchema.from_dict(entity_content_dict)
            
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
            entity_zpid = entity_content.ids.zillow.zpid
            fresh_zpid = fresh_content.ids.zillow.zpid
            if entity_zpid != fresh_zpid:
                validation_errors.append(f"zpid mismatch: {entity_zpid} vs {fresh_zpid}")
            
            # Address validation (allow some flexibility)
            entity_address = entity_content.property.location.addresses
            fresh_address = fresh_content.property.location.addresses
            if entity_address and fresh_address:
                if entity_address.lower().strip() != fresh_address.lower().strip():
                    validation_errors.append(f"address mismatch: {entity_address} vs {fresh_address}")
            
            # Property type validation
            entity_type = entity_content.property.characteristics.property_type
            fresh_type = fresh_content.property.characteristics.property_type
            if entity_type and fresh_type:
                if entity_type != fresh_type:
                    validation_errors.append(f"property_type mismatch: {entity_type} vs {fresh_type}")
            
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