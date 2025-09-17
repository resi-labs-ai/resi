# Subnet 46 Validator Vtrust Fix - Immediate Action Plan

## Quick Answers to Your Questions:

### 1. **Subnet Owner Parameter Changes**: 
✅ **YES** - As subnet owner with the cold key, you can directly set hyperparameters using:
```bash
btcli sudo set hyperparameters --netuid 46 --param PARAMETER_NAME --value VALUE
```

### 2. **weights_rate_limit (100 → 360)**:
- **Current (100)**: Validators must wait 100 blocks (~20 minutes) between weight updates
- **Validator Code**: Actually tries to set weights every 360 blocks (72 minutes/epoch)
- **Problem**: Code wants 72 min, but hyperparameter allows 20 min = potential conflicts
- **New (360)**: Align hyperparameter with validator code timing
- **Effect**: Eliminates timing conflicts, reduces unnecessary weight update attempts

### 3. **Production Rollout**: 
- Skip testnet, implement directly on mainnet
- Monitor using existing validator metrics and metagraph queries
- Changes are reversible if needed

### 4. **Monitoring Impact**:
- Track Vtrust values before/after changes
- Monitor weight variance between validators  
- Watch for validator weight update frequency

---

## ⚠️ CRITICAL TIMING CLARIFICATION

**You're getting conflicting advice because there are TWO different timing systems:**

### 1. **Validator Code Timing** (What validators actually do):
- **Weight Setting**: Every 360 blocks (72 minutes) - in `neurons/validator.py`
- **Miner Evaluation**: Every 240 minutes (4 hours) - in `common/constants.py`
- **Logic**: Validators only set weights when they reach epoch boundaries (360 blocks)

### 2. **Subnet Hyperparameter Timing** (Network-level limits):
- **weights_rate_limit**: Currently 100 blocks (20 minutes) - the MINIMUM time between weight updates
- **tempo**: 360 blocks (72 minutes) - defines network epochs

### 🔥 **THE PROBLEM**:
- Validator code tries to set weights every 72 minutes (360 blocks)
- But hyperparameter allows weight updates every 20 minutes (100 blocks)  
- This creates **timing conflicts** and **unnecessary weight update attempts**
- Validators may try to set weights when they don't have new evaluation data

### ✅ **THE SOLUTION**:
Set `weights_rate_limit = 360` to **align hyperparameter with validator code**
- This matches the 72-minute epoch timing
- Eliminates conflicts between code timing and network limits
- Ensures weights are only set when validators have fresh evaluation data

---

## IMMEDIATE ACTION PLAN (Most Likely to Fix Issue)

### Phase 1: Critical Parameter Alignment (Today)
**Goal**: Align subnet 46 with proven subnet 13 parameters

- [ ] **BACKUP CURRENT STATE**: Record current hyperparameters for rollback
  ```bash
  btcli subnet hyperparameters --netuid 46 --subtensor.network finney > current_params_backup.txt
  ```

- [ ] **MEASURE BASELINE VTRUST**: Get current Vtrust values for comparison
  ```bash
  # Run the python script to get current Vtrust values
  ./venv/bin/python -c "import bittensor as bt; metagraph = bt.subtensor(network='finney').metagraph(netuid=46); print('Current Vtrust:', [float(metagraph.validator_trust[i]) for i in [1,73,138,198,220]])"
  ```

- [ ] **SET weights_rate_limit = 360** (Most Critical Change - Align with validator code)
  ```bash
  btcli sudo set hyperparameters --netuid 46 --param weights_rate_limit --value 360 --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  ```

- [ ] **SET adjustment_alpha to match subnet 13**
  ```bash
  btcli sudo set hyperparameters --netuid 46 --param adjustment_alpha --value 17893341751498264576 --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  ```

- [ ] **SET immunity_period = 12000** (match subnet 13)
  ```bash
  btcli sudo set hyperparameters --netuid 46 --param immunity_period --value 12000 --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  ```

### Phase 2: Monitor Impact (First 24 Hours)
**Goal**: Track improvement in validator alignment

