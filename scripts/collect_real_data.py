#!/usr/bin/env python3
"""
Real Zillow Data Collection Script

This script collects real API responses from Zillow for comprehensive testing.
It fetches data for multiple zipcodes and all their properties to create
a robust offline testing dataset.

Usage:
    python scripts/collect_real_data.py --api-key YOUR_RAPIDAPI_KEY
    
    # Collect specific zipcodes only
    python scripts/collect_real_data.py --api-key YOUR_KEY --zipcodes 78041,90210
    
    # Skip property collection (search only)
    python scripts/collect_real_data.py --api-key YOUR_KEY --search-only
"""

import asyncio
import json
import os
import sys
import argparse
import httpx
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import bittensor as bt
from scraping.zillow.model import RealEstateContent

class ZillowDataCollector:
    """Collects real Zillow API responses for testing purposes"""
    
    def __init__(self, api_key: str, base_dir: str = "mocked_data"):
        self.api_key = api_key
        self.base_dir = Path(base_dir)
        self.search_dir = self.base_dir / "property_extended_search"
        self.property_dir = self.base_dir / "individual_properties"
        
        # Create directories if they don't exist
        self.search_dir.mkdir(parents=True, exist_ok=True)
        self.property_dir.mkdir(parents=True, exist_ok=True)
        
        # API configuration
        self.base_url = "https://zillow-com1.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
        # Statistics
        self.stats = {
            'zipcodes_collected': 0,
            'properties_found': 0,
            'properties_collected': 0,
            'api_calls_made': 0,
            'errors_encountered': 0,
            'start_time': None,
            'end_time': None
        }

    async def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            bt.logging.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()

    async def collect_zipcode_search_data(self, zipcode: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
        """Collect Property Extended Search data for a zipcode"""
        try:
            await self._rate_limit()
            
            params = {
                "location": zipcode,
                "sort": "Newest",
                "page": 1
            }
            
            bt.logging.info(f"Fetching search data for zipcode: {zipcode}")
            response = await client.get(
                f"{self.base_url}/propertyExtendedSearch",
                headers=self.headers,
                params=params,
                timeout=15.0
            )
            
            self.stats['api_calls_made'] += 1
            
            if response.status_code == 200:
                data = response.json()
                
                # Save to file
                filename = f"{zipcode}_{self._get_location_name(zipcode)}.json"
                filepath = self.search_dir / filename
                
                # Add metadata
                data['_metadata'] = {
                    'collected_at': datetime.now(timezone.utc).isoformat(),
                    'zipcode': zipcode,
                    'api_endpoint': 'propertyExtendedSearch',
                    'response_code': response.status_code
                }
                
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                bt.logging.info(f"✅ Saved search data for {zipcode}: {len(data.get('props', []))} properties")
                self.stats['zipcodes_collected'] += 1
                self.stats['properties_found'] += len(data.get('props', []))
                
                return data
            else:
                bt.logging.error(f"❌ Search API error for {zipcode}: {response.status_code} - {response.text}")
                self.stats['errors_encountered'] += 1
                return None
                
        except Exception as e:
            bt.logging.error(f"❌ Exception collecting search data for {zipcode}: {str(e)}")
            self.stats['errors_encountered'] += 1
            return None

    async def collect_individual_property_data(self, zpid: str, zipcode: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
        """Collect Individual Property data for a zpid"""
        try:
            await self._rate_limit()
            
            params = {"zpid": zpid}
            
            bt.logging.debug(f"Fetching property data for zpid: {zpid}")
            response = await client.get(
                f"{self.base_url}/property",
                headers=self.headers,
                params=params,
                timeout=15.0
            )
            
            self.stats['api_calls_made'] += 1
            
            if response.status_code == 200:
                data = response.json()
                
                # Save to file
                filename = f"{zpid}_{zipcode}.json"
                filepath = self.property_dir / filename
                
                # Add metadata
                data['_metadata'] = {
                    'collected_at': datetime.now(timezone.utc).isoformat(),
                    'zpid': zpid,
                    'zipcode': zipcode,
                    'api_endpoint': 'property',
                    'response_code': response.status_code
                }
                
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                bt.logging.debug(f"✅ Saved property data for zpid {zpid}")
                self.stats['properties_collected'] += 1
                
                return data
            else:
                bt.logging.warning(f"⚠️ Property API error for zpid {zpid}: {response.status_code}")
                self.stats['errors_encountered'] += 1
                return None
                
        except Exception as e:
            bt.logging.warning(f"⚠️ Exception collecting property data for zpid {zpid}: {str(e)}")
            self.stats['errors_encountered'] += 1
            return None

    def extract_zpids_from_search_data(self, search_data: Dict[str, Any]) -> List[str]:
        """Extract all zpids from search results"""
        zpids = []
        props = search_data.get('props', [])
        
        for prop in props:
            zpid = prop.get('zpid')
            if zpid:
                zpids.append(str(zpid))
        
        bt.logging.info(f"Extracted {len(zpids)} zpids from search results")
        return zpids

    async def collect_all_data(self, zipcodes: List[str], search_only: bool = False) -> Dict[str, Any]:
        """Orchestrate complete data collection"""
        bt.logging.info(f"🚀 Starting data collection for {len(zipcodes)} zipcodes")
        bt.logging.info(f"📁 Saving data to: {self.base_dir.absolute()}")
        
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            all_zpids = []
            
            # Phase 1: Collect search data for all zipcodes
            bt.logging.info("📍 Phase 1: Collecting search data for zipcodes...")
            for zipcode in zipcodes:
                search_data = await self.collect_zipcode_search_data(zipcode, client)
                
                if search_data:
                    zpids = self.extract_zpids_from_search_data(search_data)
                    for zpid in zpids:
                        all_zpids.append((zpid, zipcode))
                
                # Small delay between zipcodes
                await asyncio.sleep(0.5)
            
            if search_only:
                bt.logging.info("🛑 Search-only mode: Skipping individual property collection")
            else:
                # Phase 2: Collect individual property data
                bt.logging.info(f"🏠 Phase 2: Collecting individual property data for {len(all_zpids)} properties...")
                
                for i, (zpid, zipcode) in enumerate(all_zpids):
                    if i > 0 and i % 10 == 0:
                        bt.logging.info(f"Progress: {i}/{len(all_zpids)} properties collected")
                    
                    await self.collect_individual_property_data(zpid, zipcode, client)
                    
                    # Small delay between properties
                    await asyncio.sleep(0.2)
        
        self.stats['end_time'] = datetime.now(timezone.utc)
        return self._generate_collection_report()

    def _generate_collection_report(self) -> Dict[str, Any]:
        """Generate a comprehensive collection report"""
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        report = {
            'collection_summary': {
                'zipcodes_processed': self.stats['zipcodes_collected'],
                'properties_found': self.stats['properties_found'],
                'properties_collected': self.stats['properties_collected'],
                'total_api_calls': self.stats['api_calls_made'],
                'errors_encountered': self.stats['errors_encountered'],
                'duration_seconds': duration,
                'collection_rate': f"{self.stats['properties_collected'] / duration:.2f} properties/sec" if duration else "N/A"
            },
            'file_locations': {
                'search_data': str(self.search_dir.absolute()),
                'property_data': str(self.property_dir.absolute())
            },
            'collected_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Save report
        report_path = self.base_dir / "collection_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report

    def _get_location_name(self, zipcode: str) -> str:
        """Get a friendly location name for zipcode (for filename)"""
        location_map = {
            '78041': 'laredo_tx',
            '90210': 'beverly_hills_ca',
            '10001': 'manhattan_ny',
            '30309': 'atlanta_ga',
            '77494': 'katy_tx',
            '33101': 'miami_fl',
            '85001': 'phoenix_az',
            '98101': 'seattle_wa',
            '60601': 'chicago_il',
            '37201': 'nashville_tn'
        }
        return location_map.get(zipcode, f'zip_{zipcode}')

# Default zipcodes for comprehensive testing
DEFAULT_ZIPCODES = [
    '78041',  # Laredo, TX - Your example, border town
    '90210',  # Beverly Hills, CA - High-value market
    '10001',  # Manhattan, NY - Urban high-density
    '30309',  # Atlanta, GA - Mid-market suburban
    '77494',  # Katy, TX - Suburban family market
    '33101',  # Miami, FL - Coastal luxury market
    '85001',  # Phoenix, AZ - Desert growth market
    '98101',  # Seattle, WA - Tech hub market
    '60601',  # Chicago, IL - Midwest urban
    '37201',  # Nashville, TN - Music city growth
]

async def main():
    parser = argparse.ArgumentParser(description='Collect real Zillow API data for testing')
    parser.add_argument('--api-key', required=True, help='RapidAPI key for Zillow API')
    parser.add_argument('--zipcodes', help='Comma-separated list of zipcodes (default: predefined list)')
    parser.add_argument('--search-only', action='store_true', help='Only collect search data, skip individual properties')
    parser.add_argument('--output-dir', default='mocked_data', help='Output directory for collected data')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        bt.logging.set_trace(True)
        bt.logging.set_debug(True)
    else:
        bt.logging.set_info(True)
    
    # Parse zipcodes
    if args.zipcodes:
        zipcodes = [zip.strip() for zip in args.zipcodes.split(',')]
    else:
        zipcodes = DEFAULT_ZIPCODES
    
    bt.logging.info(f"🎯 Target zipcodes: {', '.join(zipcodes)}")
    
    # Initialize collector
    collector = ZillowDataCollector(args.api_key, args.output_dir)
    
    try:
        # Collect data
        report = await collector.collect_all_data(zipcodes, args.search_only)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 COLLECTION COMPLETE!")
        print("="*60)
        print(f"✅ Zipcodes processed: {report['collection_summary']['zipcodes_processed']}")
        print(f"🏠 Properties found: {report['collection_summary']['properties_found']}")
        print(f"💾 Properties collected: {report['collection_summary']['properties_collected']}")
        print(f"🌐 Total API calls: {report['collection_summary']['total_api_calls']}")
        print(f"⚠️ Errors encountered: {report['collection_summary']['errors_encountered']}")
        print(f"⏱️ Duration: {report['collection_summary']['duration_seconds']:.1f} seconds")
        print(f"🚀 Collection rate: {report['collection_summary']['collection_rate']}")
        print(f"📁 Data saved to: {args.output_dir}/")
        print(f"📋 Report saved to: {args.output_dir}/collection_report.json")
        print("="*60)
        
        if report['collection_summary']['errors_encountered'] > 0:
            print("⚠️ Some errors were encountered. Check logs for details.")
        
    except KeyboardInterrupt:
        print("\n⏹️ Collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Collection failed: {str(e)}")
        bt.logging.error(f"Collection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
