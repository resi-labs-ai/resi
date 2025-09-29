# Subnet 46 Zipcode-Based Incentive Mechanism

## Key Architecture Decisions & Suggestions

### 1. **Communication Flow Recommendation**
**Hybrid Approach**: 
- API server provides zipcode lists to validators every 4 hours
- Validators broadcast assignments to miners via existing bittensor protocol  
- This maintains decentralization while ensuring coordination

### 2. **Zipcode Selection Strategy**
**Population + Property Density Weighted**:
- Use Zillow research data for property counts per zipcode
- Weight by population density for market significance
- Rotate between high-value (Manhattan) and coverage (suburban) markets
- Target 50-100 zipcodes per 4-hour epoch

### 3. **Anti-Gaming Mechanisms**
**Timestamp + Nonce System**:
- API server includes epoch-specific nonce with zipcode assignments
- Miners must include nonce in their S3 uploads (prevents pre-scraping)
- Validators verify nonce matches current epoch
- S3 upload timestamps determine submission order

### 4. **Competitive Scoring Model**
**Multi-Factor Ranking**:
1. **Speed Score** (40%): Position in submission order (1st=100, 2nd=95, etc.)
2. **Quality Score** (40%): Field completeness + spot-check accuracy  
3. **Volume Score** (20%): Listings count vs expected for zipcode

**Reward Distribution**: Top 6 miners evaluated, top 3 rewarded with weights [0.6, 0.3, 0.1]

### 5. **Validation Strategy** 
**Adaptive Spot-Checking**:
- Quick validation: Count check (all miners)
- Deep validation: 5% random sample (top 6 miners only)
- Zero tolerance for fake listings/incorrect zipcodes
- Validators upload validated data to their S3 folders

### 6. **Technical Implementation Priority**

**Phase 1: API Server Extension (Week 1)**
- Extend existing S3 auth server with `/get-zipcode-assignments` endpoint
- Implement zipcode selection algorithm with population weighting
- Add epoch management (4-hour cycles)

**Phase 2: Protocol Updates (Week 2)** 
- Add new bittensor synapse type for zipcode assignments
- Update validator code to fetch and broadcast assignments
- Update miner code to receive and process assignments

**Phase 3: Competitive Scoring (Week 3)**
- Replace MinerScorer with competitive evaluation logic
- Implement submission timestamp tracking
- Add validator S3 upload capabilities

**Phase 4: Testing & Deployment (Week 4)**
- Testnet deployment with monitoring
- Load testing with multiple miners
- Mainnet rollout with community announcements

## ASCII Flow Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Server    │    │   Validators     │    │     Miners      │
│                 │    │                  │    │                 │
│ Every 4 hours:  │    │ Every 4 hours:   │    │ Continuous:     │
│ - Select zips   │◄───┤ - Fetch zip list │    │ - Receive zips  │
│ - Generate nonce│    │ - Broadcast to   │───►│ - Scrape data   │
│ - Store epoch   │    │   miners         │    │ - Upload to S3  │
│                 │    │ - Validate prev  │    │   with nonce    │
│                 │    │   epoch results  │    │                 │
│                 │    │ - Set weights    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ S3 Bucket       │    │ Bittensor Chain  │    │ Local Storage   │
│ - Zipcode data  │    │ - Weight updates │    │ - Scraped data  │
│ - Validator     │    │ - Consensus      │    │ - Upload queue  │
│   uploads       │    │   tracking       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Critical Success Factors

1. **Data Quality**: Zero tolerance for fake/incorrect data
2. **Speed Incentive**: First-to-submit advantage balanced with quality
3. **Geographic Coverage**: Ensure broad market representation
4. **Validator Consensus**: All validators must evaluate same miners deterministically
5. **Anti-Gaming**: Prevent pre-scraping and data manipulation

## Next Steps Questions for You:

1. **Market Focus**: Pennsylvania/NJ first as mentioned, or nationwide from start?
2. **Epoch Length**: 4 hours good, or prefer shorter/longer cycles?
3. **Reward Concentration**: Top 3 only, or spread rewards to top 6-10?
4. **API Hosting**: Digital Ocean preferred over AWS extension?
5. **Testnet Timeline**: How quickly do you want to see this running?


Developer input:
1. I like the api server and messaging
2. I think 50-100 zipcodes is a bit much. we are going for 5000 recently sold listings. There are say 1007 recently sold listings in the brooklyn ny zipcode of 11211.  So I need to pick a number of zipcodes that adds up to say 5000, and then we can adjust that value up as needed.  Actually to get 3M recently sold listings with 5K listings ever 4 hours will still take 100 days.  Is it too ambitious to get that down to 1 month? If what speed should I require from miners? Could they scrape 10K listings in 4 hours? using proxys?

