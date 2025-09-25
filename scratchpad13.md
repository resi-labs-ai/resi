🚨 **SUBNET 46 EVOLUTION - Major Update Coming Next Week**

**Upcoming Updates**
✅ **New Data Schema**: Comprehensive property data structure focused on sold properties from last 3 years  
✅ **Open Data Collection**: Miners build custom scrapers using ANY data source  
✅ **Validator Optimization**: New validation system reduces operational costs  
✅ **Competition-Based Mining**: Rewards innovation in data collection methods  

**Breaking Changes**
⚠️ **Custom Scraper Required**: Pre-built miner code will NOT work by default - build your own data collection  
⚠️ **Schema Compliance Mandatory**: All submissions must match new property data structure  
⚠️ **No Grace Period**: Changes effective next week (target Monday)  
⚠️ **Zero Tolerance**: No synthetic data or duplicates - quality and speed matter  

**Todo's for Miners for Upcoming Update**
**Build Custom Data Collection**: Create scraper using ANY source (Zillow, county records, MLS, public records, etc.)  
**Implement Required Schema**: Follow comprehensive property data structure - some fields REQUIRED for validation matching  
**Target Sold Properties**: Focus on properties sold in last 3 years (2022-2025) for price trend oracle  
**Modify Existing Miner**: Keep S3 upload functionality, replace data collection logic  
**Optimize for Speed**: Evaluation based on data completeness, quality, AND submission speed  
**Prepare for Zipcode Requests**: Validators will request ALL sold listings for specific zipcodes  

**Schema Documentation**: 
- **Structure**: `docs/miner-realestate-data-structure.json` 
- **Complete Example**: `docs/example-complete-property-data.json`
- **Branch**: `miner-todo` on GitHub

**Important Notes:**
- Validators will cross-check against Zillow for verification
- Required fields must be present for property matching
- Miners can modify base miner code but it won't work as-is
- Community support available in Bittensor chats - no official scraper support provided
- Incentives will gradually increase requirements over time
