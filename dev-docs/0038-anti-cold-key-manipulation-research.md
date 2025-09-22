# Cold Key Monopolization Research: Limiting Miners per Cold Key

## Problem Statement
We have 1 user running 30 miners from the same cold key address, monopolizing the system. Need to determine:
1. How to implement a 1-miner-per-cold-key restriction
2. Whether this is a validator code change
3. If this truly solves the monopolization issue or just changes their approach

## Current System Analysis

### How Registration Works
- Miners register with unique **hotkeys** but can share the same **cold key**
- Cold key is the master wallet, hotkey is the operational key
- Current system has NO restrictions on multiple hotkeys per cold key
- Registration happens via: `btcli subnet register --netuid 46 --wallet.name coldkey --wallet.hotkey hotkey`

### Current Cold Key Usage in Validation

#### 1. **Organic Query Processor (vali_utils/organic_query_processor.py:115-150)**
The system ALREADY has some cold key diversity logic:
```python
# Select diverse miners
selected_miners = []
selected_coldkeys = set()

while len(selected_miners) < self.NUM_MINERS_TO_QUERY and top_miners:
    uid, _ = top_miners.pop(idx)
    coldkey = self.metagraph.coldkeys[uid]
    
    if coldkey not in selected_coldkeys or len(selected_coldkeys) < 2:
        selected_miners.append(uid)
        selected_coldkeys.add(coldkey)
```

**Key Finding**: The organic query system already tries to avoid selecting multiple miners with the same cold key for diversity!

#### 2. **Weight Setting Process (neurons/validator.py:582-646)**
Current weight setting:
- Gets scores from `scorer.get_scores()` 
- Normalizes scores across all UIDs
- No cold key consideration - treats each UID independently
- Uses `bt.utils.weight_utils.process_weights_for_netuid()` for final processing

#### 3. **Cold Key Blacklisting Infrastructure**
There's already infrastructure for cold key blacklisting in `common/utils.py:40-51`:
```python
def is_miner(uid: int, metagraph: bt.metagraph, vpermit_rao_limit: int) -> bool:
    # 1) Blacklist known bad coldkeys.
    # if metagraph.coldkeys[uid] in [
    # ]:
    #     bt.logging.trace(f"Ignoring known bad coldkey {metagraph.coldkeys[uid]}.")
    #     return False
```

## Implementation Options

### Option 1: Registration-Level Restriction (Subnet Parameter)
**Pros:**
- Prevents registration entirely
- Network-level enforcement
- No validator code changes needed

**Cons:**
- Requires subnet governance/parameter change
- May not be possible with current Bittensor architecture
- Hard to implement without core protocol changes

**Feasibility**: LOW - Would require Bittensor core changes

### Option 2: Validator-Level Weight Restriction
**Implementation**: Modify weight setting to distribute weights among miners with same cold key

```python
def set_weights(self):
    # ... existing code ...
    
    # Group miners by cold key and redistribute weights
    coldkey_groups = {}
    for uid in range(len(self.metagraph.coldkeys)):
        coldkey = self.metagraph.coldkeys[uid]
        if coldkey not in coldkey_groups:
            coldkey_groups[coldkey] = []
        coldkey_groups[coldkey].append(uid)
    
    # Redistribute weights within cold key groups
    adjusted_weights = raw_weights.clone()
    for coldkey, uids in coldkey_groups.items():
        if len(uids) > 1:  # Multiple miners same cold key
            total_weight = sum(raw_weights[uid] for uid in uids)
            # Give full weight to highest scoring miner, zero to others
            best_uid = max(uids, key=lambda uid: raw_weights[uid])
            for uid in uids:
                adjusted_weights[uid] = total_weight if uid == best_uid else 0
```

**Pros:**
- Can be implemented in validator code
- Immediate effect without network changes
- Preserves existing registration system

**Cons:**
- Only affects weight distribution, not actual mining
- Requires all validators to update
- Complex to implement fairly

