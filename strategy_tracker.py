#!/usr/bin/env python3
"""
Organic Strategy Development Tracker
Monitors how miners naturally develop different strategies in the testnet
"""

import time
import subprocess
import json
import os
from datetime import datetime

def get_metagraph_data():
    """Get current metagraph data"""
    try:
        result = subprocess.run([
            'btcli', 'subnet', 'metagraph', 
            '--netuid', '428', 
            '--subtensor.network', 'test',
            '--json-output'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse the output - btcli json output format may vary
            return result.stdout
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Exception: {e}"

def check_screen_sessions():
    """Check which screen sessions are running"""
    try:
        result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Exception: {e}"

def check_database_activity():
    """Check database file sizes and modification times"""
    db_files = [
        'SqliteMinerStorage.sqlite',
        'SqliteMinerStorage.sqlite-wal',
        'SqliteMinerStorage.sqlite-shm'
    ]
    
    activity = {}
    for db_file in db_files:
        if os.path.exists(db_file):
            stat = os.stat(db_file)
            activity[db_file] = {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S') 
            }
    return activity

def main():
    print("=== ORGANIC STRATEGY DEVELOPMENT TRACKER ===")
    print(f"Started at: {datetime.now()}")
    print()
    
    # Initial baseline
    print("1. Screen Sessions Status:")
    print(check_screen_sessions())
    
    print("2. Database Activity:")
    db_activity = check_database_activity()
    for db, info in db_activity.items():
        print(f"  {db}: {info['size']} bytes, modified: {info['modified']}")
    
    print("\n3. Current Metagraph Status:")
    metagraph_data = get_metagraph_data()
    print(metagraph_data[:1000] + "..." if len(metagraph_data) > 1000 else metagraph_data)
    
    print("\n" + "="*60)
    print("Organic strategy experiment is running!")
    print("Miners (UIDs 5, 7, 8, 9) are competing with identical starting conditions.")
    print("Watch for:")
    print("- Changes in incentive values")
    print("- Database growth patterns")
    print("- Different miner behaviors emerging")
    print("="*60)

if __name__ == "__main__":
    main()
