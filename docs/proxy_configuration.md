# Proxy Configuration for RESI Validators

This guide covers the available proxy configuration options for RESI validators.

## Traditional Proxy Configuration

Configure a traditional proxy service for your validator:

### Command Line Configuration

```bash
python neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --proxy_url "http://username:password@proxy-server:port"
```

### Environment Variables

```bash
export HTTP_PROXY="http://username:password@proxy-server:port"
export HTTPS_PROXY="http://username:password@proxy-server:port"

python neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey
```

## ScrapingBee Configuration

ScrapingBee provides automatic proxy rotation, CAPTCHA solving, and browser fingerprinting.

### Setup Steps

1. Get your API key from [ScrapingBee.com](https://www.scrapingbee.com/)
2. Configure the API key:

```bash
# Add to .env file
echo "SCRAPINGBEE_API_KEY=your_api_key_here" >> .env

# Or export directly
export SCRAPINGBEE_API_KEY="your_api_key_here"
```

3. Enable ScrapingBee:

```bash
python neurons/validator.py \
    --netuid 46 \
    --subtensor.network finney \
    --wallet.name your_wallet \
    --wallet.hotkey your_hotkey \
    --use_scrapingbee
```

### Verification

On startup, you should see:
```
✅ ScrapingBee API configured successfully
   Using ScrapingBee for validator scraping operations
```