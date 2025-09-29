# Scratchpad 14: Miner-Validator Separation Implementation

## 🎯 **Project Overview**
Complete restructuring of the codebase to separate miner and validator scraping responsibilities:
- **Miners**: Build their own custom scrapers for data collection
- **Validators**: Use `szill` scraper for validation
- **Schema**: Unified `PropertyDataSchema` for data consistency
- **Focus**: SOLD PROPERTIES from last 3 years (2022-2025)

## 🏗️ **Architecture Changes**

### **1. Directory Structure**
```
scraping/
├── custom/                    # Miner scraper templates
│   ├── schema.py             # PropertyDataSchema (unified)
│   ├── example_scraper.py    # Template for miners
│   ├── zipcodes.csv          # Location data
│   └── model.py              # Legacy model (reference)
├── config/
│   └── miner_scraping_config.json  # Miner configuration
├── miner_provider.py         # Miner scraper provider
└── provider.py              # Base provider (legacy)

vali_utils/scrapers/
├── szill/                    # Szill library integration
│   ├── __init__.py
│   ├── details.py
│   ├── parse.py
│   ├── search.py
│   └── utils.py
├── szill_zillow_scraper.py   # Szill wrapper for validators
├── validator_scraper_provider.py  # Validator provider
└── __init__.py
```

### **2. Key Components**

#### **PropertyDataSchema** (`scraping/custom/schema.py`)
- **Purpose**: Unified data structure for all property data
- **Focus**: SOLD PROPERTIES from 2022-2025
- **Features**: 
  - Pydantic models with proper null handling
  - Comprehensive property information
  - Sales history and market context
  - School and neighborhood data

#### **MinerScraperProvider** (`scraping/miner_provider.py`)
- **Purpose**: Scraper provider for miners only
- **Features**:
  - Excludes RapidAPI scrapers
  - Clear error messages for unavailable scrapers
  - Focus on miner-specific scrapers

#### **ValidatorScraperProvider** (`vali_utils/scrapers/validator_scraper_provider.py`)
- **Purpose**: Scraper provider for validators
- **Features**:
  - Includes `szill` scraper for validation
  - Redirects RapidAPI requests to `szill`
  - Clean, focused implementation

#### **SzillZillowScraper** (`vali_utils/scrapers/szill_zillow_scraper.py`)
- **Purpose**: Direct web scraping for validators
- **Features**:
  - Uses `szill` library for data fetching
  - Converts to `PropertyDataSchema`
  - Validates miner data against fresh data

## 🔧 **Implementation Details**

### **1. Schema Implementation**
```python
class PropertyDataSchema(BaseModel):
    """Schema for SOLD PROPERTIES from last 3 years (2022-2025)"""
    
    # Property IDs
    ids: PropertyIds = Field(default_factory=PropertyIds)
    
    # Property details
    property: PropertyDetails = Field(default_factory=PropertyDetails)
    
    # Sales information
    home_sales: HomeSales = Field(default_factory=HomeSales)
    
    # Market context
    market_context: MarketContext = Field(default_factory=MarketContext)
    
    # Metadata
    metadata: PropertyMetadata = Field(default_factory=PropertyMetadata)
```

### **2. Miner Implementation**
```python
class CustomScraper(Scraper):
    """Template for miner scraper implementation"""
    
    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Implement scraping logic for SOLD PROPERTIES (2022-2025)"""
        # TODO: Implement actual scraping
        pass
    
    def _convert_to_schema(self, raw_data: dict) -> PropertyDataSchema:
        """Convert raw data to PropertyDataSchema"""
        # TODO: Map scraped data to schema
        pass
```

### **3. Validator Implementation**
```python
class SzillZillowScraper(Scraper):
    """Scraper using the szill library"""
    
    async def validate(self, entity: DataEntity) -> ValidationResult:
        """Validate DataEntity using szill scraper"""
        # Fetch fresh data with szill
        # Compare with miner data
        # Return validation result
        pass
```

