#!/bin/bash

# Testnet Miner Startup Script
# This script runs the miner on testnet (subnet 428) with proper configuration

echo "🚀 Starting Resi Labs Testnet Miner (Subnet 428)"
echo "=================================================="

# Activate virtual environment
source venv/bin/activate

# Set environment variables for testnet
export NETUID=428
export SUBTENSOR_NETWORK=test

# Miner configuration from .env.testnet
export MINER_WALLET_NAME=testnet_miner_2
export MINER_HOTKEY=hotkey_2
export MINER_DATABASE=SqliteMinerStorage_miner2.sqlite

echo "📋 Configuration:"
echo "   Network: testnet (subnet 428)"
echo "   Wallet: $MINER_WALLET_NAME"
echo "   Hotkey: $MINER_HOTKEY"
echo "   Database: $MINER_DATABASE"
echo ""

# Check if RapidAPI key is set
if [ -n "$RAPIDAPI_ZILLOW_KEY" ]; then
    echo "🔑 RapidAPI Zillow key detected - will use real estate data"
    echo "⚠️  WARNING: This will incur API costs (~$0.50-2.00 per epoch)"
else
    echo "🔧 No RapidAPI key found - will use mock scraper"
    echo "ℹ️  To use real data: export RAPIDAPI_ZILLOW_KEY=your_key"
fi

echo ""
echo "🏃 Starting miner..."
echo "   Press Ctrl+C to stop"
echo ""

# Run the miner with testnet configuration
python -m neurons.miner \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name $MINER_WALLET_NAME \
    --wallet.hotkey $MINER_HOTKEY \
    --neuron.database_name $MINER_DATABASE \
    --neuron.scraping_config_file scraping/config/testnet_scraping_config.json \
    --logging.debug
