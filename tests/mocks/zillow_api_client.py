"""
Mock Zillow API Client for Testing

This module provides a mock implementation of the Zillow API that uses
locally stored real API responses for testing. It enables comprehensive
offline testing while maintaining the ability to fall back to live API
calls when needed.

Usage:
    # Use in tests
    mock_client = MockZillowAPIClient("mocked_data")
    search_data = await mock_client.get_property_search("78041")
    property_data = await mock_client.get_individual_property("70982473")
    
    # Enable live API fallback
    mock_client = MockZillowAPIClient("mocked_data", api_key="your_key", enable_fallback=True)
"""

import asyncio
import json
import os
import httpx
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import bittensor as bt


class MockZillowAPIClient:
    """Mock Zillow API client that uses locally stored real API responses"""
    
    def __init__(self, data_dir: str, api_key: Optional[str] = None, enable_fallback: bool = False):
        """
        Initialize the mock API client.
        
        Args:
            data_dir: Directory containing stored API responses
            api_key: RapidAPI key for fallback calls (optional)
            enable_fallback: Whether to fall back to live API for missing data
        """
        self.data_dir = Path(data_dir)
        self.search_dir = self.data_dir / "property_extended_search"
        self.property_dir = self.data_dir / "individual_properties"
        
        # Fallback configuration
        self.enable_fallback = enable_fallback and api_key is not None
        self.api_key = api_key
        
        if self.enable_fallback:
            self.base_url = "https://zillow-com1.p.rapidapi.com"
            self.headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
            }
            self.last_request_time = 0
            self.min_request_interval = 1.0  # Rate limiting for fallback
        
        # Statistics
        self.stats = {
            'mock_hits': 0,
            'fallback_calls': 0,
            'cache_misses': 0,
            'errors': 0
        }
        
        # Load available data on initialization
        self._load_available_data()
    
    def _load_available_data(self):
        """Load information about available mock data"""
        self.available_searches = {}
        self.available_properties = {}
        
        # Load search data mappings
        if self.search_dir.exists():
            for file_path in self.search_dir.glob("*.json"):
                # Extract zipcode from filename (e.g., "78041_laredo_tx.json" -> "78041")
                zipcode = file_path.stem.split("_")[0]
                self.available_searches[zipcode] = file_path
        
        # Load property data mappings
        if self.property_dir.exists():
            for file_path in self.property_dir.glob("*.json"):
                # Extract zpid from filename (e.g., "70982473_78041.json" -> "70982473")
                zpid = file_path.stem.split("_")[0]
                self.available_properties[zpid] = file_path
        
        bt.logging.info(f"MockZillowAPIClient loaded: {len(self.available_searches)} searches, {len(self.available_properties)} properties")
    
    async def get_property_search(self, location: str, sort: str = "Newest", page: int = 1) -> Optional[Dict[str, Any]]:
        """
        Get property search results for a location (zipcode).
        
        Args:
            location: Zipcode or location string
            sort: Sort order (default: "Newest")
            page: Page number (default: 1)
            
        Returns:
            Property search results or None if not found
        """
        # Normalize location to zipcode
        zipcode = self._normalize_location(location)
        
        # Try to load from mock data first
        if zipcode in self.available_searches:
            try:
                with open(self.available_searches[zipcode], 'r') as f:
                    data = json.load(f)
                
                self.stats['mock_hits'] += 1
                bt.logging.debug(f"Mock hit: Property search for {zipcode}")
                
                # Remove metadata before returning
                if '_metadata' in data:
                    del data['_metadata']
                
                return data
                
            except Exception as e:
                bt.logging.error(f"Error loading mock search data for {zipcode}: {e}")
                self.stats['errors'] += 1
        
        # Try fallback to live API if enabled
        if self.enable_fallback:
            bt.logging.info(f"Mock miss: Falling back to live API for search {zipcode}")
            return await self._fallback_property_search(location, sort, page)
        
        # No data available
        self.stats['cache_misses'] += 1
        bt.logging.warning(f"No mock data available for search {zipcode}")
        return None
    
    async def get_individual_property(self, zpid: str) -> Optional[Dict[str, Any]]:
        """
        Get individual property data by zpid.
        
        Args:
            zpid: Zillow Property ID
            
        Returns:
            Individual property data or None if not found
        """
        zpid = str(zpid)  # Ensure string format
        
        # Try to load from mock data first
        if zpid in self.available_properties:
            try:
                with open(self.available_properties[zpid], 'r') as f:
                    data = json.load(f)
                
                self.stats['mock_hits'] += 1
                bt.logging.debug(f"Mock hit: Individual property for zpid {zpid}")
                
                # Remove metadata before returning
                if '_metadata' in data:
                    del data['_metadata']
                
                return data
                
            except Exception as e:
                bt.logging.error(f"Error loading mock property data for zpid {zpid}: {e}")
                self.stats['errors'] += 1
        
        # Try fallback to live API if enabled
        if self.enable_fallback:
            bt.logging.info(f"Mock miss: Falling back to live API for property {zpid}")
            return await self._fallback_individual_property(zpid)
        
        # No data available
        self.stats['cache_misses'] += 1
        bt.logging.warning(f"No mock data available for property {zpid}")
        return None
    
    async def _fallback_property_search(self, location: str, sort: str, page: int) -> Optional[Dict[str, Any]]:
        """Fallback to live API for property search"""
        try:
            await self._rate_limit()
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "location": location,
                    "sort": sort,
                    "page": page
                }
                
                response = await client.get(
                    f"{self.base_url}/propertyExtendedSearch",
                    headers=self.headers,
                    params=params
                )
                
                self.stats['fallback_calls'] += 1
                
                if response.status_code == 200:
                    return response.json()
                else:
                    bt.logging.error(f"Fallback API error for search {location}: {response.status_code}")
                    return None
                    
        except Exception as e:
            bt.logging.error(f"Fallback search error for {location}: {e}")
            self.stats['errors'] += 1
            return None
    
    async def _fallback_individual_property(self, zpid: str) -> Optional[Dict[str, Any]]:
        """Fallback to live API for individual property"""
        try:
            await self._rate_limit()
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {"zpid": zpid}
                
                response = await client.get(
                    f"{self.base_url}/property",
                    headers=self.headers,
                    params=params
                )
                
                self.stats['fallback_calls'] += 1
                
                if response.status_code == 200:
                    return response.json()
                else:
                    bt.logging.error(f"Fallback API error for property {zpid}: {response.status_code}")
                    return None
                    
        except Exception as e:
            bt.logging.error(f"Fallback property error for {zpid}: {e}")
            self.stats['errors'] += 1
            return None
    
    async def _rate_limit(self):
        """Rate limiting for fallback API calls"""
        if not self.enable_fallback:
            return
            
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location string to zipcode format"""
        # Handle various location formats
        location = location.strip()
        
        # If it's already a 5-digit zipcode, return as-is
        if location.isdigit() and len(location) == 5:
            return location
        
        # Try to extract zipcode from location string
        # This is a simple implementation - could be enhanced
        import re
        zipcode_match = re.search(r'\b(\d{5})\b', location)
        if zipcode_match:
            return zipcode_match.group(1)
        
        # Return original if we can't normalize
        return location
    
    def get_available_zipcodes(self) -> List[str]:
        """Get list of available zipcodes in mock data"""
        return list(self.available_searches.keys())
    
    def get_available_zpids(self) -> List[str]:
        """Get list of available zpids in mock data"""
        return list(self.available_properties.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        total_requests = self.stats['mock_hits'] + self.stats['fallback_calls'] + self.stats['cache_misses']
        
        return {
            'total_requests': total_requests,
            'mock_hit_rate': self.stats['mock_hits'] / max(total_requests, 1),
            'fallback_rate': self.stats['fallback_calls'] / max(total_requests, 1),
            'cache_miss_rate': self.stats['cache_misses'] / max(total_requests, 1),
            'error_rate': self.stats['errors'] / max(total_requests, 1),
            'raw_stats': self.stats.copy()
        }
    
    def validate_data_freshness(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Validate the freshness of stored mock data.
        
        Args:
            max_age_hours: Maximum age in hours before data is considered stale
            
        Returns:
            Dictionary with freshness information
        """
        current_time = datetime.now(timezone.utc)
        stale_files = []
        fresh_files = []
        
        # Check search data freshness
        for zipcode, file_path in self.available_searches.items():
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if '_metadata' in data and 'collected_at' in data['_metadata']:
                    collected_at = datetime.fromisoformat(data['_metadata']['collected_at'].replace('Z', '+00:00'))
                    age_hours = (current_time - collected_at).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        stale_files.append({'type': 'search', 'id': zipcode, 'age_hours': age_hours})
                    else:
                        fresh_files.append({'type': 'search', 'id': zipcode, 'age_hours': age_hours})
                        
            except Exception as e:
                bt.logging.warning(f"Error checking freshness for search {zipcode}: {e}")
        
        # Check property data freshness (sample a few to avoid performance issues)
        sample_properties = list(self.available_properties.items())[:10]  # Sample first 10
        
        for zpid, file_path in sample_properties:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if '_metadata' in data and 'collected_at' in data['_metadata']:
                    collected_at = datetime.fromisoformat(data['_metadata']['collected_at'].replace('Z', '+00:00'))
                    age_hours = (current_time - collected_at).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        stale_files.append({'type': 'property', 'id': zpid, 'age_hours': age_hours})
                    else:
                        fresh_files.append({'type': 'property', 'id': zpid, 'age_hours': age_hours})
                        
            except Exception as e:
                bt.logging.warning(f"Error checking freshness for property {zpid}: {e}")
        
        return {
            'fresh_files': len(fresh_files),
            'stale_files': len(stale_files),
            'freshness_rate': len(fresh_files) / max(len(fresh_files) + len(stale_files), 1),
            'max_age_hours': max_age_hours,
            'stale_details': stale_files[:5],  # Show first 5 stale files
            'sample_fresh': fresh_files[:5]    # Show first 5 fresh files
        }
    
    def __repr__(self):
        """String representation of the mock client"""
        return (f"MockZillowAPIClient(searches={len(self.available_searches)}, "
                f"properties={len(self.available_properties)}, "
                f"fallback={'enabled' if self.enable_fallback else 'disabled'})")


