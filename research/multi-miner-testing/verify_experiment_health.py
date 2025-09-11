#!/usr/bin/env python3
"""
Experiment Health Verification Script
Checks S3 uploads, validator activity, and database growth
"""

import os
import sqlite3
import subprocess
import json
from datetime import datetime, timedelta
import glob

def check_screen_processes():
    """Check which screen processes are running"""
    try:
        result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        processes = {}
        for line in lines:
            if 'validator' in line:
                processes['validator'] = '✅ Running'
            elif 'miner_2' in line:
                processes['miner_2'] = '✅ Running'
            elif 'miner_3' in line:
                processes['miner_3'] = '✅ Running'
            elif 'miner_4' in line:
                processes['miner_4'] = '✅ Running'
        
        # Check for missing processes
        for process in ['validator', 'miner_2', 'miner_3', 'miner_4']:
            if process not in processes:
                processes[process] = '❌ Not running'
                
        return processes
    except Exception as e:
        return {'error': f"Could not check processes: {e}"}

def check_database_health():
    """Check database files and record counts"""
    databases = {
        'Baseline Miner (UID 5)': 'SqliteMinerStorage.sqlite',
        'Organic Miner 2 (UID 7)': 'SqliteMinerStorage_miner2.sqlite',
        'Organic Miner 3 (UID 8)': 'SqliteMinerStorage_miner3.sqlite',
        'Organic Miner 4 (UID 9)': 'SqliteMinerStorage_miner4.sqlite'
    }
    
    db_health = {}
    for name, db_file in databases.items():
        try:
            if not os.path.exists(db_file):
                db_health[name] = "❌ Database file not found"
                continue
                
            # Get file size and modification time
            stat = os.stat(db_file)
            size_mb = stat.st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            time_since_mod = datetime.now() - mod_time
            
            # Connect and get record count
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM DataEntity")
            record_count = cursor.fetchone()[0]
            conn.close()
            
            status = "✅ Healthy"
            if time_since_mod > timedelta(minutes=30):
                status = "⚠️ No recent activity"
            if record_count == 0:
                status = "🔄 Starting up"
                
            db_health[name] = {
                'status': status,
                'size_mb': f"{size_mb:.2f} MB",
                'records': record_count,
                'last_modified': mod_time.strftime("%H:%M:%S"),
                'minutes_ago': int(time_since_mod.total_seconds() / 60)
            }
            
        except Exception as e:
            db_health[name] = f"❌ Error: {e}"
    
    return db_health

def check_s3_upload_status():
    """Check S3 upload state files and recent activity"""
    state_files = glob.glob('upload_utils/state_file*.json')
    upload_status = {}
    
    for state_file in state_files:
        try:
            if os.path.exists(state_file):
                stat = os.stat(state_file)
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                time_since_mod = datetime.now() - mod_time
                
                # Try to read the state file
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                        last_upload = state_data.get('last_upload_time', 'Unknown')
                except:
                    last_upload = 'Could not read'
                
                status = "✅ Active"
                if time_since_mod > timedelta(hours=1):
                    status = "⚠️ Stale"
                    
                upload_status[os.path.basename(state_file)] = {
                    'status': status,
                    'last_modified': mod_time.strftime("%H:%M:%S"),
                    'minutes_ago': int(time_since_mod.total_seconds() / 60),
                    'last_upload': last_upload
                }
        except Exception as e:
            upload_status[state_file] = f"❌ Error: {e}"
    
    if not state_files:
        upload_status['No state files'] = "⚠️ No S3 upload state files found"
        
    return upload_status

def check_validator_logs():
    """Check for recent validator activity in logs"""
    log_patterns = [
        "~/.bittensor/miners/428_testnet_validator/*/netuid428/None/events.log"
    ]
    
    validator_activity = {}
    
    for pattern in log_patterns:
        log_files = glob.glob(os.path.expanduser(pattern))
        for log_file in log_files:
            try:
                if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                    stat = os.stat(log_file)
                    mod_time = datetime.fromtimestamp(stat.st_mtime)
                    time_since_mod = datetime.now() - mod_time
                    
                    status = "✅ Active"
                    if time_since_mod > timedelta(minutes=10):
                        status = "⚠️ No recent activity"
                        
                    validator_activity['Validator Logs'] = {
                        'status': status,
                        'last_modified': mod_time.strftime("%H:%M:%S"),
                        'minutes_ago': int(time_since_mod.total_seconds() / 60),
                        'file_size': f"{os.path.getsize(log_file)} bytes"
                    }
                    break
            except Exception as e:
                validator_activity['Validator Logs'] = f"❌ Error: {e}"
    
    if not validator_activity:
        validator_activity['Validator Logs'] = "⚠️ No validator log files found"
        
    return validator_activity

def main():
    print("=== ORGANIC STRATEGY EXPERIMENT - HEALTH CHECK ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Process Status
    print("🖥️  PROCESS STATUS:")
    processes = check_screen_processes()
    for process, status in processes.items():
        print(f"   {process}: {status}")
    print()
    
    # 2. Database Health
    print("💾 DATABASE HEALTH:")
    db_health = check_database_health()
    for db_name, health in db_health.items():
        print(f"   {db_name}:")
        if isinstance(health, dict):
            print(f"      {health['status']} - {health['size_mb']}, {health['records']} records")
            print(f"      Last modified: {health['last_modified']} ({health['minutes_ago']} min ago)")
        else:
            print(f"      {health}")
        print()
    
    # 3. S3 Upload Status
    print("☁️  S3 UPLOAD STATUS:")
    upload_status = check_s3_upload_status()
    for file_name, status in upload_status.items():
        print(f"   {file_name}:")
        if isinstance(status, dict):
            print(f"      {status['status']} - Modified: {status['last_modified']} ({status['minutes_ago']} min ago)")
            print(f"      Last upload: {status['last_upload']}")
        else:
            print(f"      {status}")
        print()
    
    # 4. Validator Activity
    print("✅ VALIDATOR ACTIVITY:")
    validator_activity = check_validator_logs()
    for activity_name, activity in validator_activity.items():
        print(f"   {activity_name}:")
        if isinstance(activity, dict):
            print(f"      {activity['status']} - Modified: {activity['last_modified']} ({activity['minutes_ago']} min ago)")
            print(f"      Log size: {activity['file_size']}")
        else:
            print(f"      {activity}")
    print()
    
    print("=" * 60)
    print("🔍 NEXT STEPS:")
    print("- Run 'python3 organic_analysis.py' for detailed strategy analysis")
    print("- Use 'screen -r validator' to view real-time validator logs")
    print("- Check 'btcli subnet metagraph --netuid 428 --subtensor.network test'")
    print("=" * 60)

if __name__ == "__main__":
    main()
