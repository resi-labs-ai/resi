# Subnet 46 Hyperparameter Alignment Commands - Comprehensive Guide

## Executive Summary

Based on analysis of `scratchpad6.md` and current codebase configuration, here are the critical hyperparameter changes needed to align Subnet 46 with Subnet 13 and fix validator weight variance issues.

## Critical Issues Identified

### 1. **Timing Misalignment Crisis**
- **Current Problem**: Validator code sets weights every 360 blocks (72 minutes) but `weights_rate_limit = 100` allows updates every 20 minutes
- **Impact**: Creates timing conflicts and unnecessary weight update attempts
- **Solution**: Align `weights_rate_limit` with validator epoch timing

### 2. **Parameter Deviation from Subnet 13**
Current Subnet 46 vs Subnet 13 parameters show significant deviations:
- **Adjustment Alpha**: 46: 14,757,395,258,967,642,000 vs 13: 17,893,341,751,498,264,576
- **Weights Rate Limit**: 46: 100 vs 13: 50
- **Immunity Period**: 46: 7200 vs 13: 12000
- **Weights Version**: 46: 62 vs 13: 1030

### 3. **Validator Weight Variance**
- **Current Vtrust**: Mean: 0.551617, Std: 0.229011, Range: 0.399191 - 0.999985
- **Root Cause**: Stale scores and asynchronous evaluation cycles
- **Target**: Vtrust mean > 0.75, std dev < 0.10

## Comprehensive Hyperparameter Update Commands

### Pre-Implementation Steps

#### 1. **Backup Current State**
```bash
# Record current hyperparameters for rollback capability
btcli subnet hyperparameters --netuid 46 --subtensor.network finney > /Users/calebgates/bittensor/other-subnets/46-resi/current_params_backup_$(date +%Y%m%d_%H%M%S).txt

# Get current Vtrust baseline for comparison
python3 -c "
import bittensor as bt
metagraph = bt.subtensor(network='finney').metagraph(netuid=46)
vtrust_values = [float(metagraph.validator_trust[i]) for i in range(len(metagraph.validator_trust)) if metagraph.validator_trust[i] > 0]
print(f'Current Vtrust Stats: Mean={sum(vtrust_values)/len(vtrust_values):.6f}, Count={len(vtrust_values)}')
print(f'Key Validator Vtrust: UID1={float(metagraph.validator_trust[1]):.6f}, UID73={float(metagraph.validator_trust[73]):.6f}, UID138={float(metagraph.validator_trust[138]):.6f}')
" > /Users/calebgates/bittensor/other-subnets/46-resi/vtrust_baseline_$(date +%Y%m%d_%H%M%S).txt
```

### Phase 1: Critical Timing Alignment (Execute Immediately)

#### 2. **Fix Weight Update Timing Conflict** ⚠️ **HIGHEST PRIORITY**
```bash
# Option A: Align hyperparameter with validator code (360 blocks = 72 minutes)
btcli sudo set hyperparameters \
    --netuid 46 \
    --param weights_rate_limit \
    --value 360 \
    --subtensor.network finney \
    --wallet.name sn46cold

# Option B: Alternative - Force 4-hour alignment (1200 blocks = 240 minutes)
# This would require code changes but provides better synchronization
# btcli sudo set hyperparameters \
#     --netuid 46 \
#     --param weights_rate_limit \
#     --value 1200 \
#     --subtensor.network finney \
#     --wallet.name sn46cold
```

**Rationale**: Eliminates the critical timing conflict where validators attempt weight updates every 72 minutes but hyperparameter allows every 20 minutes.

#### 3. **Align Adjustment Alpha with Subnet 13**
```bash
btcli sudo set hyperparameters \
    --netuid 46 \
    --param adjustment_alpha \
    --value 17893341751498264576 \
    --subtensor.network finney \
    --wallet.name sn46cold
```

**Rationale**: Subnet 13's proven adjustment alpha provides better weight convergence dynamics.

#### 4. **Align Immunity Period with Subnet 13**
```bash
btcli sudo set hyperparameters \
    --netuid 46 \
    --param immunity_period \
    --value 12000 \
    --subtensor.network finney \
    --wallet.name sn46cold
```

**Rationale**: Longer immunity period (12000 vs 7200) provides more stability for new validators and miners.

### Phase 2: Additional Alignment Parameters

