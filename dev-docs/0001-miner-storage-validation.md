# 🔍 Miner Storage Validation Guide

**Document**: 0001-miner-storage-validation.md  
**Created**: 2025-09-10  
**Purpose**: Validate that miners are properly configured for both local storage and S3 uploads

This guide helps you validate that your miners are properly configured for both local storage and S3 uploads.

## 🚀 Quick Start

### For Testnet (Subnet 428)
```bash
# Quick health check
python tools/check_miner_storage.py --netuid 428

# Full validation with S3 auth test
python tools/validate_miner_storage.py --netuid 428 \
    --wallet.name your_testnet_wallet \
    --wallet.hotkey your_testnet_hotkey \
    --subtensor.network test
```

### For Mainnet (Subnet 46)
```bash
# Quick health check
python tools/check_miner_storage.py --netuid 46

# Full validation with S3 auth test
python tools/validate_miner_storage.py --netuid 46 \
    --wallet.name your_mainnet_wallet \
    --wallet.hotkey your_mainnet_hotkey
```

## 📋 What Gets Validated

### ✅ **Local Storage**
- **Database File**: Checks if `SqliteMinerStorage.sqlite` exists
- **Table Structure**: Validates DataEntity table and columns
- **Data Content**: Shows recent data entries and counts
- **Database Size**: Monitors size vs configured limits

### ☁️ **S3 Configuration**
- **Auth URL**: Validates correct endpoint for testnet vs mainnet
- **Service Health**: Tests if S3 auth service is reachable
- **Upload Frequency**: Confirms expected timing (5 min testnet, 2 hours mainnet)

### 🔐 **S3 Authentication**
- **Credential Retrieval**: Tests actual S3 credential fetching
- **Wallet Verification**: Validates blockchain authentication
- **Bucket Access**: Confirms proper S3 bucket permissions

### 📤 **Upload State**
- **State Files**: Checks for upload tracking files
- **Job Progress**: Shows which data jobs have been processed
- **Upload History**: Displays recent upload activity

## 🔧 **Changes Made**

### 1. **Upload Frequency Modified** ⏰
**File**: `neurons/miner.py:252-260`

```python
# Upload frequency based on network
if self.config.netuid == 428:  # Testnet
    # Upload every 5 minutes for testnet
    time_sleep_val = dt.timedelta(minutes=5).total_seconds()
    bt.logging.info("Using testnet upload frequency: 5 minutes")
else:  # Mainnet
    # Upload every 2 hours for mainnet
    time_sleep_val = dt.timedelta(hours=2).total_seconds()
    bt.logging.info("Using mainnet upload frequency: 2 hours")
```

### 2. **Auto S3 URL Configuration** 🔗
**File**: `neurons/miner.py:69-77`

```python
# Auto-configure S3 auth URL based on subnet
if self.config.netuid == 428:  # Testnet
    if self.config.s3_auth_url == "https://sn46-s3-auth.resilabs.ai":  # Default mainnet URL
        self.config.s3_auth_url = "https://s3-auth-api-testnet.resilabs.ai"
        bt.logging.info(f"Auto-configured testnet S3 auth URL: {self.config.s3_auth_url}")
else:  # Mainnet or other subnets
    if not hasattr(self.config, 's3_auth_url') or not self.config.s3_auth_url:
        self.config.s3_auth_url = "https://s3-auth-api.resilabs.ai"
        bt.logging.info(f"Auto-configured mainnet S3 auth URL: {self.config.s3_auth_url}")
```

## 📊 **Expected Behavior**

### **Testnet (Subnet 428)**
- ⏰ **Upload Frequency**: Every 5 minutes
- 🔗 **S3 Auth URL**: `https://s3-auth-api-testnet.resilabs.ai`
- 💾 **Local Storage**: `SqliteMinerStorage.sqlite`
- 📁 **S3 Structure**: `hotkey={hotkey}/job_id={job_id}/data_*.parquet`

