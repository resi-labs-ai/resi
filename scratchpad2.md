# Multi-Miner Network Evaluation Plan - Day 2

## Executive Summary

**Yesterday's Success**: ✅ Single validator-miner communication working perfectly
**Today's Goal**: Scale to multiple miners and validators for full network simulation

## 🔧 **Key System Understanding**

### Current Validator Frequency
- **MIN_EVALUATION_PERIOD**: 60 minutes (each miner evaluated once per hour)
- **Evaluation Batches**: 15 miners evaluated simultaneously in parallel threads
- **Validator Cycle**: Main loop runs every 60 seconds, but only evaluates miners due for update

### Data Validation Coverage
- **S3 Validation Sampling**: 10 entities per miner per evaluation cycle
- **API Verification**: Uses RapidAPI/Zillow to validate sampled data (3 samples per file, 20 rows per file)
- **Duplicate Detection**: Zero tolerance - any duplicates = validation failure
- **Scraper Success Rate**: Minimum 60% success rate required to pass validation

---

## 🎯 **Objectives for Tomorrow**

### Primary Goals
1. **Multi-Miner Setup**: Run 3-5 miners simultaneously with different configurations
2. **Accelerated Validation**: Increase validator evaluation frequency for testing (5-10 minutes vs 60 minutes)
3. **Network Dynamics**: Observe scoring, ranking, and reward distribution
4. **Geographic Coverage Incentives**: Ensure miners are rewarded for comprehensive US zipcode coverage
5. **API Validation Coverage**: Verify validators are properly sampling and validating against Zillow API

### Updated Understanding - Incentive Mechanisms
- **Volume Rewards**: Miners rewarded for quantity of unique, verifiable listings
- **Geographic Diversity**: Premium zipcodes (weight 4.0), Tier 1-4 coverage incentives
- **Quality Assurance**: Zero tolerance for duplicates, 60% API validation success rate required
- **Uniqueness Bonus**: Data stored by fewer miners is more valuable (credibility scaling)

### Success Metrics
- ✅ All miners responding to validator requests
- ✅ Multiple validators producing consistent evaluations
- ✅ Proper score distribution based on data quality/quantity
- ✅ No network congestion or bottlenecks
- ✅ Geographic coverage across different US regions

---

## 🚀 **Multi-Miner Setup Strategy**

### Miner Configuration Matrix

| Miner ID | Wallet | Hotkey | Zipcode Strategy | Expected Performance |
|----------|--------|--------|------------------|---------------------|
| **Miner 1** | `testnet_miner_1` | `hotkey_1` | **Premium Focus** (77494, 08701, 77449) | High rewards |
| **Miner 2** | `testnet_miner_2` | `hotkey_2` | **East Coast** (NY, NJ, FL markets) | Medium-high rewards |
| **Miner 3** | `testnet_miner_3` | `hotkey_3` | **West Coast** (CA, WA, OR markets) | Medium-high rewards |
| **Miner 4** | `testnet_miner_4` | `hotkey_4` | **Central US** (TX, IL, CO markets) | Medium rewards |
| **Miner 5** | `testnet_miner_5` | `hotkey_5` | **Rural/Diverse** (Mixed tier coverage) | Variable rewards |

### Geographic Territory Assignment

**Premium Zipcodes (Weight 4.0)**: 77494, 08701, 77449, 77084, 79936, 11385, 78660, 11208, 90011, 77433

**Miner 1 - Premium Focus**:
- Target: 77494 (Katy, TX), 08701 (Lakewood, NJ), 77449 (Katy, TX)
- Strategy: Maximum reward concentration
- Expected: Highest individual scores

**Miner 2 - East Coast**:
- Target: 10001 (NYC), 07086 (Weehawken, NJ), 33101 (Miami Beach, FL)
- Strategy: High-density metro coverage
- Expected: Consistent medium-high scores

**Miner 3 - West Coast**:
- Target: 90210 (Beverly Hills, CA), 98101 (Seattle, WA), 97201 (Portland, OR)
- Strategy: Tech hub coverage
- Expected: Consistent medium-high scores

**Miner 4 - Central US**:
- Target: 60601 (Chicago, IL), 75201 (Dallas, TX), 80202 (Denver, CO)
- Strategy: Major central markets
- Expected: Steady medium scores

**Miner 5 - Rural/Diverse**:
- Target: Mixed rural and suburban (50+ different zipcodes)
- Strategy: Volume and diversity
- Expected: Variable but consistent volume rewards

---

## 🔧 **Implementation Plan**

