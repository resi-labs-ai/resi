# JIRA TICKET: Full Property Data Upgrade Implementation

## Epic: Zillow Data Enhancement - Full Property Details

### User Story
**As a** Bittensor subnet participant  
**I want** miners to collect comprehensive property details instead of basic listing data  
**So that** the network provides richer real estate intelligence and more valuable data for validators and consumers

### Background
Currently, miners only collect basic property data (22 fields) from Zillow's Property Extended Search API, while validators have access to full property details (100+ fields) but artificially limit validation to maintain fairness. This upgrade will enable miners to collect the same comprehensive data that validators already access, significantly improving the network's data quality and value proposition.

### Business Value
- **Higher Data Quality**: Full property details provide comprehensive real estate intelligence
- **Better Validation**: Validators can perform more sophisticated data quality assessments
- **Competitive Advantage**: Rich data creates network effects and higher barriers to entry
- **Market Intelligence**: Access to historical data, climate risk, neighborhood demographics, and more

---

## Tasks

### Phase 1: Data Model & Infrastructure Updates
- [ ] **RESI-001**: Expand RealEstateContent model with Individual Property API fields
  - Add 100+ new fields (yearBuilt, taxHistory, priceHistory, resoFacts, etc.)
  - Update field validation and serialization
  - Maintain backwards compatibility
- [ ] **RESI-002**: Update ZillowFieldMapper for full field support
  - Expand MINER_AVAILABLE_FIELDS to include all Individual Property API fields
  - Add API_TO_MODEL_MAPPING for new fields
  - Create validation configs for complex fields (arrays, objects)
- [ ] **RESI-003**: Create data migration scripts
  - Script to upgrade existing miner data
  - Backwards compatibility layer for old data format
  - Data validation and integrity checks

### Phase 2: Miner Implementation
- [ ] **RESI-004**: Implement two-phase scraping in ZillowRapidAPIScraper
  - Phase 1: Property Extended Search for zipcode (get ZPIDs)
  - Phase 2: Individual Property API for each ZPID (get full details)
  - Add error handling and retry logic
- [ ] **RESI-005**: Add rate limiting and API cost management
  - Implement smart batching (prioritize high-value properties)
  - Add caching to avoid re-fetching properties
  - Create API usage monitoring and alerts
- [ ] **RESI-006**: Update storage and indexing for full data
  - Modify S3 uploader for larger data payloads
  - Update compression algorithms for efficiency
  - Implement selective storage (hot/cold data tiers)
- [ ] **RESI-007**: Create miner configuration for data collection strategy
  - Configurable property selection criteria
  - Tiered approach (basic vs full details)
  - API usage budgeting and limits

### Phase 3: Validator Updates
- [ ] **RESI-008**: Remove field filtering in validators
  - Stop using create_miner_compatible_content() filtering
  - Enable full field validation
  - Update validation scoring algorithms
- [ ] **RESI-009**: Implement enhanced validation features
  - Data quality metrics (completeness, accuracy, consistency)
  - Historical data validation (tax history, price history)
  - Market intelligence validation (climate risk, demographics)
- [ ] **RESI-010**: Update reward calculation for full data
  - Weight scoring based on data completeness
  - Bonus rewards for high-quality data
  - Penalty system for incomplete or inaccurate data

### Phase 4: Testing & Simulation Updates
- [ ] **RESI-011**: Expand mocked data collection
  - Collect full Individual Property API responses for all test properties
  - Ensure comprehensive field coverage
  - Create validation test cases for new fields
- [ ] **RESI-012**: Update simulation logic
  - Miner simulation with full property detail scraping
  - Validator simulation with full field validation
  - Performance testing with large datasets
- [ ] **RESI-013**: Create comprehensive test suite
  - Field validation tests for all new fields
  - Integration tests for miner-validator flow
  - Performance and load testing

### Phase 5: Communication & Rollout
- [ ] **RESI-014**: Create communication plan for validators and miners
  - Announcement of new validation schema timeline
  - Migration guide and documentation
  - Support channels for questions and issues
- [ ] **RESI-015**: Implement gradual rollout strategy
  - Beta testing with subset of miners
  - Phased validation schema updates
  - Monitoring and rollback procedures
