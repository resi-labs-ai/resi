#!/usr/bin/env python3
"""
Testnet-focused test script for RapidAPI Zillow integration on Subnet 428
Run this to verify everything works before deploying to testnet
"""

import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_testnet_prerequisites():
    """Check if all testnet prerequisites are met"""
    print("🔍 Checking testnet prerequisites...")
    
    issues = []
    
    # Check API key
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        issues.append("❌ RAPIDAPI_KEY not found in .env file")
    elif len(api_key) < 20:
        issues.append("❌ RAPIDAPI_KEY seems too short (check for typos)")
    else:
        print(f"✅ API key found: {api_key[:10]}...")
    
    # Check testnet configuration
    netuid = os.getenv('NETUID')
    network = os.getenv('SUBTENSOR_NETWORK')
    wallet_name = os.getenv('WALLET_NAME')
    hotkey_name = os.getenv('WALLET_HOTKEY')
    
    if netuid != '428':
        issues.append(f"❌ NETUID should be 428 for your testnet, found: {netuid}")
    else:
        print(f"✅ NETUID set to 428 (your testnet)")
    
    if network != 'test':
        issues.append(f"❌ SUBTENSOR_NETWORK should be 'test', found: {network}")
    else:
        print(f"✅ Network set to testnet")
    
    if not wallet_name or wallet_name == 'your_testnet_wallet_name':
        issues.append("❌ WALLET_NAME not configured (create wallet first)")
    else:
        print(f"✅ Wallet name: {wallet_name}")
        
    if not hotkey_name or hotkey_name == 'your_testnet_hotkey_name':
        issues.append("❌ WALLET_HOTKEY not configured (create hotkey first)")
    else:
        print(f"✅ Hotkey name: {hotkey_name}")
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} detected. Need Python 3.8+")
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")
    
    # Check required packages
    try:
        import httpx
        print("✅ httpx available")
    except ImportError:
        issues.append("❌ httpx not installed. Run: pip install httpx")
    
    try:
        import bittensor
        print("✅ bittensor available")
    except ImportError:
        issues.append("❌ bittensor not installed. Run: pip install -r requirements.txt")
    
    # Check custom modules with updated path
    try:
        from scraping.zillow.rapid_zillow_scraper import ZillowRapidAPIScraper
        print("✅ ZillowRapidAPIScraper available")
    except ImportError as e:
        issues.append(f"❌ Import error: {e}")
        issues.append("💡 Make sure you've updated the import path after renaming folders")
    
    if issues:
        print("\n🚨 Issues found:")
        for issue in issues:
            print(f"  {issue}")
        return False
    
    print("✅ All prerequisites met!")
    return True