5. validation strategy makes sense. Should make that 5% spot check an adjustable value.  Checking the number of properties returned chould be tricky since zillow only seems to return the top 1000 results even if there are more results in an area.
6. Will the bittensor validators be able to get/ remember the prevous zipcode requests or should the api server also return an endpoint for the prevous zipcode batch for when validators begin validating?

Questions:
1. Does the data storage need to change at all? I believe the miners are already uploading by zipcode.

Task:
- please address these quesitons, please help me to build out these requirements in more detail for each phase of the project.
- for the api server changes please help me define the common api interface requirements so that I can take those to the API repo and implement them seperatly.

---

## UPDATED PLAN - Detailed Requirements

### **Scaling Analysis & Target Calculations**

**Current Targets:**
- 5K listings per 4-hour epoch initially  
- Scale to 10K+ listings per epoch (achievable with proxies)
- 3M total listings in ~1 month (vs 100 days at 5K rate)

**Zipcode Selection Algorithm:**
```python
# Target: 5000 ± 500 listings (±10%)
# Example: Brooklyn 11211 = ~1000 listings
# Need: ~5 similar zipcodes per epoch
# Algorithm: Random selection weighted by expected listing count
```

**Miner Performance Requirements:**
- **5K listings in 4 hours** = ~21 listings/minute (very achievable)
- **10K listings in 4 hours** = ~42 listings/minute (requires good proxies)
- Miners should handle 2-10 zipcodes per assignment

### **Communication Architecture Decision**

**Primary: Miners → API Server Direct**
```
Every 4 hours:
1. API server generates new zipcode batch
2. Miners poll API server for assignments  
3. Validators get previous batch for validation
```

**Fallback: Validator Broadcast** (for redundancy)
```
If miner can't reach API:
1. Query multiple validators for current assignments
2. Validators cache latest API response
3. Consensus mechanism if validators disagree
```

**Complexity Comparison:**
- **Direct API**: Simple, single point of truth, easier debugging
- **Validator Broadcast**: More complex, requires consensus, but more decentralized
- **Recommendation**: Start with direct API, add validator fallback later

### **Reward Distribution Model**

**95% Top-3 Winners + 5% Participation**
```python
# Top 3 miners (based on speed + quality):
winner_1 = 0.50  # 50% of total rewards
winner_2 = 0.30  # 30% of total rewards  
winner_3 = 0.15  # 15% of total rewards

# Remaining 5% distributed among other valid submissions:
participation_pool = 0.05 / num_other_valid_miners

# Zero rewards for:
# - Fake data (wrong zipcodes, non-existent properties)
# - Missing nonce/epoch data
# - Completely empty submissions
```

**Bittensor Scoring Context:**
- Bittensor uses 0-1 scoring for weights
- You can set weights to 0 (no rewards) for bad actors
- Trust/credibility is separate and affects long-term scoring
- Small positive weights (0.001) keep honest miners above zero scorers

### **Validation Timeline & Process**

**4-Hour Offset System:**
```
Epoch N (0:00-4:00): Miners scrape assignments from API
Epoch N+1 (4:00-8:00): Validators validate Epoch N while miners work on new batch
Weight Setting: Validators set weights for Epoch N during Epoch N+1
```

**Validation Process:**
```python
SPOT_CHECK_PERCENTAGE = 5  # Configurable via env var
ZILLOW_RESULT_LIMIT = 1000  # Known Zillow limitation

def validate_miner_submission(miner_data, zipcode_batch):
    # Quick validation (all miners):
    basic_score = validate_basic_requirements(miner_data)
    
    # Deep validation (top 6 miners only):
    if miner_rank <= 6:
        sample_size = min(len(miner_data) * SPOT_CHECK_PERCENTAGE/100, 50)
        accuracy_score = spot_check_listings(miner_data, sample_size)
        return combine_scores(basic_score, accuracy_score)
    
    return basic_score
```

### **Data Storage Requirements**

**Current Storage Analysis:**
✅ **No changes needed** - miners already upload by zipcode to S3
✅ Existing partitioned storage supports zipcode-based organization  
✅ S3 folder structure: `miners/{hotkey}/zipcode={zipcode}/`

**New Requirements:**
- Add epoch/nonce metadata to uploads
- Validators need read access to all miner folders
- Validators upload validated results to their own folders

---

## **API Interface Specification**

### **Endpoint 1: Get Current Zipcode Assignment**
```http
GET /api/v1/zipcode-assignments/current
Headers: 
  Authorization: Bearer {miner_hotkey_signature}
  X-Timestamp: {current_timestamp}
  
Response:
{
  "epoch_id": "2024-03-15-16:00",
  "epoch_start": "2024-03-15T16:00:00Z",
  "epoch_end": "2024-03-15T20:00:00Z", 
  "nonce": "abc123def456",
  "target_listings": 5000,
  "tolerance_percent": 10,
  "zipcodes": [
    {
      "zipcode": "11211",
      "expected_listings": 1000,
      "state": "NY",
      "city": "Brooklyn"
    },
    {
      "zipcode": "19123", 
      "expected_listings": 850,
      "state": "PA",
      "city": "Philadelphia"
    }
  ],
  "submission_deadline": "2024-03-15T20:00:00Z"
}
```

