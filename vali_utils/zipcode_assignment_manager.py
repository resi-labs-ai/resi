"""
Zipcode Assignment Manager for coordinated consensus validation.
Handles batch creation, miner group assignment, and geographic diversity.
"""

import random
import hashlib
import datetime as dt
from typing import Dict, List, Tuple, Optional, Any, Set
import bittensor as bt
from collections import defaultdict

from common.data import DataSource


class ZipcodeAssignmentManager:
    """
    Manages zipcode batch assignments with overlap for consensus validation.
    Ensures cold key diversity and geographic distribution.
    """

    def __init__(self, metagraph: bt.metagraph, config: Dict[str, Any] = None):
        self.metagraph = metagraph
        self.config = config or self._get_default_config()
        
        # Track assignments to prevent conflicts
        self.active_assignments = {}
        self.assignment_history = []

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for zipcode assignments"""
        return {
            'zipcodes_per_batch': 20,
            'miners_per_zipcode_batch': 10,
            'batch_overlap_factor': 2,
            'max_batches_per_cycle': 50,
            'min_miners_for_consensus': 6,
            'max_miners_per_coldkey': 1,
            'geographic_diversity_required': True,
            'min_different_coldkeys': 5,
            'assignment_timeout_hours': 3,
            'expected_properties_per_zipcode': 50
        }

    def create_zipcode_assignments(self, available_zipcodes: List[str], 
                                 available_miners: List[int],
                                 sources: List[str] = None) -> Dict[str, Any]:
        """
        Create zipcode batch assignments with overlapping miner groups for consensus.
        
        Args:
            available_zipcodes: List of zipcodes to assign
            available_miners: Available miner UIDs
            sources: Data sources to assign (default: ['ZILLOW'])
            
        Returns:
            Dictionary with assignment details and miner assignments
        """
        if sources is None:
            sources = ['ZILLOW_SOLD']
            
        bt.logging.info(f"Creating zipcode assignments for {len(available_zipcodes)} zipcodes across {len(available_miners)} miners")
        
        # Validate inputs
        if len(available_miners) < self.config['min_miners_for_consensus']:
            raise ValueError(f"Need at least {self.config['min_miners_for_consensus']} miners, got {len(available_miners)}")
        
        # Create zipcode batches
        zipcode_batches = self._create_zipcode_batches(available_zipcodes)
        
        # Create miner assignments with overlap
        assignments = self._assign_miners_to_batches(zipcode_batches, available_miners, sources)
        
        # Generate assignment metadata
        assignment_metadata = self._create_assignment_metadata(assignments, zipcode_batches, sources)
        
        bt.logging.info(f"Created {len(assignments)} assignments across {len(zipcode_batches)} batches")
        
        return {
            'assignment_metadata': assignment_metadata,
            'miner_assignments': assignments,
            'zipcode_batches': zipcode_batches,
            'sources': sources,
            'total_miners_assigned': len(set().union(*[a['miners'] for a in assignments.values()])),
            'total_zipcodes': len(available_zipcodes)
        }

    def _create_zipcode_batches(self, available_zipcodes: List[str]) -> Dict[str, List[str]]:
        """Create zipcode batches for assignment"""
        batches = {}
        batch_size = self.config['zipcodes_per_batch']
        max_batches = self.config['max_batches_per_cycle']
        
        # Shuffle zipcodes for randomization
        shuffled_zipcodes = available_zipcodes.copy()
        random.shuffle(shuffled_zipcodes)
        
        # Limit to max batches
        total_zipcodes = min(len(shuffled_zipcodes), max_batches * batch_size)
        limited_zipcodes = shuffled_zipcodes[:total_zipcodes]
        
        # Create batches
        for i in range(0, len(limited_zipcodes), batch_size):
            batch_id = f"batch_{i//batch_size:03d}"
            batch_zipcodes = limited_zipcodes[i:i + batch_size]
            batches[batch_id] = batch_zipcodes
            
        bt.logging.info(f"Created {len(batches)} zipcode batches with {batch_size} zipcodes each")
        return batches

    def _assign_miners_to_batches(self, zipcode_batches: Dict[str, List[str]], 
                                available_miners: List[int], sources: List[str]) -> Dict[str, Dict[str, Any]]:
        """Assign miners to zipcode batches with overlap for consensus"""
        assignments = {}
        overlap_factor = self.config['batch_overlap_factor']
        miners_per_batch = self.config['miners_per_zipcode_batch']
        
        for batch_id, zipcodes in zipcode_batches.items():
            # Create overlapping groups for this batch
            for overlap_group in range(overlap_factor):
                assignment_key = f"{batch_id}_group_{overlap_group}"
                
                # Select diverse miners for this group
                group_miners = self._select_diverse_miners(
                    available_miners, 
                    miners_per_batch,
                    exclude_assignments=assignments  # Avoid same miner in multiple groups of same batch
                )
                
                if len(group_miners) < self.config['min_miners_for_consensus']:
                    bt.logging.warning(f"Insufficient miners for {assignment_key}: {len(group_miners)}")
                    continue
                
                assignments[assignment_key] = {
                    'batch_id': batch_id,
                    'overlap_group': overlap_group,
                    'zipcodes': zipcodes,
                    'miners': group_miners,
                    'sources': sources,
                    'expected_properties': len(zipcodes) * self.config['expected_properties_per_zipcode'],
                    'coldkey_diversity': self._calculate_coldkey_diversity(group_miners)
                }
                
        return assignments

    def _select_diverse_miners(self, available_miners: List[int], target_count: int,
                             exclude_assignments: Dict[str, Dict[str, Any]] = None) -> List[int]:
        """Select miners with cold key diversity requirements"""
        if exclude_assignments is None:
            exclude_assignments = {}
            
        # Get cold key mapping
        coldkey_to_miners = self._get_coldkey_mapping(available_miners)
        
        # Track used cold keys to enforce diversity
        used_coldkeys = set()
        selected_miners = []
        
        # First pass: select one miner per cold key
        available_coldkeys = list(coldkey_to_miners.keys())
        random.shuffle(available_coldkeys)
        
        for coldkey in available_coldkeys:
            if len(selected_miners) >= target_count:
                break
                
            # Check if this cold key is already used too much
            coldkey_usage = sum(1 for assignment in exclude_assignments.values() 
                              if any(self._get_miner_coldkey(m) == coldkey for m in assignment.get('miners', [])))
            
            if coldkey_usage >= self.config['max_miners_per_coldkey']:
                continue
                
            # Select random miner from this cold key
            coldkey_miners = coldkey_to_miners[coldkey]
            available_from_coldkey = [m for m in coldkey_miners if m in available_miners]
            
            if available_from_coldkey:
                selected_miner = random.choice(available_from_coldkey)
                selected_miners.append(selected_miner)
                used_coldkeys.add(coldkey)
        
        # Second pass: fill remaining slots if needed (allowing some cold key reuse)
        if len(selected_miners) < target_count:
            remaining_miners = [m for m in available_miners if m not in selected_miners]
            additional_needed = target_count - len(selected_miners)
            
            if remaining_miners:
                additional_miners = random.sample(
                    remaining_miners, 
                    min(additional_needed, len(remaining_miners))
                )
                selected_miners.extend(additional_miners)
        
        # Validate diversity requirements
        if len(used_coldkeys) < self.config['min_different_coldkeys']:
            bt.logging.warning(f"Insufficient cold key diversity: {len(used_coldkeys)} < {self.config['min_different_coldkeys']}")
        
        return selected_miners

    def _get_coldkey_mapping(self, miner_uids: List[int]) -> Dict[str, List[int]]:
        """Get mapping of cold keys to miner UIDs"""
        coldkey_to_miners = defaultdict(list)
        
        for uid in miner_uids:
            if uid < len(self.metagraph.coldkeys):
                coldkey = self.metagraph.coldkeys[uid]
                coldkey_to_miners[coldkey].append(uid)
            else:
                # Fallback for invalid UIDs
                coldkey_to_miners[f"unknown_{uid}"].append(uid)
                
        return dict(coldkey_to_miners)

    def _get_miner_coldkey(self, miner_uid: int) -> str:
        """Get cold key for a miner UID"""
        if miner_uid < len(self.metagraph.coldkeys):
            return self.metagraph.coldkeys[miner_uid]
        return f"unknown_{miner_uid}"

    def _calculate_coldkey_diversity(self, miner_uids: List[int]) -> Dict[str, Any]:
        """Calculate cold key diversity metrics for a group of miners"""
        coldkey_counts = defaultdict(int)
        
        for uid in miner_uids:
            coldkey = self._get_miner_coldkey(uid)
            coldkey_counts[coldkey] += 1
            
        return {
            'total_miners': len(miner_uids),
            'unique_coldkeys': len(coldkey_counts),
            'diversity_ratio': len(coldkey_counts) / len(miner_uids) if miner_uids else 0,
            'max_miners_per_coldkey': max(coldkey_counts.values()) if coldkey_counts else 0,
            'coldkey_distribution': dict(coldkey_counts)
        }

    def _create_assignment_metadata(self, assignments: Dict[str, Dict[str, Any]], 
                                  zipcode_batches: Dict[str, List[str]], 
                                  sources: List[str]) -> Dict[str, Any]:
        """Create metadata for the assignment cycle"""
        assignment_id = self._generate_assignment_id()
        
        return {
            'assignment_id': assignment_id,
            'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=self.config['assignment_timeout_hours'])).isoformat(),
            'total_batches': len(zipcode_batches),
            'total_assignments': len(assignments),
            'overlap_factor': self.config['batch_overlap_factor'],
            'miners_per_batch': self.config['miners_per_zipcode_batch'],
            'sources': sources,
            'config': self.config.copy()
        }

    def _generate_assignment_id(self) -> str:
        """Generate unique assignment ID"""
        timestamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S')
        random_suffix = hashlib.md5(f"{timestamp}_{random.random()}".encode()).hexdigest()[:8]
        return f"zipcode_assignment_{timestamp}_{random_suffix}"

    def format_assignment_for_miner(self, miner_uid: int, assignment_key: str, 
                                  assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format assignment data for a specific miner"""
        if assignment_key not in assignment_data['miner_assignments']:
            return None
            
        assignment = assignment_data['miner_assignments'][assignment_key]
        
        if miner_uid not in assignment['miners']:
            return None
            
        # Create DataAssignmentRequest format
        zipcode_assignments = {}
        for source in assignment['sources']:
            zipcode_assignments[source] = assignment['zipcodes']
            
        return {
            'request_id': f"{assignment_data['assignment_metadata']['assignment_id']}_miner_{miner_uid}",
            'assignment_mode': 'zipcodes',
            'zipcode_assignments': zipcode_assignments,
            'zipcode_batch_id': assignment['batch_id'],
            'overlap_group': assignment['overlap_group'],
            'expected_properties_per_zipcode': self.config['expected_properties_per_zipcode'],
            'expires_at': assignment_data['assignment_metadata']['expires_at'],
            'expected_completion': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)).isoformat(),
            'assignment_type': 'zipcode_scraping',
            'priority': 1
        }

    def get_assignment_statistics(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics for an assignment"""
        assignments = assignment_data['miner_assignments']
        
        total_miners = set()
        coldkey_distribution = defaultdict(int)
        batch_distribution = defaultdict(int)
        
        for assignment in assignments.values():
            total_miners.update(assignment['miners'])
            
            for miner_uid in assignment['miners']:
                coldkey = self._get_miner_coldkey(miner_uid)
                coldkey_distribution[coldkey] += 1
                
            batch_distribution[assignment['batch_id']] += 1
        
        return {
            'total_unique_miners': len(total_miners),
            'total_assignments': len(assignments),
            'unique_coldkeys': len(coldkey_distribution),
            'coldkey_diversity_ratio': len(coldkey_distribution) / len(total_miners) if total_miners else 0,
            'average_assignments_per_batch': sum(batch_distribution.values()) / len(batch_distribution) if batch_distribution else 0,
            'coldkey_distribution': dict(coldkey_distribution),
            'batch_distribution': dict(batch_distribution)
        }
