Updated 9/17/25


# An overview from the developer

- Dynamic desirability is not yet being updated by validators, right now there are incentives to pull from new geogrpahic regions, non duplicate data, and fresh data
- We'll be altering the validation code slightly in the coming week to require miners to pull the entire listing from the zillow api, not just the subset of fields returned in the pagination. We will upload the newest base miner code to github.
- The current code gets 1 page of data from each zip code and randomly cycles through them (if everyone is doing the same order you could try changing up your order), you could also alter the code to go deep on 1 zipcode and complete every page in the zipcode until there are no more listings being returned.
- The api currently lists on market houses and will be updated as new houses are added, writing code to find the deltas of those houses and possibly storing the zpids of homes you have pulled before along with a hash of their data would be 1 way to track what homes you've already seen.  If possible finding url parameters to request the delta properties since you last scraped a zipcode would be 1 strategy.
- We will be implementing a dashboard that shows areas that the subnet has scraped - the granularity of the dashboard is yet to be determined.  Miners may be able to access that api to request metrics before scraping data to determine the best locations/ those that need to be refreshed.  Similar to dynamic desirability but altered for our specific realestate use case which requires complete coverage, data accuracy, and freshness.


# Subnet 46 Validator Scoring & Miner Incentive Analysis

## Executive Summary

This analysis examines how validators score miners on Subnet 46 (real estate data scraping) and provides strategic recommendations for miners to maximize their rewards. The current system prioritizes **data uniqueness**, **geographic coverage**, **freshness**, and **validation accuracy** through a sophisticated multi-layered scoring mechanism.

## 🎯 Core Scoring Formula

### Final Score Calculation
```
Raw Score = data_source_weight × job_weight × time_scalar × scorable_bytes
Final Score = Raw Score × (credibility ^ 2.5) + S3_boost
Incentive = (miner_score / total_network_score) × total_reward_pool
```

### Key Components

| Component | Range | Purpose | Impact |
|-----------|-------|---------|---------|
| **Credibility** | 0-1 | Long-term reliability | Exponential multiplier (^2.5) |
| **Scorable Bytes** | Variable | Unique data contribution | Linear scaling factor |
| **Time Scalar** | 0-1 | Data freshness | Linear depreciation |
| **Job Weight** | 1.0-4.0 | Geographic priority | Market-based multiplier |
| **S3 Boost** | Variable | Storage validation bonus | Additive bonus |

---

## 🏆 How Miners Are Scored

### 1. Data Uniqueness (Scorable Bytes)
**Most Critical Factor**: Miners get full credit for unique data, shared credit for duplicated data.

**Calculation**:
- 1 byte credit for data no other miner has
- 1/N byte credit for data shared among N miners
- Zero credit for exact duplicates within the same miner

**Strategy**: Focus on **unique geographic areas** and **fresh listings** that competitors haven't scraped.

### 2. Geographic Coverage (Job Weights)
**Current Priority System**:

| Tier | Weight | Examples | Strategy |
|------|--------|----------|----------|
| **Premium Zipcodes** | 4.0x | 77494, 08701, 77449, 77084 | **Highest ROI** |
| **Tier 1 Premium** | 3.6x | Top metro areas (for sale) | Major cities |
| **Tier 2 Major** | 2.4x | Major metropolitan markets | Secondary cities |
| **Tier 3 Standard** | 1.8x | Standard markets | Suburban areas |
| **Tier 4 Rural** | 1.2x | Rural/smaller markets | Lowest priority |

### 3. Data Freshness (Time Scalar)
**Linear Depreciation Model**:
- Current data: 100% value
- Data at max age (30 days): 50% value  
- Older data: 0% value

**Formula**: `1.0 - (age_in_hours / (2 × max_age_in_hours))`

### 4. Credibility System
**Exponential Impact**: `credibility^2.5` means credibility is crucial
- New miners start at 0 credibility
- Successful validations increase credibility (α=0.15 learning rate)
- Failed validations decrease credibility proportionally
- **Critical**: Low credibility can zero out even large data contributions

### 5. S3 Validation Boost
**Additional Rewards**:
- Separate S3 credibility system (starts at 0.375)
- Enhanced validation using real scrapers
- Size bonuses for large uploads (logarithmic scaling)
- Zero tolerance for duplicates in S3 data

---

