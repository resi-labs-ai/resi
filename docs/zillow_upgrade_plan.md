# Zillow Data Upgrade Action Plan

## Current State vs Target State

### Current State: Property Extended Search (Miners)
- **API**: `/propertyExtendedSearch` 
- **Fields**: ~22 basic property fields
- **Data Volume**: Lightweight, fast scraping
- **Limitations**: Missing detailed property information

### Target State: Individual Property API (Full Data)
- **API**: `/property` (individual property lookup)
- **Fields**: 100+ detailed property fields  
- **Data Volume**: Rich property details
- **Benefits**: Complete property information, better validation

## Phase-by-Phase Upgrade Strategy

### Phase 1: Current Implementation ✅ COMPLETED
**Status**: Implemented subset validation
- ✅ Created field mapping system (`field_mapping.py`)
- ✅ Implemented subset-based validation (only validates miner-available fields)
- ✅ Updated validation logic to handle field differences
- ✅ Ensured compatibility between miner and validator data sources

**Result**: Validation now works with current miner data structure

### Phase 2: Enhanced Validation & Monitoring 📊
**Timeline**: 1-2 weeks
**Goal**: Improve validation accuracy and add monitoring

#### Tasks:
- [ ] Add validation metrics and logging
- [ ] Create dashboard for validation success rates
- [ ] Implement field-by-field validation statistics
- [ ] Add alerts for validation anomalies
- [ ] Create validation performance benchmarks

#### Deliverables:
- Validation metrics dashboard
- Performance monitoring system
- Field validation accuracy reports

### Phase 3: Gradual Field Expansion 🔄
**Timeline**: 2-4 weeks  
**Goal**: Incrementally add more fields without breaking existing miners

#### Strategy: Backwards-Compatible Field Addition
1. **Add optional fields to RealEstateContent model**
2. **Update miners to scrape additional fields (optional)**
3. **Validators validate both old and new field sets**
4. **Monitor adoption rates**

#### Priority Fields for Addition:
1. **Property Details**: `yearBuilt`, `propertySubType`, `homeType`
2. **Financial**: `propertyTaxRate`, `monthlyHoaFee`, `taxAnnualAmount`
3. **Features**: `hasGarage`, `hasPool`, `hasFireplace`, `stories`
4. **Location**: `schoolDistrict`, `neighborhoodRegion`, `walkScore`

#### Implementation:
```python
# Add to RealEstateContent model (all optional)
class RealEstateContent(BaseModel):
    # ... existing fields ...
    
    # Phase 3 additions (optional)
    year_built: Optional[int] = None
    property_tax_rate: Optional[float] = None  
    monthly_hoa_fee: Optional[int] = None
    has_garage: Optional[bool] = None
    stories: Optional[int] = None
    school_district: Optional[str] = None
```

### Phase 4: Full Property API Migration 🚀
**Timeline**: 4-8 weeks
**Goal**: Complete migration to Individual Property API

#### Migration Strategy:
1. **Dual-Mode Operation**: Miners support both APIs
2. **Gradual Rollout**: Percentage-based migration (10% -> 50% -> 100%)
3. **Fallback Mechanism**: Automatic fallback to search API on errors
4. **Performance Monitoring**: Track API response times and success rates

#### Migration Steps:
1. **Update Miner Scraper**:
   ```python
   async def scrape_with_fallback(self, scrape_config):
       try:
           # Try individual property API first
           return await self.scrape_individual_properties(scrape_config)
       except Exception as e:
           # Fallback to search API
           bt.logging.warning(f"Individual API failed, using search API: {e}")
           return await self.scrape_property_search(scrape_config)
   ```

2. **Configuration-Based Mode Selection**:
   ```python
   # Environment variable controls API mode
   USE_INDIVIDUAL_API = os.getenv("ZILLOW_USE_INDIVIDUAL_API", "false").lower() == "true"
   INDIVIDUAL_API_PERCENTAGE = int(os.getenv("ZILLOW_INDIVIDUAL_API_PCT", "0"))
   ```

