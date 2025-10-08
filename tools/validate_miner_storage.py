#!/usr/bin/env python3
"""
Miner Storage Validation Script
Validates that miners are:
1. Saving data locally in SQLite database
2. Uploading data to S3 with correct frequency
3. Using correct S3 auth endpoints for testnet vs mainnet
"""

import os
import sys
import sqlite3
import json
import datetime as dt
import argparse
import requests
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import bittensor as bt
from upload_utils.s3_utils import S3Auth
from storage.miner.sqlite_miner_storage import SqliteMinerStorage


class MinerStorageValidator:
    """Validates miner storage functionality"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config.neuron.database_name
        self.s3_auth_url = config.s3_auth_url
        
        # Determine expected S3 auth URL based on subnet
        if config.netuid == 428:  # Testnet
            self.expected_s3_auth_url = "https://api-staging.resilabs.ai"
            self.expected_upload_frequency = 5  # minutes
            self.network_type = "Testnet"
        else:  # Mainnet
            self.expected_s3_auth_url = "https://api.resilabs.ai"
            self.expected_upload_frequency = 120  # minutes (2 hours)
            self.network_type = "Mainnet"
    
    def validate_local_storage(self) -> bool:
        """Validate local SQLite storage functionality"""
        print(f"\n🗄️  Validating Local Storage")
        print("=" * 50)
        
        success = True
        
        # Check if database file exists
        if not os.path.exists(self.db_path):
            print(f"❌ Database file not found: {self.db_path}")
            return False
        
        print(f"✅ Database file exists: {self.db_path}")
        
        try:
            # Connect to database and check structure
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                cursor = conn.cursor()
                
                # Check if DataEntity table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='DataEntity'
                """)
                
                if not cursor.fetchone():
                    print("❌ DataEntity table not found in database")
                    return False
                
                print("✅ DataEntity table exists")
                
                # Get table info
                cursor.execute("PRAGMA table_info(DataEntity)")
                columns = cursor.fetchall()
                expected_columns = ['uri', 'datetime', 'timeBucketId', 'source', 'label', 'content', 'contentSizeBytes']
                
                actual_columns = [col[1] for col in columns]
                missing_columns = set(expected_columns) - set(actual_columns)
                
                if missing_columns:
                    print(f"❌ Missing columns: {missing_columns}")
                    success = False
                else:
                    print("✅ All required columns present")
                
                # Check data count
                cursor.execute("SELECT COUNT(*) FROM DataEntity")
                row_count = cursor.fetchone()[0]
                print(f"📊 Total data entities: {row_count:,}")
                
                if row_count == 0:
                    print("⚠️  No data found - miner may not have started scraping yet")
                else:
                    # Show recent data
                    cursor.execute("""
                        SELECT source, label, datetime, LENGTH(content) as content_size
                        FROM DataEntity 
                        ORDER BY datetime DESC 
                        LIMIT 5
                    """)
                    
                    recent_data = cursor.fetchall()
                    print("\n📋 Recent data entries:")
                    for row in recent_data:
                        source, label, datetime_str, content_size = row
                        print(f"   • Source: {source}, Label: {label}, Size: {content_size} bytes, Time: {datetime_str}")
                
                # Check database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size_bytes = cursor.fetchone()[0]
                db_size_mb = db_size_bytes / (1024 * 1024)
                max_size_gb = getattr(self.config.neuron, 'max_database_size_gb_hint', 250)
                
                print(f"💾 Database size: {db_size_mb:.2f} MB (limit: {max_size_gb} GB)")
                
                if db_size_mb > max_size_gb * 1024:
                    print(f"⚠️  Database size exceeds configured limit")
                
        except Exception as e:
            print(f"❌ Database validation error: {e}")
            success = False
        
        return success
    
    def validate_s3_configuration(self) -> bool:
        """Validate S3 upload configuration"""
        print(f"\n☁️  Validating S3 Configuration ({self.network_type})")
        print("=" * 50)
        
        success = True
        
        # Check S3 auth URL
        print(f"🔗 Current S3 auth URL: {self.s3_auth_url}")
        print(f"🎯 Expected S3 auth URL: {self.expected_s3_auth_url}")
        
        if self.s3_auth_url != self.expected_s3_auth_url:
            print(f"⚠️  S3 auth URL mismatch for {self.network_type}")
            print(f"   Consider using: --s3_auth_url {self.expected_s3_auth_url}")
        else:
            print("✅ S3 auth URL is correct")
        
        # Test S3 auth endpoint
        try:
            response = requests.get(f"{self.s3_auth_url}/healthcheck", timeout=10)
            if response.status_code == 200:
                print("✅ S3 auth service is reachable")
                health_data = response.json()
                print(f"   Service status: {health_data.get('status', 'unknown')}")
            else:
                print(f"⚠️  S3 auth service returned status {response.status_code}")
                success = False
        except Exception as e:
            print(f"❌ Cannot reach S3 auth service: {e}")
            success = False
        
        # Check upload frequency expectation
        print(f"⏰ Expected upload frequency: {self.expected_upload_frequency} minutes")
        
        return success
    
    def test_s3_auth(self, wallet, subtensor) -> bool:
        """Test S3 authentication with the configured endpoint"""
        print(f"\n🔐 Testing S3 Authentication")
        print("=" * 50)
        
        try:
            s3_auth = S3Auth(self.s3_auth_url)
            
            print("🔑 Attempting to get S3 credentials...")
            credentials = s3_auth.get_credentials(
                subtensor=subtensor,
                wallet=wallet
            )
            
            if credentials:
                print("✅ Successfully obtained S3 credentials")
                print(f"   Bucket: {credentials.get('bucket_name', 'N/A')}")
                print(f"   Region: {credentials.get('region', 'N/A')}")
                print("   ✅ Access credentials obtained")
                return True
            else:
                print("❌ Failed to obtain S3 credentials")
                return False
                
        except Exception as e:
            print(f"❌ S3 authentication error: {e}")
            return False
    
    def check_upload_state(self) -> bool:
        """Check S3 upload state file"""
        print(f"\n📤 Checking Upload State")
        print("=" * 50)
        
        # Look for state files
        state_files = [
            "upload_utils/state_file_s3_partitioned.json",
            f"upload_utils/state_file_s3_partitioned.json"
        ]
        
        state_found = False
        for state_file in state_files:
            if os.path.exists(state_file):
                state_found = True
                print(f"✅ Upload state file found: {state_file}")
                
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    if state_data:
                        print(f"📊 Jobs tracked: {len(state_data)}")
                        for job_id, job_state in list(state_data.items())[:3]:  # Show first 3
                            last_processed = job_state.get('last_processed_time', 'Never')
                            records_processed = job_state.get('total_records_processed', 0)
                            print(f"   • Job {job_id}: {records_processed} records, last: {last_processed}")
                        
                        if len(state_data) > 3:
                            print(f"   ... and {len(state_data) - 3} more jobs")
                    else:
                        print("📋 No upload jobs tracked yet")
                        
                except Exception as e:
                    print(f"⚠️  Could not read state file: {e}")
                
                break
        
        if not state_found:
            print("📋 No upload state files found - uploads may not have started yet")
        
        return True
    
    def run_validation(self, wallet=None, subtensor=None) -> bool:
        """Run complete validation"""
        print(f"🔍 Miner Storage Validation for {self.network_type} (Subnet {self.config.netuid})")
        print("=" * 70)
        
        results = []
        
        # Validate local storage
        results.append(self.validate_local_storage())
        
        # Validate S3 configuration
        results.append(self.validate_s3_configuration())
        
        # Test S3 auth if wallet provided
        if wallet and subtensor:
            results.append(self.test_s3_auth(wallet, subtensor))
        else:
            print(f"\n⚠️  Skipping S3 auth test (no wallet/subtensor provided)")
        
        # Check upload state
        results.append(self.check_upload_state())
        
        # Summary
        print(f"\n📋 Validation Summary")
        print("=" * 30)
        
        passed = sum(results)
        total = len(results)
        
        if all(results):
            print(f"✅ All validations passed ({passed}/{total})")
            print(f"🎉 Miner storage is properly configured for {self.network_type}!")
            return True
        else:
            print(f"⚠️  {passed}/{total} validations passed")
            print(f"🔧 Please review the issues above")
            return False


