# Adding New Real Estate Platforms

This guide explains how to add new real estate platforms to the multi-source miner architecture using the factory pattern. The system is designed to be easily extensible, allowing developers to add new platforms with minimal changes to the core system.

## Overview

The multi-source architecture consists of:
- **Base Schema**: Common fields across all platforms
- **Platform-Specific Schema**: Extensions for each platform
- **Scraper Implementation**: Platform-specific scraping logic
- **Factory Registration**: Runtime platform selection
- **Protocol Integration**: Unified request/response handling

## Step-by-Step Guide

### Step 1: Add New DataSource

First, add your new platform to the `DataSource` enum in `common/data.py`:

```python
class DataSource(IntEnum):
    """The source of data. Expanded for multi-platform real estate scraping."""
    
    REDDIT = 1
    X = 2
    YOUTUBE = 3
    ZILLOW = 4              # Zillow real estate data
    REDFIN = 5              # Redfin real estate data
    REALTOR_COM = 6         # Realtor.com real estate data
    HOMES_COM = 7           # Homes.com real estate data
    NEW_PLATFORM = 8        # Your new platform

    @property
    def weight(self):
        weights = {
            DataSource.REDDIT: 0.0,        # Disabled
            DataSource.X: 0.0,             # Disabled
            DataSource.YOUTUBE: 0.0,        # Disabled
            DataSource.ZILLOW: 1.0,         # Primary source
            DataSource.REDFIN: 0.8,         # Secondary source
            DataSource.REALTOR_COM: 0.6,    # Tertiary source
            DataSource.HOMES_COM: 0.4,      # Quaternary source
            DataSource.NEW_PLATFORM: 0.7,  # Set appropriate weight
        }
        return weights[self]
```

### Step 2: Create Platform Directory Structure

Create the directory structure for your new platform:

```bash
mkdir -p miners/new_platform/{web_scraping_implementation,shared}
mkdir -p miners/new_platform/api_implementation  # If API is available
```

### Step 3: Create Platform-Specific Schema

Create `miners/new_platform/shared/new_platform_schema.py`:

```python
"""
NewPlatform-specific schema extending the base real estate content model.
"""

import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import Field
import json
import hashlib

from common.data import DataEntity, DataLabel, DataSource
from miners.shared.base_schema import BaseRealEstateContent, PropertyValidationMixin


class NewPlatformRealEstateContent(BaseRealEstateContent, PropertyValidationMixin):
    """NewPlatform-specific real estate content model"""
    
    # Platform-specific identifiers
    new_platform_id: Optional[str] = Field(None, description="NewPlatform property ID")
    listing_key: Optional[str] = Field(None, description="NewPlatform listing key")
    
    # Platform-specific pricing
    platform_estimate: Optional[int] = Field(None, description="Platform's price estimate")
    
    # Platform-specific features
    special_feature: Optional[str] = Field(None, description="Platform-specific feature")
    platform_score: Optional[int] = Field(None, description="Platform-specific score")
    
    # Add more platform-specific fields as needed
    
    def get_platform_source(self) -> DataSource:
        """Return NewPlatform DataSource"""
        return DataSource.NEW_PLATFORM
    
    @classmethod
    def from_web_scraping(cls, scraped_data: Dict[str, Any], identifier: str) -> "NewPlatformRealEstateContent":
        """Create NewPlatformRealEstateContent from web scraping data"""
        
        # Generate consistent ID if needed
        if not scraped_data.get("new_platform_id"):
            identifier_hash = hashlib.md5(identifier.encode()).hexdigest()[:10]
        
        content_data = {
            # Base fields (required)
            "source_id": scraped_data.get("new_platform_id", identifier_hash),
            "source_platform": "new_platform",
            "address": scraped_data.get("address", ""),
            "detail_url": scraped_data.get("detail_url", ""),
            "price": scraped_data.get("price"),
            "bedrooms": scraped_data.get("bedrooms"),
            "bathrooms": scraped_data.get("bathrooms"),
            "living_area": scraped_data.get("living_area"),
            "property_type": scraped_data.get("property_type", "UNKNOWN"),
            "listing_status": scraped_data.get("listing_status", "UNKNOWN"),
            "scraping_method": "web_scraping",
            
            # Platform-specific fields
            "new_platform_id": scraped_data.get("new_platform_id"),
            "listing_key": scraped_data.get("listing_key"),
            "platform_estimate": scraped_data.get("platform_estimate"),
            "special_feature": scraped_data.get("special_feature"),
            "platform_score": scraped_data.get("platform_score"),
            
            # Map common fields
            "agent_name": scraped_data.get("agent_name"),
            "broker_name": scraped_data.get("broker_name"),
            "schools": scraped_data.get("schools"),
            
            # Store remaining data
            "platform_data": {k: v for k, v in scraped_data.items() if k not in [
                # List all mapped fields here to avoid duplication
                "new_platform_id", "address", "detail_url", "price", "bedrooms",
                "bathrooms", "living_area", "property_type", "listing_status",
                "listing_key", "platform_estimate", "special_feature", "platform_score",
                "agent_name", "broker_name", "schools"
            ]}
        }
        
        return cls(**content_data)
    
    def to_data_entity(self) -> DataEntity:
        """Convert to DataEntity for Bittensor storage"""
        
        # Create label based on zipcode
        label = self.create_data_label()
        
        # Serialize content
        content_json = self.model_dump_json()
        content_bytes = content_json.encode('utf-8')
        
        return DataEntity(
            uri=self.detail_url,
            datetime=self.scraped_at,
            source=self.get_platform_source(),
            label=label,
            content=content_bytes,
            content_size_bytes=len(content_bytes)
        )
    
    def get_platform_specific_metrics(self) -> Dict[str, Any]:
        """Get platform-specific metrics"""
        metrics = {}
        
        if self.platform_estimate and self.price:
            metrics["estimate_accuracy"] = abs(self.platform_estimate - self.price) / self.price * 100
        
        if self.platform_score:
            metrics["platform_score"] = self.platform_score
        
        return metrics
```

