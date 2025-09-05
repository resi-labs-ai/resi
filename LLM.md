# LLM.md

This file provides guidance to LLM agents when working with code in this repository.

## Project Overview

RESI (Real Estate Super Intelligence) is Bittensor Subnet 46 for real estate data scraping and analysis. Built upon the proven architecture of Subnet 13 (Data Universe), it collects real-time property data primarily from Zillow via RapidAPI and stores it in a distributed network of miners. Validators query miners and score them based on data quality, freshness, and diversity to build the world's largest open real estate database.

### Core Architecture

**Miners** (`neurons/miner.py`):
- Scrape real estate data from Zillow via RapidAPI using the scraping system
- Store property data locally in SQLite databases via `SqliteMinerStorage`
- Upload data to S3 for public access
- Serve data to validators through protocol requests

**Validators** (`neurons/validator.py`):
- Query miners for their data indexes
- Verify data quality and authenticity
- Score miners based on data value, freshness, and credibility
- Maintain a complete view of network data distribution

**Data Model** (`common/data.py`):
- `DataEntity`: Individual pieces of scraped data (property listings, assessor records, etc.)
- `DataEntityBucket`: Logical grouping by source, time, and label
- `DataEntityBucketId`: Unique identifier (DataSource + TimeBucket + DataLabel)
- `CompressedMinerIndex`: Summary of miner's data for efficient querying

**Protocol** (`common/protocol.py`):
- `GetMinerIndex`: Retrieve miner's data summary
- `GetDataEntityBucket`: Fetch specific data buckets
- `OnDemandRequest`: Custom scraping requests from validators

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Running Nodes
```bash
# Run miner
python neurons/miner.py --netuid 46 --subtensor.network <network> --wallet.name <wallet> --wallet.hotkey <hotkey>

# Run validator  
python neurons/validator.py --netuid 46 --subtensor.network <network> --wallet.name <wallet> --wallet.hotkey <hotkey>
```

### Testing
```bash
# Run all tests (note: currently has module import issues)
python tests/test_all.py

# Run specific test files
python -m pytest tests/common/test_protocol.py
python -m pytest tests/scraping/test_coordinator.py
python -m pytest tests/storage/miner/test_sqlite_miner_storage.py
```

## Key Directories

- `neurons/`: Main miner and validator implementations
- `common/`: Shared data models, protocol definitions, and utilities
- `scraping/`: Data scraping system with source-specific scrapers
- `storage/`: Storage abstractions for miners and validators
- `rewards/`: Scoring and reward calculation logic
- `upload_utils/`: HuggingFace and S3 uploading functionality
- `vali_utils/`: Validator-specific utilities and APIs
- `dynamic_desirability/`: Dynamic data valuation system
- `tests/`: Unit and integration tests

## Scraping System

The scraping system is modular and configurable for real estate data collection:

- `ScraperCoordinator` (`scraping/coordinator.py`): Orchestrates multiple scrapers
- `ScraperProvider` (`scraping/provider.py`): Factory for creating scrapers
- Source-specific scrapers in `scraping/zillow/` for RapidAPI Zillow data collection
- Configuration via JSON files in `scraping/config/` for property data sources
- Primary data source: Zillow via RapidAPI for comprehensive property information

## Storage Systems

**Miner Storage**:
- `MinerStorage` interface (`storage/miner/miner_storage.py`)
- SQLite implementation (`storage/miner/sqlite_miner_storage.py`)

**Validator Storage**:
- Memory-based storage for miner indexes
- S3 integration for large-scale property data access

## Data Upload and Access

**S3 Storage (Primary)**:
- Partitioned storage by miner hotkey for property data
- Efficient validator access to all miner property datasets
- Blockchain-based authentication

## Configuration

- Miner configuration via command-line args and scraping config JSON for property data sources
- Validator configuration for scoring, timeouts, and property data validation
- Dynamic desirability updates for real estate market trends
- RapidAPI key configuration required for Zillow data access

## Important Notes

- Property data older than 30 days is not scored
- Miners are rewarded based on property data value, freshness, and diversity
- All property data is anonymized before public upload
- The system supports both organic (validator-initiated) and on-demand property scraping
- Primary focus on US residential properties with plans for commercial and international expansion