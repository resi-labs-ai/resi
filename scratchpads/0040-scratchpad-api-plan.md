# API Server Requirements - Zipcode Assignment System

## Project Overview

We're implementing a competitive zipcode-based mining system for our real estate data subnet. The API server needs to coordinate zipcode assignments across miners every 4 hours, enabling competitive scraping with quality validation.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Server    │    │   Validators     │    │     Miners      │
│                 │    │                  │    │                 │
│ Every 4 hours:  │    │ Every 4 hours:   │    │ Continuous:     │
│ - Select zips   │◄───┤ - Fetch zip list │    │ - Receive zips  │
│ - Generate nonce│    │ - Broadcast to   │───►│ - Scrape data   │
│ - Store epoch   │    │   miners (opt)   │    │ - Upload to S3  │
│                 │    │ - Validate prev  │    │   with nonce    │
│                 │    │   epoch results  │    │                 │
│                 │    │ - Set weights    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Requirements

### **Epoch Management System**
- **4-hour epochs** starting at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
- **Epoch ID format**: `YYYY-MM-DD-HH:MM` (e.g., "2024-03-15-16:00")
- **Automatic epoch transitions** with new zipcode assignments
- **Historical epoch storage** for validator access (minimum 7 days retention)

### **Zipcode Selection Algorithm**
```python
# Configuration Variables (Environment/Config)
TARGET_LISTINGS = 10000  # Configurable: 5K-15K range
TOLERANCE_PERCENT = 10   # ±10% tolerance
MIN_ZIPCODE_LISTINGS = 200    # Avoid tiny markets
MAX_ZIPCODE_LISTINGS = 3000   # Avoid oversized markets
COOLDOWN_HOURS = 24          # Avoid recently assigned zipcodes

def select_zipcodes_for_epoch():
    target = TARGET_LISTINGS
    tolerance = target * (TOLERANCE_PERCENT / 100)
    
    # Filter eligible zipcodes:
    # 1. Not assigned in last COOLDOWN_HOURS
    # 2. Expected listings between MIN and MAX
    # 3. Has recent data (updated within 30 days)
    
    # Random weighted selection to hit target ± tolerance
    # Weight by: expected_listings * market_importance_factor
    # market_importance_factor = log(population + property_count)
```

### **Anti-Gaming Nonce System**
```python
# Epoch-specific nonce generation
nonce = hmac_sha256(
    key=SECRET_KEY,
    message=f"{epoch_id}:{epoch_start_timestamp}:{selected_zipcodes_hash}"
)
```
- **Purpose**: Prevents miners from pre-scraping popular zipcodes
- **Validation**: Miners must include nonce in S3 upload metadata
- **Rotation**: New nonce every epoch (4 hours)

## API Endpoints Specification

### **Endpoint 1: Get Current Zipcode Assignment**

```http
GET /api/v1/zipcode-assignments/current
```

**Headers:**
```
Authorization: Bearer {signature}
X-Timestamp: {unix_timestamp}
X-Hotkey: {bittensor_hotkey}
```

**Authentication Process:**
```python
# Signature creation (client-side)
message = f"zipcode:assignment:current:{timestamp}"
signature = hotkey.sign(message.encode()).hex()

# Server verification
verify_bittensor_signature(hotkey, message, signature)
verify_hotkey_registered_on_network(hotkey, netuid=46)
```