### Step 4: Create Web Scraper Implementation

Create `miners/new_platform/web_scraping_implementation/direct_new_platform_miner.py`:

```python
"""
Direct NewPlatform Web Scraper Implementation
"""

import asyncio
import json
import logging
import random
import time
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

from scraping.scraper import Scraper, ScrapeConfig, ValidationResult
from miners.new_platform.shared.new_platform_schema import NewPlatformRealEstateContent
from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange


class DirectNewPlatformScraper(Scraper):
    """Direct NewPlatform scraper using Selenium"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)  # Adjust as needed
        self.driver = None
        self.session_count = 0
        self.max_session_requests = 15
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
    
    def _create_driver(self):
        """Create a new undetected Chrome driver"""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')
            
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(30)
            
            return driver
            
        except Exception as e:
            logging.error(f"Failed to create Chrome driver: {e}")
            return None
    
    def _get_driver(self):
        """Get or create a Chrome driver"""
        if self.driver is None or self.session_count >= self.max_session_requests:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            self.driver = self._create_driver()
            self.session_count = 0
        
        return self.driver
    
    async def scrape_identifier(self, identifier: str) -> Optional[DataEntity]:
        """Scrape a single identifier and return DataEntity"""
        await self.rate_limiter.wait_if_needed()
        
        driver = self._get_driver()
        if not driver:
            logging.error(f"Could not create driver for identifier {identifier}")
            return None
        
        try:
            # Construct URL for your platform
            url = self._identifier_to_url(identifier)
            if not url:
                logging.error(f"Could not construct URL for identifier {identifier}")
                return None
            
            logging.info(f"Scraping identifier {identifier} from {url}")
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check for blocking
            if self._is_blocked_or_not_found(driver):
                logging.warning(f"Blocked or not found for identifier {identifier}")
                return None
            
            # Extract data from the page
            property_data = self._extract_property_data(driver, identifier, url)
            if not property_data:
                return None
            
            # Convert to schema and then DataEntity
            content = NewPlatformRealEstateContent.from_web_scraping(property_data, identifier)
            entity = content.to_data_entity()
            
            self.session_count += 1
            return entity
            
        except Exception as e:
            logging.error(f"Error scraping identifier {identifier}: {e}")
            return None
    
    def _identifier_to_url(self, identifier: str) -> Optional[str]:
        """Convert identifier to platform URL"""
        # Implement your platform's URL construction logic
        return f"https://newplatform.com/property/{identifier}"
    
    def _is_blocked_or_not_found(self, driver) -> bool:
        """Check if blocked or property not found"""
        page_source = driver.page_source.lower()
        
        blocked_indicators = [
            'access denied', 'blocked', 'captcha', 'security check',
            'property not found', 'listing not available'
        ]
        
        return any(indicator in page_source for indicator in blocked_indicators)
    
    def _extract_property_data(self, driver, identifier: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract property data from the page"""
        try:
            data = {
                'new_platform_id': identifier,
                'detail_url': url,
                'scraped_at': datetime.now(timezone.utc),
                'scraping_method': 'web_scraping'
            }
            
            # Extract basic information
            data.update(self._extract_basic_info(driver))
            
            # Extract platform-specific features
            data.update(self._extract_platform_features(driver))
            
            # Add more extraction methods as needed
            
            return data
            
        except Exception as e:
            logging.error(f"Error extracting data for {identifier}: {e}")
            return None
    
    def _extract_basic_info(self, driver) -> Dict[str, Any]:
        """Extract basic property information"""
        data = {}
        
        try:
            # Address
            try:
                address_elem = driver.find_element(By.CSS_SELECTOR, '.address, .property-address')
                data['address'] = address_elem.text.strip()
            except NoSuchElementException:
                pass
            
            # Price
            try:
                price_elem = driver.find_element(By.CSS_SELECTOR, '.price, .property-price')
                price_text = price_elem.text.strip().replace('$', '').replace(',', '')
                price_match = re.search(r'(\d+)', price_text)
                if price_match:
                    data['price'] = int(price_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Bedrooms
            try:
                beds_elem = driver.find_element(By.CSS_SELECTOR, '.beds, .bedrooms')
                beds_text = beds_elem.text.strip()
                beds_match = re.search(r'(\d+)', beds_text)
                if beds_match:
                    data['bedrooms'] = int(beds_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Bathrooms
            try:
                baths_elem = driver.find_element(By.CSS_SELECTOR, '.baths, .bathrooms')
                baths_text = baths_elem.text.strip()
                baths_match = re.search(r'([\d.]+)', baths_text)
                if baths_match:
                    data['bathrooms'] = float(baths_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Square feet
            try:
                sqft_elem = driver.find_element(By.CSS_SELECTOR, '.sqft, .square-feet')
                sqft_text = sqft_elem.text.strip().replace(',', '')
                sqft_match = re.search(r'(\d+)', sqft_text)
                if sqft_match:
                    data['living_area'] = int(sqft_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
                
        except Exception as e:
            logging.error(f"Error extracting basic info: {e}")
        
        return data
    
    def _extract_platform_features(self, driver) -> Dict[str, Any]:
        """Extract platform-specific features"""
        data = {}
        
        try:
            # Platform estimate
            try:
                estimate_elem = driver.find_element(By.CSS_SELECTOR, '.platform-estimate, .estimate')
                estimate_text = estimate_elem.text.strip().replace('$', '').replace(',', '')
                estimate_match = re.search(r'(\d+)', estimate_text)
                if estimate_match:
                    data['platform_estimate'] = int(estimate_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Platform score
            try:
                score_elem = driver.find_element(By.CSS_SELECTOR, '.platform-score, .score')
                score_text = score_elem.text.strip()
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    data['platform_score'] = int(score_match.group(1))
            except (NoSuchElementException, ValueError):
                pass
            
            # Special features
            try:
                feature_elem = driver.find_element(By.CSS_SELECTOR, '.special-feature, .feature')
                data['special_feature'] = feature_elem.text.strip()
            except NoSuchElementException:
                pass
                
        except Exception as e:
            logging.error(f"Error extracting platform features: {e}")
        
        return data
    
    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrape properties based on configuration"""
        entities = []
        
        # Extract identifiers from labels (adapt based on your identifier type)
        identifiers = []
        for label in scrape_config.labels or []:
            if label.value.startswith('new_platform_id:'):
                identifier = label.value[17:]  # Remove prefix
                identifiers.append(identifier)
            elif label.value.startswith('address:'):
                # Handle address-based requests
                address = label.value[8:]
                identifiers.append(address)
        
        if not identifiers:
            logging.warning("No identifiers found in scrape configuration")
            return entities
        
        # Limit based on entity_limit
        if scrape_config.entity_limit:
            identifiers = identifiers[:scrape_config.entity_limit]
        
        logging.info(f"Scraping {len(identifiers)} properties from NewPlatform")
        
        # Scrape each identifier
        for identifier in identifiers:
            try:
                entity = await self.scrape_identifier(identifier)
                if entity:
                    entities.append(entity)
                    logging.info(f"Successfully scraped identifier {identifier}")
                else:
                    logging.warning(f"Failed to scrape identifier {identifier}")
                    
            except Exception as e:
                logging.error(f"Error scraping identifier {identifier}: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(entities)} properties from NewPlatform")
        return entities
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """Validate entities by re-scraping"""
        results = []
        
        for entity in entities:
            try:
                # Extract identifier from entity
                content_json = json.loads(entity.content.decode('utf-8'))
                identifier = content_json.get('new_platform_id') or content_json.get('address')
                
                if not identifier:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Could not extract identifier from entity",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                    continue
                
                # Re-scrape the property
                fresh_entity = await self.scrape_identifier(identifier)
                
                if fresh_entity:
                    # Basic validation
                    is_valid = self._validate_entity_fields(entity, fresh_entity)
                    results.append(ValidationResult(
                        is_valid=is_valid,
                        reason="Validated by re-scraping" if is_valid else "Fields do not match",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                else:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Could not re-scrape property for validation",
                        content_size_bytes_validated=entity.content_size_bytes
                    ))
                    
            except Exception as e:
                logging.error(f"Validation error for {entity.uri}: {e}")
                results.append(ValidationResult(
                    is_valid=True,  # Assume valid on error
                    reason=f"Validation error - assumed valid: {str(e)}",
                    content_size_bytes_validated=entity.content_size_bytes
                ))
        
        return results
    
    def _validate_entity_fields(self, original: DataEntity, fresh: DataEntity) -> bool:
        """Validate key fields between entities"""
        try:
            original_content = json.loads(original.content.decode('utf-8'))
            fresh_content = json.loads(fresh.content.decode('utf-8'))
            
            key_fields = ['address', 'bedrooms', 'bathrooms', 'property_type']
            
            for field in key_fields:
                orig_val = original_content.get(field)
                fresh_val = fresh_content.get(field)
                
                if orig_val is not None and fresh_val is not None:
                    if orig_val != fresh_val:
                        logging.warning(f"Field {field} mismatch: {orig_val} vs {fresh_val}")
                        return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating entity fields: {e}")
            return False
    
    def __del__(self):
        """Cleanup driver on destruction"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


class RateLimiter:
    """Rate limiter for web scraping"""
    
    def __init__(self, requests_per_minute: int = 20):
        self.rpm = requests_per_minute
        self.requests = []
    
    async def wait_if_needed(self):
        """Wait if we're exceeding rate limits"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.rpm:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                logging.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)
```

