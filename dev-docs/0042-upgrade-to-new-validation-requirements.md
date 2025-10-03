# 🎯 Bittensor Subnet 46: Validator & Miner Integration Plan for Zipcode-Based Real Estate Mining

## 📋 **Executive Summary**

This document provides a comprehensive integration plan for upgrading the existing Bittensor Subnet 46 validator and miner code to work with the new NestJS API server that implements zipcode-based competitive real estate data mining. The new system introduces epoch-based zipcode assignments, S3 data storage, and validator-driven scoring mechanisms.

---

## 🏗️ **System Architecture Overview**

### **Current State vs. New State**

#### **Before (Legacy System)**
- Miners scrape arbitrary real estate data
- No centralized coordination or assignments
- Manual data validation and scoring
- Limited anti-gaming mechanisms

#### **After (New Zipcode System)**
- **Epoch-Based Mining**: 4-hour competitive mining cycles
- **Centralized Zipcode Assignment**: API server assigns specific zipcodes to prevent overlap
- **S3 Data Storage**: Structured data upload and validation
- **Automated Validator Scoring**: Validators download, analyze, and score miner submissions
- **Anti-Gaming Features**: Honeypot zipcodes, nonce verification, signature authentication

---

## 🌐 **API Server Integration Details**

### **Base Configuration**
```bash
# Production API Server
BASE_URL: https://api.resilabs.com
SWAGGER_DOCS: https://api.resilabs.com/docs
HEALTH_CHECK: https://api.resilabs.com/healthcheck

# Development/Testing
BASE_URL: http://localhost:3000
```

### **Authentication System**
All API calls require Bittensor hotkey signatures with specific commitment formats:

```python
# Signature Generation Template
def generate_signature(hotkey, commitment_string):
    commitment_bytes = commitment_string.encode('utf-8')
    signature = hotkey.sign(commitment_bytes).hex()
    return signature

# Commitment Formats by Endpoint
MINER_ZIPCODE_REQUEST = "zipcode:assignment:current:{timestamp}"
MINER_STATUS_UPDATE = "miner:status:{hotkey}:{epochId}:{timestamp}"
MINER_S3_ACCESS = "s3:data:access:{coldkey}:{hotkey}:{timestamp}"
VALIDATOR_S3_ACCESS = "s3:validator:upload:{timestamp}"
```

---

## 🗺️ **Core API Endpoints for Integration**

### **1. Miner Zipcode Assignment**
```http
GET /api/v1/zipcode-assignments/current?hotkey={hotkey}&signature={signature}&timestamp={timestamp}
```

**Purpose**: Get current epoch's zipcode assignments for competitive mining

**Response Structure**:
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

### **2. Miner S3 Data Upload**
```http
POST /get-folder-access
```

**Purpose**: Get S3 upload credentials for miner data submission

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

### **3. Miner Status Updates**
```http
POST /api/v1/zipcode-assignments/status
```

**Purpose**: Update mining progress and completion status

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

### **4. Validator S3 Access**
```http
POST /api/v1/s3-access/validator-upload
```

**Purpose**: Get S3 upload credentials for validator result storage

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

### **5. System Statistics**
```http
GET /api/v1/zipcode-assignments/stats
```

**Purpose**: Get system-wide statistics for monitoring and decision-making

---

## 🔄 **Epoch System & Workflow**

### **Epoch Schedule**
- **Duration**: 4 hours per epoch
- **Schedule**: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
- **ID Format**: `YYYY-MM-DDTHH-00-00` (e.g., `2025-10-01T16-00-00`)

### **Epoch Lifecycle**
1. **PENDING** (15 minutes before start): Zipcode assignments generated
2. **ACTIVE** (4 hours): Miners can request assignments and submit data
3. **COMPLETED** (30 minutes): Validators process and score submissions
4. **ARCHIVED**: Results stored, next epoch begins

### **Zipcode Assignment Algorithm**
- **Target**: 10,000 total expected listings per epoch
- **Tolerance**: ±10% (9,000-11,000 listings)
- **Selection**: Weighted by market tier and historical performance
- **Anti-Gaming**: Honeypot zipcodes (5-10% of assignments)
- **Fairness**: Rotation algorithm prevents repeated assignments

---

## 🤖 **Miner Integration Requirements**