**Response Format:**
```json
{
  "success": true,
  "epoch_id": "2024-03-15-16:00",
  "epoch_start": "2024-03-15T16:00:00Z",
  "epoch_end": "2024-03-15T20:00:00Z",
  "nonce": "a1b2c3d4e5f6789",
  "target_listings": 10000,
  "tolerance_percent": 10,
  "submission_deadline": "2024-03-15T20:00:00Z",
  "zipcodes": [
    {
      "zipcode": "11211",
      "expected_listings": 1200,
      "state": "NY",
      "city": "Brooklyn",
      "county": "Kings County",
      "market_tier": "premium",
      "last_assigned": "2024-03-10T12:00:00Z"
    },
    {
      "zipcode": "19123",
      "expected_listings": 850,
      "state": "PA", 
      "city": "Philadelphia",
      "county": "Philadelphia County",
      "market_tier": "standard",
      "last_assigned": null
    }
  ],
  "metadata": {
    "total_expected_listings": 9850,
    "zipcode_count": 8,
    "geographic_regions": ["Northeast", "Mid-Atlantic"],
    "selection_algorithm_version": "v1.2"
  }
}
```

**Error Responses:**
```json
// Invalid authentication
{
  "success": false,
  "error": "authentication_failed",
  "message": "Invalid hotkey signature",
  "code": 401
}

// Rate limited
{
  "success": false,
  "error": "rate_limited", 
  "message": "Max 1 request per minute per hotkey",
  "retry_after": 45,
  "code": 429
}

// Hotkey not registered
{
  "success": false,
  "error": "hotkey_not_registered",
  "message": "Hotkey not found on bittensor network netuid 46",
  "code": 403
}
```

### **Endpoint 2: Get Historical Epoch**

```http
GET /api/v1/zipcode-assignments/epoch/{epoch_id}
```

**Purpose**: Validators need historical data to validate previous epoch submissions

**Headers:** Same as Endpoint 1, but with validator-specific message:
```python
message = f"zipcode:validation:{epoch_id}:{timestamp}"
```

**Response**: Same format as current endpoint, but for specified epoch

**Additional Validation:**
- Only validators (stake > threshold) can access historical data
- Rate limit: 10 requests per hour per validator
- Data retention: 7 days minimum, 30 days maximum

### **Endpoint 3: Zipcode Statistics** (New)

```http
GET /api/v1/zipcode-assignments/stats
```

**Purpose**: Provide system health metrics and selection statistics

**Response:**
```json
{
  "success": true,
  "current_epoch": "2024-03-15-16:00",
  "system_status": "operational",
  "statistics": {
    "total_zipcodes_available": 15420,
    "avg_listings_per_zipcode": 892,
    "epochs_generated": 1247,
    "last_selection_duration_ms": 234,
    "geographic_distribution": {
      "Northeast": 32,
      "Southeast": 28, 
      "Midwest": 21,
      "West": 19
    }
  },
  "recent_epochs": [
    {
      "epoch_id": "2024-03-15-12:00",
      "zipcodes_assigned": 9,
      "target_listings": 10000,
      "actual_expected": 9750,
      "miners_participated": 23,
      "completion_rate": 0.87
    }
  ]
}
```

### **Endpoint 4: Submit Completion Status** (Optional)

```http
POST /api/v1/zipcode-assignments/status
```

**Purpose**: Track miner progress and system performance (optional)

**Request Body:**
```json
{
  "epoch_id": "2024-03-15-16:00",
  "nonce": "a1b2c3d4e5f6789",
  "status": "completed",
  "listings_scraped": 9850,
  "zipcodes_completed": [
    {
      "zipcode": "11211", 
      "listings_found": 1150,
      "scrape_duration_minutes": 45,
      "data_quality_score": 0.95
    }
  ],
  "s3_upload_complete": true,
  "s3_upload_timestamp": "2024-03-15T19:45:23Z"
}
```

## Database Schema Requirements

### **Epochs Table**
```sql
CREATE TABLE epochs (
    id VARCHAR(20) PRIMARY KEY,  -- "2024-03-15-16:00"
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    nonce VARCHAR(64) NOT NULL,
    target_listings INTEGER NOT NULL,
    tolerance_percent INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    status ENUM('pending', 'active', 'completed', 'archived')
);
```

