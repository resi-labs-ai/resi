# Validator

The Validator evaluates miners by validating their property data against external sources and scoring them based on data quality and quantity. The validator:

1. **Discovers miners** on the Bittensor network
2. **Requests data samples** from miners for validation
3. **Validates data** by cross-referencing with external sources like Zillow
4. **Scores miners** based on data accuracy, freshness, and completeness
5. **Sets weights** to distribute rewards to high-performing miners

Validators use scraping tools to verify miner data and maintain network consensus on data quality.

# System Requirements

Validators require at least 8 GB of RAM but do not require a GPU. We recommend a decent CPU (2+ cores) and sufficient network bandwidth to handle protocol traffic. Must have python >= 3.10.

# Getting Started

## Network Selection

### Testnet (Subnet 428) - Development & Testing
Testnet validation is ideal for:
- Learning validator operations without real TAO costs
- Testing configuration and setup
- Development and debugging

**Testnet Features:**
- Lower operational costs for testing
- Faster data refresh cycles from miners
- Safe environment for experimentation

### Mainnet (Subnet 46) - Production Environment
Mainnet validation for production:
- Real TAO rewards for validation work
- Production-grade validation requirements
- Full network economic participation

## Prerequisites

1. **Python >= 3.10** and virtual environment setup
2. **Bittensor wallet** with registered hotkey and validator registration
3. **Network connectivity** and sufficient RAM (32GB+ recommended)
4. **Proxy configuration** for production validation (recommended)

### Installation

```shell
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Verify installation
python -c "import bittensor as bt; print('Bittensor installed successfully')"
```

## Running the Validator

### Registration and Setup

**Step 1: Register Validator (if needed)**
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

**Step 2: Start Validation**

Use [pm2](https://pm2.keymetrics.io/) to manage the validator process.

**Testnet Validation:**
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

**Mainnet Validation:**
```shell
# Start mainnet validator
pm2 start python --name mainnet-validator -- ./neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_validator_wallet \
    --wallet.hotkey your_mainnet_validator_hotkey \
    --max_targets 256 \
    --logging.debug
```

**With Proxy Support (Recommended for Production):**
```shell
# Mainnet validator with ScrapingBee proxy
pm2 start python --name mainnet-validator -- ./neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_validator_wallet \
    --wallet.hotkey your_mainnet_validator_hotkey \
    --use_scrapingbee \
    --max_targets 256
```

**With Traditional Proxy:**
```shell
# Mainnet validator with traditional proxy
pm2 start python --name mainnet-validator -- ./neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_validator_wallet \
    --wallet.hotkey your_mainnet_validator_hotkey \
    --proxy_url "http://username:password@proxy-server:port" \
    --max_targets 256
```

# Configuring the Validator

## Available Flags

The Validator supports the following key configuration flags:

### **Required Flags:**
- `--netuid`: 428 (testnet) or 46 (mainnet)
- `--subtensor.network`: "test" (testnet) or "finney" (mainnet)
- `--wallet.name`: Your validator wallet name
- `--wallet.hotkey`: Your validator hotkey name

### **Validation Control Flags:**
- `--max_targets`: Maximum miners to validate per cycle (10 for testnet, 256 for mainnet)
- `--neuron.disable_set_weights`: Disable weight setting (for testing)
- `--organic_min_stake`: Minimum stake required for organic requests (default: 10000.0)

### **Proxy and Scraping Flags:**
- `--use_scrapingbee`: Use ScrapingBee API for validation scraping (requires API key)
- `--proxy_url`: Traditional HTTP proxy URL for scraping
- `--proxy_username`: Proxy authentication username
- `--proxy_password`: Proxy authentication password

### **Optional Flags:**
- `--logging.debug`: Enable debug logging
- `--neuron.axon_off`: Disable serving axon (not recommended)
- `--wandb.off`: Disable Weights & Biases logging (default: disabled)
- `--wandb.on`: Enable Weights & Biases logging
- `--neuron.api_on`: Enable validator API server
- `--neuron.api_port`: API server port (default: 8000)

# Monitoring and Management

## Basic Monitoring

### Check Validator Status
```shell
# Check validator registration and stake
btcli wallet overview --wallet.name your_validator_wallet --subtensor.network test    # Testnet
btcli wallet overview --wallet.name your_validator_wallet --subtensor.network finney  # Mainnet

# View subnet metagraph
btcli subnet metagraph --netuid 428 --subtensor.network test    # Testnet
btcli subnet metagraph --netuid 46 --subtensor.network finney   # Mainnet

# Check PM2 process status
pm2 status
pm2 info testnet-validator  # or mainnet-validator
```

### Monitor Validator Logs
```shell
# Watch validator logs in real-time
pm2 logs testnet-validator --lines 100 --follow   # Testnet
pm2 logs mainnet-validator --lines 100 --follow   # Mainnet

# Monitor validation activity
pm2 logs testnet-validator --lines 100 --follow | grep -E "(validation|miner|score|weight)"

# Restart validator if needed
pm2 restart testnet-validator  # or mainnet-validator
pm2 stop testnet-validator     # or mainnet-validator
```