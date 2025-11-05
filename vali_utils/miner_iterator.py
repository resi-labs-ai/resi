import bisect
import copy
import threading
from typing import List
import bittensor as bt

import random


class MinerIterator:
    """A thread safe infinite iterator to cyclically enumerate the current set of miner UIDs.

    Why? To perform miner evaluations, the validator will enumerate through the miners in order to help ensure
    each miner is evaluated at least once per epoch.
    """

    def __init__(self, miner_uids: List[int]):
        self.miner_uids = sorted(copy.deepcopy(miner_uids))
        # Start the index at a random position. This helps ensure that miners with high UIDs aren't penalized if
        # the validator restarts frequently.
        self.index = random.randint(0, len(self.miner_uids) - 1)
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def __next__(self) -> int:
        with self.lock:
            if len(self.miner_uids) == 0:
                # This iterator should be infinite. If there are no miner UIDs, raise an error.
                raise IndexError("No miner UIDs.")

            uid = self.miner_uids[self.index]
            self.index += 1
            if self.index >= len(self.miner_uids):
                self.index = 0
            return uid

    def peek(self) -> int:
        """Returns the next miner UID without advancing the iterator."""
        with self.lock:
            if len(self.miner_uids) == 0:
                # This iterator should be infinite. If there are no miner UIDs, raise an error.
                raise IndexError("No miner UIDs.")

            return self.miner_uids[self.index]

    def set_miner_uids(self, miner_uids: List[int]):
        """Updates the miner UIDs to iterate.

        The iterator will be updated to the first miner uid that is greater than or equal to UID that would be next
        returned by the iterator. This helps ensure that frequent updates to the miner_uids does not cause too much
        churn in the sequence of UIDs returned by the iterator.
        """
        sorted_uids = sorted(copy.deepcopy(miner_uids))
        with self.lock:
            next_uid = self.miner_uids[self.index]
            new_index = bisect.bisect_left(sorted_uids, next_uid)
            if new_index >= len(sorted_uids):
                new_index = 0
            self.index = new_index
            self.miner_uids = sorted_uids

    def get_synchronized_evaluation_batch(self, current_block: int, batch_size: int = 100) -> List[int]:
        """
        Return synchronized batch of miners for evaluation every 4 hours.
        All validators will select the same miners using block-based cycle determination.
        
        Optimizes API usage: 186k calls/month vs current 27.9k calls/month.
        7x faster evaluation: Every ~10.4 hours instead of ~68 hours.
        
        Args:
            current_block: Current blockchain block number
            batch_size: Number of miners to evaluate per cycle (default 100)
            
        Returns:
            List of miner UIDs for synchronized evaluation
        """
        with self.lock:
            if len(self.miner_uids) == 0:
                return []
            
            total_miners = len(self.miner_uids)
            
            # Debug: Log available miner UIDs
            bt.logging.info(f"Available miner UIDs: {self.miner_uids} (total: {total_miners})")
            
            # TESTING: Force include UID XX for testing purposes
            # bt.logging.info("TESTING: UID XX is included in synchronized evaluation batch")
            # return [XX]
            
            # For small networks (< 100 miners), evaluate all miners in a single cycle
            if total_miners <= batch_size:
                bt.logging.info(f"Small network detected ({total_miners} miners). Evaluating all miners in single cycle.")
                return self.miner_uids
            
            # Calculate which cycle we're in (changes every 4 hours = 1200 blocks)
            blocks_per_cycle = 1200  # 4 hours = 1200 blocks
            # Dynamically determine number of cycles needed
            num_cycles = max(1, (total_miners + batch_size - 1) // batch_size)  # Ceiling division
            cycle_number = (current_block // blocks_per_cycle) % num_cycles
            
            bt.logging.info(f"Synchronized evaluation: block {current_block}, cycle {cycle_number}/{num_cycles-1}, total_miners={total_miners}")
            
            # Calculate batch for this cycle
            batch_start = cycle_number * batch_size
            batch_end = min(batch_start + batch_size, total_miners)
            
            selected_uids = self.miner_uids[batch_start:batch_end]
            bt.logging.info(f"Cycle {cycle_number}: Evaluating miners {batch_start}-{batch_end-1} ({len(selected_uids)} miners)")
            
            return selected_uids

    def get_next_synchronized_batch(self, current_block: int) -> List[int]:
        """
        Convenience method that returns the current synchronized batch.
        This replaces the old random iteration with synchronized batch selection.
        """
        return self.get_synchronized_evaluation_batch(current_block)
