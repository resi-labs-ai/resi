# Zillow Sold Listings Strategy - New Data Source Implementation

## Executive Summary

**New Strategy**: Create `ZILLOW_SOLD` data source that scrapes sold homes by zipcode pagination instead of individual ZPID iteration. This approach is more scalable and aligns with how Zillow organizes sold listings data.

## URL Structure Analysis

Based on the provided Zillow sold listings URL: https://www.zillow.com/brooklyn-new-york-ny-11225/sold/4_p/?searchQueryState=...

### Key Components Identified:

#### 1. **Base URL Pattern**
```
https://www.zillow.com/{city-state-zipcode}/sold/{page_number}_p/
```
Example: `https://www.zillow.com/brooklyn-new-york-ny-11225/sold/4_p/`

#### 2. **Search Query State Parameters** (URL-encoded JSON)
```json
{
  "pagination": {"currentPage": 4},
  "regionSelection": [{"regionId": 62036, "regionType": 7}],
  "filterState": {
    "rs": {"value": true},  // Recently sold filter
    "sort": {"value": "globalrelevanceex"}
  },
  "mapBounds": {
    "west": -73.97012639694213,
    "east": -73.94047189407348,
    "south": 40.65921728342353,
    "north": 40.672221940704354
  }
}
```

#### 3. **Region ID (RID) System**
- **RID URL**: https://www.zillow.com/homes/62034_rid/
- **Purpose**: Region identifiers for specific geographic areas
- **Usage**: Can be used to identify target regions for scraping

## Data Source Architecture Plan

### 1. **New Data Source Definition**

```python
class DataSource(IntEnum):
    # Existing sources...
    ZILLOW = 4              # Individual property scraping (existing)
    ZILLOW_SOLD = 8         # Sold listings by zipcode (NEW)
    
    @property
    def weight(self):
        weights = {
            # ... existing weights ...
            DataSource.ZILLOW: 1.0,         # Individual properties
            DataSource.ZILLOW_SOLD: 1.2,    # Sold listings (higher value)
        }
        return weights[self]
```

### 2. **Zipcode-Based Request Protocol**

```python
class ZillowSoldRequest(BaseProtocol):
    """Protocol for requesting sold listings by zipcode"""
    
    zipcodes: List[str] = Field(
        description="List of zipcodes to scrape sold listings from",
        max_length=20  # Limit per request
    )
    
    max_listings_per_zipcode: int = Field(
        default=100,
        description="Maximum sold listings to scrape per zipcode"
    )
    
    date_range_days: int = Field(
        default=90,
        description="How many days back to look for sold listings"
    )
```

### 3. **Sold Listings Schema**

```python
class ZillowSoldListingContent(BaseRealEstateContent):
    """Schema for sold listings with sale-specific data"""
    
    # Core sold listing data
    zpid: str
    sale_date: Optional[str] = Field(None, description="Date property was sold")
    sale_price: Optional[int] = Field(None, description="Final sale price")
    list_price: Optional[int] = Field(None, description="Original listing price")
    days_on_market: Optional[int] = Field(None, description="Days from listing to sale")
    price_reduction: Optional[int] = Field(None, description="Amount of price reduction")
    
    # Market context
    zipcode: str = Field(description="Zipcode where property is located")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    market_hotness: Optional[str] = Field(None, description="Market competition level")
    
    # Property basics (from listing card)
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    square_feet: Optional[int]
    lot_size: Optional[str]
    property_type: Optional[str]
    
    # Listing metadata
    listing_source: str = Field(default="zillow_sold", description="Source of listing data")
    scraped_from_page: int = Field(description="Which page this listing was found on")
```

## Implementation Strategy

### Phase 1: URL Pattern Analysis and Testing

#### A. **City-State-Zipcode URL Construction**
```python
def construct_sold_url(zipcode: str, page: int = 1) -> str:
    # Need to resolve zipcode to city-state format
    # Example: 11225 -> "brooklyn-new-york-ny-11225"
    city_state = resolve_zipcode_to_city_state(zipcode)
    return f"https://www.zillow.com/{city_state}/sold/{page}_p/"
```

**Challenge**: Need zipcode-to-city-state mapping
**Solution**: 
1. Use external zipcode database
2. Or extract from initial page load
3. Or use RID system as alternative

#### B. **Region ID (RID) Alternative Approach**
```python
def construct_rid_sold_url(region_id: str, page: int = 1) -> str:
    return f"https://www.zillow.com/homes/{region_id}_rid/sold/{page}_p/"
```

**Advantage**: Simpler URL construction, no city-state resolution needed
**Challenge**: Need to map zipcodes to region IDs

