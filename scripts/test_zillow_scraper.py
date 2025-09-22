#!/usr/bin/env python3
"""
Test script for the Enhanced Zillow Scraper
Tests scraping performance and data quality with a fixed set of ZPIDs.
"""

import asyncio
import json
import logging
import time
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miners.zillow.web_scraping_implementation.enhanced_zillow_miner import EnhancedZillowScraper
from miners.zillow.shared.comprehensive_zillow_schema import ComprehensiveZillowRealEstateContent
from common.data import DataEntity


class ZillowScraperTester:
    """Comprehensive test suite for the Enhanced Zillow Scraper"""
    
    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Test ZPIDs - mix of property types and locations
        self.test_zpids = [
            # Chicago properties (known working)
            "3868856",  # Condo in downtown Chicago
            "3868729",  # Apartment in Chicago
            "3868730",  # Another Chicago property
            
            # New York properties
            "2077829067",  # Manhattan apartment
            "244383913",   # Brooklyn townhouse
            "31531959",    # Queens house
            
            # Los Angeles properties
            "20533519",    # Hollywood Hills house
            "21787931",    # Beverly Hills mansion
            "20449478",    # Santa Monica condo
            
            # San Francisco properties
            "15179711",    # SF Victorian house
            "114913357",   # SOMA condo
            "2077617114",  # Mission district
            
            # Texas properties
            "79553616",    # Austin house
            "28939974",    # Dallas suburb
            "29553488",    # Houston townhouse
            
            # Florida properties
            "43862304",    # Miami Beach condo
            "46124684",    # Orlando house
            "84866632",    # Tampa property
            
            # Seattle properties
            "48749425",    # Seattle house
            "2066747470",  # Bellevue condo
            
            # Additional diverse properties
            "98970000",    # Test ZPID from examples
            "2077540912",  # Another test property
            "114405900",   # Different property type
            "2066506303",  # Luxury property
            "48442526",    # Standard family home
            "244292043",   # Townhouse
            "21604137",    # Condo
            "79416096",    # Single family
            "43700820",    # Waterfront property
            "46005080",    # New construction
            
            # More test properties to reach 100
            "2077829068", "2077829069", "2077829070", "2077829071", "2077829072",
            "244383914", "244383915", "244383916", "244383917", "244383918",
            "31531960", "31531961", "31531962", "31531963", "31531964",
            "20533520", "20533521", "20533522", "20533523", "20533524",
            "21787932", "21787933", "21787934", "21787935", "21787936",
            "20449479", "20449480", "20449481", "20449482", "20449483",
            "15179712", "15179713", "15179714", "15179715", "15179716",
            "114913358", "114913359", "114913360", "114913361", "114913362",
            "79553617", "79553618", "79553619", "79553620", "79553621",
            "28939975", "28939976", "28939977", "28939978", "28939979",
            "29553489", "29553490", "29553491", "29553492", "29553493",
            "43862305", "43862306", "43862307", "43862308", "43862309",
            "46124685", "46124686", "46124687", "46124688", "46124689",
            "84866633", "84866634", "84866635", "84866636", "84866637",
            "48749426", "48749427", "48749428", "48749429", "48749430",
            "2066747471", "2066747472", "2066747473", "2066747474", "2066747475",
            "98970001", "98970002", "98970003", "98970004", "98970005",
            "2077540913", "2077540914", "2077540915", "2077540916", "2077540917",
            "114405901", "114405902", "114405903", "114405904", "114405905"
        ]
        
        # Ensure we have exactly 100 ZPIDs
        self.test_zpids = self.test_zpids[:100]
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_file = self.output_dir / f"scraper_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Starting Zillow scraper test with {len(self.test_zpids)} ZPIDs")
        self.logger.info(f"Output directory: {self.output_dir.absolute()}")
    
    async def run_performance_test(self, num_properties: int = 10) -> Dict[str, Any]:
        """Run performance test with specified number of properties"""
        
        self.logger.info(f"Starting performance test with {num_properties} properties")
        
        scraper = EnhancedZillowScraper()
        test_zpids = self.test_zpids[:num_properties]
        
        start_time = time.time()
        results = {
            'total_properties': num_properties,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'scraping_times': [],
            'data_quality_scores': [],
            'extraction_confidence_scores': [],
            'field_counts': [],
            'errors': [],
            'scraped_data': {}
        }
        
        for i, zpid in enumerate(test_zpids):
            self.logger.info(f"Scraping property {i+1}/{num_properties}: ZPID {zpid}")
            
            property_start_time = time.time()
            
            try:
                entity = await scraper.scrape_zpid(zpid)
                property_end_time = time.time()
                scraping_time = property_end_time - property_start_time
                
                if entity:
                    # Parse the scraped data
                    content_json = json.loads(entity.content.decode('utf-8'))
                    
                    results['successful_scrapes'] += 1
                    results['scraping_times'].append(scraping_time)
                    
                    # Extract quality metrics
                    data_completeness = content_json.get('data_completeness_score', 0)
                    extraction_confidence = content_json.get('extraction_confidence', 0)
                    field_count = len([k for k, v in content_json.items() if v is not None and v != ""])
                    
                    results['data_quality_scores'].append(data_completeness)
                    results['extraction_confidence_scores'].append(extraction_confidence)
                    results['field_counts'].append(field_count)
                    
                    # Store scraped data
                    results['scraped_data'][zpid] = content_json
                    
                    self.logger.info(f"✅ ZPID {zpid}: {scraping_time:.2f}s, "
                                   f"Completeness: {data_completeness:.1f}%, "
                                   f"Confidence: {extraction_confidence:.3f}, "
                                   f"Fields: {field_count}")
                else:
                    results['failed_scrapes'] += 1
                    results['errors'].append(f"ZPID {zpid}: No data returned")
                    self.logger.warning(f"❌ ZPID {zpid}: Failed to scrape")
                    
            except Exception as e:
                results['failed_scrapes'] += 1
                results['errors'].append(f"ZPID {zpid}: {str(e)}")
                self.logger.error(f"❌ ZPID {zpid}: Error - {str(e)}")
        
        total_time = time.time() - start_time
        
        # Calculate performance metrics
        if results['scraping_times']:
            results['avg_scraping_time'] = sum(results['scraping_times']) / len(results['scraping_times'])
            results['min_scraping_time'] = min(results['scraping_times'])
            results['max_scraping_time'] = max(results['scraping_times'])
        
        if results['data_quality_scores']:
            results['avg_data_quality'] = sum(results['data_quality_scores']) / len(results['data_quality_scores'])
            results['avg_extraction_confidence'] = sum(results['extraction_confidence_scores']) / len(results['extraction_confidence_scores'])
            results['avg_field_count'] = sum(results['field_counts']) / len(results['field_counts'])
        
        results['total_test_time'] = total_time
        results['success_rate'] = (results['successful_scrapes'] / num_properties) * 100
        results['properties_per_minute'] = (results['successful_scrapes'] / (total_time / 60)) if total_time > 0 else 0
        
        # Estimate time for 1000 properties
        if results['avg_scraping_time']:
            estimated_1000_time = (1000 * results['avg_scraping_time']) / 3600  # Convert to hours
            results['estimated_1000_properties_hours'] = estimated_1000_time
        
        self.logger.info(f"Performance test completed in {total_time:.2f} seconds")
        self.logger.info(f"Success rate: {results['success_rate']:.1f}%")
        self.logger.info(f"Average scraping time: {results.get('avg_scraping_time', 0):.2f} seconds")
        self.logger.info(f"Properties per minute: {results['properties_per_minute']:.2f}")
        
        return results
    
    async def run_data_quality_test(self, num_properties: int = 20) -> Dict[str, Any]:
        """Run comprehensive data quality assessment"""
        
        self.logger.info(f"Starting data quality test with {num_properties} properties")
        
        scraper = EnhancedZillowScraper()
        test_zpids = self.test_zpids[:num_properties]
        
        quality_results = {
            'total_tested': num_properties,
            'field_coverage': {},
            'data_types_validation': {},
            'schema_compliance': {},
            'quality_distribution': {
                'excellent': 0,  # >90% complete
                'good': 0,       # 70-90% complete
                'fair': 0,       # 50-70% complete
                'poor': 0        # <50% complete
            }
        }
        
        all_fields = set()
        field_population_count = {}
        
        for i, zpid in enumerate(test_zpids):
            self.logger.info(f"Quality testing property {i+1}/{num_properties}: ZPID {zpid}")
            
            try:
                entity = await scraper.scrape_zpid(zpid)
                
                if entity:
                    content_json = json.loads(entity.content.decode('utf-8'))
                    
                    # Track all fields encountered
                    for field, value in content_json.items():
                        all_fields.add(field)
                        if value is not None and value != "":
                            field_population_count[field] = field_population_count.get(field, 0) + 1
                    
                    # Categorize data quality
                    completeness = content_json.get('data_completeness_score', 0)
                    if completeness >= 90:
                        quality_results['quality_distribution']['excellent'] += 1
                    elif completeness >= 70:
                        quality_results['quality_distribution']['good'] += 1
                    elif completeness >= 50:
                        quality_results['quality_distribution']['fair'] += 1
                    else:
                        quality_results['quality_distribution']['poor'] += 1
                        
            except Exception as e:
                self.logger.error(f"Quality test error for ZPID {zpid}: {str(e)}")
        
        # Calculate field coverage statistics
        total_properties_tested = sum(quality_results['quality_distribution'].values())
        
        for field in all_fields:
            population_rate = (field_population_count.get(field, 0) / total_properties_tested) * 100
            quality_results['field_coverage'][field] = {
                'population_rate': population_rate,
                'populated_count': field_population_count.get(field, 0),
                'total_tested': total_properties_tested
            }
        
        # Sort fields by population rate
        quality_results['field_coverage'] = dict(
            sorted(quality_results['field_coverage'].items(), 
                  key=lambda x: x[1]['population_rate'], reverse=True)
        )
        
        self.logger.info("Data quality test completed")
        self.logger.info(f"Total unique fields found: {len(all_fields)}")
        self.logger.info(f"Quality distribution: {quality_results['quality_distribution']}")
        
        return quality_results
    
    def save_results(self, results: Dict[str, Any], test_type: str):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"{test_type}_results_{timestamp}.json"
        
        # Convert any non-serializable objects
        serializable_results = json.loads(json.dumps(results, default=str))
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        self.logger.info(f"Results saved to: {filename}")
        return filename
    
    def save_scraped_data(self, scraped_data: Dict[str, Any]):
        """Save individual scraped property data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        data_dir = self.output_dir / f"scraped_properties_{timestamp}"
        data_dir.mkdir(exist_ok=True)
        
        for zpid, data in scraped_data.items():
            filename = data_dir / f"zpid_{zpid}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        
        self.logger.info(f"Individual property data saved to: {data_dir}")
        return data_dir
    
    def generate_report(self, performance_results: Dict[str, Any], quality_results: Dict[str, Any]):
        """Generate comprehensive test report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"test_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Enhanced Zillow Scraper Test Report\n\n")
            f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Performance Results
            f.write("## Performance Results\n\n")
            f.write(f"- **Total Properties Tested**: {performance_results['total_properties']}\n")
            f.write(f"- **Successful Scrapes**: {performance_results['successful_scrapes']}\n")
            f.write(f"- **Failed Scrapes**: {performance_results['failed_scrapes']}\n")
            f.write(f"- **Success Rate**: {performance_results['success_rate']:.1f}%\n")
            f.write(f"- **Average Scraping Time**: {performance_results.get('avg_scraping_time', 0):.2f} seconds\n")
            f.write(f"- **Properties per Minute**: {performance_results['properties_per_minute']:.2f}\n")
            f.write(f"- **Estimated Time for 1000 Properties**: {performance_results.get('estimated_1000_properties_hours', 0):.2f} hours\n\n")
            
            # Data Quality Results
            f.write("## Data Quality Results\n\n")
            f.write(f"- **Average Data Completeness**: {performance_results.get('avg_data_quality', 0):.1f}%\n")
            f.write(f"- **Average Extraction Confidence**: {performance_results.get('avg_extraction_confidence', 0):.3f}\n")
            f.write(f"- **Average Field Count**: {performance_results.get('avg_field_count', 0):.1f}\n\n")
            
            # Quality Distribution
            f.write("### Quality Distribution\n\n")
            for quality, count in quality_results['quality_distribution'].items():
                percentage = (count / quality_results['total_tested']) * 100
                f.write(f"- **{quality.title()}** (>90%): {count} properties ({percentage:.1f}%)\n")
            f.write("\n")
            
            # Top Fields by Population Rate
            f.write("### Top 20 Most Populated Fields\n\n")
            f.write("| Field | Population Rate | Count |\n")
            f.write("|-------|----------------|-------|\n")
            
            top_fields = list(quality_results['field_coverage'].items())[:20]
            for field, stats in top_fields:
                f.write(f"| {field} | {stats['population_rate']:.1f}% | {stats['populated_count']} |\n")
            
            f.write("\n")
            
            # Errors
            if performance_results['errors']:
                f.write("## Errors Encountered\n\n")
                for error in performance_results['errors'][:10]:  # Show first 10 errors
                    f.write(f"- {error}\n")
                if len(performance_results['errors']) > 10:
                    f.write(f"- ... and {len(performance_results['errors']) - 10} more errors\n")
        
        self.logger.info(f"Test report generated: {report_file}")
        return report_file


