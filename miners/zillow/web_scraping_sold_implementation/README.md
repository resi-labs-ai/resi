# Zillow Sold Listings Web Scraper

This implementation scrapes **sold listings by zipcode** from Zillow search pages.

## Key Features

- **Zipcode-based scraping**: Scrapes ALL sold listings in specified zipcodes
- **Complete coverage**: No artificial limits - gets every sold listing in the area
- **Pagination support**: Automatically handles multiple pages per zipcode
- **Market-focused**: Designed for systematic market data collection

## How It Works

1. **Input**: List of zipcodes (e.g., `["11225", "10001", "90210"]`)
2. **Process**: 
   - Visits Zillow sold listings search pages for each zipcode
   - Extracts total count ("595 results")
   - Scrapes ALL pages to get complete data
   - Optional enhancement with individual property pages (30% sample)
3. **Output**: Complete sold listings data for market analysis

## Data Schema

Uses `ZillowSoldListingContent` which includes:
- Sale price, date, days on market
- Property details (beds, baths, sqft)
- Neighborhood and market context
- Optional enhanced data from property pages

## Usage

```python
from miners.zillow.web_scraping_sold_implementation.zillow_sold_scraper import ZillowSoldListingsScraper

scraper = ZillowSoldListingsScraper()
config = ScrapeConfig(
    labels=[DataLabel(value="zip:11225")],  # Brooklyn
    entity_limit=1000
)
entities = await scraper.scrape(config)
```

## Performance

- **Rate limited**: 15 requests/minute for search pages
- **Batch efficient**: ~40 listings per page request
- **Complete coverage**: Gets ALL sold listings (no arbitrary limits)
- **Market speed**: Varies by zipcode (high-volume areas take longer)

## Validator Integration

Validators should:
1. Select zipcodes to reach target volume (e.g., 5000 listings)
2. Send zipcode-based requests: `DataSource.ZILLOW_SOLD`
3. Expect complete market coverage for each requested zipcode

This scraper is designed for comprehensive market analysis rather than individual property research.
