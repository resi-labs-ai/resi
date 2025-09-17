# API Rate Limiting & Deep Zipcode Scraping Requirements

## 🚨 **CRITICAL ISSUE: API Cost Explosion**

### Current Implementation Analysis

**Before Upgrade (Property Extended Search Only)**:
- 1 API call per zipcode → gets ~41 properties
- 7,500 zipcodes × 1 call = 7,500 API calls/day
- Cost: Manageable within basic API limits

**After Upgrade (Two-Phase Individual Property API)**:
- 1 search call + 41 individual property calls per zipcode
- 7,500 zipcodes × 42 calls = **315,000 API calls/day**
- Cost: **42x increase** - exceeds even premium API limits!

### API Plan Comparison
| Plan | Monthly Limit | Daily Limit | Current Usage | New Usage | Overage |
|------|---------------|-------------|---------------|-----------|---------|
| Basic | 13,000 | 433 | ✅ 250 | ❌ 10,500 | 24x over |
| Premium | 198,000 | 6,600 | ✅ 250 | ❌ 10,500 | 1.6x over |
| Enterprise | 1,000,000+ | 33,000+ | ✅ 250 | ✅ 10,500 | Within limits |

---

## 📋 **REQUIREMENTS**

### 1. **Dynamic API Budget Management System**

#### Environment Variables
```bash
# Monthly API budget configuration
ZILLOW_MONTHLY_API_CALLS=13000          # Default: Basic plan
ZILLOW_DAILY_BUFFER_PERCENT=10          # Keep 10% buffer
ZILLOW_API_PLAN_TYPE=basic              # basic|premium|enterprise

# Advanced rate limiting
ZILLOW_MAX_PROPERTIES_PER_ZIPCODE=41    # Configurable property limit
ZILLOW_ENABLE_DEEP_SCRAPING=false       # Enable multi-page zipcode scraping
ZILLOW_DEEP_SCRAPING_PAGES=3            # Max pages to scrape per zipcode

# Smart batching configuration
ZILLOW_SMART_BATCHING_PERCENT=60        # Only scrape top 60% of properties
ZILLOW_PRIORITY_THRESHOLD=500000        # Only full scrape properties > $500K
```

#### Dynamic Rate Calculation
```python
# Calculate safe daily API usage
monthly_calls = int(os.getenv("ZILLOW_MONTHLY_API_CALLS", "13000"))
buffer_percent = int(os.getenv("ZILLOW_DAILY_BUFFER_PERCENT", "10"))
days_in_month = 30

safe_daily_calls = (monthly_calls * (100 - buffer_percent) / 100) / days_in_month
properties_per_zipcode = int(os.getenv("ZILLOW_MAX_PROPERTIES_PER_ZIPCODE", "41"))
calls_per_zipcode = 1 + properties_per_zipcode  # 1 search + N individual

max_zipcodes_per_day = safe_daily_calls // calls_per_zipcode
zipcode_scrape_interval = (24 * 60 * 60) / max_zipcodes_per_day  # seconds between zipcodes
```

### 2. **Tiered Scraping Strategy**

#### Tier 1: Basic Properties (Property Extended Search Only)
- Properties < $500K or low-priority zipcodes
- 1 API call per zipcode (current method)
- ~22 fields per property

#### Tier 2: Premium Properties (Full Individual Property API)
- Properties > $500K or high-priority zipcodes
- 1 + N API calls per zipcode (new method)
- ~100+ fields per property

#### Tier 3: Deep Zipcode Scraping
- Multi-page scraping for high-value zipcodes
- Track property changes over time (delta tracking)
- Pagination through all available properties

### 3. **Deep Zipcode Scraping System**

#### Multi-Page Property Discovery
```python
async def deep_scrape_zipcode(zipcode: str, max_pages: int = 3):
    """
    Scrape all pages for a zipcode to get complete property inventory
    
    Phase 1: Discovery - Get all ZPIDs across multiple pages
    Phase 2: Selection - Apply smart batching and priority scoring  
    Phase 3: Collection - Fetch individual property details
    Phase 4: Delta Tracking - Compare with previous scrapes
    """
    all_zpids = []
    
    # Phase 1: Multi-page discovery
    for page in range(1, max_pages + 1):
        search_results = await fetch_property_search(zipcode, page)
        page_zpids = extract_zpids(search_results)
        all_zpids.extend(page_zpids)
        
        if len(page_zpids) < 41:  # Last page
            break
    
    # Phase 2: Smart selection based on budget
    selected_zpids = apply_smart_selection(all_zpids, api_budget_remaining)
    
    # Phase 3: Individual property collection
    properties = await fetch_individual_properties(selected_zpids)
    
    # Phase 4: Delta tracking
    deltas = calculate_property_deltas(zipcode, properties)
    
    return properties, deltas
```

