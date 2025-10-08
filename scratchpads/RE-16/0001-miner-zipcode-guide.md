# Miner API Access Guide - Resi Labs Subnet 46

## Overview

This guide explains how miners can access the Resi Labs API to get their zipcode assignments for data collection. The API provides deterministic zipcode assignments that all miners receive for each 4-hour epoch.

## Quick Start

### 1. Get Your Zipcode Assignments

```bash
# Generate current timestamp
TIMESTAMP=$(date +%s)

# Sign the commitment message with your miner hotkey
btcli wallet sign \
  --wallet-name YOUR_MINER_WALLET \
  --hotkey YOUR_MINER_HOTKEY \
  --use-hotkey \
  --message "zipcode:assignment:current:$TIMESTAMP"

# Use the signature to get assignments
curl "https://api-staging.resilabs.ai/api/v1/zipcode-assignments/current?hotkey=YOUR_HOTKEY_ADDRESS&signature=0xYOUR_SIGNATURE&timestamp=$TIMESTAMP"
```

### 2. Expected Response

You'll receive 10-20 zipcodes with ~10,000 total expected listings:

```json
{
  "success": true,
  "epochId": "2025-10-07T12-00-00",
  "epochStart": "2025-10-07T12:00:00.000Z",
  "epochEnd": "2025-10-07T16:00:00.000Z",
  "targetListings": 10000,
  "zipcodes": [
    {
      "zipcode": "01607",
      "expectedListings": 248,
      "state": "MA",
      "city": "Worcester",
      "county": "Worcester County",
      "marketTier": "EMERGING",
      "geographicRegion": "Northeast"
    }
    // ... more zipcodes
  ]
}
```

## API Environments

### Staging (Testing)
- **URL**: `https://api-staging.resilabs.ai`
- **Purpose**: Development and testing
- **Network**: Testnet
- **Subnet**: 46

### Production (Live Mining)
- **URL**: `https://api.resilabs.ai`
- **Purpose**: Live mining operations
- **Network**: Finney (Mainnet)
- **Subnet**: 46

## Authentication Process

### Understanding the Signature

The API uses Bittensor's signature verification to ensure only registered miners can access assignments. You must sign a specific commitment message format.

### Commitment Message Format

```
zipcode:assignment:current:<unix_timestamp>
```

**Important**: The message format is exact - do not include your hotkey address in the message.

### Step-by-Step Authentication

#### Step 1: Prepare Your Credentials

Ensure you have:
- A registered miner on subnet 46
- Access to your miner wallet via `btcli`
- Your miner hotkey address

#### Step 2: Generate Signature

```bash
# Get current timestamp (must be within 5 minutes)
TIMESTAMP=$(date +%s)
echo "Timestamp: $TIMESTAMP"

# Create the commitment message
MESSAGE="zipcode:assignment:current:$TIMESTAMP"
echo "Message to sign: $MESSAGE"

# Sign with btcli
btcli wallet sign \
  --wallet-name YOUR_WALLET_NAME \
  --hotkey YOUR_HOTKEY_NAME \
  --use-hotkey \
  --message "$MESSAGE"
```

#### Step 3: Extract Signature

From btcli output, copy the signature (without "0x" prefix):
```
Message signed successfully!

Signature:
56ed20f4a19cd9bf827da0e45370ffdc16b7167729c498b5830254196a6eb360a92167a0b187723fc58f1337bd555c165313f461e930fce51bf1a0524681db8b
Signer address: 5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni
```

#### Step 4: Make API Request

```bash
HOTKEY="5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni"
SIGNATURE="56ed20f4a19cd9bf827da0e45370ffdc16b7167729c498b5830254196a6eb360a92167a0b187723fc58f1337bd555c165313f461e930fce51bf1a0524681db8b"
TIMESTAMP="1759843903"

curl -s "https://api-staging.resilabs.ai/api/v1/zipcode-assignments/current?hotkey=${HOTKEY}&signature=0x${SIGNATURE}&timestamp=${TIMESTAMP}" | jq .
```

## Mining Workflow

### 1. Epoch Schedule

Epochs run every 4 hours starting at:
- **00:00 UTC** (8:00 PM EST / 5:00 PM PST)
- **04:00 UTC** (12:00 AM EST / 9:00 PM PST)
- **08:00 UTC** (4:00 AM EST / 1:00 AM PST)
- **12:00 UTC** (8:00 AM EST / 5:00 AM PST)
- **16:00 UTC** (12:00 PM EST / 9:00 AM PST)
- **20:00 UTC** (4:00 PM EST / 1:00 PM PST)

