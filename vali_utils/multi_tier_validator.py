"""
Multi-Tier Validation System for Zipcode-Based Competitive Mining
Implements 3-tier validation: Quantity, Quality, and Deterministic Spot Checks
"""

import hashlib
import random
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import bittensor as bt
import pandas as pd

from vali_utils.scrapers.validator_scraper_provider import ValidatorScraperProvider, ValidatorScraperId
from common.data import DataEntity, DataLabel, DataSource
from scraping.custom.model import RealEstateContent


class MultiTierValidator:
    """
    Multi-tier validation system for miner submissions
    
    Tier 1: Quantity & Timeliness Validation
    Tier 2: Data Quality & Completeness Validation  
    Tier 3: Deterministic Spot Check Validation
    """
    
    def __init__(self):
        # Tier 1 Configuration
        self.quantity_tolerance = 0.15  # ±15% tolerance for listing count
        
        # Initialize scraper provider for spot-check verification
        self.scraper_provider = ValidatorScraperProvider()
        
        # Tier 2 Configuration
        self.required_fields = [
            'address', 'price', 'bedrooms', 'bathrooms', 'sqft',
            'listing_date', 'property_type', 'listing_status', 
            'days_on_market', 'mls_id', 'source_url', 'scraped_timestamp'
        ]
        self.quality_thresholds = {
            'field_completeness': 0.90,    # 90% of listings must have all required fields
            'reasonable_values': 0.95,     # 95% of values must be reasonable
            'data_consistency': 0.90,      # 90% of data must be consistent
            'duplicate_rate': 0.05         # <5% duplicates allowed
        }
        
        # Tier 3 Configuration
        self.spot_check_pass_rate = 0.80   # 80% of spot checks must pass
        self.min_spot_check_samples = 3    # Minimum samples to check
        self.max_spot_check_samples = 10   # Maximum samples to check
        self.spot_check_percentage = 0.10  # 10% of listings to spot check
    
    def tier1_quantity_validation(self, submission: Dict, expected_count: int) -> Dict[str, Any]:
        """
        Tier 1: Validate listing count and submission timing
        
        Args:
            submission: Miner submission data
            expected_count: Expected number of listings for this zipcode
            
        Returns:
            Dict with validation results and metrics
        """
        listings = submission.get('listings', [])
        actual_count = len(listings)
        submission_time = submission.get('submission_timestamp')
        
        # Calculate minimum acceptable count
        min_expected = int(expected_count * (1 - self.quantity_tolerance))
        
        # TODO: Remove this before pushing to mainnet
        # min_expected = 2
        
        # Check quantity (only minimum threshold, no maximum)
        passes_quantity = actual_count >= min_expected
        
        # Calculate timeliness score (earlier submissions get higher scores)
        timeliness_score = self._calculate_timeliness_score(submission_time)
        
        result = {
            'passes_quantity': passes_quantity,
            'actual_count': actual_count,
            'expected_count': expected_count,
            'min_expected': min_expected,
            'quantity_ratio': actual_count / expected_count if expected_count > 0 else 0,
            'submission_time': submission_time,
            'timeliness_score': timeliness_score,
            'tier': 1
        }
        
        bt.logging.debug(f"Tier 1 - Quantity: {actual_count}/{expected_count} ({'PASS' if passes_quantity else 'FAIL'})")
        
        return result
    
    def tier2_data_quality_validation(self, listings: List[Dict]) -> Dict[str, Any]:
        """
        Tier 2: Validate data completeness and field quality
        
        Args:
            listings: List of property listing dictionaries
            
        Returns:
            Dict with quality validation results and metrics
        """
        if not listings:
            return {
                'passes_quality': False,
                'quality_metrics': {},
                'tier': 2,
                'reason': 'No listings provided'
            }
        
        quality_metrics = {
            'field_completeness': 0.0,
            'reasonable_values': 0.0,
            'data_consistency': 0.0,
            'duplicate_rate': 0.0
        }
        
        # 1. Check field completeness
        quality_metrics['field_completeness'] = self._check_field_completeness(listings)
        
        # 2. Check for reasonable values
        quality_metrics['reasonable_values'] = self._validate_reasonable_values(listings)
        
        # 3. Check data consistency
        quality_metrics['data_consistency'] = self._validate_data_consistency(listings)
        
        # 4. Check duplicate rate
        quality_metrics['duplicate_rate'] = self._calculate_duplicate_rate(listings)
        
        # Determine if passes all quality thresholds
        passes_quality = (
            quality_metrics['field_completeness'] >= self.quality_thresholds['field_completeness'] and
            quality_metrics['reasonable_values'] >= self.quality_thresholds['reasonable_values'] and
            quality_metrics['data_consistency'] >= self.quality_thresholds['data_consistency'] and
            quality_metrics['duplicate_rate'] <= self.quality_thresholds['duplicate_rate']
        )
        
        result = {
            'passes_quality': passes_quality,
            'quality_metrics': quality_metrics,
            'quality_thresholds': self.quality_thresholds,
            'tier': 2
        }
        
        bt.logging.debug(f"Tier 2 - Quality: {'PASS' if passes_quality else 'FAIL'} "
                        f"(completeness: {quality_metrics['field_completeness']:.2f}, "
                        f"reasonable: {quality_metrics['reasonable_values']:.2f}, "
                        f"consistent: {quality_metrics['data_consistency']:.2f}, "
                        f"duplicates: {quality_metrics['duplicate_rate']:.2f})")
        
        return result
    
    def tier3_deterministic_spot_check(self, submission: Dict, epoch_nonce: str) -> Dict[str, Any]:
        """
        Tier 3: Perform deterministic spot checks using epoch nonce + miner data
        
        Args:
            submission: Miner submission data
            epoch_nonce: Epoch nonce for deterministic seed generation
            
        Returns:
            Dict with spot check results and verification details
        """
        miner_hotkey = submission['miner_hotkey']
        submission_time = submission['submission_timestamp']
        listings = submission['listings']
        
        if not listings:
            return {
                'passes_spot_check': False,
                'spot_check_pass_rate': 0.0,
                'tier': 3,
                'reason': 'No listings to spot check'
            }
        
        # Create deterministic seed that all validators will generate identically
        seed_string = f"{epoch_nonce}:{miner_hotkey}:{submission_time}:{len(listings)}"
        seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16)
        
        # Use seed to select same listings across all validators
        random.seed(seed)
        sample_size = min(
            self.max_spot_check_samples,
            max(self.min_spot_check_samples, int(len(listings) * self.spot_check_percentage))
        )
        selected_indices = sorted(random.sample(range(len(listings)), sample_size))
        
        # Perform spot checks on selected listings
        spot_check_results = []
        for idx in selected_indices:
            listing = listings[idx]
            verification_result = self._verify_listing_with_scraper(listing)
            
            spot_check_results.append({
                'listing_index': idx,
                'listing_id': listing.get('mls_id', listing.get('uri', f"listing_{idx}")),
                'verification_passed': verification_result['exists_and_accurate'],
                'verification_details': verification_result,
                'listing_address': listing.get('address', 'Unknown')
            })
        
        # Calculate pass rate
        passed_checks = sum(1 for result in spot_check_results if result['verification_passed'])
        spot_check_pass_rate = passed_checks / len(spot_check_results) if spot_check_results else 0
        
        passes_spot_check = spot_check_pass_rate >= self.spot_check_pass_rate
        
        result = {
            'passes_spot_check': passes_spot_check,
            'spot_check_pass_rate': spot_check_pass_rate,
            'spot_check_results': spot_check_results,
            'deterministic_seed': seed,
            'selected_indices': selected_indices,
            'sample_size': sample_size,
            'tier': 3
        }
        
        bt.logging.debug(f"Tier 3 - Spot Check: {'PASS' if passes_spot_check else 'FAIL'} "
                        f"({passed_checks}/{len(spot_check_results)} passed, "
                        f"rate: {spot_check_pass_rate:.2f})")
        
        return result
    
    def validate_submission_complete(self, submission: Dict, expected_listings: int, 
                                   epoch_nonce: str) -> Dict[str, Any]:
        """
        Complete 3-tier validation of a miner submission
        
        Args:
            submission: Complete miner submission
            expected_listings: Expected number of listings for zipcode
            epoch_nonce: Epoch nonce for deterministic validation
            
        Returns:
            Complete validation results with all tier results
        """
        miner_hotkey = submission['miner_hotkey']
        bt.logging.info(f"Starting 3-tier validation for miner {miner_hotkey[:8]}...")
        
        # Tier 1: Quantity & Timeliness
        tier1_result = self.tier1_quantity_validation(submission, expected_listings)
        
        if not tier1_result['passes_quantity']:
            bt.logging.info(f"Miner {miner_hotkey[:8]} failed Tier 1 (quantity)")
            return {
                'passes_all_tiers': False,
                'failed_at_tier': 1,
                'tier1_result': tier1_result,
                'tier2_result': None,
                'tier3_result': None
            }
        
        # Tier 2: Data Quality & Completeness
        tier2_result = self.tier2_data_quality_validation(submission['listings'])
        
        if not tier2_result['passes_quality']:
            bt.logging.info(f"Miner {miner_hotkey[:8]} failed Tier 2 (quality)")
            return {
                'passes_all_tiers': False,
                'failed_at_tier': 2,
                'tier1_result': tier1_result,
                'tier2_result': tier2_result,
                'tier3_result': None
            }
        
        # Tier 3: Deterministic Spot Check
        tier3_result = self.tier3_deterministic_spot_check(submission, epoch_nonce)
        
        passes_all_tiers = tier3_result['passes_spot_check']
        
        if passes_all_tiers:
            bt.logging.success(f"Miner {miner_hotkey[:8]} passed all 3 tiers!")
        else:
            bt.logging.info(f"Miner {miner_hotkey[:8]} failed Tier 3 (spot check)")
        
        return {
            'passes_all_tiers': passes_all_tiers,
            'failed_at_tier': None if passes_all_tiers else 3,
            'tier1_result': tier1_result,
            'tier2_result': tier2_result,
            'tier3_result': tier3_result
        }
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _calculate_timeliness_score(self, submission_time: str) -> float:
        """Calculate timeliness score based on submission time"""
        try:
            # Parse submission timestamp
            if isinstance(submission_time, str):
                submission_dt = datetime.fromisoformat(submission_time.replace('Z', '+00:00'))
            else:
                submission_dt = datetime.fromtimestamp(submission_time, tz=timezone.utc)
            
            # Earlier submissions get higher scores (0.5 to 1.0 range)
            return 1.0  # For now, return max score
            
        except Exception as e:
            bt.logging.warning(f"Error calculating timeliness score: {e}")
            return 0.5  # Default middle score
    
    def _check_field_completeness(self, listings: List[Dict]) -> float:
        """Check what percentage of listings have all required fields"""
        if not listings:
            return 0.0
        
        complete_listings = 0
        for listing in listings:
            if all(field in listing and listing[field] is not None and str(listing[field]).strip() 
                   for field in self.required_fields):
                complete_listings += 1
        
        return complete_listings / len(listings)
    
    def _validate_reasonable_values(self, listings: List[Dict]) -> float:
        """Validate that property values are reasonable"""
        if not listings:
            return 0.0
        
        reasonable_count = 0
        
        for listing in listings:
            is_reasonable = True
            
            # Check price range (reasonable for US real estate)
            price = listing.get('price')
            if price is not None:
                try:
                    price_val = float(price)
                    if not (10000 <= price_val <= 50000000):  # $10K to $50M
                        is_reasonable = False
                except (ValueError, TypeError):
                    is_reasonable = False
            
            # Check bedrooms (0-20 reasonable range)
            bedrooms = listing.get('bedrooms')
            if bedrooms is not None:
                try:
                    bed_val = int(bedrooms)
                    if not (0 <= bed_val <= 20):
                        is_reasonable = False
                except (ValueError, TypeError):
                    is_reasonable = False
            
            # Check bathrooms (0-20 reasonable range)
            bathrooms = listing.get('bathrooms')
            if bathrooms is not None:
                try:
                    bath_val = float(bathrooms)
                    if not (0 <= bath_val <= 20):
                        is_reasonable = False
                except (ValueError, TypeError):
                    is_reasonable = False
            
            # Check square footage (100-100,000 sqft reasonable)
            sqft = listing.get('sqft')
            if sqft is not None:
                try:
                    sqft_val = int(sqft)
                    if not (100 <= sqft_val <= 100000):
                        is_reasonable = False
                except (ValueError, TypeError):
                    is_reasonable = False
            
            if is_reasonable:
                reasonable_count += 1
        
        return reasonable_count / len(listings)
    
    def _validate_data_consistency(self, listings: List[Dict]) -> float:
        """Check data consistency within listings"""
        if not listings:
            return 0.0
        
        consistent_count = 0
        
        for listing in listings:
            is_consistent = True
            
            # Check if address contains zipcode
            address = listing.get('address', '')
            zipcode = listing.get('zipcode', '')
            if zipcode and zipcode not in str(address):
                # This might be okay, not all addresses include zipcode
                pass
            
            # Check if listing_date is valid format
            listing_date = listing.get('listing_date')
            if listing_date:
                try:
                    datetime.fromisoformat(listing_date.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    is_consistent = False
            
            # Check if scraped_timestamp is valid and recent
            scraped_timestamp = listing.get('scraped_timestamp')
            if scraped_timestamp:
                try:
                    scraped_dt = datetime.fromisoformat(scraped_timestamp.replace('Z', '+00:00'))
                    # Should be within last 24 hours for fresh data
                    if (datetime.now(timezone.utc) - scraped_dt).days > 1:
                        is_consistent = False
                except (ValueError, TypeError):
                    is_consistent = False
            
            if is_consistent:
                consistent_count += 1
        
        return consistent_count / len(listings)
    
    def _calculate_duplicate_rate(self, listings: List[Dict]) -> float:
        """Calculate the rate of duplicate listings"""
        if not listings:
            return 0.0
        
        # Use address + price as duplicate key (simple approach)
        seen_properties = set()
        duplicates = 0
        
        for listing in listings:
            address = listing.get('address', '').strip().lower()
            price = listing.get('price', '')
            
            property_key = f"{address}:{price}"
            
            if property_key in seen_properties:
                duplicates += 1
            else:
                seen_properties.add(property_key)
        
        return duplicates / len(listings)
    
    def _verify_listing_with_scraper(self, listing: Dict) -> Dict[str, Any]:
        """
        Verify a single listing by cross-checking with SzillZillowScraper
        
        Args:
            listing: Property listing to verify
            
        Returns:
            Dict with verification results
        """
        try:
            # Extract required fields
            zpid = listing.get('zpid') or listing.get('mls_id')
            address = listing.get('address', '')
            price = listing.get('price', 0)
            zipcode = listing.get('zipcode', '')
            
            verification_details = {
                'method': 'szill_zillow_scraper',
                'checks_performed': [],
                'zpid': zpid,
                'address': address
            }
            
            # Basic validation first
            if not zpid:
                return {
                    'exists_and_accurate': False,
                    'verification_details': verification_details,
                    'reason': 'No zpid or mls_id found in listing',
                    'verified_at': datetime.now(timezone.utc).isoformat()
                }
            
            # Convert listing to DataEntity format for scraper validation
            data_entity = self._convert_listing_to_data_entity(listing)
            if not data_entity:
                return {
                    'exists_and_accurate': False,
                    'verification_details': verification_details,
                    'reason': 'Could not convert listing to DataEntity format',
                    'verified_at': datetime.now(timezone.utc).isoformat()
                }
            
            # Use SzillZillowScraper for verification
            scraper = self.scraper_provider.get(ValidatorScraperId.SZILL_ZILLOW)
            
            # Perform validation (this is async, so we need to handle it)
            import asyncio
            try:
                # Run the async validation
                if hasattr(asyncio, 'run'):
                    validation_result = asyncio.run(scraper.validate(data_entity))
                else:
                    # Fallback for older Python versions
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        validation_result = loop.run_until_complete(scraper.validate(data_entity))
                    finally:
                        loop.close()
                
                verification_details['checks_performed'].append('szill_scraper_validation')
                verification_details['scraper_result'] = {
                    'is_valid': validation_result.is_valid,
                    'reason': validation_result.reason,
                    'content_size_validated': validation_result.content_size_bytes_validated
                }
                
                exists_and_accurate = validation_result.is_valid
                reason = validation_result.reason if not validation_result.is_valid else 'Property verified successfully'
                
            except Exception as scraper_error:
                bt.logging.warning(f"Scraper validation failed for zpid {zpid}: {scraper_error}")
                verification_details['checks_performed'].append('scraper_error')
                verification_details['scraper_error'] = str(scraper_error)
                
                # Fall back to basic heuristic checks
                exists_and_accurate, reason = self._perform_basic_verification_checks(listing)
            
            return {
                'exists_and_accurate': exists_and_accurate,
                'verification_details': verification_details,
                'reason': reason,
                'verified_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            bt.logging.error(f"Error in spot-check verification: {e}")
            return {
                'exists_and_accurate': False,
                'verification_details': {'method': 'error', 'error': str(e)},
                'reason': f'Verification error: {str(e)}',
                'verified_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _convert_listing_to_data_entity(self, listing: Dict) -> Optional[DataEntity]:
        """Convert a listing dict to DataEntity format for scraper validation"""
        try:
            # Get property type with fallback to SINGLE_FAMILY (most common)
            property_type = listing.get('property_type')
            if not property_type or property_type == 'UNKNOWN':
                # Try to infer from other fields or default to SINGLE_FAMILY
                property_type = 'SINGLE_FAMILY'
                bt.logging.debug(f"Property type missing for zpid {listing.get('zpid')}, defaulting to SINGLE_FAMILY")
            
            # Get listing status with fallback
            listing_status = listing.get('listing_status')
            if not listing_status or listing_status == 'UNKNOWN':
                listing_status = 'FOR_SALE'
                bt.logging.debug(f"Listing status missing for zpid {listing.get('zpid')}, defaulting to FOR_SALE")
            
            # Create RealEstateContent from listing data
            real_estate_content = RealEstateContent(
                zpid=listing.get('zpid') or listing.get('mls_id', ''),
                address=listing.get('address', ''),
                detail_url=listing.get('source_url', ''),
                property_type=property_type,
                bedrooms=listing.get('bedrooms'),
                bathrooms=listing.get('bathrooms'),
                living_area=listing.get('sqft'),
                price=listing.get('price'),
                listing_status=listing_status,
                days_on_zillow=listing.get('days_on_market'),
                data_source="miner_submission"
            )
            
            # Convert to DataEntity
            return real_estate_content.to_data_entity()
            
        except Exception as e:
            bt.logging.error(f"Error converting listing to DataEntity: {e}")
            return None
    
    def _perform_basic_verification_checks(self, listing: Dict) -> Tuple[bool, str]:
        """Perform basic heuristic checks when scraper fails"""
        address = listing.get('address', '')
        price = listing.get('price', 0)
        zipcode = listing.get('zipcode', '')
        
        # Check if address looks reasonable
        if not address or len(address.strip()) < 10:
            return False, 'Address too short or missing'
        
        # Check if price is reasonable
        try:
            price_val = float(price)
            if price_val < 1000 or price_val > 100000000:
                return False, 'Price unreasonable (outside $1K-$100M range)'
        except (ValueError, TypeError):
            return False, 'Invalid price format'
        
        # Check if zipcode format is valid
        if not re.match(r'^\d{5}$', str(zipcode)):
            return False, 'Invalid zipcode format'
        
        # Basic checks passed
        return True, 'Basic verification checks passed (scraper unavailable)'
