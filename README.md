<div align="center">

# <img src="assets/resi-logo.png" alt="RESI Logo" width="23"> RESI - Real Estate Super Intelligence


</div>

<div align="center">

**Building the world's largest open real estate database through decentralized intelligence**

*Unlocking AI innovation by democratizing real estate data trapped in corporate silos*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Bittensor](https://img.shields.io/badge/Powered%20by-Bittensor-purple.svg)](https://bittensor.com)

[Subnet Overview](#overview) • [For Miners](#for-miners) • [For Validators](#for-validators)

</div>

---
# Overview

Subnet 46 (RESI) is a specialized real estate data collection network built by ResiLabs.ai. We're creating the world's largest open real estate database by adapting Subnet 13's proven decentralized data architecture for property-specific intelligence.

---
### Three-Repository Architecture

Our implementation consists of three specialized repositories:

1. **[resi](https://github.com/resi-labs-ai/resi)** *(this repo)* - **Core Logic**
   - Core miner and validator logic adapted for real estate data
   - Property-specific validation mechanisms
   - Real estate market-focused incentive structures

2. **[resi-labs-api](https://github.com/resi-labs-ai/resi-labs-api)** - **S3 API Server**: Handles authentication and AWS storage access

   - S3 authentication server for miners and validators
   - AWS access token distribution system
   - API endpoints for data access and validation

3. **[prospector](https://github.com/resi-labs-ai/prospector)** - **Prospector System**: JSON-based incentive weighting for geographic prioritization

   - JSON-based incentive weighting system (Real Estate Dynamic Desirability)
   - Geographic prioritization with 7,572+ US zipcode coverage
   - Zipcode-based market prioritization weighted by market size and value

---
### **For Miners:**
If you're a miner looking to contribute to our subnet, please refer to the [Miner Setup Guide](docs/miner.md) to get you started

- **[New Data Schema Requirements](docs/miner-realestate-data-structure.json)** - REQUIRED: Property data structure (on `miner-todo` branch)
- **[Complete Data Example](docs/example-complete-property-data.json)** - REQUIRED: Full schema example (on `miner-todo` branch)
- **✓ S3 Upload Configuration** - UNCHANGED: Same cloud storage authentication
- **Custom Scraper Development** - REQUIRED: Build your own data collection system

### **Required Actions**
1. **Build Custom Data Collection System**
   - Use ANY accessible data source (Zillow, Redfin, county records, MLS, public records, etc.)
   - Focus on properties sold in last 3 years (2022-2025)
   - Implement comprehensive property data schema

2. **Schema Compliance**
   - Required fields MUST be present for validation property matching
   - Follow structure in `docs/miner-realestate-data-structure.json`
   - See complete example: `docs/example-complete-property-data.json`

3. **Modify Existing Miner Code**
   - Keep S3 upload functionality intact
   - Replace data collection logic with your custom implementation
   - Maintain same authentication and storage processes

### **Evaluation Criteria**
- **Data Completeness**: Number of schema fields populated
- **Data Quality**: Accuracy verified when validators cross-check against Zillow
- **Submission Quantify**: Faster data collection rewarded
- **Comprehensive Coverage**: Priority on pulling data from everywhere - we're playing catchup across the entire country
- **Zipcode Coverage**: Miners will be requested to collect ALL sold listings for specific zipcodes
- **No Tolerance**: Synthetic data or duplicates result in penalties

---
### **For Validators:**
- **[Validator Guide](docs/validator.md)** - Full validation setup
- **[Proxy Configuration Guide](docs/PROXY_CONFIGURATION.md)** - **REQUIRED for Mainnet**: Proxy setup for reliable validation
- **Real Estate Data Validation** - Specialized property data verification
- **Cross-validation Logic** - Compare results with other validators
- **Performance Monitoring** - Track validation success rates and API usage

---
# Product Roadmap

ResiLabs will launch its own products built with subnet 46:

## Platform Applications To Be Built on RESI Data

### Seller Intent Prediction
*Our flagship AI application demonstrates the platform's potential*

By training machine learning models on our comprehensive dataset - including ownership patterns, financial indicators, life events, and market conditions - we can identify selling signals invisible to traditional approaches. This enables real estate investors to approach prospects with personalized, data-driven insights.

### Additional Applications Enabled by Open Data on RESI
- **Market Analysis Tools**: Investment opportunity scoring and trend analysis
- **CRM Enhancement**: Data enrichment for real estate professionals
- **Legal Services**: Due diligence tools for attorneys and title companies  
- **Financial Services**: Underwriting support for lenders and asset allocators

This showcases how open real estate data enables innovation impossible within corporate data silos.


## Competitive Advantage

Unlike existing solutions, RESI:

- **Removes barriers**: No enterprise sales process, documentation requirements, or $250K+ minimum commitments
- **Offers field-level precision** instead of expensive property-level data packages
- **Provides real-time updates** through distributed monitoring vs. quarterly batch processing
- **Enables AI training** on comprehensive datasets previously locked behind corporate walls
- **Rewards data discovery** through specialized mining vs. maintenance-only models
- **Scales intelligently** with field-level confidence and temporal decay algorithms


## Roadmap

### Phase 1: Data Foundation - API Launch
- **National property database**: 150M+ US residential properties with core attributes
- **Multi-source aggregation**: Platform enables miners to collect from any accessible data source
- **Developer evaluation**: Limited preview access through web interface

### Phase 2: Platform Applications - Predict dot Casa Launch (v2)
- **Flagship AI products**: Launch seller intent prediction, market analysis tools, Agent enabled CRM.
- **API ecosystem**: Enable third-party developers to build on RESI data
- **Compute-to-data services**: Train models without accessing raw datasets
- **Customer revenue**: Transition from TAO emissions to sustainable business model
- **MCP Integration**: Integrate subnet 46, Resi Labs, directly into Claude and Cursor via our MCP

### Phase 3: Global Expansion
- **Commercial property expansion**: Office, retail, and industrial property data
- **International markets**: Global property data collection networks
- **Enterprise partnerships**: White-label solutions for large organizations
- **Training marketplace**: Miners offer specialized AI training services using RESI data

---
## Resi Labs Dashboard

As you can see above, Resi Labs rewards diversity of data (storing 200 copies of the same data isn't exactly beneficial!)

To help understand the current data on the Subnet, the Resi Labs team plans to host a dashboard [(Coming Soon)](https://sn46-dashboard.ResiLabs.ai/), showing the amount of each type of data (by DataEntityBucketId) on the Subnet. Miners will be strongly encouraged to use this dashboard to customize their [Miner Configuration](./docs/miner.md#configuring-the-miner), to maximize their rewards.

---
# Terminology

**DataEntity:** A single "item" of data collected by a Miner. Each DataEntity has a URI, that the Validators can use to retrieve the item from its DataSource.

**DataEntityBucket:** A logical grouping of DataEntities, based on its DataEntityBucketId.

**DataEntityBucketId:** The unique identifier for a DataEntityBucket. It contains the TimeBucket, DataSource, and DataLabel.

**DataLabel:** A label associated with a DataEntity. Precisely what the label represents is unique to the DataSource. For example, for a Yahoo finance DataSource, the label is the stock ticker of the finance data.

**DataSource:** A source from which Miners scrape data.

**Miner Credibility**: A per-miner rating, based on how often they pass data validation checks. Used to heavily penalize Miner's who misrepresent their MinerIndex.

**Miner Index**: A summary of how much and what types of data a Miner has. Specifically, it's a list of DataEntityBuckets.

---
## Attribution & Technical Foundation

**Subnet 46 (RESI) is built upon the proven architecture of [Subnet 13: Data Universe](https://github.com/macrocosm-os/data-universe) by Macrocosmos.com.**

We extend our sincere gratitude to the Macrocosmos team, particularly [Arrmlet](https://github.com/Arrmlet) and [ewekazoo](https://github.com/ewekazoo), for creating the robust, scalable data collection and validation framework that serves as our foundation. Their pioneering work on decentralized data collection, consensus mechanisms, and anti-gaming protections has enabled us to focus on real estate specialization rather than rebuilding core infrastructure.

---
### **Legal Disclaimer:**
For those that may be concerned with the practice of scraping data please be assured that we have consulted with our legal team regarding the validity of this practice. The standing case law points to scraping of openly accessible data on the internet as **LEGAL**. In the event of manipulating logins or paywalls, this is where liability is a cause for concern. 

The landmark [hiQ Labs v. LinkedIn](https://en.wikipedia.org/wiki/HiQ_Labs_v._LinkedIn) case (2019) established that scraping publicly available data is legal under U.S. law. While scraping may violate Terms of Service and result in IP blocking, it cannot result in legal action against users for collecting public information not behind paywalls or login requirements.

---
## Contact and Support
Feel free to reach out for any questions or support in the [RESI Subnet Channel](https://discord.com/channels/799672011265015819/1397618038894759956) in the Official Bittensor Discord Server.  Find us on [X/Twitter](https://x.com/resilabsai)
