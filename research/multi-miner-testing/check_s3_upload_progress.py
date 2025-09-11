#!/usr/bin/env python3
"""
Quick script to check S3 upload progress for all miners
"""
import os
import json
from datetime import datetime

def check_s3_progress():
    print("=== S3 UPLOAD PROGRESS CHECK ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Expected miner hotkeys
    miners = {
        'miner_2': '5CAsdjbWjgj1f7Ubt1eYzQDhDfpcPuWkAAZES6HrBM7LbGq9',
        'miner_3': '5F1SejVkczocndDfPuFmjwhBqpsbP4mXGJMCdyQCTs4KnezW', 
        'miner_4': '5GYaE1VteBMvzpf35upMMwpyNs1eqDhD8LMvxehi5WaaPu8W'
    }
    
    print("1. LOCAL S3 DIRECTORIES:")
    s3_dir = "s3_partitioned_storage"
    if os.path.exists(s3_dir):
        dirs = os.listdir(s3_dir)
        dirs = [d for d in dirs if d.startswith('5')]  # Filter hotkey directories
        print(f"   Found {len(dirs)} miner directories:")
        for d in dirs:
            print(f"   ✅ {d}")
        
        missing = []
        for name, hotkey in miners.items():
            if hotkey not in dirs:
                missing.append(f"{name} ({hotkey})")
        
        if missing:
            print(f"   ❌ Missing: {', '.join(missing)}")
    else:
        print("   ❌ No s3_partitioned_storage directory found")
    
    print()
    print("2. S3 STATE FILES:")
    state_files = [
        'upload_utils/state_file_miner2_s3_partitioned.json',
        'upload_utils/state_file_miner3_s3_partitioned.json', 
        'upload_utils/state_file_miner4_s3_partitioned.json'
    ]
    
    for state_file in state_files:
        if os.path.exists(state_file):
            size = os.path.getsize(state_file)
            miner_name = state_file.split('_')[2]  # Extract miner number
            
            if size > 1000:  # Large file indicates uploads
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    job_count = len(data)
                    print(f"   ✅ {miner_name}: {size:,} bytes, {job_count} jobs")
                except:
                    print(f"   ✅ {miner_name}: {size:,} bytes")
            else:
                print(f"   ⏳ {miner_name}: {size} bytes (waiting for uploads)")
        else:
            miner_name = state_file.split('_')[2]
            print(f"   ❌ {miner_name}: No state file")
    
    print()
    print("3. DATABASE SIZES:")
    db_files = [
        'SqliteMinerStorage_miner2.sqlite',
        'SqliteMinerStorage_miner3.sqlite',
        'SqliteMinerStorage_miner4.sqlite'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            miner_name = db_file.split('_')[1].replace('.sqlite', '')
            print(f"   📊 {miner_name}: {size:,} bytes")
    
    print()
    print("EXPECTED S3 BUCKET DIRECTORIES:")
    for name, hotkey in miners.items():
        print(f"   {name}: {hotkey}")
    
    print()
    print("Check your S3 bucket for these directories!")
    print("https://us-east-2.console.aws.amazon.com/s3/buckets/2000-resilabs-test-bittensor-sn428-datacollection")

if __name__ == "__main__":
    check_s3_progress()
