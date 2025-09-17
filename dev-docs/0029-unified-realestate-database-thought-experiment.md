# Unified Real Estate Database Design for Miner Parquet Data

## Overview
Based on analysis of the Bittensor Subnet 46 (RESI) codebase, miners save real estate listings as .parquet files to S3 storage in a structured format. This document outlines a comprehensive solution for creating a unified database that consolidates all miner submissions with full attestation tracking.

## Current S3 Storage Structure

### File Organization
```
S3 Bucket: {base_bucket}/data/
├── hotkey={miner_hotkey_1}/
│   └── job_id={job_id}/
│       ├── data_20250910_120000_1500.parquet
│       ├── data_20250910_120500_890.parquet
│       └── data_20250910_121000_1200.parquet
├── hotkey={miner_hotkey_2}/
│   └── job_id={job_id}/
│       └── data_20250910_120000_2100.parquet
└── hotkey={miner_hotkey_N}/...
```

### Parquet File Naming Convention
- Format: `data_{timestamp}_{record_count}.parquet`
- Timestamp: `YYYYMMDD_HHMMSS` format
- Record count: Number of listings in the file
- Example: `data_20250910_161551_2201.parquet` = 2,201 records uploaded on Sept 10, 2025 at 16:15:51

## Real Estate Data Schema

### Core Fields in Parquet Files
Based on the `_create_raw_dataframe()` function for Zillow data:

```python
# Primary fields stored for each listing:
{
    'uri': str,           # Unique identifier/URL for the listing
    'datetime': datetime, # When the data was scraped
    'label': str,         # Geographic label (zip code)
    'zpid': str,          # Zillow Property ID (unique identifier)
    'price': int,         # Listing price
    'address': str,       # Property address
    'bedrooms': int,      # Number of bedrooms
    'bathrooms': float,   # Number of bathrooms
    'living_area': int,   # Living area in sq ft
    'home_type': str,     # Property type (SINGLE_FAMILY, CONDO, etc.)
    'home_status': str,   # Listing status (FOR_SALE, FOR_RENT, etc.)
    'days_on_zillow': int, # Days the listing has been active
    'url': str,           # Direct URL to the listing
    'zip_code': str,      # Property zip code
    'city': str,          # Property city
    'state': str,         # Property state
    'latitude': float,    # Geographic coordinates
    'longitude': float    # Geographic coordinates
}
```

### Attestation Metadata
Each parquet file inherently contains:
- **Miner Identity**: Embedded in S3 path (`hotkey={miner_hotkey}`)
- **Submission Time**: File creation timestamp in filename
- **Data Volume**: Record count in filename
- **Job Context**: Job ID indicating scraping parameters

## Unified Database Architecture

### 1. Master Listings Table
```sql
CREATE TABLE unified_listings (
    -- Primary identifiers
    zpid VARCHAR(50) PRIMARY KEY,
    uri VARCHAR(500) UNIQUE,
    
    -- Property details
    price BIGINT,
    address TEXT,
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    living_area INTEGER,
    home_type VARCHAR(50),
    home_status VARCHAR(50),
    days_on_zillow INTEGER,
    url TEXT,
    zip_code VARCHAR(10),
    city VARCHAR(100),
    state VARCHAR(10),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    
    -- Unified metadata
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    total_submissions INTEGER DEFAULT 1,
    unique_miners_count INTEGER DEFAULT 1,
    
    -- Data quality indicators
    consensus_score DECIMAL(3,2), -- Agreement ratio across miners
    data_freshness_hours INTEGER,
    
    -- Indexes for performance
    INDEX idx_zip_code (zip_code),
    INDEX idx_price (price),
    INDEX idx_location (latitude, longitude),
    INDEX idx_last_updated (last_updated_at),
    INDEX idx_home_status (home_status)
);
```

