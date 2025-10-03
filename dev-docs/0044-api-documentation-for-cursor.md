# 🚀 Resi Labs API Documentation for Validator Integration

## 📋 **API Base URLs**

### **Production Environment**
```
Base URL: https://api.resilabs.com
Health Check: https://api.resilabs.com/healthcheck
Swagger Docs: https://api.resilabs.com/docs
OpenAPI JSON: https://api.resilabs.com/docs-json
```

### **Development/Testing Environment**
```
Base URL: http://localhost:3000
Health Check: http://localhost:3000/healthcheck
Swagger Docs: http://localhost:3000/docs
OpenAPI JSON: http://localhost:3000/docs-json
```

---

## 🔐 **Authentication Method**

### **Bittensor Signature Authentication**
All API endpoints require Bittensor hotkey signatures using the following process:

#### **1. Signature Generation Process**
```python
# Using @polkadot/keyring (JavaScript/TypeScript)
import { Keyring } from '@polkadot/keyring';
import { stringToU8a } from '@polkadot/util';

const keyring = new Keyring({ type: 'sr25519' });
const pair = keyring.addFromUri('your_mnemonic_here');

function generateSignature(commitmentString) {
    const messageBytes = stringToU8a(commitmentString);
    const signature = pair.sign(messageBytes);
    return Buffer.from(signature).toString('hex');
}

# Using bittensor Python library
import bittensor as bt
from datetime import datetime

def generate_signature(hotkey, commitment_string):
    commitment_bytes = commitment_string.encode('utf-8')
    signature = hotkey.sign(commitment_bytes).hex()
    return signature
```

#### **2. Commitment String Formats**
Each endpoint requires a specific commitment format:

```javascript
// Zipcode Assignment Request
const commitment = `zipcode:assignment:current:${timestamp}`;

// Miner Status Update
const commitment = `miner:status:${hotkey}:${epochId}:${timestamp}`;

// Miner S3 Access
const commitment = `s3:data:access:${coldkey}:${hotkey}:${timestamp}`;

// Validator S3 Access
const commitment = `s3:validator:upload:${timestamp}`;
```

#### **3. Timestamp Validation**
- **Format**: Unix timestamp in seconds (not milliseconds)
- **Range**: Between 1600000000 and 2147483647
- **Tolerance**: ±5 minutes from current server time
- **Generation**: `Math.floor(Date.now() / 1000)` in JavaScript

---

## 🗺️ **Key API Endpoints**

### **1. Zipcode Assignment Endpoint**

#### **GET Current Zipcode Assignments**
```http
GET /api/v1/zipcode-assignments/current?hotkey={hotkey}&signature={signature}&timestamp={timestamp}
```

**Purpose**: Get current epoch's zipcode assignments for competitive mining

**Rate Limit**: 10 requests per minute per hotkey

**Authentication**: 
- **Commitment Format**: `zipcode:assignment:current:{timestamp}`
- **Signature**: Sign commitment with miner hotkey

**Query Parameters**:
```typescript
{
  hotkey: string;     // Miner's hotkey address
  signature: string;  // Hex-encoded signature
  timestamp: number;  // Unix timestamp in seconds
}
```

**Response Format**:
```json
{
  "success": true,
  "epochId": "2025-10-01T16-00-00",
  "epochStart": "2025-10-01T16:00:00.000Z",
  "epochEnd": "2025-10-01T20:00:00.000Z",
  "nonce": "376ce532f42cf2a5",
  "targetListings": 10000,
  "tolerancePercent": 10,
  "submissionDeadline": "2025-10-01T20:00:00.000Z",
  "zipcodes": [
    {
      "zipcode": "19103",
      "expectedListings": 250,
      "state": "PA",
      "city": "Philadelphia",
      "county": "Philadelphia County",
      "marketTier": "PREMIUM",
      "geographicRegion": "Northeast"
    }
  ],
  "metadata": {
    "totalExpectedListings": 9420,
    "zipcodeCount": 25,
    "algorithmVersion": "v1.0",
    "selectionSeed": 12345
  }
}
```