### Phase 1: Wallet & Hotkey Setup (30 minutes)

#### Step 1.1: Create Miner Wallets
- [ ] Create 4 additional miner wallets (you already have 1)
```bash
for i in {2..5}; do
    btcli wallet new_coldkey --wallet.name "testnet_miner_$i" --no-prompt
    btcli wallet new_hotkey --wallet.name "testnet_miner_$i" --wallet.hotkey "hotkey_$i" --no-prompt
done
```

#### Step 1.2: Fund Wallets
- [ ] Get testnet TAO for each wallet (via Discord faucet or transfer)
```bash
for i in {2..5}; do
    echo "Fund testnet_miner_$i via Discord faucet or transfer"
    # btcli wallet transfer --amount 5.0 --dest testnet_miner_$i
done
```

#### Step 1.3: Register Miners
- [ ] Register all miners on testnet 428
```bash
for i in {2..5}; do
    btcli subnet register --netuid 428 --subtensor.network test \
        --wallet.name "testnet_miner_$i" \
        --wallet.hotkey "hotkey_$i" \
        --no-prompt
done
```

### Phase 2: Miner Configuration (45 minutes)

#### Step 2.1: Create Configuration Files
- [ ] Create separate .env files for each miner
```bash
for i in {2..5}; do
    cp .env ".env_miner_$i"
    # Edit each file with specific wallet names and zipcode strategies
done
```

#### Step 2.2: Zipcode Strategy Configuration
- [ ] Create custom scraping configurations for each miner:

```bash
# Miner 1 - Premium Focus
cat > config/premium_zipcodes.json << EOF
{
    "target_zipcodes": ["77494", "08701", "77449", "77084", "79936"],
    "strategy": "premium_focus",
    "scrape_frequency": 300
}
EOF

# Miner 2 - East Coast
cat > config/east_coast_zipcodes.json << EOF
{
    "target_zipcodes": ["10001", "07086", "33101", "02101", "19101"],
    "strategy": "east_coast_metro",
    "scrape_frequency": 360
}
EOF

# Similar files for miners 3, 4, 5...
```

#### Step 2.3: Launch Miners
- [ ] Launch all miners in separate terminals/tmux sessions
```bash
for i in {1..5}; do
    tmux new-session -d -s "miner_$i" \
        "source venv/bin/activate && \
         python neurons/miner.py \
         --netuid 428 \
         --subtensor.network test \
         --wallet.name testnet_miner_$i \
         --wallet.hotkey hotkey_$i \
         --use_uploader \
         --logging.debug \
         --config config/miner_${i}_zipcodes.json"
done
```

### Phase 3: Validator Setup (20 minutes)

#### Step 3.1: Accelerated Validator Configuration
**Primary Goal**: Increase evaluation frequency for comprehensive testing

**Option A: Modified Evaluation Period (Recommended)**
- [ ] Temporarily reduce MIN_EVALUATION_PERIOD for testing
- [ ] Launch validator with accelerated evaluation cycles
```bash
# Edit common/constants.py:
# MIN_EVALUATION_PERIOD = dt.timedelta(minutes=5)  # Instead of 60 minutes

# Or set via environment variable:
export MINER_EVAL_PERIOD_MINUTES=5

python neurons/validator.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name 428_testnet_validator \
    --wallet.hotkey 428_testnet_validator_hotkey \
    --logging.debug \
    --max_targets 10
```

**Option B: Multiple Validators (Advanced)**
- [ ] Create 2-3 additional validator wallets
- [ ] Stake each with sufficient TAO (>300 ඥ equivalent) 
- [ ] Compare evaluation consistency and API validation coverage
- [ ] Ensure each validator samples different data portions

#### Step 3.2: API Validation Monitoring
- [ ] Set up API validation monitoring
```bash
# Monitor API validation coverage
tail -f validator.log | grep -E "(scraper.*validation|API.*success|duplicate.*percentage)"

# Track Zillow API usage
grep -c "RapidAPI" validator.log
grep "validation.*percentage" validator.log | tail -20
```

### Phase 4: Monitoring & Analysis (Ongoing)

#### Step 4.1: Real-time Monitoring Setup
- [ ] Set up multi-miner log monitoring
- [ ] Set up validator evaluation monitoring
```bash
# Monitor all miner logs
tmux new-session -d -s "monitoring" \
    "multitail -i miner_1.log -i miner_2.log -i miner_3.log -i miner_4.log -i miner_5.log"

# Monitor validator evaluation results
tail -f validator.log | grep -E "(Evaluated Miner|Score=|Credibility=)"
```

