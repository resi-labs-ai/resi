# Miner

Miners collect real estate data and serve it to validators for verification. The miner implements scraping solutions to collect property data and serves this data through Bittensor's axon protocol to validators for scoring and validation.

**⚠️ IMPORTANT:**
- Miners must implement their own scraping solutions
- Focus on comprehensive property data collection
- Data is validated by validators against external sources
- Rewards based on data quality and quantity

The Miner stores all scraped property data in a local SQLite database and serves data to validators via Bittensor protocol.

# System Requirements

Miners do not require a GPU and should be able to run on a low-tier machine, as long as it has sufficient network bandwidth and disk space. Must have python >= 3.10.

# Getting Started

## Network Selection

### Testnet (Subnet 428) - Recommended for Testing
Testnet is perfect for:
- Testing your setup without real TAO costs
- Learning how the system works
- Validating your configuration
- Development and debugging

**Key Features:**
- **Faster S3 Uploads**: Every 5 minutes (vs 2 hours on mainnet)
- **Auto-configured endpoints**: Automatically uses testnet S3 auth service
- **Lower stakes**: Test environment with no financial risk

### Mainnet (Subnet 46) - Production Environment
Mainnet for production mining:
- Real TAO rewards based on data quality
- Production-grade requirements
- Standard 2-hour S3 upload frequency
- Full network participation

## Prerequisites

1. **Python >= 3.10** and virtual environment setup
2. **Bittensor wallet** with registered hotkey
3. **Custom scraper implementation** (see scraping/custom/ for examples)
4. **Network registration** on chosen subnet

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

## Running the Miner

### Manual Setup

**Step 1: Register on Network (if needed)**
```shell
# Testnet registration
btcli subnet register --netuid 428 --subtensor.network test \
    --wallet.name your_testnet_wallet --wallet.hotkey your_testnet_hotkey

# Mainnet registration
btcli subnet register --netuid 46 --subtensor.network finney \
    --wallet.name your_mainnet_wallet --wallet.hotkey your_mainnet_hotkey
```

**Step 2: Start Mining**

Use [pm2](https://pm2.keymetrics.io/) to manage the Miner process for automatic restarts.

**Testnet Mining:**
```shell
# Start testnet miner
pm2 start python --name testnet-miner -- ./neurons/miner.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name your_testnet_wallet \
    --wallet.hotkey your_testnet_hotkey \
    --logging.debug
```

**Mainnet Mining:**
```shell
# Start mainnet miner
pm2 start python --name mainnet-miner -- ./neurons/miner.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_wallet \
    --wallet.hotkey your_mainnet_hotkey \
    --logging.debug
```

# Configuring the Miner

## Available Flags

The Miner supports the following key configuration flags:

### **Required Flags:**
- `--netuid`: 428 (testnet) or 46 (mainnet)
- `--subtensor.network`: "test" (testnet) or "finney" (mainnet)
- `--wallet.name`: Your wallet name
- `--wallet.hotkey`: Your hotkey name

### **Optional Flags:**
- `--neuron.database_name`: Custom database file path (default: SqliteMinerStorage.sqlite)
- `--neuron.max_database_size_gb_hint`: Database size limit in GB (default: 250)
- `--offline`: Run in offline mode (no network participation)
- `--logging.debug`: Enable debug logging
- `--use_uploader`: Enable S3 data uploading (default: enabled)
- `--no_use_uploader`: Disable S3 data uploading
- `--neuron.scraping_config_file`: Custom scraping configuration file
- `--encoding_key_json_file`: Custom encoding keys file
- `--miner_upload_state_file`: Custom upload state file

## Data Collection

Miners collect property data using custom scraper implementations. The scraping configuration is defined in JSON files that specify:
- **Scraper cadence**: How often to run each scraper
- **Data labels**: Geographic areas and property types to target
- **Collection limits**: Maximum number of entities per scraping run

Example configuration structure:
```json
{
    "scraper_configs": [
        {
            "scraper_id": "Custom.your_scraper",
            "cadence_seconds": 3600,
            "labels_to_scrape": [...]
        }
    ]
}
```

## Data Storage

All scraped data is stored locally in a SQLite database and optionally uploaded to S3 for public access.

# Monitoring and Management

## Basic Monitoring

### Check Miner Status
```shell
# Check PM2 process status
pm2 status
pm2 info testnet-miner  # or mainnet-miner

# View real-time logs
pm2 logs testnet-miner --lines 100 --follow  # Testnet
pm2 logs mainnet-miner --lines 100 --follow  # Mainnet

# Monitor database growth
ls -lh SqliteMinerStorage*.sqlite

# Check wallet registration
btcli wallet overview --wallet.name your_wallet --subtensor.network test  # Testnet
btcli wallet overview --wallet.name your_wallet --subtensor.network finney # Mainnet
```

## Management Commands
```shell
# Restart miner if needed
pm2 restart testnet-miner  # or mainnet-miner
pm2 stop testnet-miner     # or mainnet-miner

# Check available storage tools
python tools/check_miner_storage.py --help
```

## Troubleshooting

### Common Issues

**Miner Not Starting:**
- Verify wallet and hotkey exist and are registered
- Check subnet connectivity: `btcli subnet list`
- Ensure virtual environment is activated

**Database Issues:**
- Check available disk space
- Verify database file permissions
- Monitor for SQLite corruption

**Network Issues:**
- Confirm firewall allows Bittensor ports
- Check internet connectivity
- Verify wallet has sufficient balance for transactions