**Example Usage**:
```python
import requests
import time

def get_zipcode_assignments(hotkey, api_base_url):
    timestamp = int(time.time())
    commitment = f"zipcode:assignment:current:{timestamp}"
    signature = generate_signature(hotkey, commitment)
    
    url = f"{api_base_url}/api/v1/zipcode-assignments/current"
    params = {
        'hotkey': str(hotkey.ss58_address),
        'signature': signature,
        'timestamp': timestamp
    }
    
    response = requests.get(url, params=params)
    return response.json()
```

---

### **2. Miner Status Update Endpoint**

#### **POST Miner Status Update**
```http
POST /api/v1/zipcode-assignments/status
```

**Purpose**: Update mining progress and completion status

**Rate Limit**: 5 requests per minute per hotkey

**Authentication**:
- **Commitment Format**: `miner:status:{hotkey}:{epochId}:{timestamp}`
- **Signature**: Sign commitment with miner hotkey

**Request Body**:
```json
{
  "hotkey": "5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx",
  "signature": "a1b2c3d4e5f6...",
  "timestamp": 1696089600,
  "epochId": "2025-10-01T16-00-00",
  "nonce": "376ce532f42cf2a5",
  "status": "COMPLETED",
  "listingsScraped": 1250,
  "zipcodesCompleted": [
    {
      "zipcode": "19103",
      "listingsScraped": 245,
      "completedAt": "2025-10-01T17:30:00.000Z"
    }
  ],
  "s3UploadComplete": true,
  "s3UploadTimestamp": "2025-10-01T17:45:00.000Z"
}
```

**Response Format**:
```json
{
  "success": true,
  "message": "Miner status updated successfully",
  "epochId": "2025-10-01T16-00-00",
  "status": "COMPLETED",
  "timestamp": "2025-10-01T17:45:00.000Z"
}
```

**Status Values**:
- `IN_PROGRESS`: Mining is ongoing
- `COMPLETED`: All zipcodes completed and uploaded
- `FAILED`: Mining failed due to error
- `TIMEOUT`: Mining exceeded time limit

---

### **3. S3 Credentials Endpoint (Miners)**

#### **POST Miner S3 Access**
```http
POST /get-folder-access
```

**Purpose**: Get S3 upload credentials for miners to upload scraped data

**Rate Limit**: 10 requests per minute per hotkey

**Authentication**:
- **Commitment Format**: `s3:data:access:{coldkey}:{hotkey}:{timestamp}`
- **Signature**: Sign commitment with miner hotkey

**Request Body**:
```json
{
  "coldkey": "5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX",
  "hotkey": "5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx",
  "timestamp": 1696089600,
  "signature": "a1b2c3d4e5f6...",
  "expiry": 1696176000
}
```

**Response Format**:
```json
{
  "success": true,
  "message": "S3 upload credentials generated successfully",
  "uploadUrl": "https://1000-resilabs-caleb-dev-bittensor-sn46-datacollection.s3.us-east-2.amazonaws.com/",
  "fields": {
    "acl": "private",
    "bucket": "1000-resilabs-caleb-dev-bittensor-sn46-datacollection",
    "key": "data/hotkey=5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx/epoch=2025-10-01T16-00-00/timestamp=1696089600/",
    "Policy": "eyJleHBpcmF0aW9uIjoi...",
    "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
    "X-Amz-Credential": "AKIA.../20251001/us-east-2/s3/aws4_request",
    "X-Amz-Date": "20251001T120000Z",
    "X-Amz-Signature": "abc123..."
  },
  "metadata": {
    "folderPath": "data/hotkey=5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx/",
    "expiresAt": "2025-10-02T12:00:00.000Z",
    "maxFileSize": "100MB"
  }
}
```

---

### **4. Validator Result Upload Endpoint**

