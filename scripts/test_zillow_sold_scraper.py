#!/usr/bin/env python3
"""
Test script for Zillow Sold Listings Scraper
Tests the new ZILLOW_SOLD data source with zipcode-based scraping.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from miners.zillow.web_scraping_sold_implementation.zillow_sold_scraper import ZillowSoldListingsScraper
from miners.zillow.shared.sold_url_builder import ZillowSoldURLBuilder, test_zipcode_url_construction as test_single_zipcode_url
from miners.zillow.shared.zipcode_utils import get_test_zipcodes, get_zipcode_mapper
from common.data import DataLabel, DataSource
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_zipcode_url_construction():
    """Test URL construction for various zipcodes"""
    
    print("\n" + "="*60)
    print("TESTING ZIPCODE URL CONSTRUCTION")
    print("="*60)
    
    test_zipcodes = get_test_zipcodes()
    builder = ZillowSoldURLBuilder()
    
    for zipcode in test_zipcodes:
        print(f"\nTesting zipcode: {zipcode}")
        
        try:
            # Test URL construction
            result = await test_single_zipcode_url(zipcode)
            
            if result["zipcode_resolved"]:
                print(f"✅ Zipcode resolved: {result['zipcode_info']['zillow_format']}")
                print(f"   City: {result['zipcode_info']['city']}, {result['zipcode_info']['state']}")
                print(f"   Simple URL (page 1): {result['urls']['simple_page_1']}")
                print(f"   Complex URL (page 1): {result['urls']['complex_page_1'][:100]}...")
            else:
                print(f"❌ Failed to resolve zipcode")
                if result["errors"]:
                    print(f"   Errors: {result['errors']}")
        
        except Exception as e:
            print(f"❌ Error testing zipcode {zipcode}: {e}")


async def test_sold_scraper_basic():
    """Test basic sold listings scraper functionality"""
    
    print("\n" + "="*60)
    print("TESTING SOLD LISTINGS SCRAPER - BASIC")
    print("="*60)
    
    # Test with a single zipcode
    test_zipcode = "11225"  # Brooklyn, NY
    limit_for_testing = 20  # Limit for quick testing (scraper gets ALL but we limit for demo)
    
    try:
        scraper = ZillowSoldListingsScraper()
        
        print(f"Testing sold listings scraper with zipcode {test_zipcode}")
        print(f"Note: Scraper gets ALL sold listings, limiting to {limit_for_testing} for testing")
        
        # Create scrape config
        config = ScrapeConfig(
            entity_limit=limit_for_testing,
            date_range=DateRange(
                start=datetime.now(timezone.utc),
                end=datetime.now(timezone.utc)
            ),
            labels=[DataLabel(value=f"zip:{test_zipcode}")]
        )
        
        # Run scraper
        start_time = time.time()
        entities = await scraper.scrape(config)
        end_time = time.time()
        
        print(f"\n✅ Scraping completed in {end_time - start_time:.2f} seconds")
        print(f"✅ Retrieved {len(entities)} sold listings")
        
        # Analyze results
        if entities:
            print(f"\nFirst entity details:")
            first_entity = entities[0]
            print(f"  URI: {first_entity.uri}")
            print(f"  Source: {first_entity.source}")
            print(f"  Label: {first_entity.label.value if first_entity.label else 'None'}")
            print(f"  Content size: {first_entity.content_size_bytes} bytes")
            
            # Try to parse content
            try:
                content_json = json.loads(first_entity.content.decode('utf-8'))
                print(f"  Address: {content_json.get('address', 'N/A')}")
                print(f"  Sale price: ${content_json.get('sale_price', 'N/A'):,}" if content_json.get('sale_price') else "  Sale price: N/A")
                print(f"  Bedrooms: {content_json.get('bedrooms', 'N/A')}")
                print(f"  Bathrooms: {content_json.get('bathrooms', 'N/A')}")
                print(f"  Square feet: {content_json.get('square_feet', 'N/A'):,}" if content_json.get('square_feet') else "  Square feet: N/A")
            except Exception as e:
                print(f"  Error parsing content: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing sold scraper: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_zipcodes():
    """Test scraper with multiple zipcodes"""
    
    print("\n" + "="*60)
    print("TESTING SOLD LISTINGS SCRAPER - MULTIPLE ZIPCODES")
    print("="*60)
    
    # Test with multiple zipcodes
    test_zipcodes = ["11225", "10001"]  # Brooklyn, Manhattan (reduced for faster testing)
    max_listings_total = 30  # Total limit distributed across zipcodes
    
    try:
        scraper = ZillowSoldListingsScraper()
        
        print(f"Testing sold listings scraper with zipcodes: {test_zipcodes}")
        print(f"Max total listings: {max_listings_total}")
        
        # Create scrape config with multiple zipcode labels
        labels = [DataLabel(value=f"zip:{zipcode}") for zipcode in test_zipcodes]
        
        config = ScrapeConfig(
            entity_limit=max_listings_total,
            date_range=DateRange(
                start=datetime.now(timezone.utc),
                end=datetime.now(timezone.utc)
            ),
            labels=labels
        )
        
        # Run scraper
        start_time = time.time()
        entities = await scraper.scrape(config)
        end_time = time.time()
        
        print(f"\n✅ Multi-zipcode scraping completed in {end_time - start_time:.2f} seconds")
        print(f"✅ Retrieved {len(entities)} total sold listings")
        
        # Analyze results by zipcode
        zipcode_counts = {}
        for entity in entities:
            try:
                content_json = json.loads(entity.content.decode('utf-8'))
                zipcode = content_json.get('zipcode', 'Unknown')
                zipcode_counts[zipcode] = zipcode_counts.get(zipcode, 0) + 1
            except:
                zipcode_counts['Parse Error'] = zipcode_counts.get('Parse Error', 0) + 1
        
        print(f"\nListings by zipcode:")
        for zipcode, count in zipcode_counts.items():
            print(f"  {zipcode}: {count} listings")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing multiple zipcodes: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_url_validation():
    """Test URL validation and extraction functions"""
    
    print("\n" + "="*60)
    print("TESTING URL VALIDATION")
    print("="*60)
    
    from miners.zillow.shared.sold_url_builder import validate_sold_listings_url
    
    test_urls = [
        "https://www.zillow.com/brooklyn-new-york-ny-11225/sold/",
        "https://www.zillow.com/brooklyn-new-york-ny-11225/sold/2_p/",
        "https://www.zillow.com/brooklyn-new-york-ny-11225/sold/4_p/?searchQueryState=%7B%22pagination%22%3A%7B%22currentPage%22%3A4%7D",
        "https://www.zillow.com/homes/11225_rb/",  # Not a sold listing URL
        "https://www.redfin.com/NY/Brooklyn/",  # Not a Zillow URL
    ]
    
    for url in test_urls:
        print(f"\nTesting URL: {url[:80]}...")
        result = validate_sold_listings_url(url)
        
        print(f"  Valid: {result['is_valid']}")
        print(f"  Is sold listings: {result['is_sold_listings']}")
        print(f"  Zipcode: {result['zipcode']}")
        print(f"  Page: {result['page']}")
        print(f"  Has search params: {result['has_search_params']}")
        
        if result['errors']:
            print(f"  Errors: {result['errors']}")


def save_test_results(results: dict, filename: str = "zillow_sold_test_results.json"):
    """Save test results to file"""
    
    output_dir = Path(__file__).parent / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / filename
    
    # Convert datetime objects to strings for JSON serialization
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=json_serializer)
        
        print(f"\n✅ Test results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error saving test results: {e}")


async def main():
    """Run all tests"""
    
    print("ZILLOW SOLD LISTINGS SCRAPER TEST SUITE")
    print("="*60)
    print(f"Test started at: {datetime.now()}")
    
    results = {
        "test_start_time": datetime.now(),
        "tests": {}
    }
    
    try:
        # Test 1: URL Construction
        print("\n🔧 Running URL construction tests...")
        await test_zipcode_url_construction()
        results["tests"]["url_construction"] = {"status": "completed"}
        
        # Test 2: URL Validation
        print("\n🔧 Running URL validation tests...")
        await test_url_validation()
        results["tests"]["url_validation"] = {"status": "completed"}
        
        # Test 3: Basic Scraper Test
        print("\n🔧 Running basic scraper tests...")
        basic_success = await test_sold_scraper_basic()
        results["tests"]["basic_scraper"] = {"status": "success" if basic_success else "failed"}
        
        # Test 4: Multiple Zipcodes Test
        print("\n🔧 Running multiple zipcodes tests...")
        multi_success = await test_multiple_zipcodes()
        results["tests"]["multiple_zipcodes"] = {"status": "success" if multi_success else "failed"}
        
        # Summary
        results["test_end_time"] = datetime.now()
        results["total_duration"] = (results["test_end_time"] - results["test_start_time"]).total_seconds()
        
        print("\n" + "="*60)
        print("TEST SUITE SUMMARY")
        print("="*60)
        
        for test_name, test_result in results["tests"].items():
            status_icon = "✅" if test_result["status"] in ["completed", "success"] else "❌"
            print(f"{status_icon} {test_name}: {test_result['status']}")
        
        print(f"\nTotal test duration: {results['total_duration']:.2f} seconds")
        
        # Save results
        save_test_results(results)
        
        print("\n🎉 Test suite completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = str(e)
        save_test_results(results)


if __name__ == "__main__":
    asyncio.run(main())
