# 🚀 Zipcode Mining System Deployment Guide

## 📋 **Overview**

This guide provides step-by-step instructions for deploying the new zipcode-based competitive mining system for Bittensor Subnet 46. The system implements multi-tier validation with deterministic consensus to ensure all validators reach identical conclusions.

## 🏗️ **System Architecture**

### **Core Components**
- **ResiLabs API Client**: Handles zipcode assignments and miner status updates
- **Multi-Tier Validator**: Implements 3-tier validation (quantity, quality, spot-check)
- **Zipcode Competitive Scorer**: Calculates per-zipcode rewards (55%/30%/10%/5%)
- **Deterministic Consensus**: Ensures validator agreement using cryptographic verification

### **Reward Distribution**
- **1st Place per Zipcode**: 55% of zipcode weight
- **2nd Place per Zipcode**: 30% of zipcode weight  
- **3rd Place per Zipcode**: 10% of zipcode weight
- **All Other Participants**: 5% distributed equally

## 🔧 **Prerequisites**

### **System Requirements**
- Python 3.8+
- Bittensor SDK 6.0+
- 16GB+ RAM (for validators processing large datasets)
- 100GB+ storage (for S3 data caching)

### **API Access**
- **Production**: `https://api.resilabs.com`
- **Testnet**: `http://localhost:3000` (development)
- Valid Bittensor hotkey/coldkey pair for authentication

### **Dependencies**
```bash
pip install bittensor>=6.0.0 requests>=2.28.0 pandas>=1.5.0 pyarrow>=10.0.0
```

## 🏃‍♂️ **Miner Deployment**

### **Step 1: Enable Zipcode Mining**

Update your miner startup command to enable zipcode mining:

```bash
# Testnet deployment
python neurons/miner.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --zipcode_mining_enabled \
    --resi_api_url http://localhost:3000

# Mainnet deployment  
python neurons/miner.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --zipcode_mining_enabled \
    --resi_api_url https://api.resilabs.com
```

### **Step 2: Verify API Connectivity**

Check miner logs for successful API initialization:

```
✅ ResiLabs API client initialized for zipcode mining
✅ API server connected: resi-labs-api
🔄 Starting zipcode mining cycle...
```

### **Step 3: Monitor Mining Progress**

Watch for epoch detection and mining activity:

```
📍 New epoch detected: 2025-10-01T16-00-00
📊 Received 25 zipcode assignments
⛏️  Mining zipcode 19103 (target: 250 listings)
✅ Completed zipcode 19103: 245 listings
📤 Uploading epoch data to S3...
✅ Epoch 2025-10-01T16-00-00 mining completed: COMPLETED
```

### **Step 4: Troubleshooting**

Common issues and solutions:

**API Connection Failed**
```bash
# Check API health
curl https://api.resilabs.com/healthcheck

# Verify wallet configuration
python -c "import bittensor as bt; wallet = bt.wallet(name='your_wallet', hotkey='your_hotkey'); print(wallet.hotkey.ss58_address)"
```

**No Zipcode Assignments**
- Ensure miner is registered on the network
- Check if current epoch is active
- Verify hotkey has sufficient stake

## 🔍 **Validator Deployment**

### **Step 1: Enable Zipcode Validation**

Update your validator startup command:

```bash
# Testnet deployment
python neurons/validator.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --zipcode_mining_enabled \
    --resi_api_url http://localhost:3000

# Mainnet deployment
python neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --zipcode_mining_enabled \
    --resi_api_url https://api.resilabs.com
```

### **Step 2: Verify Validation System**

Check validator logs for successful initialization:

```
✅ Zipcode validation system initialized
✅ API server connected: resi-labs-api
🔄 Starting epoch validation cycle...
```

### **Step 3: Monitor Validation Process**

Watch for epoch processing and consensus:

