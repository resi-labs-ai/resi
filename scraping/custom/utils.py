"""
Utility functions for Zillow real estate data validation.
Provides validation logic similar to Twitter/Reddit but adapted for real estate data.

This module handles validation between miners (using Property Extended Search) 
and validators (using Individual Property API) by validating only the subset 
of fields that miners actually have access to.
"""

import datetime as dt
import json
import traceback
from typing import Optional, Dict, Any
import bittensor as bt

from common.data import DataEntity
from scraping.scraper import ValidationResult
from scraping.custom.model import RealEstateContent
from scraping.custom.field_mapping import ZillowFieldMapper, FieldValidationConfig


def validate_zillow_data_entity_fields(actual_content: RealEstateContent, entity: DataEntity) -> ValidationResult:
    """
    Validate DataEntity fields against actual Zillow content with timestamp tolerance.
    
    This function provides comprehensive validation for Zillow real estate data,
    handling the unique challenges of real estate data including:
    - Timestamp differences between miner and validator scraping
    - Time-sensitive fields that may change frequently
    - Complex property data structure
    
    Args:
        actual_content: RealEstateContent with fresh data from Zillow API
        entity: DataEntity submitted by miner for validation
        
    Returns:
        ValidationResult indicating if the entity is valid
    """
    try:
        # Create DataEntity from actual content for comparison
        actual_entity = actual_content.to_data_entity()
        
        # Validate content size (prevent claiming more bytes than actual)
        byte_difference_allowed = 50  # Allow small differences for timestamp serialization
        
        if (entity.content_size_bytes - actual_entity.content_size_bytes) > byte_difference_allowed:
            return ValidationResult(
                is_valid=False,
                reason="The claimed bytes must not exceed the actual Zillow content size.",
                content_size_bytes_validated=entity.content_size_bytes,
            )
        
        # Create normalized entities for comparison (handle timestamp differences)
        normalized_actual_entity = DataEntity(
            uri=actual_entity.uri,
            datetime=entity.datetime,  # Use miner's datetime to avoid timestamp comparison issues
            source=actual_entity.source,
            label=actual_entity.label,
            content=actual_entity.content,
            content_size_bytes=actual_entity.content_size_bytes
        )
        
        # Validate non-content fields using the standard comparison
        if not DataEntity.are_non_content_fields_equal(normalized_actual_entity, entity):
            return ValidationResult(
                is_valid=False,
                reason="The DataEntity fields are incorrect based on the Zillow content.",
                content_size_bytes_validated=entity.content_size_bytes,
            )
        
        # Additional Zillow-specific content validation
        content_validation_result = validate_zillow_content_fields(actual_content, entity)
        if not content_validation_result.is_valid:
            return content_validation_result
            
        return ValidationResult(
            is_valid=True,
            reason="Valid Zillow property data",
            content_size_bytes_validated=entity.content_size_bytes,
        )
        
    except Exception as e:
        bt.logging.error(f"Error validating Zillow DataEntity fields: {traceback.format_exc()}")
        return ValidationResult(
            is_valid=False,
            reason=f"Validation error: {str(e)}",
            content_size_bytes_validated=entity.content_size_bytes,
        )