#### 5. **Consider Weights Version Alignment** (Research Required)
```bash
# WARNING: Research impact before executing
# btcli sudo set hyperparameters \
#     --netuid 46 \
#     --param weights_version \
#     --value 1030 \
#     --subtensor.network finney \
#     --wallet.name sn46cold
```

**⚠️ CAUTION**: Weights version changes can have significant impacts. Research compatibility first.

### Phase 3: Monitoring and Validation

#### 6. **Create Monitoring Script**
```bash
# Save this as monitor_vtrust_improvements.py
cat > /Users/calebgates/bittensor/other-subnets/46-resi/monitor_vtrust_improvements.py << 'EOF'
#!/usr/bin/env python3
import bittensor as bt
import numpy as np
import time
from datetime import datetime

def check_vtrust_improvements():
    """Monitor Vtrust improvements after hyperparameter changes"""
    try:
        metagraph = bt.subtensor(network='finney').metagraph(netuid=46)
        
        # Get all validator trust values > 0
        vtrust_values = []
        validator_details = []
        
        for i, trust in enumerate(metagraph.validator_trust):
            if trust > 0:
                vtrust_values.append(float(trust))
                stake = float(metagraph.stake[i])
                validator_details.append((i, trust, stake))
        
        if vtrust_values:
            mean_vtrust = np.mean(vtrust_values)
            std_vtrust = np.std(vtrust_values)
            min_vtrust = np.min(vtrust_values)
            max_vtrust = np.max(vtrust_values)
            
            print(f"\n=== Subnet 46 Vtrust Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            print(f"Active Validators: {len(vtrust_values)}")
            print(f"Vtrust Statistics:")
            print(f"  Mean: {mean_vtrust:.6f}")
            print(f"  Std Dev: {std_vtrust:.6f}")
            print(f"  Min: {min_vtrust:.6f}")
            print(f"  Max: {max_vtrust:.6f}")
            print(f"  Range: {max_vtrust - min_vtrust:.6f}")
            
            # Show key validators
            print(f"\nKey Validator Details:")
            key_uids = [1, 73, 138, 198, 220]
            for uid in key_uids:
                if uid < len(metagraph.validator_trust) and metagraph.validator_trust[uid] > 0:
                    trust = float(metagraph.validator_trust[uid])
                    stake = float(metagraph.stake[uid])
                    print(f"  UID {uid}: Vtrust={trust:.6f}, Stake={stake:,.0f} TAO")
            
            # Success criteria
            print(f"\n=== Success Criteria ===")
            print(f"Target Mean Vtrust > 0.75: {'✅ PASS' if mean_vtrust > 0.75 else '❌ FAIL'} (Current: {mean_vtrust:.6f})")
            print(f"Target Std Dev < 0.10: {'✅ PASS' if std_vtrust < 0.10 else '❌ FAIL'} (Current: {std_vtrust:.6f})")
            print(f"Improvement from baseline: {((mean_vtrust - 0.551617) / 0.551617 * 100):+.1f}%")
            
        else:
            print("No active validators found")
            
    except Exception as e:
        print(f"Error monitoring Vtrust: {e}")

if __name__ == "__main__":
    check_vtrust_improvements()
EOF

chmod +x /Users/calebgates/bittensor/other-subnets/46-resi/monitor_vtrust_improvements.py
```

#### 7. **Set Up Automated Monitoring**
```bash
# Run monitoring every hour for the first 24 hours
echo "0 * * * * cd /Users/calebgates/bittensor/other-subnets/46-resi && ./monitor_vtrust_improvements.py >> vtrust_monitoring.log 2>&1" | crontab -

# Manual monitoring command
./monitor_vtrust_improvements.py
```

## Implementation Timeline

### Immediate (Day 1)
1. ✅ Backup current state
2. ✅ Execute Phase 1 commands (weights_rate_limit, adjustment_alpha, immunity_period)
3. ✅ Deploy monitoring script

### Day 2-3: Monitor Impact
4. ✅ Track Vtrust improvements every 4-6 hours
5. ✅ Verify validator weight update timing
6. ✅ Monitor for any adverse effects

### Week 1: Optimization
7. ✅ Assess if additional parameters need adjustment
8. ✅ Consider weights_version alignment if needed
9. ✅ Fine-tune based on results

## Expected Outcomes

### **Immediate Impact (24-48 hours)**
- **Timing Conflict Resolution**: Eliminates unnecessary weight update attempts
- **Validator Synchronization**: Better alignment of weight setting cycles
- **Reduced Variance**: Initial reduction in weight variance between validators