- [ ] **RESI-016**: Update documentation and guides
  - Miner setup guide for full data collection
  - Validator configuration for new validation
  - API usage and cost optimization guides

---

## Acceptance Criteria

### Data Model Updates
- [ ] RealEstateContent model supports all Individual Property API fields
- [ ] Backwards compatibility maintained for existing data
- [ ] Field validation works for all new field types (strings, numbers, arrays, objects)
- [ ] Data serialization/deserialization handles full property data correctly

### Miner Implementation
- [ ] Miners successfully collect full property details for all properties in zipcode
- [ ] Two-phase scraping (search → individual properties) works reliably
- [ ] Rate limiting prevents API quota exhaustion
- [ ] Error handling gracefully manages API failures and retries
- [ ] Data storage and indexing handles larger payloads efficiently
- [ ] S3 upload/download works with full property data

### Validator Implementation
- [ ] Validators validate all fields that miners provide (no artificial filtering)
- [ ] Validation scoring includes data quality and completeness metrics
- [ ] Historical data validation works correctly (tax history, price history)
- [ ] Market intelligence validation functions properly
- [ ] Reward calculation accurately reflects data quality

### Performance & Reliability
- [ ] Full data collection completes within acceptable time limits
- [ ] Validation performance meets network requirements
- [ ] API usage stays within budgeted limits
- [ ] System handles peak load without degradation
- [ ] Error rates remain below acceptable thresholds

### Testing & Quality
- [ ] All new fields have comprehensive test coverage
- [ ] Integration tests pass for full miner-validator flow
- [ ] Mocked simulations accurately represent production behavior
- [ ] Performance tests validate system under load
- [ ] Data integrity checks ensure accuracy

### Communication & Rollout
- [ ] Validators and miners receive clear communication about timeline
- [ ] Migration documentation is complete and accurate
- [ ] Support channels are established and responsive
- [ ] Rollout plan includes monitoring and rollback procedures
- [ ] All stakeholders understand new validation schema requirements

---

## Technical Specifications

### API Rate Limiting Strategy
- **Current**: 7,500 calls/day (1 per zipcode)
- **Proposed**: 315,000 calls/day (1 search + 41 individual per zipcode)
- **Solution**: Smart batching, priority scoring, caching, API tier upgrade

### Data Storage Requirements
- **Current**: ~22 fields per property
- **Proposed**: 100+ fields per property (4-5x larger)
- **Solution**: Enhanced compression, selective storage, archival system

### Validation Performance
- **Current**: 22 fields per property validation
- **Proposed**: 100+ fields per property validation
- **Solution**: Parallel validation, caching, field sampling

---

## Timeline
- **Week 1-2**: Data model updates and infrastructure
- **Week 3-4**: Miner implementation and testing
- **Week 5-6**: Validator updates and testing
- **Week 7-8**: Simulation updates and comprehensive testing
- **Week 9-10**: Communication, documentation, and rollout preparation

---

# Zillow Data Upgrade Analysis: Full Property Details Implementation

## Current System Analysis

### Current Miner Implementation
**Data Source**: Property Extended Search API (`/propertyExtendedSearch`)
- **API Endpoint**: `https://zillow-com1.p.rapidapi.com/propertyExtendedSearch`
- **Data Volume**: Up to 41 properties per zipcode (1 page)
- **Fields Available**: ~22 basic property fields (defined in `ZillowFieldMapper.MINER_AVAILABLE_FIELDS`)
- **Scraping Pattern**: 
  - Scrapes by zipcode using labels like `zip:78041`
  - Gets basic listing data for up to 41 properties per zipcode
  - Stores as `RealEstateContent` objects in `DataEntity` format
  - Uploads to S3 in partitioned buckets

**Current Field Set (Miners)**:
```python
MINER_AVAILABLE_FIELDS = {
    'zpid', 'address', 'detailUrl', 'propertyType', 'bedrooms', 'bathrooms',
    'livingArea', 'lotAreaValue', 'lotAreaUnit', 'price', 'zestimate', 
    'rentZestimate', 'priceChange', 'datePriceChanged', 'latitude', 'longitude',
    'country', 'currency', 'listingStatus', 'daysOnZillow', 'comingSoonOnMarketDate',
    'imgSrc', 'hasImage', 'hasVideo', 'has3DModel', 'carouselPhotos',
    'listingSubType', 'contingentListingType', 'variableData'
}
```