#### Step 4.2: Performance Metrics Collection
- [ ] Create and run network monitoring script
```bash
# Create monitoring script
cat > monitor_network.sh << 'EOF'
#!/bin/bash
while true; do
    echo "=== $(date) ==="
    echo "Metagraph Status:"
    btcli subnet metagraph --netuid 428 --subtensor.network test | head -20
    
    echo "Miner Response Status:"
    for i in {1..5}; do
        echo "Miner $i: $(tail -1 miner_${i}.log | grep -o "SUCCESS\|ERROR\|Got to a")"
    done
    
    echo "Validator Evaluation Count:"
    grep -c "Evaluated Miner" validator.log
    
    sleep 300  # Every 5 minutes
done
EOF

chmod +x monitor_network.sh
./monitor_network.sh &
```

---

## 📊 **Analysis Framework**

### Key Metrics to Track

#### 1. Network Health
- **Miner Response Rate**: % of miners responding to validator requests
- **Evaluation Frequency**: Target 5-10 minute cycles vs default 60 minutes
- **API Validation Coverage**: % of data validated against Zillow API
- **S3 Upload Success**: Data persistence rate

#### 2. Geographic Coverage Incentives
- **Zipcode Distribution**: Ensure miners target all US zipcodes (7,572+)
- **Premium Zipcode Performance**: Miners targeting weight 4.0 zipcodes should score highest
- **Volume vs Quality Balance**: More unique listings = higher scores, but must pass 60% API validation
- **Duplicate Penalty**: Zero tolerance enforcement working correctly

#### 3. API Validation Effectiveness
- **Sampling Rate**: 10 entities per miner per cycle, 3 samples per file, 20 rows per file
- **RapidAPI Usage**: Track API calls to ensure proper external validation
- **Success Rate Distribution**: Monitor which miners consistently pass 60% threshold
- **Validation Coverage**: Ensure all geographic regions get API validation

#### 4. Network Dynamics
- **Evaluation Frequency**: How often each miner gets evaluated (target: 5-10 minutes)
- **Load Balancing**: Even distribution of validator attention across all zipcodes
- **Convergence Time**: How quickly scores reflect geographic coverage strategies
- **Resource Usage**: CPU/memory/bandwidth consumption under accelerated evaluation

### Expected Results

#### Scenario 1: Perfect Geographic Coverage Network
- ✅ All 5 miners respond consistently to 5-10 minute evaluation cycles
- ✅ Premium-focused miner (Miner 1) has highest scores due to weight 4.0 zipcodes
- ✅ Geographic diversity creates balanced competition across all US regions
- ✅ API validation consistently samples 10+ entities per miner per cycle
- ✅ All miners pass 60% API validation threshold with unique, verified data

#### Scenario 2: Realistic Coverage Network  
- ⚠️ 1-2 miners may have intermittent API validation failures
- ⚠️ Some zipcodes may have lower listing volumes affecting scores
- ⚠️ Accelerated evaluation (5-10 min) may cause higher resource usage
- ✅ Overall system incentivizes comprehensive zipcode coverage
- ✅ Duplicate detection prevents gaming/cheating

#### Scenario 3: Comprehensive Coverage Analysis
- 🔍 Identify which zipcodes are under-covered by current miners
- 🔍 Measure API validation effectiveness across different geographic regions
- 🔍 Understand optimal balance between evaluation frequency and resource usage
- 🔍 Validate that volume rewards properly incentivize comprehensive coverage
- 🔍 Confirm uniqueness bonuses work correctly for diverse geographic strategies

---

## 🚨 **Potential Issues & Solutions**

### Issue 1: Miner Registration Conflicts
**Problem**: Multiple registrations may hit rate limits or slippage
**Solution**: Stagger registrations, use --unsafe flag, request admin help

### Issue 2: S3 Storage Conflicts  
**Problem**: Multiple miners uploading to same buckets
**Solution**: Ensure proper hotkey-based S3 partitioning

### Issue 3: Accelerated Evaluation Overload
**Problem**: 5-10 minute cycles may overwhelm validator or API limits
**Solution**: Monitor evaluation times, adjust frequency if needed, track RapidAPI usage

### Issue 4: Geographic Coverage Gaps
**Problem**: Miners may focus only on premium zipcodes, ignoring comprehensive coverage
**Solution**: Monitor zipcode distribution, ensure volume rewards incentivize breadth

### Issue 5: API Validation Bottlenecks  
**Problem**: Increased evaluation frequency may hit RapidAPI rate limits
**Solution**: Monitor API usage, implement intelligent sampling, consider multiple API keys

