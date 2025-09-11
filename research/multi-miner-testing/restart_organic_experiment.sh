#!/bin/bash

# Organic Strategy Experiment - Quick Restart Script
echo "=== RESTARTING ORGANIC STRATEGY EXPERIMENT ==="

# Check if we're in the right directory
if [[ ! -f "neurons/miner.py" ]]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Set accelerated evaluation period
export MINER_EVAL_PERIOD_MINUTES=5
echo "⚡ Set evaluation period to 5 minutes (accelerated testing)"

# Start validator
echo "🎯 Starting validator with accelerated evaluation..."
screen -dmS validator bash -c "source venv/bin/activate && python neurons/validator.py --netuid 428 --subtensor.network test --wallet.name 428_testnet_validator --wallet.hotkey 428_testnet_validator_hotkey --logging.debug --max_targets 10"

# Wait a moment for validator to initialize
sleep 3

# Start miners with separate databases
echo "🏃 Starting Miner 2 (UID 7) with separate database..."
screen -dmS miner_2 bash -c "source venv/bin/activate && python neurons/miner.py --netuid 428 --subtensor.network test --wallet.name testnet_miner_2 --wallet.hotkey hotkey_2 --use_uploader --logging.debug --neuron.database_name SqliteMinerStorage_miner2.sqlite"

echo "🏃 Starting Miner 3 (UID 8) with separate database..."
screen -dmS miner_3 bash -c "source venv/bin/activate && python neurons/miner.py --netuid 428 --subtensor.network test --wallet.name testnet_miner_3 --wallet.hotkey hotkey_3 --use_uploader --logging.debug --neuron.database_name SqliteMinerStorage_miner3.sqlite"

echo "🏃 Starting Miner 4 (UID 9) with separate database..."
screen -dmS miner_4 bash -c "source venv/bin/activate && python neurons/miner.py --netuid 428 --subtensor.network test --wallet.name testnet_miner_4 --wallet.hotkey hotkey_4 --use_uploader --logging.debug --neuron.database_name SqliteMinerStorage_miner4.sqlite"

# Wait for processes to start
sleep 5

# Verify all processes are running
echo ""
echo "🖥️  PROCESS STATUS:"
screen -list

echo ""
echo "✅ ORGANIC STRATEGY EXPERIMENT STARTED!"
echo ""
echo "📊 Monitor with:"
echo "   python3 organic_analysis.py"
echo ""
echo "🔍 View individual logs:"
echo "   screen -r validator"
echo "   screen -r miner_2"
echo "   screen -r miner_3" 
echo "   screen -r miner_4"
echo "   (Use Ctrl+A, D to detach)"
echo ""
echo "🛑 Stop experiment:"
echo "   screen -S validator -X quit && screen -S miner_2 -X quit && screen -S miner_3 -X quit && screen -S miner_4 -X quit"
echo ""
echo "🎯 Expected: Miners will develop different strategies organically over 2-4 hours"
