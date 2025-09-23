# Validator-Miner Communication Specification

## Current System vs Proposed Changes

This document details the requests validators send to miners and the expected responses, covering both the current system and the proposed validator-controlled data distribution changes.

## Current Request Types

### 1. GetMinerIndex Request
**Purpose**: Retrieve miner's data inventory/index
**Frequency**: Once per evaluation period (4 hours)

**Request Structure:**
```python
class GetMinerIndex(bt.Synapse):
    version: Optional[int] = None
```

**Miner Response:**
```python
{
    "compressed_index_serialized": "base64_encoded_compressed_index",
    "version": 4
}
```

**Response Contains:**
- List of available data buckets with metadata
- Data source types (Zillow, Redfin, etc.)
- Geographic coverage (zipcodes)
- Data freshness timestamps
- Bucket sizes and entity counts

### 2. GetDataEntityBucket Request
**Purpose**: Retrieve specific data bucket contents
**Frequency**: 1 per evaluation period per bucket

**Request Structure:**
```python
class GetDataEntityBucket(bt.Synapse):
    data_entity_bucket_id: DataEntityBucketId  # Contains source, labels, time_bucket
    data_entities: List[DataEntity] = []  # Empty in request
```

**Miner Response:**
```python
{
    "data_entity_bucket_id": {
        "source": "ZILLOW",
        "label": "zip:77494", 
        "time_bucket": {"id": 12345}
    },
    "data_entities": [
        {
            "uri": "https://zillow.com/homedetails/123-main-st/12345_zpid/",
            "datetime": "2025-01-15T10:30:00Z",
            "source": "ZILLOW",
            "label": {"value": "zip:77494"},
            "content": "base64_encoded_property_data",
            "content_size_bytes": 1024
        },
        # ... more entities
    ]
}
```

### 3. OnDemandRequest (Current Real Estate)
**Purpose**: Request specific properties on-demand
**Frequency**: Up to 5 per evaluation period

**Current Request Structure:**
```python
class OnDemandRequest(bt.Synapse):
    source: DataSource  # ZILLOW, REDFIN, REALTOR_COM, HOMES_COM, ZILLOW_SOLD
    
    # Real estate specific fields
    zpids: List[str] = []           # Zillow Property IDs
    redfin_ids: List[str] = []      # Redfin Property IDs  
    addresses: List[str] = []       # Street addresses
    zipcodes: List[str] = []        # Zipcodes (for sold listings)
    
    # Date range
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None    # ISO format
    limit: int = 100                  # Max items to return
    
    # Response field
    data: List[DataEntity] = []
```

**Current Miner Response:**
```python
{
    "source": "ZILLOW",
    "zpids": ["12345", "67890"],
    "data": [
        {
            "uri": "https://zillow.com/homedetails/123-main-st/12345_zpid/",
            "datetime": "2025-01-15T10:30:00Z", 
            "source": "ZILLOW",
            "label": {"value": "zpid:12345"},
            "content": "base64_encoded_json_property_data",
            "content_size_bytes": 1024
        },
        {
            "uri": "https://zillow.com/homedetails/456-oak-ave/67890_zpid/",
            "datetime": "2025-01-15T10:32:00Z",
            "source": "ZILLOW", 
            "label": {"value": "zpid:67890"},
            "content": "base64_encoded_json_property_data",
            "content_size_bytes": 956
        }
    ],
    "limit": 100
}
```

## Proposed New Request Type: DataAssignmentRequest

### Purpose
Distribute coordinated scraping assignments from validators to miners every 4 hours.

### Request Structure
```python
class DataAssignmentRequest(bt.Synapse):
    # Assignment metadata
    request_id: str                              # Unique assignment identifier
    assignment_data: Dict[str, List[str]]        # Property IDs by source
    expires_at: datetime                         # Assignment expiry time
    expected_completion: datetime                # When results are due
    assignment_type: str = "property_scraping"   # Assignment type
    
    # Assignment details
    block_id: str                               # Data block identifier
    priority: int = 1                           # Assignment priority
    
    # Response tracking
    submission_timestamp: Optional[datetime] = None
    scrape_timestamp: Optional[datetime] = None
    completion_status: str = "pending"
```

### Example Request from Validator
```python
{
    "request_id": "assignment_2025011510_block_001",
    "assignment_data": {
        "ZILLOW": ["12345", "67890", "11111", "22222", "33333"],
        "REDFIN": ["abc123", "def456", "ghi789"],
        "REALTOR_COM": ["123 Main St, Austin TX", "456 Oak Ave, Dallas TX"],
        "HOMES_COM": ["789 Pine St, Houston TX", "321 Elm Dr, San Antonio TX"]
    },
    "expires_at": "2025-01-15T14:00:00Z",
    "expected_completion": "2025-01-15T12:00:00Z",
    "assignment_type": "property_scraping",
    "block_id": "data_block_2025011510",
    "priority": 1,
    "completion_status": "pending"
}
```

