# RESI Unified Real Estate Database - Complete Implementation Guide

## Project Overview

This document provides a complete implementation guide for building a unified, attested real estate database that processes miner-uploaded Parquet files from S3 into a Supabase PostgreSQL database with continuous AWS-hosted processing.

## Executive Summary

Based on comprehensive analysis of the RESI subnet codebase, miners upload **incremental data (deltas)** using sophisticated offset tracking. This creates an ideal foundation for building a cost-effective, scalable unified database that:

- ✅ **Processes real-time miner submissions** from S3 Parquet files
- ✅ **Builds consensus data** with confidence scoring
- ✅ **Prevents abuse** through trust-based rate limiting
- ✅ **Stays cost-effective** using Supabase Pro ($25/month)
- ✅ **Scales automatically** with AWS Lambda + SQS architecture

## How Miners Currently Upload Data

### 🔍 **Key Finding: Miners Upload DELTAS, Not Full Datasets**

**Upload Pattern:**
- **Frequency**: Every 2 hours (mainnet) / 5 minutes (testnet)
- **Method**: Incremental uploads using offset-based state tracking
- **Structure**: `hotkey={miner_hotkey}/job_id={job_id}/data_{timestamp}_{record_count}.parquet`
- **State Management**: Each miner tracks `last_offset` per job_id to avoid re-uploading existing data

**Example Upload Cycle:**
```
Cycle 1: zillow_zip_77494: Records 0-1000 (1000 new records)
Cycle 2: zillow_zip_77494: Records 1000-1050 (50 NEW records only)  
Cycle 3: zillow_zip_77494: No new data → Skip upload
```

**State Tracking System:**
```json
{
  "zillow_zip_77494": {
    "last_offset": 1050,
    "total_records_processed": 1050,
    "last_processed_time": "2025-09-17T15:30:00",
    "processing_completed": false
  }
}
```

### 📊 **Data Schema Analysis**

**Core Fields in Parquet Files:**
- `zpid` (Zillow Property ID) - Primary unique identifier
- `uri` - Unique URL identifier  
- `datetime` - Scrape timestamp
- `price`, `address`, `bedrooms`, `bathrooms`, `living_area`
- `home_type`, `home_status`, `days_on_zillow`
- `latitude`, `longitude`, `zip_code`, `city`, `state`

**Attestation Metadata (Embedded in S3 Structure):**
- **Miner Identity**: `hotkey={miner_hotkey}` in S3 path
- **Submission Time**: Timestamp in filename `data_20250917_153000_330.parquet`
- **Data Volume**: Record count in filename
- **Job Context**: `job_id={job_id}` indicates scraping parameters

## Recommended Database Architecture

### 🏗️ **Option 1: Hybrid Architecture (RECOMMENDED)**

**Primary Database: PostgreSQL (Supabase)**
- Store active listings with attestation metadata
- Handle API queries and real-time access
- Size limit: ~50GB to control costs

**Archive Storage: S3 + Delta Lake**
- Historical data and full miner submissions
- Cost-effective long-term storage
- Enable full dataset downloads

**Benefits:**
- ✅ Cost-effective (Supabase stays under expensive tiers)
- ✅ Real-time API performance
- ✅ Complete historical attestation
- ✅ Open data access via S3

### 🗄️ **Database Schema Design**