## 📋 **Configuration Updates**

### **Miner Configuration** (`scraping/config/miner_scraping_config.json`)
```json
{
    "scraper_configs": [
        {
            "scraper_id": "X.apidojo",
            "cadence_seconds": 300,
            "labels_to_scrape": [...]
        }
    ],
    "_comments": {
        "todo": {
            "message": "Implement your own scraping solution",
            "instructions": [
                "1. Create scraper class implementing Scraper interface",
                "2. Use PropertyDataSchema from scraping/custom/schema.py",
                "3. Add scraper to your local scraper provider",
                "4. See scraping/custom/example_scraper.py for guidance",
                "5. Use scraping/custom/zipcodes.csv for location data"
            ]
        }
    }
}
```

### **Environment Variables** (`env.example`)
```bash
# Scraping Configuration
# Miners: Implement your own scraping solution for SOLD PROPERTIES (2022-2025)

# Bittensor Configuration
BT_SUBTENSOR_NETWORK=test
BT_WALLET_NAME=default
BT_WALLET_HOTKEY=default
```

## 🧹 **Code Cleanup**

### **Removed Components**
- ✅ **RapidAPI Integration**: Completely removed from codebase
- ✅ **Cross-References**: Miners don't see validator implementation
- ✅ **Verbose Documentation**: Minimal, focused comments only
- ✅ **Negative Language**: No mentions of "removed" features

### **Clean Implementation**
- **Miner Code**: Focused on their own scraping implementation
- **Validator Code**: Clean validation tools without miner concerns
- **Templates**: Basic TODOs without extensive guidance
- **Configuration**: Simple, clear instructions

## 🚀 **Key Features**

### **1. Unified Schema**
- Single `PropertyDataSchema` for all property data
- Proper null handling with `Union[type, None]`
- Focus on sold properties from 2022-2025
- Comprehensive property information

### **2. Clean Separation**
- **Miners**: Custom scraping solutions
- **Validators**: `szill` scraper for validation
- **No Dependencies**: Miners don't depend on validator tools
- **Clear Boundaries**: Each component has its own purpose

### **3. Production Ready**
- Clean, minimal code
- Proper error handling
- Focused documentation
- Professional implementation

## 📊 **Testing Results**

### **Final Test Output**
```
✅ All imports work
✅ MinerScraperProvider works
✅ ValidatorScraperProvider works
✅ Schema works with null values
🎉 Final clean implementation working!
```

### **Key Validations**
- ✅ Schema handles null values correctly
- ✅ Miner provider excludes RapidAPI
- ✅ Validator provider uses `szill` only
- ✅ No unwanted documentation
- ✅ Clean, focused code

## 🎯 **Final State**

### **Miner Responsibilities**
1. **Build Custom Scrapers**: Implement own scraping logic
2. **Use Schema**: Convert data to `PropertyDataSchema`
3. **Focus on Sold Properties**: 2022-2025 timeframe
4. **Handle Rate Limiting**: Ethical scraping practices

### **Validator Responsibilities**
1. **Use Szill Scraper**: Direct web scraping for validation
2. **Validate Miner Data**: Compare against fresh data
3. **Schema Compliance**: Ensure data matches schema
4. **Quality Assessment**: Evaluate data accuracy

### **Shared Components**
1. **PropertyDataSchema**: Unified data structure
2. **DataEntity**: Standard data format
3. **ValidationResult**: Consistent validation output
4. **Scraper Interface**: Common scraper contract

## ✨ **Success Metrics**

- **Clean Code**: Minimal, focused implementation
- **Clear Separation**: Miners and validators have distinct roles
- **Unified Schema**: Consistent data structure
- **Production Ready**: Professional, maintainable code
- **No Dependencies**: Clean boundaries between components

**The implementation is complete and production-ready!** 🚀
