#!/usr/bin/env python3
"""
Test Miner S3 Configuration
Quick script to verify miner S3 upload configuration and test authentication
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import bittensor as bt
from neurons.config import create_config, NeuronType
from upload_utils.s3_uploader import S3PartitionedUploader


def test_miner_s3_config(wallet_name, hotkey_name):
    """Test miner S3 configuration"""
    print("🔍 Testing Miner S3 Configuration")
    print("=" * 60)
    
    try:
        # Create config similar to how miner does it
        config = create_config(NeuronType.MINER)
        
        # Override with test parameters
        config.wallet.name = wallet_name
        config.wallet.hotkey = hotkey_name
        config.netuid = 428
        config.subtensor.network = "test"
        
        print(f"📋 Configuration:")
        print(f"   Wallet: {config.wallet.name}")
        print(f"   Hotkey: {config.wallet.hotkey}")
        print(f"   Netuid: {config.netuid}")
        print(f"   Network: {config.subtensor.network}")
        print(f"   Use Uploader: {getattr(config, 'use_uploader', 'Not set')}")
        print(f"   S3 Auth URL: {getattr(config, 's3_auth_url', 'Not set')}")
        print(f"   State File: {getattr(config, 'miner_upload_state_file', 'Not set')}")
        
        # Auto-configure S3 auth URL like miner does
        if config.netuid == 428:
            if not hasattr(config, 's3_auth_url') or config.s3_auth_url == "https://s3-auth-api.resilabs.ai":
                config.s3_auth_url = "https://s3-auth-api-testnet.resilabs.ai"
                print(f"✅ Auto-configured testnet S3 auth URL: {config.s3_auth_url}")
        
        # Load wallet and subtensor
        print(f"\n🔑 Loading Wallet and Subtensor...")
        wallet = bt.wallet(config=config)
        subtensor = bt.subtensor(config=config)
        
        print(f"✅ Wallet loaded:")
        print(f"   Coldkey: {wallet.coldkey.ss58_address}")
        print(f"   Hotkey: {wallet.hotkey.ss58_address}")
        
        # Test S3 uploader initialization
        print(f"\n☁️  Testing S3 Uploader Initialization...")
        try:
            s3_uploader = S3PartitionedUploader(
                db_path=config.neuron.database_name,
                subtensor=subtensor,
                wallet=wallet,
                s3_auth_url=config.s3_auth_url,
                state_file=config.miner_upload_state_file,
            )
            print(f"✅ S3 uploader initialized successfully")
            print(f"   Database path: {config.neuron.database_name}")
            print(f"   State file: {config.miner_upload_state_file}")
            
            # Test S3 authentication
            print(f"\n🔐 Testing S3 Authentication...")
            try:
                credentials = s3_uploader.s3_auth.get_credentials(
                    subtensor=subtensor,
                    wallet=wallet
                )
                
                if credentials:
                    print(f"✅ S3 authentication successful!")
                    print(f"   Bucket: {credentials.get('bucket_name', 'N/A')}")
                    print(f"   Region: {credentials.get('region', 'N/A')}")
                    print(f"   Upload URL: {credentials.get('url', 'N/A')}")
                    
                    return True
                else:
                    print(f"❌ S3 authentication failed - no credentials returned")
                    return False
                    
            except Exception as e:
                print(f"❌ S3 authentication error: {e}")
                return False
                
        except Exception as e:
            print(f"❌ S3 uploader initialization failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_miner_s3_config.py <wallet_name> <hotkey_name>")
        print("Example: python test_miner_s3_config.py 428_testnet_miner 428_testnet_miner_hotkey")
        return
    
    wallet_name = sys.argv[1]
    hotkey_name = sys.argv[2]
    
    success = test_miner_s3_config(wallet_name, hotkey_name)
    
    if success:
        print(f"\n🎉 SUCCESS! Your miner S3 configuration is working correctly.")
        print(f"\n📋 Next Steps:")
        print(f"   1. Restart your miner with explicit uploader flag:")
        print(f"      python neurons/miner.py --netuid 428 --subtensor.network test \\")
        print(f"          --wallet.name {wallet_name} --wallet.hotkey {hotkey_name} \\")
        print(f"          --use_uploader --logging.debug")
        print(f"   2. Monitor logs for S3 upload messages")
        print(f"   3. Check for upload state file: upload_utils/state_file_s3_partitioned.json")
        print(f"   4. Verify S3 folder creation after first upload (30 minutes)")
    else:
        print(f"\n❌ FAILED! There are issues with your S3 configuration.")
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Verify wallet is registered on testnet subnet 428")
        print(f"   2. Check internet connectivity")
        print(f"   3. Verify S3 auth service is reachable")
        print(f"   4. Run the official S3 test script: python test_testnet_s3_auth.py")


if __name__ == "__main__":
    main()
