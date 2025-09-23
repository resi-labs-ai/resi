#!/bin/bash
# testnet_validation.sh - Comprehensive testnet consensus validation check

set -e

echo "🚀 Starting Testnet Consensus Validation Setup Check"
echo "=================================================="

# Check Python version
echo "✅ Checking Python version..."
python3 --version
if ! python3 -c "import sys; assert sys.version_info >= (3, 11)"; then
    echo "❌ Python 3.11+ required"
    exit 1
fi

# Check virtual environment
echo "✅ Checking virtual environment..."
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Virtual environment not activated"
    echo "Run: source venv/bin/activate"
    exit 1
fi

# Check dependencies
echo "✅ Checking dependencies..."
pip show flask bittensor pydantic > /dev/null || {
    echo "❌ Missing dependencies. Run: pip install -r requirements.txt"
    exit 1
}

# Check environment file
echo "✅ Checking environment configuration..."
if [[ ! -f ".env" ]]; then
    echo "⚠️ .env file not found. Copy from env.example (optional for testing)"
fi

# Test mock configuration
echo "✅ Testing mock consensus system..."
if ! python3 mock_data_api_server.py --host localhost --port 8000 &
then
    echo "❌ Failed to start mock server"
    exit 1
fi

# Wait for server to start
sleep 3

# Test mock configuration
if python3 scripts/test_zipcode_consensus_system.py --config mock; then
    echo "✅ Mock consensus system test PASSED"
else
    echo "❌ Mock consensus system test FAILED"
    exit 1
fi

# Kill mock server
pkill -f "mock_data_api_server.py" || true

# Test production API (optional)
echo "✅ Testing production API connectivity..."
if python3 scripts/test_zipcode_consensus_system.py --config testnet 2>&1 | grep -q "ALL TESTS PASSED"; then
    echo "✅ Production API test PASSED - Ready for testnet!"
elif python3 scripts/test_zipcode_consensus_system.py --config testnet 2>&1 | grep -q "Failed to resolve\|Api Connectivity"; then
    echo "⚠️  Production API not accessible (expected) - Mock tests confirm setup is correct"
else
    echo "❌ Unexpected error in production API test"
    exit 1
fi

echo ""
echo "🎉 All validation checks passed!"
echo "Your testnet consensus validation setup is ready."
echo ""
echo "Next steps:"
echo "1. Ensure you have production API access credentials"
echo "2. Register validator on testnet: btcli subnet register --netuid 428 --subtensor.network test"
echo "3. Start validator with consensus validation enabled"