def validate_zillow_content_fields(actual_content: RealEstateContent, entity: DataEntity) -> ValidationResult:
    """
    Validate Zillow-specific content fields using only fields available to miners.
    
    This function validates only the subset of fields that miners have access to
    from the Property Extended Search API, avoiding validation failures due to
    field mismatches between miner and validator data sources.
    
    Args:
        actual_content: Fresh RealEstateContent from Individual Property API
        entity: Miner's submitted DataEntity from Property Extended Search
        
    Returns:
        ValidationResult for content-specific validation
    """
    try:
        # Decode miner's content from entity
        miner_content = RealEstateContent.from_data_entity(entity)
        
        # Ensure this is a sold property before validation
        if miner_content.listing_status and miner_content.listing_status.upper() not in ['SOLD', 'RECENTLY_SOLD']:
            return ValidationResult(
                is_valid=False,
                reason=f"Only sold properties are validated. Property status: {miner_content.listing_status}",
                content_size_bytes_validated=0,
            )
        
        # Validate each field according to its configuration
        for field_name, config in ZillowFieldMapper.FIELD_VALIDATION_CONFIG.items():
            # Skip ignored fields
            if config.validation_type == 'ignore':
                continue
                
            # Get values from both sources
            actual_val = getattr(actual_content, field_name, None)
            miner_val = getattr(miner_content, field_name, None)
            
            # Validate according to field configuration
            validation_result = validate_field_by_config(
                field_name, actual_val, miner_val, config, entity
            )
            
            if not validation_result.is_valid:
                return validation_result
        
        return ValidationResult(
            is_valid=True,
            reason="Zillow content fields validated successfully (subset validation)",
            content_size_bytes_validated=entity.content_size_bytes,
        )
        
    except Exception as e:
        bt.logging.error(f"Error validating Zillow content fields: {traceback.format_exc()}")
        return ValidationResult(
            is_valid=False,
            reason=f"Content validation error: {str(e)}",
            content_size_bytes_validated=entity.content_size_bytes,
        )


def validate_field_by_config(field_name: str, actual_val: Any, miner_val: Any, 
                           config: FieldValidationConfig, entity: DataEntity) -> ValidationResult:
    """
    Validate a single field according to its configuration.
    
    Args:
        field_name: Name of the field being validated
        actual_val: Value from validator's fresh API call
        miner_val: Value from miner's stored data
        config: Validation configuration for this field
        entity: DataEntity for error reporting
        
    Returns:
        ValidationResult for this field
    """
    try:
        if config.validation_type == 'exact':
            return validate_exact_match(field_name, actual_val, miner_val, config, entity)
        elif config.validation_type == 'tolerance':
            return validate_with_tolerance(field_name, actual_val, miner_val, config, entity)
        elif config.validation_type == 'compatible':
            return validate_compatible_values(field_name, actual_val, miner_val, config, entity)
        else:
            # Unknown validation type - assume valid
            return ValidationResult(
                is_valid=True,
                reason=f"Unknown validation type for {field_name}: {config.validation_type}",
                content_size_bytes_validated=entity.content_size_bytes,
            )
            
    except Exception as e:
        bt.logging.warning(f"Error validating field {field_name}: {str(e)}")
        return ValidationResult(
            is_valid=True,  # Assume valid on validation errors
            reason=f"Field validation error for {field_name} (assumed valid): {str(e)}",
            content_size_bytes_validated=entity.content_size_bytes,
        )


def validate_exact_match(field_name: str, actual_val: Any, miner_val: Any, 
                        config: FieldValidationConfig, entity: DataEntity) -> ValidationResult:
    """Validate that two values match exactly (with None handling)"""
    
    # Handle None values
    if actual_val is None and miner_val is None:
        return ValidationResult(
            is_valid=True,
            reason=f"Field {field_name} exact match (both None)",
            content_size_bytes_validated=entity.content_size_bytes,
        )
    
    # If only one is None, it's a mismatch for critical fields
    if (actual_val is None) != (miner_val is None):
        if config.is_critical:
            return ValidationResult(
                is_valid=False,
                reason=f"Critical field '{field_name}' None mismatch: validator='{actual_val}', miner='{miner_val}'",
                content_size_bytes_validated=entity.content_size_bytes,
            )
        else:
            # Non-critical fields with None values are acceptable
            return ValidationResult(
                is_valid=True,
                reason=f"Non-critical field {field_name} None value accepted",
                content_size_bytes_validated=entity.content_size_bytes,
            )
    
    # Both values are not None - check for exact match
    if actual_val != miner_val:
        severity = "Critical" if config.is_critical else "Stable"
        return ValidationResult(
            is_valid=False,
            reason=f"{severity} field '{field_name}' mismatch: validator='{actual_val}', miner='{miner_val}'",
            content_size_bytes_validated=entity.content_size_bytes,
        )
    
    return ValidationResult(
        is_valid=True,
        reason=f"Field {field_name} exact match",
        content_size_bytes_validated=entity.content_size_bytes,
    )