### **1. Startup & Initialization**
```python
class ResiLabsMiner:
    def __init__(self, hotkey, coldkey, api_base_url):
        self.hotkey = hotkey
        self.coldkey = coldkey
        self.api = ResiLabsAPI(api_base_url, hotkey, coldkey)
        self.current_epoch = None
        self.assigned_zipcodes = []
        self.mining_status = "IDLE"
    
    def initialize(self):
        """Initialize miner and check API connectivity"""
        health = self.api.check_health()
        if not health['status'] == 'ok':
            raise Exception("API server not available")
        
        self.logger.info(f"Connected to API server v{health['version']}")
```

### **2. Epoch Detection & Assignment Request**
```python
def start_epoch_mining(self):
    """Request zipcode assignments for current epoch"""
    try:
        # Get current epoch assignments
        assignment_response = self.api.get_current_zipcodes()
        
        if not assignment_response['success']:
            self.logger.error("Failed to get zipcode assignments")
            return False
        
        self.current_epoch = {
            'id': assignment_response['epochId'],
            'start_time': assignment_response['epochStart'],
            'end_time': assignment_response['epochEnd'],
            'nonce': assignment_response['nonce'],
            'target_listings': assignment_response['targetListings'],
            'deadline': assignment_response['submissionDeadline']
        }
        
        self.assigned_zipcodes = assignment_response['zipcodes']
        self.mining_status = "IN_PROGRESS"
        
        self.logger.info(f"Epoch {self.current_epoch['id']}: Assigned {len(self.assigned_zipcodes)} zipcodes")
        
        # Start mining process
        return self.execute_mining_process()
        
    except Exception as e:
        self.logger.error(f"Epoch assignment failed: {e}")
        return False
```

### **3. Data Mining Process**
```python
def execute_mining_process(self):
    """Execute mining for assigned zipcodes"""
    completed_zipcodes = []
    total_listings = 0
    
    for zipcode_assignment in self.assigned_zipcodes:
        zipcode = zipcode_assignment['zipcode']
        expected_listings = zipcode_assignment['expectedListings']
        
        self.logger.info(f"Mining zipcode {zipcode} (target: {expected_listings} listings)")
        
        try:
            # Scrape real estate data for this zipcode
            listings_data = self.scrape_zipcode_data(zipcode, expected_listings)
            
            # Validate and format data
            formatted_data = self.format_listings_data(listings_data, zipcode)
            
            # Store locally for batch upload
            self.store_zipcode_data(zipcode, formatted_data)
            
            completed_zipcodes.append({
                'zipcode': zipcode,
                'listingsScraped': len(listings_data),
                'completedAt': datetime.utcnow().isoformat() + 'Z'
            })
            
            total_listings += len(listings_data)
            
            # Update progress periodically
            if len(completed_zipcodes) % 5 == 0:
                self.update_mining_status(completed_zipcodes, total_listings, "IN_PROGRESS")
                
        except Exception as e:
            self.logger.error(f"Failed to mine zipcode {zipcode}: {e}")
            continue
    
    # Upload all data to S3
    s3_success = self.upload_data_to_s3()
    
    # Final status update
    final_status = "COMPLETED" if s3_success else "FAILED"
    self.update_mining_status(completed_zipcodes, total_listings, final_status, s3_success)
    
    return s3_success
```

### **4. S3 Data Upload**
```python
def upload_data_to_s3(self):
    """Upload mined data to S3 using API credentials"""
    try:
        # Get S3 upload credentials
        s3_creds = self.api.get_s3_credentials()
        
        if not s3_creds['success']:
            self.logger.error("Failed to get S3 credentials")
            return False
        
        # Prepare data files
        data_files = self.prepare_data_files()
        
        # Upload each file to S3
        for file_path, file_data in data_files.items():
            upload_success = self.upload_file_to_s3(
                file_data, 
                s3_creds['uploadUrl'], 
                s3_creds['fields'],
                file_path
            )
            
            if not upload_success:
                self.logger.error(f"Failed to upload {file_path}")
                return False
        
        self.logger.info(f"Successfully uploaded {len(data_files)} files to S3")
        return True
        
    except Exception as e:
        self.logger.error(f"S3 upload failed: {e}")
        return False

def prepare_data_files(self):
    """Prepare data files in required format"""
    files = {}
    
    # Main listings data (Parquet format preferred)
    listings_df = self.compile_all_listings_data()
    files['listings.parquet'] = listings_df.to_parquet()
    
    # Metadata file
    metadata = {
        'epoch_id': self.current_epoch['id'],
        'miner_hotkey': str(self.hotkey.ss58_address),
        'mining_start_time': self.mining_start_time,
        'mining_end_time': datetime.utcnow().isoformat(),
        'total_listings': len(listings_df),
        'zipcodes_completed': len(self.assigned_zipcodes),
        'data_format_version': '2.0'
    }
    files['metadata.json'] = json.dumps(metadata, indent=2)
    
    return files
```