### **Epoch Assignments Table**
```sql
CREATE TABLE epoch_assignments (
    epoch_id VARCHAR(20) REFERENCES epochs(id),
    zipcode VARCHAR(10) NOT NULL,
    expected_listings INTEGER NOT NULL,
    state VARCHAR(2) NOT NULL,
    city VARCHAR(100) NOT NULL,
    county VARCHAR(100),
    market_tier ENUM('premium', 'standard', 'emerging'),
    selection_weight DECIMAL(10,4),
    PRIMARY KEY (epoch_id, zipcode)
);
```

### **Zipcode Master Data**
```sql
CREATE TABLE zipcodes (
    zipcode VARCHAR(10) PRIMARY KEY,
    state VARCHAR(2) NOT NULL,
    city VARCHAR(100) NOT NULL,
    county VARCHAR(100),
    population INTEGER,
    median_home_value INTEGER,
    expected_listings INTEGER,
    market_tier ENUM('premium', 'standard', 'emerging'),
    last_assigned TIMESTAMP,
    data_updated_at TIMESTAMP,
    INDEX idx_last_assigned (last_assigned),
    INDEX idx_market_tier (market_tier),
    INDEX idx_expected_listings (expected_listings)
);
```

### **Miner Status Tracking** (Optional)
```sql
CREATE TABLE miner_submissions (
    epoch_id VARCHAR(20),
    miner_hotkey VARCHAR(100),
    submission_timestamp TIMESTAMP,
    listings_scraped INTEGER,
    zipcodes_completed INTEGER,
    s3_upload_complete BOOLEAN,
    status ENUM('in_progress', 'completed', 'failed'),
    PRIMARY KEY (epoch_id, miner_hotkey)
);
```

## Configuration Requirements

### **Environment Variables**
```bash
# Core Configuration
TARGET_LISTINGS=10000           # Configurable: 5K-15K
TOLERANCE_PERCENT=10           # ±10% tolerance
EPOCH_DURATION_HOURS=4         # Fixed: 4 hours
COOLDOWN_HOURS=24             # Avoid recently assigned zipcodes

# Selection Algorithm
MIN_ZIPCODE_LISTINGS=200      # Avoid tiny markets  
MAX_ZIPCODE_LISTINGS=3000     # Avoid oversized markets
MARKET_TIER_WEIGHTS=premium:1.5,standard:1.0,emerging:0.8

# Security
SECRET_KEY=your_secret_key_here    # For nonce generation
BITTENSOR_NETWORK_URL=wss://...    # For hotkey verification
NETUID=46                          # Subnet ID

# Rate Limiting
MINER_RATE_LIMIT=1/minute         # Current assignments
VALIDATOR_RATE_LIMIT=10/hour      # Historical data
MAX_CONCURRENT_REQUESTS=100       # Server capacity

# Database
DATABASE_URL=postgresql://...     # Connection string
REDIS_URL=redis://...            # For caching/rate limiting

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=60         # Seconds
```

## Rate Limiting & Security

### **Authentication Flow**
1. **Client creates signature**: `hotkey.sign(f"zipcode:assignment:{type}:{timestamp}")`
2. **Server verifies signature**: Cryptographic verification using bittensor libraries
3. **Server checks registration**: Query bittensor network for hotkey registration
4. **Server enforces rate limits**: Redis-based sliding window rate limiting

### **Rate Limits**
- **Miners**: 1 request per minute for current assignments
- **Validators**: 10 requests per hour for historical data  
- **Stats endpoint**: 5 requests per minute (public)
- **Global**: 1000 requests per minute per IP (DDoS protection)

### **Security Measures**
- **HTTPS only** - No HTTP allowed
- **Request signing** - All requests must be cryptographically signed
- **Timestamp validation** - Requests must be within 5 minutes of server time
- **Hotkey verification** - Must be registered on bittensor network
- **Input sanitization** - All inputs validated and sanitized
- **SQL injection prevention** - Parameterized queries only

## Performance Requirements

### **Response Times**
- **Current assignments**: < 200ms (95th percentile)
- **Historical data**: < 500ms (95th percentile)  
- **Stats endpoint**: < 100ms (95th percentile)

