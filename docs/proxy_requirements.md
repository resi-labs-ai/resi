# Proxy Requirements for Validators

## Overview

Validators in the Resi Labs subnet **REQUIRE** proxy services for production deployment on mainnet. This is essential for Tier 3 spot-check validation, where validators directly scrape real estate websites to verify miner-submitted data.

## Why Proxies Are Required

### Tier 3 Spot-Check Validation Process:
1. **Miner submits** real estate listings with URLs
2. **Validator receives** submission for validation
3. **Validator performs** 3-tier validation:
   - **Tier 1**: Quantity & timeliness checks
   - **Tier 2**: Data quality & completeness checks  
   - **Tier 3**: **Direct website scraping** to verify URLs ← **REQUIRES PROXY**

### Without Proxies:
- ❌ **IP bans** from real estate websites (Zillow, Realtor.com, etc.)
- ❌ **Rate limiting** preventing proper validation
- ❌ **Reduced validation accuracy** leading to poor scoring
- ❌ **Validator downtime** due to blocked requests

## Recommended Proxy Service: Webshare.io

Based on our analysis, [Webshare.io](https://www.webshare.io/pricing) offers the best solution for validator needs:

### **Recommended Plan: Rotating Residential Proxy**
- **100 GB plan**: $225/month (currently 50% off = **$112.50/month**)
- **99.97% uptime** - Critical for continuous validation
- **80M+ residential IPs** - Excellent for avoiding detection
- **195 countries coverage** - Global real estate data support
- **HTTP/SOCKS5 support** - Compatible with our scrapers

### **Alternative Plans:**
- **25 GB plan**: $65/month (50% off) - For lower-volume validators
- **250 GB plan**: $500/month (50% off) - For high-volume validators

## Configuration

### Mainnet (REQUIRED)
```bash
python neurons/validator.py \
  --netuid 13 \
  --proxy_url "http://username:password@proxy-server:port" \
  --wallet.name your_validator \
  --wallet.hotkey your_hotkey
```

### Testnet (Optional but Recommended)
```bash
python neurons/validator.py \
  --netuid 428 \
  --subtensor.network test \
  --proxy_url "http://username:password@proxy-server:port" \
  --wallet.name your_testnet_validator \
  --wallet.hotkey your_testnet_hotkey
```

### Webshare.io Configuration Example
```bash
# After purchasing Webshare.io plan, use their provided credentials:
python neurons/validator.py \
  --netuid 13 \
  --proxy_url "http://rotating-residential.webshare.io:9000" \
  --proxy_username "your-webshare-username" \
  --proxy_password "your-webshare-password" \
  --wallet.name your_validator \
  --wallet.hotkey your_hotkey
```

## Proxy Setup Steps

### 1. Purchase Webshare.io Plan
1. Visit [Webshare.io Pricing](https://www.webshare.io/pricing)
2. Select **Rotating Residential Proxy** plan (100GB recommended)
3. Complete purchase and account setup

### 2. Get Proxy Credentials
1. Login to Webshare.io dashboard
2. Navigate to proxy settings
3. Copy your proxy endpoint, username, and password

### 3. Configure Validator
```bash
# Method 1: Command line arguments
python neurons/validator.py \
  --proxy_url "http://rotating-residential.webshare.io:9000" \
  --proxy_username "your-username" \
  --proxy_password "your-password"

# Method 2: Environment variables
export HTTP_PROXY="http://username:password@rotating-residential.webshare.io:9000"
export HTTPS_PROXY="http://username:password@rotating-residential.webshare.io:9000"
python neurons/validator.py
```

### 4. Verify Configuration
Check validator logs for:
```
✅ Proxy configured: rotating-residential.webshare.io:9000
✅ Scraper proxy configuration applied
```

## Cost Analysis

### Monthly Proxy Costs vs Validator Revenue:
- **Proxy cost**: ~$112.50/month (100GB plan with 50% discount)
- **Validator revenue**: Varies based on stake and performance
- **ROI**: Essential for maintaining validation accuracy and avoiding downtime

### Cost Optimization:
- **Start with 25GB plan** ($32.50/month) for testing
- **Monitor usage** in Webshare.io dashboard
- **Scale up** to 100GB+ based on validation volume
- **Annual plans** save additional 30%

## Troubleshooting

### Common Issues:

**1. Proxy Authentication Errors**
```bash
# Verify credentials are correct
curl -x "http://username:password@proxy:port" http://httpbin.org/ip
```

**2. Rate Limiting Still Occurring**
- Check proxy usage in Webshare.io dashboard
- Consider upgrading to higher bandwidth plan
- Verify proxy rotation is working

**3. Validation Failures**
```bash
# Check proxy connectivity
python -c "
import requests
proxies = {'http': 'http://username:password@proxy:port'}
response = requests.get('http://httpbin.org/ip', proxies=proxies)
print(response.json())
"
```

## Security Considerations

### Best Practices:
- ✅ **Use environment variables** for proxy credentials
- ✅ **Rotate proxy passwords** regularly
- ✅ **Monitor proxy usage** for anomalies
- ✅ **Use dedicated proxy accounts** per validator
- ❌ **Never commit proxy credentials** to version control

### Environment Variable Setup:
```bash
# Add to ~/.bashrc or ~/.zshrc
export VALIDATOR_PROXY_URL="http://rotating-residential.webshare.io:9000"
export VALIDATOR_PROXY_USERNAME="your-username"
export VALIDATOR_PROXY_PASSWORD="your-password"

# Use in validator startup
python neurons/validator.py \
  --proxy_url "$VALIDATOR_PROXY_URL" \
  --proxy_username "$VALIDATOR_PROXY_USERNAME" \
  --proxy_password "$VALIDATOR_PROXY_PASSWORD"
```

## Support

### Getting Help:
1. **Webshare.io Support**: support@webshare.io
2. **Resi Labs Discord**: Technical support channel
3. **Documentation**: This guide and API docs

### Monitoring:
- **Webshare.io Dashboard**: Monitor usage and performance
- **Validator Logs**: Check for proxy-related errors
- **Validation Success Rate**: Monitor spot-check pass rates

---

**⚠️ IMPORTANT**: Mainnet validators **WILL NOT START** without proper proxy configuration. This is enforced to ensure network reliability and prevent validator downtime due to IP bans.