### Current Validator Implementation
**Data Source**: Individual Property API (`/property`)
- **API Endpoint**: `https://zillow-com1.p.rapidapi.com/property`
- **Data Volume**: Single property per API call
- **Fields Available**: 100+ detailed property fields
- **Validation Pattern**:
  - Receives zpids from miners during validation
  - Calls Individual Property API for each zpid
  - Uses `ZillowFieldMapper.create_miner_compatible_content()` to filter to miner-available fields
  - Validates only the subset of fields that miners would have

**Key Insight**: Validators already have access to full property data but artificially limit themselves to miner-compatible fields for "fair" validation.

### Current Mocked Data Structure
**Location**: `/mocked_data/`
- **Property Extended Search**: 10 zipcode files (e.g., `78041_laredo_tx.json`)
- **Individual Properties**: 328 property files (e.g., `70982473_78041.json`)
- **Data Collection**: Scripts collect both search results AND individual property details
- **Simulation**: Uses both data types for comprehensive testing

## Proposed Upgrade Strategy

### Phase 1: Update Miners to Pull Full Property Details

#### 1.1 Modify Miner Scraping Logic
**Current Flow**:
```
Zipcode → Property Extended Search → 41 basic properties → Store
```

**Proposed Flow**:
```
Zipcode → Property Extended Search → Extract ZPIDs → Individual Property API → Full properties → Store
```

#### 1.2 Implementation Changes Required

**A. Update `ZillowRapidAPIScraper`**:
- Add new method `_fetch_individual_property_details(zpid: str)` 
- Modify `_scrape_entities()` to:
  1. First call Property Extended Search for zipcode
  2. Extract all ZPIDs from search results
  3. For each ZPID, call Individual Property API
  4. Store full property details instead of basic search results

**B. Update `RealEstateContent` Model**:
- Expand field set to include all Individual Property API fields
- Add new fields like:
  - `yearBuilt`, `propertySubType`, `homeType`
  - `taxHistory[]`, `priceHistory[]`
  - `resoFacts{}` (50+ property details)
  - `schoolDistrict{}`, `neighborhood{}`
  - `climateRisk{}`, `hoaFee`, `monthlyHoaFee`
  - `contact_recipients[]`, `buildingPermits[]`

**C. Update Field Mapping**:
- Expand `ZillowFieldMapper.MINER_AVAILABLE_FIELDS` to include all Individual Property API fields
- Update `API_TO_MODEL_MAPPING` for new fields
- Add validation configs for new fields

#### 1.3 Rate Limiting Considerations
**Current**: 1 API call per zipcode (Property Extended Search)
**Proposed**: 1 + N API calls per zipcode (1 search + N individual properties)

**Impact Analysis**:
- Current: 7,500 zipcodes × 1 call = 7,500 calls/day
- Proposed: 7,500 zipcodes × (1 + 41) calls = 315,000 calls/day
- **Issue**: This exceeds even premium API limits (198K calls/month)

**Solutions**:
1. **Batch Processing**: Process fewer zipcodes per day but with full details
2. **Selective Scraping**: Only scrape full details for high-value properties
3. **Tiered Approach**: Basic properties get search data, premium properties get full details
4. **API Upgrade**: Move to enterprise API with higher limits

### Phase 2: Update Validators for Full Field Validation

#### 2.1 Remove Field Filtering
**Current**: Validators artificially limit themselves to miner-available fields
**Proposed**: Validators validate against ALL fields that miners now provide

#### 2.2 Update Validation Logic
**A. Update `ZillowFieldMapper`**:
- Remove `create_miner_compatible_content()` filtering
- Update `FIELD_VALIDATION_CONFIG` to include all new fields
- Add validation strategies for complex fields (arrays, objects)

**B. Update Validator Scoring**:
- Expand validation criteria to include full property details
- Add scoring for data completeness and accuracy
- Implement validation for historical data (tax history, price history)

