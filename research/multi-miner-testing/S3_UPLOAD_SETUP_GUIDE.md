# S3 Upload Setup Guide - Complete Documentation

## 🎯 **Issues Identified & Fixed**

### ❌ **Root Cause #1: Platform Mapping Mismatch**
**Problem**: The dynamic desirability file uses `"platform": "rapid_zillow"` but the S3 uploader only recognized `"zillow"`.

**Fix Applied**: `upload_utils/s3_uploader.py` (Line 145)
```python
# BEFORE (broken):
elif platform == 'zillow':
    source_int = DataSource.RAPID_ZILLOW.value

# AFTER (fixed):
elif platform in ['zillow', 'rapid_zillow']:
    source_int = DataSource.RAPID_ZILLOW.value
```

### ❌ **Root Cause #2: CRITICAL Label Mismatch**
**Problem**: The dynamic desirability file requested labels like `"status:forsale"` and `"status:forrent"`, but miners only store `"zip:XXXXX"` labels.

**Evidence**:
- Dynamic desirability requested: `"status:forsale"`, `"status:forrent"`, `"zip:77494"`
- Database actually contained: `"zip:01803"`, `"zip:02130"`, `"zip:02780"`, etc.
- Result: S3 uploader found 0 records for every job due to label mismatch

**Fix Applied**: Created corrected `dynamic_desirability/total.json` with 141 actual zip code labels from database:
```json
{
  "id": "zillow_zip_02130",
  "weight": 1.0,
  "params": {
    "platform": "rapid_zillow",
    "label": "zip:02130",  // Using actual database labels
    "keyword": null
  }
}
```

## 🚀 **How to Ensure S3 Uploads Work for Future Miners**

### 1. **Required Files & Configuration**

**Dynamic Desirability File**: `dynamic_desirability/total.json`
- Must exist and contain job configurations
- Uses `"platform": "rapid_zillow"` for Zillow data
- **Critical**: Platform names must match S3 uploader mapping

**S3 Uploader Configuration**:
- `--use_uploader` flag (enabled by default)
- Separate state files per miner: `--miner_upload_state_file upload_utils/state_file_minerX.json`
- Testnet S3 auth URL: `https://api-staging.resilabs.ai`

### 2. **Miner Launch Command Template**

```bash
screen -dmS miner_X bash -c "
source venv/bin/activate && 
python neurons/miner.py \
  --netuid 428 \
  --subtensor.network test \
  --wallet.name WALLET_NAME \
  --wallet.hotkey HOTKEY_NAME \
  --use_uploader \
  --logging.debug \
  --neuron.database_name SqliteMinerStorage_minerX.sqlite \
  --miner_upload_state_file upload_utils/state_file_minerX.json
"
```

### 3. **S3 Upload Process Timeline**

**Testnet (netuid 428)**:
- **Initial Wait**: 5 minutes before first upload
- **Upload Frequency**: Every 5 minutes thereafter
- **Directory Creation**: `s3_partitioned_storage/{miner_hotkey}/`

**Mainnet (netuid 46)**:
- **Initial Wait**: 30 minutes before first upload  
- **Upload Frequency**: Every 2 hours thereafter

### 4. **Platform Mapping Support**

The S3 uploader now supports these platform mappings:
```python
'reddit' → DataSource.REDDIT.value
['x', 'twitter'] → DataSource.X.value  
'youtube' → DataSource.YOUTUBE.value
['zillow', 'rapid_zillow'] → DataSource.RAPID_ZILLOW.value
```

## 🔍 **Verification Steps**

### Step 1: Check S3 Uploader Initialization
```python
# Test script to verify S3 uploader works
import bittensor as bt
from upload_utils.s3_uploader import S3PartitionedUploader

wallet = bt.wallet(name='WALLET_NAME', hotkey='HOTKEY_NAME')
subtensor = bt.subtensor(network='test')

s3_uploader = S3PartitionedUploader(
    db_path='SqliteMinerStorage.sqlite',
    subtensor=subtensor,
    wallet=wallet,
    s3_auth_url='https://api-staging.resilabs.ai',
    state_file='upload_utils/state_file.json'
)

# Test upload
result = s3_uploader.upload_dd_data()
print(f"Upload result: {result}")
```

### Step 2: Monitor S3 Upload Activity
```bash
# Check for S3 directories (created after first upload)
ls -la s3_partitioned_storage/

# Monitor S3 state files for updates
watch -n 30 'ls -la upload_utils/state_file*s3*.json'

# Check miner logs for S3 activity
screen -r miner_X
# Look for: "Starting S3 partitioned upload", "S3 upload thread started"
```

### Step 3: Verify Upload Success
```bash
# Check state files are being updated
find upload_utils/ -name "*s3*.json" -newer SqliteMinerStorage.sqlite

# Look for S3 success messages in logs
grep -i "s3.*success\|upload.*success" ~/.bittensor/miners/*/hotkey*/netuid*/None/events.log
```

## 🛠 **Troubleshooting Common Issues**

### Issue 1: "Unsupported platform" warnings
**Cause**: Platform name in `dynamic_desirability/total.json` not recognized
**Solution**: Update platform mapping in `upload_utils/s3_uploader.py` line 145

### Issue 2: "No jobs found from Gravity"
**Cause**: No matching jobs after platform filtering
**Solution**: Verify `dynamic_desirability/total.json` exists and has valid job configs

### Issue 3: S3 authentication failures
**Cause**: Wrong S3 auth URL or wallet issues
**Solution**: 
- Testnet: `https://api-staging.resilabs.ai`
- Mainnet: `https://api.resilabs.ai`

### Issue 4: S3 upload thread not starting
**Cause**: S3 uploader not initialized or `use_uploader` disabled
**Solution**: Ensure `--use_uploader` flag and check miner logs for "S3 upload thread started"

## 📋 **Quick Setup Checklist**

- [ ] ✅ `dynamic_desirability/total.json` exists
- [ ] ✅ Platform mapping fixed in `s3_uploader.py`
- [ ] ✅ Miner launched with `--use_uploader` flag
- [ ] ✅ Separate state file per miner
- [ ] ✅ Correct S3 auth URL for network
- [ ] ✅ Wait 5+ minutes for first upload (testnet)
- [ ] ✅ Monitor state file updates
- [ ] ✅ Check for S3 directories creation

## 🎯 **Expected Results**

**After Fix Applied**:
- ✅ No more "Unsupported platform: rapid_zillow" warnings
- ✅ S3 upload returns `True` (success)
- ✅ State files updated every 5 minutes
- ✅ S3 directories created per miner hotkey
- ✅ Validators can access miner data from S3

**Timeline**:
- **0-5 minutes**: Miner startup, S3 uploader initialization
- **5-10 minutes**: First S3 upload attempt  
- **10+ minutes**: Regular 5-minute upload cycles
- **Ongoing**: Continuous data upload to S3 for validator access