### Issue 6: Duplicate Data Gaming
**Problem**: Miners may try to game system with slight variations of same data
**Solution**: Verify zero-tolerance duplicate detection works, monitor validation logs

### Issue 7: Resource Constraints
**Problem**: Running 5+ processes with accelerated evaluation simultaneously
**Solution**: Monitor system resources, use tmux/screen, consider distributed testing

---

## 🎯 **Success Criteria for Tomorrow**

### Minimum Viable Success
- ✅ 3+ miners running and responding to accelerated validator cycles (5-10 min)
- ✅ Validator completing evaluation cycles with API validation
- ✅ Clear score differentiation based on geographic coverage strategies
- ✅ API validation sampling working (10 entities per miner per cycle)
- ✅ No major network errors or crashes

### Optimal Success  
- ✅ 5 miners with distinct geographic strategies covering different US regions
- ✅ Consistent 5-10 minute evaluation cycles (vs default 60 minutes)
- ✅ Premium zipcode miner showing highest rewards (weight 4.0 advantage)
- ✅ Rural/diverse miner demonstrating volume reward benefits
- ✅ API validation consistently verifying data against Zillow (60%+ success rates)
- ✅ Zero duplicate tolerance enforcement working correctly
- ✅ Comprehensive zipcode coverage incentives functioning

### Stretch Goals
- ✅ Multiple validators producing consistent scores and API validation
- ✅ Real-time geographic coverage monitoring dashboard
- ✅ API validation coverage heat map showing sampling distribution
- ✅ Automated zipcode coverage analysis and gap identification
- ✅ RapidAPI usage optimization and rate limit management

---

## 📋 **Tomorrow's Schedule**

### Morning (9 AM - 12 PM)
- [ ] **9:00-9:15**: Modify `MIN_EVALUATION_PERIOD` to 5 minutes for accelerated testing
- [ ] **9:15-9:45**: Create additional wallets and hotkeys for geographic strategy miners
- [ ] **9:45-10:30**: Register all miners on testnet 428 (stagger to avoid rate limits)
- [ ] **10:30-11:15**: Configure distinct zipcode strategies for each miner
- [ ] **11:15-11:30**: Launch all miners with geographic territory assignments
- [ ] **11:30-12:00**: Start validator with accelerated evaluation cycles and API validation

### Afternoon (12 PM - 5 PM)  
- [ ] **12:00-12:30**: Verify all miner-validator connections and API validation sampling
- [ ] **12:30-1:30**: Monitor first accelerated evaluation cycles (5-10 minutes each)
- [ ] **1:30-2:30**: Analyze geographic coverage distribution and API validation rates
- [ ] **2:30-3:30**: Track premium zipcode performance vs volume-based strategies
- [ ] **3:30-4:30**: Monitor RapidAPI usage and duplicate detection effectiveness
- [ ] **4:30-5:00**: Optimize configurations based on coverage gaps and API validation results

### Evening (5 PM - 7 PM)
- [ ] **5:00-6:00**: Run comprehensive coverage analysis across all US regions
- [ ] **6:00-6:30**: Generate zipcode coverage heat map and API validation report
- [ ] **6:30-7:00**: Document geographic incentive effectiveness and scaling recommendations

### Key Monitoring Throughout Day
- [ ] **API Validation Coverage**: Track 10 entities per miner per 5-10 minute cycle
- [ ] **Geographic Distribution**: Ensure miners cover premium, tier 1-4, and rural zipcodes
- [ ] **Duplicate Detection**: Verify zero-tolerance enforcement prevents gaming
- [ ] **RapidAPI Usage**: Monitor rate limits and validation success rates (target 60%+)

---

**CONCLUSION**: Tomorrow's accelerated multi-miner evaluation will validate that your subnet properly incentivizes comprehensive US zipcode coverage through:

1. **Geographic Strategy Differentiation**: Premium vs volume-based vs regional approaches
2. **API Validation Effectiveness**: 10 entities per miner per 5-10 minute cycle with 60%+ success rates  
3. **Comprehensive Coverage Incentives**: Ensuring miners are rewarded for mining ALL zipcodes
4. **Quality Assurance**: Zero-tolerance duplicate detection and external API verification
5. **Scalable Network Dynamics**: Proving the system can handle multiple miners with accelerated evaluation

This will demonstrate that your incentive mechanisms successfully drive miners to provide comprehensive, unique, and verifiable real estate data across all US geographic regions.