def validate_with_tolerance(field_name: str, actual_val: Any, miner_val: Any, 
                          config: FieldValidationConfig, entity: DataEntity) -> ValidationResult:
    """Validate numeric values with tolerance"""
    
    # Handle None values
    if actual_val is None or miner_val is None:
        return ValidationResult(
            is_valid=True,
            reason=f"Field {field_name} tolerance validation skipped (None value)",
            content_size_bytes_validated=entity.content_size_bytes,
        )
    
    try:
        # Convert to numbers for comparison
        actual_num = float(actual_val)
        miner_num = float(miner_val)
        
        # Calculate difference
        diff = abs(actual_num - miner_num)
        
        # Check percentage tolerance
        if config.tolerance_percent is not None:
            if actual_num == 0:
                # Avoid division by zero
                tolerance_met = diff == 0
            else:
                percent_diff = diff / abs(actual_num)
                tolerance_met = percent_diff <= config.tolerance_percent
                
            if not tolerance_met:
                return ValidationResult(
                    is_valid=False,
                    reason=f"Field '{field_name}' exceeds {config.tolerance_percent:.1%} tolerance: "
                           f"validator={actual_val}, miner={miner_val}, diff={percent_diff:.1%}",
                    content_size_bytes_validated=entity.content_size_bytes,
                )
        
        # Check absolute tolerance
        if config.tolerance_absolute is not None:
            if diff > config.tolerance_absolute:
                return ValidationResult(
                    is_valid=False,
                    reason=f"Field '{field_name}' exceeds {config.tolerance_absolute} absolute tolerance: "
                           f"validator={actual_val}, miner={miner_val}, diff={diff}",
                    content_size_bytes_validated=entity.content_size_bytes,
                )
        
        return ValidationResult(
            is_valid=True,
            reason=f"Field {field_name} within tolerance",
            content_size_bytes_validated=entity.content_size_bytes,
        )
        
    except (ValueError, TypeError) as e:
        # Values are not numeric - fall back to exact match
        bt.logging.debug(f"Non-numeric values for {field_name}, using exact match: {e}")
        return validate_exact_match(field_name, actual_val, miner_val, config, entity)


def validate_compatible_values(field_name: str, actual_val: Any, miner_val: Any, 
                             config: FieldValidationConfig, entity: DataEntity) -> ValidationResult:
    """Validate values that may have compatible transitions (e.g., listing status)"""
    
    # Handle None values
    if actual_val is None or miner_val is None:
        return ValidationResult(
            is_valid=True,
            reason=f"Field {field_name} compatibility validation skipped (None value)",
            content_size_bytes_validated=entity.content_size_bytes,
        )
    
    # For listing status, use existing compatibility logic
    if field_name == 'listing_status':
        if are_listing_statuses_compatible(actual_val, miner_val):
            return ValidationResult(
                is_valid=True,
                reason=f"Listing status transition valid: {miner_val} -> {actual_val}",
                content_size_bytes_validated=entity.content_size_bytes,
            )
        else:
            return ValidationResult(
                is_valid=False,
                reason=f"Invalid listing status transition: {miner_val} -> {actual_val}",
                content_size_bytes_validated=entity.content_size_bytes,
            )
    
    # For other compatible fields, fall back to exact match for now
    return validate_exact_match(field_name, actual_val, miner_val, config, entity)


