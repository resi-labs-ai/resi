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
- **TARGET_LISTINGS=10000** (configurable env variable: 5K-15K range)
- Scale dynamically based on miner performance and network capacity
- 3M total listings in ~1 month (vs 100 days at 5K rate)
- **Tolerance**: ±10% of target (configurable via TOLERANCE_PERCENT)

**Zipcode Selection Algorithm:**
```python
# Configuration Variables (Environment)
TARGET_LISTINGS = 10000  # Configurable: 5K-15K range
TOLERANCE_PERCENT = 10   # ±10% tolerance  
MIN_ZIPCODE_LISTINGS = 200    # Avoid tiny markets
MAX_ZIPCODE_LISTINGS = 3000   # Avoid oversized markets
COOLDOWN_HOURS = 24          # Avoid recently assigned zipcodes

def select_zipcodes_for_epoch():
    target = TARGET_LISTINGS
    tolerance = target * (TOLERANCE_PERCENT / 100)
    
    # Filter eligible zipcodes:
    # 1. Not assigned in last COOLDOWN_HOURS
    # 2. Expected listings between MIN and MAX
    # 3. Has recent data (updated within 30 days)
    
    # Random weighted selection to hit target ± tolerance
    # Weight by: expected_listings * market_importance_factor
    # market_importance_factor = log(population + property_count)
```

**Miner Performance Requirements:**
- **10K listings in 4 hours** = ~42 listings/minute (achievable with proxies)
- **15K listings in 4 hours** = ~63 listings/minute (aggressive scaling target)
- Miners should handle 3-12 zipcodes per assignment (depends on TARGET_LISTINGS)
- **Proxy Requirements**: Rotating IP pools recommended for 10K+ targets
- **Concurrency**: 5-10 parallel scraping threads per miner optimal

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
- **Epoch Metadata**: Add epoch_id and nonce to S3 upload metadata
- **Submission Timestamps**: S3 upload timestamp determines submission order
- **Validator Read Access**: Validators need read access to all miner S3 folders
- **Validator Write Access**: Validators get S3 write credentials to upload winning data
- **Dual Bucket System**: 
  ```
  # Miner Data Bucket (existing)
  s3://resi-miner-data/miners/{hotkey}/epoch={epoch_id}/zipcode={zipcode}/
  
  # Validator Results Bucket (new)
  s3://resi-validated-data/validators/{hotkey}/epoch={epoch_id}/
  ├── validated_data.parquet          # Top 3 miners' combined winning data
  ├── validation_report.json          # Detailed scoring and audit info
  └── epoch_metadata.json             # Epoch assignments and timestamps
  ```
- **Audit Trail**: Complete history of validation decisions with timestamps

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

4. **Nonce Generation & Anti-Gaming**
   ```python
   # Epoch-specific nonce generation
   nonce = hmac_sha256(
       key=SECRET_KEY,
       message=f"{epoch_id}:{epoch_start_timestamp}:{selected_zipcodes_hash}"
   )
   ```
   - **Purpose**: Prevents miners from pre-scraping popular zipcodes
   - **Validation**: Miners must include nonce in S3 upload metadata
   - **Rotation**: New nonce every epoch (4 hours)
   - **Verification**: Validators check nonce matches epoch assignment

### **Phase 2: Miner Updates (Week 2)**

**Requirements:**
1. **API Client Integration**
   - Add zipcode assignment fetching to miner startup
   - Poll API server every 4 hours for new assignments
   - Handle API failures with exponential backoff

2. **Scraping Modifications**  
   - **Zipcode Focus**: Only scrape assigned zipcodes for current epoch
   - **Metadata Inclusion**: Add epoch_id, nonce, submission_timestamp to S3 uploads
   - **Performance Optimization**: Implement parallel scraping (5-10 threads)
   - **Proxy Management**: Rotate IP addresses to handle higher volumes
   - **Error Handling**: Graceful degradation if some zipcodes fail
   - **Progress Tracking**: Optional status updates to API server

3. **Fallback Mechanism** (Phase 2.5 - Optional)
   - **Primary Failure**: If API server unreachable, query multiple validators
   - **Consensus Logic**: Miners accept assignment if 2+ validators agree
   - **Cache Duration**: Validators cache latest assignments for 6 hours
   - **Retry Logic**: Exponential backoff for API server reconnection
   - **Graceful Degradation**: Continue with cached assignments if needed

### **Phase 3: Validator Updates (Week 2-3)**

**Requirements:**
1. **Validation Logic Replacement**
   - Replace current MinerScorer with competitive evaluation
   - Implement 4-hour offset validation timeline
   - Add configurable spot-check percentage

2. **API Integration & S3 Upload System**
   - **Fetch Assignments**: Get previous epoch assignments for validation
   - **Cache Management**: Cache assignments for miner fallback queries
   - **S3 Upload Access**: Request validator-specific S3 write credentials from API
   - **Winning Data Upload**: Upload top 3 miners' data to validator S3 folder
   - **Validation Reports**: Generate detailed scoring and audit reports
   - **Metadata Tracking**: Include epoch_id, validation_timestamp, validator_hotkey