### Phase 2: Pagination Strategy

#### A. **Page Discovery Logic**
```python
class SoldListingsPaginator:
    def __init__(self, zipcode: str, max_listings: int = 100):
        self.zipcode = zipcode
        self.max_listings = max_listings
        self.current_page = 1
        self.listings_per_page = 40  # Typical Zillow pagination
        
    async def get_all_pages(self) -> List[str]:
        """Get all page URLs needed to reach max_listings"""
        max_pages = math.ceil(self.max_listings / self.listings_per_page)
        return [self.get_page_url(page) for page in range(1, max_pages + 1)]
```

#### B. **Listing Extraction from Cards**
```python
async def extract_sold_listings_from_page(self, driver, page_url: str) -> List[Dict]:
    """Extract sold listing data from Zillow search results page"""
    
    driver.get(page_url)
    
    # Wait for listings to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="property-card"]'))
    )
    
    listings = []
    property_cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card"]')
    
    for card in property_cards:
        listing_data = self.extract_card_data(card)
        if listing_data:
            listings.append(listing_data)
    
    return listings
```

### Phase 3: Data Extraction Enhancement

#### A. **Listing Card Data Extraction**
From the provided example, each card contains:
- **Address**: "111 Montgomery St APT 10F, Brooklyn, NY 11225"
- **Price**: "$830,000" (sale price)
- **Specs**: "1 bd, 1 ba, 678 sqft"
- **Status**: "Sold"
- **Images**: Multiple photos available

#### B. **Enhanced Data via Individual Property Links**
```python
async def enhance_listing_data(self, basic_listing: Dict) -> Dict:
    """Get additional data by visiting individual property page"""
    
    if basic_listing.get('zpid'):
        # Visit individual property page for more details
        property_url = f"https://www.zillow.com/homedetails/{basic_listing['zpid']}_zpid/"
        enhanced_data = await self.scrape_individual_property(property_url)
        
        # Merge basic + enhanced data
        return {**basic_listing, **enhanced_data}
    
    return basic_listing
```

### Phase 4: Validator Integration

#### A. **Zipcode Selection Strategy**
```python
class ZipcodeSelector:
    """Intelligent zipcode selection for optimal data coverage"""
    
    def select_zipcodes_for_target_listings(self, target_count: int = 5000) -> List[str]:
        """Select zipcodes to reach approximately target_count sold listings"""
        
        # Use historical data or API to estimate listings per zipcode
        zipcode_estimates = self.get_zipcode_listing_estimates()
        
        selected_zipcodes = []
        estimated_total = 0
        
        # Sort by listing density for efficiency
        sorted_zipcodes = sorted(zipcode_estimates.items(), 
                               key=lambda x: x[1], reverse=True)
        
        for zipcode, estimated_listings in sorted_zipcodes:
            if estimated_total >= target_count:
                break
                
            selected_zipcodes.append(zipcode)
            estimated_total += estimated_listings
        
        return selected_zipcodes
```

#### B. **Request Distribution**
```python
# Validator sends zipcode-based requests
request = ZillowSoldRequest(
    source=DataSource.ZILLOW_SOLD,
    zipcodes=["11225", "10001", "90210", "94105"],
    max_listings_per_zipcode=250,  # 4 * 250 = 1000 listings total
    date_range_days=90
)
```

## Technical Implementation Details

### 1. **URL Construction Challenges**

#### Problem: Zipcode to City-State-Zipcode Format
- Need: "11225" → "brooklyn-new-york-ny-11225"
- Solutions:
  1. **Static mapping file**: Pre-built zipcode → city-state mapping
  2. **API lookup**: Use postal code API for resolution
  3. **Page scraping**: Extract from initial Zillow page load
  4. **RID system**: Use region IDs instead of city-state format

#### Recommended Approach: Hybrid Strategy
```python
class ZillowURLBuilder:
    def __init__(self):
        self.zipcode_cache = {}  # Cache successful resolutions
        self.rid_cache = {}      # Cache RID mappings
    
    async def build_sold_url(self, zipcode: str, page: int = 1) -> str:
        # Try cached city-state format first
        if zipcode in self.zipcode_cache:
            city_state = self.zipcode_cache[zipcode]
            return f"https://www.zillow.com/{city_state}/sold/{page}_p/"
        
        # Try RID format as fallback
        if zipcode in self.rid_cache:
            rid = self.rid_cache[zipcode]
            return f"https://www.zillow.com/homes/{rid}_rid/sold/{page}_p/"
        
        # Discover format by testing
        return await self.discover_url_format(zipcode, page)
```

