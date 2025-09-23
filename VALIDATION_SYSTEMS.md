# Enhanced Validation Systems

This document describes the two validation approaches implemented for coordinated data distribution and validation in the RESI subnet.

## Overview

The system provides two validation strategies:

1. **Consensus-Based Validation** (Default) - Uses statistical consensus between miners without requiring validators to scrape data
2. **API-Based Validation** (Optional) - Uses traditional validator scraping for verification when needed

## System Architecture

### Core Components

- **DataAssignmentRequest Protocol** - New protocol for coordinated data assignments
- **ValidatorDataAPI** - Client for pulling coordinated data blocks from API
- **PropertyConsensusEngine** - Statistical consensus validation system
- **APIBasedValidator** - Traditional validator scraping system
- **EnhancedMinerEvaluator** - Integrates both validation approaches

### Configuration

The system is configured via environment variables and the `ValidationConfig` class:

```python
from config.validation_config import ValidationConfig, CONSENSUS_ONLY_CONFIG

# Use consensus-only validation (default)
config = CONSENSUS_ONLY_CONFIG

# Or enable API validation
config.enable_validator_spot_checks = True
```

## Consensus-Based Validation (Recommended)

### How It Works

1. **Data Distribution**: Validators pull random property blocks from API every 4 hours
2. **Assignment Creation**: Properties assigned to groups of 5 miners with cold key diversity
3. **Miner Scraping**: Miners scrape assigned properties and return data
4. **Statistical Consensus**: Validators compare responses using credibility-weighted voting
5. **Behavioral Analysis**: Detect synchronized submissions and identical responses
6. **Credibility Updates**: Update miner credibility based on consensus agreement

### Benefits

- ✅ **No Validator Scraping Required** - Eliminates need for validators to regularly scrape data
- ✅ **Scales Efficiently** - Statistical consensus scales better than individual validation
- ✅ **Anti-Gaming Protection** - Multiple layers of behavioral analysis and diversity requirements
- ✅ **Cost Effective** - No API costs for validators
- ✅ **Real-Time Data** - Miners provide live scraping with timestamp validation

### Configuration

```bash
# Enable consensus-only validation
export ENABLE_VALIDATOR_SPOT_CHECKS=false
export CONSENSUS_CONFIDENCE_THRESHOLD=0.6
export ANOMALY_DETECTION_THRESHOLD=0.3
export MINERS_PER_PROPERTY=5
```

### Example Usage

```python
from vali_utils.consensus_validator import PropertyConsensusEngine
from config.validation_config import CONSENSUS_ONLY_CONFIG

# Initialize consensus engine
engine = PropertyConsensusEngine(
    config=CONSENSUS_ONLY_CONFIG,
    wallet=wallet,
    metagraph=metagraph,
    scorer=scorer,
    scraper_provider=scraper_provider
)

# Process assignment responses
results = await engine.process_assignment_responses(assignment_id, responses)
```

## API-Based Validation (Optional)

### How It Works

1. **Data Distribution**: Same as consensus system
2. **Miner Scraping**: Miners scrape assigned properties
3. **Validator Verification**: Validators scrape same properties using APIs
4. **Field Comparison**: Compare miner data vs validator data field-by-field
5. **Credibility Updates**: Update based on validation success/failure

### Benefits

- ✅ **High Accuracy** - Direct validation against source APIs
- ✅ **Proven Approach** - Traditional Bittensor validation method
- ✅ **Immediate Feedback** - Clear validation results per property
- ❌ **Higher Costs** - Requires API access for validators
- ❌ **Scaling Concerns** - Each validator must scrape data

### Configuration

```bash
# Enable API-based validation
export ENABLE_VALIDATOR_SPOT_CHECKS=true
export CONSENSUS_CONFIDENCE_THRESHOLD=0.8
export ANOMALY_DETECTION_THRESHOLD=0.2
```

### Example Usage

