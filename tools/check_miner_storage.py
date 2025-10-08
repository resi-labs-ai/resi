#!/usr/bin/env python3
"""
Simple Miner Storage Checker
Validates local storage and S3 configuration without bittensor dependencies
"""

import os
import sqlite3
import json
import requests
import sys
from datetime import datetime


def check_database(db_path="SqliteMinerStorage.sqlite"):
    """Check local SQLite database"""
    print(f"\n🗄️  Checking Local Database: {db_path}")
    print("=" * 50)
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    print(f"✅ Database file exists ({os.path.getsize(db_path) / (1024*1024):.2f} MB)")
    
    try:
        with sqlite3.connect(db_path, timeout=10.0) as conn:
            cursor = conn.cursor()
            
            # Check table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='DataEntity'")
            if not cursor.fetchone():
                print("❌ DataEntity table not found")
                return False
            
            print("✅ DataEntity table exists")
            
            # Get data count
            cursor.execute("SELECT COUNT(*) FROM DataEntity")
            count = cursor.fetchone()[0]
            print(f"📊 Total records: {count:,}")
            
            if count > 0:
                # Show recent data
                cursor.execute("""
                    SELECT source, label, datetime, LENGTH(content) as size
                    FROM DataEntity 
                    ORDER BY datetime DESC 
                    LIMIT 3
                """)
                
                print("📋 Recent entries:")
                for row in cursor.fetchall():
                    source, label, dt, size = row
                    print(f"   • Source {source}, Label: {label}, Size: {size}B, Time: {dt}")
            else:
                print("⚠️  No data found - miner may not be running yet")
            
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def check_s3_config(netuid=None):
    """Check S3 configuration"""
    print(f"\n☁️  Checking S3 Configuration")
    print("=" * 50)
    
    # Determine expected URLs
    if netuid == 428:
        expected_url = "https://api-staging.resilabs.ai"
        upload_freq = "5 minutes"
        network = "Testnet"
    else:
        expected_url = "https://api.resilabs.ai"
        upload_freq = "2 hours"
        network = "Mainnet"
    
    print(f"🌐 Network: {network} (Subnet {netuid or 'Unknown'})")
    print(f"🔗 Expected S3 URL: {expected_url}")
    print(f"⏰ Expected upload frequency: {upload_freq}")
    
    # Test endpoint
    try:
        response = requests.get(f"{expected_url}/healthcheck", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ S3 auth service is reachable")
            print(f"   Status: {health.get('status', 'unknown')}")
            return True
        else:
            print(f"⚠️  S3 auth service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach S3 auth service: {e}")
        return False


def check_upload_state():
    """Check upload state files"""
    print(f"\n📤 Checking Upload State")
    print("=" * 50)
    
    state_files = [
        "upload_utils/state_file_s3_partitioned.json",
        "state_file_s3_partitioned.json"
    ]
    
    for state_file in state_files:
        if os.path.exists(state_file):
            print(f"✅ Upload state file found: {state_file}")
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                if state:
                    print(f"📊 Jobs tracked: {len(state)}")
                    for job_id, job_state in list(state.items())[:2]:
                        last_time = job_state.get('last_processed_time', 'Never')
                        records = job_state.get('total_records_processed', 0)
                        print(f"   • {job_id}: {records} records, last: {last_time}")
                else:
                    print("📋 No jobs tracked yet")
                return True
            except Exception as e:
                print(f"⚠️  Could not read state file: {e}")
                return False
    
    print("📋 No upload state files found")
    return True


def check_miner_logs():
    """Check for miner log files"""
    print(f"\n📝 Checking Miner Logs")
    print("=" * 50)
    
    log_locations = [
        "logs/miner.log",
        "miner.log",
        "~/.bittensor/miners/logs/miner.log"
    ]
    
    for log_path in log_locations:
        expanded_path = os.path.expanduser(log_path)
        if os.path.exists(expanded_path):
            print(f"✅ Log file found: {expanded_path}")
            
            # Check recent log entries
            try:
                with open(expanded_path, 'r') as f:
                    lines = f.readlines()
                
                # Look for relevant log messages
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                upload_msgs = [line for line in recent_lines if 'upload' in line.lower() or 's3' in line.lower()]
                
                if upload_msgs:
                    print("📋 Recent upload-related logs:")
                    for line in upload_msgs[-3:]:  # Show last 3
                        print(f"   {line.strip()}")
                else:
                    print("📋 No recent upload logs found")
                
                return True
                
            except Exception as e:
                print(f"⚠️  Could not read log file: {e}")
    
    print("📋 No miner log files found")
    return True


def main():
    print("🔍 Miner Storage Quick Check")
    print("=" * 60)
    
    # Parse simple arguments
    netuid = None
    db_path = "SqliteMinerStorage.sqlite"
    
    if "--netuid" in sys.argv:
        try:
            idx = sys.argv.index("--netuid")
            if idx + 1 < len(sys.argv):
                netuid = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            pass
    
    if "--database" in sys.argv:
        try:
            idx = sys.argv.index("--database")
            if idx + 1 < len(sys.argv):
                db_path = sys.argv[idx + 1]
        except IndexError:
            pass
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python check_miner_storage.py [--netuid SUBNET] [--database PATH]")
        print("")
        print("Examples:")
        print("  python check_miner_storage.py --netuid 428  # Testnet check")
        print("  python check_miner_storage.py --netuid 46   # Mainnet check")
        return
    
    results = []
    
    # Run checks
    results.append(check_database(db_path))
    results.append(check_s3_config(netuid))
    results.append(check_upload_state())
    results.append(check_miner_logs())
    
    # Summary
    print(f"\n📋 Summary")
    print("=" * 30)
    
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ All checks passed ({passed}/{total})")
        if netuid == 428:
            print("🎉 Testnet miner storage looks good!")
            print("⏰ Uploads should happen every 5 minutes")
        else:
            print("🎉 Miner storage looks good!")
            print("⏰ Uploads should happen every 2 hours")
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("🔧 Review the issues above")
    
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