### 2. Mining Process

```bash
#!/bin/bash
# Example mining script

# 1. Get current epoch assignments
get_assignments() {
    TIMESTAMP=$(date +%s)
    
    # Sign commitment
    SIGNATURE=$(btcli wallet sign \
        --wallet-name miner_wallet \
        --hotkey miner_hotkey \
        --use-hotkey \
        --message "zipcode:assignment:current:$TIMESTAMP" \
        --quiet | grep "Signature:" | cut -d' ' -f2)
    
    # Get assignments
    curl -s "https://api.resilabs.ai/api/v1/zipcode-assignments/current?hotkey=$MINER_HOTKEY&signature=0x$SIGNATURE&timestamp=$TIMESTAMP"
}

# 2. Process each zipcode
mine_zipcode() {
    local zipcode=$1
    local expected_listings=$2
    
    echo "Mining zipcode: $zipcode (target: $expected_listings listings)"
    
    # Your scraping logic here
    # - Scrape real estate listings for this zipcode
    # - Collect property data, prices, features, etc.
    # - Save to your preferred format
}

# 3. Main mining loop
main() {
    echo "Starting mining for current epoch..."
    
    # Get assignments
    ASSIGNMENTS=$(get_assignments)
    
    # Parse and mine each zipcode
    echo "$ASSIGNMENTS" | jq -r '.zipcodes[]? | "\(.zipcode) \(.expectedListings)"' | while read zipcode expected; do
        mine_zipcode "$zipcode" "$expected"
    done
    
    echo "Mining complete for current epoch"
}

main
```

### 3. Data Collection Guidelines

#### What to Collect
- **Property listings**: Active real estate listings
- **Property details**: Price, bedrooms, bathrooms, square footage
- **Location data**: Address, neighborhood, school districts
- **Market data**: Days on market, price history, comparable sales
- **Property features**: Amenities, lot size, year built

#### Data Quality Standards
- **Accuracy**: Collect current, accurate data
- **Completeness**: Aim for the target listing count per zipcode
- **Consistency**: Use standardized data formats
- **Timeliness**: Complete collection within the 4-hour epoch

## API Endpoints for Miners

### Current Assignments (Primary)

**Endpoint**: `GET /api/v1/zipcode-assignments/current`

**Purpose**: Get your zipcode assignments for the current epoch

**Authentication**: Required (miner signature)

**Response**: List of zipcodes to mine with expected listing counts

### System Statistics (Optional)

**Endpoint**: `GET /api/v1/zipcode-assignments/stats`

**Purpose**: Check system status and epoch information

**Authentication**: None required

**Usage**: Monitor epoch transitions and system health

```bash
# Check current epoch status
curl -s "https://api.resilabs.ai/api/v1/zipcode-assignments/stats" | jq '.epochStatus'
```

### Health Check (Optional)

**Endpoint**: `GET /health`

**Purpose**: Verify API availability

**Authentication**: None required

```bash
# Quick health check
curl -s "https://api.resilabs.ai/health"
```

## Error Handling

### Common Errors and Solutions

#### 1. Invalid Signature (401)
```json
{"statusCode": 401, "message": "Invalid signature"}
```

**Causes**:
- Wrong commitment message format
- Expired timestamp (>5 minutes old)
- Miner not registered on subnet 46

**Solutions**:
```bash
# Verify message format
echo "zipcode:assignment:current:$(date +%s)"

# Check miner registration
btcli subnet list --netuid 46 --subtensor.network finney | grep YOUR_HOTKEY

# Generate fresh signature
TIMESTAMP=$(date +%s)
btcli wallet sign --wallet-name YOUR_WALLET --hotkey YOUR_HOTKEY --use-hotkey --message "zipcode:assignment:current:$TIMESTAMP"
```

#### 2. Invalid Timestamp (400)
```json
{"statusCode": 400, "message": "Invalid timestamp"}
```

**Cause**: Timestamp too old or malformed

**Solution**:
```bash
# Use current timestamp
TIMESTAMP=$(date +%s)
echo "Current timestamp: $TIMESTAMP"
```

#### 3. Rate Limit Exceeded (429)
```json
{"statusCode": 429, "message": "Too Many Requests"}
```

**Cause**: Too many requests (limit: 10 per minute)