3. **Scoring Algorithm**
   ```python
   def score_epoch_submissions(epoch_assignments, miner_submissions):
       # Phase 1: Basic validation and ranking
       valid_submissions = []
       for submission in miner_submissions:
           if validate_basic_requirements(submission, epoch_assignments):
               valid_submissions.append(submission)
       
       # Phase 2: Rank by submission timestamp (speed)
       ranked_submissions = sorted(valid_submissions, 
                                 key=lambda x: x.s3_upload_timestamp)
       
       # Phase 3: Deep validation for top performers
       final_scores = {}
       for rank, submission in enumerate(ranked_submissions[:6], 1):
           if rank <= 3:
               # Full validation for top 3 candidates
               score = full_validation_score(submission, rank, epoch_assignments)
           else:
               # Light validation for positions 4-6
               score = basic_validation_score(submission, rank)
           final_scores[submission.miner_hotkey] = score
       
       # Phase 4: Assign participation scores to remaining miners
       participation_score = 0.05 / max(1, len(ranked_submissions) - 6)
       for submission in ranked_submissions[6:]:
           if submission.basic_validation_passed:
               final_scores[submission.miner_hotkey] = participation_score
           else:
               final_scores[submission.miner_hotkey] = 0.0  # Penalty for bad data
       
       return final_scores
   
   def upload_validation_results(final_scores, epoch_assignments, validator_hotkey):
       # Phase 5: Upload winning data and validation results
       top_3_miners = get_top_3_miners(final_scores)
       
       # Combine winning data from top 3 miners
       validated_data = combine_miner_data(top_3_miners, epoch_assignments)
       
       # Create validation report
       validation_report = {
           "epoch_id": epoch_assignments.epoch_id,
           "validation_timestamp": datetime.utcnow().isoformat(),
           "validator_hotkey": validator_hotkey,
           "total_miners_evaluated": len(final_scores),
           "top_3_winners": [
               {
                   "rank": rank,
                   "miner_hotkey": miner.hotkey,
                   "score": final_scores[miner.hotkey],
                   "listings_submitted": miner.listing_count,
                   "zipcodes_completed": miner.zipcode_count,
                   "validation_issues": miner.validation_issues
               }
               for rank, miner in enumerate(top_3_miners, 1)
           ],
           "validation_summary": {
               "total_listings_validated": sum(m.listing_count for m in top_3_miners),
               "spot_checks_performed": get_spot_check_count(),
               "validation_duration_seconds": get_validation_duration(),
               "quality_score_average": get_average_quality_score(top_3_miners)
           }
       }
       
       # Upload to validator S3 folder
       s3_uploader = ValidatorS3Uploader(validator_hotkey, api_server_url)
       s3_uploader.upload_validation_results(
           validated_data, 
           validation_report, 
           epoch_assignments
       )
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

## **Critical Implementation Questions & Solutions**

### **1. Scraping-Based Validation System**
**Approach**: Validators use direct scraping (not APIs) for spot-checking  
**Implementation**:
- **Proxy Rotation**: Each validator uses rotating proxy pools for validation scraping
- **Deterministic Sampling**: All validators check same properties using deterministic seeds
- **Cached Results**: Cache spot-check results for 24 hours to avoid re-scraping
- **Distributed Load**: Each validator checks different miners to distribute scraping load
- **Smart Sampling**: Focus spot-checks on suspicious patterns vs random sampling

### **2. Validator Consensus on API Data**
**Problem**: What if validators get different assignments from API server?  
**Solutions**:
- **Deterministic API**: API server uses deterministic algorithms (same seed = same result)
- **Consensus Mechanism**: Validators vote on "canonical" assignment if differences detected
- **Fallback Protocol**: Use most recent consensus assignment if API inconsistent
- **Health Monitoring**: Alert system if validator assignment consensus < 90%

### **3. Miner Failure Recovery**  
**Problem**: What if miners miss epoch assignments due to downtime?
**Solutions**:
- **No Catch-up**: Missed epochs = zero rewards (encourages uptime)
- **Grace Period**: 15-minute grace period at epoch start for late joiners
- **Partial Credit**: Miners can submit partial zipcode results for reduced rewards
- **Status Tracking**: Optional miner status API to track participation rates

### **4. Geographic Distribution Strategy**
**Problem**: Random selection might cluster in expensive markets  
**Solutions**:
- **Weighted Randomness**: Include geographic diversity factor in selection algorithm
- **Market Tier Balance**: Ensure mix of premium/standard/emerging markets each epoch  
- **Regional Quotas**: Soft limits on zipcodes per state/region per epoch
- **Long-term Tracking**: Monitor coverage over 30-day windows, adjust if needed

### **5. New Implementation Considerations**

#### **A. Validator Coordination**
**Challenge**: Multiple validators validating same epoch simultaneously  
**Solution**: 
```python
# Deterministic validation assignment
validator_assignments = hash(epoch_id + validator_hotkey) % total_validators
assigned_miners = miners[validator_assignments::total_validators]
```

#### **B. S3 Performance at Scale**  
**Challenge**: 100+ miners uploading 10K listings simultaneously  
**Solutions**:
- **Staggered Uploads**: Miners randomize upload timing within epoch
- **Compression**: Use parquet with snappy compression
- **Partitioning**: Upload by zipcode chunks vs single large files
- **Rate Limiting**: S3 upload rate limits per miner

#### **C. Epoch Transition Reliability**
**Challenge**: Ensuring seamless 4-hour epoch transitions  
**Solutions**:
- **Pre-generation**: Generate next epoch assignments 30 minutes early
- **Health Checks**: API server health monitoring with automatic failover
- **Backup Systems**: Secondary API server with synchronized data
- **Monitoring**: Real-time alerts for missed or delayed epoch transitions

#### **D. Validator S3 Upload Management**
**Challenge**: Multiple validators uploading results simultaneously  
**Solutions**:
- **Isolated Folders**: Each validator uploads to their own S3 prefix
- **Credential Management**: Time-limited S3 credentials per validator
- **Upload Verification**: API tracks successful validator uploads
- **Conflict Resolution**: Deterministic file naming prevents overwrites
- **Audit Logging**: All validator uploads logged with timestamps

#### **E. Data Consistency & Audit Trail**
**Challenge**: Ensuring validator consensus on winning data  
**Solutions**:
- **Deterministic Validation**: Same inputs always produce same results
- **Cross-Validation**: Compare validator results for consensus checking
- **Immutable Records**: S3 uploads create permanent audit trail
- **Metadata Integrity**: Cryptographic hashes verify data integrity
- **Historical Analysis**: Track validator agreement rates over time

## **Success Metrics**

- **Speed**: 90% of miners complete assignments within 4 hours
- **Quality**: <5% false positive rate in spot-checking via scraping validation
- **Coverage**: Target listings achieved within ±10% tolerance
- **Participation**: 80%+ of registered miners submit valid data per epoch
- **Consensus**: 95%+ validator agreement on top 3 winners per epoch
- **Reliability**: 99.9% API server uptime with zero missed epoch transitions

---

## **Manual Developer Tasks Checklist**

### **Subnet Owner (You) Tasks**
1. **S3 Infrastructure Setup**
   - [ ] Create new `resi-validated-data` S3 bucket
   - [ ] Configure IAM roles for validator write access
   - [ ] Set up bucket policies and lifecycle rules
   - [ ] Test validator S3 upload permissions

2. **Bittensor Network Configuration**
   - [ ] Update subnet hyperparameters if needed
   - [ ] Verify validator stake thresholds
   - [ ] Test hotkey signature verification
   - [ ] Announce system changes to community

3. **Data Preparation**
   - [ ] Collect and format zipcode listing count data
   - [ ] Create zipcode master database with market tiers
   - [ ] Set initial TARGET_LISTINGS configuration
   - [ ] Prepare geographic distribution data

### **Validator Code Updates**
1. **Core Changes**
   - [ ] Replace MinerScorer with competitive evaluation system
   - [ ] Implement API client for zipcode assignments
   - [ ] Add ValidatorS3Uploader class for results upload
   - [ ] Implement deterministic spot-check sampling

2. **Scraping Validation System**
   - [ ] Set up proxy rotation for validation scraping
   - [ ] Implement scraping-based property verification
   - [ ] Add validation result caching (24 hours)
   - [ ] Configure validation timeout handling

3. **Monitoring Integration**
   - [ ] Add validator consensus tracking metrics
   - [ ] Implement validation performance monitoring
   - [ ] Set up S3 upload success/failure logging
   - [ ] Configure alert thresholds

### **Miner Code Updates**
1. **API Integration**
   - [ ] Add zipcode assignment API client
   - [ ] Implement 4-hour polling for new assignments
   - [ ] Add epoch metadata to S3 uploads
   - [ ] Handle API server failures gracefully

2. **Performance Optimization**
   - [ ] Implement parallel scraping (5-10 threads)
   - [ ] Add proxy rotation for high-volume scraping
   - [ ] Optimize for early upload (3:30-3:45 target)
   - [ ] Add progress tracking and status reporting

### **Testing & Deployment**
1. **Testnet Phase**
   - [ ] Deploy API server on testnet environment
   - [ ] Test with 3 validators, 5 miners
   - [ ] Verify epoch transitions work correctly
   - [ ] Validate consensus mechanisms

2. **Mainnet Deployment**
   - [ ] Deploy production API server
   - [ ] Push validator/miner code updates
   - [ ] Monitor first few epochs closely
   - [ ] Adjust TARGET_LISTINGS based on performance

3. **Post-Launch Monitoring**
   - [ ] Track miner participation rates
   - [ ] Monitor validator agreement percentages
   - [ ] Analyze data quality improvements
   - [ ] Optimize based on performance metrics