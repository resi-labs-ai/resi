# Validator Weight Setting Analysis

## Question 1: How often does the validator code try to set weights?

### Answer: Every 20 minutes (after initial startup delay)

### Key Findings:

1. **Weight Setting Frequency**: The validator sets weights every **20 minutes** after the initial startup period.

2. **Startup Delay**: After validator startup, it must complete **15 evaluation cycles** before it starts setting weights. This is controlled by the `EVALUATION_ON_STARTUP = 15` constant.

3. **Evaluation vs Weight Setting Timing**:
   - **Miner Evaluation**: Every 4 hours (240 minutes) by default, configurable via `MINER_EVAL_PERIOD_MINUTES` environment variable
   - **Weight Setting**: Every 20 minutes (independent of evaluation timing)

### Code Evidence:

**Weight Setting Logic** (`neurons/validator.py` lines 474-494):
```python
def should_set_weights(self) -> bool:
    # Check if enough epoch blocks have elapsed since the last epoch.
    if self.config.neuron.disable_set_weights:
        return False

    with self.lock:
        # After a restart, we want to wait two evaluation cycles
        # Check if we've completed at least two evaluation cycles since startup
        if not self.evaluation_cycles_since_startup:
            self.evaluation_cycles_since_startup = 0
            bt.logging.info("Initializing evaluation cycles counter for delayed weight setting")

        #  if we've completed fewer than the allotted number of evaluation cycles, don't set weights
        if self.evaluation_cycles_since_startup < constants.EVALUATION_ON_STARTUP:
            bt.logging.info(
                f"Skipping weight setting - completed {self.evaluation_cycles_since_startup}/15 evaluation cycles since startup")
            return False

        # Normal 20-minute interval check for subsequent weight settings
        return dt.datetime.utcnow() - self.last_weights_set_time > dt.timedelta(minutes=20)
```

**Main Loop** (`neurons/validator.py` lines 286-288):
```python
# Maybe set weights.
if self.should_set_weights():
    self.set_weights()
```

**Evaluation Timing** (`common/constants.py` lines 33-35):
```python
_DEFAULT_EVAL_PERIOD_MINUTES = 240
_TESTNET_EVAL_PERIOD_MINUTES = int(os.getenv('MINER_EVAL_PERIOD_MINUTES', _DEFAULT_EVAL_PERIOD_MINUTES))
MIN_EVALUATION_PERIOD = dt.timedelta(minutes=_TESTNET_EVAL_PERIOD_MINUTES)
```

## Question 2: Why does it require 15 evaluation cycles since starting?

### Answer: To allow the scoring system to build up sufficient data and credibility before setting meaningful weights

### Key Reasoning:

1. **Scoring System Initialization**: The validator starts with all miners having zero scores and zero credibility (`STARTING_CREDIBILITY = 0`). The scoring system needs time to:
   - Evaluate miners and collect their data
   - Build up credibility scores through validation
   - Establish meaningful score differences between miners

2. **Credibility Building Process**: The scoring system uses a credibility-based approach where:
   - Miners start with `STARTING_CREDIBILITY = 0` (no trust initially)
   - Credibility increases through successful validations
   - Credibility decreases when miners fail validation or provide inconsistent data
   - Final scores = raw data scores × credibility^2.5

3. **Data Collection Requirements**: The validator needs to:
   - Evaluate miners across multiple batches (15 miners per batch)
   - Collect sufficient validation data to make informed scoring decisions
   - Allow the credibility system to stabilize before setting weights

4. **Preventing Premature Weight Setting**: Without this delay, the validator would:
   - Set weights based on incomplete or zero data
   - Potentially give unfair advantages to miners evaluated first
   - Make uninformed decisions about miner quality

### Code Evidence:

**Starting Credibility** (`rewards/miner_scorer.py` lines 18-19):
```python
# Start new miner's at a credibility of 0.
STARTING_CREDIBILITY = 0
```

**Credibility Scaling** (`rewards/miner_scorer.py` lines 24-25):
```python
# The exponent used to scale the miner's score by its credibility.
_CREDIBILITY_EXP = 2.5
```

**Evaluation Batch Size** (`vali_utils/miner_evaluator.py` line 352):
```python
# Run in batches of 15.
miners_to_eval = 15
```