async def test_api_connection():
    """Test basic API connection"""
    print("\n🔗 Testing API connection...")
    
    try:
        import httpx
        
        headers = {
            'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
            'X-RapidAPI-Host': 'zillow-com1.p.rapidapi.com'
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                'https://zillow-com1.p.rapidapi.com/propertyExtendedSearch',
                headers=headers,
                params={
                    'location': '06424',  # East Hampton, CT (from your example)
                    'status_type': 'ForSale',
                    'home_type': 'Houses',
                    'page': '1'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                props = data.get('props', [])
                print(f"✅ API connection successful! Found {len(props)} properties")
                
                if props:
                    first_prop = props[0]
                    print(f"📍 Sample property: {first_prop.get('address', 'N/A')}")
                    print(f"💰 Price: ${first_prop.get('price', 'N/A')}")
                
                return True
            elif response.status_code == 429:
                print("❌ Rate limited. Wait a minute and try again.")
                return False
            else:
                print(f"❌ API error: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

async def test_scraper():
    """Test the scraper with updated import path"""
    print("\n🏠 Testing Zillow scraper...")
    
    try:
        from scraping.zillow.rapid_zillow_scraper import ZillowRapidAPIScraper
        from scraping.scraper import ScrapeConfig
        from common.data import DataLabel
        
        scraper = ZillowRapidAPIScraper()
        
        config = ScrapeConfig(
            labels=[
                DataLabel(value='zip:06424'),  # Your test zip code
                DataLabel(value='status:forsale')
            ],
            entity_limit=3  # Small test
        )
        
        entities = await scraper.scrape(config)
        
        if entities:
            print(f"✅ Scraped {len(entities)} properties successfully!")
            
            # Show details of first property
            first_entity = entities[0]
            content = json.loads(first_entity.content.decode())
            
            print(f"📍 Address: {content.get('address', 'N/A')}")
            print(f"💰 Price: ${content.get('price', 'N/A')}")
            print(f"🏠 Type: {content.get('property_type', 'N/A')}")
            print(f"🛏️  Bedrooms: {content.get('bedrooms', 'N/A')}")
            print(f"🛁 Bathrooms: {content.get('bathrooms', 'N/A')}")
            print(f"📏 Living Area: {content.get('living_area', 'N/A')} sq ft")
            print(f"🔗 URI: {first_entity.uri}")
            print(f"🏷️  Label: {first_entity.label.value if first_entity.label else 'None'}")
            
            return entities
        else:
            print("❌ No properties scraped")
            return []
            
    except Exception as e:
        print(f"❌ Scraper test failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_bittensor_config():
    """Test Bittensor configuration for testnet"""
    print("\n⛓️  Testing Bittensor testnet configuration...")
    
    try:
        import bittensor as bt
        
        # Test configuration parsing
        wallet_name = os.getenv('WALLET_NAME')
        hotkey_name = os.getenv('WALLET_HOTKEY')
        netuid = int(os.getenv('NETUID', 428))
        network = os.getenv('SUBTENSOR_NETWORK', 'test')
        
        print(f"✅ Configuration parsed:")
        print(f"  - Wallet: {wallet_name}")
        print(f"  - Hotkey: {hotkey_name}")
        print(f"  - Network: {network}")
        print(f"  - Subnet: {netuid}")
        
        # Test if wallet exists (don't load it, just check)
        try:
            # This is just a configuration test, not actually loading the wallet
            print(f"💡 Make sure to create wallet: btcli wallet new_coldkey --wallet.name {wallet_name}")
            print(f"💡 Make sure to create hotkey: btcli wallet new_hotkey --wallet.name {wallet_name} --wallet.hotkey {hotkey_name}")
            
            return True
        except Exception as e:
            print(f"⚠️  Wallet check: {e}")
            return True  # Config is still valid even if wallet doesn't exist yet
            
    except Exception as e:
        print(f"❌ Bittensor config test failed: {e}")
        return False

def show_deployment_instructions():
    """Show testnet deployment instructions"""
    wallet_name = os.getenv('WALLET_NAME', 'your_wallet')
    hotkey_name = os.getenv('WALLET_HOTKEY', 'your_hotkey')
    
    print(f"""
🚀 TESTNET DEPLOYMENT INSTRUCTIONS

1. **Create Bittensor Wallets (if not done):**
   # Create wallet (will prompt for password)
   btcli wallet new_coldkey --wallet.name {wallet_name}
   
   # Create miner hotkey
   btcli wallet new_hotkey --wallet.name {wallet_name} --wallet.hotkey {hotkey_name}
   
   # Create validator hotkey (if running validator)
   btcli wallet new_hotkey --wallet.name {wallet_name} --wallet.hotkey validator_{hotkey_name}

2. **Get Testnet TAO (if needed):**
   # Join Bittensor Discord: https://discord.gg/bittensor
   # Ask for testnet TAO in #testnet-faucet channel
   # Or use faucet: https://faucet.bittensor.com/

3. **Check Your Testnet Subnet:**
   # See if validators are already running
   btcli subnet show --netuid 428 --subtensor.network test
   
   # Check metagraph
   btcli subnet metagraph --netuid 428 --subtensor.network test

4. **Register on Testnet Subnet 428:**
   # Register miner
   btcli subnet register --netuid 428 --subtensor.network test --wallet.name {wallet_name} --wallet.hotkey {hotkey_name}
   
   # Register validator (if running one)
   btcli subnet register --netuid 428 --subtensor.network test --wallet.name {wallet_name} --wallet.hotkey validator_{hotkey_name}

5. **Bootstrap Your Testnet (IMPORTANT!):**
   # If no validators exist, you need to run both:
   
   # Terminal 1 - Start Validator:
   python neurons/validator.py \\
     --netuid 428 \\
     --subtensor.network test \\
     --wallet.name {wallet_name} \\
     --wallet.hotkey validator_{hotkey_name} \\
     --logging.debug
   
   # Terminal 2 - Start Miner:
   python neurons/miner.py \\
     --netuid 428 \\
     --subtensor.network test \\
     --wallet.name {wallet_name} \\
     --wallet.hotkey {hotkey_name} \\
     --logging.debug

6. **Password Handling:**
   # Bittensor will prompt for passwords when starting
   # For automation, you can set (KEEP SECURE!):
   # COLDKEY_PASSWORD=your_password in .env
   # HOTKEY_PASSWORD=your_password in .env

7. **Monitor Your Setup:**
   # Check registration status
   btcli wallet overview --wallet.name {wallet_name} --subtensor.network test
   
   # Monitor miner logs
   tail -f miner.log
   
   # Monitor validator logs  
   tail -f validator.log

8. **Invite Others:**
   # Share your testnet details to grow the network:
   # Network: test
   # Subnet ID: 428
   # Registration: btcli subnet register --netuid 428 --subtensor.network test
""")

async def main():
    """Run all testnet tests"""
    print("🚀 RapidAPI Zillow Testnet Integration Test (Subnet 428)\n")
    
    # Check prerequisites
    if not check_testnet_prerequisites():
        print("\n❌ Prerequisites not met. Please fix issues above.")
        return
    
    # Test Bittensor configuration
    if not test_bittensor_config():
        print("\n❌ Bittensor configuration failed.")
        return
    
    # Test API connection
    if not await test_api_connection():
        print("\n❌ API connection failed.")
        return
    
    # Test scraper
    entities = await test_scraper()
    if not entities:
        print("\n❌ Scraper test failed.")
        return
    
    # Final summary
    print(f"\n🎯 TESTNET TEST SUMMARY:")
    print(f"✅ Prerequisites: Passed")
    print(f"✅ Bittensor Config: Passed") 
    print(f"✅ API Connection: Passed")
    print(f"✅ Scraper: Passed ({len(entities)} properties)")
    
    print(f"\n🎉 All tests passed! Ready for testnet deployment.")
    
    show_deployment_instructions()

if __name__ == "__main__":
    asyncio.run(main())
