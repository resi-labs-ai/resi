"""
Zipcode Competitive Scoring System
Implements per-zipcode competition with 55%/30%/10%/5% reward distribution
"""

from typing import Dict, List, Any, Optional, Set
import bittensor as bt
import json
import asyncio


class ZipcodeCompetitiveScorer:
    """
    Per-zipcode competitive scoring system with multi-tier validation
    
    Reward Distribution:
    - 1st place per zipcode: 55%
    - 2nd place per zipcode: 30% 
    - 3rd place per zipcode: 10%
    - All other participants: 5% (distributed equally)
    """
    
    def __init__(self, miner_evaluator=None):
        self.reward_distribution = {
            'first_place': 0.55,   # 55% to top miner per zipcode
            'second_place': 0.30,  # 30% to second miner per zipcode  
            'third_place': 0.10,   # 10% to third miner per zipcode
            'participation': 0.05  # 5% distributed among all other valid participants
        }
        
        # Reference to MinerEvaluator for validation (injected after initialization)
        self.miner_evaluator = miner_evaluator
    
    def set_miner_evaluator(self, miner_evaluator):
        """Inject the MinerEvaluator instance for validation"""
        self.miner_evaluator = miner_evaluator
        bt.logging.info("MinerEvaluator injected into ZipcodeCompetitiveScorer")
    
    async def validate_and_rank_zipcode_submissions(self, zipcode: str, submissions: List[Dict], 
                                             expected_listings: int, epoch_nonce: str) -> Dict[str, Any]:
        """
        Multi-tier validation and ranking for a specific zipcode
        
        Process:
        1. Sort submissions by time (earliest first)
        2. Validate each submission through 3 tiers until we find 3 winners
        3. Stop validation once 3 winners are found (efficiency optimization)
        
        Args:
            zipcode: Zipcode being validated
            submissions: List of miner submissions for this zipcode
            expected_listings: Expected number of listings for this zipcode
            epoch_nonce: Epoch nonce for deterministic validation
            
        Returns:
            Dict with winners, participants, and reward allocation
        """
        if not self.miner_evaluator:
            bt.logging.error("MinerEvaluator not injected into ZipcodeCompetitiveScorer!")
            return {
                'zipcode': zipcode,
                'expected_listings': expected_listings,
                'winners': [],
                'participants': [],
                'zipcode_rewards': {},
                'total_listings_found': 0,
                'total_submissions_processed': 0,
                'validation_summary': {
                    'winners_found': 0,
                    'participants_found': 0,
                    'total_validated': 0
                }
            }
        
        bt.logging.info(f"Validating {len(submissions)} submissions for zipcode {zipcode}")
        
        # Step 1: Sort by submission time (earliest first for competitive advantage)
        sorted_submissions = sorted(submissions, key=lambda x: x['submission_timestamp'])
        
        # Step 2: Multi-tier validation to find top 3 winners
        winners = []
        participants = []  # Miners who passed some validation but not all tiers
        
        for submission in sorted_submissions:
            miner_hotkey = submission['miner_hotkey']
            
            bt.logging.debug(f"Validating submission from {miner_hotkey[:8]}... for zipcode {zipcode}")
            
            # Use MinerEvaluator's validation methods
            validation_result = await self._validate_submission_with_evaluator(
                submission, expected_listings
            )
            
            if validation_result['passes_all_tiers']:
                # This miner passes all tiers - add to winners if we need more
                if len(winners) < 3:
                    winner_rank = len(winners) + 1
                    listings = submission.get('listings', [])
                    winners.append({
                        'miner_hotkey': miner_hotkey,
                        'submission_time': submission['submission_timestamp'],
                        'listing_count': len(listings),
                        'rank': winner_rank,
                        'validation_result': validation_result,
                        'listings': listings 
                    })
                    
                    bt.logging.success(f"Winner #{winner_rank} for zipcode {zipcode}: {miner_hotkey[:8]}... ({len(listings)} listings)")
                    
                    # Stop validation once we have 3 winners (efficiency optimization)
                    if len(winners) == 3:
                        bt.logging.info(f"Found 3 winners for zipcode {zipcode}, stopping validation")
                        break
            else:
                # Failed validation but may still get participation reward
                failed_at_tier = validation_result['failed_at_tier']
                
                # Only add to participants if they passed at least Tier 1 (quantity check)
                if failed_at_tier > 1:
                    participants.append({
                        'miner_hotkey': miner_hotkey,
                        'failed_at_tier': failed_at_tier,
                        'submission_time': submission['submission_timestamp'],
                        'listing_count': len(submission.get('listings', [])),
                        'validation_result': validation_result
                    })
                    
                    bt.logging.debug(f"Miner {miner_hotkey[:8]} added to participants (failed at tier {failed_at_tier})")
        
        # Step 3: Calculate zipcode-specific rewards
        zipcode_rewards = {}
        total_listings_in_zipcode = sum(w['listing_count'] for w in winners)
        
        for i, winner in enumerate(winners):
            if i == 0:  # 1st place
                reward_percentage = self.reward_distribution['first_place']
            elif i == 1:  # 2nd place  
                reward_percentage = self.reward_distribution['second_place']
            elif i == 2:  # 3rd place
                reward_percentage = self.reward_distribution['third_place']
            else:
                continue  # Should never happen since we limit to 3 winners
            
            zipcode_rewards[winner['miner_hotkey']] = {
                'rank': winner['rank'],
                'reward_percentage': reward_percentage,
                'listing_count': winner['listing_count']
            }
        
        result = {
            'zipcode': zipcode,
            'expected_listings': expected_listings,
            'winners': winners,
            'participants': participants,
            'zipcode_rewards': zipcode_rewards,
            'total_listings_found': total_listings_in_zipcode,
            'total_submissions_processed': len(sorted_submissions),
            'validation_summary': {
                'winners_found': len(winners),
                'participants_found': len(participants),
                'total_validated': len([s for s in sorted_submissions if s['miner_hotkey'] in 
                                      [w['miner_hotkey'] for w in winners] + 
                                      [p['miner_hotkey'] for p in participants]])
            }
        }
        
        bt.logging.info(f"Zipcode {zipcode} validation complete: "
                       f"{len(winners)} winners, {len(participants)} participants, "
                       f"{total_listings_in_zipcode} total listings")
        
        return result
    
    async def _validate_submission_with_evaluator(self, submission: Dict, expected_listings: int) -> Dict[str, Any]:
        """
        Validate a submission using MinerEvaluator's validation methods
        
        This ensures consistency across real-time and epoch-end validation:
        - Same Tier 1 logic (API-driven ±15%)
        - Same Tier 2 logic (quality + epoch compliance)
        - Same Tier 3 logic (spot-check validation with scraper)
        - Same duplicate detection (zpid, URI-zpid consistency)
        
        Args:
            submission: Miner submission data with 'listings' field
            expected_listings: Expected number of listings
            
        Returns:
            Dict with validation results
        """
        from common.data import DataEntity, DataSource
        from vali_utils import utils as vali_utils
        
        # Convert submission listings to DataEntity format
        entities = []
        for listing in submission.get('listings', []):
            try:
                # Create DataEntity from listing
                content = json.dumps(listing).encode('utf-8')
                entity = DataEntity(
                    uri=listing.get('source_url', f"submission://{listing.get('zpid', 'unknown')}"),
                    datetime=listing.get('scraped_timestamp'),
                    source=DataSource.SZILL_VALI,
                    content=content,
                    content_size_bytes=len(content)
                )
                entities.append(entity)
            except Exception as e:
                bt.logging.debug(f"Failed to convert listing to DataEntity: {e}")
                continue
        
        if not entities:
            return {
                'passes_all_tiers': False,
                'failed_at_tier': 1,
                'tier1': {'passes': False, 'reason': 'No valid entities'},
                'tier2': None,
                'tier3': None
            }
        
        # Check for duplicates using the same 4-layer check as real-time validation
        from vali_utils import utils as vali_utils
        unique = vali_utils.are_entities_unique(entities)
        if not unique:
            bt.logging.info(f"Submission failed duplicate check (zpid or URI-zpid consistency)")
            return {
                'passes_all_tiers': False,
                'failed_at_tier': 0,  # Pre-tier failure
                'tier1': {'passes': False, 'reason': 'Duplicate entities found'},
                'tier2': None,
                'tier3': None
            }
        
        # Tier 1: Quantity validation (same as real-time)
        tier1_passes, tier1_reason, tier1_metrics = self.miner_evaluator._apply_tier1_quantity_validation(
            entities, expected_count=expected_listings
        )
        
        if not tier1_passes:
            return {
                'passes_all_tiers': False,
                'failed_at_tier': 1,
                'tier1': {'passes': False, 'reason': tier1_reason, 'metrics': tier1_metrics},
                'tier2': None,
                'tier3': None
            }
        
        # Tier 2: Quality & Epoch Compliance validation (same as real-time)
        tier2_passes, tier2_reason, tier2_metrics = self.miner_evaluator._apply_tier2_quality_validation(entities)
        
        if not tier2_passes:
            return {
                'passes_all_tiers': False,
                'failed_at_tier': 2,
                'tier1': {'passes': True, 'reason': tier1_reason, 'metrics': tier1_metrics},
                'tier2': {'passes': False, 'reason': tier2_reason, 'metrics': tier2_metrics},
                'tier3': None
            }
        
        # Tier 3: Spot-check validation (same as real-time)
        # Randomly select 2 entities for accuracy verification
        entities_to_validate = vali_utils.choose_entities_to_verify(entities)
        
        bt.logging.debug(f"Tier 3: Selected {len(entities_to_validate)} entities for spot-check validation")
        
        if not entities_to_validate:
            return {
                'passes_all_tiers': False,
                'failed_at_tier': 3,
                'tier1': {'passes': True, 'reason': tier1_reason, 'metrics': tier1_metrics},
                'tier2': {'passes': True, 'reason': tier2_reason, 'metrics': tier2_metrics},
                'tier3': {'passes': False, 'reason': 'No entities selected for spot-check', 'metrics': {}}
            }
        
        # Get data source from entities
        data_source = entities[0].source if entities else DataSource.SZILL_VALI
        
        # Validate entities using scraper
        from common.validation_result import ValidationResult
        
        # Skip unsupported data sources
        if data_source in [DataSource.X, DataSource.REDDIT, DataSource.YOUTUBE]:
            bt.logging.debug(f"Data source {data_source} not supported for Tier 3 - marking as pass")
            validation_results = [ValidationResult(
                is_valid=True, 
                reason=f"Data source not supported - skipping validation", 
                content_size_bytes_validated=0
            ) for _ in entities_to_validate]
        else:
            # Use the scraper provider from miner_evaluator
            try:
                scraper = self.miner_evaluator.scraper_provider.get(
                    self.miner_evaluator.PREFERRED_SCRAPERS[data_source]
                )
                validation_results = await scraper.validate(entities_to_validate)
            except Exception as e:
                bt.logging.error(f"Scraper validation failed: {e}")
                # Mark as failed validation
                validation_results = [ValidationResult(
                    is_valid=False,
                    reason=f"Scraper error: {str(e)}",
                    content_size_bytes_validated=0
                ) for _ in entities_to_validate]
        
        # Apply Tier 3 validation
        tier3_passes, tier3_reason, tier3_metrics = self.miner_evaluator._apply_tier3_spot_check_validation(
            entities_to_validate,
            validation_results
        )
        
        bt.logging.debug(f"Tier 3 result: {tier3_reason}")
        
        return {
            'passes_all_tiers': tier3_passes,
            'failed_at_tier': None if tier3_passes else 3,
            'tier1': {'passes': True, 'reason': tier1_reason, 'metrics': tier1_metrics},
            'tier2': {'passes': True, 'reason': tier2_reason, 'metrics': tier2_metrics},
            'tier3': {'passes': tier3_passes, 'reason': tier3_reason, 'metrics': tier3_metrics}
        }
    
    def calculate_epoch_proportional_weights(self, all_zipcode_results: List[Dict]) -> Dict[str, Any]:
        """
        Calculate final proportional weights across all zipcodes in epoch
        
        Process:
        1. Calculate zipcode weights based on actual listings found
        2. Weight each miner's zipcode rewards by zipcode size
        3. Distribute 5% participation reward among all non-winners
        4. Normalize final scores to sum to 1.0
        
        Args:
            all_zipcode_results: List of validation results for each zipcode
            
        Returns:
            Dict with normalized miner scores and metadata
        """
        bt.logging.info(f"Calculating proportional weights across {len(all_zipcode_results)} zipcodes")
        
        # Step 1: Calculate zipcode weights based on listing counts
        total_epoch_listings = sum(
            result['total_listings_found'] for result in all_zipcode_results
        )
        
        if total_epoch_listings == 0:
            bt.logging.warning("No listings found across all zipcodes")
            return {
                'miner_scores': {},
                'zipcode_weights': {},
                'total_participants': 0,
                'total_winners': 0,
                'total_epoch_listings': 0,
                'reward_distribution_summary': {
                    'winners_total_reward': 0,
                    'participants_total_reward': 0,
                    'total_miners_rewarded': 0
                }
            }
        
        zipcode_weights = {}
        for result in all_zipcode_results:
            zipcode_weights[result['zipcode']] = (
                result['total_listings_found'] / total_epoch_listings
            )
        
        bt.logging.info(f"Zipcode weights calculated. Total epoch listings: {total_epoch_listings}")
        
        # Step 2: Calculate miner scores weighted by zipcode size
        miner_scores = {}
        all_participants = set()
        all_winners = set()
        
        for result in all_zipcode_results:
            zipcode = result['zipcode']
            zipcode_weight = zipcode_weights[zipcode]
            
            bt.logging.debug(f"Processing zipcode {zipcode} (weight: {zipcode_weight:.4f})")
            
            # Add winners with their weighted rewards
            for miner_hotkey, reward_info in result['zipcode_rewards'].items():
                if miner_hotkey not in miner_scores:
                    miner_scores[miner_hotkey] = 0.0
                
                # Weight the reward by zipcode size
                weighted_reward = reward_info['reward_percentage'] * zipcode_weight
                miner_scores[miner_hotkey] += weighted_reward
                all_winners.add(miner_hotkey)
                
                bt.logging.debug(f"Winner {miner_hotkey[:8]} in {zipcode}: "
                               f"rank {reward_info['rank']}, "
                               f"reward {reward_info['reward_percentage']:.2f}, "
                               f"weighted {weighted_reward:.4f}")
            
            # Collect all participants for 5% distribution (excluding winners)
            for participant in result['participants']:
                participant_hotkey = participant['miner_hotkey']
                if participant_hotkey not in all_winners:  # Don't double-reward winners
                    all_participants.add(participant_hotkey)
        
        # Step 3: Distribute remaining 5% among all participants
        remaining_percentage = self.reward_distribution['participation']
        non_winner_participants = all_participants - all_winners
        
        if non_winner_participants:
            participation_reward_per_miner = remaining_percentage / len(non_winner_participants)
            
            bt.logging.info(f"Distributing {remaining_percentage:.2f} among "
                           f"{len(non_winner_participants)} non-winner participants "
                           f"({participation_reward_per_miner:.4f} each)")
            
            for participant_hotkey in non_winner_participants:
                if participant_hotkey not in miner_scores:
                    miner_scores[participant_hotkey] = 0.0
                miner_scores[participant_hotkey] += participation_reward_per_miner
        else:
            bt.logging.info("No non-winner participants found for 5% distribution")
        
        # Step 4: Normalize scores to sum to 1.0
        total_score = sum(miner_scores.values())
        if total_score > 0:
            normalized_scores = {
                hotkey: score / total_score 
                for hotkey, score in miner_scores.items()
            }
        else:
            normalized_scores = {}
        
        # Verify normalization
        normalized_sum = sum(normalized_scores.values())
        bt.logging.info(f"Score normalization: {total_score:.4f} -> {normalized_sum:.4f}")
        
        result = {
            'miner_scores': normalized_scores,
            'zipcode_weights': zipcode_weights,
            'total_participants': len(all_participants),
            'total_winners': len(all_winners),
            'total_epoch_listings': total_epoch_listings,
            'reward_distribution_summary': {
                'winners_total_reward': sum(score for hotkey, score in normalized_scores.items() 
                                          if hotkey in all_winners),
                'participants_total_reward': sum(score for hotkey, score in normalized_scores.items() 
                                               if hotkey in non_winner_participants),
                'total_miners_rewarded': len(normalized_scores)
            }
        }
        
        bt.logging.success(f"Epoch scoring complete: {len(normalized_scores)} miners scored, "
                          f"{len(all_winners)} winners, {len(all_participants)} total participants")
        
        return result
    
    def get_zipcode_leaderboard(self, zipcode_result: Dict) -> List[Dict[str, Any]]:
        """
        Get formatted leaderboard for a specific zipcode
        
        Args:
            zipcode_result: Result from validate_and_rank_zipcode_submissions
            
        Returns:
            List of miner rankings with details
        """
        leaderboard = []
        
        # Add winners
        for winner in zipcode_result['winners']:
            reward_info = zipcode_result['zipcode_rewards'].get(winner['miner_hotkey'], {})
            leaderboard.append({
                'miner_hotkey': winner['miner_hotkey'],
                'rank': winner['rank'],
                'status': 'WINNER',
                'listing_count': winner['listing_count'],
                'reward_percentage': reward_info.get('reward_percentage', 0),
                'submission_time': winner['submission_time']
            })
        
        # Add participants (no zipcode-specific reward, but eligible for 5% distribution)
        for participant in zipcode_result['participants']:
            leaderboard.append({
                'miner_hotkey': participant['miner_hotkey'],
                'rank': None,
                'status': 'PARTICIPANT',
                'listing_count': participant['listing_count'],
                'reward_percentage': 0,  # Will get share of 5% in final calculation
                'submission_time': participant['submission_time'],
                'failed_at_tier': participant['failed_at_tier']
            })
        
        return leaderboard
    
    def get_epoch_summary(self, all_zipcode_results: List[Dict], 
                         final_scores: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive epoch summary
        
        Args:
            all_zipcode_results: All zipcode validation results
            final_scores: Final calculated scores
            
        Returns:
            Comprehensive epoch summary
        """
        total_submissions = sum(r['total_submissions_processed'] for r in all_zipcode_results)
        total_winners = sum(len(r['winners']) for r in all_zipcode_results)
        total_participants = sum(len(r['participants']) for r in all_zipcode_results)
        
        # Top performers across all zipcodes
        top_performers = sorted(
            final_scores['miner_scores'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # Zipcode performance summary
        zipcode_summary = []
        for result in all_zipcode_results:
            zipcode_summary.append({
                'zipcode': result['zipcode'],
                'expected_listings': result['expected_listings'],
                'actual_listings': result['total_listings_found'],
                'winners_found': len(result['winners']),
                'participants': len(result['participants']),
                'submissions_processed': result['total_submissions_processed'],
                'weight': final_scores['zipcode_weights'].get(result['zipcode'], 0)
            })
        
        return {
            'epoch_totals': {
                'total_zipcodes': len(all_zipcode_results),
                'total_submissions': total_submissions,
                'total_winners': total_winners,
                'total_participants': total_participants,
                'total_listings': final_scores['total_epoch_listings'],
                'miners_rewarded': len(final_scores['miner_scores'])
            },
            'top_performers': top_performers,
            'zipcode_summary': zipcode_summary,
            'reward_distribution': final_scores['reward_distribution_summary']
        }