## Question 3: If an evaluation period is 4 hours, how long does the 15 period immunity last?

### Answer: 60 hours (2.5 days)

### Calculation:

- **Evaluation Period**: 4 hours (240 minutes) per cycle
- **Required Cycles**: 15 evaluation cycles
- **Total Time**: 15 cycles × 4 hours = **60 hours**

### Breakdown:
- **60 hours** = **2.5 days** = **3,600 minutes**

### Important Notes:

1. **Evaluation vs Weight Setting Timing**: While miners are evaluated every 4 hours, the validator's main loop runs continuously and can complete multiple evaluation cycles in parallel.

2. **Batch Processing**: Each evaluation cycle processes 15 miners simultaneously, so the validator can evaluate many miners within each 4-hour window.

3. **Accelerated Testing**: For testing purposes, the evaluation period can be reduced (e.g., to 5 minutes) using the `MINER_EVAL_PERIOD_MINUTES` environment variable, which would reduce the immunity period to 75 minutes.

## Question 4: Does every validator validate every miner every 4 hours?

### Answer: No - validators operate independently and evaluate miners at different times

### Key Findings:

1. **Independent Operation**: Each validator operates independently with its own:
   - Miner iterator starting at a random position
   - Evaluation schedule based on when it started
   - Local storage of when each miner was last evaluated

2. **Randomized Starting Position**: The `MinerIterator` starts at a random position to prevent all validators from evaluating the same miners simultaneously:
   ```python
   # Start the index at a random position. This helps ensure that miners with high UIDs aren't penalized if
   # the validator restarts frequently.
   self.index = random.randint(0, len(self.miner_uids) - 1)
   ```

3. **Individual Evaluation Tracking**: Each validator maintains its own `last_evaluated` timestamp for each miner, so they don't coordinate evaluation schedules.

4. **Cyclical Evaluation**: Validators cycle through all miners continuously, but each validator starts at a different point in the cycle.

### How It Works:

1. **Validator Startup**: When a validator starts, it creates a `MinerIterator` with a random starting position
2. **Evaluation Logic**: Each validator checks if the next miner in its cycle is due for evaluation (4+ hours since last evaluation)
3. **Independent Timing**: If a miner was recently evaluated by this validator, it waits; if not, it evaluates the next batch of 15 miners
4. **No Coordination**: Validators don't communicate with each other about evaluation schedules

### Code Evidence:

**Random Starting Position** (`vali_utils/miner_iterator.py` lines 18-20):
```python
# Start the index at a random position. This helps ensure that miners with high UIDs aren't penalized if
# the validator restarts frequently.
self.index = random.randint(0, len(self.miner_uids) - 1)
```

**Individual Evaluation Tracking** (`vali_utils/miner_evaluator.py` lines 336-341):
```python
last_evaluated = self.storage.read_miner_last_updated(hotkey)
now = dt.datetime.utcnow()
due_update = (
    last_evaluated is None
    or (now - last_evaluated) >= constants.MIN_EVALUATION_PERIOD
)
```

## Question 5: How can I adjust the evaluation period to every epoch (72 min, 360 blocks)?

### Answer: Set the `MINER_EVAL_PERIOD_MINUTES` environment variable to 72

### Understanding Epoch Length:

**Epoch Calculation:**
- **Block Time**: 12 seconds per block
- **Epoch Length**: 360 blocks (as you mentioned)
- **Epoch Duration**: 360 blocks × 12 seconds = 4,320 seconds = **72 minutes**

**Current Configuration:**
- **Default Epoch Length**: 100 blocks = 20 minutes (100 × 12 seconds)
- **Default Evaluation Period**: 240 minutes (4 hours)
- **Your Target**: 360 blocks = 72 minutes

### How to Configure:

#### Option 1: Environment Variable (Recommended)
Set the environment variable before running the validator:

```bash
export MINER_EVAL_PERIOD_MINUTES=72
python neurons/validator.py [other flags]
```

#### Option 2: Inline Environment Variable
```bash
MINER_EVAL_PERIOD_MINUTES=72 python neurons/validator.py [other flags]
```

#### Option 3: Modify Default in Code
Edit `common/constants.py` line 33:
```python
# Change from:
_DEFAULT_EVAL_PERIOD_MINUTES = 240
# To:
_DEFAULT_EVAL_PERIOD_MINUTES = 72
```

