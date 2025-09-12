# Zillow Validator Testing Guide

## 🎉 **Test Results: All 61 Tests Passing!**

Your Zillow validation system has a comprehensive test suite covering all critical functionality.

## 🧪 **Running the Tests**

### 1. **Unit Tests** (Recommended)

```bash
# Activate virtual environment
source venv/bin/activate

# Install pytest if not already installed
pip install pytest

# Run all Zillow tests
python -m pytest tests/scraping/zillow/ -v

# Run specific test categories
python -m pytest tests/scraping/zillow/test_utils.py -v      # Validation logic tests
python -m pytest tests/scraping/zillow/test_model.py -v     # Data model tests
python -m pytest tests/scraping/zillow/test_scraper.py -v   # Scraper validation tests

# Run with coverage (if you have pytest-cov installed)
python -m pytest tests/scraping/zillow/ --cov=scraping.zillow --cov-report=html
```

### 2. **Integration Testing Options**

#### A. **API Testing** (Test Property Existence)
```bash
# Test with your actual property from scratchpad2.md
curl -X GET "https://zillow-com1.p.rapidapi.com/property?zpid=70982473" \
  -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
  -H "X-RapidAPI-Host: zillow-com1.p.rapidapi.com"
```

#### B. **Validator Component Testing**
```python
# Create a test script: test_validator_integration.py
import asyncio
from scraping.zillow.rapid_zillow_scraper import ZillowRapidAPIScraper
from common.data import DataEntity, DataSource
from datetime import datetime, timezone

async def test_validator():
    scraper = ZillowRapidAPIScraper()
    
    # Test with your actual property
    entity = DataEntity(
        uri="https://zillow.com/homedetails/7622-R-W-Emerson-Loop-Laredo-TX-78041/70982473_zpid/",
        datetime=datetime.now(timezone.utc),
        source=DataSource.RAPID_ZILLOW,
        label="zip:78041",
        content=b'{"zpid":"70982473","address":"7622 R W Emerson Loop, Laredo, TX 78041","price":465000}',
        content_size_bytes=100
    )
    
    results = await scraper.validate([entity])
    print(f"Validation Result: {results[0].is_valid}")
    print(f"Reason: {results[0].reason}")

# Run the test
asyncio.run(test_validator())
```

#### C. **Full Miner-Validator Simulation**
```python
# Create test_miner_validator_flow.py
import asyncio
from scraping.zillow.rapid_zillow_scraper import ZillowRapidAPIScraper
from scraping.zillow.model import RealEstateContent
from datetime import datetime, timezone

async def simulate_miner_validator_flow():
    """Simulate the complete miner -> validator flow"""
    
    # Step 1: Simulate miner scraping (using Property Extended Search data)
    miner_data = {
        "zpid": "70982473",
        "address": "7622 R W Emerson Loop, Laredo, TX 78041",
        "property_type": "SINGLE_FAMILY",
        "bedrooms": 4,
        "bathrooms": 3.0,
        "living_area": 2464,
        "price": 465000,
        "zestimate": 460900,
        "listing_status": "FOR_SALE",
        "days_on_zillow": 15,
        "scraped_at": datetime.now(timezone.utc)
    }
    
    # Create miner's data entity
    miner_content = RealEstateContent(**miner_data)
    miner_entity = miner_content.to_data_entity()
    
    # Step 2: Validator validates the miner's data
    scraper = ZillowRapidAPIScraper()
    validation_results = await scraper.validate([miner_entity])
    
    # Step 3: Check results
    result = validation_results[0]
    print(f"✅ Validation {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"📝 Reason: {result.reason}")
    print(f"📊 Bytes Validated: {result.content_size_bytes_validated}")
    
    return result.is_valid

# Run the simulation
asyncio.run(simulate_miner_validator_flow())
```

## 🔍 **Test Coverage Overview**

### **Test Categories (61 Tests Total)**

#### **1. Validation Logic Tests** (`test_utils.py` - 24 tests)
- ✅ **Critical Field Validation**: zpid, address, property_type must match exactly
- ✅ **Time-Sensitive Field Tolerance**: price (5%), zestimate (10%), days_on_zillow (7 days)
- ✅ **Listing Status Compatibility**: Valid status transitions (FOR_SALE → PENDING → SOLD)
- ✅ **Timestamp Handling**: Uses miner's datetime to avoid validation failures
- ✅ **Error Handling**: Graceful handling of validation exceptions
- ✅ **Integration Scenarios**: Realistic miner-validator scenarios

