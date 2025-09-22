# Multi-Source Real Estate Miner Architecture

This directory contains a comprehensive multi-platform real estate scraping system for the Bittensor RESI subnet. Miners can choose from multiple platforms and implementation methods to maximize their data collection capabilities.

## 🏗️ Architecture Overview

### Supported Platforms

1. **🏠 Zillow** - Primary real estate platform
   - **ID-based**: ZPID incremental scraping
   - **URL Pattern**: `https://www.zillow.com/homedetails/ADDRESS/ZPID_zpid/`
   - **Example**: `98970000_zpid`

2. **🏡 Redfin** - Secondary real estate platform  
   - **ID-based**: Property ID incremental scraping
   - **URL Pattern**: `https://www.redfin.com/STATE/CITY/ADDRESS/home/PROPERTY_ID`
   - **Example**: `20635864`

3. **🏘️ Realtor.com** - Tertiary real estate platform
   - **Address-based**: Address lookup scraping
   - **URL Pattern**: `https://www.realtor.com/realestateandhomes-detail/ADDRESS_SLUG`
   - **Requires**: Address-to-slug conversion

4. **🏙️ Homes.com** - Quaternary real estate platform
   - **Address-based**: Address lookup scraping  
   - **URL Pattern**: `https://www.homes.com/property/ADDRESS/HASH_SLUG/`
   - **Requires**: Address-to-hash conversion

### Implementation Methods

- **🕷️ Web Scraping**: Direct page scraping using Selenium + undetected Chrome
- **🔌 API**: Third-party API integration (where available)

## 📁 Directory Structure

```
miners/
├── zillow/                          # Zillow implementations
│   ├── api_implementation/          # RapidAPI approach (example)
│   ├── web_scraping_implementation/ # Direct scraping (primary)
│   └── shared/
│       └── zillow_schema.py         # Zillow-specific data model
│
├── redfin/                          # Redfin implementations
│   ├── web_scraping_implementation/ # Direct scraping
│   └── shared/
│       └── redfin_schema.py         # Redfin-specific data model
│
├── realtor_com/                     # Realtor.com implementations
│   ├── web_scraping_implementation/ # Direct scraping (address-based)
│   └── shared/
│       └── realtor_schema.py        # Realtor.com data model
│
├── homes_com/                       # Homes.com implementations
│   ├── web_scraping_implementation/ # Direct scraping (address-based)
│   └── shared/
│       └── homes_schema.py          # Homes.com data model
│
├── shared/                          # Cross-platform components
│   ├── base_schema.py               # Base real estate model
│   ├── protocol.py                  # Unified request protocols
│   └── miner_factory.py             # Runtime platform selection
│
└── README.md                        # This file
```

## 🚀 Quick Start

### Environment Configuration

Set your preferred platform and implementation method:

```bash
# Choose platform (zillow, redfin, realtor_com, homes_com)
export MINER_PLATFORM=zillow

# Choose implementation (web_scraping, api)
export MINER_IMPLEMENTATION=web_scraping

# Optional: Configure rate limiting
export MINER_RATE_LIMIT=30
export MINER_MAX_BATCH_SIZE=50
```

### Command Line Usage

```bash
# Start miner with specific platform
python ./neurons/miner.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --miner.platform zillow \
    --miner.implementation web_scraping

# Or use environment variables
export MINER_PLATFORM=redfin
export MINER_IMPLEMENTATION=web_scraping
python ./neurons/miner.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey
```

### Validator Request Examples

#### Zillow ZPID Requests
```python
from common.protocol import OnDemandRequest
from common.data import DataSource

request = OnDemandRequest(
    source=DataSource.ZILLOW,
    zpids=["98970000", "12345678", "87654321"],
    limit=50
)
```

#### Redfin ID Requests
```python
request = OnDemandRequest(
    source=DataSource.REDFIN,
    redfin_ids=["20635864", "19876543", "18765432"],
    limit=50
)
```

#### Address-Based Requests
```python
# Realtor.com
request = OnDemandRequest(
    source=DataSource.REALTOR_COM,
    addresses=[
        "123 Main St, New York, NY 10001",
        "456 Oak Ave, Los Angeles, CA 90210"
    ],
    limit=50
)

# Homes.com
request = OnDemandRequest(
    source=DataSource.HOMES_COM,
    addresses=[
        "789 Pine St, Chicago, IL 60601",
        "321 Elm Dr, Miami, FL 33101"
    ],
    limit=50
)
```