- [ ] **CREATE MONITORING SCRIPT**: Save this as `monitor_vtrust.py`
  ```python
  import bittensor as bt
  import time
  import json
  from datetime import datetime
  
  def monitor_vtrust():
      subtensor = bt.subtensor(network='finney')
      metagraph = subtensor.metagraph(netuid=46)
      
      validator_uids = [1, 73, 138, 198, 220]
      vtrust_values = {}
      
      for uid in validator_uids:
          vtrust_values[uid] = {
              'vtrust': float(metagraph.validator_trust[uid]),
              'last_update_block': int(metagraph.last_update[uid]),
              'blocks_since_update': int(metagraph.block.item()) - int(metagraph.last_update[uid])
          }
      
      result = {
          'timestamp': datetime.now().isoformat(),
          'current_block': int(metagraph.block.item()),
          'validators': vtrust_values
      }
      
      print(json.dumps(result, indent=2))
      return result
  
  if __name__ == "__main__":
      monitor_vtrust()
  ```

- [ ] **RUN MONITORING EVERY 2 HOURS** for first 24 hours
  ```bash
  # Run manually every 2 hours or set up cron job
  ./venv/bin/python monitor_vtrust.py >> vtrust_monitoring.log
  ```

- [ ] **CHECK VALIDATOR LOGS**: Monitor for weight setting frequency changes
  ```bash
  # Check if validators are setting weights more frequently
  pm2 logs net46-vali --lines 100 | grep -E "(weight|epoch|block)"
  ```

### Phase 3: Evaluate Results (After 24 Hours)
**Goal**: Measure improvement and decide next steps

- [ ] **COMPARE VTRUST IMPROVEMENT**: 
  - Calculate new Vtrust mean/std deviation
  - Compare to baseline values
  - Target: >20% improvement in mean Vtrust

- [ ] **CHECK WEIGHT UPDATE FREQUENCY**:
  - Verify validators are updating more frequently
  - Look for reduced "blocks since update" values

- [ ] **MEASURE WEIGHT VARIANCE**:
  - Check if weight distributions are more aligned between validators
  - Look for reduced standard deviation in validator scores

### Phase 4: Additional Fixes (If Needed)
**Goal**: Secondary improvements if primary fixes insufficient

- [ ] **ENABLE LIQUID ALPHA** (if Vtrust still low):
  ```bash
  btcli sudo set hyperparameters --netuid 46 --param liquid_alpha_enabled --value True --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  ```

- [ ] **ADJUST ALPHA VALUES** (if liquid alpha enabled):
  ```bash
  # Match subnet 13 values
  btcli sudo set hyperparameters --netuid 46 --param alpha_high --value 58982 --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  btcli sudo set hyperparameters --netuid 46 --param alpha_low --value 45875 --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  ```

---

## ROLLBACK PLAN (If Things Go Wrong)

- [ ] **RESTORE ORIGINAL PARAMETERS** (if needed):
  ```bash
  btcli sudo set hyperparameters --netuid 46 --param weights_rate_limit --value 100 --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  btcli sudo set hyperparameters --netuid 46 --param adjustment_alpha --value 14757395258967642000 --subtensor.network finney --wallet.name YOUR_COLD_WALLET  
  btcli sudo set hyperparameters --netuid 46 --param immunity_period --value 7200 --subtensor.network finney --wallet.name YOUR_COLD_WALLET
  ```

---

## SUCCESS METRICS

### Target Improvements (24-48 hours):
- **Vtrust Mean**: From 0.552 → >0.70 (27% improvement)
- **Vtrust Std Dev**: From 0.229 → <0.15 (35% reduction)  
- **Weight Update Frequency**: All validators updating within 100 blocks of each other
- **Validator Alignment**: Reduced variance in miner weight assignments

### Critical Success Indicators:
- ✅ All validators show Vtrust > 0.5
- ✅ No validator has >200 blocks since last update  
- ✅ Vtrust standard deviation < 0.2
- ✅ No network instability or validator disconnections

---

## FUTURE IMPROVEMENTS (After Primary Fix)
*Note: Implement these later if primary fix insufficient*

- **Weight Smoothing**: Add exponential moving average to weight updates
- **Validator Coordination**: Randomize evaluation timing to prevent conflicts  
- **Enhanced Monitoring**: Real-time Vtrust dashboard
- **Dynamic Desirability**: Encourage all validators to participate in preference setting
- **Credibility System Tuning**: Adjust starting credibility and convergence rates

---

## WHY THIS APPROACH WORKS

1. **Proven Parameters**: Subnet 13 has stable Vtrust, we're copying their exact settings
2. **Root Cause**: weights_rate_limit=100 is too restrictive, causing stale weights  
3. **Immediate Impact**: Parameter changes take effect within 1-2 blocks
4. **Low Risk**: All changes are reversible via the same commands
5. **Measurable**: Clear before/after metrics to track success
