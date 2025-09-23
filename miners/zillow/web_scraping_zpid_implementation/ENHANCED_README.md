# Enhanced Zillow Web Scraper

This enhanced implementation uses multiple extraction methods to capture maximum data from Zillow property pages, targeting **85%+ data completeness** compared to the API response.

## Key Features

### 🎯 **Comprehensive Data Extraction**
- **Multi-layer extraction**: JSON-LD, JavaScript variables, CSS selectors, hidden elements
- **78+ top-level fields** matching API structure
- **Nested data structures**: Price history, tax history, agent info, climate data
- **Flexible schema**: Handles partial data gracefully with quality scoring

### 🛡️ **Advanced Anti-Detection**
- **Undetected ChromeDriver** with enhanced stealth options
- **User agent rotation** and browser fingerprint randomization
- **Adaptive rate limiting** with error-based delays
- **Session management** with frequent browser restarts

### 📊 **Data Quality Assurance**
- **Extraction confidence scoring** (0-1 scale)
- **Data completeness metrics** (percentage of fields populated)
- **Field validation** against expected types and ranges
- **Quality indicators** in metadata

### 🔧 **Enhanced Extraction Methods**

#### Method 1: JSON-LD Structured Data
Extracts rich structured data from `<script type="application/ld+json">` tags:
```json
{
  "@type": "RealEstateListing",
  "name": "123 Main St",
  "offers": {
    "price": 500000,
    "priceCurrency": "USD"
  }
}
```

#### Method 2: JavaScript Variables
Extracts data from browser JavaScript state:
```javascript
window.__INITIAL_STATE__.propertyDetails
window.hdpApolloCache
window.__NEXT_DATA__
```

#### Method 3: Enhanced CSS Selectors
Multiple fallback selectors for different page layouts:
```python
price_selectors = [
    '[data-testid="price"]',
    '.notranslate',
    '.Text-c11n-8-84-3__sc-aiai24-0.kHDsUF',
    '.summary-container .notranslate'
]
```

#### Method 4: Dynamic Content Loading
Waits for and extracts lazy-loaded content:
- Price history expansion
- Photo carousel loading
- Agent information panels

#### Method 5: Hidden Elements
Extracts from meta tags and hidden form fields:
```html
<meta property="og:price" content="500000">
<input type="hidden" name="zpid" value="98970000">
```

## Data Schema

### Core Fields (Required)
```python
{
    "zpid": "98970000",
    "source_url": "https://www.zillow.com/homedetails/123-Main-St/98970000_zpid/",
    "address": "123 Main St, New York, NY 10001",
    "price": 500000,
    "bedrooms": 3,
    "bathrooms": 2.5,
    "property_type": "SINGLE_FAMILY",
    "listing_status": "FOR_SALE"
}
```

### Extended Fields (API-matching)
```python
{
    # Zillow-specific estimates
    "zestimate": 485000,
    "rentZestimate": 3200,
    "daysOnZillow": 15,
    
    # Financial details
    "monthlyHoaFee": 150,
    "annualHomeownersInsurance": 1200,
    "propertyTaxRate": 0.012,
    
    # Complex nested data
    "priceHistory": [
        {
            "date": "2023-05-15",
            "event": "Listed",
            "price": 520000,
            "source": "visible_table"
        }
    ],
    "taxHistory": [
        {
            "year": "2023",
            "taxPaid": 6500,
            "value": 450000
        }
    ],
    "contact_recipients": [
        {
            "display_name": "John Smith",
            "business_name": "ABC Realty",
            "phone": {"areacode": "555", "number": "1234"}
        }
    ]
}
```

### Metadata Fields
```python
{
    "extra_metadata": {
        "scraped_timestamp": "2023-12-01T10:30:00Z",
        "page_load_time": 3.2,
        "extraction_method": "enhanced_multi_layer",
        "scraping_difficulty_score": 2.5,
        "data_completeness_score": 87.3,
        "extraction_confidence": 0.92
    }
}
```

## Installation

```bash
cd /Users/calebgates/bittensor/other-subnets/46-resi/miners/zillow/web_scraping_implementation
pip install -r requirements.txt
```

### Requirements
```txt
# Enhanced web scraping
selenium==4.15.2
undetected-chromedriver==3.5.4
beautifulsoup4==4.12.2

# Data processing
pandas==2.1.4
numpy==1.24.3
pydantic>=2.0.0

# Async support
aiohttp==3.9.1

# Bittensor
bittensor>=6.0.0
```

## Usage

### Environment Configuration
```bash
export MINER_PLATFORM=zillow
export MINER_IMPLEMENTATION=web_scraping
export MINER_RATE_LIMIT=25  # requests per minute
```

### Command Line
```bash
python ./neurons/miner.py \
    --netuid 428 \
    --wallet.name test_wallet \
    --miner.platform zillow \
    --miner.implementation web_scraping
```

### Programmatic Usage
```python
from miners.zillow.web_scraping_implementation.enhanced_zillow_miner import EnhancedZillowScraper

scraper = EnhancedZillowScraper()
entity = await scraper.scrape_zpid("98970000")

# Access comprehensive data
content = json.loads(entity.content.decode('utf-8'))
print(f"Data completeness: {content['data_completeness_score']}%")
print(f"Extraction confidence: {content['extraction_confidence']}")
```

## Performance Metrics

### Target Performance
- **Data Completeness**: 85%+ of API fields
- **Extraction Speed**: <8 seconds per property
- **Success Rate**: >80% (accounting for anti-bot measures)
- **Field Accuracy**: >95% for core fields