### **5. Status Updates**
```python
def update_mining_status(self, completed_zipcodes, total_listings, status, s3_complete=False):
    """Update mining status via API"""
    try:
        response = self.api.update_miner_status(
            epoch_id=self.current_epoch['id'],
            nonce=self.current_epoch['nonce'],
            status=status,
            listings_scraped=total_listings,
            zipcodes_completed=completed_zipcodes,
            s3_upload_complete=s3_complete,
            s3_upload_timestamp=datetime.utcnow().isoformat() + 'Z' if s3_complete else None
        )
        
        if response['success']:
            self.logger.info(f"Status updated: {status} ({total_listings} listings)")
        else:
            self.logger.error(f"Status update failed: {response.get('message', 'Unknown error')}")
            
    except Exception as e:
        self.logger.error(f"Status update error: {e}")
```

---

## 🏆 **Validator Integration Requirements**

### **1. Validator Initialization**
```python
class ResiLabsValidator:
    def __init__(self, hotkey, api_base_url):
        self.hotkey = hotkey
        self.api = ResiLabsAPI(api_base_url, hotkey)
        self.current_epoch = None
        self.miner_submissions = {}
        self.validation_results = {}
    
    def initialize(self):
        """Initialize validator and check API connectivity"""
        health = self.api.check_health()
        if not health['status'] == 'ok':
            raise Exception("API server not available")
        
        # Verify validator status
        if not self.api.verify_validator_status():
            raise Exception("Hotkey is not registered as validator")
        
        self.logger.info(f"Validator initialized for hotkey {self.hotkey.ss58_address}")
```

### **2. Epoch Monitoring & Data Collection**
```python
def monitor_epoch_completion(self):
    """Monitor for epoch completion and collect miner data"""
    while True:
        try:
            # Check system statistics
            stats = self.api.get_system_statistics()
            current_epoch = stats['epochStatus']['currentEpoch']
            
            # If epoch just completed, start validation process
            if (current_epoch['status'] == 'COMPLETED' and 
                current_epoch['id'] != self.last_processed_epoch):
                
                self.logger.info(f"Epoch {current_epoch['id']} completed, starting validation")
                self.validate_epoch(current_epoch)
                self.last_processed_epoch = current_epoch['id']
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            self.logger.error(f"Epoch monitoring error: {e}")
            time.sleep(300)  # Wait 5 minutes on error
```