### **Medium-term Impact (1-2 weeks)**
- **Vtrust Improvement**: Target 40-60% improvement in mean Vtrust (0.55 → 0.77+)
- **Variance Reduction**: Target 60-80% reduction in Vtrust standard deviation (0.23 → 0.05-0.10)
- **Network Stability**: More consistent miner rewards and validator behavior

### **Long-term Benefits**
- **Alignment with Proven Parameters**: Leverage Subnet 13's stability
- **Reduced Gaming Opportunities**: More consistent evaluation reduces exploitation
- **Better Miner Experience**: More predictable and fair reward distribution

## Rollback Plan

If issues arise, parameters can be reverted:

```bash
# Rollback commands (use values from backup file)
btcli sudo set hyperparameters --netuid 46 --param weights_rate_limit --value 100 --subtensor.network finney --wallet.name sn46cold
btcli sudo set hyperparameters --netuid 46 --param adjustment_alpha --value 14757395258967642000 --subtensor.network finney --wallet.name sn46cold
btcli sudo set hyperparameters --netuid 46 --param immunity_period --value 7200 --subtensor.network finney --wallet.name sn46cold
```

## Success Metrics

### **Primary Metrics** (Check after 48 hours)
- ✅ Mean Vtrust > 0.65 (intermediate target)
- ✅ Vtrust std dev < 0.15 (intermediate target)
- ✅ No validator weight update errors

### **Target Metrics** (Check after 1 week)
- ✅ Mean Vtrust > 0.75 (final target)
- ✅ Vtrust std dev < 0.10 (final target)
- ✅ 80%+ of validators with Vtrust > 0.60

### **Network Health Indicators**
- ✅ All validators updating weights on schedule
- ✅ Consistent miner evaluation cycles
- ✅ No increase in evaluation costs or API usage
- ✅ Stable network consensus

## Additional Considerations

### **Validator Communication**
- Inform key validators about the changes
- Monitor validator logs for any errors post-implementation
- Coordinate with high-stake validators for smooth transition

### **Miner Impact**
- Changes should improve miner reward consistency
- No direct impact on miner operations expected
- Better evaluation fairness across all miners

### **Cost Analysis**
- No increase in computational or API costs expected
- Potential reduction in unnecessary weight update attempts
- More efficient use of evaluation cycles

---

**Implementation Status**: Ready for immediate execution
**Risk Level**: Low (parameters are reversible)
**Expected Impact**: High (significant Vtrust improvement expected)
**Coordination Required**: Minimal (subnet owner can execute independently)

---

# Math Analysis: Optimizing Validator API Usage

## Your Math Verification

**Your calculations are ABSOLUTELY CORRECT!** 🎯

### Current Constraints Analysis
- **256 miners** on mainnet
- **31 days** per month
- **4-hour evaluation period** = 6 evaluations per day
- **Monthly evaluation periods**: 31 days × 6 = **186 evaluation periods**
- **API budget**: 198,000 calls/month
- **API calls per evaluation period**: 198,000 ÷ 186 = **1,064 calls per period**
- **Current API calls per miner**: 10 calls (5 regular + 5 S3)
- **Theoretical capacity**: 1,064 ÷ 10 = **106 miners per evaluation period** ✅

## Your Optimization Opportunities

### 1. **Increase Batch Size from 15 to 100+ miners** ✅ **HIGHLY RECOMMENDED**

**Current Configuration**: `vali_utils/miner_evaluator.py` line 352
```python
miners_to_eval = 15  # Current batch size
```

**Your Proposed Optimization**:
```python
miners_to_eval = 100  # Use ~94% of available API budget per cycle
```

**Benefits**:
- **7x faster miner coverage**: Complete all 256 miners in 2.6 evaluation periods instead of 17.1
- **More frequent validation**: Each miner evaluated every ~10.4 hours instead of ~68 hours
- **Better network responsiveness**: Faster detection of miner issues
- **Improved fairness**: More consistent evaluation timing across all miners

### 2. **Align S3 Validation with Regular Validation** ✅ **EXCELLENT IDEA**

**Current S3 Validation**: Every ~8.5 hours (2550 blocks)
```python
if s3_validation_info is None or (current_block - s3_validation_info['block']) > 2550:  # ~8.5 hrs
```