### 2. Miner Attestations Table
```sql
CREATE TABLE miner_attestations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Miner identification
    miner_hotkey VARCHAR(100) NOT NULL,
    miner_uid INTEGER,
    
    -- Submission details
    zpid VARCHAR(50) NOT NULL,
    submission_timestamp TIMESTAMP NOT NULL,
    job_id VARCHAR(100),
    parquet_file_path VARCHAR(500),
    record_count INTEGER,
    
    -- Data hash for duplicate detection
    data_hash VARCHAR(64), -- SHA-256 of normalized listing data
    
    -- Validation status
    is_validated BOOLEAN DEFAULT FALSE,
    validation_timestamp TIMESTAMP NULL,
    validation_score DECIMAL(3,2),
    
    FOREIGN KEY (zpid) REFERENCES unified_listings(zpid),
    INDEX idx_miner_hotkey (miner_hotkey),
    INDEX idx_submission_time (submission_timestamp),
    INDEX idx_zpid (zpid),
    INDEX idx_data_hash (data_hash)
);
```

### 3. Data Consensus Tracking
```sql
CREATE TABLE listing_consensus (
    zpid VARCHAR(50) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    field_value TEXT,
    miner_count INTEGER DEFAULT 1,
    first_reported_at TIMESTAMP,
    last_reported_at TIMESTAMP,
    confidence_score DECIMAL(3,2),
    
    PRIMARY KEY (zpid, field_name, field_value),
    FOREIGN KEY (zpid) REFERENCES unified_listings(zpid),
    INDEX idx_confidence (confidence_score DESC)
);
```

## Data Processing Pipeline

### Phase 1: S3 Discovery and Ingestion
```python
def discover_miner_submissions():
    """
    Scan S3 bucket structure to find all miner parquet files
    """
    miners = []
    for hotkey_folder in list_s3_folders(bucket, prefix="hotkey="):
        miner_hotkey = extract_hotkey_from_path(hotkey_folder)
        
        for job_folder in list_s3_folders(hotkey_folder):
            job_id = extract_job_id_from_path(job_folder)
            
            parquet_files = list_s3_files(job_folder, suffix=".parquet")
            for file_path in parquet_files:
                miners.append({
                    'miner_hotkey': miner_hotkey,
                    'job_id': job_id,
                    'file_path': file_path,
                    'timestamp': extract_timestamp_from_filename(file_path),
                    'record_count': extract_record_count_from_filename(file_path)
                })
    
    return miners
```

### Phase 2: Data Normalization and Deduplication
```python
def process_parquet_file(file_info):
    """
    Process individual parquet file and normalize data
    """
    df = pd.read_parquet(file_info['file_path'])
    
    # Normalize data for consistent comparison
    normalized_records = []
    for _, row in df.iterrows():
        normalized = {
            'zpid': str(row['zpid']).strip(),
            'price': int(row['price']) if pd.notna(row['price']) else None,
            'address': normalize_address(row['address']),
            # ... normalize all fields
        }
        
        # Calculate data hash for duplicate detection
        data_hash = calculate_listing_hash(normalized)
        
        normalized_records.append({
            **normalized,
            'miner_hotkey': file_info['miner_hotkey'],
            'submission_timestamp': file_info['timestamp'],
            'data_hash': data_hash,
            'job_id': file_info['job_id'],
            'parquet_file_path': file_info['file_path']
        })
    
    return normalized_records
```