### **Endpoint 2: Get Previous Epoch for Validation**
```http
GET /api/v1/zipcode-assignments/epoch/{epoch_id}
Headers:
  Authorization: Bearer {validator_hotkey_signature}
  
Response: {same format as current, but for specified epoch}
```

### **Endpoint 3: Submit Completion Status** (Optional)
```http
POST /api/v1/zipcode-assignments/status
Body:
{
  "epoch_id": "2024-03-15-16:00",
  "miner_hotkey": "5F...",
  "status": "completed|in_progress|failed",
  "listings_found": 4850,
  "s3_upload_complete": true
}
```

### **Authentication Requirements**
- Reuse existing hotkey signature system from S3 auth server
- Miners sign request with: `zipcode:assignment:{epoch_id}:{timestamp}`
- Validators sign with: `zipcode:validation:{epoch_id}:{timestamp}`

### **Rate Limiting & Security**
- Max 1 request per minute per hotkey for current assignments
- Max 10 requests per hour for historical epochs  
- Blacklist miners not registered on bittensor network

---

## **Detailed Phase Implementation**

### **Phase 1: API Server Extension (Week 1)**

**Requirements:**
1. **Zipcode Database Setup**
   - Import Zillow research data for listing counts per zipcode
   - Create weighted selection algorithm (population + property density)
   - Build epoch management system (4-hour cycles)

2. **New API Endpoints**
   - `/api/v1/zipcode-assignments/current` 
   - `/api/v1/zipcode-assignments/epoch/{id}`
   - `/api/v1/zipcode-assignments/status` (optional)

3. **Selection Algorithm**
   ```python
   def select_zipcodes_for_epoch(target_listings=5000, tolerance=0.1):
       # Random weighted selection to hit target ± tolerance
       # Prefer zipcodes with 500-2000 expected listings
       # Avoid recently assigned zipcodes (within 24 hours)
   ```

4. **Nonce Generation**
   - Epoch-specific nonce: `hash(epoch_id + secret_key + timestamp)`
   - Prevents pre-scraping by changing every epoch

### **Phase 2: Miner Updates (Week 2)**

**Requirements:**
1. **API Client Integration**
   - Add zipcode assignment fetching to miner startup
   - Poll API server every 4 hours for new assignments
   - Handle API failures with exponential backoff

2. **Scraping Modifications**  
   - Focus scraping on assigned zipcodes only
   - Include nonce in S3 upload metadata
   - Add submission timestamp tracking

3. **Fallback Mechanism**
   - Query validators if API server unreachable
   - Implement validator consensus for assignments

### **Phase 3: Validator Updates (Week 2-3)**

**Requirements:**
1. **Validation Logic Replacement**
   - Replace current MinerScorer with competitive evaluation
   - Implement 4-hour offset validation timeline
   - Add configurable spot-check percentage

2. **API Integration**
   - Fetch previous epoch assignments for validation
   - Cache assignments for miner fallback queries
   - Add validator S3 upload capabilities

3. **Scoring Algorithm**
   ```python
   def score_epoch_submissions(epoch_assignments, miner_submissions):
       # 1. Rank by submission timestamp (speed score)
       # 2. Validate data quality for top 6 miners
       # 3. Assign rewards: 95% to top 3, 5% to others
   ```

### **Phase 4: Testing & Deployment (Week 3-4)**

**Requirements:**
1. **Testnet Deployment**
   - Deploy API server on Digital Ocean
   - Test with 3-5 miners and 2 validators
   - Verify epoch transitions and weight setting

2. **Load Testing**
   - Test 10K listings per epoch performance
   - Validate spot-checking accuracy
   - Monitor API server performance under load

3. **Monitoring Dashboard**
   - Track epoch assignments and completion rates
   - Monitor miner performance and validator consensus
   - Alert on API failures or validation issues

---

## **Critical Implementation Questions**

1. **Zillow Rate Limiting**: How will validators handle Zillow's rate limits during spot-checking?
2. **Validator Consensus**: What happens if validators get different assignment data from API?
3. **Miner Failure Recovery**: Should miners be able to "catch up" on missed epochs?
4. **Geographic Bias**: Should we ensure geographic distribution or allow random clustering?

## **Success Metrics**

- **Speed**: 90% of miners complete assignments within 4 hours
- **Quality**: <5% false positive rate in spot-checking  
- **Coverage**: Target listings achieved within ±10% tolerance
- **Participation**: 80%+ of registered miners submit valid data per epoch