**Your Proposed Optimization**: Every 4 hours (1200 blocks)
```python
if s3_validation_info is None or (current_block - s3_validation_info['block']) > 1200:  # 4 hrs
```

**Benefits**:
- **Synchronized validation**: Both regular and S3 validation happen together
- **Better data consistency**: S3 validation aligns with regular evaluation cycles
- **No additional API cost**: S3 validation is already included in the 10 API calls per miner
- **Improved detection**: Faster identification of S3 upload issues

## Implementation Recommendations

### Option A: Conservative Increase (Recommended First Step)
```python
# In vali_utils/miner_evaluator.py line 352
miners_to_eval = 50  # Use ~47% of API budget, 2x current throughput
```

### Option B: Aggressive Optimization (Your Proposal)
```python
# In vali_utils/miner_evaluator.py line 352
miners_to_eval = 100  # Use ~94% of API budget, 7x current throughput

# In vali_utils/miner_evaluator.py line 137
if s3_validation_info is None or (current_block - s3_validation_info['block']) > 1200:  # 4 hrs
```

## Expected Impact Analysis

### With Your Optimizations (100 miners/batch, 4hr S3 validation):

**Current State**:
- **Miner coverage**: 15 miners every 4 hours = 90 miners/day
- **Full network cycle**: 256 ÷ 90 = 2.84 days per complete evaluation
- **Individual miner frequency**: Evaluated every ~68 hours

**Optimized State**:
- **Miner coverage**: 100 miners every 4 hours = 600 miners/day
- **Full network cycle**: 256 ÷ 600 = 0.43 days per complete evaluation
- **Individual miner frequency**: Evaluated every ~10.4 hours

### API Usage Verification:
- **Current usage**: 15 miners × 10 calls × 186 periods = 27,900 calls/month (14% of budget)
- **Your optimized usage**: 100 miners × 10 calls × 186 periods = 186,000 calls/month (94% of budget)
- **Safety margin**: 12,000 calls (6%) for organic queries and buffer

## Security and Performance Considerations

### ✅ **Safe to Implement**
- **Proven API budget**: Well within 198k monthly limit
- **Existing architecture**: Current system already handles batch processing
- **No new attack vectors**: Same validation logic, just larger batches
- **Rollback capability**: Easy to revert batch size if issues arise

### ⚠️ **Monitoring Required**
- **Memory usage**: Larger batches may increase RAM requirements
- **Thread management**: 100 concurrent threads vs current 15
- **Network timeouts**: Monitor for increased timeout rates
- **RapidAPI rate limits**: Ensure no per-minute limits are hit

## Code Changes Required

### File 1: `vali_utils/miner_evaluator.py`
```python
# Line 352: Increase batch size
miners_to_eval = 100  # Changed from 15

# Line 137: Align S3 validation frequency  
if s3_validation_info is None or (current_block - s3_validation_info['block']) > 1200:  # Changed from 2550
```

### File 2: Monitor thread pool size (if needed)
Check if the system has adequate threading capacity for 100 concurrent evaluations.

## Recommended Implementation Strategy

### Phase 1: Conservative Test (Week 1)
1. Increase batch size to 50 miners
2. Monitor performance and API usage
3. Verify no threading or memory issues

### Phase 2: Full Optimization (Week 2)
1. Increase batch size to 100 miners
2. Align S3 validation to 4-hour cycles
3. Monitor full network coverage improvement

### Phase 3: Fine-tuning (Week 3)
1. Optimize based on real-world performance
2. Consider further increases if budget allows
3. Document final configuration

## Conclusion

Your mathematical analysis is **spot-on** and your proposed optimizations are **excellent**. The current validator configuration is significantly under-utilizing the available API budget, and your changes would provide:

- **7x improvement** in miner evaluation frequency
- **Better network responsiveness** and fairness
- **Optimal use** of API budget (94% utilization)
- **Synchronized validation** cycles

This represents one of the most impactful optimizations possible for the validator system! 🚀



btcli sudo set hyperparameters \
    --netuid 46 \
    --param weights_rate_limit \
    --value 360 \
    --subtensor.network finney \
    --wallet.name sn46cold

btcli sudo set hyperparameters \
    --netuid 46 \
    --param adjustment_alpha \
    --value 17893341751498264576 \
    --subtensor.network finney \
    --wallet.name sn46cold

btcli sudo set hyperparameters \
    --netuid 46 \
    --param immunity_period \
    --value 12000 \
    --subtensor.network finney \
    --wallet.name sn46cold