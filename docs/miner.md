# Miner

Miners scrape real estate data from Zillow via RapidAPI and get rewarded based on how much valuable property data they have (see the [Incentive Mechanism](../README.md#incentive-mechanism) for the full details). The incentive mechanism focuses on property data quality, freshness, and coverage across different geographic areas and property types. Miners are scored based on the total amount of unique, valuable property data they collect.

The Miner stores all scraped property data in a local database.

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

### Getting Your RapidAPI Zillow Key (Required)

Miners need a RapidAPI key for Zillow to access real estate data. This is the primary data source that validators will verify against.

**Step 1: Create a RapidAPI Account**
1. Go to [RapidAPI.com](https://rapidapi.com/) and sign up for a free account
2. Verify your email address

**Step 2: Subscribe to Zillow API**
1. Navigate to the [Zillow API on RapidAPI](https://rapidapi.com/apimaker/api/zillow-com1/)
2. Click "Subscribe to Test" or "Pricing" to view available plans
3. Choose a plan that fits your mining needs:
   - **Basic Plan**: Usually includes 1,000+ requests/month (good for testing)
   - **Pro Plans**: Higher request limits for serious mining operations
4. Complete the subscription process

**Step 3: Get Your API Key**
1. After subscribing, you'll see your RapidAPI key in the "X-RapidAPI-Key" header
2. Copy this key - you'll need it for your `.env` file

**Step 4: Configure Your Environment**
Add these to your `.env` file:
```
RAPIDAPI_KEY=YOUR_ACTUAL_API_KEY_HERE
RAPIDAPI_HOST=zillow-com1.p.rapidapi.com
```

**Important Notes:**
- Keep your API key secure and never commit it to version control
- Monitor your API usage to avoid overage charges
- Higher-tier plans provide better mining opportunities with more requests

For detailed setup instructions see the [RapidAPI documentation](rapidapi.md).

2. Clone the repo

```shell
git clone https://github.com/resi-labs-ai/resi.git
```

3. Setup your python [virtual environment](https://docs.python.org/3/library/venv.html) or [Conda environment](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-with-commands).

4. Install the requirements. From your virtual environment, run
```shell
cd resi
python -m pip install -e .
```

5. (Optional) Run your miner in [offline mode](#offline) to scrape an initial set of data.

6. Make sure you've [created a Wallet](https://docs.bittensor.com/getting-started/wallets) and [registered a hotkey](https://docs.bittensor.com/subnets/register-and-participate).

## Running the Miner

### Quick Start Options

#### Option 1: Bootstrap Script (Recommended for Testnet)
```shell
# Automated testnet setup and start
python bootstrap_testnet_428.py
```
This script handles wallet registration, subnet verification, and miner startup automatically.

#### Option 2: Manual Setup

**Step 1: Configure Environment**
Update your `.env` file with your wallet information:
```shell
# For Testnet (Subnet 428)
NETUID=428
SUBTENSOR_NETWORK=test
WALLET_NAME=your_testnet_wallet_name
WALLET_HOTKEY=your_testnet_hotkey_name
RAPIDAPI_KEY=your_rapidapi_key_here
RAPIDAPI_HOST=zillow-com1.p.rapidapi.com

# For Mainnet (Subnet 46)
NETUID=46
SUBTENSOR_NETWORK=finney
WALLET_NAME=your_mainnet_wallet_name
WALLET_HOTKEY=your_mainnet_hotkey_name
RAPIDAPI_KEY=your_rapidapi_key_here
RAPIDAPI_HOST=zillow-com1.p.rapidapi.com
```

**Step 2: Register on Network (if needed)**
```shell
# Testnet registration
btcli subnet register --netuid 428 --subtensor.network test \
    --wallet.name your_testnet_wallet --wallet.hotkey your_testnet_hotkey

# Mainnet registration
btcli subnet register --netuid 46 --subtensor.network finney \
    --wallet.name your_mainnet_wallet --wallet.hotkey your_mainnet_hotkey
```

**Step 3: Start Mining**

For this guide, we'll use [pm2](https://pm2.keymetrics.io/) to manage the Miner process, because it'll restart the Miner if it crashes. If you don't already have it, install pm2.

**Testnet Mining:**
```shell
# Start testnet miner (5-minute S3 uploads, auto-configured endpoints)
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

**Mainnet Mining:**
```shell
# Start mainnet miner (2-hour S3 uploads, production settings)
pm2 start python --name mainnet-miner -- ./neurons/miner.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_mainnet_wallet \
    --wallet.hotkey your_mainnet_hotkey \
    --use_uploader \
    --neuron.database_name SqliteMinerStorage_mainnet.sqlite \
    --miner_upload_state_file upload_utils/state_file_mainnet.json
```

**Offline Mode:**
```shell
# Run offline for initial data collection (no network participation)
pm2 start python -- ./neurons/miner.py --offline
```

Please note that your miner will not respond to validator requests in offline mode and therefore if you have already registered to the subnet you should run in online mode.

# Configuring the Miner

## Flags

The Miner offers some flags to customize properties, such as the database name and the maximum amount of data to store.

You can view the full set of flags by running
```shell
python ./neurons/miner.py -h
```

## Configuring Property Data Collection

The frequency and types of property data your Miner will scrape is configured in the [scraping_config.json](https://github.com/resi-labs-ai/resi/blob/main/scraping/config/scraping_config.json) file. This file defines which property data scrapers your Miner will use. To customize your Miner, you either edit `scraping_config.json` or create your own file and pass its filepath via the `--neuron.scraping_config_file` flag.

By default `scraping_config.json` is set up to use the Zillow RapidAPI scraper for collecting property data.

The configuration focuses on:
- **Geographic Coverage**: Different zip codes and metropolitan areas
- **Property Types**: Residential properties, condos, townhomes, etc.
- **Data Freshness**: Recently listed, sold, or updated properties

If the Zillow RapidAPI configuration is not set up properly in your `.env` file, your miner will log errors and cannot collect property data.

For each scraper, you can define:

1. `cadence_seconds`: to control how frequently the scraper will run.
2. `labels_to_scrape`: to define how much of what type of data to scrape from this source. Each entry in this list consists of the following properties:
    1. `label_choices`: is a list of DataLabels to scrape. Each time the scraper runs, **one** of these labels is chosen at random to scrape.
    2. `max_age_hint_minutes`: provides a hint to the scraper of the maximum age of data you'd like to collect for the chosen label. Not all scrapers provide date/time filters so this is a hint, not a rule.
    3. `max_data_entities`: defines the maximum number of items to scrape for this set of labels, each time the scraper runs. This gives you full control over the maximum cost of scraping data from paid sources (e.g. Apify)

Let's walk through an example real estate scraping configuration:
```json
{
    "scraper_configs": [
        {
            "scraper_id": "Zillow.rapid",
            "cadence_seconds": 1800,
            "labels_to_scrape": [
                {
                    "label_choices": [
                        "90210",
                        "10001",
                        "94102"
                    ],
                    "max_age_hint_minutes": 2880,
                    "max_data_entities": 50
                },
                {
                    "label_choices": [
                        "33101",
                        "60601"
                    ],
                    "max_data_entities": 30
                }
            ]
        }
    ]
}
```

In this example, we configure the Miner to scrape property data using the Zillow RapidAPI scraper. The scraper will run every 30 minutes (1800 seconds). When it runs, it'll perform 2 different scraping operations:
1. The first will scrape at most 50 property listings from high-value zip codes (Beverly Hills, Manhattan, San Francisco). The scraper will focus on properties listed or updated within the last 48 hours (2880 minutes).
2. The second will scrape at most 30 properties from other major metropolitan areas (Miami, Chicago), prioritizing the most recent listings.

The scraper automatically selects random [TimeBuckets](../README.md#terminology) weighted toward newer data to match the Validator's incentive for [Data Freshness](../README.md#1-data-freshness).

You can start your Miner with a different scraping config by passing the filepath to `--neuron.scraping_config_file`

# On Demand request handle
As described in [on demand request handle](../docs/on_demand.md)

# Choosing which data to scrape

As described in the [incentive mechanism](../README.md#incentive-mechanism), Miners are, in part, scored based on their data's desirability and uniqueness. We encourage Miners to tune their Miners to maximize their scores by scraping unique, desirable data.

For uniqueness, you can [view the dashboard](../README.md#resi-labs-dashboard) to see how much property data, by geographic area and property type, is currently on the Subnet.

For desirability, the [DataDesirabilityLookup](https://github.com/resi-labs-ai/resi/blob/main/rewards/data_desirability_lookup.py) defines the exact rules Validators use to compute property data desirability. High-value areas, recently listed properties, and unique property types typically receive higher desirability scores.

# Storage and Upload Configuration

## Local Storage
Your miner automatically stores all scraped data locally in a SQLite database:
- **Default Location**: `SqliteMinerStorage.sqlite`
- **Default Size Limit**: 250GB (configurable with `--neuron.max_database_size_gb_hint`)
- **Custom Path**: Use `--neuron.database_name` to specify a different location

## S3 Cloud Storage
Miners automatically upload data to S3 for public dataset access:

### Upload Frequency
- **Testnet (Subnet 428)**: Every 5 minutes (optimized for testing)
- **Mainnet (Subnet 46)**: Every 2 hours (standard production)
- **First Upload**: 30 minutes after miner starts

### S3 Authentication
The miner automatically configures the correct S3 authentication endpoint:
- **Testnet**: `https://s3-auth-api-testnet.resilabs.ai`
- **Mainnet**: `https://s3-auth-api.resilabs.ai`

No manual S3 configuration is required - the system detects your subnet and configures appropriately.

### S3 Data Structure
Data is organized in S3 as:
```
bucket-name/
└── hotkey={your_hotkey}/
    ├── job_id=job_001/
    │   ├── data_20250910_120000_1500.parquet
    │   └── data_20250910_120500_890.parquet
    └── job_id=job_002/
        └── data_20250910_120000_2100.parquet
```

# Monitoring and Validation

## Health Check Tools
Use the built-in validation tools to monitor your miner:

### Quick Health Check
```shell
# Fast operational validation
python tools/check_miner_storage.py --netuid 428  # Testnet
python tools/check_miner_storage.py --netuid 46   # Mainnet
```

### Comprehensive Validation
```shell
# Full validation with S3 authentication testing
python tools/validate_miner_storage.py --netuid 428 \
    --wallet.name your_wallet --wallet.hotkey your_hotkey \
    --subtensor.network test
```

## Expected Log Messages
When your miner is working correctly, you'll see:

**Testnet Configuration:**
```
Auto-configured testnet S3 auth URL: https://s3-auth-api-testnet.resilabs.ai
Using testnet upload frequency: 5 minutes
Starting S3 partitioned upload for DD data
S3 partitioned upload completed successfully
```

**Mainnet Configuration:**
```
Auto-configured mainnet S3 auth URL: https://s3-auth-api.resilabs.ai
Using mainnet upload frequency: 2 hours
Starting S3 partitioned upload for DD data
S3 partitioned upload completed successfully
```

## Monitoring Commands
```shell
# Watch miner logs in real-time
pm2 logs testnet-miner --lines 100 --follow  # Testnet
pm2 logs mainnet-miner --lines 100 --follow  # Mainnet

# Monitor S3 upload activity
pm2 logs testnet-miner --lines 100 --follow | grep -E "(S3|upload|partitioned)"

# Check database growth
ls -lh SqliteMinerStorage*.sqlite

# Check PM2 process status
pm2 status
pm2 info testnet-miner  # or mainnet-miner

# Verify wallet registration
btcli wallet overview --wallet.name your_wallet --subtensor.network test  # Testnet
btcli wallet overview --wallet.name your_wallet --subtensor.network finney # Mainnet

# Restart miner if needed
pm2 restart testnet-miner  # or mainnet-miner
pm2 stop testnet-miner     # or mainnet-miner
```

## Important Flags Reference

### **Required Flags:**
- `--netuid`: 428 (testnet) or 46 (mainnet)
- `--subtensor.network`: "test" (testnet) or "finney" (mainnet)
- `--wallet.name`: Your wallet name
- `--wallet.hotkey`: Your hotkey name

### **S3 Upload Flags:**
- `--use_uploader`: Enable S3 uploads (default: true)
- `--no_use_uploader`: Disable S3 uploads
- `--neuron.database_name`: Custom database file path
- `--miner_upload_state_file`: Custom upload state file path

### **Common Optional Flags:**
- `--logging.debug`: Enable debug logging
- `--neuron.max_database_size_gb_hint`: Database size limit (default: 250GB)
- `--offline`: Run in offline mode (no network participation)
- `--neuron.scraping_config_file`: Custom scraping configuration file

### **Example Commands by Use Case:**

**Development/Testing:**
```shell
pm2 start python --name dev-miner -- ./neurons/miner.py \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name dev_wallet \
    --wallet.hotkey dev_hotkey \
    --use_uploader \
    --logging.debug \
    --neuron.database_name SqliteMinerStorage_dev.sqlite
```

**Production Mainnet:**
```shell
pm2 start python --name prod-miner -- ./neurons/miner.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name production_wallet \
    --wallet.hotkey production_hotkey \
    --use_uploader \
    --neuron.database_name SqliteMinerStorage_prod.sqlite \
    --neuron.max_database_size_gb_hint 500
```

# Troubleshooting

## Common Issues

### Database Not Growing
- Check RapidAPI key configuration in `.env`
- Verify RapidAPI subscription is active
- Monitor logs for scraping errors

### S3 Upload Failures
- Verify wallet is registered on the correct subnet
- Check S3 auth service connectivity: `python tools/check_miner_storage.py`
- Ensure sufficient API quota for authentication

### Network Connection Issues
- Verify subnet registration: `btcli wallet overview`
- Check firewall settings for bittensor ports
- Confirm subtensor network connectivity

## Success Indicators
✅ **Database Growth**: `SqliteMinerStorage.sqlite` increases in size over time
✅ **Regular S3 Uploads**: Log messages every 5 minutes (testnet) or 2 hours (mainnet)
✅ **Validator Responses**: Successful responses to validator queries
✅ **No Authentication Errors**: Clean logs without S3 or API failures

For detailed troubleshooting, see the validation guide: `dev-docs/0001-miner-storage-validation.md`
