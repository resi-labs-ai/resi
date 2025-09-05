# RapidAPI Zillow Integration

[RapidAPI](https://rapidapi.com/) is a popular API marketplace that provides access to thousands of APIs, including the Zillow API used by RESI for real estate data collection.

RESI uses RapidAPI to access Zillow's comprehensive property database. All Validators use RapidAPI to validate miner-submitted property data, and it is **required** for all miners to participate in the network.

## Getting Started with RapidAPI

### Step 1: Create a RapidAPI Account

1. Go to [RapidAPI.com](https://rapidapi.com/)
2. Click "Sign Up" and create a free account
3. Verify your email address
4. Complete your profile setup

### Step 2: Subscribe to Zillow API

1. Navigate to the [Zillow API on RapidAPI](https://rapidapi.com/apimaker/api/zillow-com1/)
2. Review the API documentation and endpoints
3. Click "Pricing" to view available subscription plans:
   - **Basic Plan**: Usually includes 1,000+ requests/month (good for testing)
   - **Pro Plans**: 10,000+ requests/month (recommended for active mining)
   - **Mega Plans**: 100,000+ requests/month (for high-volume operations)

### Step 3: Choose Your Plan

**For Miners:**
- Start with a **Pro Plan** (10,000+ requests/month) for consistent mining
- Monitor usage and upgrade as needed
- Consider higher-tier plans for competitive advantage

**For Validators:**
- Choose **Pro or Mega Plans** for validation capacity
- Budget for validation costs as operational expense
- Higher limits ensure continuous validation capability

### Step 4: Get Your API Key

1. After subscribing, go to the API's "Endpoints" tab
2. Your RapidAPI key will be visible in the "X-RapidAPI-Key" header
3. Copy this key - you'll need it for your environment configuration

## Setting Your API Key

Create a file named `.env` in the project root directory if it doesn't already exist and add the following:

```bash
RAPIDAPI_KEY="your_actual_rapidapi_key_here"
RAPIDAPI_HOST="zillow-com1.p.rapidapi.com"
```