```sql
-- Core listings table (optimized for queries)
CREATE TABLE listings (
    zpid VARCHAR(50) PRIMARY KEY,
    uri VARCHAR(500) UNIQUE,
    
    -- Property data
    price BIGINT,
    address TEXT,
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    living_area INTEGER,
    home_type VARCHAR(50),
    home_status VARCHAR(50),
    days_on_zillow INTEGER,
    zip_code VARCHAR(10),
    city VARCHAR(100),
    state VARCHAR(10),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    
    -- Consensus metadata
    first_seen_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ,
    consensus_score DECIMAL(3,2), -- Agreement ratio across miners
    total_attestations INTEGER DEFAULT 1,
    unique_miners_count INTEGER DEFAULT 1,
    
    -- Indexes for performance
    INDEX idx_zip_code (zip_code),
    INDEX idx_price (price),
    INDEX idx_location (latitude, longitude),
    INDEX idx_last_updated (last_updated_at),
    INDEX idx_home_status (home_status)
);

-- Miner attestations (tracks all submissions)
CREATE TABLE miner_attestations (
    id BIGSERIAL PRIMARY KEY,
    
    -- Miner identification  
    miner_hotkey VARCHAR(100) NOT NULL,
    miner_uid INTEGER,
    
    -- Submission details
    zpid VARCHAR(50) NOT NULL,
    submission_timestamp TIMESTAMPTZ NOT NULL,
    job_id VARCHAR(100),
    s3_file_path VARCHAR(500),
    record_count INTEGER,
    
    -- Data integrity
    data_hash VARCHAR(64), -- SHA-256 of normalized data
    
    -- Validation status
    is_validated BOOLEAN DEFAULT FALSE,
    validation_timestamp TIMESTAMPTZ,
    validation_score DECIMAL(3,2),
    
    FOREIGN KEY (zpid) REFERENCES listings(zpid),
    INDEX idx_miner_hotkey (miner_hotkey),
    INDEX idx_submission_time (submission_timestamp),
    INDEX idx_zpid (zpid)
);

-- Miner trust scores (prevents DDoS, enables weighting)
CREATE TABLE miner_trust (
    miner_hotkey VARCHAR(100) PRIMARY KEY,
    trust_score DECIMAL(3,2) DEFAULT 0.5, -- 0.0 to 1.0
    total_submissions BIGINT DEFAULT 0,
    validated_submissions BIGINT DEFAULT 0,
    last_submission TIMESTAMPTZ,
    
    -- Rate limiting
    submissions_today INTEGER DEFAULT 0,
    last_submission_date DATE,
    
    -- Quality metrics
    duplicate_rate DECIMAL(3,2) DEFAULT 0.0,
    accuracy_score DECIMAL(3,2) DEFAULT 0.5,
    
    INDEX idx_trust_score (trust_score DESC),
    INDEX idx_last_submission (last_submission)
);
```

## Cost Management Strategy

### 💰 **Supabase Cost Control**

**Database Size Management:**
- **Target**: Keep under 8GB (free tier) or 50GB (pro tier $25/month)
- **Method**: Archive old listings, focus on active/recent data
- **Retention**: 6 months active data in Supabase, rest in S3

**Query Optimization:**
- Use indexes strategically (zip_code, price ranges, location)
- Implement query result caching
- Use read replicas for heavy analytics

**Rate Limiting:**
```sql
-- Prevent miner DDoS with daily submission limits
CREATE OR REPLACE FUNCTION check_miner_rate_limit(hotkey TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    daily_count INTEGER;
    trust_score DECIMAL(3,2);
    max_daily_submissions INTEGER;
BEGIN
    -- Get current submissions and trust score
    SELECT submissions_today, miner_trust.trust_score 
    INTO daily_count, trust_score
    FROM miner_trust 
    WHERE miner_hotkey = hotkey;
    
    -- Calculate max submissions based on trust
    max_daily_submissions := CASE 
        WHEN trust_score >= 0.8 THEN 10000
        WHEN trust_score >= 0.6 THEN 5000  
        WHEN trust_score >= 0.4 THEN 1000
        ELSE 100
    END;
    
    RETURN daily_count < max_daily_submissions;
END;
$$ LANGUAGE plpgsql;
```

## Delta Detection & Incremental Updates

### 🔄 **S3 Event-Driven Processing**

**Architecture:**
```
S3 New File → SQS Queue → Lambda/Worker → Database Update
```

**Processing Logic:**
```python
def process_new_parquet_file(s3_event):
    """Process newly uploaded parquet file"""
    
    # Extract metadata from S3 path
    file_info = extract_file_metadata(s3_event['s3_key'])
    # hotkey=5C7VLTuy.../job_id=zillow_zip_77494/data_20250917_153000_330.parquet
    
    miner_hotkey = file_info['miner_hotkey']
    job_id = file_info['job_id'] 
    timestamp = file_info['timestamp']
    record_count = file_info['record_count']
    
    # Check rate limits and trust score
    if not check_miner_rate_limit(miner_hotkey):
        log_and_reject("Rate limit exceeded", miner_hotkey)
        return
    
    # Download and process parquet file
    df = pd.read_parquet(s3_event['s3_url'])
    
    # Process each listing
    for _, row in df.iterrows():
        zpid = row['zpid']
        
        # Check if listing exists
        existing = get_listing(zpid)
        
        if existing:
            # Update consensus if data differs
            update_listing_consensus(zpid, row, miner_hotkey, timestamp)
        else:
            # Create new listing
            create_listing(row, miner_hotkey, timestamp)
        
        # Record attestation
        record_attestation(zpid, miner_hotkey, job_id, timestamp, s3_event['s3_key'])
    
    # Update miner trust metrics
    update_miner_trust(miner_hotkey, record_count, validation_results)
```

