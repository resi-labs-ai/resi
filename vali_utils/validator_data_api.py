"""
Validator Data API Client for coordinated data distribution.
Reuses existing S3 authentication pattern for consistency.
"""

import requests
import time
import datetime as dt
import threading
import bittensor as bt
from typing import Dict, Optional, Any, List
import os
import json
import random


class ValidatorDataAPI:
    """API client for validators to pull coordinated data blocks"""

    def __init__(self, wallet: bt.wallet, data_api_url: str, debug: bool = False):
        self.wallet = wallet
        self.data_api_url = data_api_url
        self.access_data = None
        self.expiry_time = 0
        self.lock = threading.RLock()
        self.debug = debug

    def _debug_print(self, message: str):
        if self.debug:
            print(f"DEBUG DATA_API: {message}")

    async def ensure_access(self) -> bool:
        """Ensure valid API access is available, refreshing if needed"""
        with self.lock:
            current_time = time.time()
            # Check if credentials are still valid (with 1 hour buffer)
            if self.access_data and current_time < self.expiry_time - 3600:
                self._debug_print("Using cached API access")
                return True

            # Get new access
            self._debug_print("Getting new API access from auth server")
            access_data = await self.get_validator_access()

            if not access_data:
                self._debug_print("Failed to get API access from auth server")
                return False

            self.access_data = access_data
            self._debug_print(f"Got API access data with keys: {list(access_data.keys())}")

            # Set expiry time based on the returned expiry
            if 'expiry_seconds' in access_data:
                self.expiry_time = current_time + access_data['expiry_seconds'] - 600  # 10 minute buffer
            else:
                # Parse ISO format expiry string if available
                try:
                    expiry_str = access_data.get('expiry')
                    if expiry_str:
                        expiry_dt = dt.datetime.fromisoformat(expiry_str)
                        self.expiry_time = expiry_dt.timestamp()
                    else:
                        self.expiry_time = current_time + 4 * 3600  # Default 4 hours
                except Exception:
                    self.expiry_time = current_time + 4 * 3600  # Default 4 hours

            return True

    async def get_validator_access(self, sources: str = "zillow,redfin,realtor,homes") -> Optional[Dict[str, Any]]:
        """
        Get validator access token using blockchain signature.
        Reuses existing S3 authentication pattern.
        """
        try:
            hotkey = self.wallet.hotkey.ss58_address
            timestamp = int(time.time())
            # Same commitment pattern as S3, just different prefix
            commitment = f"api:data:request:{hotkey}:{timestamp}:{sources}"
            signature = self.wallet.hotkey.sign(commitment.encode())
            signature_hex = signature.hex()

            payload = {
                "hotkey": hotkey,
                "timestamp": timestamp,
                "signature": signature_hex,
                "sources": sources
            }

            # Same request pattern as existing S3 auth
            response = requests.post(
                f"{self.data_api_url.rstrip('/')}/get-validator-access",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                try:
                    error_detail = response.json().get("detail", "Unknown error")
                except Exception:
                    error_detail = response.text or "Unknown error"
                bt.logging.error(f"❌ Failed to get API access: {error_detail}")
                return None

            access_data = response.json()
            bt.logging.info(f"✅ Got API access for sources: {sources}")

            return access_data

        except Exception as e:
            bt.logging.error(f"Error getting validator API access: {str(e)}")
            return None

    async def get_data_blocks(self, sources: List[str] = None, block_size: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Get random data blocks for coordinated mining assignments.
        
        Args:
            sources: List of data sources (zillow, redfin, realtor, homes)
            block_size: Number of properties per source
            
        Returns:
            Dictionary with data blocks by source
        """
        if not await self.ensure_access():
            bt.logging.error("Failed to ensure API access")
            return None

        if sources is None:
            sources = ["zillow", "redfin", "realtor", "homes"]

        try:
            # Build query parameters
            params = {
                "sources": ",".join(sources),
                "block_size": block_size,
                "format": "json"
            }

            # Add authorization header
            headers = {}
            if self.access_data and 'access_token' in self.access_data:
                headers['Authorization'] = f"Bearer {self.access_data['access_token']}"

            response = requests.get(
                f"{self.data_api_url.rstrip('/')}/api/v1/validator-data",
                params=params,
                headers=headers,
                timeout=60
            )

            if response.status_code != 200:
                bt.logging.error(f"Failed to get data blocks: {response.status_code}")
                bt.logging.error(f"Response: {response.text}")
                return None

            data_blocks = response.json()
            bt.logging.info(f"Got data blocks for {len(sources)} sources")
            
            # Log block sizes for debugging
            for source, block_data in data_blocks.get('data_blocks', {}).items():
                if isinstance(block_data, dict) and 'zpids' in block_data:
                    bt.logging.info(f"{source}: {len(block_data['zpids'])} properties")
                elif isinstance(block_data, dict):
                    for key, values in block_data.items():
                        if isinstance(values, list):
                            bt.logging.info(f"{source}.{key}: {len(values)} items")

            return data_blocks

        except Exception as e:
            bt.logging.error(f"Error getting data blocks: {str(e)}")
            return None

    def create_miner_assignments(self, data_blocks: Dict[str, Any], available_miners: List[int], 
                               miners_per_property: int = 5) -> Dict[str, List[int]]:
        """
        Create miner assignments ensuring diversity and overlap.
        
        Args:
            data_blocks: Data blocks from API
            available_miners: List of available miner UIDs
            miners_per_property: Number of miners to assign per property
            
        Returns:
            Dictionary mapping property IDs to assigned miner UIDs
        """
        assignments = {}
        
        # Extract all properties from all sources
        all_properties = []
        
        for source, block_data in data_blocks.get('data_blocks', {}).items():
            if source.upper() == 'ZILLOW' and 'zpids' in block_data:
                for zpid in block_data['zpids']:
                    all_properties.append(f"zillow:{zpid}")
            elif source.upper() == 'REDFIN' and 'property_ids' in block_data:
                for prop_id in block_data['property_ids']:
                    all_properties.append(f"redfin:{prop_id}")
            elif source.upper() in ['REALTOR_COM', 'HOMES_COM'] and 'addresses' in block_data:
                for address in block_data['addresses']:
                    all_properties.append(f"{source.lower()}:{address}")

        bt.logging.info(f"Creating assignments for {len(all_properties)} properties")
        
        # Assign miners to each property
        for property_id in all_properties:
            # Randomly select miners for this property
            if len(available_miners) >= miners_per_property:
                assigned_miners = random.sample(available_miners, miners_per_property)
            else:
                # If not enough miners, assign all available miners
                assigned_miners = available_miners.copy()
                
            assignments[property_id] = assigned_miners

        bt.logging.info(f"Created {len(assignments)} property assignments")
        return assignments

    def format_assignment_for_miner(self, miner_uid: int, data_blocks: Dict[str, Any], 
                                   assignments: Dict[str, List[int]]) -> Dict[str, List[str]]:
        """
        Format assignment data for a specific miner.
        
        Args:
            miner_uid: Target miner UID
            data_blocks: Original data blocks
            assignments: Property to miner assignments
            
        Returns:
            Assignment data formatted for DataAssignmentRequest
        """
        miner_assignment = {
            "ZILLOW": [],
            "REDFIN": [],
            "REALTOR_COM": [],
            "HOMES_COM": []
        }

        # Find properties assigned to this miner
        for property_id, assigned_miners in assignments.items():
            if miner_uid in assigned_miners:
                source, prop_id = property_id.split(':', 1)
                
                if source == 'zillow':
                    miner_assignment["ZILLOW"].append(prop_id)
                elif source == 'redfin':
                    miner_assignment["REDFIN"].append(prop_id)
                elif source == 'realtor_com':
                    miner_assignment["REALTOR_COM"].append(prop_id)
                elif source == 'homes_com':
                    miner_assignment["HOMES_COM"].append(prop_id)

        # Remove empty sources
        miner_assignment = {k: v for k, v in miner_assignment.items() if v}

        return miner_assignment


# Configuration for the data API
class DataAPIConfig:
    """Configuration for validator data API"""
    
    def __init__(self):
        self.data_api_url = os.getenv('DATA_API_URL', 'https://api.resi-subnet.com')
        self.enable_validator_spot_checks = os.getenv('ENABLE_VALIDATOR_SPOT_CHECKS', 'false').lower() == 'true'
        self.consensus_confidence_threshold = float(os.getenv('CONSENSUS_CONFIDENCE_THRESHOLD', '0.6'))
        self.anomaly_detection_threshold = float(os.getenv('ANOMALY_DETECTION_THRESHOLD', '0.3'))
        self.miners_per_property = int(os.getenv('MINERS_PER_PROPERTY', '5'))
        self.assignment_timeout_hours = int(os.getenv('ASSIGNMENT_TIMEOUT_HOURS', '2'))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'data_api_url': self.data_api_url,
            'enable_validator_spot_checks': self.enable_validator_spot_checks,
            'consensus_confidence_threshold': self.consensus_confidence_threshold,
            'anomaly_detection_threshold': self.anomaly_detection_threshold,
            'miners_per_property': self.miners_per_property,
            'assignment_timeout_hours': self.assignment_timeout_hours
        }