### 2. **Pagination Detection**

#### Challenge: Determine Total Pages Available
```python
async def get_total_pages(self, driver, base_url: str) -> int:
    """Detect total number of pages available for zipcode"""
    
    driver.get(base_url)
    
    try:
        # Look for pagination controls
        pagination = driver.find_element(By.CSS_SELECTOR, '[data-testid="pagination"]')
        page_links = pagination.find_elements(By.CSS_SELECTOR, 'a')
        
        # Get highest page number
        page_numbers = []
        for link in page_links:
            text = link.text.strip()
            if text.isdigit():
                page_numbers.append(int(text))
        
        return max(page_numbers) if page_numbers else 1
        
    except NoSuchElementException:
        # Single page of results
        return 1
```

### 3. **Anti-Detection for Search Pages**

#### Enhanced Stealth for Pagination
```python
class SoldListingsScraper(EnhancedZillowScraper):
    """Specialized scraper for sold listings pagination"""
    
    def __init__(self):
        super().__init__()
        # More conservative for search pages
        self.rate_limiter = RateLimiter(requests_per_minute=15)
        self.max_session_requests = 10  # Restart browser more frequently
    
    async def scrape_zipcode_sold_listings(self, zipcode: str, max_listings: int = 100):
        """Scrape sold listings for a specific zipcode"""
        
        all_listings = []
        page = 1
        
        while len(all_listings) < max_listings:
            await self.rate_limiter.wait_if_needed()
            
            page_url = await self.build_sold_url(zipcode, page)
            page_listings = await self.scrape_sold_page(page_url)
            
            if not page_listings:
                break  # No more listings
            
            all_listings.extend(page_listings)
            page += 1
            
            # Random delay between pages
            await asyncio.sleep(random.uniform(2, 5))
        
        return all_listings[:max_listings]
```

## Advantages of New ZILLOW_SOLD Approach

### 1. **Scalability**
- **Zipcode-based**: More natural data organization
- **Batch processing**: Multiple listings per request
- **Predictable volume**: Can estimate listings per zipcode

### 2. **Data Relevance**
- **Recently sold**: More valuable market data
- **Geographic clustering**: Better for market analysis
- **Complete coverage**: All sold listings in area, not random ZPIDs

### 3. **Validator Control**
- **Zipcode targeting**: Focus on specific markets
- **Volume control**: Adjust listings per zipcode
- **Market coverage**: Ensure diverse geographic representation

### 4. **Reduced Anti-Bot Risk**
- **Natural browsing**: Mimics normal user behavior
- **Fewer requests**: Batch data collection
- **Varied patterns**: Different zipcodes = different URLs

## Next Steps Implementation Plan

### Week 1: URL Pattern Research
1. **Test URL construction** for various zipcodes
2. **Map zipcode → city-state** formats
3. **Investigate RID system** as alternative
4. **Test pagination** behavior across different markets

### Week 2: Core Scraper Development
1. **Build SoldListingsScraper** class
2. **Implement pagination** logic
3. **Create listing card** extraction
4. **Add anti-detection** measures

### Week 3: Schema and Protocol Integration
1. **Define ZillowSoldListingContent** schema
2. **Update DataSource** enum
3. **Create zipcode-based** request protocol
4. **Integrate with miner factory**

### Week 4: Validator Integration
1. **Build zipcode selection** logic
2. **Create volume estimation** system
3. **Update miner.py** for new data source
4. **Test end-to-end** workflow

This approach transforms the scraping strategy from individual property hunting to systematic market coverage, making it much more scalable and valuable for comprehensive real estate data collection.

## Implementation Todo List

### Phase 1: Core Infrastructure
- [ ] Add ZILLOW_SOLD to DataSource enum in common/data.py
- [ ] Create ZillowSoldListingContent schema in miners/zillow/shared/
- [ ] Update OnDemandRequest protocol to support zipcode-based requests
- [ ] Create basic zipcode-to-city-state mapping utility

### Phase 2: URL Pattern & Pagination
- [ ] Build ZillowSoldURLBuilder class for URL construction
- [ ] Implement pagination detection (extract total results like "595 results")
- [ ] Create pagination URL builder with encoded parameters
- [ ] Test URL construction with various zipcodes

### Phase 3: Sold Listings Scraper
- [ ] Create ZillowSoldListingsScraper class extending EnhancedZillowScraper
- [ ] Implement listing card extraction from search results pages
- [ ] Add pagination logic to scrape multiple pages per zipcode
- [ ] Extract ZPID from listing cards for enhanced data collection
- [ ] Add rate limiting and anti-detection measures for search pages

