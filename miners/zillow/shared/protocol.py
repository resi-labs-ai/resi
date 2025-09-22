"""
Shared protocol definitions for both API and web scraping implementations.
"""

import bittensor as bt
from pydantic import Field, ConfigDict
from typing import List, Optional
from common.data import DataEntity, DataSource


class ZpidScrapeRequest(bt.Synapse):
    """Protocol for ZPID-based property scraping requests"""
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )

    # Request parameters
    zpids: List[str] = Field(
        description="List of Zillow Property IDs to scrape",
        max_length=50  # Limit batch size for performance
    )
    
    source: DataSource = Field(
        default=DataSource.RAPID_ZILLOW,
        description="Data source (should be RAPID_ZILLOW for real estate)"
    )
    
    priority: Optional[float] = Field(
        default=1.0,
        description="Priority weight for this request"
    )
    
    # Response fields
    scraped_properties: List[DataEntity] = Field(
        default_factory=list,
        description="Scraped property data entities"
    )
    
    success_count: int = Field(
        default=0,
        description="Number of successfully scraped properties"
    )
    
    failed_zpids: List[str] = Field(
        default_factory=list,
        description="ZPIDs that failed to scrape"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages for failed scrapes"
    )
    
    version: Optional[int] = Field(
        default=None,
        description="Protocol version"
    )


def is_valid_zpid(zpid: str) -> bool:
    """Validate ZPID format"""
    if not zpid:
        return False
    
    # Remove _zpid suffix if present
    clean_zpid = zpid.replace("_zpid", "")
    
    # Should be numeric and reasonable length (6-10 digits)
    return clean_zpid.isdigit() and 6 <= len(clean_zpid) <= 10


def normalize_zpid(zpid: str) -> str:
    """Normalize ZPID to consistent format"""
    clean_zpid = zpid.replace("_zpid", "")
    return clean_zpid if clean_zpid.isdigit() else zpid


def zpid_to_url(zpid: str) -> str:
    """Convert ZPID to Zillow URL format"""
    clean_zpid = normalize_zpid(zpid)
    # Note: We need the address part for the URL, which we don't have from just ZPID
    # This will need to be handled by the scraper implementation
    return f"https://www.zillow.com/homedetails/ADDRESS/{clean_zpid}_zpid/"