#### Delta Tracking System
```python
class PropertyDeltaTracker:
    """Track property changes over time for efficient re-scraping"""
    
    def __init__(self):
        self.last_scrape_cache = {}  # zpid -> last_scraped_data
        self.change_frequency = {}   # zpid -> change_frequency_score
    
    def calculate_deltas(self, zipcode: str, current_properties: List[Property]):
        """
        Compare current scrape with previous scrape to identify:
        - New properties (not seen before)
        - Changed properties (price, status, details changed)
        - Removed properties (no longer available)
        """
        
    def get_priority_properties(self, zipcode: str) -> List[str]:
        """
        Return ZPIDs that should be prioritized for full scraping:
        - High-change frequency properties
        - Recently changed properties
        - High-value properties
        """
```

---

## 🎯 **ACTION PLAN**

### Phase 1: Emergency API Cost Control (Week 1)
**Priority: CRITICAL - Prevent API budget exhaustion**

#### Task 1.1: Implement Emergency Rate Limiting
- [ ] Add `ZILLOW_MONTHLY_API_CALLS` environment variable
- [ ] Calculate safe daily API limits with buffer
- [ ] Add budget checking before each zipcode scrape
- [ ] Implement emergency throttling when budget is low

#### Task 1.2: Smart Batching Enhancement
- [ ] Add `ZILLOW_PRIORITY_THRESHOLD` for property value filtering
- [ ] Implement tiered scraping (basic vs premium properties)
- [ ] Reduce smart batching percentage to 40% (from 60%)
- [ ] Add property value-based selection criteria

#### Task 1.3: Budget Monitoring System
- [ ] Create `APIBudgetManager` class
- [ ] Add real-time usage tracking
- [ ] Implement daily/monthly budget alerts
- [ ] Add budget exhaustion protection

### Phase 2: Deep Zipcode Scraping (Week 2-3)
**Priority: HIGH - Enable comprehensive data collection**

#### Task 2.1: Multi-Page Property Discovery
- [ ] Implement `deep_scrape_zipcode()` method
- [ ] Add pagination support for Property Extended Search
- [ ] Handle multiple pages per zipcode (up to 10 pages)
- [ ] Extract all available ZPIDs from zipcode

#### Task 2.2: Delta Tracking System
- [ ] Create `PropertyDeltaTracker` class
- [ ] Implement property change detection
- [ ] Add change frequency scoring
- [ ] Store delta history for trend analysis

#### Task 2.3: Intelligent Property Selection
- [ ] Prioritize changed properties for full scraping
- [ ] Skip unchanged properties (use cached data)
- [ ] Focus on high-value and high-activity properties
- [ ] Implement property lifecycle tracking

### Phase 3: Advanced Zipcode Management (Week 3-4)
**Priority: MEDIUM - Optimize scraping efficiency**

#### Task 3.1: Zipcode Priority System
- [ ] Create `ZipcodeScheduler` class
- [ ] Implement zipcode priority scoring
- [ ] Add market activity level tracking
- [ ] Schedule zipcodes based on data freshness needs

#### Task 3.2: Dynamic Scraping Cadence
- [ ] Adjust scraping frequency based on zipcode priority
- [ ] High-priority zipcodes: daily scraping
- [ ] Medium-priority zipcodes: weekly scraping
- [ ] Low-priority zipcodes: monthly scraping

---

## 📊 **EXPECTED OUTCOMES**

### API Cost Reduction
- **Immediate**: 60-80% reduction in API calls through smart batching
- **Short-term**: 40-60% reduction through tiered scraping
- **Long-term**: 20-40% reduction through delta tracking

### Data Quality Improvement
- **Coverage**: 100% property discovery through deep scraping
- **Freshness**: Real-time change detection and delta tracking
- **Richness**: Full property details for high-value properties
- **Accuracy**: Historical trend tracking and validation

### Operational Efficiency
- **Budget Management**: Automated budget monitoring and alerting
- **Resource Optimization**: Intelligent zipcode and property prioritization
- **Scalability**: Support for different API plan tiers
- **Maintenance**: Automated parameter tuning based on usage patterns

---

## ⚠️ **IMPLEMENTATION PRIORITY**

**IMMEDIATE (This Week)**:
1. Add monthly API budget configuration
2. Implement emergency rate limiting
3. Reduce smart batching to 40% of properties
4. Add budget exhaustion protection

**SHORT-TERM (Next 2-3 Weeks)**:
1. Deep zipcode scraping with pagination
2. Delta tracking system
3. Tiered scraping based on property value
4. Zipcode priority scheduling

**LONG-TERM (Next Month)**:
1. Advanced market intelligence integration
2. Performance optimization
3. Cost analytics and reporting
4. Scalability improvements

This plan addresses the critical API cost issue while building toward comprehensive, intelligent real estate data collection.