## 🚀 Miner Optimization Strategies

### 1. Geographic Strategy
**Immediate Actions**:
- **Target Premium Zipcodes** (4.0x multiplier): 77494, 08701, 77449, 77084, 79936
- **Focus on Tier 1 areas** (3.6x): Major metro "for sale" properties
- **Avoid oversaturated rural areas** (1.2x): Unless no competition

**Advanced Strategy**:
- Monitor validator preferences via Dynamic Desirability system
- Validators can vote on new high-priority zipcodes
- Early entry into new preference areas = maximum uniqueness bonus

### 2. Timing Strategy
**Optimal Scraping Schedule**:
- **Fresh data is king**: Scrape as frequently as API limits allow
- **5-minute intervals** for testnet, longer for mainnet
- **Avoid stale data**: Don't hold data longer than necessary
- **Upload immediately**: S3 storage provides additional validation path

### 3. Uniqueness Strategy
**Data Differentiation**:
- **Geographic diversification**: Spread across multiple zipcodes
- **Property type variety**: Mix for-sale and for-rent properties
- **Timing advantages**: Be first to scrape new listings
- **Quality over quantity**: Better to have unique data than duplicate data

### 4. Validation Strategy
**Build Credibility Fast**:
- **Start conservative**: Focus on easily validated, accurate data
- **Quality control**: Implement data validation before submission
- **Avoid duplicates**: Use content hashing to prevent internal duplication
- **S3 compliance**: Ensure S3 uploads pass enhanced validation

---

## 🎯 Competition Dynamics

### Current State Analysis
**Competition Factors**:
1. **Limited high-value zipcodes**: Premium areas have 4x multiplier but attract competition
2. **API rate limits**: Budget constraints limit aggressive expansion
3. **Credibility barriers**: New miners face exponential penalty until proven
4. **Geographic spread**: 7,500+ supported zipcodes allow specialization

### Competitive Advantages
**How to Rise to the Top**:

1. **Early Geographic Entry**
   - Monitor Dynamic Desirability for new validator preferences
   - Enter new high-priority areas before competitors
   - Establish credibility in premium zipcodes early

2. **Operational Excellence**
   - Maintain 99%+ validation success rate
   - Implement robust data quality controls
   - Optimize API usage for maximum coverage

3. **Strategic Positioning**
   - Focus on underserved high-value areas
   - Balance premium zipcodes with less competitive standard areas
   - Build credibility in easier areas, then expand to premium

4. **Technical Advantages**
   - Faster scraping cycles (within API limits)
   - Better data deduplication
   - More reliable S3 upload processes

---

## ⚠️ Current Incentive Issues & Recommendations

### Issue 1: Geographic Concentration Risk
**Problem**: Premium zipcodes (4x multiplier) create winner-take-all dynamics
**Impact**: May lead to geographic clustering, neglecting broader coverage
**Recommendation**: 
- Consider graduated bonuses for geographic diversity
- Implement diminishing returns for multiple miners in same zipcode
- Add bonus for "coverage completeness" across regions

### Issue 2: New Miner Barriers
**Problem**: Starting credibility of 0 with exponential penalty (^2.5) creates high barriers
**Impact**: New miners effectively get zero rewards until proven
**Recommendations**:
- Start new miners at 0.1-0.2 credibility instead of 0
- Reduce credibility exponent to 2.0 or implement progressive scaling
- Add "new miner grace period" with reduced penalties

### Issue 3: API Cost vs. Reward Imbalance
**Problem**: Premium data requires 42x more API calls but only 4x reward multiplier
**Impact**: May not justify the additional API costs for comprehensive scraping
**Recommendations**:
- Increase premium zipcode multipliers to 6-8x
- Add volume bonuses for comprehensive property data
- Implement tiered validation rewards for detailed vs. basic data

### Issue 4: Validation Bottlenecks
**Problem**: Validators sample limited data for validation due to API costs
**Impact**: High-quality miners may be penalized by unlucky sampling
**Recommendations**:
- Increase validation sample sizes for high-stake miners
- Implement confidence intervals for validation results
- Add "validation insurance" for consistent performers

### Issue 5: S3 vs. Direct Validation Disparity
**Problem**: S3 validation provides additional rewards but has separate credibility system
**Impact**: Creates two-tier system where S3-capable miners have advantages
**Recommendations**:
- Unify credibility systems or clearly separate reward tracks
- Provide alternative validation paths for miners without S3 access
- Balance S3 bonuses with direct validation rewards