def main():
    # Simple argument parsing without conflicting with bittensor
    import sys
    
    # Default values
    netuid = 46
    database_name = "SqliteMinerStorage.sqlite"
    s3_auth_url = None
    wallet_name = None
    wallet_hotkey = None
    subtensor_network = "finney"
    
    # Parse simple arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--netuid" and i + 1 < len(sys.argv):
            netuid = int(sys.argv[i + 1])
            i += 2
        elif arg == "--database_name" and i + 1 < len(sys.argv):
            database_name = sys.argv[i + 1]
            i += 2
        elif arg == "--s3_auth_url" and i + 1 < len(sys.argv):
            s3_auth_url = sys.argv[i + 1]
            i += 2
        elif arg == "--wallet.name" and i + 1 < len(sys.argv):
            wallet_name = sys.argv[i + 1]
            i += 2
        elif arg == "--wallet.hotkey" and i + 1 < len(sys.argv):
            wallet_hotkey = sys.argv[i + 1]
            i += 2
        elif arg == "--subtensor.network" and i + 1 < len(sys.argv):
            subtensor_network = sys.argv[i + 1]
            i += 2
        elif arg in ["-h", "--help"]:
            print("Miner Storage Validation Script")
            print("Usage: python validate_miner_storage.py [options]")
            print("")
            print("Options:")
            print("  --netuid INT              Subnet netuid (default: 46)")
            print("  --database_name STR       Database file path (default: SqliteMinerStorage.sqlite)")
            print("  --s3_auth_url STR         S3 auth URL (auto-detected if not provided)")
            print("  --wallet.name STR         Wallet name for S3 auth test")
            print("  --wallet.hotkey STR       Hotkey name for S3 auth test")
            print("  --subtensor.network STR   Subtensor network (default: finney)")
            print("")
            print("Examples:")
            print("  # Testnet validation")
            print("  python validate_miner_storage.py --netuid 428 --subtensor.network test")
            print("")
            print("  # Mainnet validation with S3 test")
            print("  python validate_miner_storage.py --netuid 46 --wallet.name my_wallet --wallet.hotkey my_hotkey")
            return
        else:
            i += 1
    
    # Create args object
    class Args:
        pass
    
    args = Args()
    args.netuid = netuid
    args.database_name = database_name
    args.s3_auth_url = s3_auth_url
    setattr(args, 'wallet.name', wallet_name)
    setattr(args, 'wallet.hotkey', wallet_hotkey)
    setattr(args, 'subtensor.network', subtensor_network)
    
    # Create mock config
    class MockConfig:
        def __init__(self):
            self.netuid = args.netuid
            self.neuron = MockNeuronConfig()
            
            # Auto-configure S3 auth URL if not provided
            if args.s3_auth_url:
                self.s3_auth_url = args.s3_auth_url
            elif args.netuid == 428:  # Testnet
                self.s3_auth_url = "https://api-staging.resilabs.ai"
            else:  # Mainnet
                self.s3_auth_url = "https://api.resilabs.ai"
    
    class MockNeuronConfig:
        def __init__(self):
            self.database_name = args.database_name
            self.max_database_size_gb_hint = 250
    
    config = MockConfig()
    
    # Create validator
    validator = MinerStorageValidator(config)
    
    # Setup wallet and subtensor if provided
    wallet = None
    subtensor = None
    
    if hasattr(args, 'wallet.name') and getattr(args, 'wallet.name'):
        try:
            wallet = bt.wallet(name=getattr(args, 'wallet.name'), hotkey=getattr(args, 'wallet.hotkey'))
            subtensor = bt.subtensor(network=args.subtensor.network)
        except Exception as e:
            print(f"⚠️  Could not setup wallet/subtensor: {e}")
    
    # Run validation
    success = validator.run_validation(wallet, subtensor)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