**Solution**: Cache assignments and avoid repeated calls

#### 4. No Current Epoch (404)
```json
{"statusCode": 404, "message": "No current epoch available"}
```

**Cause**: System maintenance or epoch transition

**Solution**: Wait and retry, check system status

### Retry Logic

```bash
# Robust API call with retry
call_api_with_retry() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt of $max_attempts..."
        
        TIMESTAMP=$(date +%s)
        SIGNATURE=$(btcli wallet sign --wallet-name miner_wallet --hotkey miner_hotkey --use-hotkey --message "zipcode:assignment:current:$TIMESTAMP" --quiet | grep "Signature:" | cut -d' ' -f2)
        
        RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" "https://api.resilabs.ai/api/v1/zipcode-assignments/current?hotkey=$MINER_HOTKEY&signature=0x$SIGNATURE&timestamp=$TIMESTAMP")
        
        HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
        
        if [ "$HTTP_STATUS" = "200" ]; then
            echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//'
            return 0
        elif [ "$HTTP_STATUS" = "429" ]; then
            echo "Rate limited, waiting 60 seconds..."
            sleep 60
        else
            echo "Error $HTTP_STATUS, retrying in 30 seconds..."
            sleep 30
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo "Failed after $max_attempts attempts"
    return 1
}
```

## Best Practices

### 1. Caching Strategy

```bash
# Cache assignments for the full epoch
CACHE_FILE="/tmp/current_assignments.json"
CACHE_DURATION=14400  # 4 hours in seconds

get_cached_assignments() {
    if [ -f "$CACHE_FILE" ]; then
        local cache_age=$(($(date +%s) - $(stat -c %Y "$CACHE_FILE" 2>/dev/null || stat -f %m "$CACHE_FILE")))
        if [ $cache_age -lt $CACHE_DURATION ]; then
            cat "$CACHE_FILE"
            return 0
        fi
    fi
    
    # Cache expired or doesn't exist, fetch new
    local assignments=$(call_api_with_retry)
    if [ $? -eq 0 ]; then
        echo "$assignments" > "$CACHE_FILE"
        echo "$assignments"
    fi
}
```

### 2. Monitoring Epoch Transitions

```bash
# Monitor for new epochs
monitor_epochs() {
    local current_epoch=""
    
    while true; do
        local stats=$(curl -s "https://api.resilabs.ai/api/v1/zipcode-assignments/stats")
        local new_epoch=$(echo "$stats" | jq -r '.epochStatus.currentEpoch.id')
        
        if [ "$new_epoch" != "$current_epoch" ]; then
            echo "New epoch detected: $new_epoch"
            current_epoch="$new_epoch"
            
            # Clear cache and get new assignments
            rm -f "$CACHE_FILE"
            get_cached_assignments > /dev/null
            
            # Start mining new epoch
            start_mining
        fi
        
        # Check every 5 minutes
        sleep 300
    done
}
```

### 3. Resource Management

- **Rate Limiting**: Max 10 API calls per minute
- **Caching**: Store assignments for full epoch duration
- **Parallel Processing**: Mine multiple zipcodes concurrently
- **Error Recovery**: Implement robust retry mechanisms

### 4. Data Submission

After collecting data, you'll need to submit results according to subnet 46 protocols:

```bash
# Example data submission (implement according to subnet specs)
submit_mining_results() {
    local epoch_id=$1
    local data_file=$2
    
    # Upload to designated S3 bucket or submission endpoint
    # Follow subnet 46 submission requirements
    echo "Submitting results for epoch: $epoch_id"
}
```

## Testing Your Setup

### 1. Test Authentication

```bash
# Test with staging API first
TIMESTAMP=$(date +%s)
btcli wallet sign --wallet-name YOUR_WALLET --hotkey YOUR_HOTKEY --use-hotkey --message "zipcode:assignment:current:$TIMESTAMP"

# Verify you get a valid signature and can call the API
```

### 2. Validate Assignments

```bash
# Check you receive expected data structure
curl -s "https://api-staging.resilabs.ai/api/v1/zipcode-assignments/current?..." | jq '.zipcodes | length'

# Should return a number (typically 10-20)
```

### 3. Test Error Handling

```bash
# Test with expired timestamp
OLD_TIMESTAMP=$(($(date +%s) - 600))  # 10 minutes ago
# Should return 400 error

# Test with invalid signature
# Should return 401 error
```

## Support and Troubleshooting

