The subnet13 dev said that weights and balances is buggy and expensive and he's making his own logging he plans to share with other subnets.

For now we're going to disable wandb.

##########

# Validator Error Analysis: Weights & Biases (wandb) Entity Not Found

## Error Summary
The validator is failing to initialize due to a Weights & Biases (wandb) configuration error:

```
wandb.errors.errors.CommError: failed to upsert bucket: returned error 404 Not Found: {"errors": [{"message" :"entity resi-labs-ai not found during upsertBucket", "path": ["upsertBucket"]}], "data": {"upsertBucket" : null}}
```

## Root Cause
The error occurs in the `new_wandb_run()` method in `neurons/validator.py` at line 228, where the validator is hardcoded to use the entity `"resi-labs-ai"`:

```python
self.wandb_run = wandb.init(
    name=name,
    project="resi-validators",
    entity="resi-labs-ai",  # <-- This entity doesn't exist or isn't accessible
    config={...}
)
```

## Specific Issues

1. **Entity Access**: The wandb entity `"resi-labs-ai"` either:
   - Doesn't exist in your wandb account
   - You don't have access permissions to it
   - The entity name has changed

2. **Authentication**: The error suggests you're logged into wandb as `wildsagelabs` (from the log: "Currently logged in as: wildsagelabs"), but trying to create runs under the `resi-labs-ai` entity.

3. **Git Version Tag Error**: There's also a secondary error with git version fetching:
   ```
   fatal: No names found, cannot describe anything.
   Couldn't fetch latest version tag: Command '['git', 'describe', '--tags', '--abbrev=0']' returned non-zero exit status 128.
   ```

## Solutions

### Option 1: Use Your Own Entity (Recommended)
Change the entity in `neurons/validator.py` line 228 from:
```python
entity="resi-labs-ai",
```
to:
```python
entity="wildsagelabs",  # or your actual wandb username
```

### Option 2: Disable wandb Logging
Add the `--wandb.off` flag when running the validator:
```bash
python neurons/validator.py --wandb.off
```

### Option 3: Get Access to resi-labs-ai Entity
Contact the ResiLabs team to get added as a collaborator to the `resi-labs-ai` wandb entity.

### Option 4: Use Anonymous Logging
Modify the wandb.init() call to use anonymous logging by removing the entity parameter or setting it to None.

## What is Weights & Biases (wandb)?

**Weights & Biases (wandb)** is a machine learning experiment tracking platform that helps developers:
- Track and visualize training metrics, losses, and performance over time
- Log hyperparameters and configuration settings
- Save and version models and datasets
- Collaborate on ML projects with team members
- Monitor experiments remotely

## What Data Does the Validator Log to wandb?

Based on the code analysis, the validator logs the following information to wandb:

### Initial Configuration (logged once per run):
- **Validator UID**: Your validator's unique identifier on the subnet
- **Hotkey**: Your validator's wallet hotkey address
- **Run Name**: Timestamp-based unique identifier for this run
- **Type**: "validator" 
- **Version**: Git version tag (currently failing due to no tags)
- **Scrapers**: List of preferred data scrapers your validator uses

### What This Means for You:

1. **It's NOT your personal data** - The validator logs operational metrics about how it's performing, not your personal information
2. **It's shared with the ResiLabs team** - The data goes to the `resi-labs-ai` entity, which appears to be the ResiLabs organization account
3. **It's for monitoring and debugging** - This helps the ResiLabs team monitor validator performance across the network
4. **It's optional** - You can disable it with `--wandb.off` if you prefer

## Account vs Entity Clarification:

- **Your wandb account**: `wildsagelabs` (where you're logged in)
- **Target entity**: `resi-labs-ai` (where the data should go)
- **The issue**: You don't have permission to write to the `resi-labs-ai` entity

## Should You Use wandb or Not?

### **Recommendation: DISABLE wandb (`--wandb.off`)**

Here's why you should run without wandb, especially as a new validator:

### **Downsides of wandb:**
1. **Cost**: wandb can be expensive for continuous logging (runs 24/7)
2. **Buggy**: You've heard correctly - wandb can be unreliable and cause crashes
3. **Not Essential**: The validator has robust built-in monitoring alternatives
4. **Being Deprecated**: Code comment says "After July 15th 2025 we are moving away from wandb"
5. **Permission Issues**: You don't have access to the `resi-labs-ai` entity anyway

### **What You'll Miss Without wandb:**
**Almost nothing critical!** The validator only logs basic configuration data to wandb:
- Validator UID and hotkey (already public on blockchain)
- Scraper preferences
- Version info
- Run timestamps

### **Better Monitoring Alternatives Available:**

#### 1. **Prometheus Metrics (Built-in)**
The validator has comprehensive Prometheus metrics tracking:
- Main loop iterations and errors
- Weight setting success/failure
- Validation duration and success rates
- API request metrics
- Dynamic desirability retrieval metrics

#### 2. **Validator API Server**
Enable with `--neuron.api_on` to get:
- Real-time health monitoring
- Performance metrics dashboard
- System status endpoints
- Rate limiting and usage tracking

#### 3. **Standard Logging**
The validator logs extensively to files:
- Detailed validation logs
- Error tracking
- Performance metrics
- Debug information

#### 4. **Blockchain Monitoring**
- Use `btcli wallet overview` to check validator status
- Monitor stake and registration
- Track weight setting success

### **For a New Validator, Focus On:**
1. **Getting the validator running reliably** (disable wandb)
2. **Monitoring via logs and API** (much more useful)
3. **Understanding the validation process** (not wandb dashboards)
4. **Setting up proper monitoring** (Prometheus + Grafana if needed)

### **Command to Run Without wandb:**
```bash
python neurons/validator.py --wandb.off --neuron.api_on
```

## Additional Notes

- The validator continues to run despite the wandb error (it catches the exception and retries later)
- The git version tag error is non-critical but indicates the repository might not have any tags
- The validator is configured to retry wandb initialization in the main loop if it fails initially
- **Important**: The comment in the code says "After July 15th 2025 we are moving away from wandb" - so this may become obsolete soon

## Files Modified

### Changes Made to Disable wandb by Default:

1. **`neurons/config.py`**:
   - Changed `--wandb.off` default from `False` to `True` (wandb disabled by default)
   - Added `--wandb.on` flag to enable wandb when needed
   - Updated help text to reflect new default behavior

2. **`neurons/validator.py`**:
   - Updated wandb initialization logic to check both `--wandb.on` and `--wandb.off` flags
   - Logic: wandb runs if `--wandb.on` is set OR `--wandb.off` is not set
   - This means wandb is disabled by default, but can be enabled with `--wandb.on`

3. **`docs/validator.md`**:
   - Updated documentation to reflect new default behavior
   - Added `--wandb.on` flag documentation
   - Removed `--wandb.off` from example commands since it's now the default

### How to Use:

**Default behavior (wandb disabled):**
```bash
python neurons/validator.py  # wandb is automatically disabled
```

**Enable wandb when needed:**
```bash
python neurons/validator.py --wandb.on  # enables wandb logging
```

**Explicitly disable wandb (redundant but clear):**
```bash
python neurons/validator.py --wandb.off  # explicitly disables wandb
```