## 📊 Data Schema Comparison

### Universal Fields (All Platforms)
```python
{
    "source_id": "98970000",           # Platform-specific ID
    "source_platform": "zillow",       # Platform identifier
    "address": "123 Main St, City, State 12345",
    "price": 350000,
    "bedrooms": 3,
    "bathrooms": 2,
    "living_area": 1500,
    "property_type": "SINGLE_FAMILY",
    "listing_status": "FOR_SALE",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "photos": ["url1", "url2"],
    "agent_name": "John Doe",
    "scraped_at": "2024-01-15T10:30:00Z",
    "scraping_method": "web_scraping"
}
```

### Platform-Specific Extensions

#### Zillow-Specific Fields
```python
{
    "zpid": "98970000",
    "zestimate": 355000,
    "rent_zestimate": 2800,
    "days_on_zillow": 15,
    "price_history": [...],
    "tax_history": [...],
    "climate_data": {...},
    "nearby_homes": [...]
}
```

#### Redfin-Specific Fields
```python
{
    "redfin_id": "20635864",
    "redfin_estimate": 348000,
    "walk_score": 85,
    "transit_score": 72,
    "bike_score": 68,
    "market_competition": "High",
    "days_on_redfin": 12
}
```

## 🔧 Platform Setup Guides

### Zillow Setup
```bash
# Web scraping (recommended)
cd miners/zillow/web_scraping_implementation
pip install -r requirements.txt

# API (example only)
cd miners/zillow/api_implementation  
pip install -r requirements.txt
# Set RAPIDAPI_KEY in .env
```

### Redfin Setup
```bash
cd miners/redfin/web_scraping_implementation
pip install -r requirements.txt
```

### Realtor.com Setup
```bash
cd miners/realtor_com/web_scraping_implementation
pip install -r requirements.txt
```

### Homes.com Setup
```bash
cd miners/homes_com/web_scraping_implementation
pip install -r requirements.txt
```

## 📈 S3 Storage Structure

Data is organized by platform in S3:

```
s3-bucket/
└── hotkey={miner_hotkey}/
    ├── zillow/
    │   ├── job_id=zillow_zpids_001/
    │   │   └── data_20250915_120000.parquet
    │   └── job_id=zillow_web_scraping/
    │       └── data_20250915_120500.parquet
    │
    ├── redfin/
    │   └── job_id=redfin_web_scraping/
    │       └── data_20250915_120000.parquet
    │
    ├── realtor_com/
    │   └── job_id=realtor_addresses/
    │       └── data_20250915_120000.parquet
    │
    └── homes_com/
        └── job_id=homes_addresses/
            └── data_20250915_120000.parquet
```

## 🎯 Validator Strategies

### ID-Based Allocation (Zillow, Redfin)

Validators can assign specific ID ranges to miners:

```python
# Assign ZPID ranges
miner_a_zpids = ["98970000", "98970001", "98970002"]  # Range 1
miner_b_zpids = ["98980000", "98980001", "98980002"]  # Range 2

# Send targeted requests
request_a = OnDemandRequest(source=DataSource.ZILLOW, zpids=miner_a_zpids)
request_b = OnDemandRequest(source=DataSource.ZILLOW, zpids=miner_b_zpids)
```

### Address-Based Allocation

For platforms without incremental IDs, validators provide address lists:

```python
# Get addresses from Zillow/Redfin data first
addresses_from_zillow = ["123 Main St, NY", "456 Oak Ave, CA"]

# Request same addresses from other platforms for cross-validation
realtor_request = OnDemandRequest(
    source=DataSource.REALTOR_COM, 
    addresses=addresses_from_zillow
)

homes_request = OnDemandRequest(
    source=DataSource.HOMES_COM,
    addresses=addresses_from_zillow
)
```

## ⚡ Performance Comparison

| Platform | Implementation | Speed/Property | Data Completeness | Success Rate |
|----------|---------------|----------------|-------------------|--------------|
| Zillow | API | <1 sec | 100% | 99%+ |
| Zillow | Web Scraping | 3-5 sec | 60-70% | 80-90% |
| Redfin | Web Scraping | 2-4 sec | 70-80% | 85-95% |
| Realtor.com | Web Scraping | 3-6 sec | 50-60% | 70-85% |
| Homes.com | Web Scraping | 4-7 sec | 40-50% | 65-80% |