### Phase 3: Consensus Building
```python
def build_consensus_for_listing(zpid, all_submissions):
    """
    Analyze multiple miner submissions for the same listing
    """
    submissions = [s for s in all_submissions if s['zpid'] == zpid]
    unique_miners = set(s['miner_hotkey'] for s in submissions)
    
    consensus_data = {}
    field_consensus = {}
    
    for field in ['price', 'bedrooms', 'bathrooms', 'address', etc.]:
        field_values = {}
        for submission in submissions:
            value = submission.get(field)
            if value is not None:
                value_str = str(value)
                if value_str not in field_values:
                    field_values[value_str] = {
                        'count': 0, 
                        'miners': set(),
                        'first_seen': None,
                        'last_seen': None
                    }
                
                field_values[value_str]['count'] += 1
                field_values[value_str]['miners'].add(submission['miner_hotkey'])
                
                timestamp = submission['submission_timestamp']
                if not field_values[value_str]['first_seen'] or timestamp < field_values[value_str]['first_seen']:
                    field_values[value_str]['first_seen'] = timestamp
                if not field_values[value_str]['last_seen'] or timestamp > field_values[value_str]['last_seen']:
                    field_values[value_str]['last_seen'] = timestamp
        
        # Determine consensus value (most reported by unique miners)
        if field_values:
            consensus_value = max(field_values.items(), 
                                key=lambda x: len(x[1]['miners']))
            
            field_consensus[field] = {
                'value': consensus_value[0],
                'miner_agreement_count': len(consensus_value[1]['miners']),
                'total_unique_miners': len(unique_miners),
                'confidence_score': len(consensus_value[1]['miners']) / len(unique_miners),
                'alternatives': {k: len(v['miners']) for k, v in field_values.items() if k != consensus_value[0]}
            }
    
    return field_consensus, len(unique_miners)
```

## Implementation Strategy

### 1. Batch Processing System
- **Initial Load**: Process all existing parquet files in S3
- **Incremental Updates**: Monitor S3 for new files using event notifications
- **Processing Schedule**: Run consensus rebuilding daily for data quality

### 2. Data Quality Metrics
```python
quality_metrics = {
    'miner_agreement_ratio': agreeing_miners / total_miners,
    'data_freshness_score': 1 - (hours_since_last_update / 168),  # Weekly decay
    'field_completeness': non_null_fields / total_fields,
    'geographic_coverage': unique_zip_codes / total_expected_zip_codes
}
```

### 3. Real-time Query Interface
```sql
-- Get most up-to-date listings with attestation info
SELECT 
    ul.*,
    ul.consensus_score,
    COUNT(ma.id) as total_attestations,
    COUNT(DISTINCT ma.miner_hotkey) as unique_miners,
    MAX(ma.submission_timestamp) as latest_submission,
    GROUP_CONCAT(DISTINCT ma.miner_hotkey) as attesting_miners
FROM unified_listings ul
LEFT JOIN miner_attestations ma ON ul.zpid = ma.zpid
WHERE ul.home_status = 'FOR_SALE'
    AND ul.price BETWEEN 300000 AND 800000
    AND ul.zip_code IN ('90210', '10001', '94102')
    AND ul.consensus_score >= 0.7
GROUP BY ul.zpid
ORDER BY ul.last_updated_at DESC
LIMIT 100;
```

## Benefits of This Approach

### 1. Complete Attestation Tracking
- **Source Attribution**: Every listing traced back to contributing miners
- **Temporal Tracking**: Full history of when data was submitted
- **Validation Status**: Track which submissions have been validator-verified

### 2. Data Quality Assurance
- **Consensus Scoring**: Identify listings with high miner agreement
- **Conflict Resolution**: Handle disagreements between miners systematically
- **Freshness Indicators**: Prioritize recently updated listings

### 3. Network Insights
- **Miner Performance**: Track which miners provide highest quality data
- **Coverage Analysis**: Identify geographic gaps in data collection
- **Duplicate Detection**: Prevent data pollution from repeated submissions

### 4. Scalability
- **Incremental Processing**: Only process new/changed data
- **Horizontal Scaling**: Database can be sharded by geographic region
- **Efficient Queries**: Optimized indexes for common access patterns

## Next Steps for Implementation

1. **Set up S3 access** with read permissions to miner data buckets
2. **Deploy database infrastructure** with the proposed schema
3. **Implement batch processing pipeline** for historical data ingestion
4. **Build real-time monitoring** for new parquet file submissions
5. **Create API layer** for querying unified database
6. **Implement data quality dashboards** for monitoring consensus metrics
7. **Set up automated alerts** for data quality issues or miner anomalies

This unified database would provide the most comprehensive, up-to-date, and well-attributed real estate database from the Bittensor network, with full transparency about data sources and quality metrics.