#### **POST Validator S3 Upload Access**
```http
POST /api/v1/s3-access/validator-upload
```

**Purpose**: Get S3 upload credentials for validators to store validation results

**Rate Limit**: 5 requests per hour per validator

**Authentication**:
- **Commitment Format**: `s3:validator:upload:{timestamp}`
- **Signature**: Sign commitment with validator hotkey

**Request Body**:
```json
{
  "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
  "signature": "a1b2c3d4e5f6...",
  "timestamp": 1696089600,
  "epochId": "2025-10-01T16-00-00",
  "purpose": "epoch_validation_results",
  "estimatedDataSizeMb": 25,
  "retentionDays": 90
}
```

**Response Format**:
```json
{
  "success": true,
  "message": "S3 upload credentials generated successfully",
  "uploadUrl": "https://resi-validated-data-dev.s3.us-east-2.amazonaws.com/",
  "fields": {
    "acl": "private",
    "bucket": "resi-validated-data-dev",
    "key": "validators/5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty/2025-10-01T16-00-00/validation_results/1696089600/",
    "Policy": "eyJleHBpcmF0aW9uIjoi...",
    "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
    "X-Amz-Credential": "AKIA.../20251001/us-east-2/s3/aws4_request",
    "X-Amz-Date": "20251001T120000Z",
    "X-Amz-Signature": "def456..."
  },
  "metadata": {
    "folderPath": "validators/5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty/",
    "expiresAt": "2025-10-01T20:00:00.000Z",
    "maxFileSize": "100MB",
    "supportedFormats": ["parquet", "csv", "json"]
  }
}
```

---

### **5. System Statistics Endpoint**

#### **GET System Statistics**
```http
GET /api/v1/zipcode-assignments/stats
```

**Purpose**: Get system-wide statistics and current epoch information

**Rate Limit**: 30 requests per minute (public endpoint)

**Authentication**: None required

**Response Format**:
```json
{
  "success": true,
  "currentTime": 1759336626,
  "systemStatus": "operational",
  "epochStatus": {
    "currentEpoch": {
      "id": "2025-10-01T16-00-00",
      "status": "ACTIVE",
      "startTime": "2025-10-01T16:00:00.000Z",
      "endTime": "2025-10-01T20:00:00.000Z",
      "nonce": "376ce532f42cf2a5",
      "zipcodeCount": 25,
      "targetListings": 10000,
      "actualExpected": 9420
    },
    "timing": {
      "timeUntilEpochEnd": 12173,
      "timeUntilNextEpoch": 12173,
      "epochDurationHours": 4
    },
    "nextEpoch": {
      "startTime": "2025-10-01T20:00:00.000Z"
    }
  },
  "zipcodeStatistics": {
    "totalZipcodes": 29,
    "activeZipcodes": 29,
    "inactiveZipcodes": 0,
    "stateDistribution": [
      {"state": "PA", "count": 17, "avgListings": 358},
      {"state": "NJ", "count": 12, "avgListings": 358}
    ],
    "tierDistribution": [
      {"tier": "STANDARD", "count": 9, "avgListings": 344},
      {"tier": "EMERGING", "count": 10, "avgListings": 497},
      {"tier": "PREMIUM", "count": 10, "avgListings": 231}
    ],
    "configuration": {
      "targetListings": 10000,
      "tolerancePercent": 10,
      "cooldownHours": 24,
      "minListings": 200,
      "maxListings": 3000
    }
  },
  "recentPerformance": [
    {
      "epochId": "2025-10-01T16-00-00",
      "status": "ACTIVE",
      "zipcodesAssigned": 25,
      "targetListings": 10000,
      "actualExpected": 9420
    }
  ]
}
```

---

### **6. Health Check Endpoint**

#### **GET Health Check**
```http
GET /healthcheck
```

**Purpose**: Check API server health and database connectivity

**Rate Limit**: No limit

**Authentication**: None required