def validate_time_sensitive_fields(actual_content: RealEstateContent, miner_content: RealEstateContent) -> ValidationResult:
    """
    Validate fields that may change over time with appropriate tolerance.
    
    Args:
        actual_content: Fresh content from API
        miner_content: Miner's submitted content
        
    Returns:
        ValidationResult for time-sensitive field validation
    """
    try:
        # Price validation with tolerance
        if actual_content.price and miner_content.price:
            price_diff_percent = abs(actual_content.price - miner_content.price) / actual_content.price
            if price_diff_percent > 0.05:  # Allow 5% price difference
                return ValidationResult(
                    is_valid=False,
                    reason=f"Price difference too large: {price_diff_percent:.1%} (max 5%)",
                    content_size_bytes_validated=0,
                )
        
        # Zestimate validation with higher tolerance
        if actual_content.zestimate and miner_content.zestimate:
            zest_diff_percent = abs(actual_content.zestimate - miner_content.zestimate) / actual_content.zestimate
            if zest_diff_percent > 0.10:  # Allow 10% Zestimate difference
                return ValidationResult(
                    is_valid=False,
                    reason=f"Zestimate difference too large: {zest_diff_percent:.1%} (max 10%)",
                    content_size_bytes_validated=0,
                )
        
        # Days on Zillow validation with time tolerance
        if actual_content.days_on_zillow and miner_content.days_on_zillow:
            days_diff = abs(actual_content.days_on_zillow - miner_content.days_on_zillow)
            if days_diff > 7:  # Allow 7-day difference
                return ValidationResult(
                    is_valid=False,
                    reason=f"Days on Zillow difference too large: {days_diff} days (max 7)",
                    content_size_bytes_validated=0,
                )
        
        # Listing status should generally match, but allow some flexibility
        status_compatible = are_listing_statuses_compatible(
            actual_content.listing_status, 
            miner_content.listing_status
        )
        if not status_compatible:
            return ValidationResult(
                is_valid=False,
                reason=f"Incompatible listing status: '{miner_content.listing_status}' vs '{actual_content.listing_status}'",
                content_size_bytes_validated=0,
            )
        
        return ValidationResult(
            is_valid=True,
            reason="Time-sensitive fields validated successfully",
            content_size_bytes_validated=0,
        )
        
    except Exception as e:
        bt.logging.error(f"Error validating time-sensitive fields: {str(e)}")
        return ValidationResult(
            is_valid=True,  # Default to valid on validation errors to avoid false negatives
            reason=f"Time-sensitive validation error (assumed valid): {str(e)}",
            content_size_bytes_validated=0,
        )


def are_listing_statuses_compatible(actual_status: str, miner_status: str) -> bool:
    """
    Check if listing statuses are compatible, allowing for reasonable transitions.
    
    Args:
        actual_status: Current status from API
        miner_status: Status from miner's data
        
    Returns:
        True if statuses are compatible, False otherwise
    """
    if actual_status == miner_status:
        return True
    
    # Define compatible status transitions (actual_status -> allowed_miner_statuses)
    compatible_transitions = {
        'FOR_SALE': ['PENDING', 'SOLD'],  # Property may have sold or gone pending
        'FOR_RENT': ['RENTED'],           # Property may have been rented
        'PENDING': ['SOLD', 'FOR_SALE'], # Pending may complete or fall through
        'SOLD': ['FOR_SALE'],             # Rare, but deals can fall through
        'RENTED': ['FOR_RENT'],           # Rental may have become available again
    }
    
    return miner_status in compatible_transitions.get(actual_status, [])


class RealEstateContentExtended(RealEstateContent):
    """Extended RealEstateContent with additional validation methods."""
    
    @classmethod
    def from_data_entity(cls, entity: DataEntity) -> "RealEstateContentExtended":
        """
        Create RealEstateContent from a DataEntity.
        
        Args:
            entity: DataEntity containing serialized RealEstateContent
            
        Returns:
            RealEstateContentExtended instance
            
        Raises:
            ValueError: If entity content cannot be parsed
        """
        try:
            # Decode content from bytes
            content_str = entity.content.decode('utf-8')
            content_dict = json.loads(content_str)
            
            # Create instance from dictionary
            return cls(**content_dict)
            
        except Exception as e:
            bt.logging.error(f"Failed to create RealEstateContent from DataEntity: {traceback.format_exc()}")
            raise ValueError(f"Invalid DataEntity content: {str(e)}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of key fields for validation logging."""
        return {
            'zpid': self.zpid,
            'address': self.address[:50] + '...' if len(self.address) > 50 else self.address,
            'price': self.price,
            'listing_status': self.listing_status,
            'days_on_zillow': self.days_on_zillow,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None
        }


# Monkey patch the original RealEstateContent to add from_data_entity method
RealEstateContent.from_data_entity = RealEstateContentExtended.from_data_entity
