"""
API-based validation system with coordinated data distribution.
Uses traditional validator scraping for verification when needed.
"""

import asyncio
import random
import datetime as dt
from typing import Dict, List, Tuple, Optional, Any
import bittensor as bt
from collections import defaultdict
import json

from common.data import DataEntity, DataSource
from common.protocol import DataAssignmentRequest
from rewards.miner_scorer import MinerScorer
from vali_utils.validator_data_api import ValidatorDataAPI, DataAPIConfig
from scraping.provider import ScraperProvider
from scraping.scraper import ScraperId, ScrapeConfig
from common.date_range import DateRange
from common.data import DataLabel
from vali_utils.s3_utils import ValidationResult


class APIBasedValidator:
    """
    API-based validation system that uses coordinated data distribution
    with traditional validator scraping for verification.
    """

    def __init__(self, config: DataAPIConfig, wallet: bt.wallet, metagraph: bt.metagraph, 
                 scorer: MinerScorer, scraper_provider: ScraperProvider):
        self.config = config
        self.wallet = wallet
        self.metagraph = metagraph
        self.scorer = scorer
        self.scraper_provider = scraper_provider
        
        # Initialize data API client
        self.data_api = ValidatorDataAPI(wallet, config.data_api_url)
        
        # Track assignments and responses
        self.active_assignments = {}
        self.assignment_responses = defaultdict(list)
        
        # Validation statistics
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'api_errors': 0
        }

    async def process_assignment_responses(self, assignment_id: str, responses: List[DataAssignmentRequest]) -> Dict[str, Any]:
        """
        Process miner responses using API-based validation.
        Validates each property by scraping it directly.
        """
        bt.logging.info(f"Processing {len(responses)} responses for assignment {assignment_id} with API validation")

        # Filter valid responses
        valid_responses = self._filter_valid_responses(responses)
        
        if not valid_responses:
            bt.logging.warning("No valid responses to process")
            return {"status": "no_valid_responses", "responses": []}

        # Validate each response using API scraping
        validation_results = {}
        
        for response in valid_responses:
            miner_uid = getattr(response, 'miner_uid', None)
            if not miner_uid:
                continue
                
            bt.logging.info(f"Validating response from miner {miner_uid}")
            
            miner_validation_results = []
            
            # Validate each property in the response
            for source, entities in response.scraped_data.items():
                for entity in entities:
                    validation_result = await self._validate_property_with_api(entity, source)
                    miner_validation_results.append(validation_result)
                    
            validation_results[miner_uid] = miner_validation_results

        # Update miner credibility based on validation results
        self._update_miner_credibility_with_validation(validation_results)

        # Calculate overall validation statistics
        total_validations = sum(len(results) for results in validation_results.values())
        successful_validations = sum(sum(1 for r in results if r.is_valid) for results in validation_results.values())
        
        self.validation_stats['total_validations'] += total_validations
        self.validation_stats['successful_validations'] += successful_validations
        self.validation_stats['failed_validations'] += (total_validations - successful_validations)

        bt.logging.info(f"API validation completed: {successful_validations}/{total_validations} successful")

        return {
            "status": "completed",
            "validation_results": validation_results,
            "total_validations": total_validations,
            "successful_validations": successful_validations,
            "success_rate": successful_validations / total_validations if total_validations > 0 else 0
        }

    def _filter_valid_responses(self, responses: List[DataAssignmentRequest]) -> List[DataAssignmentRequest]:
        """Filter out invalid responses"""
        valid_responses = []
        
        for response in responses:
            # Check completion status
            if response.completion_status != "completed":
                bt.logging.debug(f"Skipping incomplete response from assignment {response.request_id}")
                continue
                
            # Check if response has data
            if not response.scraped_data or not any(response.scraped_data.values()):
                bt.logging.debug(f"Skipping empty response from assignment {response.request_id}")
                continue
                
            # Check timestamp validity
            if not self._validate_response_timestamps(response):
                bt.logging.debug(f"Skipping response with invalid timestamps from assignment {response.request_id}")
                continue
                
            valid_responses.append(response)

        bt.logging.info(f"Filtered {len(valid_responses)} valid responses from {len(responses)} total")
        return valid_responses

    def _validate_response_timestamps(self, response: DataAssignmentRequest) -> bool:
        """Validate response timestamps"""
        try:
            if not response.scrape_timestamp or not response.submission_timestamp:
                return False
                
            scrape_time = dt.datetime.fromisoformat(response.scrape_timestamp.replace('Z', '+00:00'))
            submission_time = dt.datetime.fromisoformat(response.submission_timestamp.replace('Z', '+00:00'))
            
            # Reasonable scraping time: 5 minutes to 2 hours
            scrape_duration = submission_time - scrape_time
            
            if scrape_duration < dt.timedelta(minutes=5):
                bt.logging.warning("Suspiciously fast scraping detected")
                return False
            elif scrape_duration > dt.timedelta(hours=2):
                bt.logging.warning("Data too stale")
                return False
                
            return True
            
        except Exception as e:
            bt.logging.error(f"Error validating timestamps: {e}")
            return False

    async def _validate_property_with_api(self, entity: DataEntity, source: str) -> ValidationResult:
        """
        Validate a property by scraping it directly using the same API the miner should have used.
        This is the traditional Bittensor validation approach.
        """
        try:
            # Extract property identifier from entity
            property_id = self._extract_property_id(entity, source)
            if not property_id:
                return ValidationResult(
                    is_valid=False,
                    reason="Could not extract property ID from entity",
                    content_size_bytes_validated=entity.content_size_bytes
                )

            # Get appropriate scraper for validation
            scraper = self._get_scraper_for_source(source)
            if not scraper:
                return ValidationResult(
                    is_valid=False,
                    reason=f"No scraper available for source {source}",
                    content_size_bytes_validated=entity.content_size_bytes
                )

            # Create scrape config for this property
            config = self._create_validation_scrape_config(property_id, source)
            
            bt.logging.debug(f"Validating {source} property {property_id} with API scraping")
            
            # Perform validation scraping
            validation_entities = await scraper.scrape(config)
            
            if not validation_entities:
                return ValidationResult(
                    is_valid=False,
                    reason="Property not found during validation scraping",
                    content_size_bytes_validated=entity.content_size_bytes
                )

            # Compare miner data with validation data
            validation_entity = validation_entities[0]
            comparison_result = self._compare_property_data(entity, validation_entity, source)
            
            return comparison_result

        except Exception as e:
            bt.logging.error(f"Error during API validation: {e}")
            self.validation_stats['api_errors'] += 1
            return ValidationResult(
                is_valid=False,
                reason=f"API validation error: {str(e)}",
                content_size_bytes_validated=entity.content_size_bytes
            )

    def _extract_property_id(self, entity: DataEntity, source: str) -> Optional[str]:
        """Extract property ID from DataEntity based on source"""
        try:
            uri = entity.uri
            
            if source.upper() == 'ZILLOW' and 'zillow.com' in uri:
                # Extract ZPID from Zillow URI
                if '_zpid' in uri:
                    zpid = uri.split('/')[-1].replace('_zpid', '').split('?')[0]
                    return zpid
            elif source.upper() == 'REDFIN' and 'redfin.com' in uri:
                # Extract Redfin property ID from URI
                prop_id = uri.split('/')[-1].split('?')[0]
                return prop_id
            # Add more property ID extraction logic for other sources
            
        except Exception as e:
            bt.logging.error(f"Error extracting property ID from {uri}: {e}")
            
        return None

    def _get_scraper_for_source(self, source: str) -> Optional[any]:
        """Get appropriate scraper for the data source"""
        try:
            if source.upper() == 'ZILLOW':
                return self.scraper_provider.get(ScraperId.RAPID_ZILLOW)
            elif source.upper() == 'REDFIN':
                # Add Redfin scraper when available
                return None
            # Add more scrapers as needed
            
        except Exception as e:
            bt.logging.error(f"Error getting scraper for source {source}: {e}")
            
        return None

    def _create_validation_scrape_config(self, property_id: str, source: str) -> ScrapeConfig:
        """Create scrape config for validation"""
        if source.upper() == 'ZILLOW':
            label = DataLabel(value=f"zpid:{property_id}")
        elif source.upper() == 'REDFIN':
            label = DataLabel(value=f"redfin_id:{property_id}")
        else:
            label = DataLabel(value=property_id)

        return ScrapeConfig(
            entity_limit=1,
            date_range=DateRange(
                start=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
                end=dt.datetime.now(dt.timezone.utc)
            ),
            labels=[label]
        )

    def _compare_property_data(self, miner_entity: DataEntity, validation_entity: DataEntity, 
                             source: str) -> ValidationResult:
        """
        Compare miner data with validation data.
        Uses field-by-field comparison similar to existing validation.
        """
        try:
            # Decode content from both entities
            miner_content_str = miner_entity.content.decode('utf-8') if isinstance(miner_entity.content, bytes) else miner_entity.content
            validation_content_str = validation_entity.content.decode('utf-8') if isinstance(validation_entity.content, bytes) else validation_entity.content
            
            miner_data = json.loads(miner_content_str)
            validation_data = json.loads(validation_content_str)

            # Define key fields to validate based on source
            if source.upper() == 'ZILLOW':
                key_fields = ['price', 'bedrooms', 'bathrooms', 'living_area', 'address', 'property_type']
            elif source.upper() == 'REDFIN':
                key_fields = ['price', 'bedrooms', 'bathrooms', 'square_feet', 'address', 'property_type']
            else:
                key_fields = ['price', 'bedrooms', 'bathrooms', 'address']

            # Compare key fields
            matching_fields = 0
            total_fields = 0
            field_comparisons = []

            for field in key_fields:
                if field in validation_data:
                    total_fields += 1
                    
                    if field in miner_data:
                        miner_value = miner_data[field]
                        validation_value = validation_data[field]
                        
                        # Handle different data types
                        if isinstance(validation_value, (int, float)) and isinstance(miner_value, (int, float)):
                            # Allow 5% tolerance for numerical fields
                            tolerance = 0.05
                            if abs(validation_value - miner_value) / max(abs(validation_value), abs(miner_value), 1) <= tolerance:
                                matching_fields += 1
                                field_comparisons.append(f"{field}: MATCH ({miner_value} ≈ {validation_value})")
                            else:
                                field_comparisons.append(f"{field}: MISMATCH ({miner_value} vs {validation_value})")
                        elif str(miner_value).lower() == str(validation_value).lower():
                            matching_fields += 1
                            field_comparisons.append(f"{field}: MATCH ({miner_value})")
                        else:
                            field_comparisons.append(f"{field}: MISMATCH ({miner_value} vs {validation_value})")
                    else:
                        field_comparisons.append(f"{field}: MISSING in miner data")

            # Calculate validation success
            if total_fields == 0:
                return ValidationResult(
                    is_valid=False,
                    reason="No comparable fields found in validation data",
                    content_size_bytes_validated=miner_entity.content_size_bytes
                )

            match_ratio = matching_fields / total_fields
            is_valid = match_ratio >= 0.8  # 80% of fields must match

            reason = f"Field validation: {matching_fields}/{total_fields} fields match ({match_ratio:.2%})"
            if field_comparisons:
                reason += f". Details: {'; '.join(field_comparisons[:3])}"  # Show first 3 comparisons

            return ValidationResult(
                is_valid=is_valid,
                reason=reason,
                content_size_bytes_validated=miner_entity.content_size_bytes
            )

        except Exception as e:
            bt.logging.error(f"Error comparing property data: {e}")
            return ValidationResult(
                is_valid=False,
                reason=f"Data comparison error: {str(e)}",
                content_size_bytes_validated=miner_entity.content_size_bytes
            )

    def _update_miner_credibility_with_validation(self, validation_results: Dict[int, List[ValidationResult]]):
        """Update miner credibility using existing MinerScorer mechanism"""
        for miner_uid, results in validation_results.items():
            if results:
                # Use existing credibility update mechanism
                self.scorer._update_credibility(miner_uid, results)
                
                # Calculate success rate for logging
                successful = sum(1 for r in results if r.is_valid)
                total = len(results)
                success_rate = successful / total if total > 0 else 0
                
                bt.logging.info(f"Updated credibility for miner {miner_uid}: {successful}/{total} validations successful ({success_rate:.2%})")

    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics for monitoring"""
        total = self.validation_stats['total_validations']
        successful = self.validation_stats['successful_validations']
        
        return {
            'total_validations': total,
            'successful_validations': successful,
            'failed_validations': self.validation_stats['failed_validations'],
            'api_errors': self.validation_stats['api_errors'],
            'success_rate': successful / total if total > 0 else 0,
            'error_rate': self.validation_stats['api_errors'] / total if total > 0 else 0
        }

    def reset_statistics(self):
        """Reset validation statistics"""
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'api_errors': 0
        }
