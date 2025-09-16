# Weights & Biases (wandb) Configuration Research

## Current wandb Configuration in Codebase

### **Current Setup:**
- **Project**: `resi-validators`
- **Entity**: `resi-labs-ai` (hardcoded)
- **Default Status**: **DISABLED** by default (as of recent changes)
- **Configuration**: Located in `neurons/validator.py` and `neurons/config.py`

### **Key Findings from Code Analysis:**

#### **1. wandb is Currently Disabled by Default**
```python
# In neurons/config.py
parser.add_argument(
    "--wandb.off",
    action="store_true",
    help="Set this flag to disable logging to wandb.",
    default=True, # Disabled by default - wandb is expensive and buggy for 24/7 logging
)
```

#### **2. Hardcoded Entity Configuration**
```python
# In neurons/validator.py line 236-252
self.wandb_run = wandb.init(
    name=name,
    project="resi-validators",
    entity="resi-labs-ai",  # <-- HARDCODED ENTITY
    config={
        "uid": self.uid,
        "hotkey": self.wallet.hotkey.ss58_address,
        "run_name": run_id,
        "type": "validator",
        "version": version_tag,
        "scrapers": scraper_providers
    },
    allow_val_change=True,
    anonymous="allow",
    reinit=True,
    resume="never",
    settings=wandb.Settings(start_method="thread"),
)
```

#### **3. What Data is Logged to wandb:**
- **Validator UID**: Your validator's unique identifier
- **Hotkey**: Your validator's wallet address
- **Run Name**: Timestamp-based unique identifier
- **Type**: "validator"
- **Version**: Git version tag
- **Scrapers**: List of preferred data scrapers

## Configuration Options for Your New wandb Account

### **Option 1: Use Your Own Entity (Recommended)**
**Steps on wandb website:**
1. Go to https://wandb.ai
2. Sign in to your new account
3. Go to Settings → Teams & Organizations
4. Note your username (this will be your entity name)

**Code changes needed:**
```python
# Change in neurons/validator.py line 239
entity="your-wandb-username",  # Replace with your actual wandb username
```

### **Option 2: Create a Team/Organization**
**Steps on wandb website:**
1. Go to https://wandb.ai
2. Click "Create Team" or "Create Organization"
3. Choose a name (e.g., "your-validator-team")
4. Invite collaborators if needed
5. Note the team/organization name

**Code changes needed:**
```python
# Change in neurons/validator.py line 239
entity="your-team-name",  # Replace with your team/organization name
```

### **Option 3: Use Anonymous Logging**
**Code changes needed:**
```python
# Remove or comment out the entity line in neurons/validator.py
self.wandb_run = wandb.init(
    name=name,
    project="resi-validators",
    # entity="resi-labs-ai",  # <-- Remove this line
    config={...}
)
```

## API Key Configuration

### **Do You Need to Provide API Keys to Validators?**
**Answer: NO** - Each validator runs independently and uses its own wandb account.

### **How wandb Authentication Works:**
1. **Local Authentication**: Each validator machine needs to authenticate with wandb
2. **API Key Storage**: wandb stores API keys locally on each machine
3. **No Sharing Required**: Validators don't share API keys with each other

### **Steps to Set Up wandb Authentication:**

#### **1. Get Your API Key:**
1. Go to https://wandb.ai/settings
2. Scroll down to "API Keys"
3. Click "Create new key"
4. Copy the API key (starts with something like `a1b2c3d4e5f6...`)

#### **2. Authenticate on Your Validator Machine:**
```bash
# Install wandb if not already installed
pip install wandb

# Login with your API key
wandb login

# When prompted, paste your API key
```

#### **3. Verify Authentication:**
```bash
# Check if you're logged in
wandb status

# Should show your username and API key status
```

## Team Collaboration Setup (If Needed)

### **If You Want to Share Data with Other Validators:**

#### **1. Create a Team on wandb:**
1. Go to https://wandb.ai
2. Click "Create Team" or "Create Organization"
3. Choose a name (e.g., "bittensor-subnet-46")
4. Set privacy level (public/private)

#### **2. Invite Collaborators:**
1. Go to your team page
2. Click "Invite Members"
3. Enter email addresses of other validators
4. Set permission level (Viewer/Editor/Admin)

#### **3. Update Code for Team:**
```python
# Change in neurons/validator.py line 239
entity="your-team-name",  # Replace with your team name
```

## Cost Considerations

### **wandb Pricing (2024):**
- **Free Tier**: 100GB storage, unlimited runs
- **Paid Plans**: Start at $50/month for teams
- **24/7 Logging**: Can be expensive for continuous operation

### **Cost Optimization:**
1. **Use Free Tier**: For individual validators, free tier should be sufficient
2. **Rotate Runs**: Code already rotates runs every 3 hours to manage costs
3. **Disable if Needed**: Can always disable with `--wandb.off`

## Recommended Setup for New Validator

### **Step 1: Create wandb Account**
1. Go to https://wandb.ai
2. Sign up with your email
3. Verify your account

### **Step 2: Get API Key**
1. Go to Settings → API Keys
2. Create new key
3. Copy the key

### **Step 3: Authenticate Locally**
```bash
wandb login
# Paste your API key when prompted
```

### **Step 4: Update Code**
```python
# In neurons/validator.py line 239, change:
entity="your-wandb-username",  # Replace with your actual username
```

### **Step 5: Test Configuration**
```bash
# Run validator with wandb enabled
python neurons/validator.py --wandb.on

# Check wandb dashboard at https://wandb.ai
# Look for project "resi-validators"
```

## Alternative: Keep wandb Disabled

### **Why You Might Want to Disable wandb:**
1. **Cost**: 24/7 logging can be expensive
2. **Buggy**: Code comments indicate wandb can be unreliable
3. **Being Deprecated**: Code says "After July 15th 2025 we are moving away from wandb"
4. **Not Essential**: Validator has other monitoring options

### **Better Monitoring Alternatives:**
1. **Prometheus Metrics**: Built-in comprehensive monitoring
2. **Validator API**: Enable with `--neuron.api_on`
3. **Standard Logging**: Detailed logs to files
4. **Blockchain Monitoring**: Use `btcli wallet overview`

### **Command to Run Without wandb:**
```bash
python neurons/validator.py --wandb.off --neuron.api_on
```

## Summary

### **For Your New wandb Account:**
1. **Create account** at https://wandb.ai
2. **Get API key** from Settings → API Keys
3. **Authenticate locally** with `wandb login`
4. **Update code** to use your entity name
5. **Test configuration** with `--wandb.on`

### **For Team Collaboration:**
1. **Create team** on wandb website
2. **Invite other validators** to your team
3. **Update code** to use team entity name
4. **Each validator** authenticates with their own API key

### **Recommendation:**
- **Start with wandb disabled** (`--wandb.off`) to get validator running
- **Enable later** if you want the monitoring data
- **Consider alternatives** like Prometheus + Grafana for better monitoring