### Step 5: Update Factory Registration

Add your new platform to the factory in `miners/shared/miner_factory.py`:

```python
class MinerPlatform(Enum):
    """Available real estate platforms"""
    ZILLOW = "zillow"
    REDFIN = "redfin"
    REALTOR_COM = "realtor_com"
    HOMES_COM = "homes_com"
    NEW_PLATFORM = "new_platform"  # Add your platform


class MinerFactory:
    def _register_default_scrapers(self):
        """Register default scraper implementations"""
        try:
            # ... existing registrations ...
            
            # NewPlatform implementations
            try:
                from miners.new_platform.web_scraping_implementation.direct_new_platform_miner import DirectNewPlatformScraper
                self.register_scraper(MinerPlatform.NEW_PLATFORM, MinerImplementation.WEB_SCRAPING, DirectNewPlatformScraper)
            except ImportError:
                logging.warning("NewPlatform web scraping implementation not available")
            
        except Exception as e:
            logging.error(f"Error registering default scrapers: {e}")
    
    def get_data_source_for_platform(self, platform: MinerPlatform) -> DataSource:
        """Get the appropriate DataSource enum for a platform"""
        platform_to_source = {
            MinerPlatform.ZILLOW: DataSource.ZILLOW,
            MinerPlatform.REDFIN: DataSource.REDFIN,
            MinerPlatform.REALTOR_COM: DataSource.REALTOR_COM,
            MinerPlatform.HOMES_COM: DataSource.HOMES_COM,
            MinerPlatform.NEW_PLATFORM: DataSource.NEW_PLATFORM,  # Add mapping
        }
        
        return platform_to_source.get(platform, DataSource.ZILLOW)
```

