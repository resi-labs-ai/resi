# Data API Server Specification

This document defines the API endpoints required for coordinated zipcode distribution and consensus validation.

## Overview

The Data API Server provides coordinated zipcode blocks to validators every 4 hours, enabling consensus validation without requiring validators to scrape data themselves. The API includes authentication, zipcode block generation, and assignment tracking.

## Base Configuration

```python
# Environment Variables
DATA_API_URL = "https://api.resi-subnet.com"  # Production
DATA_API_URL = "http://localhost:8000"        # Development/Mock

# Mock Server for Development
python mock_data_api_server.py --host 0.0.0.0 --port 8000
```

## Authentication Flow

### 1. Validator Authentication

**Endpoint**: `POST /get-validator-access`

**Purpose**: Authenticate validator using blockchain signature and get access token

**Request Body**:
```json
{
    "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    "timestamp": 1705312800,
    "signature": "0x1234567890abcdef...",
    "sources": "ZILLOW_SOLD"
}
```

**Signature Generation** (reuses existing S3 pattern):
```python
# Same pattern as S3 authentication
commitment = f"api:data:request:{hotkey}:{timestamp}:{sources}"
signature = wallet.hotkey.sign(commitment.encode())
signature_hex = signature.hex()
```

**Success Response** (200):
```json
{
    "access_token": "abc123def456...",
    "expires_at": "2025-01-15T16:00:00Z",
    "expiry_seconds": 21600,
    "sources_authorized": ["ZILLOW_SOLD"],
    "rate_limits": {
        "requests_per_hour": 100,
        "max_batch_size": 50
    }
}
```

**Error Response** (400/401):
```json
{
    "error": "Request timestamp too old or too far in future"
}
```

## Data Block Retrieval

### 2. Get Zipcode Blocks

**Endpoint**: `GET /api/v1/validator-data`

**Purpose**: Get coordinated zipcode blocks for assignment to miners

**Headers**:
```
Authorization: Bearer abc123def456...
```

**Query Parameters**:
- `sources`: Comma-separated list of sources (default: "ZILLOW_SOLD")
- `block_size`: Number of zipcodes per batch (default: 20)
- `format`: Response format (default: "json")

**Example Request**:
```
GET /api/v1/validator-data?sources=ZILLOW_SOLD&block_size=20&format=json
Authorization: Bearer abc123def456...
```

**Success Response** (200):
```json
{
    "request_id": "zipcode_block_20250115_1030_a1b2c3d4",
    "generated_at": "2025-01-15T10:30:00Z",
    "expires_at": "2025-01-15T14:30:00Z",
    "data_blocks": {
        "batch_001": {
            "zipcodes": ["77494", "78701", "90210", "10001", "30309"],
            "expected_properties": 250,
            "assignment_groups": 2,
            "miners_per_group": 10,
            "geographic_info": {
                "states": ["TX", "CA", "NY", "GA"],
                "metros": ["Houston", "Austin", "Los Angeles", "New York", "Atlanta"],
                "size_ranks": [15, 23, 1, 2, 45]
            },
            "sources": ["ZILLOW_SOLD"]
        },
        "batch_002": {
            "zipcodes": ["85001", "98101", "60601", "37201", "33101"],
            "expected_properties": 250,
            "assignment_groups": 2,
            "miners_per_group": 10,
            "geographic_info": {
                "states": ["AZ", "WA", "IL", "TN", "FL"],
                "metros": ["Phoenix", "Seattle", "Chicago", "Nashville", "Miami"],
                "size_ranks": [67, 34, 3, 89, 12]
            },
            "sources": ["ZILLOW_SOLD"]
        }
    },
    "assignment_config": {
        "overlap_factor": 2,
        "miners_per_batch": 10,
        "expected_properties_per_zipcode": 50,
        "assignment_timeout_hours": 4
    },
    "total_batches": 2,
    "total_zipcodes": 10
}
```

## Assignment Status Tracking

### 3. Update Assignment Status

**Endpoint**: `POST /api/v1/assignment-status`

**Purpose**: Report assignment completion status and statistics

**Request Body**:
```json
{
    "assignment_id": "zipcode_assignment_20250115_1030_a1b2c3d4",
    "status": "completed",
    "statistics": {
        "total_miners_assigned": 40,
        "responses_received": 38,
        "consensus_achieved": 35,
        "anomalies_detected": 2,
        "total_properties_scraped": 9450,
        "average_response_time_minutes": 45,
        "success_rate": 0.95
    }
}
```

**Response**:
```json
{
    "success": true,
    "message": "Status updated"
}
```

## Monitoring and Statistics

### 4. Health Check

**Endpoint**: `GET /health`

**Response**:
```json
{
    "status": "healthy",
    "timestamp": "2025-01-15T10:30:00Z",
    "total_zipcodes": 7573,
    "active_assignments": 3
}
```