#### **2. Data Model Tests** (`test_model.py` - 19 tests)
- ✅ **API Data Conversion**: From Zillow API response to RealEstateContent
- ✅ **DataEntity Conversion**: Serialization and deserialization
- ✅ **Field Validation**: Optional fields, data types, constraints
- ✅ **Utility Methods**: Price per sqft, lot size calculations, property analysis
- ✅ **Edge Cases**: Missing data, invalid values, boundary conditions

#### **3. Scraper Validation Tests** (`test_scraper.py` - 18 tests)
- ✅ **Property Existence Checks**: API calls, rate limiting, error handling
- ✅ **Content Fetching**: Individual property API integration
- ✅ **Multi-Step Validation**: Existence + content validation pipeline
- ✅ **Exception Handling**: API errors, network issues, malformed responses
- ✅ **Multi-Entity Processing**: Batch validation scenarios

## 🚦 **Test Scenarios Covered**

### **✅ Success Scenarios**
- Valid property with exact field matches
- Time-sensitive fields within tolerance
- Compatible listing status transitions
- Proper timestamp handling

### **⚠️ Failure Scenarios**
- Critical field mismatches (zpid, address)
- Price changes exceeding 5% tolerance
- Invalid listing status transitions
- Property not found in Zillow API
- Malformed data entities

### **🔧 Error Handling**
- API rate limiting responses
- Network timeouts and connection errors
- Invalid JSON responses
- Missing required fields
- Validation exceptions

## 📊 **Performance Benchmarks**

Based on test results:
- **Average test execution**: ~0.73 seconds for 61 tests
- **Memory usage**: Minimal overhead with proper cleanup
- **API simulation**: Mock responses for consistent testing
- **Async handling**: Proper async/await patterns tested

## 🔧 **Additional Testing Options**

### **1. Load Testing**
```python
# Create load_test.py for stress testing
async def load_test_validator(num_requests=100):
    scraper = ZillowRapidAPIScraper()
    entities = [create_test_entity() for _ in range(num_requests)]
    
    start_time = time.time()
    results = await scraper.validate(entities)
    end_time = time.time()
    
    print(f"Processed {num_requests} validations in {end_time - start_time:.2f}s")
    print(f"Success rate: {sum(1 for r in results if r.is_valid) / len(results):.1%}")
```

### **2. Live API Testing** (Use Carefully - API Costs)
```python
# Only run with real API key and sparingly
async def test_live_api():
    scraper = ZillowRapidAPIScraper()
    
    # Use a known property
    entity = create_real_property_entity("70982473")  # Your Laredo property
    results = await scraper.validate([entity])
    
    print(f"Live API test result: {results[0].is_valid}")
```

### **3. Database Integration Testing**
```python
# Test with actual miner storage data
def test_with_stored_data():
    # Read from your SQLite miner storage
    import sqlite3
    conn = sqlite3.connect('SqliteMinerStorage.sqlite')
    
    # Get recent Zillow entities
    cursor = conn.execute("""
        SELECT uri, datetime, source, label, content 
        FROM entities 
        WHERE source = 4  -- DataSource.RAPID_ZILLOW
        LIMIT 5
    """)
    
    for row in cursor:
        entity = DataEntity(*row)
        # Test validation...
```

## 🎯 **Recommended Testing Workflow**

### **For Development:**
1. **Run unit tests** after any code changes
2. **Test specific components** when modifying validation logic
3. **Use mock data** for consistent, fast testing

### **For Deployment:**
1. **Full test suite** before deploying to production
2. **Integration tests** with real (but limited) API calls
3. **Load testing** to verify performance under load

### **For Monitoring:**
1. **Automated test runs** in CI/CD pipeline
2. **Periodic live API tests** to catch API changes
3. **Validation success rate monitoring** in production

## 🚨 **Important Notes**

- **API Costs**: Live API testing uses your RapidAPI quota - use sparingly
- **Rate Limits**: Tests include rate limiting simulation, but be careful with live APIs
- **Test Data**: Uses realistic but synthetic data to avoid API costs
- **Async Testing**: All scraper tests properly handle async/await patterns

Your validator is now thoroughly tested and ready for production! 🎉