```python
from vali_utils.api_validator import APIBasedValidator
from config.validation_config import API_VALIDATION_CONFIG

# Initialize API validator
validator = APIBasedValidator(
    config=API_VALIDATION_CONFIG,
    wallet=wallet,
    metagraph=metagraph,
    scorer=scorer,
    scraper_provider=scraper_provider
)

# Process assignment responses
results = await validator.process_assignment_responses(assignment_id, responses)
```

## Data Assignment Protocol

### Request Structure

```python
class DataAssignmentRequest(bt.Synapse):
    request_id: str                              # Unique assignment ID
    assignment_data: Dict[str, List[str]]        # Property IDs by source
    expires_at: Optional[str]                    # Assignment expiry
    expected_completion: Optional[str]           # When results are due
    
    # Response fields (populated by miner)
    submission_timestamp: Optional[str]          # When submitted
    scrape_timestamp: Optional[str]              # When scraping started
    completion_status: str                       # "pending", "completed", "failed"
    scraped_data: Dict[str, List[DataEntity]]    # Scraped data by source
    assignment_stats: Optional[Dict[str, any]]   # Execution statistics
```

### Example Assignment

```json
{
    "request_id": "assignment_20250115_block_001",
    "assignment_data": {
        "ZILLOW": ["12345", "67890", "11111"],
        "REDFIN": ["abc123", "def456"],
        "REALTOR_COM": ["123 Main St, Austin TX"],
        "HOMES_COM": ["789 Pine St, Houston TX"]
    },
    "expires_at": "2025-01-15T14:00:00Z",
    "expected_completion": "2025-01-15T12:00:00Z"
}
```

## Miner Implementation

### Data Assignment Handler

Miners now handle `DataAssignmentRequest` in addition to existing protocols:

```python
async def handle_data_assignment(self, synapse: DataAssignmentRequest) -> DataAssignmentRequest:
    """Handle coordinated data assignment requests from validators"""
    
    # Record start time
    start_time = dt.datetime.now(dt.timezone.utc)
    synapse.scrape_timestamp = start_time.isoformat()
    
    # Process each source
    for source, property_ids in synapse.assignment_data.items():
        scraped_entities = await self._scrape_property_batch(source_enum, property_ids)
        synapse.scraped_data[source] = scraped_entities
    
    # Record completion
    synapse.submission_timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    synapse.completion_status = "completed"
    
    return synapse
```

## Validator Integration

### Enhanced Miner Evaluator

The `EnhancedMinerEvaluator` integrates both validation systems:

```python
from vali_utils.enhanced_miner_evaluator import EnhancedMinerEvaluator

# Initialize enhanced evaluator
evaluator = EnhancedMinerEvaluator(config, uid, metagraph_syncer, s3_reader)

# Run coordinated evaluation cycle
results = await evaluator.run_coordinated_evaluation_cycle()
```

### Backward Compatibility

The enhanced system maintains full backward compatibility:
- All existing protocols (`GetMinerIndex`, `GetDataEntityBucket`, `OnDemandRequest`) continue to work
- Existing validator logic remains functional
- Gradual rollout possible - some validators can use new system while others use current

## Configuration Options

### Environment Variables

```bash
# Core Configuration
DATA_API_URL=https://api.resi-subnet.com
ENABLE_VALIDATOR_SPOT_CHECKS=false

# Consensus Parameters
CONSENSUS_CONFIDENCE_THRESHOLD=0.6
ANOMALY_DETECTION_THRESHOLD=0.3
MINERS_PER_PROPERTY=5

# Assignment Parameters
ASSIGNMENT_TIMEOUT_HOURS=2
MAX_PROPERTIES_PER_ASSIGNMENT=50
ENABLED_DATA_SOURCES=zillow,redfin,realtor,homes
BLOCK_SIZE_PER_SOURCE=1000

# Time-Based Rewards
ENABLE_TIME_BASED_REWARDS=true
FAST_RESPONSE_BONUS=1.5
MEDIUM_RESPONSE_BONUS=1.2
SLOW_RESPONSE_PENALTY=0.8

# Behavioral Analysis
ENABLE_BEHAVIORAL_ANALYSIS=true
SYNC_THRESHOLD_SECONDS=30
IDENTICAL_CONTENT_PENALTY=0.5
```