### Phase 4: Data Processing & Schema
- [ ] Create data extraction methods for sold listing cards
- [ ] Implement optional individual property enhancement
- [ ] Add data validation and cleaning
- [ ] Create DataEntity conversion methods

### Phase 5: Integration
- [ ] Update miner_factory.py to include ZILLOW_SOLD scraper
- [ ] Update neurons/miner.py to handle zipcode-based requests
- [ ] Create validator zipcode selection logic
- [ ] Add volume estimation system

### Phase 6: Testing & Validation
- [ ] Create test script for sold listings scraper
- [ ] Test with sample zipcodes (11225, 10001, 90210)
- [ ] Validate data completeness vs individual property scraping
- [ ] Performance testing for batch zipcode processing

## Key Implementation Details Discovered

### Pagination Structure
- **URL Pattern**: `{base_url}/sold/{page}_p/?searchQueryState={encoded_json}`
- **Page Parameter**: Both `4_p` in URL AND `"currentPage":4` in encoded JSON
- **Volume Display**: "595 results" - can extract total listings per zipcode
- **Results Per Page**: ~40 listings per page (observed from sample)

### URL Encoding Requirements
```
currentPage":6} → currentPage"%3A6%7D%2C
```
Need proper URL encoding for the searchQueryState parameter.

### Zipcode-to-City-State Strategy
Use zipcode database/mapping rather than RID system for simpler implementation.

## ✅ IMPLEMENTATION COMPLETED

### Summary of Implementation

All planned components have been successfully implemented:

#### ✅ Phase 1: Core Infrastructure
- **DataSource.ZILLOW_SOLD (8)** added to `common/data.py` with weight 1.2
- **ZillowSoldListingContent** schema created in `miners/zillow/shared/zillow_sold_schema.py`
- **OnDemandRequest** protocol updated with `zipcodes` and `max_listings_per_zipcode` fields
- **ZipcodeMapper** utility created with common zipcode mappings and async resolution

#### ✅ Phase 2: URL Pattern & Pagination  
- **ZillowSoldURLBuilder** class created with proper URL encoding and pagination support
- **Pagination detection** implemented to extract "595 results" style counts
- **URL validation** functions for testing and debugging

#### ✅ Phase 3: Sold Listings Scraper
- **ZillowSoldListingsScraper** class extending EnhancedZillowScraper
- **Listing card extraction** from search results pages with multiple CSS selectors
- **Anti-detection measures** with conservative rate limiting for search pages
- **Property enhancement** with optional individual page scraping (30% sample rate)

#### ✅ Phase 4: Integration
- **MinerFactory** updated to register ZILLOW_SOLD scraper
- **neurons/miner.py** updated to handle zipcode-based requests 
- **DataLabel** format: `zip:12345` for zipcode-based requests

#### ✅ Phase 5: Testing
- **Comprehensive test script** created: `scripts/test_zillow_sold_scraper.py`
- Tests URL construction, validation, basic scraping, and multiple zipcodes
- Saves results to JSON for analysis

### Key Features Implemented

1. **Scalable Architecture**: Zipcode-based scraping vs individual ZPID iteration
2. **Pagination Support**: Handles "595 results" detection and multi-page scraping  
3. **URL Construction**: Converts zipcodes to Zillow URL format (brooklyn-new-york-ny-11225)
4. **Data Enhancement**: Optional individual property page scraping for detailed data
5. **Anti-Detection**: Conservative rate limiting and browser rotation
6. **Flexible Schema**: Supports both basic listing card data and enhanced property data
7. **Integration Ready**: Works with existing miner/validator infrastructure

### Usage Example

**Validator Request:**
```python
request = OnDemandRequest(
    source=DataSource.ZILLOW_SOLD,
    zipcodes=["11225", "10001", "90210"],
    max_listings_per_zipcode=100,
    limit=250
)
```

**Miner Response:**
- Scrapes sold listings from each zipcode's search pages
- Extracts ~40 listings per page with pagination
- Returns up to 250 total DataEntity objects with ZILLOW_SOLD source
- Each entity contains ZillowSoldListingContent with sale price, date, property details

### Performance Characteristics

- **Rate Limited**: 15 requests/minute for search pages
- **Batch Efficient**: ~40 listings per page request vs 1 per ZPID
- **Volume Predictable**: Can estimate listings per zipcode from "595 results" display
- **Enhancement Optional**: 30% of listings get detailed property page data

This implementation successfully transforms the scraping strategy from individual property hunting to systematic market coverage, making it much more scalable and valuable for comprehensive real estate data collection.