### **3. Miner Data Download & Analysis**
```python
def validate_epoch(self, epoch_info):
    """Download and validate all miner submissions for an epoch"""
    try:
        # Get list of miner submissions for this epoch
        submissions = self.api.get_epoch_submissions(epoch_info['id'])
        
        self.logger.info(f"Found {len(submissions)} miner submissions for epoch {epoch_info['id']}")
        
        validation_results = {}
        
        for submission in submissions:
            miner_hotkey = submission['minerHotkey']
            
            try:
                # Download miner's S3 data
                miner_data = self.download_miner_data(miner_hotkey, epoch_info['id'])
                
                # Validate data quality and accuracy
                validation_score = self.validate_miner_data(miner_data, submission)
                
                validation_results[miner_hotkey] = {
                    'score': validation_score,
                    'data_quality': validation_score['data_quality'],
                    'accuracy': validation_score['accuracy'],
                    'completeness': validation_score['completeness'],
                    'timeliness': validation_score['timeliness'],
                    'total_score': validation_score['total_score']
                }
                
                self.logger.info(f"Validated {miner_hotkey}: Score {validation_score['total_score']:.2f}")
                
            except Exception as e:
                self.logger.error(f"Failed to validate {miner_hotkey}: {e}")
                validation_results[miner_hotkey] = {
                    'score': 0.0,
                    'error': str(e)
                }
        
        # Upload validation results
        self.upload_validation_results(epoch_info['id'], validation_results)
        
        # Update Bittensor weights based on scores
        self.update_bittensor_weights(validation_results)
        
    except Exception as e:
        self.logger.error(f"Epoch validation failed: {e}")

def validate_miner_data(self, miner_data, submission_info):
    """Validate miner data quality and accuracy"""
    
    # Load miner's data files
    listings_df = pd.read_parquet(miner_data['listings.parquet'])
    metadata = json.loads(miner_data['metadata.json'])
    
    # Initialize scoring components
    scores = {
        'data_quality': 0.0,
        'accuracy': 0.0,
        'completeness': 0.0,
        'timeliness': 0.0
    }
    
    # 1. Data Quality Assessment (25% of score)
    quality_score = self.assess_data_quality(listings_df)
    scores['data_quality'] = quality_score
    
    # 2. Accuracy Verification (35% of score)
    # Sample and verify a subset of listings
    accuracy_score = self.verify_listing_accuracy(listings_df)
    scores['accuracy'] = accuracy_score
    
    # 3. Completeness Check (25% of score)
    # Check if all assigned zipcodes were attempted
    completeness_score = self.check_completeness(listings_df, submission_info)
    scores['completeness'] = completeness_score
    
    # 4. Timeliness Score (15% of score)
    # Check submission timing
    timeliness_score = self.assess_timeliness(metadata, submission_info)
    scores['timeliness'] = timeliness_score
    
    # Calculate weighted total score
    total_score = (
        scores['data_quality'] * 0.25 +
        scores['accuracy'] * 0.35 +
        scores['completeness'] * 0.25 +
        scores['timeliness'] * 0.15
    )
    
    scores['total_score'] = total_score
    
    return scores

def assess_data_quality(self, listings_df):
    """Assess data quality metrics"""
    quality_metrics = {
        'required_fields_present': 0.0,
        'data_types_correct': 0.0,
        'no_duplicates': 0.0,
        'reasonable_values': 0.0
    }
    
    # Check required fields
    required_fields = ['address', 'price', 'bedrooms', 'bathrooms', 'sqft', 'listing_date', 'zipcode']
    fields_present = sum(1 for field in required_fields if field in listings_df.columns)
    quality_metrics['required_fields_present'] = fields_present / len(required_fields)
    
    # Check data types
    type_score = self.validate_data_types(listings_df)
    quality_metrics['data_types_correct'] = type_score
    
    # Check for duplicates
    duplicate_rate = listings_df.duplicated().sum() / len(listings_df)
    quality_metrics['no_duplicates'] = max(0, 1.0 - duplicate_rate)
    
    # Check for reasonable values
    reasonable_score = self.validate_reasonable_values(listings_df)
    quality_metrics['reasonable_values'] = reasonable_score
    
    # Average all quality metrics
    return sum(quality_metrics.values()) / len(quality_metrics)

def verify_listing_accuracy(self, listings_df):
    """Verify accuracy by sampling and cross-checking listings"""
    
    # Sample 10% of listings for verification (minimum 5, maximum 50)
    sample_size = max(5, min(50, int(len(listings_df) * 0.1)))
    sample_listings = listings_df.sample(n=sample_size)
    
    verified_count = 0
    
    for _, listing in sample_listings.iterrows():
        try:
            # Attempt to verify listing exists and details are accurate
            is_accurate = self.verify_single_listing(listing)
            if is_accurate:
                verified_count += 1
        except Exception as e:
            self.logger.warning(f"Could not verify listing: {e}")
            continue
    
    accuracy_rate = verified_count / sample_size
    return accuracy_rate

def check_completeness(self, listings_df, submission_info):
    """Check if miner completed all assigned zipcodes"""
    
    assigned_zipcodes = set(submission_info['assignedZipcodes'])
    completed_zipcodes = set(listings_df['zipcode'].unique())
    
    # Calculate completion rate
    completion_rate = len(completed_zipcodes.intersection(assigned_zipcodes)) / len(assigned_zipcodes)
    
    # Check if target listing counts were met
    target_met_score = 0.0
    for zipcode in assigned_zipcodes:
        zipcode_listings = listings_df[listings_df['zipcode'] == zipcode]
        expected_count = submission_info['zipcodeTargets'].get(zipcode, 0)
        actual_count = len(zipcode_listings)
        
        # Score based on how close to target (within tolerance)
        if expected_count > 0:
            ratio = actual_count / expected_count
            if 0.9 <= ratio <= 1.1:  # Within 10% tolerance
                target_met_score += 1.0
            elif 0.8 <= ratio <= 1.2:  # Within 20% tolerance
                target_met_score += 0.7
            elif 0.7 <= ratio <= 1.3:  # Within 30% tolerance
                target_met_score += 0.4
    
    if len(assigned_zipcodes) > 0:
        target_met_score /= len(assigned_zipcodes)
    
    # Combine completion rate and target achievement
    return (completion_rate * 0.6) + (target_met_score * 0.4)
```