### 📈 **Consensus Building Algorithm**

```python
def update_listing_consensus(zpid, new_data, miner_hotkey, timestamp):
    """Update listing with consensus from multiple miners"""
    
    # Get all attestations for this listing
    attestations = get_attestations(zpid)
    unique_miners = set(a['miner_hotkey'] for a in attestations)
    
    # Build field consensus
    consensus_data = {}
    for field in ['price', 'bedrooms', 'bathrooms', 'address']:
        field_values = {}
        
        for attestation in attestations:
            value = attestation.get(field)
            if value:
                if value not in field_values:
                    field_values[value] = {'miners': set(), 'trust_sum': 0}
                
                field_values[value]['miners'].add(attestation['miner_hotkey'])
                field_values[value]['trust_sum'] += get_miner_trust(attestation['miner_hotkey'])
        
        # Choose consensus value (weighted by miner trust)
        if field_values:
            consensus_value = max(field_values.items(), 
                                key=lambda x: x[1]['trust_sum'])
            
            consensus_data[field] = {
                'value': consensus_value[0],
                'confidence': len(consensus_value[1]['miners']) / len(unique_miners),
                'supporting_miners': len(consensus_value[1]['miners'])
            }
    
    # Update listing with consensus data
    update_listing(zpid, consensus_data)
```

## Anti-DDoS & Miner Verification

### 🛡️ **Multi-Layer Protection**

**1. Rate Limiting:**
- Daily submission limits based on miner trust score
- Progressive penalties for excessive submissions
- Temporary bans for abuse patterns

**2. Data Quality Checks:**
```python
def validate_submission_quality(df, miner_hotkey):
    """Validate data quality to prevent spam"""
    
    quality_score = 1.0
    issues = []
    
    # Check for obvious fake data
    if df['price'].min() < 1000 or df['price'].max() > 100_000_000:
        quality_score *= 0.5
        issues.append("Suspicious price ranges")
    
    # Check for duplicate zpids within submission
    if df['zpid'].duplicated().any():
        quality_score *= 0.3
        issues.append("Duplicate zpids in submission")
    
    # Check for realistic geographic clustering
    if df['zip_code'].nunique() > 50:  # Too many zip codes
        quality_score *= 0.7
        issues.append("Excessive geographic spread")
    
    # Check against known bad data patterns
    bad_patterns = check_against_blacklist(df)
    if bad_patterns:
        quality_score *= 0.1
        issues.extend(bad_patterns)
    
    return quality_score, issues
```

**3. Trust Score Evolution:**
```python
def update_miner_trust(miner_hotkey, submission_quality, validation_results):
    """Update miner trust based on submission quality"""
    
    current_trust = get_miner_trust(miner_hotkey)
    
    # Positive adjustments
    if validation_results.get('validator_confirmed', False):
        trust_adjustment = +0.1
    elif submission_quality > 0.8:
        trust_adjustment = +0.05
    
    # Negative adjustments  
    elif submission_quality < 0.3:
        trust_adjustment = -0.2
    elif validation_results.get('contains_fake_data', False):
        trust_adjustment = -0.5
    
    # Apply adjustment with decay
    new_trust = current_trust * 0.95 + trust_adjustment
    new_trust = max(0.0, min(1.0, new_trust))  # Clamp to [0,1]
    
    update_miner_trust_score(miner_hotkey, new_trust)
```

## Implementation Strategy

### 🚀 **Recommended Approach: Separate Repository**

**Create New Repository: `resi-unified-database`**

**Reasons:**
- ✅ **Clean Architecture**: Focused on database/API concerns only
- ✅ **Open Source Friendly**: Easy for community to contribute
- ✅ **Independent Deployment**: Can scale database independently
- ✅ **Clear Separation**: Miners upload to S3, database processes separately
- ✅ **Multiple Consumers**: Other projects can use the unified database