```
📊 Processing completed epoch: 2025-10-01T16-00-00
📥 Downloading submissions for epoch 2025-10-01T16-00-00
🔍 Validating 15 submissions for zipcode 19103
✅ Winner #1 for zipcode 19103: 5H2WNbNf...
✅ Winner #2 for zipcode 19103: 5F3sa2TJ...
✅ Winner #3 for zipcode 19103: 5DvggEsd...
🧮 Calculating proportional weights across 25 zipcodes
🔐 Generated consensus hash: abc123def456...
✅ Consensus achieved: PERFECT_CONSENSUS
⚖️  Setting weights for 45 miners
```

### **Step 4: Consensus Verification**

Monitor consensus health:

```bash
# Check validator consensus logs
grep "Consensus" ~/.bittensor/validators/your_wallet/your_hotkey/netuid46/validator/logs/

# Expected output:
# ✅ Consensus achieved: PERFECT_CONSENSUS (100% agreement, 12 validators)
# ✅ All validators reached identical validation conclusion
```

## 🧪 **Testing & Validation**

### **Run Integration Tests**

Test deterministic consensus:

```bash
cd /path/to/subnet46
python tests/integration/test_deterministic_consensus.py
```

Expected output:
```
🧪 Running Deterministic Consensus Tests...
✅ All 5 validators selected identical indices: [5, 12, 23, 34, 45, 56, 67, 78, 89, 95]
✅ All 5 validators generated identical consensus hash: abc123def456...
✅ All 3 validators reached identical validation conclusion: passes_all_tiers=True
✅ All 3 validators calculated identical proportional weights
✅ Seed generation is deterministic and ungameable
✅ Consensus verification correctly identifies outliers: ['validator4']
✅ All 3 validators detected identical anti-gaming patterns: 0.0
✅ All 3 validators verified identical epoch determinism
🎉 All deterministic consensus tests passed!
```

### **Verify API Integration**

Test API connectivity:

```python
from common.resi_api_client import create_api_client
import bittensor as bt

# Initialize client
config = bt.config()
config.resi_api_url = "https://api.resilabs.com"
wallet = bt.wallet(name="your_wallet", hotkey="your_hotkey")
client = create_api_client(config, wallet)

# Test health
health = client.check_health()
print(f"API Status: {health['status']}")

# Test zipcode assignments
assignments = client.get_current_zipcode_assignments()
print(f"Current epoch: {assignments['epochId']}")
print(f"Zipcodes: {len(assignments['zipcodes'])}")
```

## 📊 **Monitoring & Metrics**

### **Key Metrics to Monitor**

**Miner Metrics**
- Epoch participation rate
- Zipcode completion rate
- Listings per zipcode
- S3 upload success rate
- API response times

**Validator Metrics**
- Consensus achievement rate
- Validation processing time
- Weight setting frequency
- Outlier detection rate

### **Monitoring Commands**

```bash
# Monitor miner performance
tail -f ~/.bittensor/miners/your_wallet/your_hotkey/netuid46/miner/logs/debug.log | grep -E "(epoch|zipcode|mining)"

# Monitor validator consensus
tail -f ~/.bittensor/validators/your_wallet/your_hotkey/netuid46/validator/logs/debug.log | grep -E "(consensus|validation|weights)"

# Check API health
watch -n 30 'curl -s https://api.resilabs.com/healthcheck | jq'
```

### **Performance Dashboards**

Monitor system health via:
- **API Statistics**: `GET /api/v1/zipcode-assignments/stats`
- **Validator Metrics**: Built-in Prometheus metrics
- **Miner Status**: API status updates

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Consensus Failures**
```
❌ Consensus failed for epoch 2025-10-01T16-00-00
Consensus rate: 67%
```

**Solutions:**
- Check validator synchronization
- Verify identical API responses
- Restart validators with consensus issues
- Check network connectivity

**2. API Authentication Errors**
```
401 Unauthorized (invalid signature)
```

**Solutions:**
- Verify wallet hotkey/coldkey
- Check timestamp synchronization
- Regenerate signatures
- Validate commitment format

**3. S3 Upload Failures**
```
Failed to get S3 upload credentials
```

**Solutions:**
- Check S3 authentication service
- Verify wallet permissions
- Retry with exponential backoff
- Check network connectivity