## 🛡️ Anti-Detection Features

### Built-in Protection
- **Undetected Chrome**: Bypasses basic bot detection
- **User Agent Rotation**: Randomizes browser signatures
- **Rate Limiting**: Configurable request throttling
- **Session Management**: Periodic browser restarts
- **Request Delays**: Random delays between requests

### Advanced Configuration
```python
# Custom rate limiting
export MINER_RATE_LIMIT=20  # Requests per minute

# Proxy support (recommended for production)
export MINER_USE_PROXY=true
export MINER_PROXY_URL=http://proxy:port

# User agent rotation
export MINER_USER_AGENT_ROTATION=true
```

## 🔍 Monitoring and Debugging

### Available Scrapers
```python
from miners.shared.miner_factory import list_available_implementations

print(list_available_implementations())
# Output:
# {
#   "zillow": {"web_scraping": True, "api": True},
#   "redfin": {"web_scraping": True, "api": False},
#   "realtor_com": {"web_scraping": True, "api": False},
#   "homes_com": {"web_scraping": True, "api": False}
# }
```

### Runtime Platform Detection
```python
from miners.shared.miner_factory import get_scraper

# Get scraper for current configuration
scraper = get_scraper()  # Uses environment variables

# Get specific scraper
zillow_scraper = get_scraper("zillow", "web_scraping")
redfin_scraper = get_scraper("redfin", "web_scraping")
```

### Health Checks
```bash
# Test specific platform
python -c "
from miners.shared.miner_factory import get_scraper
scraper = get_scraper('zillow', 'web_scraping')
print('Zillow scraper:', 'Available' if scraper else 'Not available')
"

# Test all platforms
python -c "
from miners.shared.miner_factory import list_available_implementations
import json
print(json.dumps(list_available_implementations(), indent=2))
"
```

## 🔧 Troubleshooting

### Common Issues

#### Platform Not Available
```
Error: No scraper available for source REDFIN
```
**Solution**: Install platform requirements or check environment configuration

#### Invalid Configuration
```
Error: Invalid platform. Must be one of: ['zillow', 'redfin', 'realtor_com', 'homes_com']
```
**Solution**: Check `MINER_PLATFORM` environment variable

#### Chrome Driver Issues
```
Error: Failed to create Chrome driver
```
**Solution**: 
```bash
pip install --upgrade undetected-chromedriver
# Or install Chrome browser if missing
```

#### Rate Limiting
```
Warning: Rate limiting: sleeping for 30.0 seconds
```
**Solution**: Reduce `MINER_RATE_LIMIT` or use proxies

### Debug Mode

Enable detailed logging:
```bash
export MINER_DEBUG=true
python ./neurons/miner.py --logging.debug
```

## 🚀 Future Extensions

### Adding New Platforms

1. **Create platform directory**:
   ```bash
   mkdir -p miners/new_platform/{web_scraping_implementation,shared}
   ```

2. **Implement schema**:
   ```python
   # miners/new_platform/shared/new_platform_schema.py
   class NewPlatformRealEstateContent(BaseRealEstateContent):
       platform_specific_field: str
   ```

3. **Implement scraper**:
   ```python
   # miners/new_platform/web_scraping_implementation/scraper.py
   class NewPlatformScraper(Scraper):
       async def scrape(self, config): ...
   ```

4. **Register with factory**:
   ```python
   # Update miners/shared/miner_factory.py
   self.register_scraper(MinerPlatform.NEW_PLATFORM, ...)
   ```

5. **Add to data sources**:
   ```python
   # Update common/data.py
   class DataSource(IntEnum):
       NEW_PLATFORM = 8
   ```

### Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-platform`
3. **Implement following the patterns above**
4. **Add tests and documentation**
5. **Submit pull request**

## 📄 License

This implementation is part of the Bittensor RESI subnet and follows the same licensing terms. Miners are free to customize and extend these implementations for their specific needs.

## 🤝 Support

- **Documentation**: See individual platform READMEs
- **Issues**: Report via GitHub issues
- **Community**: Join the Bittensor Discord for miner support
- **Updates**: Follow the RESI subnet announcements

---

**Ready to start mining?** Choose your platform, configure your environment, and start contributing valuable real estate data to the Bittensor network! 🏠⛏️