**Response Format**:
```json
{
  "status": "ok",
  "timestamp": "2025-10-01T16:37:06.459Z",
  "uptime": 10.671315875,
  "database": "connected",
  "version": "1.0.0",
  "service": "resi-labs-api"
}
```

---

## 📚 **Existing Client Code Examples**

### **Python API Client**
```python
import requests
import time
import json
from typing import Dict, Any, Optional

class ResiLabsAPIClient:
    def __init__(self, base_url: str, hotkey, coldkey=None):
        self.base_url = base_url.rstrip('/')
        self.hotkey = hotkey
        self.coldkey = coldkey
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ResiLabs-Client/1.0'
        })
    
    def _generate_signature(self, commitment: str) -> str:
        """Generate Bittensor signature for commitment"""
        commitment_bytes = commitment.encode('utf-8')
        signature = self.hotkey.sign(commitment_bytes).hex()
        return signature
    
    def _get_timestamp(self) -> int:
        """Get current Unix timestamp in seconds"""
        return int(time.time())
    
    def get_current_zipcodes(self) -> Dict[str, Any]:
        """Get current epoch zipcode assignments"""
        timestamp = self._get_timestamp()
        commitment = f"zipcode:assignment:current:{timestamp}"
        signature = self._generate_signature(commitment)
        
        url = f"{self.base_url}/api/v1/zipcode-assignments/current"
        params = {
            'hotkey': str(self.hotkey.ss58_address),
            'signature': signature,
            'timestamp': timestamp
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def update_miner_status(self, epoch_id: str, nonce: str, status: str, 
                           listings_scraped: Optional[int] = None,
                           zipcodes_completed: Optional[list] = None,
                           s3_upload_complete: bool = False) -> Dict[str, Any]:
        """Update miner status"""
        timestamp = self._get_timestamp()
        commitment = f"miner:status:{self.hotkey.ss58_address}:{epoch_id}:{timestamp}"
        signature = self._generate_signature(commitment)
        
        data = {
            'hotkey': str(self.hotkey.ss58_address),
            'signature': signature,
            'timestamp': timestamp,
            'epochId': epoch_id,
            'nonce': nonce,
            'status': status,
            's3UploadComplete': s3_upload_complete
        }
        
        if listings_scraped is not None:
            data['listingsScraped'] = listings_scraped
        
        if zipcodes_completed:
            data['zipcodesCompleted'] = zipcodes_completed
        
        if s3_upload_complete:
            data['s3UploadTimestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        
        url = f"{self.base_url}/api/v1/zipcode-assignments/status"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_s3_credentials(self) -> Dict[str, Any]:
        """Get S3 upload credentials for miners"""
        if not self.coldkey:
            raise ValueError("Coldkey required for S3 access")
        
        timestamp = self._get_timestamp()
        commitment = f"s3:data:access:{self.coldkey.ss58_address}:{self.hotkey.ss58_address}:{timestamp}"
        signature = self._generate_signature(commitment)
        
        data = {
            'coldkey': str(self.coldkey.ss58_address),
            'hotkey': str(self.hotkey.ss58_address),
            'timestamp': timestamp,
            'signature': signature,
            'expiry': timestamp + 86400  # 24 hours
        }
        
        url = f"{self.base_url}/get-folder-access"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_validator_s3_credentials(self, epoch_id: str, purpose: str = "epoch_validation_results") -> Dict[str, Any]:
        """Get S3 upload credentials for validators"""
        timestamp = self._get_timestamp()
        commitment = f"s3:validator:upload:{timestamp}"
        signature = self._generate_signature(commitment)
        
        data = {
            'hotkey': str(self.hotkey.ss58_address),
            'signature': signature,
            'timestamp': timestamp,
            'epochId': epoch_id,
            'purpose': purpose,
            'estimatedDataSizeMb': 25,
            'retentionDays': 90
        }
        
        url = f"{self.base_url}/api/v1/s3-access/validator-upload"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        url = f"{self.base_url}/api/v1/zipcode-assignments/stats"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def check_health(self) -> Dict[str, Any]:
        """Check API server health"""
        url = f"{self.base_url}/healthcheck"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

# Usage Example
if __name__ == "__main__":
    import bittensor as bt
    
    # Initialize with your keys
    hotkey = bt.Keypair.create_from_mnemonic("your mnemonic here")
    coldkey = bt.Keypair.create_from_mnemonic("your coldkey mnemonic here")
    
    # Create API client
    api = ResiLabsAPIClient("http://localhost:3000", hotkey, coldkey)
    
    # Check health
    health = api.check_health()
    print(f"API Status: {health['status']}")
    
    # Get zipcode assignments
    assignments = api.get_current_zipcodes()
    print(f"Current epoch: {assignments['epochId']}")
    print(f"Zipcodes assigned: {len(assignments['zipcodes'])}")
    
    # Update status
    status_update = api.update_miner_status(
        epoch_id=assignments['epochId'],
        nonce=assignments['nonce'],
        status="IN_PROGRESS",
        listings_scraped=500
    )
    print(f"Status updated: {status_update['success']}")
```