async def main():
    """Main test execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Enhanced Zillow Scraper")
    parser.add_argument('--performance', '-p', type=int, default=10, 
                       help="Number of properties for performance test (default: 10)")
    parser.add_argument('--quality', '-q', type=int, default=20,
                       help="Number of properties for quality test (default: 20)")
    parser.add_argument('--full-test', '-f', action='store_true',
                       help="Run full test with all 100 properties")
    parser.add_argument('--output', '-o', default="test_results",
                       help="Output directory for results (default: test_results)")
    
    args = parser.parse_args()
    
    tester = ZillowScraperTester(output_dir=args.output)
    
    if args.full_test:
        print("🚀 Running FULL TEST with all 100 properties...")
        print("⚠️  This will take approximately 1-2 hours!")
        
        performance_results = await tester.run_performance_test(100)
        quality_results = await tester.run_data_quality_test(100)
    else:
        print(f"🚀 Running performance test with {args.performance} properties...")
        performance_results = await tester.run_performance_test(args.performance)
        
        print(f"🔍 Running quality test with {args.quality} properties...")
        quality_results = await tester.run_data_quality_test(args.quality)
    
    # Save results
    perf_file = tester.save_results(performance_results, "performance")
    quality_file = tester.save_results(quality_results, "quality")
    
    # Save individual scraped data
    if performance_results.get('scraped_data'):
        data_dir = tester.save_scraped_data(performance_results['scraped_data'])
    
    # Generate report
    report_file = tester.generate_report(performance_results, quality_results)
    
    print(f"\n✅ Test completed!")
    print(f"📊 Performance results: {perf_file}")
    print(f"🔍 Quality results: {quality_file}")
    print(f"📋 Full report: {report_file}")
    
    # Print quick summary
    print(f"\n📈 Quick Summary:")
    print(f"   Success Rate: {performance_results['success_rate']:.1f}%")
    print(f"   Avg Scraping Time: {performance_results.get('avg_scraping_time', 0):.2f}s")
    print(f"   Avg Data Completeness: {performance_results.get('avg_data_quality', 0):.1f}%")
    print(f"   Est. Time for 1000 properties: {performance_results.get('estimated_1000_properties_hours', 0):.2f} hours")


if __name__ == "__main__":
    asyncio.run(main())
