# RapidAPI Zillow Implementation (Example)

This is an example implementation that uses the RapidAPI Zillow endpoint to scrape property data. This approach provides comprehensive data but requires API costs.

## ⚠️ Important Notice

This is provided as an **example implementation only**. Miners are free to choose their own data collection methods. The network does not require or endorse the use of any specific API service.

## Features

- **Complete Data**: Access to all 1,565+ data fields from Zillow API
- **High Reliability**: Stable API with consistent data format
- **Fast Performance**: Quick response times (typically <1 second per property)
- **Comprehensive Coverage**: Tax history, climate data, comparable sales, etc.

## Data Completeness

This implementation provides access to extensive property data including:

✅ **Complete Coverage:**
- Basic property information (address, price, beds, baths, sqft)
- Detailed tax history (25+ years of records)
- Complete price history with all transactions
- Climate risk data (flood, fire, heat, air quality with 30-year projections)
- Nearby comparable properties (9+ similar homes)
- Detailed room information (19+ rooms with dimensions)
- School data (ratings, distances, district information)
- Agent information (complete contact details and reviews)
- Building features (HOA fees, amenities, parking details)
- Market analytics (days on market, page views, trends)
- MLS data (when available)

## Installation

1. Sign up for RapidAPI account at https://rapidapi.com/
2. Subscribe to Zillow API at https://rapidapi.com/apimaker/api/zillow-com1/
3. Get your API key from the dashboard
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Set environment variables:

```bash
export RAPIDAPI_KEY="your_api_key_here"
export RAPIDAPI_HOST="zillow-com1.p.rapidapi.com"
```

## Usage

### Basic Usage

```python
from rapid_zillow_miner import ZillowRapidAPIScraper
from scraping.scraper import ScrapeConfig
from common.data import DataLabel

# Create scraper
scraper = ZillowRapidAPIScraper()

# Create configuration
labels = [DataLabel(value="zip:90210")]  # Beverly Hills
config = ScrapeConfig(
    entity_limit=50,
    date_range=DateRange(...),
    labels=labels
)

# Scrape properties
entities = await scraper.scrape(config)
print(f"Scraped {len(entities)} properties")
```

### ZPID-Based Requests

```python
# For specific property requests
labels = [DataLabel(value="zpid:98970000")]
config = ScrapeConfig(
    entity_limit=1,
    date_range=DateRange(...),
    labels=labels
)

entities = await scraper.scrape(config)
```

## API Endpoints Used

### Property Extended Search
- **Endpoint**: `/propertyExtendedSearch`
- **Usage**: Search properties by location, type, status
- **Rate Limit**: 2 requests/second
- **Cost**: ~$0.01-0.05 per request (varies by plan)

### Individual Property
- **Endpoint**: `/property`
- **Usage**: Get detailed data for specific ZPID
- **Rate Limit**: 2 requests/second  
- **Cost**: ~$0.01-0.05 per request (varies by plan)

## Rate Limiting

The implementation includes built-in rate limiting:

```python
# Built-in rate limiting (2 requests/second)
MAX_REQUESTS_PER_SECOND = 2
REQUEST_DELAY = 0.5  # 500ms between requests
```

## Cost Considerations

### Typical API Costs
- **Basic Plan**: 1,000 requests/month (~$10-20/month)
- **Pro Plan**: 10,000 requests/month (~$50-100/month)
- **Mega Plan**: 100,000 requests/month (~$200-500/month)

### Cost Optimization Strategies
1. **Targeted Scraping**: Only scrape requested ZPIDs
2. **Caching**: Cache results to avoid duplicate requests
3. **Batch Processing**: Group requests efficiently
4. **Error Handling**: Avoid retrying failed requests unnecessarily

## Data Schema

The API provides comprehensive data in this structure:

```python
{
    "zpid": "98970000",
    "address": "360 E Randolph St APT 2005, Chicago, IL 60601",
    "price": 624900,
    "bedrooms": 2,
    "bathrooms": 2,
    "living_area": 1580,
    "property_type": "CONDO",
    "year_built": 1982,
    "zestimate": 604100,
    "rent_zestimate": 4692,
    
    # Extensive historical data
    "tax_history": [
        {
            "time": 1694533645604,
            "tax_paid": 6641.4,
            "value": 37445
        }
        # ... 25 years of records
    ],
    
    "price_history": [
        {
            "date": "2025-09-08",
            "event": "Listed for sale",
            "price": 624900,
            "price_per_square_foot": 396
        }
        # ... complete transaction history
    ],
    
    # Climate risk data
    "climate": {
        "flood_sources": {
            "risk_score": {"value": 1, "label": "MINIMAL"},
            "probability": [...] // 30-year projections
        },
        "fire_sources": {...},
        "heat_sources": {...}
    },
    
    # Nearby comparable properties
    "nearby_homes": [
        {
            "zpid": 3868728,
            "address": {...},
            "price": 531500,
            "bedrooms": 2,
            "bathrooms": 2
        }
        // ... 9+ comparable properties
    ],
    
    # Detailed room information
    "reso_facts": {
        "rooms": [
            {
                "room_type": "MasterBedroom",
                "room_area": "325",
                "room_dimensions": "13X25",
                "room_features": ["Flooring (Carpet)", "Bathroom (Full)"]
            }
            // ... 19+ rooms
        ]
    },
    
    # School information
    "schools": [
        {
            "name": "Ogden Elementary School",
            "rating": 3,
            "distance": 1.2,
            "grades": "PK-8",
            "type": "Public"
        }
    ],
    
    # And 1,500+ more fields...
}
```

## Error Handling

The scraper handles various API error conditions:

```python
# Rate limiting
if response.status_code == 429:
    await asyncio.sleep(60)  # Wait for rate limit reset

# Property not found
if response.status_code == 404:
    return ValidationResult(is_valid=False, reason="Property not found")

# API errors
if response.status_code != 200:
    # Log error and continue
    bt.logging.error(f"API error: {response.status_code}")
```

## Validation

The API implementation provides robust validation:

1. **Property Existence**: Verify property exists via API
2. **Content Validation**: Compare field values with tolerance for time-sensitive data
3. **Cross-Validation**: Use different API endpoints for verification

## Advantages

✅ **Complete Data**: Access to all available property information
✅ **Reliability**: Stable API with consistent uptime
✅ **Speed**: Fast response times
✅ **Historical Data**: Complete tax and price history
✅ **Calculated Fields**: Zestimate, comparable analysis
✅ **No Anti-Bot Issues**: Legitimate API access

## Disadvantages

❌ **Cost**: Requires ongoing API subscription costs
❌ **Rate Limits**: Limited to 2 requests/second
❌ **Dependency**: Reliance on third-party service
❌ **Terms of Service**: Must comply with RapidAPI terms

## Alternative Approaches

Miners may choose to implement their own data collection methods, such as:

1. **Direct Web Scraping**: See `../web_scraping_implementation/`
2. **Other APIs**: Alternative real estate data providers
3. **Hybrid Approaches**: Combine multiple data sources
4. **Custom Solutions**: Proprietary data collection methods

## Support and Maintenance

This example implementation is provided as-is. Miners using this approach should:

1. Monitor API costs and usage
2. Handle rate limiting appropriately
3. Implement proper error handling
4. Keep API keys secure
5. Comply with RapidAPI terms of service

## Legal Considerations

- Review RapidAPI terms of service
- Ensure compliance with data usage policies
- Monitor for changes in API pricing or availability
- Maintain appropriate data retention policies