**4. Zipcode Assignment Issues**
```
No zipcode assignments available
```

**Solutions:**
- Check epoch timing
- Verify miner registration
- Ensure sufficient stake
- Check API server status

### **Debug Commands**

```bash
# Check miner registration
python -c "
import bittensor as bt
subtensor = bt.subtensor(network='finney')
metagraph = subtensor.metagraph(netuid=46)
wallet = bt.wallet(name='your_wallet', hotkey='your_hotkey')
uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)
print(f'UID: {uid}, Stake: {metagraph.S[uid]}')
"

# Test API signature generation
python -c "
import bittensor as bt
import time
wallet = bt.wallet(name='your_wallet', hotkey='your_hotkey')
timestamp = int(time.time())
commitment = f'zipcode:assignment:current:{timestamp}'
signature = wallet.hotkey.sign(commitment.encode()).hex()
print(f'Signature: {signature}')
"

# Verify consensus hash calculation
python -c "
from vali_utils.deterministic_consensus import DeterministicConsensus
consensus = DeterministicConsensus()
test_scores = {'miner_scores': {'test': 1.0}, 'zipcode_weights': {'19103': 1.0}, 'total_participants': 1, 'total_winners': 1, 'total_epoch_listings': 100}
hash_val = consensus.calculate_consensus_hash(test_scores, 'test_nonce')
print(f'Consensus hash: {hash_val}')
"
```

## 📈 **Performance Optimization**

### **Miner Optimization**

**Scraping Efficiency**
- Target specific zipcodes only
- Implement parallel scraping
- Cache frequently accessed data
- Use connection pooling

**S3 Upload Optimization**
- Compress data before upload
- Use multipart uploads for large files
- Implement retry logic with exponential backoff
- Monitor upload progress

### **Validator Optimization**

**Validation Performance**
- Process zipcodes in parallel
- Cache validation results
- Implement early termination for failed submissions
- Use efficient data structures

**Consensus Optimization**
- Batch consensus hash calculations
- Cache deterministic seed generation
- Optimize spot check selection
- Minimize network calls

### **System-Wide Optimization**

**Network Efficiency**
- Use HTTP/2 for API calls
- Implement request batching
- Cache API responses
- Use CDN for static data

**Resource Management**
- Monitor memory usage during validation
- Implement garbage collection
- Use streaming for large datasets
- Optimize database queries

## 🔒 **Security Considerations**

### **API Security**
- Always use HTTPS in production
- Implement rate limiting
- Validate all signatures
- Monitor for suspicious activity

### **Consensus Security**
- Verify deterministic seed generation
- Monitor for consensus manipulation
- Implement outlier detection
- Log all consensus decisions

### **Data Security**
- Encrypt sensitive data at rest
- Use secure S3 bucket policies
- Implement access logging
- Regular security audits

## 📅 **Deployment Schedule**

### **Phase 1: Testnet Deployment (Week 1)**
- Deploy API client and validation system
- Test with small validator set
- Verify consensus mechanisms
- Performance testing

### **Phase 2: Mainnet Rollout (Week 2-3)**
- Gradual validator migration
- Monitor consensus health
- Full miner deployment
- System optimization

### **Phase 3: Full Production (Week 4)**
- All validators using new system
- Complete miner migration
- Performance monitoring
- Documentation updates

## 📞 **Support & Resources**

### **Documentation**
- [API Documentation](./0044-api-documentation-for-cursor.md)
- [Implementation Plan](./0043-zipcode-validation-upgrade-plan.md)
- [Integration Requirements](./0042-upgrade-to-new-validation-requirements.md)

### **Support Channels**
- **GitHub Issues**: Technical problems and bug reports
- **Discord**: Real-time support and community discussion
- **Documentation**: Comprehensive guides and API references

### **Emergency Contacts**
- **System Outages**: Monitor API health endpoint
- **Consensus Failures**: Check validator logs and restart if needed
- **Data Issues**: Verify S3 connectivity and permissions

---

*Last Updated: October 3, 2025*  
*Version: 1.0.0*  
*Status: Ready for Deployment* 🚀