#### 2.3 Enhanced Validation Features
**A. Data Quality Metrics**:
- Validate tax history consistency
- Check price history accuracy
- Verify property details completeness
- Validate school district information

**B. Market Intelligence Validation**:
- Verify climate risk data
- Validate neighborhood demographics
- Check HOA fee accuracy
- Validate contact information

### Phase 3: Update Mocked Simulation

#### 3.1 Expand Mock Data Collection
**Current**: 10 zipcodes, 328 individual properties
**Proposed**: 
- Collect full Individual Property API responses for all 328 properties
- Ensure comprehensive field coverage
- Add validation test cases for new fields

#### 3.2 Update Simulation Logic
**A. Miner Simulation**:
- Simulate full property detail scraping
- Test rate limiting and error handling
- Validate data storage and indexing

**B. Validator Simulation**:
- Test full field validation
- Simulate complex validation scenarios
- Test data quality scoring

#### 3.3 Test Coverage
**A. Field Validation Tests**:
- Test all new fields individually
- Test complex nested objects (tax history, price history)
- Test array fields (photos, contact recipients)

**B. Integration Tests**:
- End-to-end miner → validator flow
- S3 upload/download with full data
- Performance testing with large datasets

## Implementation Roadmap

### Week 1: Data Model Updates
- [ ] Expand `RealEstateContent` model with all Individual Property API fields
- [ ] Update `ZillowFieldMapper` with new field mappings
- [ ] Create migration scripts for existing data

### Week 2: Miner Updates
- [ ] Implement two-phase scraping (search → individual properties)
- [ ] Add rate limiting and error handling
- [ ] Update storage and indexing for full data
- [ ] Test with subset of zipcodes

### Week 3: Validator Updates
- [ ] Remove field filtering in validators
- [ ] Implement full field validation
- [ ] Add data quality scoring
- [ ] Update reward calculation

### Week 4: Testing & Optimization
- [ ] Update mocked data and simulations
- [ ] Performance testing and optimization
- [ ] API rate limit optimization
- [ ] Production deployment

## Technical Considerations

### API Rate Limiting
**Challenge**: Individual Property API calls are 41x more expensive than search calls
**Solutions**:
1. **Smart Batching**: Only fetch full details for properties that pass initial validation
2. **Priority Scoring**: Focus on high-value properties first
3. **Caching**: Cache individual property data to avoid re-fetching
4. **API Tiers**: Consider upgrading to higher API tier

### Data Storage
**Challenge**: Full property data is significantly larger
**Solutions**:
1. **Compression**: Implement better compression for S3 storage
2. **Selective Storage**: Store only essential fields in hot storage
3. **Archival**: Move detailed historical data to cold storage

### Validation Performance
**Challenge**: Validating 100+ fields per property is computationally expensive
**Solutions**:
1. **Parallel Validation**: Validate fields in parallel
2. **Caching**: Cache validation results
3. **Sampling**: Validate subset of fields per validation cycle

## Expected Benefits

### For Miners
- **Higher Data Value**: Full property details are more valuable than basic listings
- **Better Rewards**: More comprehensive data should lead to higher validator scores
- **Competitive Advantage**: Miners with full data will outperform those with basic data

### For Validators
- **Better Validation**: Can validate data quality, not just existence
- **Market Intelligence**: Access to rich market data for analysis
- **Improved Scoring**: More sophisticated scoring based on data completeness

### For the Network
- **Higher Data Quality**: Full property details provide much richer dataset
- **Better Market Intelligence**: Access to comprehensive real estate data
- **Competitive Moat**: High-quality data creates network effects

## Risks and Mitigation

### API Cost Risk
**Risk**: Individual Property API calls are expensive
**Mitigation**: Implement smart batching and priority scoring

### Performance Risk
**Risk**: Full data validation may be slow
**Mitigation**: Implement parallel processing and caching

### Compatibility Risk
**Risk**: Breaking changes to existing miners
**Mitigation**: Implement gradual rollout with backwards compatibility

### Data Quality Risk
**Risk**: More fields means more potential for validation failures
**Mitigation**: Implement robust error handling and field-level validation strategies
