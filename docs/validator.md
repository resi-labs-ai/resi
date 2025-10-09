# Validator

The Validator is responsible for validating the Miners' property data and scoring them according to the [incentive mechanism](../README.md#incentive-mechanism). It runs a loop to enumerate all Miners in the network, and for each, it performs the following sequence:
1. It requests the latest [MinerIndex](../README.md#terminology) from the miner, which contains their property data summary, and stores it in an in-memory database.
2. It chooses a random (sampled by size) DataEntityBucket from the MinerIndex to sample for validation.
3. It gets that DataEntityBucket containing property listings from the Miner.
4. It chooses N property DataEntities from the DataEntityBucket to validate. It then verifies the property data by cross‑referencing with Zillow using the Szill scraper.
5. It compares the retrieved property data against what the Miner provided and updates the Miner Credibility based on accuracy.
6. Finally, it updates the Miner's score based on the total property data index scaled by Freshness/Desirability/Geographic Coverage/Credibility.

Once this sequence has been performed for all Miners, the Validator waits a period of time before starting the next loop to ensure it does not evaluate a Miner more often than once per N minutes. This helps ensure the operational cost of running a Validator is not too high, and also protects the network against high amounts of traffic.

The expected cost for property data validation depends on: `Number of Miners * validation frequency * samples per validation * 24 hours`. With scraper-based validation via Szill, costs are driven by compute, bandwidth, and proxy usage rather than third‑party API fees.

# System Requirements

Validators require at least 32 GB of RAM but do not require a GPU. We recommend a decent CPU (4+ cores) and sufficient network bandwidth to handle protocol traffic. Must have python >= 3.10.

# Getting Started

## Network Selection

### Testnet (Subnet 428) - Development & Testing
Testnet validation is ideal for:
- Learning validator operations without real TAO costs
- Testing configuration and setup
- Development and debugging
- Validating against miners with 5-minute upload frequency

**Testnet Features:**
- Lower operational costs for testing
- Faster data refresh cycles from miners
- Auto-configured testnet endpoints
- Safe environment for experimentation

### Mainnet (Subnet 46) - Production Environment
Mainnet validation for production:
- Real TAO rewards for validation work
- Production-grade validation requirements
- Standard miner upload cycles (2 hours)
- Full network economic participation

## Prerequisites

### Scraper Requirements (Validator)

Validators use the Szill-based Zillow scraper for validation. Ensure your environment meets the following:

- Python dependencies installed via `pip install -e .`
- **REQUIRED for Mainnet**: Proxy configuration to avoid IP blocking during validation
- **Recommended**: ScrapingBee API for reliable, professional scraping

#### Proxy Configuration (REQUIRED for Production)

Choose one of the following proxy options:

**Option 1: ScrapingBee API (Recommended)**
```bash
# Set environment variable
export SCRAPINGBEE_API_KEY="your_api_key_here"

# Run validator with ScrapingBee
python neurons/validator.py --netuid 13 --use_scrapingbee
```

**Option 2: Traditional HTTP Proxy**
```bash
# Run validator with traditional proxy
python neurons/validator.py --netuid 13 --proxy_url "http://user:pass@proxy:port"
```

**📖 Complete Proxy Setup Guide**: See [PROXY_CONFIGURATION.md](./PROXY_CONFIGURATION.md) for detailed configuration instructions.
- Sufficient bandwidth and stable network connectivity

If proxies are used, configure them via environment variables specific to your proxy provider or Szill settings (see comments in code under `vali_utils/scrapers/szill_zillow_scraper.py`).

2. Clone the repo

```shell
git clone https://github.com/resi-labs-ai/resi.git
```

3. Setup your python [virtual environment](https://docs.python.org/3/library/venv.html) or [Conda environment](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-with-commands).

4. Install the requirements. From your virtual environment, run
```shell
cd resi
python -m pip install -e .

pip install bittensor
pip install bittensor-cli
```

5. Make sure you've [created a Wallet](https://docs.bittensor.com/getting-started/wallets) and [registered a hotkey](https://docs.bittensor.com/subnets/register-and-participate).

6. (Optional) Set up Weights & Biases for monitoring:
```shell
wandb login
```

This will prompt you to navigate to https://wandb.ai/authorize and copy your api key back into the terminal.

## Running the Validator

### Environment Configuration

**Step 1: Configure Environment**
Update your `.env` file based on your target network:

```shell
# For Testnet (Subnet 428)
NETUID=428
SUBTENSOR_NETWORK=test
WALLET_NAME=your_testnet_validator_wallet
WALLET_HOTKEY=your_testnet_validator_hotkey

# For Mainnet (Subnet 46)
NETUID=46
SUBTENSOR_NETWORK=finney
WALLET_NAME=your_mainnet_validator_wallet
WALLET_HOTKEY=your_mainnet_validator_hotkey
```

If you are using proxies for validation scraping, add the relevant environment variables required by your proxy provider.

**Step 2: Register Validator (if needed)**
```shell
# Testnet registration
btcli subnet register --netuid 428 --subtensor.network test \
    --wallet.name your_testnet_validator_wallet \
    --wallet.hotkey your_testnet_validator_hotkey

# Mainnet registration
btcli subnet register --netuid 46 --subtensor.network finney \
    --wallet.name your_mainnet_validator_wallet \
    --wallet.hotkey your_mainnet_validator_hotkey
```

### Starting the Validator

#### Testnet Validation
```shell
# Start testnet validator
pm2 start python --name testnet-validator -- ./neurons/validator.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_testnet_validator_wallet \
    --wallet.hotkey your_testnet_validator_hotkey \
    --logging.debug \
    --max_targets 10
```

#### Mainnet Validation

**With auto-updates (Recommended for Production)**

We highly recommend running the validator with auto-updates. This will help ensure your validator is always running the latest release, helping to maintain a high vtrust.

Prerequisites:
1. To run with auto-update, you will need to have [pm2](https://pm2.keymetrics.io/) installed.
2. Make sure your virtual environment is activated. This is important because the auto-updater will automatically update the package dependencies with pip.
3. Make sure you're using the main branch: `git checkout main`.

From the resi folder:
```shell
pm2 start --name net46-vali-updater --interpreter python scripts/start_validator.py -- \
    --pm2_name net46-vali \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_validator_wallet \
    --wallet.hotkey your_mainnet_validator_hotkey
```

This will start a process called `net46-vali-updater`. This process periodically checks for a new git commit on the current branch. When one is found, it performs a `pip install` for the latest packages, and restarts the validator process (whose name is given by the `--pm2_name` flag).

**Without auto-updates**

If you'd prefer to manage your own validator updates:

```shell
pm2 start python --name mainnet-validator -- ./neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_validator_wallet \
    --wallet.hotkey your_mainnet_validator_hotkey \
    --max_targets 256
```

# Configuring the Validator

## Flags

The Validator offers some flags to customize properties.

You can view the full set of flags by running
```shell
python ./neurons/validator.py -h
```

## `.env`

Your validator `.env` should look like the following after setup for real estate data validation:

```
# Network
NETUID=46
SUBTENSOR_NETWORK=finney
WALLET_NAME="your_wallet"
WALLET_HOTKEY="your_hotkey"

# Optional proxy settings for Szill scraper
# PROXY_HOST=...
# PROXY_PORT=...
# PROXY_USER=...
# PROXY_PASS=...
```

The validator uses the Szill-based scraper to validate property data against Zillow.

# Monitoring and Validation

## Validator Health Monitoring

### Check Validator Status
```shell
# Check validator registration and stake
btcli wallet overview --wallet.name your_validator_wallet --subtensor.network test    # Testnet
btcli wallet overview --wallet.name your_validator_wallet --subtensor.network finney  # Mainnet

# View subnet metagraph
btcli subnet metagraph --netuid 428 --subtensor.network test    # Testnet
btcli subnet metagraph --netuid 46 --subtensor.network finney   # Mainnet
```

### Monitor Validator Logs
```shell
# Watch validator logs in real-time
pm2 logs testnet-validator --lines 100 --follow   # Testnet
pm2 logs mainnet-validator --lines 100 --follow   # Mainnet
pm2 logs net46-vali-updater --lines 100 --follow  # Mainnet with auto-updates

# Or direct log monitoring
tail -f logs/validator.log

# Monitor validation activity specifically
pm2 logs testnet-validator --lines 100 --follow | grep -E "(validation|miner|score|weight)"

# Check PM2 process status
pm2 status
pm2 info testnet-validator  # or mainnet-validator

# Restart validator if needed
pm2 restart testnet-validator  # or mainnet-validator
pm2 stop testnet-validator     # or mainnet-validator
```

## Important Flags Reference

### **Required Flags:**
- `--netuid`: 428 (testnet) or 46 (mainnet)
- `--subtensor.network`: "test" (testnet) or "finney" (mainnet)
- `--wallet.name`: Your validator wallet name
- `--wallet.hotkey`: Your validator hotkey name

### **Validation Control Flags:**
- `--max_targets`: Maximum miners to validate per cycle (10 for testnet, 256 for mainnet)
- `--neuron.disable_set_weights`: Disable weight setting (for testing)
- `--organic_min_stake`: Minimum stake required for organic requests (default: 10000.0)

### **API and Monitoring Flags:**
- `--neuron.api_on`: Enable validator API server
- `--neuron.api_port`: API server port (default: 8000)
- `--wandb.off`: Disable Weights & Biases logging (disabled by default)
- `--wandb.on`: Enable Weights & Biases logging (overrides --wandb.off)

### **Common Optional Flags:**
- `--logging.debug`: Enable debug logging
- `--neuron.axon_off`: Disable serving axon (not recommended)
- `--s3_results_path`: Custom S3 validation results path

### **Example Commands by Use Case:**

**Development/Testing Validator:**
```shell
pm2 start python --name dev-validator -- ./neurons/validator.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name dev_validator_wallet \
    --wallet.hotkey dev_validator_hotkey \
    --logging.debug \
    --max_targets 5
```

**Production Mainnet Validator:**
```shell
pm2 start python --name prod-validator -- ./neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name production_validator_wallet \
    --wallet.hotkey production_validator_hotkey \
    --max_targets 256 \
    --neuron.api_on \
    --neuron.api_port 8000
```

### Expected Validator Behavior

**Testnet Validation Cycle:**
- Miners upload data every 5 minutes
- More frequent data refresh for validation
- Faster iteration for testing and development
- Lower validation costs due to test environment

**Mainnet Validation Cycle:**
- Miners upload data every 2 hours
- Standard production validation frequency
- Full economic validation with real rewards
- Production-level validation costs

## Performance Metrics

### Key Validator Metrics to Monitor
1. **Validation Success Rate**: Percentage of successful miner validations
2. **Scraper Reliability**: Monitor scraper success/timeout rates
3. **Weight Setting**: Ensure weights are being set properly
4. **Miner Coverage**: Number of miners successfully validated per cycle
5. **Network Connectivity**: Connection stability to subtensor

### Troubleshooting Common Issues

**Scraper failures/timeouts:**
```shell
# Verify network and proxy settings
# Reduce concurrency if being blocked
# Increase timeouts where appropriate
```

**Network Connection Issues:**
```shell
# Test subtensor connectivity
btcli subnet list --subtensor.network test    # Testnet
btcli subnet list --subtensor.network finney  # Mainnet

# Check firewall settings for bittensor ports
# Verify network stability and bandwidth
```

**Weight Setting Failures:**
```shell
# Check validator registration status
btcli wallet overview --wallet.name your_validator

# Verify sufficient stake for weight setting
# Monitor logs for weight setting errors
```

## Success Indicators

✅ **Regular Validation Cycles**: Consistent miner evaluation and scoring
✅ **Successful Weight Setting**: Weights updated on blockchain regularly
✅ **Stable Scraper Reliability**: Szill scraper runs within acceptable failure rates
✅ **Network Participation**: Active participation in consensus
✅ **Clean Logs**: No persistent errors or connection issues

## Cost Management

### Estimating Validation Costs

**Formula**: `Number of Miners × Validation Frequency × Samples per Validation`

Costs are primarily compute, bandwidth, and optional proxy usage. No third‑party API subscription is required.

# Network-Specific Considerations

## Testnet vs Mainnet Validation Differences

### Data Refresh Rates
- **Testnet**: Miners upload every 5 minutes, enabling more frequent validation
- **Mainnet**: Standard 2-hour upload cycles, requiring patience for data updates

### Validation Strategy
- **Testnet**: Experiment with validation parameters and strategies
- **Mainnet**: Use proven, stable validation approaches

### Economic Impact
- **Testnet**: No real economic consequences, focus on learning
- **Mainnet**: Real TAO rewards and costs, optimize for profitability

## Switching Between Networks

To switch from testnet to mainnet validation:

1. **Update Environment Configuration**:
   - Change `NETUID` from 428 to 46
   - Change `SUBTENSOR_NETWORK` from "test" to "finney"
   - Update wallet names to mainnet wallets

2. **Register New Validator** (if using different wallet):
   ```shell
   btcli subnet register --netuid 46 --subtensor.network finney \
       --wallet.name your_mainnet_validator_wallet \
       --wallet.hotkey your_mainnet_validator_hotkey
   ```

3. **Update Monitoring and Alerting**:
   - Adjust for 2-hour validation cycles
   - Monitor scraper reliability and timeouts
   - Implement production-grade monitoring

# Coming Soon

We are working hard to add more features to RESI. For the Validators, we have plans to:

1. Have the Validator serve an Axon on the network, so neurons on other Subnets can retrieve property data.
2. Add scrapers for additional real estate DataSources (county assessors, MLS feeds, public records).
3. Implement more cost-effective validation methods while maintaining data accuracy.
4. Add support for commercial property data validation.
5. Expand to international property markets.
6. Enhanced validation tools and monitoring dashboards.
7. Automated cost optimization and quota management.
