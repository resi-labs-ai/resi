Track when miners submit their data

E: Validator V2 EPIC: Build this incentives mechanism now for V2 Mining and Validating based on zipcodes & first to submit strategy
S: Todo J: Task Get a list of all zipcodes
All Zipcodes In List (already just have a list of zipcodes 
Zipcode by population by Zillow Research
S: Todo J: Spike 20min?: Can we get the number of homes in each zip code from one of these exports?
S: Todo J: Spike We can make the validator code scrape the zipcode. and feed everyone the needs for each epoch?
S: Todo J: Feature Get the current number of sold listings for a zipcode so we can know how many should be returned by the miners for a quick spot check.  require miners to be within 10% of that number...
J: Spike MVP - what zipcodes to scrape?  how many listings should be in that zipcode?  Who submitted first? (everyone is running the same validator code), validator code should check submissions by miners, look for the timestamps, look for whos first by ordering them, then validate and set weights.
API server to return this list to validators
S: Todo J: Feature Can we start in Pensylvania and NJ because that's where we have clients?
S: Todo J: Task API that tells validators the next zipcodes
S: Todo J: Spike Decide how the new zipcodes are decided upon and when? Do we create a list of X zipcodes every 4 hours to target a specific number of listings and bring that minimum number of listings up over time?
S: Todo J: Task Determine where this API is hosted (digital ocean? or aws?) (I prefer digital ocean because AWS is overly complicated. Lets launch API server on digital ocean
S: Todo J: Spike Define Security: Same security as S3 server, validators need to prove that they are an active validator in order to get the list of zipcodes.  We could even modify the S3 server to return validators the current zipcodes and S3 access keys (that would require minimal changes and we already have the API server code)  Do we add a new endpoint or do we return with the current endpoint for S3 access (I would say new endpoint so that they can request more often)
S: Todo J: Task Validation Strategy
S: Todo J: Task Change validation strategy to review the results submitted the fastest.  Draw out a time line for review.
S: Todo J: Spike Miners are given zipcodes to scrape in a broadcast announcement at the beginning of each epic (how do they get this list?  Bittensor neuron emitted, or they also call the S3 api server to request the given zipcodes?)
S: Todo J: Task Miners scrape, save code to their local database, and submit code to S3 as soon as they are done with all the zipcodes.  The data uploaded needs to be for the requested areas.
S: Todo J: Spike How do miners tell validators when they submitted their S3 data. Or do they sign their submitted data with a timestamp (in a way that cannot be faked?)
S: Todo J: Task Validators Order all miners by submission time.
S: Todo J: Task at the beginning of the epic validators validate miners from the previous epic for the previous zipcodes.  Validators go from "First to submit" and continue to validate miners until they find 3 miners that pass the threshold goal.
S: Todo J: Task Validators set weights for miners
S: Todo J: Spike How much weight should the 1st, 2nd, 3rd get?  Should it taper off?  Maybe the top 6 miners are evaluated that pass the threshold but only the top 3 are rewarded (you can pass the quick spot check that does not require api calls (are the number of results reasonable for each zipcode).  But then the 4th to submit might have better data quality so they jump over the first 3.  That way first to submit isn't the only gamified thing. (Balance speed and quality)
NOTE: If only top miners are rewarded all the annoying miners are going to disappear - miners are going to have to compete, not just copy - and they have no way of copying each other.
NOTE: Smart miners would start pre mining data for future zipcodes... but that data could be out of date... So how do we get them to wait until a zipcode comes up?
S: Todo J: Spike We might really need to think through this mechanic so that the bar requires fields to be filled out (if they are available from zillow then theres no reason that a miner should not have every field filled out (unless it happens to be empty on zillow).  So maybe there is a calculation that weighs how many fields are filled out vs time submitted, vs accuracy to number of properties.  (And it does all these checks before choosing which miners to spotcheck).  Needs to be deterministic so that all validators choose to spot check the same miners.
S: Todo J: Spike How do validators spot check miners? What percentage of listings do they check?  And if miners.  TODO: Calculate how many api calls/ scrapes a validator would need to do to validate all top miners (check 1%, 10%, more...? How do we decide what the number is?)
S: Todo J: Spike !!!!! How do validators upload to S3, validators should upload to their own hot key folder the data from the winning miners.  We need a way to save the data that was actually accepted and validated.  Can upload this data along with metadata about the confidence scoring and if the spotcheck was 100% successful (Should be 100% because there should be zero tolerance for non existing listings or ZPIds that don't match the scraped zipcode)
S: Todo J: Spike how do miners not get deregistered if many of them are getting zeros?  Should we at least give minimal weights to miners who submitted something?  We can check that miners at least submitted something even if they didn't win.  Vs didn't submit anything at all.  it does not take api calls to check the number of listings that a miner submitted.  Though they could easily submit the correct number of listings in trash data if they know we're not going to validate just so they can get a minimal reward.  I'm thinking "how do we differentiate that they did submit something vs they didnt' do any work at all". how about they did submit the right number of listings vs no listings. (0.0001 vs 0.0000) weight. --- TODO: We probably want to reserve a score of 0 for miners who submit quickly but submit synthetic data - that should be worse than miners who submit slowly or miners who do not submit any results.  Submitting fast but malicious should be rewarded with an actual score of Zero.
S: Todo J: Task Pre Production
S: Todo J: Task Pre production API with Preproduction S3 bucket... Diwas you can do with your own S3.  or if you need me to configure our AWS for you I can do that monday.  TODO: write up what you need Caleb to configure in S3 for an AWS S3 bucket and API keys for development
S: Todo J: Task Testnet Validators Running
S: Todo J: Task Write up an announcement for miners and validators when this is live
S: Todo J: Task Our own testnet miner (basic)
S: Todo J: Task Verify outcomes
S: Todo J: Task Testnet miner and validators working (Code running properly)
S: Todo J: Task Testnet S3 data being uploaded by miners and validators S: Todo J: Task Testnet weights being set (is there a taostats for testnet?)
S: Todo J: Task Go live steps:
S: Todo J: Task Announce rules to miners: Write up an announcement for miners that describes the consensus mechanism, how they will be provided zipcodes to scrape, how exactly their submissions will be rated.  And how speed is the key factor.  
S: Todo J: Task Push new code to Github
S: Todo J: Task Relaunch API server in production (update any required permissions - Create user permissions for Validators if they are uploading data to their own folders)
S: Todo J: Task Verify outcomes
S: Todo J: Task Testnet miner and validators working
S: Todo J: Task have validators update their code bases, test they can start the validator, and turn off burn code.
S: Todo J: Task Verify weights are being set properly by validators (1-3 miners with weights, all others with zeros)
