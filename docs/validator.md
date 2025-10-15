# Validator

## System Requirements

Validators will require a minimum of:
- **CPU**: 4 cores
- **RAM**: 8 GB
- Sufficient network bandwidth to handle protocol traffic.

## Prerequisites

1. **Python >= 3.10** and virtual environment setup
2. **Bittensor wallet** with registered hotkey and validator registration
3. **Network connectivity** with sufficient network bandwidth
4. **Proxy configuration**  (recommended)

## Installation

```shell
# Clone the repository
git clone https://github.com/resi-labs-ai/resi.git
cd resi

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Running the Validator

### Registration and Setup

**Step 1: Register Validator (if needed).**
For installation of btcli, [use this guide](https://github.com/opentensor/bittensor/blob/master/README.md#install-bittensor-sdk)
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
**Step 2: Configure Environment Variables**
Configure your `.env` file (example `.env` provided)

**Step 3: Start Validation**

### Install pm2 (if not already installed)
```bash
npm install -g pm2
```

**Running on testnet:**
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

**Running on mainnet:**
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
See [Proxy Configuration Guide](PROXY_CONFIGURATION.md) for setup details.
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

## Configuring the Validator

The Validator supports the following key configuration flags:

### Required Flags:
- `--netuid`: 428 (testnet) or 46 (mainnet)
- `--subtensor.network`: "test" (testnet) or "finney" (mainnet)
- `--wallet.name`: Your validator wallet name
- `--wallet.hotkey`: Your validator hotkey name

### Validation Control Flags:
- `--max_targets`: Maximum miners to validate per cycle (10 for testnet, 256 for mainnet)
- `--neuron.disable_set_weights`: Disable weight setting (for testing)
- `--organic_min_stake`: Minimum stake required for organic requests (default: 10000.0)

### Proxy and Scraping Flags:
- `--use_scrapingbee`: Use ScrapingBee API for validation scraping (requires API key)
- `--proxy_url`: Traditional HTTP proxy URL for scraping
- `--proxy_username`: Proxy authentication username
- `--proxy_password`: Proxy authentication password

### Optional Flags:
- `--logging.debug`: Enable debug logging
- `--neuron.axon_off`: Disable serving axon (not recommended)
- `--wandb.off`: Disable Weights & Biases logging (default: disabled)
- `--wandb.on`: Enable Weights & Biases logging
- `--neuron.api_on`: Enable validator API server
- `--neuron.api_port`: API server port (default: 8000)

## Monitoring and Management

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

## Auto-Start on System Boot

Configure pm2 to automatically restart your validator after system reboots:

```shell
# Save current pm2 process list
pm2 save

# Generate and configure startup script
pm2 startup
```