### Impact of This Change:

**With 72-minute evaluation periods:**
- **15-period immunity duration**: 15 cycles × 72 minutes = **18 hours** (instead of 60 hours)
- **Evaluation frequency**: Every 72 minutes instead of every 4 hours
- **More frequent validation**: Miners get evaluated 3.33x more often
- **Higher API costs**: More frequent validation = more RapidAPI calls

### Code Evidence:

**Environment Variable Usage** (`common/constants.py` lines 33-35):
```python
_DEFAULT_EVAL_PERIOD_MINUTES = 240
_TESTNET_EVAL_PERIOD_MINUTES = int(os.getenv('MINER_EVAL_PERIOD_MINUTES', _DEFAULT_EVAL_PERIOD_MINUTES))
MIN_EVALUATION_PERIOD = dt.timedelta(minutes=_TESTNET_EVAL_PERIOD_MINUTES)
```

**Epoch Length Configuration** (`neurons/config.py` lines 94-98):
```python
parser.add_argument(
    "--neuron.epoch_length",
    type=int,
    help="The default epoch length (how often we sync the metagraph, measured in 12 second blocks).",
    default=100,
)
```

**Epoch Calculation** (`neurons/miner.py` lines 323-326):
```python
# Epoch length defaults to 100 blocks at 12 seconds each for 20 minutes.
while dt.datetime.now() - self.last_sync_timestamp < (
    dt.timedelta(seconds=12 * self.config.neuron.epoch_length)
):
```

## Question 6: How to make validators set weights every epoch (72 minutes) instead of every 20 minutes?

### Answer: Code has been modified to track epoch boundaries using block numbers

### Changes Made:

#### 1. Added Epoch Tracking (`neurons/validator.py`)
- **Added**: `self.last_weights_set_block = 0` to track the block when weights were last set
- **Modified**: `should_set_weights()` method to check epoch boundaries instead of time intervals
- **Updated**: `set_weights()` method to record the current block when weights are set

#### 2. Updated Epoch Length (`neurons/config.py`)
- **Changed**: Default epoch length from 100 blocks to **360 blocks** (72 minutes)
- **Calculation**: 360 blocks × 12 seconds = 4,320 seconds = 72 minutes

#### 3. New Weight Setting Logic
```python
# Check if an epoch has passed since last weight setting
current_block = self.block
epoch_length = self.config.neuron.epoch_length
blocks_since_last_weights = current_block - self.last_weights_set_block

# If we haven't set weights yet, or if an epoch has passed
if self.last_weights_set_block == 0 or blocks_since_last_weights >= epoch_length:
    return True
```

### How It Works Now:

1. **Epoch-Based Weight Setting**: Validators now set weights every 360 blocks (72 minutes) instead of every 20 minutes
2. **Block Tracking**: The system tracks the block number when weights were last set
3. **Epoch Boundary Detection**: When the current block minus the last weights set block equals or exceeds 360, weights are set
4. **Startup Delay Preserved**: Still requires 15 evaluation cycles before first weight setting

### Benefits:

- **Synchronized with Network**: Weight setting now aligns with the actual blockchain epoch length
- **More Predictable**: Weight setting happens at consistent epoch boundaries
- **Better Performance**: Reduces unnecessary weight setting attempts
- **Network Alignment**: Matches the 72-minute epoch length you specified

### Testing:

To test the changes, run your validator and monitor the logs for:
```
Epoch boundary reached: current_block=X, last_weights_set_block=Y, blocks_since_last_weights=Z, epoch_length=360
```

### Summary:
- **Weight setting frequency**: Every epoch (360 blocks = 72 minutes)
- **Miner evaluation frequency**: Every 4 hours (240 minutes) by default
- **Startup delay**: Must complete 15 evaluation cycles before first weight setting
- **Immunity duration**: 60 hours (2.5 days) with 4-hour evaluation periods
- **Independent timing**: Weight setting and miner evaluation operate on separate schedules
- **Purpose of delay**: Allows scoring system to build credibility and collect sufficient validation data before making weight decisions
- **Validator coordination**: No - each validator operates independently with randomized starting positions
- **Epoch-based weights**: Now uses block-based epoch tracking instead of time-based intervals
