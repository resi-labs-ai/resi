# RESI - Real Estate Super Intelligence

<div align="center">

**Building the world's largest open real estate database through decentralized intelligence**

*Unlocking AI innovation by democratizing real estate data trapped in corporate silos*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Bittensor](https://img.shields.io/badge/Powered%20by-Bittensor-purple.svg)](https://bittensor.com)

[S3 Testing](#-immediate-action-s3-connectivity-test-required-for-all-validators--miners) • [Get Started](#get-started) • [Documentation](#documentation) • [Three-Repo Architecture](#three-repository-architecture)

</div>

---

# 🚨 DEVELOPMENT STATUS

> **⚠️ ACTIVE DEVELOPMENT IN PROGRESS ⚠️**
> 
> **We have successfully forked Subnet 13's proven architecture and are adapting it for real estate data collection.**
>
> **✅ COMPLETED:**
> - ✅ **S3 API Server** - Authentication system for validators and miners to access AWS S3 storage
> - ✅ **Prospector System** - JSON-based incentive weighting that prioritizes larger metro areas
> - ✅ **Core Architecture** - Forked and adapted Subnet 13's data collection framework
>
> **🔧 IN PROGRESS:**
> - 🔧 **Miner & Validator Code** - Adapting core mining and validation logic for real estate data
> - 🔧 **RapidAPI Zillow Integration** - Primary data source implementation
>
> **📋 ACTION REQUIRED FOR VALIDATORS/MINERS:**
> Please test your S3 connectivity using our quick start guide (takes <2 minutes):
> - **Testing Guide:** [MINER_VALIDATOR_TESTING_GUIDE.md](https://github.com/resi-labs-ai/resi-labs-api/blob/main/MINER_VALIDATOR_TESTING_GUIDE.md)
> - **Test Script:** [test_mainnet_s3_auth.py](https://github.com/resi-labs-ai/resi-labs-api/blob/main/api-test/test_mainnet_s3_auth.py)
>
> This verification ensures you can receive AWS S3 access tokens once the full system launches.

---

## Attribution & Technical Foundation

**Subnet 46 (RESI) is built upon the proven architecture of [Subnet 13: Data Universe](https://github.com/macrocosm-os/data-universe) by Macrocosmos.com.**

We extend our sincere gratitude to the Macrocosmos team, particularly [Arrmlet](https://github.com/Arrmlet) and [ewekazoo](https://github.com/ewekazoo), for creating the robust, scalable data collection and validation framework that serves as our foundation. Their pioneering work on decentralized data collection, consensus mechanisms, and anti-gaming protections has enabled us to focus on real estate specialization rather than rebuilding core infrastructure.

### Three-Repository Architecture

Our implementation consists of three specialized repositories:

1. **[resi](https://github.com/resi-labs-ai/resi)** *(This repo)*
   - Core miner and validator logic adapted for real estate data
   - Property-specific validation mechanisms
   - Real estate market-focused incentive structures

2. **[resi-labs-api](https://github.com/resi-labs-ai/resi-labs-api)**
   - S3 authentication server for miners and validators
   - AWS access token distribution system
   - API endpoints for data access and validation

3. **[prospector](https://github.com/resi-labs-ai/prospector)**
   - JSON-based incentive weighting system (Real Estate Dynamic Desirability)
   - Geographic prioritization with 7,572+ US zipcode coverage
   - Zipcode-based market prioritization weighted by market size and value

**Key adaptations for real estate:**
- Specialized data sources (Zillow, county assessors, MLS feeds, public records)
- Geographic incentive weighting through Prospector system
- Property-specific validation mechanisms
- Zipcode-based market prioritization for maximum market impact

---

## The Problem: Price Barriers, Data Fragmentation, and Restrictive Terms Lock Out Innovation

Real estate data is the lifeblood of a $45 trillion industry, yet it's trapped behind three critical barriers:

**1. Prohibitive Pricing**: Base-level access to comprehensive real estate databases come with unjustifiable costs to the tune of $250K+ per year per customer.

**2. Data Fragmentation**: Critical property information is scattered across thousands of county assessors, MLS systems, and tens of proprietary databases, requiring separate expensive contracts for each source.

**3. Restrictive Terms**: Data providers use licensing terms that prevent AI companies like ChatGPT, Claude, and Grok from training on this data, protecting monopolistic moats while stifling innovation.

The result? Small businesses, researchers, and developers are completely priced out, while even well-funded AI companies can't access the data needed to build transformative real estate intelligence applications.

## Our Solution: Open Source, Real-Time, Decentralized Intelligence

**RESI creates the first open, real-time, national real estate database powered by decentralized intelligence.**

*The Thesis: By creating an ecosystem that continuously learns from miner scraping, user data inputs, and behavior, products on RESI will ultimately build collective real estate super intelligence that drastically outperforms all closed systems.*

We're opening Pandora's box on real estate data by enabling miners to collect from any accessible source - Zillow, county assessors, thousands of public records, and even consumer behavior - then making it accessible through modern APIs with field-level confidence tracking and temporal decay algorithms.

This creates a **real-time national database** that serves as the foundational infrastructure for highly profitable and scalable real estate solutions across all sectors. Unlike corporate data silos that price out innovation, our decentralized approach enables AI applications impossible for any single company to build.

**The Vision**: Start with 150M+ properties in the USA, then scale globally to create the world's most comprehensive open real estate intelligence network that powers the next generation of PropTech innovation.

---

# MUST READ: Miner Data Compliance Policy

By participating as a miner on Subnet 46, you are agreeing to adhere to our [Miner Policy](docs/miner_policy.md) below. 
<details>
  <summary>
    ResiLabs Miner Data Compliance Policy
  </summary>

---

*Version 1.0, March 2025*

---

## Introduction
As a miner on ResiLabs Subnets, you play a crucial role in handling various types of data. This summary outlines your potential obligations under the UK General Data Protection Regulation (UK GDPR) should you inadvertently collect personal data, and the expectations regarding prohibited content and acceptable use of ResiLabs subnet code.
We expect any participant (however they may define themselves or their involvement) in our subnet ecosystems to adhere to the guidelines set out in this policy. Deliberate and consistent violation of these guidelines may result in ResiLabs seeking to limit your ability to participate, support for your participation and/or your incentive rewards.
Miners and all other participants are responsible for their own legal and regulatory compliance procedures and are encouraged to seek advice if in any doubt as to how to proceed. ResiLabs is available to provide informal guidance if required (see contact information below).

## 1. Your Responsibilities Under UK GDPR
While ResiLabs does not directly collect or process data, and seeks to avoid incentivising any collection or interaction with personal data, as a miner, you may be subject to GDPR obligations if your activities result in the inadvertent or accidental collection of personal data. We recommend that you put in place appropriate policies and procedures to accommodate this eventuality and set out below a summary of key responsibilities:
1. Lawful Basis for Processing
    - You must ensure there is a lawful basis for collecting and processing any personal data (e.g., consent, legitimate interests, or legal obligation).
2. Transparency
    - Inform individuals about how their data is being collected, processed, and stored.
    - Provide clear privacy information, including the purpose and lawful basis for processing.
3. Data Minimization
    - Only collect and process data that is strictly necessary for your stated purpose.
    - Avoid collecting sensitive personal data unless absolutely required and lawful.
4. Upholding Individuals' Rights
    - Be prepared to handle requests or objections from individuals regarding their right to access, rectify, limit processing of or delete their personal data in compliance with GDPR.
5. Data Security
    - Implement robust security measures to protect any data you collect from unauthorized access or breaches.
    - Ensure encryption and secure storage practices are in place.
6. Breach Reporting
    - Notify the appropriate data protection authority (e.g., ICO) within 72 hours of becoming aware of a personal data breach.

## 2. Prohibited Content
As a miner, you are strictly prohibited from collecting, processing, or transmitting the following types of content:
1. Illegal Content
    - Child abuse material or exploitation.
    - Hate speech, extremist propaganda, or content inciting violence.
    - Content related to human trafficking or modern slavery.
2. Copyrighted Material
    - Content protected by copyright unless you have explicit permission or a valid license to use it.
3. Explicit or Harmful Content
    - Pornographic or explicit imagery.
    - Content promoting self-harm, suicide, or drug abuse.

3. Acceptable Use Expectations
ResiLabs expects all miners to:
Comply with platform-specific terms of service and relevant laws, including GDPR.
Use ResiLabs subnets for ethical and lawful purposes only.
Regularly review and update your data collection and processing practices to ensure compliance with legal and ethical standards.
Immediately cease processing any flagged or prohibited material and report concerns to the appropriate authorities where required.

4. Commitment to Support
ResiLabs is committed to supporting miners in understanding and meeting their GDPR obligations. To help you navigate these requirements and ensure compliance, we provide the following guidance and resources:

## **GDPR Guidance and Resources**
1. Overview of GDPR Requirements
    - The UK Information Commissioner's Office (ICO) provides a comprehensive guide to GDPR obligations, including lawful bases for processing, data minimization, and security requirements:
    - [ICO Guide to GDPR](https://ico.org.uk/media/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr-1-1.pdf)
2. Lawful Basis for Processing Data
    - Understand the six lawful bases for processing personal data as defined under GDPR:
    - [ICO Lawful Basis Guide](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/a-guide-to-lawful-basis/)
3. Transparency and Privacy Notices
    - Guidance on providing clear and accessible privacy notices to individuals:
    - [ICO Privacy Notice Checklist](https://ico.org.uk/media/for-organisations/documents/1625126/privacy-notice-checklist.pdf)
4. Handling Data Subject Rights
    - Information on responding to requests from individuals to access, rectify, or delete their personal data:
    - [ICO Individual Rights Guide](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/)
5. Data Security and Minimization
    - Best practices for securing personal data and ensuring data minimization:
    - [ICO Security Guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/security/a-guide-to-data-security/)
6. Reporting Data Breaches
    - Guidance on recognizing and reporting data breaches to the ICO within the required 72-hour window:
    - [ICO Guide to Data Breach Reporting](https://ico.org.uk/for-organisations/report-a-breach/personal-data-breach/personal-data-breaches-a-guide/)

## **General Resources**
1. UK GDPR Key Definitions
    - A quick reference guide to key GDPR definitions and principles:
    - [ICO Key Definitions](https://ico.org.uk/for-organisations/guide-to-eidas/key-definitions/)
2. Data Protection Impact Assessments (DPIAs)
    - Information on when and how to conduct a DPIA for high-risk data processing activities:
    - [ICO DPIA Guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/)
3. FAQs on GDPR Compliance
    - Practical answers to common GDPR compliance questions:
    - [GDPR FAQs from the European Data Protection Board](https://edpb.europa.eu/our-work-tools/our-documents/faqs_en)

## **Support from ResiLabs**
1. Regular Updates and Communication
    - ResiLabs will provide updates on GDPR-related requirements and best practices through periodic communications.
2. Consultation Support
    - If miners have specific questions or require clarification on GDPR obligations, ResiLabs offers a support channel to address these concerns: compliance@ResiLabs.ai
3. Training Materials
    - ResiLabs may share training materials and resources from time to time to help miners enhance their understanding of GDPR compliance.

</details>

# Introduction

Subnet 46 (RESI) is a specialized real estate data collection network built by ResiLabs.ai. We're creating the world's largest open real estate database by adapting Subnet 13's proven decentralized data architecture for property-specific intelligence.

## Current Development Status
- ✅ **S3 API Infrastructure** - Fully operational authentication and storage system
- ✅ **Prospector Incentive System** - Geographic prioritization with 7,572+ US zipcode coverage
- 🔧 **Core Mining/Validation Logic** - In active development (adapted from Subnet 13)
- 🔧 **Zillow RapidAPI Integration** - Primary data source implementation underway

## Architecture Overview
RESI operates through a **three-repository system**:
- **Core Logic** (this repo): Miners and validators adapted for real estate data
- **S3 API Server**: Handles authentication and AWS storage access
- **Prospector System**: JSON-based incentive weighting for geographic prioritization

## Scale & Vision
At launch, RESI will support **150+ Million US properties** across 200+ miners, requiring only ~10GB validator storage. The decentralized architecture ensures no single entity controls the data - it's distributed across miners and queryable through validators, creating the foundation for a truly open real estate intelligence network.

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

# Overview

The Resi Labs documentation assumes you are familiar with basic Bittensor concepts: Miners, Validators, and incentives. If you need a primer, please check out https://docs.bittensor.com/learn/bittensor-building-blocks.

In the Resi Labs, Miners scrape data from a defined set of sources, called DataSources. Each piece of data (e.g. a webpage, BTC prices), called a DataEntity, is stored in the miner's database. Each DataEntity belongs to exactly one DataEntityBucket, which is uniquely identified by its DataEntityBucketId, a tuple of: where the data came from (DataSource), when it was created (TimeBucket), and a classification of the data (DataLabel, e.g. a stock ticker symbol). The full set of DataEntityBuckets on a Miner is referred to as its MinerIndex.

Validators periodically query each Miner to fetch their latest MinerIndexes and store them in a local database. This gives the Validator a complete understanding of all data that's stored on the network, as well as which Miners to query for specific types of data. Validators also periodically verify the correctness of the data stored on Miners and reward Miners based on the amount of [valuable data](#data-value) the Miner has. Validators log to [wandb](https://wandb.ai/ResiLabs/Resi Labs-validators) anonymously by default.

Miners upload their local stores to S3-compatible storage for public dataset access. This data is anonymized for privacy purposes to comply with the Terms of Service per each data source.

- For S3 storage setup, see the [S3 Storage documentation](https://github.com/macrocosm-os/Resi Labs-api).

The S3 storage option provides improved scalability, security, and performance, especially for large datasets. It uses a folder-based structure with blockchain authentication to ensure miners can only access their own data while validators can efficiently access all miners' data.

See the [Miner](docs/miner.md) and [Validator](docs/validator.md) docs for more information about how they work, as well as setup instructions.

# Incentive Mechanism

As described above, each Miner reports its MinerIndex to the Validator. The MinerIndex details how much and what type of data the Miner has. The Miner is then scored based on 2 dimensions:
1. How much data the Miner has and how valuable that data is.
1. How credible the Miner is.

## Data Value

Not all data is equally valuable! There are several factors used to determine data value:

### 1) Data Freshness

Fresh data is more valuable than old data, and data older than a certain threshold is not scored.

As of Dec 11th, 2023 data older than 30 days is not scored. This may increase in future.

### 2) Data Desirability & Geographic Prioritization

Resi Labs maintains a [Dynamic Desirability List](docs/dynamic_desirability.md) and uses our **Gravity System** to prioritize data collection:

**Gravity System:**
- JSON-based incentive weighting managed in the [gravity repository](https://github.com/resi-labs-ai/gravity)
- Currently prioritizes larger metro areas for maximum market impact
- Dynamically adjustable to respond to market demands and user requests
- Geographic weighting ensures miners focus on high-value property markets

**Dynamic Desirability:**
- Data deemed desirable is scored more highly based on both content and location
- Unspecified labels get the default_scale_factor of 0.3, meaning they score less than half value in comparison
- Metro area properties receive bonus weighting through the Gravity system

The DataDesirabilityLookup and Gravity weightings will evolve over time, but each change will be announced ahead of time to give Miners adequate time to prepare for updates.

### 3) Duplication Factor

Data that's stored by many Miners is less valuable than data stored by only a few. The value of a piece of data is decreases proportional to the number of Miners storing it.

## Miner Credibility

Validators remain suspicious of Miners and so they periodically check a sample of data from each Miner's MinerIndex, to verify the data correctness. The Validator uses these checks to track a Miner's credibility, which it then uses to scale a Miner's score. The scaling is done in such a way that it is **always** worse for a Miner to misrepresent what types and how much data it has.

# Resi Labs Dashboard

As you can see from the above, Resi Labs rewards diversity of data (storing 200 copies of the same data isn't exactly beneficial!)

To help understand the current data on the Subnet, the Resi Labs team hosts a dashboard (https://sn13-dashboard.api.ResiLabs.ai/), showing the amount of each type of data (by DataEntityBucketId) on the Subnet. Miners are strongly encouraged to use this dashboard to customize their [Miner Configuration](./docs/miner.md#configuring-the-miner), to maximize their rewards.

# Use Cases

subnet 46, Resi Labs, has a range of use-cases:

- Low-cost data-scraping that undercuts centralized and decentralized alternatives.
- Aid in market research in any industry by collecting social media results on pressing topics.
- Help boost the accuracy of predictive tools by injecting them with freshly scraped social media data.
- Understand global online sentiment on any topic, to help inform businesses on their goals.
- Track sports analytics on social media (used by Subnet 44, Score).
- Forecast performance of assets (used by Subnet 64, Chutes, via Squad.ai).

Resi Labs's potential is extensive, as anybody can use it to build datasets on whatever topics are meaningful to them. By tapping into Bittensor's miner and validator communities, people can access data scraping and analysis at a fast and affordable rate.

# Getting Started

## 🔥 IMMEDIATE ACTION: S3 Connectivity Test (Required for All Validators & Miners)

**Before the full system launches, please verify your S3 connectivity:**

### Quick Test (Takes <2 Minutes)
1. **Testing Guide:** [MINER_VALIDATOR_TESTING_GUIDE.md](https://github.com/resi-labs-ai/resi-labs-api/blob/main/MINER_VALIDATOR_TESTING_GUIDE.md)
2. **Direct Test Script:** [test_mainnet_s3_auth.py](https://github.com/resi-labs-ai/resi-labs-api/blob/main/api-test/test_mainnet_s3_auth.py)

### What This Test Does:
- ✅ Verifies you're registered as a validator/miner on Subnet 46
- ✅ Confirms you can receive AWS S3 access tokens from our API server
- ✅ Tests S3 bucket connectivity and permissions
- ✅ Ensures you're ready for full system launch

### Expected Output:
- Successful authentication with our S3 API server
- Valid AWS access tokens issued to your registered hotkey
- Confirmation of S3 bucket access permissions

**This test is critical** - it ensures you'll be able to participate fully once miner and validator code is complete.

---

## Full Setup (Coming Soon)

See [Miner Setup](docs/miner.md#miner_setup) to learn how to setup a Miner *(Code in development)*.

See [Validator Setup](docs/validator.md#validator_setup) to learn how to setup a Validator *(Code in development)*.

**📋 For Validators**: See the comprehensive [Validator Preferences Guide](./docs/validator_preferences_guide.md) to learn how to submit custom data preferences and influence network priorities through Dynamic Desirability.

# Upcoming Features

1. Private storage
2. More datasources feel free to add by yourself in [this repo](https://github.com/macrocosm-os/scrapers)! 
3. Youtube multilanguage support

# Terminology

**DataEntity:** A single "item" of data collected by a Miner. Each DataEntity has a URI, that the Validators can use to retrieve the item from its DataSource.

**DataEntityBucket:** A logical grouping of DataEntities, based on its DataEntityBucketId.

**DataEntityBucketId:** The unique identifier for a DataEntityBucket. It contains the TimeBucket, DataSource, and DataLabel.

**DataLabel:** A label associated with a DataEntity. Precisely what the label represents is unique to the DataSource. For example, for a Yahoo finance DataSource, the label is the stock ticker of the finance data.

**DataSource:** A source from which Miners scrape data.

**Miner Credibility**: A per-miner rating, based on how often they pass data validation checks. Used to heavily penalize Miner's who misrepresent their MinerIndex.

**Miner Index**: A summary of how much and what types of data a Miner has. Specifically, it's a list of DataEntityBuckets.

# Feedback

We welcome feedback!