### **4. Validator Result Upload**
```python
def upload_validation_results(self, epoch_id, validation_results):
    """Upload validation results to S3"""
    try:
        # Get S3 upload credentials for validators
        s3_creds = self.api.get_validator_s3_credentials(epoch_id)
        
        if not s3_creds['success']:
            self.logger.error("Failed to get validator S3 credentials")
            return False
        
        # Prepare validation results file
        results_data = {
            'epoch_id': epoch_id,
            'validator_hotkey': str(self.hotkey.ss58_address),
            'validation_timestamp': datetime.utcnow().isoformat(),
            'validation_results': validation_results,
            'summary': {
                'total_miners': len(validation_results),
                'average_score': sum(r.get('total_score', 0) for r in validation_results.values()) / len(validation_results),
                'top_performers': sorted(validation_results.items(), key=lambda x: x[1].get('total_score', 0), reverse=True)[:10]
            }
        }
        
        # Upload to S3
        file_content = json.dumps(results_data, indent=2)
        upload_success = self.upload_file_to_s3(
            file_content,
            s3_creds['uploadUrl'],
            s3_creds['fields'],
            f"validation_results_{epoch_id}.json"
        )
        
        if upload_success:
            self.logger.info(f"Uploaded validation results for epoch {epoch_id}")
        
        return upload_success
        
    except Exception as e:
        self.logger.error(f"Failed to upload validation results: {e}")
        return False
```

### **5. Bittensor Weight Updates**
```python
def update_bittensor_weights(self, validation_results):
    """Update Bittensor weights based on validation scores"""
    try:
        # Convert validation scores to weight distribution
        weights = {}
        
        for miner_hotkey, results in validation_results.items():
            score = results.get('total_score', 0.0)
            
            # Convert score to weight (0.0 to 1.0)
            weight = max(0.0, min(1.0, score))
            weights[miner_hotkey] = weight
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            for hotkey in weights:
                weights[hotkey] = weights[hotkey] / total_weight
        
        # Update Bittensor weights
        success = self.subtensor.set_weights(
            wallet=self.wallet,
            netuid=46,
            uids=list(weights.keys()),
            weights=list(weights.values()),
            wait_for_inclusion=True
        )
        
        if success:
            self.logger.info(f"Updated Bittensor weights for {len(weights)} miners")
        
        return success
        
    except Exception as e:
        self.logger.error(f"Failed to update Bittensor weights: {e}")
        return False
```

---

## 📊 **Data Formats & Standards**

### **Miner Data Upload Format**
```json
{
  "listings.parquet": "Binary Parquet file with listing data",
  "metadata.json": {
    "epoch_id": "2025-10-01T16-00-00",
    "miner_hotkey": "5H2WNbNfkRmHWJGdEUzZyVd7jZuP3BkwNDYgZQF8a1BcKwGx",
    "mining_start_time": "2025-10-01T16:05:00.000Z",
    "mining_end_time": "2025-10-01T19:45:00.000Z",
    "total_listings": 1250,
    "zipcodes_completed": 25,
    "data_format_version": "2.0"
  }
}
```

