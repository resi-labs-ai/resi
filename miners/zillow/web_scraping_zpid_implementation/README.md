# Zillow ZPID Web Scraper

This implementation scrapes **individual properties by ZPID** from Zillow property detail pages.

## Key Features

- **ZPID-based scraping**: Scrapes specific properties by Zillow Property ID
- **Detailed data**: Gets comprehensive property information from detail pages
- **Enhanced extraction**: Uses multiple methods (JSON-LD, JS variables, CSS)
- **Individual focus**: Designed for specific property research

## How It Works

1. **Input**: List of ZPIDs (e.g., `["98970000", "12345678"]`)
2. **Process**: 
   - Visits individual property detail pages
   - Uses enhanced extraction methods for maximum data
   - Handles anti-bot detection with stealth measures
3. **Output**: Detailed property data for specific listings

## Data Schema

Uses `ZillowRealEstateContent` which includes:
- Complete property details (price, specs, history)
- Zestimate and market data
- Agent and listing information
- Photos, schools, neighborhood data
- Price and tax history

## Available Scrapers

### Enhanced Scraper (Recommended)
- **File**: `enhanced_zillow_miner.py`
- **Features**: 85%+ data completeness, multiple extraction methods
- **Use case**: Maximum data quality for individual properties

### Direct Scraper (Basic)
- **File**: `direct_zillow_miner.py`
- **Features**: Basic property data extraction
- **Use case**: Simple property information

## Usage

```python
from miners.zillow.web_scraping_zpid_implementation.enhanced_zillow_miner import EnhancedZillowScraper

scraper = EnhancedZillowScraper()
config = ScrapeConfig(
    labels=[DataLabel(value="zpid:98970000")],
    entity_limit=50
)
entities = await scraper.scrape(config)
```

## Performance

- **Rate limited**: 25 requests/minute for property pages
- **Individual focused**: 1 property per request
- **Data rich**: High information density per property
- **Anti-detection**: Advanced stealth measures

## Validator Integration

Validators should:
1. Send ZPID-based requests: `DataSource.ZILLOW`
2. Specify individual property IDs to scrape
3. Expect detailed property information

This scraper is designed for detailed property research rather than market-wide analysis.