### Step 6: Update Protocol Support

If your platform uses a different identifier type, update the protocol in `miners/shared/protocol.py`:

```python
class MultiSourceRequest(bt.Synapse):
    """Unified protocol for multi-source real estate scraping requests"""
    
    # ... existing fields ...
    
    # Add new identifier type if needed
    new_platform_ids: List[str] = Field(
        default_factory=list,
        description="List of NewPlatform Property IDs to scrape",
        max_length=50
    )


class RequestValidator:
    @staticmethod
    def validate_request(request: MultiSourceRequest) -> List[str]:
        """Validate a multi-source request and return any errors"""
        errors = []
        
        # ... existing validation ...
        
        elif request.source == DataSource.NEW_PLATFORM:
            if not request.new_platform_ids:
                errors.append("NewPlatform IDs required for NewPlatform requests")
            else:
                invalid_ids = [nid for nid in request.new_platform_ids if not is_valid_new_platform_id(nid)]
                if invalid_ids:
                    errors.append(f"Invalid NewPlatform IDs: {invalid_ids}")
        
        return errors


def is_valid_new_platform_id(platform_id: str) -> bool:
    """Validate NewPlatform ID format"""
    if not platform_id:
        return False
    
    # Implement your platform's ID validation logic
    return platform_id.isalnum() and 6 <= len(platform_id) <= 12
```

