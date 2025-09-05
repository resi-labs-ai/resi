#!/usr/bin/env python3
"""
Bootstrap script for Testnet Subnet 428
Helps you check subnet status and start both validator and miner if needed
"""

import subprocess
import sys
import os
from dotenv import load_dotenv
import time

load_dotenv()

def run_command(cmd, capture_output=True):
    """Run a command and return the result"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            # For interactive commands
            result = subprocess.run(cmd, shell=True, timeout=30)
            return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_subnet_status():
    """Check if subnet 428 exists and has validators"""
    print("🔍 Checking Subnet 428 status...")
    
    # Check if subnet exists
    success, stdout, stderr = run_command("btcli subnet list --subtensor.network test")
    
    if not success:
        print(f"❌ Could not check subnet list: {stderr}")
        return False, False
    
    # Check if 428 is in the list
    subnet_exists = "428" in stdout
    print(f"{'✅' if subnet_exists else '❌'} Subnet 428 {'exists' if subnet_exists else 'not found'}")
    
    if not subnet_exists:
        print("💡 You may need to create the subnet first or check the subnet ID")
        return False, False
    
    # Check metagraph for validators
    print("🔍 Checking for existing validators...")
    success, stdout, stderr = run_command("btcli subnet metagraph --netuid 428 --subtensor.network test")
    
    if not success:
        print(f"⚠️  Could not check metagraph: {stderr}")
        return subnet_exists, False
    
    # Look for validator indicators in output
    has_validators = "validator" in stdout.lower() or "stake" in stdout.lower()
    lines = stdout.split('\n')
    validator_count = len([line for line in lines if 'uid' in line.lower() and line.strip()])
    
    print(f"📊 Found {validator_count} registered participants")
    print(f"{'✅' if has_validators else '❌'} {'Validators detected' if has_validators else 'No validators detected'}")
    
    return subnet_exists, has_validators

def check_wallet_status():
    """Check wallet and registration status"""
    wallet_name = os.getenv('WALLET_NAME', 'your_testnet_wallet_name')
    hotkey_name = os.getenv('WALLET_HOTKEY', 'your_testnet_hotkey_name')
    
    print(f"🔍 Checking wallet status for {wallet_name}...")
    
    # Check wallet overview
    success, stdout, stderr = run_command(f"btcli wallet overview --wallet.name {wallet_name} --subtensor.network test")
    
    if not success:
        print(f"❌ Could not check wallet: {stderr}")
        print(f"💡 Make sure wallet '{wallet_name}' exists")
        return False
    
    print("✅ Wallet found")
    
    # Check if registered on subnet 428
    if "428" in stdout:
        print("✅ Already registered on subnet 428")
        return True
    else:
        print("❌ Not registered on subnet 428")
        return False

def register_on_subnet():
    """Register on subnet 428"""
    wallet_name = os.getenv('WALLET_NAME')
    hotkey_name = os.getenv('WALLET_HOTKEY')
    
    if not wallet_name or wallet_name == 'your_testnet_wallet_name':
        print("❌ Please set WALLET_NAME in .env file")
        return False
    
    if not hotkey_name or hotkey_name == 'your_testnet_hotkey_name':
        print("❌ Please set WALLET_HOTKEY in .env file")
        return False
    
    print(f"🔐 Registering {wallet_name}/{hotkey_name} on subnet 428...")
    
    cmd = f"btcli subnet register --netuid 428 --subtensor.network test --wallet.name {wallet_name} --wallet.hotkey {hotkey_name}"
    success, stdout, stderr = run_command(cmd, capture_output=False)
    
    if success:
        print("✅ Registration successful!")
        return True
    else:
        print(f"❌ Registration failed: {stderr}")
        return False

def start_validator():
    """Start validator in background"""
    wallet_name = os.getenv('WALLET_NAME')
    validator_hotkey = f"validator_{os.getenv('WALLET_HOTKEY')}"
    
    print(f"🚀 Starting validator with hotkey: {validator_hotkey}")
    print("💡 This will run in the background. Check validator.log for output.")
    
    cmd = f"""python neurons/validator.py \
        --netuid 428 \
        --subtensor.network test \
        --wallet.name {wallet_name} \
        --wallet.hotkey {validator_hotkey} \
        --logging.debug > validator.log 2>&1 &"""
    
    os.system(cmd)
    time.sleep(3)  # Give it time to start
    
    # Check if process started
    success, stdout, stderr = run_command("ps aux | grep 'neurons/validator.py' | grep -v grep")
    
    if success and stdout:
        print("✅ Validator started successfully!")
        print("📝 Monitor with: tail -f validator.log")
        return True
    else:
        print("❌ Validator may not have started properly")
        print("📝 Check validator.log for errors")
        return False

def start_miner():
    """Start miner in background"""
    wallet_name = os.getenv('WALLET_NAME')
    hotkey_name = os.getenv('WALLET_HOTKEY')
    
    print(f"🚀 Starting miner with hotkey: {hotkey_name}")
    print("💡 This will run in the background. Check miner.log for output.")
    
    cmd = f"""python neurons/miner.py \
        --netuid 428 \
        --subtensor.network test \
        --wallet.name {wallet_name} \
        --wallet.hotkey {hotkey_name} \
        --logging.debug > miner.log 2>&1 &"""
    
    os.system(cmd)
    time.sleep(3)  # Give it time to start
    
    # Check if process started
    success, stdout, stderr = run_command("ps aux | grep 'neurons/miner.py' | grep -v grep")
    
    if success and stdout:
        print("✅ Miner started successfully!")
        print("📝 Monitor with: tail -f miner.log")
        return True
    else:
        print("❌ Miner may not have started properly")
        print("📝 Check miner.log for errors")
        return False

def main():
    """Main bootstrap process"""
    print("🚀 Bootstrapping Testnet Subnet 428\n")
    
    # Check environment
    if not os.path.exists('.env'):
        print("❌ No .env file found. Copy .env.testnet to .env and configure it.")
        return
    
    wallet_name = os.getenv('WALLET_NAME')
    if not wallet_name or wallet_name == 'your_testnet_wallet_name':
        print("❌ Please configure WALLET_NAME in .env file")
        return
    
    # Step 1: Check subnet status
    subnet_exists, has_validators = check_subnet_status()
    
    if not subnet_exists:
        print("\n❌ Subnet 428 not found. Make sure you created it or check the subnet ID.")
        return
    
    # Step 2: Check wallet status
    print(f"\n" + "="*50)
    is_registered = check_wallet_status()
    
    # Step 3: Register if needed
    if not is_registered:
        print(f"\n" + "="*50)
        print("🔐 Registration required...")
        if not register_on_subnet():
            return
    
    # Step 4: Handle validator situation
    print(f"\n" + "="*50)
    if not has_validators:
        print("⚠️  No validators detected on subnet 428")
        print("🚀 Starting validator to bootstrap the network...")
        
        # Create validator hotkey if needed
        validator_hotkey = f"validator_{os.getenv('WALLET_HOTKEY')}"
        print(f"💡 Creating validator hotkey: {validator_hotkey}")
        
        cmd = f"btcli wallet new_hotkey --wallet.name {wallet_name} --wallet.hotkey {validator_hotkey}"
        run_command(cmd, capture_output=False)
        
        # Register validator
        cmd = f"btcli subnet register --netuid 428 --subtensor.network test --wallet.name {wallet_name} --wallet.hotkey {validator_hotkey}"
        run_command(cmd, capture_output=False)
        
        # Start validator
        if start_validator():
            print("⏳ Waiting 10 seconds for validator to initialize...")
            time.sleep(10)
        else:
            print("❌ Could not start validator")
            return
    else:
        print("✅ Validators already running on subnet 428")
    
    # Step 5: Start miner
    print(f"\n" + "="*50)
    print("🚀 Starting miner...")
    
    if start_miner():
        print(f"\n🎉 Bootstrap complete!")
        print(f"""
📊 MONITORING COMMANDS:
- Wallet overview: btcli wallet overview --wallet.name {wallet_name} --subtensor.network test
- Subnet status: btcli subnet metagraph --netuid 428 --subtensor.network test  
- Miner logs: tail -f miner.log
- Validator logs: tail -f validator.log (if running)

🛑 STOPPING COMMANDS:
- Stop miner: pkill -f "neurons/miner.py"
- Stop validator: pkill -f "neurons/validator.py"
        """)
    else:
        print("❌ Could not start miner")

if __name__ == "__main__":
    main()
