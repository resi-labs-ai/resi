# Miner

Miners scrape real estate data from Zillow via RapidAPI and get rewarded based on how much valuable property data they have (see the [Incentive Mechanism](../README.md#incentive-mechanism) for the full details). The incentive mechanism focuses on property data quality, freshness, and coverage across different geographic areas and property types. Miners are scored based on the total amount of unique, valuable property data they collect.

The Miner stores all scraped property data in a local database.

# System Requirements

Miners do not require a GPU and should be able to run on a low-tier machine, as long as it has sufficient network bandwidth and disk space. Must have python >= 3.10.

# Getting Started

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
cd data-universe
python -m pip install -e .
```

5. (Optional) Run your miner in [offline mode](#offline) to scrape an initial set of data.

6. Make sure you've [created a Wallet](https://docs.bittensor.com/getting-started/wallets) and [registered a hotkey](https://docs.bittensor.com/subnets/register-and-participate).

## Running the Miner

For this guide, we'll use [pm2](https://pm2.keymetrics.io/) to manage the Miner process, because it'll restart the Miner if it crashes. If you don't already have it, install pm2.

### Online

From the resi folder, run:
```shell
pm2 start python -- ./neurons/miner.py --wallet.name your-wallet --wallet.hotkey your-hotkey
```

### Offline

From the resi folder, run:
```shell
pm2 start python -- ./neurons/miner.py --offline
```

Please note that your miner will not respond to validator requests in this mode and therefore if you have already registered to the subnet you should run in online mode.

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
