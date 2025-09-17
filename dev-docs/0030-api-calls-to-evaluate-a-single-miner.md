# API Calls Used to Evaluate a Single Miner

## Summary

**Yes, your understanding is correct!** The current implementation uses **10 API calls total per miner evaluation**:
- **5 API calls** for regular neuron validation (from miner's local storage)
- **5 API calls** for S3 validation (from miner's S3 uploads)

## Detailed Breakdown

### 1. Regular Miner Validation: 5 API Calls

**Location**: `vali_utils/utils.py` line 53
```python
num_entities_to_choose = min(5, len(entities))
```

**Process**:
1. Validator requests miner's index
2. Chooses a random DataEntityBucket from the miner
3. Gets that bucket containing property listings from the miner
4. **Samples 5 random entities** from the bucket
5. Validates each entity against Zillow via RapidAPI (5 API calls)

### 2. S3 Validation: 5 API Calls

**Location**: `vali_utils/s3_utils.py` line 381
```python
entities_to_validate = random.sample(all_entities, min(5, len(all_entities)))
```

**Process**:
1. Accesses miner's S3 data via auth service
2. Analyzes recent data (last 3 hours)
3. **Samples 5 random entities** from S3 files
4. Validates each entity using real scrapers (5 API calls)
5. Checks for duplicates and data quality

## Historical Context

### Previous Configuration (Before Dec 16, 2024)
- **Regular validation**: 2 samples/miner/hour
- **S3 validation**: 10 samples/miner/hour  
- **Organic queries**: 10 samples for cross-validation
- **Total**: ~22 API calls/miner/hour

### Current Optimized Configuration
- **Regular validation**: 5 samples/miner/evaluation
- **S3 validation**: 5 samples/miner/evaluation
- **Organic queries**: 5 samples for cross-validation
- **Total**: ~10 API calls/miner/evaluation

## Evaluation Frequency

- **Evaluation Period**: Every 4 hours per miner (240 minutes)
- **S3 Validation**: Every ~8.5 hours (2550 blocks)
- **Batch Size**: 15 miners evaluated simultaneously

## API Cost Optimization

The changes reduced API usage by **90%+**:
- **Before**: 2.16M calls/month per validator
- **After**: ~198k calls/month per validator
- **Cost reduction**: From $500+/month to $50-100/month per validator

## Code References

### Main Evaluation Flow
- `vali_utils/miner_evaluator.py:89` - Main eval_miner function
- `vali_utils/miner_evaluator.py:237-250` - Regular validation with 5 samples
- `vali_utils/miner_evaluator.py:287-290` - S3 validation trigger

### Sample Size Configuration
- `vali_utils/utils.py:53` - Regular validation: 5 samples
- `vali_utils/s3_utils.py:381` - S3 validation: 5 samples  
- `vali_utils/organic_query_processor.py:35` - Cross-validation: 5 samples

### Validation Documentation
- `dev-docs/0019-validator-sampling-vs-api-cost.md` - Detailed optimization analysis