### **JavaScript/TypeScript API Client**
```typescript
import axios, { AxiosInstance } from 'axios';

interface ZipcodeAssignment {
  zipcode: string;
  expectedListings: number;
  state: string;
  city: string;
  county: string | null;
  marketTier: string;
  geographicRegion: string;
}

interface EpochResponse {
  success: boolean;
  epochId: string;
  epochStart: string;
  epochEnd: string;
  nonce: string;
  targetListings: number;
  tolerancePercent: number;
  submissionDeadline: string;
  zipcodes: ZipcodeAssignment[];
  metadata: {
    totalExpectedListings: number;
    zipcodeCount: number;
    algorithmVersion: string;
    selectionSeed: number;
  };
}

class ResiLabsAPIClient {
  private client: AxiosInstance;
  private hotkey: string;
  private coldkey?: string;

  constructor(baseUrl: string, hotkey: string, coldkey?: string) {
    this.hotkey = hotkey;
    this.coldkey = coldkey;
    
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'ResiLabs-Client/1.0'
      },
      timeout: 30000
    });
  }

  private generateSignature(commitment: string): string {
    // Implement signature generation using your crypto library
    // This would use @polkadot/keyring or similar
    throw new Error('Implement signature generation');
  }

  private getTimestamp(): number {
    return Math.floor(Date.now() / 1000);
  }

  async getCurrentZipcodes(): Promise<EpochResponse> {
    const timestamp = this.getTimestamp();
    const commitment = `zipcode:assignment:current:${timestamp}`;
    const signature = this.generateSignature(commitment);

    const response = await this.client.get('/api/v1/zipcode-assignments/current', {
      params: {
        hotkey: this.hotkey,
        signature,
        timestamp
      }
    });

    return response.data;
  }

  async updateMinerStatus(
    epochId: string,
    nonce: string,
    status: string,
    options: {
      listingsScraped?: number;
      zipcodesCompleted?: Array<{
        zipcode: string;
        listingsScraped: number;
        completedAt: string;
      }>;
      s3UploadComplete?: boolean;
    } = {}
  ) {
    const timestamp = this.getTimestamp();
    const commitment = `miner:status:${this.hotkey}:${epochId}:${timestamp}`;
    const signature = this.generateSignature(commitment);

    const data = {
      hotkey: this.hotkey,
      signature,
      timestamp,
      epochId,
      nonce,
      status,
      ...options,
      ...(options.s3UploadComplete && {
        s3UploadTimestamp: new Date().toISOString()
      })
    };

    const response = await this.client.post('/api/v1/zipcode-assignments/status', data);
    return response.data;
  }

  async getS3Credentials() {
    if (!this.coldkey) {
      throw new Error('Coldkey required for S3 access');
    }

    const timestamp = this.getTimestamp();
    const commitment = `s3:data:access:${this.coldkey}:${this.hotkey}:${timestamp}`;
    const signature = this.generateSignature(commitment);

    const data = {
      coldkey: this.coldkey,
      hotkey: this.hotkey,
      timestamp,
      signature,
      expiry: timestamp + 86400 // 24 hours
    };

    const response = await this.client.post('/get-folder-access', data);
    return response.data;
  }

  async getValidatorS3Credentials(epochId: string, purpose = 'epoch_validation_results') {
    const timestamp = this.getTimestamp();
    const commitment = `s3:validator:upload:${timestamp}`;
    const signature = this.generateSignature(commitment);

    const data = {
      hotkey: this.hotkey,
      signature,
      timestamp,
      epochId,
      purpose,
      estimatedDataSizeMb: 25,
      retentionDays: 90
    };

    const response = await this.client.post('/api/v1/s3-access/validator-upload', data);
    return response.data;
  }

  async getSystemStats() {
    const response = await this.client.get('/api/v1/zipcode-assignments/stats');
    return response.data;
  }

  async checkHealth() {
    const response = await this.client.get('/healthcheck');
    return response.data;
  }
}

export default ResiLabsAPIClient;
```