### Debugging Checklist

1. **Verify miner registration**: Check subnet 46 registration status
2. **Test signature generation**: Ensure btcli is working correctly
3. **Check timestamp validity**: Must be within 5 minutes
4. **Validate message format**: Exact format required
5. **Test network connectivity**: Ensure API is accessible
6. **Monitor rate limits**: Don't exceed 10 calls per minute

### Getting Help

- **API Documentation**: https://api.resilabs.ai/docs
- **Subnet 46 Discord**: [Join for community support]
- **GitHub Issues**: [Repository for bug reports]
- **System Status**: Monitor via `/health` and `/stats` endpoints

### Useful Commands

```bash
# Check your miner registration
btcli subnet list --netuid 46 --subtensor.network finney | grep $(btcli wallet overview --wallet.name YOUR_WALLET | grep "Hotkey:" | awk '{print $2}')

# Monitor current epoch
watch -n 60 'curl -s "https://api.resilabs.ai/api/v1/zipcode-assignments/stats" | jq ".epochStatus.currentEpoch"'

# Test API connectivity
curl -w "Total time: %{time_total}s\n" -s "https://api.resilabs.ai/health" > /dev/null
```

## Security Notes

- **Never share your private keys** or wallet passwords
- **Keep signatures temporary** - they expire in 5 minutes
- **Use secure connections** - Always HTTPS
- **Validate responses** - Check API response structure
- **Monitor for anomalies** - Watch for unexpected behavior

## Example Integration

Here's a complete example of integrating the API into your mining operation:

```python
#!/usr/bin/env python3
"""
Example miner integration with Resi Labs API
"""

import requests
import subprocess
import json
import time
from datetime import datetime

class ResiMiner:
    def __init__(self, wallet_name, hotkey_name, hotkey_address):
        self.wallet_name = wallet_name
        self.hotkey_name = hotkey_name  
        self.hotkey_address = hotkey_address
        self.api_base = "https://api.resilabs.ai"
        
    def generate_signature(self, timestamp):
        """Generate signature using btcli"""
        message = f"zipcode:assignment:current:{timestamp}"
        
        cmd = [
            "btcli", "wallet", "sign",
            "--wallet-name", self.wallet_name,
            "--hotkey", self.hotkey_name,
            "--use-hotkey",
            "--message", message,
            "--quiet"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Extract signature from output
        for line in result.stdout.split('\n'):
            if line.startswith('Signature:'):
                return line.split(':', 1)[1].strip()
        
        raise Exception("Failed to generate signature")
    
    def get_assignments(self):
        """Get current epoch assignments"""
        timestamp = int(time.time())
        signature = self.generate_signature(timestamp)
        
        url = f"{self.api_base}/api/v1/zipcode-assignments/current"
        params = {
            "hotkey": self.hotkey_address,
            "signature": f"0x{signature}",
            "timestamp": timestamp
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def mine_zipcode(self, zipcode_data):
        """Mine a specific zipcode"""
        zipcode = zipcode_data['zipcode']
        expected = zipcode_data['expectedListings']
        
        print(f"Mining {zipcode}: target {expected} listings")
        
        # Your scraping logic here
        # Return collected data
        
        return {
            'zipcode': zipcode,
            'listings_found': expected,  # Replace with actual count
            'data': []  # Replace with actual data
        }
    
    def run_mining_cycle(self):
        """Run one complete mining cycle"""
        try:
            # Get assignments
            assignments = self.get_assignments()
            epoch_id = assignments['epochId']
            zipcodes = assignments['zipcodes']
            
            print(f"Starting mining for epoch {epoch_id}")
            print(f"Assigned {len(zipcodes)} zipcodes")
            
            results = []
            for zipcode_data in zipcodes:
                result = self.mine_zipcode(zipcode_data)
                results.append(result)
            
            print(f"Mining complete: collected data for {len(results)} zipcodes")
            return results
            
        except Exception as e:
            print(f"Mining failed: {e}")
            return None

# Usage
if __name__ == "__main__":
    miner = ResiMiner(
        wallet_name="my_miner_wallet",
        hotkey_name="my_miner_hotkey", 
        hotkey_address="5F..."  # Your actual hotkey address
    )
    
    results = miner.run_mining_cycle()
    if results:
        print("Mining successful!")
    else:
        print("Mining failed!")
```

This guide provides everything miners need to successfully integrate with the Resi Labs API and start collecting real estate data for subnet 46!
