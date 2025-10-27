# Miner
## Overview

Miners collect real estate data and serve it to validators for verification. The miner implements scraping solutions to collect property data and serves this data through Bittensor's axon protocol to validators for scoring and validation.

**⚠️ IMPORTANT:**
- Miners must implement their own scraping solutions
- Focus on comprehensive property data collection
- Data is validated by validators against external sources
- Rewards based on data quality and quantity
- All miners must read our data compliance section: [here](#important-miner-data-compliance-policy)

The Miner stores all scraped property data in a local SQLite database and serves data to validators via Bittensor protocol.

### Miner Requirements:
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 250 GB free space
- **Network**: Stable internet connection with sufficient bandwidth


### Prerequisites:
1. **Python >= 3.10** and virtual environment setup
2. **Bittensor wallet** with registered hotkey
3. **Custom scraper implementation** (see scraping/custom/ for examples)
4. **Network registration** on chosen subnet


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


## Running the Miner

### Manual Setup

**Step 1: Register Miner (if needed).**
*For installation of btcli, [use this guide](https://github.com/opentensor/bittensor/blob/master/README.md#install-bittensor-sdk)*
```shell
# Testnet registration
btcli subnet register --netuid 428 --subtensor.network test \
    --wallet.name your_testnet_wallet --wallet.hotkey your_testnet_hotkey

# Mainnet registration
btcli subnet register --netuid 46 --subtensor.network finney \
    --wallet.name your_mainnet_wallet --wallet.hotkey your_mainnet_hotkey
```
**Step 2: Configure Environment Variables**

Configure your `.env` file (example `.env` provided)

**Step 3: Install pm2 (if not already installed)**
```bash
npm install -g pm2
```

**Step 4: Start Mining**

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
---
## Configuring the Miner

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

---
## Monitoring and Management

## Basic Monitoring
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
```

---
## Compliance & Miner Policy
By participating as a miner on Subnet 46, you are agreeing to adhere to our [Miner Policy](miner_policy.md) below. 
<details>
  <summary>
    ResiLabs Miner Data Compliance Policy
  </summary>

---

*Version 1.0, March 2025*

---
</details>