### **Required Listing Data Schema**
```python
REQUIRED_LISTING_FIELDS = {
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

### **Validator Results Format**
```json
{
  "epoch_id": "2025-10-01T16-00-00",
  "validator_hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
  "validation_timestamp": "2025-10-01T20:30:00.000Z",
  "validation_results": {
    "miner_hotkey_1": {
      "score": {
        "data_quality": 0.85,
        "accuracy": 0.92,
        "completeness": 0.78,
        "timeliness": 0.95,
        "total_score": 0.87
      }
    }
  },
  "summary": {
    "total_miners": 150,
    "average_score": 0.73,
    "top_performers": [...]
  }
}
```

---

## 🔒 **Security & Anti-Gaming Measures**

### **1. Honeypot Detection**
- **Implementation**: 5-10% of zipcode assignments are honeypots
- **Detection**: Validators check for impossible/fake listings in honeypot zipcodes
- **Penalty**: Miners submitting honeypot data receive zero score

### **2. Signature Verification**
- **All API calls** require valid Bittensor hotkey signatures
- **Timestamp validation** prevents replay attacks (±5 minute window)
- **Nonce verification** ensures epoch authenticity

### **3. Rate Limiting**
- **Miner zipcode requests**: 10/minute per hotkey
- **S3 access requests**: 20/day per miner
- **Status updates**: 5/minute per hotkey

### **4. Data Validation**
- **Cross-verification**: Validators sample and verify listing accuracy
- **Duplicate detection**: Penalize duplicate listings across miners
- **Reasonable value checks**: Flag unrealistic property data

---

## ⚡ **Performance & Scalability**

### **Expected Load**
- **Miners**: 100-500 active miners per epoch
- **Validators**: 10-50 active validators
- **API Requests**: ~10,000 requests per hour during peak
- **Data Volume**: 50-200GB per epoch (all miners combined)

### **Rate Limits**
- **Zipcode Assignment**: 10 requests/minute per hotkey
- **S3 Access**: 20 requests/day per miner
- **Status Updates**: 5 requests/minute per hotkey
- **System Stats**: 30 requests/minute (public)

### **Caching Strategy**
- **Zipcode assignments**: Cached for full epoch duration
- **System statistics**: Cached for 1 minute
- **S3 credentials**: Generated fresh, expire in 1 hour

---

## 🚨 **Error Handling & Monitoring**

### **Common Error Scenarios**
1. **API Server Unavailable**: Implement retry logic with exponential backoff
2. **Invalid Signatures**: Check timestamp and commitment format
3. **Rate Limit Exceeded**: Implement request queuing
4. **S3 Upload Failures**: Retry with different credentials
5. **Epoch Timing Issues**: Handle epoch transitions gracefully

### **Monitoring Requirements**
```python
# Health Check Integration
def monitor_api_health():
    """Continuously monitor API server health"""
    while True:
        try:
            health = requests.get(f"{API_BASE_URL}/healthcheck", timeout=10)
            if health.status_code != 200:
                logger.error(f"API health check failed: {health.status_code}")
                # Implement alerting logic
        except Exception as e:
            logger.error(f"API health check error: {e}")
        
        time.sleep(60)  # Check every minute

