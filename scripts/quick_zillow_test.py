#!/usr/bin/env python3
"""
Quick test script for Enhanced Zillow Scraper
Tests a few properties quickly to verify scraper is working.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miners.zillow.web_scraping_implementation.enhanced_zillow_miner import EnhancedZillowScraper


async def quick_test():
    """Quick test with a few known properties"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Test ZPIDs - known working properties
    test_zpids = [
        "3868856",    # Chicago condo
        "98970000",   # Test property
        "2077829067", # NYC property
        "20533519",   # LA property
        "15179711"    # SF property
    ]
    
    scraper = EnhancedZillowScraper()
    
    print("🚀 Starting quick Zillow scraper test...")
    print(f"Testing {len(test_zpids)} properties")
    
    results = []
    
    for i, zpid in enumerate(test_zpids):
        print(f"\n📍 Testing property {i+1}/{len(test_zpids)}: ZPID {zpid}")
        
        try:
            start_time = asyncio.get_event_loop().time()
            entity = await scraper.scrape_zpid(zpid)
            end_time = asyncio.get_event_loop().time()
            
            scraping_time = end_time - start_time
            
            if entity:
                # Parse the data
                content_json = json.loads(entity.content.decode('utf-8'))
                
                # Extract key metrics
                completeness = content_json.get('data_completeness_score', 0)
                confidence = content_json.get('extraction_confidence', 0)
                field_count = len([k for k, v in content_json.items() if v is not None and v != ""])
                
                result = {
                    'zpid': zpid,
                    'success': True,
                    'scraping_time': scraping_time,
                    'data_completeness': completeness,
                    'extraction_confidence': confidence,
                    'field_count': field_count,
                    'has_price': content_json.get('price') is not None,
                    'has_address': content_json.get('address') is not None,
                    'has_photos': bool(content_json.get('photos')),
                    'has_price_history': bool(content_json.get('priceHistory')),
                    'source_url': content_json.get('source_url')
                }
                
                results.append(result)
                
                print(f"   ✅ Success in {scraping_time:.2f}s")
                print(f"   📊 Completeness: {completeness:.1f}%")
                print(f"   🎯 Confidence: {confidence:.3f}")
                print(f"   📝 Fields: {field_count}")
                print(f"   💰 Has price: {result['has_price']}")
                print(f"   📍 Has address: {result['has_address']}")
                print(f"   📸 Has photos: {result['has_photos']}")
                print(f"   📈 Has price history: {result['has_price_history']}")
                
                # Save individual result
                output_file = f"quick_test_zpid_{zpid}_{datetime.now().strftime('%H%M%S')}.json"
                with open(output_file, 'w') as f:
                    json.dump(content_json, f, indent=2, default=str)
                print(f"   💾 Saved to: {output_file}")
                
            else:
                result = {
                    'zpid': zpid,
                    'success': False,
                    'scraping_time': scraping_time,
                    'error': 'No data returned'
                }
                results.append(result)
                print(f"   ❌ Failed - no data returned")
                
        except Exception as e:
            result = {
                'zpid': zpid,
                'success': False,
                'error': str(e)
            }
            results.append(result)
            print(f"   ❌ Error: {str(e)}")
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total_time = sum(r.get('scraping_time', 0) for r in results)
    avg_time = total_time / len(results) if results else 0
    
    print(f"\n📊 QUICK TEST SUMMARY:")
    print(f"   Success Rate: {successful}/{len(test_zpids)} ({(successful/len(test_zpids)*100):.1f}%)")
    print(f"   Average Time: {avg_time:.2f} seconds per property")
    print(f"   Total Time: {total_time:.2f} seconds")
    
    if successful > 0:
        avg_completeness = sum(r.get('data_completeness', 0) for r in results if r['success']) / successful
        avg_confidence = sum(r.get('extraction_confidence', 0) for r in results if r['success']) / successful
        avg_fields = sum(r.get('field_count', 0) for r in results if r['success']) / successful
        
        print(f"   Avg Completeness: {avg_completeness:.1f}%")
        print(f"   Avg Confidence: {avg_confidence:.3f}")
        print(f"   Avg Fields: {avg_fields:.1f}")
        
        # Estimate for 1000 properties
        est_1000_hours = (1000 * avg_time) / 3600
        print(f"   Est. 1000 properties: {est_1000_hours:.2f} hours")
    
    print(f"\n🎉 Quick test completed!")
    
    return results


if __name__ == "__main__":
    asyncio.run(quick_test())
