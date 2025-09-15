# Organic Strategy Experiment - Complete Guide

## 🎯 **Experiment Overview**

This experiment tests whether your subnet's incentive mechanisms naturally drive miners to develop different strategies for comprehensive US real estate data coverage. Instead of artificially assigning territories, all miners start with identical configurations and compete organically.

## 🚀 **How to Restart the Experiment**

### Prerequisites
- Ensure you're in the project directory: `/Users/calebgates/bittensor/other-subnets/46-resi`
- Virtual environment activated: `source venv/bin/activate`
- All wallet registrations complete (UIDs 5, 7, 8, 9 on testnet 428)

### Step 1: Start the Validator (with 5-minute evaluation cycles)
```bash
export MINER_EVAL_PERIOD_MINUTES=5
screen -dmS validator bash -c "source venv/bin/activate && python neurons/validator.py --netuid 428 --subtensor.network test --wallet.name 428_testnet_validator --wallet.hotkey 428_testnet_validator_hotkey --logging.debug --max_targets 10"
```

### Step 2: Start the Miners (each with separate databases)
```bash
# Miner 2 (UID 7)
screen -dmS miner_2 bash -c "source venv/bin/activate && python neurons/miner.py --netuid 428 --subtensor.network test --wallet.name testnet_miner_2 --wallet.hotkey hotkey_2 --use_uploader --logging.debug --neuron.database_name SqliteMinerStorage_miner2.sqlite"

# Miner 3 (UID 8)
screen -dmS miner_3 bash -c "source venv/bin/activate && python neurons/miner.py --netuid 428 --subtensor.network test --wallet.name testnet_miner_3 --wallet.hotkey hotkey_3 --use_uploader --logging.debug --neuron.database_name SqliteMinerStorage_miner3.sqlite"

# Miner 4 (UID 9)
screen -dmS miner_4 bash -c "source venv/bin/activate && python neurons/miner.py --netuid 428 --subtensor.network test --wallet.name testnet_miner_4 --wallet.hotkey hotkey_4 --use_uploader --logging.debug --neuron.database_name SqliteMinerStorage_miner4.sqlite"
```

### Step 3: Verify All Processes Running
```bash
screen -list
# Should show: validator, miner_2, miner_3, miner_4
```

## 📊 **Monitoring the Experiment**

### Real-time Analysis
```bash
python3 organic_analysis.py
```

### Continuous Monitoring (every 5 minutes)
```bash
./monitor_organic_strategies.sh
```

### Network Status
```bash
btcli subnet metagraph --netuid 428 --subtensor.network test
```

### Individual Process Logs
```bash
screen -r validator    # Attach to validator (Ctrl+A, D to detach)
screen -r miner_2      # Attach to miner 2 logs
screen -r miner_3      # Attach to miner 3 logs  
screen -r miner_4      # Attach to miner 4 logs
```

## 💾 **Database Connections in DataGrip**

### Database Files Location
- **Baseline Miner (UID 5)**: `SqliteMinerStorage.sqlite`
- **Organic Miner 2 (UID 7)**: `SqliteMinerStorage_miner2.sqlite`
- **Organic Miner 3 (UID 8)**: `SqliteMinerStorage_miner3.sqlite`
- **Organic Miner 4 (UID 9)**: `SqliteMinerStorage_miner4.sqlite`

### DataGrip Connection Setup

1. **Open DataGrip** → New → Data Source → SQLite

2. **For each database, create a connection:**
   
   **Connection 1 - Baseline Miner (UID 5)**
   - Name: `Testnet_Miner_5_Baseline`
   - File: `/Users/calebgates/bittensor/other-subnets/46-resi/SqliteMinerStorage.sqlite`
   
   **Connection 2 - Organic Miner 2 (UID 7)**
   - Name: `Testnet_Miner_7_Organic`
   - File: `/Users/calebgates/bittensor/other-subnets/46-resi/SqliteMinerStorage_miner2.sqlite`
   
   **Connection 3 - Organic Miner 3 (UID 8)**
   - Name: `Testnet_Miner_8_Organic`
   - File: `/Users/calebgates/bittensor/other-subnets/46-resi/SqliteMinerStorage_miner3.sqlite`
   
   **Connection 4 - Organic Miner 4 (UID 9)**
   - Name: `Testnet_Miner_9_Organic`
   - File: `/Users/calebgates/bittensor/other-subnets/46-resi/SqliteMinerStorage_miner4.sqlite`

