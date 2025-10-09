# Proxy Configuration Guide for RESI Validators

This guide explains how to configure proxy services for RESI validators to ensure reliable data validation and avoid IP blocking during spot-check validation.


## Option 1: Traditional Proxy Configuration

**Note:** Option 2 Recommedended
### Configuration

Add proxy configuration to your validator startup command:

```bash
# Basic proxy configuration
python neurons/validator.py \
    --netuid 13 \
    --subtensor.network finney \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --proxy_url "http://username:password@proxy-server:port"
```

### Environment Variables (Alternative)

You can also set proxy configuration via environment variables:

```bash
# Set in your .env file or shell
export HTTP_PROXY="http://username:password@proxy-server:port"
export HTTPS_PROXY="http://username:password@proxy-server:port"

# Then run validator normally
python neurons/validator.py --netuid 13 --subtensor.network finney --wallet.name your_wallet --wallet.hotkey your_hotkey
```

## Option 2: ScrapingBee Configuration (Recommended)

ScrapingBee is a premium web scraping API that handles proxy rotation, CAPTCHA solving, and browser fingerprinting automatically.

### Setup Steps

#### 1. Get ScrapingBee API Key

1. Visit [ScrapingBee.com](https://www.scrapingbee.com/)
2. Sign up for an account
3. Choose a plan - Use free trial for testing
4. Get your API key from the dashboard

#### 2. Configure Environment Variables

Add your ScrapingBee API key to your environment:

```bash
# Add to .env file
echo "SCRAPINGBEE_API_KEY=your_api_key_here" >> .env

# Or export directly
export SCRAPINGBEE_API_KEY="your_api_key_here"
```

#### 3. Enable ScrapingBee in Validator

```bash
# Enable ScrapingBee for your validator
python neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --use_scrapingbee
```

#### 4. Verify Configuration

When the validator starts, you should see:

```
✅ ScrapingBee API configured successfully
   Using ScrapingBee for validator scraping operations
```