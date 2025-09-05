# Validator

The Validator is responsible for validating the Miners' property data and scoring them according to the [incentive mechanism](../README.md#incentive-mechanism). It runs a loop to enumerate all Miners in the network, and for each, it performs the following sequence:
1. It requests the latest [MinerIndex](../README.md#terminology) from the miner, which contains their property data summary, and stores it in an in-memory database.
2. It chooses a random (sampled by size) DataEntityBucket from the MinerIndex to sample for validation.
3. It gets that DataEntityBucket containing property listings from the Miner.
4. It chooses N property DataEntities from the DataEntityBucket to validate. It then verifies the property data by cross-referencing with Zillow via RapidAPI.
5. It compares the retrieved property data against what the Miner provided and updates the Miner Credibility based on accuracy.
6. Finally, it updates the Miner's score based on the total property data index scaled by Freshness/Desirability/Geographic Coverage/Credibility.

Once this sequence has been performed for all Miners, the Validator waits a period of time before starting the next loop to ensure it does not evaluate a Miner more often than once per N minutes. This helps ensure the cost of running a Validator is not too high, and also protects the network against high amounts of traffic.

The expected cost for property data validation via RapidAPI Zillow is calculated based on: `Number of Miners * validation frequency * samples per validation * 24 hours`. With RapidAPI Zillow pricing typically around $0.001-$0.01 per request depending on your plan, validation costs are generally manageable for serious validator operations.

# System Requirements

Validators require at least 32 GB of RAM but do not require a GPU. We recommend a decent CPU (4+ cores) and sufficient network bandwidth to handle protocol traffic. Must have python >= 3.10.

# Getting Started

## Prerequisites

### Getting Your RapidAPI Zillow Key (Required)

Validators need a RapidAPI key for Zillow to verify the property data that miners submit. This is essential for the validation process.

**Step 1: Create a RapidAPI Account**
1. Go to [RapidAPI.com](https://rapidapi.com/) and sign up for a free account
2. Verify your email address

**Step 2: Subscribe to Zillow API**
1. Navigate to the [Zillow API on RapidAPI](https://rapidapi.com/apimaker/api/zillow-com1/)
2. Click "Subscribe to Test" or "Pricing" to view available plans
3. Choose a plan suitable for validation needs:
   - **Pro Plans Recommended**: Validators need higher request limits for verification
   - Consider plans with 10,000+ requests/month for active validation
4. Complete the subscription process

**Step 3: Get Your API Key**
1. After subscribing, copy your RapidAPI key from the "X-RapidAPI-Key" header
2. This key will be used to verify miner data accuracy

**Step 4: Configure Your Environment**
Add these to your `.env` file:
```
RAPIDAPI_KEY=YOUR_ACTUAL_API_KEY_HERE
RAPIDAPI_HOST=zillow-com1.p.rapidapi.com
```

**Important for Validators:**
- Budget for API costs as part of your validation operations
- Higher-tier plans provide more validation capacity
- Monitor usage to ensure continuous validation capability

For detailed setup instructions, cost management, and troubleshooting, see the [RapidAPI documentation](rapidapi.md).

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

5. Make sure you've [created a Wallet](https://docs.bittensor.com/getting-started/wallets) and [registered a hotkey](https://docs.bittensor.com/subnets/register-and-participate).

```

This will prompt you to navigate to https://wandb.ai/authorize and copy your api key back into the terminal.

## Running the Validator

### With auto-updates

We highly recommend running the validator with auto-updates. This will help ensure your validator is always running the latest release, helping to maintain a high vtrust.

Prerequisites:
1. To run with auto-update, you will need to have [pm2](https://pm2.keymetrics.io/) installed.
2. Make sure your virtual environment is activated. This is important because the auto-updater will automatically update the package dependencies with pip.
3. Make sure you're using the main branch: `git checkout main`.

From the resi folder:
```shell
pm2 start --name net13-vali-updater --interpreter python scripts/start_validator.py -- --pm2_name net13-vali --wallet.name cold_wallet --wallet.hotkey hotkey_wallet [other vali flags]
```

This will start a process called `net13-vali-updater`. This process periodically checks for a new git commit on the current branch. When one is found, it performs a `pip install` for the latest packages, and restarts the validator process (who's name is given by the `--pm2_name` flag)


### Without auto-updates

If you'd prefer to manage your own validator updates...

From the resi folder:
```shell
pm2 start python -- ./neurons/validator.py --wallet.name your-wallet --wallet.hotkey your-hotkey
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
RAPIDAPI_KEY="your_rapidapi_key_here"
RAPIDAPI_HOST="zillow-com1.p.rapidapi.com"
```

The RapidAPI key is essential for validators to verify property data accuracy by cross-referencing with Zillow's database during the validation process.

Please see the [RapidAPI documentation](rapidapi.md) for complete setup instructions and cost management guidance.

# Coming Soon

We are working hard to add more features to RESI. For the Validators, we have plans to:

1. Have the Validator serve an Axon on the network, so neurons on other Subnets can retrieve property data.
2. Add scrapers for additional real estate DataSources (county assessors, MLS feeds, public records).
3. Implement more cost-effective validation methods while maintaining data accuracy.
4. Add support for commercial property data validation.
5. Expand to international property markets.
