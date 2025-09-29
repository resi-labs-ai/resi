I'm building a subnet for data scraping on bittensor - we forked subnet 13 supercosmos's data universe.  We just updated the code so that our validators require miners to scrape rather than use an API.  (I'm waiting for that code to be pushed by our jr. developer).

Next I need to change the entire incentives mechanism and allow miners and validators to scrape specific zipcodes in a given time period.  Please let me know how I can organize this.

I also have a seperate server that grants S3 authentication tokens. I think that I could use that codebase for the API that tells validators what zipcodes to scrape.  I'm not sure if miners should also have access to that API or if they will be told by validators.

based on my new goals in @0039-update-zipcode-scraping.md can you help me to organize these requirements below into a todo list [].  Please ask me any questions you need the answer to first.

I would eventually like an ASCII diagram like an Oauth login that shows what resources are messaged by what actors when all the way from the API server picking a set of zipcodes every 4 hours, to validators updating miner weights every 4 hours for the previous set of zipcodes.

I'm sure we'll have to change the code to message validators, to message miners, to set weights to be more competative. etc.

Please also make any suggestions you see before we write out the full plan and I'll approve them.

Next steps, suggestions and answers. Please add them to @0039-scratchpad.md 

####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################

I'll help you organize these requirements and create a comprehensive plan. First, let me understand your current system better and ask some clarifying questions.

[5 tools called]

Now let me ask some clarifying questions and then create a comprehensive plan for your zipcode-based incentive mechanism:

## Clarifying Questions:

1. **Zipcode Selection Strategy**: Should validators select zipcodes based on population density, property count, geographic distribution, or a mix? Do you want to prioritize high-value markets (like Manhattan) or ensure broad coverage?

2. **Miner Communication**: Should miners get zipcode assignments directly from validators via the existing bittensor protocol, or should they also call the API server? The validator approach would be more decentralized but requires protocol changes.

3. **Validation Depth**: What percentage of scraped listings should validators spot-check? 1% for speed, 10% for accuracy, or adaptive based on miner reputation?

4. **Reward Distribution**: Should only the top 3 miners get rewards (winner-take-all), or should there be a graduated reward system (e.g., top 6 get decreasing weights)?

5. **Data Freshness**: How do you prevent miners from pre-scraping popular zipcodes? Should the API server include a timestamp/nonce that miners must include in their data?

Let me create the organized todo list and suggestions:

[2 tools called]

I've created a comprehensive analysis and plan for your zipcode-based incentive mechanism. Here are the key insights and recommendations:

## **Major Architectural Recommendations:**

### 1. **Hybrid Communication Model**
Instead of choosing between validators or miners calling the API, I recommend both:
- **API → Validators**: Get zipcode assignments every 4 hours
- **Validators → Miners**: Broadcast via existing bittensor protocol
- This maintains decentralization while ensuring coordination

### 2. **Anti-Gaming Strategy** 
The biggest risk is miners pre-scraping popular zipcodes. My solution:
- **Epoch-specific nonces** included with zipcode assignments
- Miners must include the nonce in S3 uploads
- Prevents pre-scraping since nonce changes every epoch

### 3. **Competitive Scoring Model**
Replace the current persistent scoring with real-time competition:
- **Speed (40%)** + **Quality (40%)** + **Volume (20%)**
- Top 6 evaluated, top 3 rewarded with decreasing weights
- Zero tolerance for fake data (immediate score of 0)

## **Implementation Phases:**

**Week 1**: Extend your existing S3 auth server with zipcode endpoints
**Week 2**: Update validator/miner protocols for zipcode broadcasting  
**Week 3**: Replace MinerScorer with competitive evaluation logic
**Week 4**: Testnet deployment and mainnet rollout

## **Critical Questions for You:**

1. **Geographic Focus**: Start with PA/NJ as mentioned, or nationwide?
2. **Epoch Timing**: 4-hour cycles optimal, or prefer different frequency?
3. **Reward Distribution**: Top 3 winners only, or spread to more miners?
4. **Hosting**: Digital Ocean for API server as preferred?
5. **Timeline**: How aggressive should the deployment timeline be?

The plan addresses all your requirements from the document while providing practical solutions for the technical challenges. The ASCII diagram shows the complete flow from API server selection through weight updates.

Would you like me to dive deeper into any specific aspect, or shall we start implementing based on your answers to the questions above?

####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################

Please help me improve the plan.

Answers to questions:
1. zipcodes should be selected randomly and should try to get the miners to mine the target number of listings each 4 hour period.  So combining mulitple zipcodes to hit that target plus or minus 10%.

2.  think the miners should get the zipcodes from the API server to start if that's easier.  Can you make a plan for what it would take for them to get the zipcodes from the validators?  Is that much more complecated? or no?  Does it have failure points and need redundancy  if the miners miss that communication, how can they recheck?

3. The number of listings checked should be fixed but adjustable by a config variable/ env variable.

4. I think the top 3 should get 95% of rewards and then there should be 5% or less distributed among other miners.  (Maybe less than 5%.  I really just want to encourage submissions but also be able to score miners at 0 if they lie.   Is bittensor 0-1 scoring? or there's also trust where I can slash trust.  I would like to distribute the rewards to the top 3 with very small rewards that keep those participating above those who lie.

5. Yes and no, do I care if miners prescrape if they return the right data... not really.  Will others think it's unfair?  Maybe...

Recomendations:
1. I don't mind validator api and miner broadcast if you think that is best
2. if prescraping will cause issues lets prevent it
3. Lets do that scoring

Critical questions:
1. no, just start random
2. 4 hours is good. Validators should be submitting the weights from the previous 4 hours for the next 4 hours becuase they should have 4 hours to score the miners before submitting the new weights. (Does that make sense?) - miners scrape for 4 hours then submit, validators have 4 hours to judge, then submit the weights, since validators are setting the wegiths every epic (72 minutes) they should be setting weights from the previous period as they are still validating the next period.
3. 3 winners, plus nominal scoring for others based on basic non checked data huristics simply to keep their weights above the liars.
4. yes digital ocean is prefered for api server
5. I think we can discuss this code and too caught up in the timeline.

####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################

Excellent feedback! Let me address your questions and update the plan with much more detailed requirements.

[2 tools called]

Perfect! I've created a comprehensive updated plan that addresses all your feedback and questions. Here are the key improvements:

## **Key Answers to Your Questions:**

### **1. Scaling & Performance** 
- **10K listings in 4 hours is very achievable** (~42 listings/minute with good proxies)
- Dynamic zipcode selection targets 5K ±10% initially, scales to 10K+
- Gets you to 3M listings in ~1 month instead of 100 days

### **2. Communication Architecture**
**Primary: Miners → API Direct** (simpler, easier to debug)
- Miners poll API server every 4 hours
- Single point of truth, no consensus issues

**Fallback: Validator Broadcast** (for redundancy)
- If API fails, miners query multiple validators
- Validators cache latest assignments for backup
- **Complexity**: Moderate - mainly just caching logic

### **3. Reward Distribution**
**95% Top-3 + 5% Participation Model:**
- Winner 1: 50%, Winner 2: 30%, Winner 3: 15%
- Remaining 5% split among honest participants
- Zero weights for liars/fake data
- Small positive weights (0.001) keep honest miners above cheaters

### **4. Validation Timeline**
**4-Hour Offset System** (exactly what you described):
- Epoch N: Miners scrape
- Epoch N+1: Validators validate Epoch N while miners work on new batch
- Weight setting happens during validation of previous epoch

### **5. Data Storage**
**✅ No changes needed** - your current zipcode-based S3 structure works perfectly!

## **Complete API Interface Specification**

I've defined three endpoints you can implement in your separate API repo:

1. **`GET /api/v1/zipcode-assignments/current`** - Miners get current assignments
2. **`GET /api/v1/zipcode-assignments/epoch/{id}`** - Validators get historical data
3. **`POST /api/v1/zipcode-assignments/status`** - Optional completion tracking

The API spec includes authentication (reusing your existing hotkey signatures), rate limiting, and detailed request/response formats.

## **Critical Implementation Insights:**

### **Zillow 1000-Result Limit Handling:**
- Validators should expect ~1000 results max per zipcode
- Use statistical sampling for spot-checks rather than exact counts
- Focus validation on data quality over precise quantity

### **Pre-scraping Decision:**
Based on your feedback, I kept the nonce system but made it optional. You're right that if miners return correct data, pre-scraping isn't necessarily bad - but it might create perception of unfairness.

### **Configurable Spot-Checking:**
```python
SPOT_CHECK_PERCENTAGE = 5  # Configurable via env var
```

## **Next Steps:**

1. **API Server**: Take the interface specification to your API repo team
2. **Miner Updates**: Implement API client for zipcode fetching  
3. **Validator Updates**: Replace MinerScorer with competitive evaluation
4. **Testing**: Deploy on testnet with 3-5 miners

The plan is now detailed enough for implementation while remaining flexible for adjustments. Would you like me to dive deeper into any specific phase or component?

####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################



####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################



####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################



####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################



####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################
####################################################################################################################################################################################

