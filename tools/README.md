# 🛠️ Validation and Diagnostic Tools

This directory contains operational tools for validating, monitoring, and diagnosing miner functionality.

## 📋 Available Tools

### 🔍 `check_miner_storage.py`
**Quick operational health check for miner storage**

- **Purpose**: Fast validation of miner storage and S3 configuration
- **Dependencies**: Minimal (no bittensor required)
- **Use Case**: Quick health checks, monitoring, troubleshooting

**Usage:**
```bash
# Testnet validation
python tools/check_miner_storage.py --netuid 428

# Mainnet validation  
python tools/check_miner_storage.py --netuid 46

# Custom database path
python tools/check_miner_storage.py --netuid 428 --database path/to/custom.sqlite
```

**What it checks:**
- ✅ Local SQLite database existence and health
- ✅ S3 configuration and endpoint reachability  
- ✅ Upload state files and job progress
- ✅ Recent log entries (if available)

### 🔬 `validate_miner_storage.py`
**Comprehensive validation with full bittensor integration**

- **Purpose**: Complete system validation including S3 authentication
- **Dependencies**: Full bittensor stack, S3Auth, storage classes
- **Use Case**: Thorough testing, integration validation, development

**Usage:**
```bash
# Basic validation
python tools/validate_miner_storage.py --netuid 428

# Full validation with S3 auth test
python tools/validate_miner_storage.py --netuid 428 \
    --wallet.name your_testnet_wallet \
    --wallet.hotkey your_testnet_hotkey \
    --subtensor.network test
```

**What it validates:**
- ✅ All checks from `check_miner_storage.py`
- ✅ S3 credential retrieval and authentication
- ✅ Wallet verification and blockchain connectivity
- ✅ Bucket access permissions
- ✅ Complete upload workflow testing

## 🎯 When to Use Which Tool

### Use `check_miner_storage.py` for:
- 🚀 **Quick health checks** before starting miners
- 📊 **Monitoring** running systems
- 🔧 **Troubleshooting** basic issues
- 🤖 **Automated monitoring** (CI/CD, cron jobs)

### Use `validate_miner_storage.py` for:
- 🔬 **Comprehensive testing** during development
- 🔐 **S3 authentication** verification
- 🧪 **Integration testing** with full stack
- 📋 **Pre-deployment validation**

## 📊 Expected Output Examples

### ✅ Healthy System (Testnet)
```
🔍 Miner Storage Quick Check
============================================================

🗄️  Checking Local Database: SqliteMinerStorage.sqlite
==================================================
✅ Database file exists (21.21 MB)
✅ DataEntity table exists
📊 Total records: 4,243

☁️  Checking S3 Configuration
==================================================
🌐 Network: Testnet (Subnet 428)
✅ S3 auth service is reachable

📋 Summary
==============================
✅ All checks passed (4/4)
🎉 Testnet miner storage looks good!
⏰ Uploads should happen every 5 minutes
```

### ⚠️ Issues Detected
```
🔍 Miner Storage Quick Check
============================================================

🗄️  Checking Local Database: SqliteMinerStorage.sqlite
==================================================
❌ Database file not found: SqliteMinerStorage.sqlite

☁️  Checking S3 Configuration
==================================================
❌ Cannot reach S3 auth service: Connection timeout

📋 Summary
==============================
⚠️  2/4 checks passed
🔧 Review the issues above
```

## 🔗 Related Documentation

- **Setup Guide**: `dev-docs/0001-miner-storage-validation.md`
- **Unit Tests**: `tests/storage/miner/test_sqlite_miner_storage.py`
- **Integration Tests**: `tests/integration/`

## 🚀 Quick Start

```bash
# 1. Quick health check
python tools/check_miner_storage.py --netuid 428

# 2. If issues found, run comprehensive validation
python tools/validate_miner_storage.py --netuid 428 \
    --wallet.name your_wallet --wallet.hotkey your_hotkey

# 3. Check logs for more details
tail -f logs/miner.log | grep -E "(S3|upload|storage)"
```

---

*These tools complement the existing unit tests in `tests/` by providing operational validation of running systems.*