---

## 🚨 **Error Handling**

### **Common HTTP Status Codes**
- **200**: Success
- **400**: Bad Request (invalid parameters, timestamp out of range)
- **401**: Unauthorized (invalid signature)
- **404**: Not Found (no current epoch available)
- **429**: Too Many Requests (rate limit exceeded)
- **500**: Internal Server Error

### **Error Response Format**
```json
{
  "statusCode": 400,
  "message": [
    "timestamp must not be greater than 2147483647",
    "hotkey must be a string"
  ],
  "error": "Bad Request"
}
```

### **Rate Limit Headers**
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1696089660
```

---

## 📊 **Data Formats**

### **Required Listing Data Schema**
When uploading to S3, miners should use this data format:

```python
REQUIRED_FIELDS = {
    'address': str,           # Full property address
    'zipcode': str,          # 5-digit zipcode
    'price': float,          # Listing price in USD
    'bedrooms': int,         # Number of bedrooms
    'bathrooms': float,      # Number of bathrooms
    'sqft': int,            # Square footage
    'listing_date': str,     # ISO 8601 date when listed
    'property_type': str,    # 'house', 'condo', 'townhouse', etc.
    'listing_status': str,   # 'active', 'pending', 'sold'
    'days_on_market': int,   # Days since first listed
    'mls_id': str,          # MLS listing ID (if available)
    'source_url': str,       # URL where data was scraped
    'scraped_timestamp': str # ISO 8601 timestamp when scraped
}
```

### **File Upload Structure**
```
S3 Bucket Structure:
├── data/
│   └── hotkey={miner_hotkey}/
│       └── epoch={epoch_id}/
│           ├── listings.parquet    # Main data file
│           └── metadata.json       # Metadata file
└── validators/
    └── {validator_hotkey}/
        └── {epoch_id}/
            └── validation_results.json
```

---

## 🔧 **Configuration & Environment**

### **Environment Variables**
```bash
# API Configuration
API_BASE_URL=https://api.resilabs.com
API_TIMEOUT=30000

# Bittensor Configuration
BT_NETWORK=finney
NET_UID=46

# Rate Limiting
RATE_LIMIT_ENABLED=true
```

### **Dependencies**
```python
# Python
bittensor>=6.0.0
requests>=2.28.0
pandas>=1.5.0
pyarrow>=10.0.0  # For Parquet support
```

```json
// Node.js package.json
{
  "dependencies": {
    "axios": "^1.0.0",
    "@polkadot/keyring": "^13.0.0",
    "@polkadot/util": "^13.0.0",
    "@polkadot/util-crypto": "^13.0.0"
  }
}
```

---

*Last Updated: October 1, 2025*  
*API Version: 1.0.0*  
*Status: Production Ready* 🚀