### 5. API Statistics

**Endpoint**: `GET /api/v1/statistics`

**Response**:
```json
{
    "total_validators": 15,
    "active_assignments": 3,
    "completed_assignments": 127,
    "total_zipcodes_available": 7573,
    "server_uptime": "72h 15m",
    "last_assignment": {
        "assignment_id": "zipcode_assignment_20250115_0630_x9y8z7",
        "status": "completed",
        "timestamp": "2025-01-15T08:45:00Z"
    }
}
```

## Data Block Structure Details

### Zipcode Batch Format

Each batch contains:
- **zipcodes**: Array of 5-digit US zipcodes
- **expected_properties**: Estimated total properties across all zipcodes
- **assignment_groups**: Number of overlapping miner groups (typically 2)
- **miners_per_group**: Number of miners per group (typically 10)
- **geographic_info**: Metadata about zipcode locations and rankings
- **sources**: Data sources to scrape (["ZILLOW_SOLD"])

### Assignment Configuration

- **overlap_factor**: How many groups scrape the same zipcodes (2 = consensus)
- **miners_per_batch**: Total miners assigned per zipcode batch
- **expected_properties_per_zipcode**: Average properties expected per zipcode
- **assignment_timeout_hours**: How long miners have to complete assignment

## Error Handling

### Common Error Codes

- **400**: Bad Request - Invalid parameters or missing fields
- **401**: Unauthorized - Invalid or expired access token
- **403**: Forbidden - Source not authorized for validator
- **429**: Too Many Requests - Rate limit exceeded
- **500**: Internal Server Error - Server-side error

### Error Response Format

```json
{
    "error": "Descriptive error message",
    "error_code": "INVALID_TOKEN",
    "timestamp": "2025-01-15T10:30:00Z",
    "request_id": "req_abc123"
}
```

## Rate Limiting

- **Authentication**: 10 requests per minute per validator
- **Data Blocks**: 1 request per 4 hours per validator (aligned with assignment cycles)
- **Status Updates**: 100 requests per hour per validator
- **Statistics**: 60 requests per hour (public endpoint)

## Security Considerations

### Authentication Security
- Blockchain signature verification prevents impersonation
- Timestamp validation prevents replay attacks (5-minute window)
- Access tokens expire after 6 hours
- Rate limiting prevents abuse

### Data Security
- No sensitive property data stored on API server
- Only zipcode assignments distributed
- All requests logged for audit trail
- HTTPS required in production

## Mock Server Usage

### Development Setup

```bash
# Start mock server
python mock_data_api_server.py --host 0.0.0.0 --port 8000

# Test authentication
curl -X POST http://localhost:8000/get-validator-access \
  -H "Content-Type: application/json" \
  -d '{
    "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    "timestamp": 1705312800,
    "signature": "mock_signature_for_testing",
    "sources": "ZILLOW_SOLD"
  }'

# Test data retrieval
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "http://localhost:8000/api/v1/validator-data?sources=ZILLOW_SOLD&block_size=20"
```

### Configuration

```python
# In validator configuration
DATA_API_CONFIG = {
    'data_api_url': 'http://localhost:8000',  # Mock server
    'sources': ['ZILLOW_SOLD'],
    'block_size_per_source': 20,
    'assignment_timeout_hours': 4,
    'miners_per_batch': 10,
    'overlap_factor': 2
}
```

## Integration with Existing Systems

### Validator Integration

```python
from vali_utils.validator_data_api import ValidatorDataAPI

# Initialize API client
data_api = ValidatorDataAPI(wallet, config.data_api_url)

# Get zipcode blocks
data_blocks = await data_api.get_data_blocks(['ZILLOW_SOLD'], block_size=20)

# Create assignments using ZipcodeAssignmentManager
assignment_manager = ZipcodeAssignmentManager(metagraph, config)
assignments = assignment_manager.create_zipcode_assignments_from_api_blocks(
    data_blocks, available_miners
)
```

### Miner Integration

Miners receive zipcode assignments via existing `DataAssignmentRequest` protocol:

```python
# Assignment received by miner
synapse.assignment_mode = "zipcodes"
synapse.zipcode_assignments = {"ZILLOW_SOLD": ["77494", "78701", "90210"]}
synapse.expected_properties_per_zipcode = 50

# Miner processes zipcode batch
scraped_data = await self._scrape_zipcode_batch(DataSource.ZILLOW_SOLD, zipcodes)
```

## Production Deployment Requirements

### Infrastructure
- Load balancer with SSL termination
- Redis for access token storage
- PostgreSQL for assignment tracking
- Monitoring with Prometheus/Grafana

### Scaling
- Horizontal scaling with multiple API instances
- Database connection pooling
- Caching for frequently requested data
- CDN for static content

### Monitoring
- Request/response metrics
- Error rate tracking
- Assignment completion rates
- Validator participation statistics