### Miner Response Structure
```python
{
    "request_id": "assignment_2025011510_block_001",
    "assignment_data": {
        "ZILLOW": ["12345", "67890", "11111", "22222", "33333"],
        "REDFIN": ["abc123", "def456", "ghi789"],
        "REALTOR_COM": ["123 Main St, Austin TX", "456 Oak Ave, Dallas TX"],
        "HOMES_COM": ["789 Pine St, Houston TX", "321 Elm Dr, San Antonio TX"]
    },
    "submission_timestamp": "2025-01-15T10:45:00Z",
    "scrape_timestamp": "2025-01-15T10:30:00Z",  # When scraping started
    "completion_status": "completed",
    "scraped_data": {
        "ZILLOW": [
            {
                "zpid": "12345",
                "uri": "https://zillow.com/homedetails/123-main-st/12345_zpid/",
                "datetime": "2025-01-15T10:30:00Z",
                "source": "ZILLOW",
                "content": "base64_encoded_property_data",
                "content_size_bytes": 1024,
                "scrape_duration_seconds": 15.2
            },
            {
                "zpid": "67890", 
                "uri": "https://zillow.com/homedetails/456-oak-ave/67890_zpid/",
                "datetime": "2025-01-15T10:32:00Z",
                "source": "ZILLOW",
                "content": "base64_encoded_property_data", 
                "content_size_bytes": 956,
                "scrape_duration_seconds": 12.8
            }
            # ... more Zillow properties
        ],
        "REDFIN": [
            {
                "redfin_id": "abc123",
                "uri": "https://redfin.com/property/abc123",
                "datetime": "2025-01-15T10:35:00Z",
                "source": "REDFIN",
                "content": "base64_encoded_property_data",
                "content_size_bytes": 1156,
                "scrape_duration_seconds": 18.5
            }
            # ... more Redfin properties
        ],
        "REALTOR_COM": [
            # ... Realtor.com property data
        ],
        "HOMES_COM": [
            # ... Homes.com property data
        ]
    },
    "assignment_stats": {
        "total_properties_assigned": 12,
        "total_properties_scraped": 11,
        "failed_properties": 1,
        "total_scrape_time_seconds": 185.6,
        "average_scrape_time_seconds": 16.9
    }
}
```

## Property Data Content Structure

### Zillow Property Content (Base64 Decoded)
```json
{
    "zpid": "12345",
    "address": "123 Main St, Austin, TX 78701",
    "price": 450000,
    "bedrooms": 3,
    "bathrooms": 2.5,
    "living_area": 1850,
    "lot_size": 7200,
    "year_built": 2018,
    "property_type": "Single Family",
    "listing_status": "For Sale",
    "days_on_market": 15,
    "zestimate": 465000,
    "rent_zestimate": 2800,
    "price_history": [
        {"date": "2025-01-01", "price": 450000, "event": "Listed"}
    ],
    "neighborhood": "East Austin",
    "schools": {
        "elementary": "Maplewood Elementary",
        "middle": "Austin Middle School", 
        "high": "Austin High School"
    },
    "hoa_fee": 0,
    "property_tax": 8100,
    "last_sold_date": "2020-03-15",
    "last_sold_price": 380000,
    "photos": [
        "https://photos.zillowstatic.com/fp/abc123.jpg"
    ],
    "description": "Beautiful 3-bedroom home in desirable East Austin...",
    "scraped_at": "2025-01-15T10:30:00Z",
    "data_source": "zillow_individual_property_api"
}
```

### Redfin Property Content
```json
{
    "redfin_id": "abc123",
    "address": "456 Oak Ave, Dallas, TX 75201",
    "price": 325000,
    "bedrooms": 2,
    "bathrooms": 2,
    "square_feet": 1200,
    "lot_size": 5000,
    "year_built": 2015,
    "property_type": "Townhouse",
    "status": "Active",
    "days_on_redfin": 8,
    "walk_score": 85,
    "transit_score": 70,
    "bike_score": 75,
    "neighborhood": "Deep Ellum",
    "mls_number": "14567890",
    "listing_agent": "Jane Smith, Redfin",
    "scraped_at": "2025-01-15T10:35:00Z",
    "data_source": "redfin_property_api"
}
```

## Validator Request Flow Changes

### Current Flow
1. **Evaluation Cycle** (every 4 hours)
   - Validator selects 15 miners to evaluate
   - Sends `GetMinerIndex` to each miner
   - Chooses data buckets to validate
   - Sends `GetDataEntityBucket` requests
   - Validates data using RapidAPI Zillow
   - Updates miner scores and credibility

### Proposed New Flow
1. **Data Distribution Cycle** (every 4 hours, synchronized)
   - **Step 1**: Validator authenticates with Data API
   - **Step 2**: Pulls random property blocks by source
   - **Step 3**: Assigns properties to miner groups (5 miners per property)
   - **Step 4**: Sends `DataAssignmentRequest` to assigned miners
   - **Step 5**: Miners scrape assigned properties
   - **Step 6**: Miners return `DataAssignmentRequest` with scraped data
   - **Step 7**: Validators perform statistical consensus analysis
   - **Step 8**: Optional spot-checks if anomalies detected (configurable)
   - **Step 9**: Update miner credibility based on consensus agreement