### Predefined Configurations

```python
# Consensus-only (recommended for production)
from config.validation_config import CONSENSUS_ONLY_CONFIG

# API validation (higher accuracy, higher cost)
from config.validation_config import API_VALIDATION_CONFIG

# Development testing
from config.validation_config import DEVELOPMENT_CONFIG
```

## Testing

### Test Script

```bash
# Test consensus validation
python scripts/test_validation_systems.py --config consensus

# Test API validation
python scripts/test_validation_systems.py --config api --enable-spot-checks

# Development testing
python scripts/test_validation_systems.py --config development
```

### Manual Testing

```python
from scripts.test_validation_systems import ValidationSystemTester
from config.validation_config import CONSENSUS_ONLY_CONFIG

# Create tester
tester = ValidationSystemTester(CONSENSUS_ONLY_CONFIG)

# Run tests
results = await tester.run_all_tests()
```

## Monitoring and Statistics

### Validation Statistics

Both systems provide comprehensive statistics:

```python
# Get statistics
stats = evaluator.get_statistics()

print(f"Validation mode: {stats['validation_mode']}")
print(f"Assignments completed: {stats['assignments_completed']}")
print(f"Properties validated: {stats['total_properties_validated']}")

# API validator specific stats
if stats['api_validator_stats']:
    api_stats = stats['api_validator_stats']
    print(f"API success rate: {api_stats['success_rate']:.2%}")
    print(f"API errors: {api_stats['api_errors']}")
```

### Logging

Enable detailed logging for debugging:

```bash
export ENABLE_DETAILED_LOGGING=true
export LOG_VALIDATION_DETAILS=true
```

## Migration Guide

### From Current System

1. **Phase 1**: Deploy new code with consensus validation disabled
2. **Phase 2**: Enable consensus validation for subset of validators
3. **Phase 3**: Gradually migrate all validators to consensus system
4. **Phase 4**: Optionally enable API validation for high-value properties

### Configuration Migration

```python
# Current system continues to work
# Add new configuration gradually

# Start with consensus disabled
config = ValidationConfig(enable_validator_spot_checks=False)

# Enable consensus when ready
config.validation_mode = 'consensus'
```

## Troubleshooting

### Common Issues

1. **No API Endpoint**: Set `DATA_API_URL` to valid endpoint
2. **Insufficient Miners**: Ensure at least 5 miners available for consensus
3. **High Anomaly Rate**: Tune `ANOMALY_DETECTION_THRESHOLD`
4. **Low Consensus**: Adjust `CONSENSUS_CONFIDENCE_THRESHOLD`

### Debug Mode

```bash
export ENABLE_DETAILED_LOGGING=true
export LOG_VALIDATION_DETAILS=true

# Run with debug logging
python scripts/test_validation_systems.py --config development
```

## Performance Characteristics

### Consensus-Based Validation

- **Validator Load**: Low (no scraping required)
- **Network Traffic**: Medium (coordinate assignments)
- **API Costs**: None for validators
- **Scalability**: High (statistical consensus)
- **Accuracy**: High with sufficient miners

### API-Based Validation

- **Validator Load**: High (scraping required)
- **Network Traffic**: High (individual validation)
- **API Costs**: High (per property validation)
- **Scalability**: Medium (limited by API rates)
- **Accuracy**: Very High (direct verification)

## Conclusion

The consensus-based validation system provides an efficient, scalable approach to data validation without requiring validators to scrape data themselves. The API-based validation system remains available as an option for scenarios requiring maximum accuracy at higher cost.

Both systems integrate seamlessly with existing infrastructure and provide comprehensive anti-gaming protections through behavioral analysis, diversity requirements, and credibility-weighted consensus mechanisms.
