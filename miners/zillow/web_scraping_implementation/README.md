# Direct Zillow Web Scraping Implementation

This implementation scrapes Zillow property data directly from property pages using Selenium and undetected Chrome. It provides an alternative to API-based scraping while attempting to fill the same data schema.

## Features

- **Direct Web Scraping**: Scrapes property pages directly from Zillow
- **Anti-Detection**: Uses undetected-chromedriver and various stealth techniques
- **Rate Limiting**: Built-in rate limiting (30 requests/minute by default)
- **Data Completeness**: Attempts to extract as much data as possible from web pages
- **Error Handling**: Robust error handling and retry logic

## Installation

1. Install Chrome browser (required for Selenium)
2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from direct_zillow_miner import DirectZillowScraper
from scraping.scraper import ScrapeConfig
from common.data import DataLabel

# Create scraper
scraper = DirectZillowScraper()

# Create configuration with ZPIDs
labels = [DataLabel(value="zpid:98970000")]
config = ScrapeConfig(
    entity_limit=10,
    date_range=DateRange(...),
    labels=labels
)

# Scrape properties
entities = await scraper.scrape(config)
```

### ZPID-Based Requests

This implementation supports the new ZPID-based request protocol:

```python
from shared.protocol import ZpidScrapeRequest

# Create ZPID request
request = ZpidScrapeRequest(
    zpids=["98970000", "12345678", "87654321"],
    priority=1.0
)

# Process request (in miner handler)
for zpid in request.zpids:
    entity = await scraper.scrape_zpid(zpid)
    if entity:
        request.scraped_properties.append(entity)
        request.success_count += 1
    else:
        request.failed_zpids.append(zpid)
```

## Data Extraction

### Available Data Fields

The scraper attempts to extract the following data from Zillow property pages:

✅ **Successfully Extracted:**
- Basic info (address, price, bedrooms, bathrooms, sqft)
- Property details (year built, property type, lot size)
- Price history (sale dates, prices, events)
- Photos (property images from carousel)
- Agent information (listing agent details)
- School information (nearby schools and ratings)
- Pricing estimates (Zestimate, rent estimates)

🟡 **Partially Available:**
- Tax information (recent tax data)
- Market analytics (days on market)
- Property features (heating, cooling, parking)

❌ **Not Available:**
- Detailed climate data (30-year projections)
- Complete tax history (25+ years)
- Detailed room dimensions
- MLS-specific data

### Data Schema Compatibility

The scraper attempts to fill the same `RealEstateContent` schema used by the API implementation:

```python
{
    "zpid": "98970000",
    "address": "123 Main St, City, State 12345",
    "price": 350000,
    "bedrooms": 3,
    "bathrooms": 2,
    "living_area": 1500,
    "property_type": "SINGLE_FAMILY",
    "year_built": 2000,
    "zestimate": 355000,
    "rent_zestimate": 2800,
    "price_history": [
        {
            "date": "2023-01-15",
            "event": "Sold",
            "price": 340000
        }
    ],
    "carousel_photos": [
        "https://photos.zillowstatic.com/...",
        "..."
    ],
    "schools": [
        {
            "name": "Elementary School",
            "rating": "8"
        }
    ],
    "scraped_at": "2024-01-15T10:30:00Z",
    "data_source": "direct_scraping"
}
```

## Anti-Detection Measures

### Implemented Techniques

1. **Undetected Chrome**: Uses undetected-chromedriver to avoid detection
2. **User Agent Rotation**: Rotates between different browser user agents
3. **Rate Limiting**: Limits requests to 30 per minute
4. **Session Management**: Creates new browser sessions periodically
5. **Request Delays**: Random delays between requests
6. **Stealth Options**: Disables automation indicators

### Additional Recommendations

For production use, consider adding:

1. **Proxy Rotation**: Use residential proxy services
2. **Behavioral Mimicking**: Add mouse movements and scrolling
3. **Request Distribution**: Spread requests across different IP addresses
4. **CAPTCHA Handling**: Implement CAPTCHA solving services
5. **Monitoring**: Monitor for rate limits and blocks

## Configuration

### Scraper Configuration

```python
# Rate limiting
scraper.rate_limiter = RateLimiter(requests_per_minute=20)  # Slower rate

# Session management
scraper.max_session_requests = 10  # Restart browser more frequently

# User agents
scraper.user_agents = [
    "Custom User Agent 1",
    "Custom User Agent 2"
]
```

### Chrome Options

Modify the `_create_driver()` method to adjust Chrome options:

```python
options.add_argument('--headless')  # Run in headless mode
options.add_argument('--proxy-server=http://proxy:port')  # Use proxy
options.add_argument('--window-size=1920,1080')  # Set window size
```

## Error Handling

The scraper handles various error conditions:

- **Anti-bot detection**: Automatically detects and reports blocks
- **Page load timeouts**: Handles slow-loading pages gracefully
- **Missing elements**: Continues extraction even if some elements are missing
- **Invalid ZPIDs**: Reports invalid or non-existent properties
- **Network errors**: Implements retry logic for network issues

## Validation

The scraper includes validation by re-scraping:

```python
# Validate entities
validation_results = await scraper.validate(entities)

for result in validation_results:
    if result.is_valid:
        print(f"Valid: {result.reason}")
    else:
        print(f"Invalid: {result.reason}")
```

## Legal and Ethical Considerations

### Important Notes

1. **Respect robots.txt**: Check Zillow's robots.txt before scraping
2. **Rate Limiting**: Always implement reasonable rate limiting
3. **Terms of Service**: Review Zillow's terms of service
4. **Data Usage**: Use scraped data responsibly and legally
5. **Monitoring**: Monitor for cease and desist requests

### Recommended Practices

- Start with conservative rate limits (10-20 requests/minute)
- Use residential proxies for production
- Implement proper error handling and logging
- Monitor scraping success rates
- Have fallback strategies for blocked requests

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues**:
   ```bash
   pip install --upgrade undetected-chromedriver
   ```

2. **Anti-bot Detection**:
   - Reduce request rate
   - Use different user agents
   - Implement proxy rotation

3. **Element Not Found**:
   - Zillow may have updated their HTML structure
   - Update CSS selectors in the extraction methods

4. **Memory Issues**:
   - Reduce `max_session_requests`
   - Close browser sessions more frequently

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance

### Expected Performance

- **Success Rate**: 70-90% depending on anti-bot measures
- **Speed**: 2-5 seconds per property (including delays)
- **Data Completeness**: ~60-70% of API fields

### Optimization Tips

1. **Disable Images**: `options.add_argument('--disable-images')`
2. **Disable JavaScript**: For basic data extraction
3. **Use Headless Mode**: Faster but may be more detectable
4. **Batch Processing**: Process multiple ZPIDs in same session

## Support

This implementation is provided as an example for miners to build upon. Miners are encouraged to:

1. Improve anti-detection measures
2. Add proxy rotation
3. Enhance data extraction
4. Optimize performance
5. Add monitoring and alerting

The goal is to provide a starting point that miners can customize for their specific needs and infrastructure.