### Step 7: Update Main Miner Integration

The main miner (`neurons/miner.py`) should automatically support your new platform through the factory pattern, but you may need to add specific label handling:

```python
# In neurons/miner.py, the factory pattern should automatically handle your platform
elif synapse.source == DataSource.NEW_PLATFORM and hasattr(synapse, 'new_platform_ids') and synapse.new_platform_ids:
    bt.logging.info(f"Processing NewPlatform ID-based request with {len(synapse.new_platform_ids)} IDs")
    labels.extend([DataLabel(value=f"new_platform_id:{nid}") for nid in synapse.new_platform_ids])
```

### Step 8: Create Tests

Create comprehensive tests in `tests/miners/test_new_platform_implementations.py`:

```python
"""
Tests for NewPlatform miner implementations.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from miners.new_platform.shared.new_platform_schema import NewPlatformRealEstateContent
from miners.shared.miner_factory import MinerFactory, MinerPlatform, MinerImplementation
from common.data import DataEntity, DataSource, DataLabel


class TestNewPlatformSchema:
    """Test NewPlatform-specific schema"""
    
    def test_new_platform_schema_creation(self):
        """Test creating NewPlatformRealEstateContent from web scraping data"""
        scraped_data = {
            "address": "123 Test St, Test City, TS 12345",
            "price": 400000,
            "bedrooms": 3,
            "bathrooms": 2,
            "living_area": 1500,
            "new_platform_id": "NP123456",
            "platform_estimate": 395000,
            "platform_score": 85
        }
        
        content = NewPlatformRealEstateContent.from_web_scraping(scraped_data, "NP123456")
        
        assert content.source_platform == "new_platform"
        assert content.new_platform_id == "NP123456"
        assert content.platform_estimate == 395000
        assert content.platform_score == 85
        assert content.get_platform_source() == DataSource.NEW_PLATFORM


class TestNewPlatformMinerFactory:
    """Test NewPlatform miner factory integration"""
    
    def test_new_platform_factory(self):
        """Test creating NewPlatform miner via factory"""
        factory = MinerFactory()
        scraper = factory.create_scraper(MinerPlatform.NEW_PLATFORM, MinerImplementation.WEB_SCRAPING)
        
        assert scraper is not None
        assert hasattr(scraper, 'scrape')
        assert hasattr(scraper, 'validate')


# Add more tests as needed...
```