### **Mainnet (Subnet 46)**
- ⏰ **Upload Frequency**: Every 2 hours
- 🔗 **S3 Auth URL**: `https://s3-auth-api.resilabs.ai`
- 💾 **Local Storage**: `SqliteMinerStorage.sqlite`
- 📁 **S3 Structure**: `hotkey={hotkey}/job_id={job_id}/data_*.parquet`

## 🔍 **Manual Verification**

### Check Local Database
```bash
# Connect to SQLite database
sqlite3 SqliteMinerStorage.sqlite

# Check data count
SELECT COUNT(*) FROM DataEntity;

# View recent entries
SELECT source, label, datetime, LENGTH(content) as size 
FROM DataEntity 
ORDER BY datetime DESC 
LIMIT 10;

# Check database size
SELECT page_count * page_size / 1024.0 / 1024.0 as size_mb 
FROM pragma_page_count(), pragma_page_size();
```

### Monitor Upload Logs
```bash
# Watch miner logs for upload activity
tail -f logs/miner.log | grep -E "(S3|upload|partitioned)"

# Look for these log messages:
# - "Using testnet upload frequency: 5 minutes"
# - "Auto-configured testnet S3 auth URL"
# - "Starting S3 partitioned upload for DD data"
# - "S3 partitioned upload completed successfully"
```

### Check Upload State
```bash
# View upload state file
cat upload_utils/state_file_s3_partitioned.json | jq '.'

# Check for job progress
ls -la s3_partitioned_storage/*/
```

## 🚨 **Troubleshooting**

### ❌ **Database Not Found**
```bash
# Check if miner is running and scraping
ps aux | grep miner
ls -la SqliteMinerStorage.sqlite*
```

### ❌ **S3 Auth Failures**
```bash
# Test S3 auth endpoint manually
curl -X GET "https://s3-auth-api-testnet.resilabs.ai/healthcheck"

# Check wallet registration
btcli wallet overview --wallet.name your_wallet --subtensor.network test
```

### ❌ **No Upload Activity**
```bash
# Check if uploader is enabled
grep "use_uploader" logs/miner.log

# Verify upload thread is running
grep "s3_partitioned_thread" logs/miner.log
```

## 📈 **Monitoring Upload Progress**

### Expected Timeline (Testnet)
- **First Upload**: 30 minutes after miner start
- **Subsequent Uploads**: Every 5 minutes
- **Data Processing**: Continuous (based on scraping activity)

### S3 Bucket Structure
```
bucket-name/
└── hotkey=5ABC123.../
    ├── job_id=job_001/
    │   ├── data_20250910_120000_1500.parquet
    │   └── data_20250910_120500_890.parquet
    └── job_id=job_002/
        └── data_20250910_120000_2100.parquet
```

## 🎯 **Success Indicators**

### ✅ **Local Storage Working**
- Database file exists and grows over time
- Recent data entries visible
- No database corruption errors

### ✅ **S3 Uploads Working**
- Upload state file shows job progress
- S3 auth service returns credentials
- Upload logs show successful transfers

### ✅ **Correct Configuration**
- Testnet uses 5-minute intervals
- Correct S3 auth URL for network
- No authentication errors

## 🔗 **API Endpoints Reference**

### **Testnet S3 Auth API**
- **Base URL**: `https://s3-auth-api-testnet.resilabs.ai`
- **Health**: `GET /healthcheck`
- **Miner Access**: `POST /get-folder-access`

### **Mainnet S3 Auth API**
- **Base URL**: `https://s3-auth-api.resilabs.ai`
- **Health**: `GET /healthcheck`
- **Miner Access**: `POST /get-folder-access`

---

## 🎉 **Ready to Test!**

Your miners are now configured with:
- ⚡ **5-minute uploads for testnet** (down from 2 hours)
- 🔗 **Automatic S3 URL selection** based on subnet
- 🔍 **Comprehensive validation tools**

Run the validation script to confirm everything is working correctly!