class MockZillowScraperIntegration:
    """Integration helper to use MockZillowAPIClient with existing scrapers"""
    
    def __init__(self, mock_client: MockZillowAPIClient):
        self.mock_client = mock_client
    
    async def patch_scraper(self, scraper_instance):
        """
        Patch an existing scraper instance to use mock data.
        
        This replaces the scraper's HTTP calls with mock data calls.
        """
        # Store original methods
        scraper_instance._original_http_get = getattr(scraper_instance, '_http_get', None)
        
        # Replace with mock methods
        scraper_instance._http_get = self._mock_http_get
        
        # Add reference to mock client
        scraper_instance._mock_client = self.mock_client
    
    async def _mock_http_get(self, url: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Mock HTTP GET method that uses stored data"""
        
        # Determine which endpoint is being called
        if "propertyExtendedSearch" in url:
            location = params.get("location", "")
            sort = params.get("sort", "Newest")
            page = params.get("page", 1)
            
            result = await self.mock_client.get_property_search(location, sort, page)
            if result is None:
                raise Exception(f"No mock data available for search: {location}")
            return result
            
        elif "property" in url and "zpid" in params:
            zpid = params.get("zpid", "")
            
            result = await self.mock_client.get_individual_property(zpid)
            if result is None:
                raise Exception(f"No mock data available for property: {zpid}")
            return result
            
        else:
            raise Exception(f"Unsupported mock API endpoint: {url}")


# Convenience function for easy testing
async def create_mock_client_from_collected_data(data_dir: str = "mocked_data", 
                                               api_key: Optional[str] = None,
                                               enable_fallback: bool = False) -> MockZillowAPIClient:
    """
    Create a mock client using the collected real data.
    
    Args:
        data_dir: Directory containing collected API responses
        api_key: RapidAPI key for fallback (optional)
        enable_fallback: Whether to enable live API fallback
        
    Returns:
        Configured MockZillowAPIClient instance
    """
    client = MockZillowAPIClient(data_dir, api_key, enable_fallback)
    
    bt.logging.info(f"Created mock client with {len(client.get_available_zipcodes())} zipcodes "
                   f"and {len(client.get_available_zpids())} properties")
    
    return client