3. **Test each connection** and click "Apply"

### Key Tables to Monitor
- **DataEntity**: Main table containing scraped real estate listings
- Check columns: `source`, `label`, `contentSizeBytes`, `timeBucketId`

### Useful Queries for Strategy Analysis
```sql
-- Count records per miner
SELECT COUNT(*) as total_records FROM DataEntity;

-- Records by zipcode (label contains zip info)
SELECT label, COUNT(*) as count 
FROM DataEntity 
WHERE label LIKE 'zip:%' 
GROUP BY label 
ORDER BY count DESC;

-- Recent activity (last hour)
SELECT label, COUNT(*) as recent_count
FROM DataEntity 
WHERE datetime(timeBucketId, 'unixepoch') > datetime('now', '-1 hour')
GROUP BY label;

-- Data size analysis
SELECT label, 
       COUNT(*) as records,
       SUM(contentSizeBytes) as total_bytes,
       AVG(contentSizeBytes) as avg_bytes
FROM DataEntity 
GROUP BY label 
ORDER BY records DESC;
```

## ☁️ **S3 Upload Verification**

### Check S3 Upload Status
```bash
# Monitor S3 upload logs in miner logs
screen -r miner_2
# Look for lines containing "S3", "upload", "partitioned"

# Check upload state files
ls -la upload_utils/state_file*.json
```

### S3 Upload Configuration Files
- Main state file: `upload_utils/state_file_s3_partitioned.json`
- Each miner should create its own upload tracking

### Verify S3 Uploads Working
1. **Check miner logs** for S3 upload success messages
2. **Monitor upload state files** for timestamp updates
3. **Look for S3 authentication** success in startup logs

### S3 Upload Commands to Monitor
```bash
# Check recent S3 upload activity
grep -i "s3\|upload" ~/.bittensor/miners/testnet_miner_*/hotkey_*/netuid428/None/events.log

# Monitor upload state file changes
watch -n 30 'ls -la upload_utils/state_file*.json'
```

## ✅ **Validator Verification**

### Check Validator is Evaluating All Miners
```bash
# Monitor validator logs for evaluation activity
screen -r validator
# Look for: "Running validation on the following batch of uids: {7, 8, 9}"
```

### Validator Evaluation Verification
```bash
# Check validator is seeing all miners
btcli subnet metagraph --netuid 428 --subtensor.network test

# Look for evaluation logs
grep -i "evaluat" ~/.bittensor/miners/428_testnet_validator/*/netuid428/None/events.log
```

### API Validation Monitoring
```bash
# Monitor API validation in validator logs
tail -f ~/.bittensor/miners/428_testnet_validator/*/netuid428/None/events.log | grep -E "(API|validation|Zillow|RapidAPI)"
```

### Expected Validator Behavior
- **Every 5 minutes**: Validator should evaluate miners due for update
- **API Validation**: Should sample 10 entities per miner per cycle
- **Score Updates**: Should see incentive/emission changes in metagraph

## 🔍 **Success Indicators**

### Database Growth Patterns
- Each miner database should grow at different rates
- Different zipcodes appearing in different miners
- Unique strategies emerging over 2-4 hours

### Network Metrics
- Incentive values diverging between miners
- Different emission patterns
- Miners discovering premium zipcodes at different times

### S3 Upload Success
- Upload state files updating regularly
- No S3 authentication errors in logs
- Validator can access miner data for validation

## 🛑 **How to Stop the Experiment**

```bash
# Stop all processes
screen -S validator -X quit
screen -S miner_2 -X quit  
screen -S miner_3 -X quit
screen -S miner_4 -X quit

# Verify stopped
screen -list
```

## 📈 **Expected Timeline**

- **0-30 minutes**: Miners starting up, databases initializing
- **30-60 minutes**: First data collection, S3 uploads beginning
- **1-2 hours**: Clear strategy differentiation emerging
- **2-4 hours**: Stable patterns, premium zipcode competition
- **4+ hours**: Long-term sustainable strategies vs gaming

## 🎯 **What You're Testing**

This experiment validates whether your incentive mechanisms naturally drive:
1. **Comprehensive Geographic Coverage** across all US regions
2. **Quality Competition** through zero-tolerance duplicate detection
3. **Premium Zipcode Discovery** and competition (weight 4.0 multiplier)
4. **Sustainable Strategies** vs short-term gaming
5. **Network Effects** of multiple miners on overall coverage

The organic approach provides realistic validation of your subnet's incentive design!