### **Availability**
- **Uptime**: 99.9% (< 8.77 hours downtime per year)
- **Epoch transitions**: Must be seamless, no missed epochs
- **Failover**: Automatic failover within 30 seconds

### **Scalability**
- **Concurrent miners**: Support 100+ miners per epoch
- **Concurrent validators**: Support 50+ validators
- **Database growth**: Handle 1M+ epoch assignments over time
- **Geographic distribution**: Ready for CDN deployment

## Testing Requirements

### **Unit Tests**
- Zipcode selection algorithm accuracy
- Nonce generation and validation
- Authentication and authorization
- Rate limiting enforcement

### **Integration Tests**
- End-to-end epoch creation and assignment
- Database consistency across epoch transitions
- Bittensor network integration
- Error handling and recovery

### **Load Tests**
- 100 concurrent miners requesting assignments
- Database performance under high load
- Rate limiting effectiveness
- Memory usage and leak detection

## Deployment Requirements

### **Infrastructure**
- **Platform**: Digital Ocean (preferred)
- **Instance**: 4 CPU, 8GB RAM minimum
- **Database**: PostgreSQL 14+ with connection pooling
- **Cache**: Redis for rate limiting and session management
- **Load Balancer**: For high availability
- **Monitoring**: Prometheus + Grafana for metrics

### **Environment Setup**
```bash
# Production deployment
docker-compose up -d
# OR
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Database migrations
alembic upgrade head

# Health check
curl https://api.resilabs.ai/api/v1/health
```

### **Monitoring & Alerts**
- **Health checks**: Every 30 seconds
- **Error rate alerts**: > 5% error rate
- **Response time alerts**: > 500ms average
- **Database alerts**: Connection pool exhaustion
- **Epoch transition alerts**: Failed or delayed epochs

## Success Criteria

### **Functional Requirements**
✅ Generate new zipcode assignments every 4 hours  
✅ Target 10K ±10% listings per epoch (configurable)  
✅ Prevent pre-scraping with epoch-specific nonces  
✅ Authenticate all requests with bittensor signatures  
✅ Store 7+ days of historical epoch data  
✅ Handle 100+ concurrent miners and validators  

### **Performance Requirements**  
✅ < 200ms response time for current assignments  
✅ 99.9% uptime with automatic failover  
✅ Zero missed epoch transitions  
✅ Rate limiting prevents abuse  

### **Security Requirements**
✅ All requests cryptographically signed and verified  
✅ Only registered bittensor hotkeys can access  
✅ Protection against common attacks (DDoS, injection, etc.)  
✅ Secure nonce generation prevents gaming  

## Implementation Timeline

**Week 1: Core Development**
- Database schema and migrations
- Basic API endpoints (current + historical)
- Zipcode selection algorithm
- Authentication system

**Week 2: Advanced Features**  
- Nonce generation and validation
- Rate limiting implementation
- Error handling and logging
- Stats endpoint

**Week 3: Testing & Polish**
- Unit and integration tests
- Load testing and optimization
- Security audit and hardening
- Documentation and deployment guides

**Week 4: Deployment & Monitoring**
- Production deployment on Digital Ocean
- Monitoring and alerting setup
- Integration testing with miners/validators
- Performance tuning and optimization

## Questions for Development Team

1. **Database preference**: PostgreSQL vs MySQL vs other?
2. **Framework preference**: FastAPI vs Flask vs other?
3. **Caching strategy**: Redis vs in-memory vs other?
4. **Deployment method**: Docker vs direct vs other?
5. **Monitoring tools**: Prometheus vs DataDog vs other?

## Support & Documentation

- **API Documentation**: OpenAPI/Swagger specification
- **Integration Guide**: Step-by-step miner/validator integration
- **Troubleshooting**: Common issues and solutions
- **Contact**: Technical support channel for issues