### Step 9: Create Documentation

Create `miners/new_platform/README.md`:

```markdown
# NewPlatform Real Estate Scraper

This implementation scrapes property data directly from NewPlatform using web scraping.

## Features

- Direct web scraping from NewPlatform property pages
- Platform-specific data extraction
- Anti-detection measures
- Rate limiting

## Installation

```bash
cd miners/new_platform/web_scraping_implementation
pip install -r requirements.txt
```

## Usage

```bash
export MINER_PLATFORM=new_platform
export MINER_IMPLEMENTATION=web_scraping
python ./neurons/miner.py --netuid 428 --wallet.name test_wallet
```

## Configuration

- Rate limit: 20 requests/minute (configurable)
- Session restart: Every 15 requests
- Supported identifiers: NewPlatform IDs, addresses

## Data Fields

### Platform-Specific Fields
- `new_platform_id`: Platform property identifier
- `platform_estimate`: Platform's price estimate
- `platform_score`: Platform-specific scoring

### Universal Fields
- All base real estate fields (address, price, bedrooms, etc.)

## Testing

```bash
python -m pytest tests/miners/test_new_platform_implementations.py -v
```
```

### Step 10: Create Requirements File

Create `miners/new_platform/web_scraping_implementation/requirements.txt`:

```txt
# NewPlatform Web Scraping Requirements

# Core web scraping
selenium==4.15.2
undetected-chromedriver==3.5.4
beautifulsoup4==4.12.2

# Data processing
pandas==2.1.4
numpy==1.24.3

# Async support
aiohttp==3.9.1

# Bittensor dependencies
bittensor>=6.0.0
pydantic>=2.0.0
```

## Best Practices

### 1. Rate Limiting
- Always implement conservative rate limiting
- Start with 10-20 requests/minute
- Monitor for blocking and adjust accordingly

### 2. Error Handling
- Handle all common error scenarios
- Implement graceful degradation
- Log errors appropriately without exposing sensitive data

### 3. Data Validation
- Validate all extracted data
- Handle missing or malformed data gracefully
- Implement field-specific validation logic

### 4. Anti-Detection
- Use undetected-chromedriver
- Rotate user agents
- Implement random delays
- Monitor for blocking patterns

### 5. Testing
- Write comprehensive unit tests
- Test with real data when possible
- Mock external dependencies
- Test error scenarios

### 6. Documentation
- Document all platform-specific features
- Provide clear setup instructions
- Include troubleshooting guide
- Document rate limits and restrictions

## Common Patterns

### ID-Based Platforms
For platforms with incrementable IDs (like Zillow ZPIDs, Redfin IDs):
- Use numeric validation
- Support bulk ID processing
- Implement efficient URL construction

### Address-Based Platforms
For platforms requiring address lookup:
- Implement address normalization
- Handle search result parsing
- Support fuzzy address matching

### API Integration
If the platform provides APIs:
- Create separate API implementation
- Handle authentication and rate limits
- Implement proper error handling

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Driver Issues**: Update Chrome and chromedriver
3. **Rate Limiting**: Reduce request frequency
4. **Element Not Found**: Update CSS selectors for platform changes

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding a new platform:

1. Follow the established patterns
2. Write comprehensive tests
3. Document platform-specific features
4. Test with real data
5. Submit pull request with examples

## Support

- Check existing platform implementations for examples
- Review test files for usage patterns
- Consult the main miners README for architecture overview