---

## 📊 Optimal Miner Configuration

### Recommended Setup
```python
# Geographic Strategy
PRIORITY_ZIPCODES = [
    "77494", "08701", "77449", "77084", "79936",  # Premium 4.0x
    # Add Tier 1 premium areas based on validator preferences
]

# Scraping Strategy  
SCRAPING_FREQUENCY = "5_minutes"  # Testnet
API_BUDGET_ALLOCATION = {
    "premium_zipcodes": 0.6,    # 60% budget to high-value areas
    "tier1_areas": 0.3,         # 30% to major metros
    "exploration": 0.1          # 10% for discovering new opportunities
}

# Quality Control
VALIDATION_THRESHOLD = 0.95     # 95% data accuracy target
DUPLICATE_TOLERANCE = 0.0       # Zero duplicate tolerance
S3_UPLOAD_FREQUENCY = "immediate"  # Upload as soon as scraped
```

### Success Metrics to Track
1. **Credibility Score**: Target >0.8 within first month
2. **Geographic Coverage**: Number of unique zipcodes served
3. **Data Freshness**: Average age of data in hours
4. **Validation Success Rate**: Percentage of successful validations
5. **Uniqueness Ratio**: Percentage of data unique to your miner
6. **S3 Validation Score**: Enhanced validation performance

---

## 🔮 Future Optimization Opportunities

### Upcoming Features to Leverage
1. **Dynamic Desirability Evolution**: Validator voting will create new high-value opportunities
2. **Enhanced Validation**: More sophisticated validation may reward detailed data
3. **Geographic Expansion**: New zipcodes and property types may be added
4. **API Efficiency Improvements**: Better rate limiting may enable more comprehensive scraping

### Strategic Positioning
1. **Build relationships** with validators to understand preference trends
2. **Invest in infrastructure** for rapid geographic expansion
3. **Develop competitive intelligence** on other miners' coverage
4. **Prepare for market shifts** in real estate data demand

---

## 🎯 Action Plan for Miners

### Immediate (Week 1)
1. ✅ **Audit current geographic coverage** - identify gaps in premium zipcodes
2. ✅ **Implement data deduplication** - ensure zero internal duplicates
3. ✅ **Optimize scraping frequency** - maximize freshness within API limits
4. ✅ **Set up S3 validation** - capture additional reward stream

### Short-term (Month 1)  
1. ✅ **Target premium zipcodes** - focus 60% of resources on 4.0x multiplier areas
2. ✅ **Build credibility systematically** - start with easier validations, expand gradually  
3. ✅ **Monitor validator preferences** - watch for new high-priority areas
4. ✅ **Establish quality control processes** - maintain >95% validation success

### Long-term (Months 2-3)
1. ✅ **Geographic diversification** - expand to underserved high-value areas
2. ✅ **Competitive analysis** - understand other miners' strategies and find gaps
3. ✅ **Validator relationship building** - engage with Dynamic Desirability system
4. ✅ **Infrastructure scaling** - prepare for rapid expansion into new opportunities

---

## 💡 Key Takeaways

### For Miners
1. **Uniqueness > Volume**: Better to have small amounts of unique data than large amounts of duplicate data
2. **Geography is King**: Premium zipcodes provide 4x reward multiplier - prioritize them
3. **Credibility is Critical**: Exponential impact means validation accuracy is crucial
4. **Timing Matters**: Fresh data gets full value, stale data gets heavily penalized
5. **S3 Provides Edge**: Additional validation path creates competitive advantage

### For Network Health
1. **Competition is Working**: Geographic and temporal incentives drive healthy competition
2. **Quality is Incentivized**: Validation system rewards accuracy over volume
3. **Innovation is Rewarded**: Early entry into new areas provides first-mover advantages
4. **Barriers May Be Too High**: New miner credibility system may need adjustment

### Bottom Line
**The current incentive system strongly rewards unique, fresh, geographically-strategic data with high validation accuracy.** Miners should focus on premium zipcodes, maintain excellent data quality, and leverage both direct validation and S3 storage for maximum rewards. The exponential credibility system means that building trust with validators is absolutely critical for long-term success.