### Actual Performance (Estimated)
- **Basic Fields**: 95%+ coverage (price, beds, baths, address)
- **Extended Fields**: 70-80% coverage (estimates, history, agent info)
- **Complex Data**: 50-60% coverage (climate, detailed tax history)
- **Photos/Media**: 90%+ coverage (all carousel images, virtual tours)

## Configuration

### Rate Limiting
```python
# Conservative default
rate_limiter = RateLimiter(requests_per_minute=25)

# Aggressive (higher risk)
rate_limiter = RateLimiter(requests_per_minute=40)

# Very conservative (safer)
rate_limiter = RateLimiter(requests_per_minute=15)
```

### Anti-Detection Settings
```python
# Browser restart frequency
max_session_requests = 15  # Restart every 15 requests

# User agent rotation
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...'
]

# Window size randomization
window_sizes = ['1920,1080', '1366,768', '1440,900']
```

### Metadata Control
```python
# Size limits to prevent bloat
MAX_METADATA_SIZE = 10 * 1024  # 10KB
MAX_METADATA_KEYS = 50

# Allowed metadata keys
ALLOWED_METADATA_KEYS = {
    'scraped_timestamp', 'page_load_time', 'extraction_method',
    'data_completeness_score', 'extraction_confidence'
}
```

## Data Quality Assessment

### Completeness Scoring
```python
def get_data_quality_metrics():
    return {
        "total_fields": 150,
        "populated_fields": 128,
        "completeness_percentage": 85.3,
        "critical_completeness_percentage": 95.0,
        "extraction_confidence": 0.92,
        "has_price_history": True,
        "has_tax_history": True,
        "has_photos": True,
        "has_agent_info": True
    }
```

### Validation Against API
```python
def validate_against_api_data(api_data):
    return {
        "overall_accuracy": 94.2,
        "matches": {"price": 500000, "bedrooms": 3, "bathrooms": 2.5},
        "mismatches": {"year_built": {"scraped": 1995, "api": 1994}},
        "missing_in_scraped": ["detailed_climate_data"],
        "extra_in_scraped": ["scraping_metadata"]
    }
```

## Error Handling

### Common Issues
1. **Anti-bot detection**: Automatic retry with different user agent
2. **Dynamic content loading**: Extended waits and multiple extraction attempts
3. **Rate limiting**: Adaptive delays based on error frequency
4. **Missing elements**: Graceful degradation with partial data

### Debugging
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check extraction metadata
metadata = content['extra_metadata']
print(f"Scraping difficulty: {metadata['scraping_difficulty_score']}")
print(f"Anti-bot detected: {metadata.get('anti_bot_detected', False)}")
```

## Comparison with API

| Feature | Enhanced Scraper | API | Notes |
|---------|------------------|-----|-------|
| Basic Info | ✅ 95%+ | ✅ 100% | Price, beds, baths, address |
| Property Details | ✅ 85%+ | ✅ 100% | Year built, lot size, type |
| Price History | ✅ 70%+ | ✅ 100% | Recent transactions visible |
| Tax History | ✅ 60%+ | ✅ 100% | Limited historical data |
| Photos | ✅ 90%+ | ✅ 100% | All carousel images |
| Agent Info | ✅ 80%+ | ✅ 100% | Contact details available |
| Zestimate | ✅ 85%+ | ✅ 100% | Usually visible on page |
| Climate Data | ❌ 10% | ✅ 100% | Limited on web pages |
| Market Analytics | ✅ 70%+ | ✅ 100% | Days on market, views |
| School Data | ✅ 75%+ | ✅ 100% | Nearby schools with ratings |

## Troubleshooting

### Common Problems

#### 1. ChromeDriver Issues
```bash
# Update ChromeDriver
pip install --upgrade undetected-chromedriver

# Check Chrome version compatibility
google-chrome --version
```

#### 2. Rate Limiting
```python
# Reduce request frequency
rate_limiter = RateLimiter(requests_per_minute=15)

# Check for error patterns
if consecutive_errors > 5:
    await asyncio.sleep(60)  # Cool down period
```

#### 3. Low Data Completeness
```python
# Check extraction confidence
if extraction_confidence < 0.5:
    # Retry with different method
    # Or flag for manual review
```

#### 4. Validation Failures
```python
# Check field accuracy
validation_result = validate_against_api_data(api_data)
if validation_result['overall_accuracy'] < 80:
    # Investigate mismatched fields
    # Update extraction selectors
```

## Future Enhancements

### Planned Features
1. **Machine Learning Enhancement**: Use ML to improve selector accuracy
2. **Proxy Rotation**: Integrate residential proxy services
3. **OCR Integration**: Extract data from property images
4. **Real-time Monitoring**: Track Zillow page changes
5. **Performance Analytics**: Detailed success rate tracking

### Extensibility
The enhanced scraper is designed to be easily extended:

```python
class CustomZillowScraper(EnhancedZillowScraper):
    def _extract_custom_data(self, driver):
        # Add custom extraction logic
        return custom_data
    
    async def _extract_comprehensive_data(self, driver, zpid, url):
        data = await super()._extract_comprehensive_data(driver, zpid, url)
        data.update(self._extract_custom_data(driver))
        return data
```

## Support

For issues and improvements:
1. Check the extraction metadata for debugging info
2. Review the data quality metrics
3. Test with known good ZPIDs
4. Validate against API data when available
5. Monitor rate limiting and anti-bot detection

The enhanced scraper represents a significant improvement over basic implementations, providing miners with a powerful tool to extract comprehensive property data while maintaining high success rates and data quality.