**Feasibility**: MEDIUM-HIGH

### Option 3: Evaluation-Level Restriction
**Implementation**: Modify miner evaluation to only evaluate one miner per cold key

```python
def select_miners_for_evaluation(self):
    # ... existing selection logic ...
    
    # Filter to one miner per cold key
    seen_coldkeys = set()
    filtered_miners = []
    
    for uid in candidate_miners:
        coldkey = self.metagraph.coldkeys[uid]
        if coldkey not in seen_coldkeys:
            filtered_miners.append(uid)
            seen_coldkeys.add(coldkey)
    
    return filtered_miners
```

**Pros:**
- Reduces evaluation load
- Naturally limits rewards to one miner per cold key
- Easier to implement than weight redistribution

**Cons:**
- Other miners still waste resources mining
- Unfair if best miner from a cold key isn't selected
- Still allows registration

**Feasibility**: HIGH

### Option 4: Cold Key Blacklisting
**Implementation**: Add problematic cold keys to blacklist

```python
# In common/utils.py
BLACKLISTED_COLDKEYS = [
    "5Ey8ByeiAnqsML5KuYB3jnprQFVE25KAW9sr5HXA66YhvC3E",  # The monopolizing user
]

def is_miner(uid: int, metagraph: bt.metagraph, vpermit_rao_limit: int) -> bool:
    # Blacklist known bad coldkeys.
    if metagraph.coldkeys[uid] in BLACKLISTED_COLDKEYS:
        bt.logging.trace(f"Ignoring blacklisted coldkey {metagraph.coldkeys[uid]}.")
        return False
```

**Pros:**
- Immediate solution
- Easy to implement
- Can target specific bad actors

**Cons:**
- Reactive, not preventive
- Requires manual maintenance
- User can create new cold keys

**Feasibility**: VERY HIGH

## Will This Solve the Monopolization Issue?

### Short Term: YES
- Immediately reduces the impact of the current 30-miner operation
- Forces more fair distribution of rewards
- Improves network diversity

### Long Term: PARTIALLY
**Potential Workarounds:**
1. **Multiple Cold Keys**: User creates 30 different cold keys, each with 1 miner
2. **Sybil Attacks**: Creates appearance of different users
3. **Stake Washing**: Distributes stake across multiple identities

**Additional Measures Needed:**
1. **Stake Requirements**: Minimum stake per miner to limit Sybil attacks
2. **Geographic Diversity**: Require different IP addresses/regions
3. **Performance Monitoring**: Detect coordinated behavior patterns
4. **Registration Costs**: Higher costs for registration to limit spam

## Recommended Implementation Strategy

### Phase 1: Immediate Action (Cold Key Blacklisting)
- Add the monopolizing cold key to blacklist
- Deploy to all validators immediately
- Monitor impact on network diversity

### Phase 2: Systematic Solution (Evaluation-Level Restriction)
- Implement one-miner-per-cold-key evaluation logic
- Add configuration parameter to enable/disable
- Roll out gradually with monitoring

### Phase 3: Enhanced Protection
- Add minimum stake requirements per miner
- Implement geographic diversity requirements
- Monitor for new attack patterns

## Code Changes Required

### Primary Change Location: `vali_utils/miner_evaluator.py`
- Modify miner selection logic to enforce cold key diversity
- Add configuration parameters for the restriction

### Secondary Changes:
- `common/utils.py`: Add blacklisting logic
- `neurons/validator.py`: Optional weight redistribution logic
- Configuration files: Add parameters for cold key restrictions

## Conclusion

**Answer to Original Questions:**
1. **How to implement**: Validator code changes in miner evaluation logic
2. **Is it validator code**: YES - primarily validator-side enforcement
3. **Does it solve the issue**: Partially - reduces immediate impact but user can adapt with multiple cold keys

The most effective approach is a **multi-layered strategy** starting with immediate blacklisting and evolving to systematic restrictions with additional anti-Sybil measures.