# Performance Metrics
METRICS_TO_TRACK = {
    'api_response_times': [],
    'successful_requests': 0,
    'failed_requests': 0,
    'data_upload_success_rate': 0.0,
    'average_mining_time': 0.0,
    'validation_scores': []
}
```

---

## 📋 **Integration Checklist**

### **For Miner Developers**
- [ ] Implement API client with signature authentication
- [ ] Add epoch detection and zipcode assignment request
- [ ] Modify scraping logic to target assigned zipcodes only
- [ ] Implement S3 data upload with proper formatting
- [ ] Add status update reporting throughout mining process
- [ ] Implement error handling and retry logic
- [ ] Add health monitoring and alerting
- [ ] Test with development API server
- [ ] Validate data format compliance

### **For Validator Developers**
- [ ] Implement API client for validator endpoints
- [ ] Add epoch completion monitoring
- [ ] Implement miner data download from S3
- [ ] Create data validation and scoring algorithms
- [ ] Add validator result upload to S3
- [ ] Integrate with Bittensor weight setting
- [ ] Implement honeypot detection logic
- [ ] Add comprehensive logging and monitoring
- [ ] Test validation accuracy and performance

### **For Both**
- [ ] Update configuration for production API endpoints
- [ ] Implement proper logging and error reporting
- [ ] Add performance monitoring and metrics
- [ ] Create deployment and update procedures
- [ ] Document integration and troubleshooting guides

---

## ❓ **Questions for Development Team**

### **Technical Implementation Questions**
1. **Bittensor Integration**: What is the current structure of the miner and validator codebases? Are they using the standard Bittensor template or custom implementations?
A: current validator was forked from SN13 data universe. It pings miners to request realestate properties and checks with data scraping to see if they are correct data, it also pings the data that miners upload to s3 to check for duplicates and spot checks some of that data with a data scraping engine. It then rewards the miners by setting weights for them. That process needs improvement and is why we're moving towards a system where miners are deternamistcially evaluated on "when they upload their data - how fast", telling them to all scrape the same zipcodes each period and then seeing who comes closest to the target number of listings, the fastest, and individually evaluating each zipcode.  We should reward the top 3 miners for each zipcode with 55%, 30%, 10% of rewards and spread 5% among all other miners. and provide 0% to any miners who lie with synthetic data. Since there are multiple zipcodes per batch the actual distribution each cycle will vary but it will be fixed per zipcode. in this way we also only have to evaluate 3 miners for each zipcode instead of all 250 per zipcode data submitted. Does that make sense?

2. **Signature Library**: Which cryptographic library is currently being used for Bittensor signature generation? (e.g., `@polkadot/keyring`, `bittensor` Python library, custom implementation)
bittensor - but possibly also keyring. Will have to check

3. **Data Storage**: How is scraped data currently stored locally before submission? Should we maintain compatibility with existing storage formats?
Yes pleas do not change the storage of data. It's being stored on the miners up to 250gb (which is configurable), but also being uploaded as a diff to S3.  Maybe we should change the diffs to upload per zipcode per diff.  Although they may already upload per zipcode - please check on this.

4. **Validation Logic**: What are the current criteria for scoring miners? Should we maintain existing scoring weights or implement the new 4-component system (quality, accuracy, completeness, timeliness)?

5. **Error Handling**: What is the current approach to handling network failures, API timeouts, and data corruption? Should we implement specific retry strategies?

### **Operational Questions**
6. **Deployment Strategy**: How are miner and validator updates currently deployed? Do we need to maintain backward compatibility during the transition?

7. **Configuration Management**: How are API endpoints, credentials, and other configuration parameters currently managed? Should we use environment variables, config files, or a different approach?

8. **Monitoring & Alerting**: What monitoring systems are currently in place? Should we integrate with existing monitoring or implement new health checks?

9. **Testing Strategy**: What testing environments are available? Do we need to create mock API endpoints for development and testing?

10. **Performance Requirements**: What are the expected performance characteristics? How many miners/validators need to be supported simultaneously?

### **Business Logic Questions**
11. **Scoring Algorithm**: Should the new validation scoring system completely replace the existing scoring, or should it be a gradual transition with weighted combinations?

12. **Honeypot Strategy**: What percentage of assignments should be honeypots? How should honeypot zipcodes be selected and validated?

13. **Data Retention**: How long should miner data and validator results be retained in S3? Are there compliance or cost considerations?

14. **Epoch Timing**: Is the 4-hour epoch duration acceptable, or should it be configurable? How should epoch transitions be handled if miners are mid-scrape?

15. **Failure Recovery**: How should the system handle partial failures (e.g., some miners complete, others fail)? Should there be minimum participation thresholds?

### **Integration Timeline Questions**
16. **Rollout Strategy**: Should this be a hard cutover or gradual migration? Can old and new systems run in parallel?

17. **Testing Phase**: How long should the testing phase be? What success criteria need to be met before full deployment?

18. **Validator Coordination**: How will validators coordinate the transition? Do they all need to upgrade simultaneously?

19. **Miner Communication**: How will miners be notified of the upgrade requirements? Is there a communication channel or documentation system?

20. **Rollback Plan**: What is the rollback strategy if critical issues are discovered after deployment?

---

## 📞 **Support & Resources**

### **API Documentation**
- **Swagger UI**: https://api.resilabs.com/docs
- **OpenAPI JSON**: https://api.resilabs.com/docs-json
- **Health Check**: https://api.resilabs.com/healthcheck

### **Development Resources**
- **GitHub Repository**: [Link to be provided]
- **Integration Examples**: Available in `/examples` directory
- **Test Scripts**: Available in `/test-scripts` directory

### **Contact Information**
- **API Support**: [Contact details]
- **Integration Support**: [Contact details]
- **Emergency Contact**: [Contact details]

---

*Document Version: 1.0*  
*Last Updated: October 1, 2025*  
*Status: Ready for Implementation* 🚀