### Assignment Strategy
```python
# Example assignment for a property
property_assignments = {
    "zpid_12345": {
        "assigned_miners": [45, 78, 102, 156, 203],  # 5 miners
        "assignment_time": "2025-01-15T10:00:00Z",
        "expected_completion": "2025-01-15T12:00:00Z",
        "consensus_threshold": 0.6  # 60% agreement required
    }
}
```

## Response Validation Changes

### Current Validation (Synthetic)
- Validator scrapes same property using RapidAPI
- Compares miner data field-by-field
- Binary valid/invalid result
- Updates credibility based on exact matches

### Proposed Validation (Statistical Consensus)
```python
# Example consensus analysis
consensus_analysis = {
    "zpid_12345": {
        "responses": [
            {"miner_uid": 45, "price": 450000, "bedrooms": 3, "credibility": 0.85},
            {"miner_uid": 78, "price": 450000, "bedrooms": 3, "credibility": 0.92},
            {"miner_uid": 102, "price": 452000, "bedrooms": 3, "credibility": 0.78},
            {"miner_uid": 156, "price": 450000, "bedrooms": 3, "credibility": 0.88},
            {"miner_uid": 203, "price": 449000, "bedrooms": 3, "credibility": 0.82}
        ],
        "consensus": {
            "price": {
                "value": 450000,
                "confidence": 0.75,  # 75% weighted agreement
                "supporting_miners": 3,
                "outliers": [102, 203]
            },
            "bedrooms": {
                "value": 3,
                "confidence": 1.0,   # 100% agreement
                "supporting_miners": 5,
                "outliers": []
            }
        },
        "overall_confidence": 0.87,
        "spot_check_required": false,
        "credibility_updates": {
            "45": 0.02,   # Bonus for agreement
            "78": 0.02,   # Bonus for agreement  
            "102": -0.01, # Penalty for price outlier
            "156": 0.02,  # Bonus for agreement
            "203": -0.01  # Penalty for price outlier
        }
    }
}
```

## Error Handling

### Assignment Request Failures
```python
{
    "request_id": "assignment_2025011510_block_001",
    "completion_status": "failed",
    "error_details": {
        "error_type": "scraping_timeout",
        "error_message": "Zillow API rate limit exceeded",
        "failed_properties": ["12345", "67890"],
        "successful_properties": ["11111", "22222", "33333"],
        "retry_recommended": true
    },
    "submission_timestamp": "2025-01-15T10:45:00Z"
}
```

### Consensus Failures
```python
{
    "zpid_12345": {
        "consensus_status": "failed",
        "reason": "insufficient_responses",
        "responses_received": 2,
        "responses_required": 3,
        "action": "lower_confidence_penalty"
    }
}
```

## Rate Limits and Constraints

### Current Limits
```python
REQUEST_LIMIT_BY_TYPE_PER_PERIOD = {
    GetMinerIndex: 1,           # Once per 4-hour period
    GetDataEntityBucket: 1,     # Once per 4-hour period  
    GetContentsByBuckets: 5,    # 5 times per 4-hour period
    OnDemandRequest: 5,         # 5 times per 4-hour period
}
```

### Proposed Additional Limits
```python
REQUEST_LIMIT_BY_TYPE_PER_PERIOD = {
    # ... existing limits ...
    DataAssignmentRequest: 1,   # Once per 4-hour period (from validators)
    # Response limits for miners
    DataAssignmentResponse: 1,  # Once per assignment
}

# Assignment constraints
ASSIGNMENT_CONSTRAINTS = {
    "max_properties_per_assignment": 50,
    "max_miners_per_property": 5,
    "min_miners_per_property": 3,
    "assignment_timeout_hours": 2,
    "max_concurrent_assignments": 1
}
```

## Implementation Notes

### Miner Changes Required
1. **Add DataAssignmentRequest handler** (copy OnDemandRequest pattern)
2. **Add assignment storage** (track active assignments)
3. **Add timestamp tracking** (scrape start/end times)
4. **Add batch scraping capability** (handle multiple properties per source)
5. **Add assignment status reporting**

### Validator Changes Required  
1. **Add Data API client** (reuse S3 auth pattern)
2. **Add assignment distribution logic** (extend sync cycle)
3. **Add statistical consensus engine** (reuse OrganicQueryProcessor)
4. **Add configurable spot-checking** (use existing scrapers)
5. **Add behavioral anomaly detection** (extend existing system)

### Backward Compatibility
- All existing request types remain functional
- `DataAssignmentRequest` is additive, not replacing current system
- Gradual rollout possible (some validators can use new system while others use current)
- Miners handle both old and new request types simultaneously

This specification provides the complete picture of how validators and miners will communicate in both the current and proposed systems, enabling implementation teams to build the necessary request handlers and response processors.
