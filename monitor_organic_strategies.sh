#!/bin/bash

# Monitor organic strategy development in multi-miner testnet
echo "=== Multi-Miner Organic Strategy Monitor ==="
echo "Started at: $(date)"
echo ""

while true; do
    echo "=== $(date) ==="
    
    # Check screen sessions
    echo "Active Sessions:"
    screen -list | grep -E "(miner_|validator)" || echo "No active sessions found"
    echo ""
    
    # Check metagraph status
    echo "Current Subnet Status:"
    btcli subnet metagraph --netuid 428 --subtensor.network test | grep -A 15 "UID.*Stake.*Alpha"
    echo ""
    
    # Check if we can see any miner activity (basic check)
    echo "Miner Activity Check:"
    for miner in 2 3 4; do
        echo "Miner $miner (screen session): $(screen -list | grep miner_$miner | wc -l) session(s)"
    done
    echo ""
    
    echo "Validator Activity: $(screen -list | grep validator | wc -l) session(s)"
    echo ""
    
    echo "Next check in 5 minutes..."
    echo "================================================"
    echo ""
    
    sleep 300  # 5 minutes
done
