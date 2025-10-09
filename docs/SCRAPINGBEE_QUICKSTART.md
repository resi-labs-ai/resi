# RESI ScrapingBee Integration - Quick Reference

## Overview

RESI validators now support ScrapingBee API integration for reliable, professional web scraping without IP blocking concerns.

## Quick Setup

### 1. Get ScrapingBee API Key
1. Visit [ScrapingBee.com](https://www.scrapingbee.com/)
2. Sign up and choose a plan (Professional recommended: $99/month)
3. Get your API key from dashboard

### 2. Configure Environment
```bash
# Add to .env file
echo "SCRAPINGBEE_API_KEY=your_api_key_here" >> .env
```

### 3. Run Validator with ScrapingBee
```bash
# Testnet
python neurons/validator.py --netuid 428 --subtensor.network test --use_scrapingbee --wallet.name miner --wallet.hotkey default --logging.debug

# Mainnet  
python neurons/validator.py --netuid 46 --subtensor.network finney --use_scrapingbee --wallet.name miner --wallet.hotkey default --logging.debug
```

## Requirements

- **Mainnet**: Proxy configuration (ScrapingBee or traditional) is **MANDATORY**
- **Testnet**: Proxy configuration is optional but recommended

## Complete Documentation

- **[Complete Proxy Guide](./PROXY_CONFIGURATION.md)** - Full configuration options
- **[ScrapingBee Examples](./SCRAPINGBEE_EXAMPLES.md)** - Practical implementation examples  
- **[Validator Setup Guide](../dev-docs/0036-validator-setup-guide.md)** - Complete EC2 deployment guide