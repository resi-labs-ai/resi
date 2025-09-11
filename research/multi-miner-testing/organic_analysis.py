#!/usr/bin/env python3
"""
Organic Strategy Analysis - Continuous Monitoring
Tracks how miners develop different strategies over time
"""

import time
import subprocess
import json
import os
from datetime import datetime
import sqlite3

def analyze_miner_databases():
    """Analyze all miner databases to see what data is being collected"""
    databases = [
        ('Baseline Miner (UID 5)', 'SqliteMinerStorage.sqlite'),
        ('Organic Miner 2 (UID 7)', 'SqliteMinerStorage_miner2.sqlite'),
        ('Organic Miner 3 (UID 8)', 'SqliteMinerStorage_miner3.sqlite'),
        ('Organic Miner 4 (UID 9)', 'SqliteMinerStorage_miner4.sqlite')
    ]
    
    all_analysis = {}
    
    for miner_name, db_file in databases:
        try:
            if not os.path.exists(db_file):
                all_analysis[miner_name] = "Database file not found"
                continue
                
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get table info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            analysis = {
                'tables': [table[0] for table in tables],
                'total_records': {},
                'file_size': os.path.getsize(db_file)
            }
            
            for table_name in analysis['tables']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name[0]};")
                    count = cursor.fetchone()[0]
                    analysis['total_records'][table_name[0]] = count
                except:
                    analysis['total_records'][table_name[0]] = "Error reading"
            
            conn.close()
            all_analysis[miner_name] = analysis
            
        except Exception as e:
            all_analysis[miner_name] = f"Database analysis error: {e}"
    
    return all_analysis

def get_miner_incentives():
    """Extract current incentive values for our miners"""
    try:
        result = subprocess.run([
            'btcli', 'subnet', 'metagraph', 
            '--netuid', '428', 
            '--subtensor.network', 'test',
            '--json-output'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse JSON output
            data = json.loads(result.stdout)
            
            # Extract our miners (UIDs 5, 7, 8, 9)
            our_miners = {}
            for uid_info in data.get('uids', []):
                uid = uid_info.get('uid')
                if uid in [5, 7, 8, 9]:
                    our_miners[uid] = {
                        'incentive': uid_info.get('incentive', 0),
                        'emissions': uid_info.get('emissions', 0),
                        'stake': uid_info.get('stake', 0),
                        'hotkey': uid_info.get('hotkey', '')[:8] + "..."
                    }
            
            return our_miners
        else:
            return f"Error getting metagraph: {result.stderr}"
    except Exception as e:
        return f"Exception: {e}"

def monitor_strategy_development():
    """Main monitoring function"""
    print("=== ORGANIC STRATEGY DEVELOPMENT - LIVE ANALYSIS ===")
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # 1. Check miner incentives
    print("📊 CURRENT MINER PERFORMANCE:")
    incentives = get_miner_incentives()
    if isinstance(incentives, dict):
        for uid, data in incentives.items():
            miner_name = {
                5: "Baseline Miner (existing)",
                7: "Organic Miner 2", 
                8: "Organic Miner 3",
                9: "Organic Miner 4"
            }.get(uid, f"Miner {uid}")
            
            print(f"  UID {uid} ({miner_name}):")
            print(f"    Incentive: {data['incentive']:.6f}")
            print(f"    Emissions: {data['emissions']:.6f}")
            print(f"    Stake: {data['stake']:.6f}")
            print(f"    Hotkey: {data['hotkey']}")
            print()
    else:
        print(f"  Error: {incentives}")
    
    # 2. Database analysis
    print("💾 DATABASE ANALYSIS (SEPARATE DATABASES):")
    db_analyses = analyze_miner_databases()
    for miner_name, analysis in db_analyses.items():
        print(f"  {miner_name}:")
        if isinstance(analysis, dict):
            print(f"    File size: {analysis['file_size']:,} bytes")
            if analysis['total_records']:
                for table, count in analysis['total_records'].items():
                    print(f"    {table}: {count} records")
            else:
                print("    No tables found yet")
        else:
            print(f"    {analysis}")
        print()
    
    # 3. Process status
    print("\n🖥️  PROCESS STATUS:")
    try:
        result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
        active_sessions = [line.strip() for line in result.stdout.split('\n') 
                          if 'miner_' in line or 'validator' in line]
        for session in active_sessions:
            if session:
                print(f"  ✅ {session}")
    except:
        print("  Error checking screen sessions")
    
    print("\n" + "="*60)
    print("🔬 EXPERIMENT STATUS:")
    print("The organic strategy experiment is running with 4 miners competing")
    print("for rewards using identical starting configurations.")
    print()
    print("Key things to watch for:")
    print("- Different incentive values emerging between miners")
    print("- Database growth patterns indicating different scraping strategies")
    print("- Miners discovering premium zipcodes vs broad coverage approaches")
    print("="*60)

if __name__ == "__main__":
    monitor_strategy_development()