3. **Gradual Rollout Schedule**:
   - Week 1-2: 10% of miners use individual API
   - Week 3-4: 25% of miners use individual API  
   - Week 5-6: 50% of miners use individual API
   - Week 7-8: 100% migration (if metrics are good)

### Phase 5: Advanced Features 🎯
**Timeline**: 8-12 weeks
**Goal**: Leverage full property data for advanced features

#### Advanced Validation Features:
- **Property History Validation**: Compare against historical data
- **Market Context Validation**: Use comparable properties for validation
- **Anomaly Detection**: ML-based validation for suspicious data
- **Cross-Property Validation**: Validate against neighborhood data

#### New Data Products:
- **Market Analysis**: Property value trends by area
- **Investment Metrics**: Cap rates, cash flow analysis
- **Risk Assessment**: Climate risk, market volatility
- **Neighborhood Insights**: School ratings, crime data, amenities

## Risk Mitigation Strategies

### Technical Risks:
1. **API Rate Limiting**: 
   - Solution: Implement exponential backoff, request queuing
   - Monitoring: Track rate limit hits and response times

2. **Data Quality Issues**:
   - Solution: Enhanced validation, data quality metrics
   - Monitoring: Field completeness rates, validation failure patterns

3. **Performance Degradation**:
   - Solution: Caching, batch processing, async operations
   - Monitoring: Response time percentiles, throughput metrics

### Business Risks:
1. **Miner Adoption**:
   - Solution: Gradual rollout, clear migration guides, support
   - Monitoring: Adoption rates, miner feedback, error rates

2. **Validation Conflicts**:
   - Solution: Extensive testing, validation tolerance tuning
   - Monitoring: Validation success rates, conflict patterns

## Success Metrics

### Phase 2 Metrics:
- Validation success rate > 95%
- Average validation time < 500ms
- Field validation accuracy > 99%

### Phase 3 Metrics:
- New field adoption rate > 80%
- Zero breaking changes for existing miners
- Enhanced data quality scores

### Phase 4 Metrics:
- 100% miner migration success
- API response time < 2s (95th percentile)
- Data completeness > 90% for all fields

### Phase 5 Metrics:
- Advanced validation accuracy > 98%
- New data product usage > 50%
- Market insight accuracy validated against external sources

## Implementation Timeline

```
Month 1: Phase 2 (Enhanced Validation & Monitoring)
├── Week 1-2: Validation metrics implementation
└── Week 3-4: Dashboard and monitoring setup

Month 2: Phase 3 (Gradual Field Expansion)  
├── Week 1-2: Model updates and optional field addition
└── Week 3-4: Miner updates and field adoption monitoring

Month 3: Phase 4 (Full API Migration)
├── Week 1-2: Dual-mode implementation and testing
└── Week 3-4: Gradual rollout and migration

Month 4+: Phase 5 (Advanced Features)
├── Advanced validation features
└── New data products and insights
```

## Resource Requirements

### Development:
- 1 Senior Backend Developer (full-time)
- 1 DevOps Engineer (50% time for infrastructure)
- 1 Data Engineer (25% time for monitoring/analytics)

### Infrastructure:
- Enhanced monitoring systems (Grafana, Prometheus)
- Additional API quota for Individual Property API
- Caching infrastructure (Redis) for performance
- Data storage expansion for additional fields

### Testing:
- Comprehensive integration test suite
- Load testing for API performance
- A/B testing framework for gradual rollout
- Validation accuracy testing against known data

## Rollback Plan

Each phase includes rollback capabilities:

### Phase 2-3 Rollback:
- Disable new validation features via configuration
- Revert to basic field validation
- Maintain backwards compatibility

### Phase 4 Rollback:  
- Switch miners back to Property Extended Search API
- Disable individual property API features
- Maintain existing validation logic

### Emergency Rollback:
- Feature flags for instant rollback
- Automated rollback triggers based on error rates
- Manual override capabilities for immediate response

---

**Next Steps**: 
1. Review and approve this upgrade plan
2. Begin Phase 2 implementation (Enhanced Validation & Monitoring)
3. Set up project tracking and milestone monitoring
4. Establish communication plan for miner updates
