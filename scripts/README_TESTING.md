# Zillow Scraper Testing Scripts

This directory contains comprehensive testing scripts for the Enhanced Zillow Scraper.

## Quick Test (5 minutes)

**File**: `quick_zillow_test.py`

Tests 5 known properties to verify the scraper is working:

```bash
cd /Users/calebgates/bittensor/other-subnets/46-resi
python scripts/quick_zillow_test.py
```

**Output**:
- Individual JSON files for each scraped property
- Console summary with success rates and performance metrics
- Quick estimation for 1000 properties

## Comprehensive Test Suite

**File**: `test_zillow_scraper.py`

Full testing suite with performance and quality analysis:

### Basic Test (10 properties, ~5 minutes)
```bash
python scripts/test_zillow_scraper.py --performance 10 --quality 10
```

### Medium Test (50 properties, ~30 minutes)
```bash
python scripts/test_zillow_scraper.py --performance 50 --quality 30
```

### Full Test (100 properties, ~1-2 hours)
```bash
python scripts/test_zillow_scraper.py --full-test
```

### Custom Test
```bash
python scripts/test_zillow_scraper.py \
    --performance 25 \
    --quality 40 \
    --output my_test_results
```

## Test Results

### Performance Metrics
- **Success Rate**: Percentage of successfully scraped properties
- **Average Scraping Time**: Time per property in seconds
- **Properties per Minute**: Throughput rate
- **Estimated Time for 1000**: Projection for large-scale scraping

### Data Quality Metrics
- **Data Completeness Score**: Percentage of fields populated
- **Extraction Confidence**: Accuracy confidence (0-1 scale)
- **Field Count**: Number of populated fields per property
- **Quality Distribution**: Properties categorized by completeness

### Output Files
- `performance_results_TIMESTAMP.json`: Detailed performance data
- `quality_results_TIMESTAMP.json`: Data quality analysis
- `test_report_TIMESTAMP.md`: Human-readable summary report
- `scraped_properties_TIMESTAMP/`: Individual property JSON files
- `scraper_test_TIMESTAMP.log`: Detailed execution log

## Expected Performance (1000 Properties)

Based on the enhanced scraper configuration:

### Conservative Estimate (Default Settings)
- **Rate Limit**: 25 requests/minute
- **Scraping Time**: ~8 seconds per property
- **Browser Restarts**: Every 15 requests
- **Total Time**: **3.5-4.0 hours**

### Optimized Settings
- **Rate Limit**: 35-40 requests/minute
- **Parallel Processing**: 2-3 concurrent scrapers
- **Total Time**: **1.5-2.0 hours**

### Factors Affecting Performance
- **Anti-bot detection**: May require slower rates
- **Property complexity**: More data = longer extraction time
- **Network conditions**: Affects page load times
- **Zillow's response time**: Variable based on load

## Test Property Coverage

The test suite includes 100 diverse properties:

### Geographic Distribution
- **Chicago**: 15 properties (condos, apartments)
- **New York**: 15 properties (Manhattan, Brooklyn, Queens)
- **Los Angeles**: 15 properties (Hollywood, Beverly Hills, Santa Monica)
- **San Francisco**: 15 properties (various neighborhoods)
- **Texas**: 15 properties (Austin, Dallas, Houston)
- **Florida**: 10 properties (Miami, Orlando, Tampa)
- **Seattle**: 10 properties (Seattle, Bellevue)
- **Other**: 5 properties (diverse locations)

### Property Types
- **Single Family Homes**: 40%
- **Condominiums**: 35%
- **Townhouses**: 15%
- **Apartments**: 10%

### Price Ranges
- **Under $300K**: 20%
- **$300K - $600K**: 30%
- **$600K - $1M**: 25%
- **$1M - $2M**: 15%
- **Over $2M**: 10%

## Interpreting Results

### Success Rate Benchmarks
- **>85%**: Excellent performance
- **70-85%**: Good performance
- **50-70%**: Acceptable (may need optimization)
- **<50%**: Poor (investigate issues)

### Data Completeness Benchmarks
- **>80%**: Excellent data extraction
- **60-80%**: Good data extraction
- **40-60%**: Fair data extraction
- **<40%**: Poor data extraction

### Common Issues and Solutions

#### Low Success Rate
- **Cause**: Anti-bot detection, rate limiting
- **Solution**: Reduce rate limit, add more delays
- **Command**: Modify `requests_per_minute` in scraper

#### Low Data Completeness
- **Cause**: Page layout changes, missing selectors
- **Solution**: Update CSS selectors, add fallbacks
- **Investigation**: Check individual property files

#### Slow Performance
- **Cause**: Conservative rate limiting, browser restarts
- **Solution**: Optimize settings, consider parallel processing
- **Optimization**: Increase rate limit cautiously

## Debugging Failed Properties

When properties fail to scrape:

1. **Check the log file** for detailed error messages
2. **Manually visit the Zillow URL** to verify property exists
3. **Look for anti-bot detection** indicators in logs
4. **Examine extraction metadata** for clues
5. **Test with individual ZPIDs** using quick test

## Example Test Output

```
🚀 Starting performance test with 10 properties
✅ ZPID 3868856: 7.3s, Completeness: 87.2%, Confidence: 0.92, Fields: 94
✅ ZPID 98970000: 6.1s, Completeness: 82.5%, Confidence: 0.89, Fields: 87
❌ ZPID 2077829067: Failed to scrape
✅ ZPID 20533519: 8.7s, Completeness: 91.3%, Confidence: 0.95, Fields: 102

📊 Quick Summary:
   Success Rate: 80.0%
   Avg Scraping Time: 7.37s
   Avg Data Completeness: 87.0%
   Est. Time for 1000 properties: 2.05 hours
```

## Running Tests in Different Environments

### Local Development
```bash
# Ensure dependencies are installed
pip install -r miners/zillow/web_scraping_implementation/enhanced_requirements.txt

# Run quick test
python scripts/quick_zillow_test.py
```

### Production Environment
```bash
# Use conservative settings
export MINER_RATE_LIMIT=20
python scripts/test_zillow_scraper.py --performance 20
```

### CI/CD Pipeline
```bash
# Minimal test for validation
python scripts/quick_zillow_test.py > test_results.log
```

The testing scripts provide comprehensive analysis of the Enhanced Zillow Scraper's performance and data quality, enabling optimization and validation before production deployment.
