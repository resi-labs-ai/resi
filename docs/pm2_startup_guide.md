# 🚀 **PM2 Startup Guide - Updated Instructions**

## 📋 **Summary of Changes Made**

The miner and validator documentation has been **completely updated** to include all the flags from your previous testnet commands and ensure they work correctly for both testnet and mainnet.

## ✅ **What Was Fixed/Updated:**

### **1. Added Missing max_targets Flag**
- **Issue**: `--max_targets` flag was missing from config.py
- **Fix**: Added to validator configuration with default value of 256
- **Your Command**: `--max_targets 10` ✅ **Now Supported**

### **2. Corrected Miner S3 Upload Flags**
- **Issue**: Missing S3 upload configuration flags
- **Fix**: Added `--use_uploader`, `--neuron.database_name`, `--miner_upload_state_file`
- **Your Command**: All flags from your previous command ✅ **Now Included**

### **3. Added PM2 Process Names**
- **Issue**: No process names for easier management
- **Fix**: Added `--name` flags for better PM2 process identification
- **Benefit**: Easy to identify and manage processes with `pm2 status`

### **4. Updated Environment Variables**
- **Issue**: Missing RapidAPI configuration in .env examples
- **Fix**: Added complete .env examples with all required variables

## 🔄 **Comparison: Your Previous vs Updated Instructions**

### **Your Previous Testnet Miner Command:**
```bash
python neurons/miner.py \
  --netuid 428 \
  --subtensor.network test \
  --wallet.name testnet_miner_3 \
  --wallet.hotkey hotkey_3 \
  --use_uploader \
  --logging.debug \
  --neuron.database_name SqliteMinerStorage_miner3.sqlite \
  --miner_upload_state_file upload_utils/state_file_miner3.json
```

### **Updated PM2 Testnet Miner Command:**
```bash
pm2 start python --name testnet-miner -- ./neurons/miner.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_testnet_wallet \
    --wallet.hotkey your_testnet_hotkey \
    --use_uploader \
    --logging.debug \
    --neuron.database_name SqliteMinerStorage_testnet.sqlite \
    --miner_upload_state_file upload_utils/state_file_testnet.json
```

### **Your Previous Testnet Validator Command:**
```bash
python neurons/validator.py \
  --netuid 428 \
  --subtensor.network test \
  --wallet.name 428_testnet_validator \
  --wallet.hotkey 428_testnet_validator_hotkey \
  --logging.debug \
  --max_targets 10
```

### **Updated PM2 Testnet Validator Command:**
```bash
pm2 start python --name testnet-validator -- ./neurons/validator.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_testnet_validator_wallet \
    --wallet.hotkey your_testnet_validator_hotkey \
    --logging.debug \
    --max_targets 10
```

## 🎯 **Ready-to-Use Commands**

### **Testnet Setup:**

#### **Miner:**
```bash
pm2 start python --name testnet-miner -- ./neurons/miner.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_testnet_wallet \
    --wallet.hotkey your_testnet_hotkey \
    --use_uploader \
    --logging.debug \
    --neuron.database_name SqliteMinerStorage_testnet.sqlite \
    --miner_upload_state_file upload_utils/state_file_testnet.json
```

#### **Validator:**
```bash
pm2 start python --name testnet-validator -- ./neurons/validator.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_testnet_validator_wallet \
    --wallet.hotkey your_testnet_validator_hotkey \
    --logging.debug \
    --max_targets 10
```

### **Mainnet Setup:**

#### **Miner:**
```bash
pm2 start python --name mainnet-miner -- ./neurons/miner.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_wallet \
    --wallet.hotkey your_mainnet_hotkey \
    --use_uploader \
    --neuron.database_name SqliteMinerStorage_mainnet.sqlite \
    --miner_upload_state_file upload_utils/state_file_mainnet.json
```

#### **Validator:**
```bash
pm2 start python --name mainnet-validator -- ./neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_validator_wallet \
    --wallet.hotkey your_mainnet_validator_hotkey \
    --max_targets 256
```

## 📊 **PM2 Management Commands**

```bash
# Check status of all processes
pm2 status

# View logs
pm2 logs testnet-miner --lines 100 --follow
pm2 logs testnet-validator --lines 100 --follow
pm2 logs mainnet-miner --lines 100 --follow
pm2 logs mainnet-validator --lines 100 --follow

# Restart processes
pm2 restart testnet-miner
pm2 restart testnet-validator
pm2 restart mainnet-miner
pm2 restart mainnet-validator

# Stop processes
pm2 stop testnet-miner
pm2 stop testnet-validator

# Delete processes
pm2 delete testnet-miner
pm2 delete testnet-validator
```

## 🔧 **Required .env Configuration**

Create/update your `.env` file:

```bash
# Network Configuration
NETUID=428                    # 428 for testnet, 46 for mainnet
SUBTENSOR_NETWORK=test        # "test" for testnet, "finney" for mainnet

# Wallet Configuration
WALLET_NAME=your_wallet_name
WALLET_HOTKEY=your_hotkey_name

# API Configuration (Required)
RAPIDAPI_KEY=your_rapidapi_key_here
RAPIDAPI_HOST=zillow-com1.p.rapidapi.com
```

## ✅ **Verification Steps**

1. **Check PM2 Status**: `pm2 status` should show your processes
2. **Monitor Logs**: `pm2 logs [process-name]` should show activity
3. **Check Wallet Registration**: `btcli wallet overview --wallet.name your_wallet`
4. **Verify S3 Uploads** (miners): Look for "S3 partitioned upload completed successfully"
5. **Verify Validation** (validators): Look for miner validation activities

## 🚨 **Key Differences from Original Docs**

### **✅ What's Now Correct:**
- All your testnet flags are supported and documented
- `--max_targets` flag is properly defined
- S3 upload flags are included and explained
- PM2 process names for easy management
- Complete environment variable examples
- Monitoring and troubleshooting commands

### **🔧 What Was Missing Before:**
- `--max_targets` flag definition
- Complete S3 upload flag documentation
- PM2 process naming
- Comprehensive flag reference sections
- Environment variable examples with RapidAPI

## 🎉 **Result**

**All instructions in `miner.md` and `validator.md` are now correct and up-to-date!**

- ✅ **Your previous commands work perfectly**
- ✅ **All flags are properly supported**
- ✅ **Mainnet instructions include all necessary flags**
- ✅ **PM2 process management is streamlined**
- ✅ **Environment configuration is complete**

**You can now confidently use the documentation for both testnet and mainnet deployments! 🚀**
