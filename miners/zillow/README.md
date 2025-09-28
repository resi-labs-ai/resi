# Zillow Miners - Multi-Implementation Architecture

This directory contains multiple Zillow scraping implementations, each optimized for different use cases.

## 📁 Directory Structure

```
miners/zillow/
├── api_implementation/              # Zillow API-based scraping (example)
├── web_scraping_zpid_implementation/    # Individual property scraping by ZPID
├── web_scraping_sold_implementation/    # Sold listings scraping by zipcode
└── shared/                         # Shared utilities and schemas
```

## 🎯 Implementation Types

### 1. **ZPID-Based Web Scraping** (`web_scraping_zpid_implementation/`)
- **Purpose**: Individual property research
- **Input**: Zillow Property IDs (ZPIDs)
- **Data Source**: `DataSource.ZILLOW`
- **Use Case**: Detailed property information, investment analysis
- **Performance**: 1 property per request, data-rich

**Features:**
- Enhanced and basic scraper options
- 85%+ data completeness (enhanced version)
- Comprehensive property details, history, photos
- Anti-bot detection handling

### 2. **Sold Listings Web Scraping** (`web_scraping_sold_implementation/`)
- **Purpose**: Market analysis and comprehensive coverage
- **Input**: Zipcodes
- **Data Source**: `DataSource.ZILLOW_SOLD`
- **Use Case**: Market research, sold comparables, area analysis
- **Performance**: ~40 listings per page request, complete coverage

**Features:**
- Scrapes ALL sold listings in specified zipcodes
- Pagination handling for complete data
- Market-focused data schema
- Optimized for bulk data collection

### 3. **API Implementation** (`api_implementation/`)
- **Purpose**: Example/reference implementation
- **Status**: Moved to example (API deprecated per requirements)
- **Use Case**: Reference for data structure and completeness

## 🔧 Miner Selection

Miners can choose their implementation using environment variables:

```bash
# For individual property scraping (ZPID-based)
export MINER_PLATFORM=zillow
export MINER_IMPLEMENTATION=web_scraping

# For sold listings scraping (zipcode-based)
# This is handled automatically when DataSource.ZILLOW_SOLD is requested
```

## 📊 Data Sources Comparison

| Implementation | Data Source | Input Type | Coverage | Use Case |
|---|---|---|---|---|
| ZPID Web Scraping | `ZILLOW` | Individual ZPIDs | 1 property/request | Property research |
| Sold Listings | `ZILLOW_SOLD` | Zipcodes | All sold in area | Market analysis |
| API (Example) | `ZILLOW` | ZPIDs | High completeness | Reference only |

## 🚀 Usage Examples

### Individual Property Scraping
```python
request = OnDemandRequest(
    source=DataSource.ZILLOW,
    zpids=["98970000", "12345678"],
    limit=50
)
```

### Sold Listings Market Analysis
```python
request = OnDemandRequest(
    source=DataSource.ZILLOW_SOLD,
    zipcodes=["11225", "10001", "90210"],
    limit=1000  # Distributed across zipcodes
)
```

## ⚙️ Configuration

Each implementation has its own:
- **README.md**: Detailed usage instructions
- **requirements.txt**: Specific dependencies
- **Configuration options**: Rate limiting, anti-detection settings

## 🔄 Validator Strategy

**For Property Research:**
- Use `DataSource.ZILLOW` with specific ZPIDs
- Get detailed individual property data

**For Market Analysis:**
- Use `DataSource.ZILLOW_SOLD` with target zipcodes
- Validators select zipcodes to reach desired volume (e.g., 5000 listings)
- Miners scrape ALL sold listings in those zipcodes

This architecture allows miners to specialize in different data collection strategies while maintaining compatibility with the existing validator infrastructure.