**Repository Structure:**
```
resi-unified-database/
├── src/
│   ├── database/             # Database layer & schema
│   │   ├── schema/          # Prisma schema & migrations
│   │   ├── models/          # Data models/types
│   │   └── queries/         # Common queries
│   ├── ingestion/           # S3 event processing
│   │   ├── lambda/          # AWS Lambda functions
│   │   ├── processors/      # Parquet file processors
│   │   └── validators/      # Data validation
│   ├── consensus/           # Consensus algorithms  
│   ├── api/                # REST/GraphQL API
│   ├── trust/              # Miner trust system
│   └── monitoring/         # Quality metrics
├── infrastructure/         # Terraform/CloudFormation
│   ├── aws/               # AWS resources
│   ├── supabase/          # Supabase configuration
│   └── monitoring/        # CloudWatch, alerts
├── docs/                  # API documentation
├── tests/                # Comprehensive test suite
└── scripts/              # Deployment & utility scripts
```

### 📋 **Implementation Phases**

**Phase 1: MVP Database (4-6 weeks)**
- Set up PostgreSQL schema
- Basic S3 event processing
- Simple consensus algorithm
- Basic API endpoints

**Phase 2: Trust & Anti-DDoS (2-3 weeks)**  
- Implement miner trust scoring
- Add rate limiting and quality checks
- Enhanced validation integration

**Phase 3: Advanced Features (4-6 weeks)**
- Real-time consensus updates
- Advanced analytics API
- Tiling server capabilities
- Performance optimization

**Phase 4: Open Source Release (2-3 weeks)**
- Documentation and examples
- Community contribution guidelines
- Public API documentation

## Data Access Strategy

### 🌐 **Hybrid Open/Closed Model**

**Open Data Access:**
- ✅ **Full S3 Downloads**: Anyone can download complete parquet datasets
- ✅ **Historical Data**: All historical submissions available
- ✅ **Raw Miner Data**: Complete transparency of miner contributions

**Premium Hosted Database:**
- 🔒 **Real-time API**: Live, consensus-built data with confidence scores
- 🔒 **Advanced Queries**: Complex filtering, aggregation, analytics
- 🔒 **Tiling Server**: Map tile generation for visualization
- 🔒 **Quality Assurance**: Validated, deduplicated, consensus data

**Benefits:**
- Maintains open source principles (raw data accessible)
- Creates sustainable business model (hosted API services)
- Encourages innovation (others can build competing databases)
- Provides fallback (if hosted service fails, S3 data remains)

## Cost Projections

### 💰 **Estimated Monthly Costs**

**Supabase (Pro Plan): $25/month**
- 8GB database storage
- 100GB bandwidth
- Suitable for ~2M active listings

**AWS Costs: ~$50-100/month**
- Lambda processing: $20
- SQS queues: $5  
- S3 storage (archive): $25-50
- CloudWatch monitoring: $10

**Total: ~$75-125/month**

**Revenue Potential:**
- API access subscriptions: $50-500/month per customer
- Enterprise integrations: $1000+/month
- Break-even: 2-3 API customers

## Next Steps & Action Items

### 🎯 **Immediate Actions (Week 1)**

1. **Validate S3 Access**: Confirm you can read all miner parquet files
2. **Set Up Development Environment**: PostgreSQL + basic schema
3. **Create Repository**: `resi-unified-database` with initial structure
4. **Test Data Processing**: Process sample parquet files locally

### 📈 **Development Roadmap (Weeks 2-12)**

**Weeks 2-4: Core Database**
- Implement PostgreSQL schema
- Basic parquet file processing
- Simple consensus algorithm
- Basic API endpoints

**Weeks 5-6: Trust System**
- Miner trust scoring
- Rate limiting implementation
- Quality validation checks

**Weeks 7-10: Advanced Features**
- Real-time processing pipeline
- Enhanced consensus algorithms
- Performance optimization
- Comprehensive testing

**Weeks 11-12: Production Deployment**
- Infrastructure setup (Terraform)
- Monitoring and alerting
- Documentation and examples
- Community launch

## Conclusion

The RESI subnet's incremental upload system is perfectly suited for building a cost-effective, real-time unified database. By leveraging the existing S3 structure and implementing smart consensus algorithms, you can create a valuable service that:

- ✅ **Stays Cost-Effective**: Smart data management keeps Supabase costs low
- ✅ **Prevents Abuse**: Multi-layer trust and rate limiting systems
- ✅ **Maintains Quality**: Consensus algorithms ensure data accuracy  
- ✅ **Enables Innovation**: Open data access encourages ecosystem growth
- ✅ **Creates Value**: Premium API services provide sustainable revenue

The hybrid open/closed model balances open source principles with sustainable business operations, making this both a valuable community resource and a viable commercial product.
