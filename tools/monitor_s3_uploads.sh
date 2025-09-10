#!/bin/bash

echo "🔍 Monitoring S3 Upload Activity"
echo "================================"
echo "Started at: $(date)"
echo "First upload expected: ~30 minutes after miner start (around 15:34 EDT)"
echo "Subsequent uploads: Every 5 minutes"
echo ""

# Monitor the miner log for S3-related messages
tail -f miner_startup.log | grep --line-buffered -E "(S3|upload|partitioned|auth|Starting S3|upload.*completed|Using.*frequency)" &

# Also monitor for upload state file creation
echo "Watching for upload state file creation..."
while true; do
    if [ -f "upload_utils/state_file_s3_partitioned.json" ]; then
        echo "✅ $(date): Upload state file created!"
        echo "📊 Upload state contents:"
        cat upload_utils/state_file_s3_partitioned.json | head -20
        break
    fi
    sleep 30
done &

# Monitor database growth
echo "📈 Database size monitoring:"
while true; do
    if [ -f "SqliteMinerStorage.sqlite" ]; then
        size=$(ls -lh SqliteMinerStorage.sqlite | awk '{print $5}')
        echo "$(date): Database size: $size"
    fi
    sleep 300  # Check every 5 minutes
done &

echo "Press Ctrl+C to stop monitoring"
wait
