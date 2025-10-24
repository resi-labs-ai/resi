"""
ResiLabs API Client for Bittensor Subnet 46 Integration
Handles zipcode assignments, miner status updates, and S3 credentials
"""

import requests
import time
import json
from datetime import datetime as dt
from typing import Dict, Any, Optional, List
import bittensor as bt


class ResiLabsAPIClient:
    """API client for ResiLabs zipcode assignment and validation system"""
    
    def __init__(self, base_url: str, hotkey, coldkey=None):
        self.base_url = base_url.rstrip('/')
        self.hotkey = hotkey
        self.coldkey = coldkey
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ResiLabs-Bittensor-Client/1.0'
        })
    
    def _generate_signature(self, commitment: str) -> str:
        """Generate Bittensor signature for commitment string"""
        commitment_bytes = commitment.encode('utf-8')
        signature = self.hotkey.sign(commitment_bytes).hex()
        return signature
    
    def _get_timestamp(self) -> int:
        """Get current Unix timestamp in seconds"""
        return int(time.time())
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(3):  # 3 retry attempts
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, **kwargs)
                elif method.upper() == 'POST':
                    response = self.session.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                bt.logging.warning(f"API request attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
    
    # ===== MINER ENDPOINTS =====
    
    def get_current_zipcode_assignments(self) -> Dict[str, Any]:
        """
        Get current epoch zipcode assignments for competitive mining
        
        Returns:
            Dict containing epoch info, zipcodes, nonce, and metadata
        """
        timestamp = self._get_timestamp()
        commitment = f"zipcode:assignment:current:{timestamp}"
        signature = self._generate_signature(commitment)
        
        params = {
            'hotkey': str(self.hotkey.ss58_address),
            'signature': signature,
            'timestamp': timestamp
        }
        
        bt.logging.info(f"Requesting zipcode assignments for hotkey {self.hotkey.ss58_address[:8]}...")
        
        result = self._make_request('GET', '/api/v1/zipcode-assignments/current', params=params)
        
        if result.get('success'):
            bt.logging.success(f"Received {len(result.get('zipcodes', []))} zipcode assignments for epoch {result.get('epochId')}")
        
        return result
    
    def update_miner_status(self, epoch_id: str, nonce: str, status: str, 
                           listings_scraped: Optional[int] = None,
                           zipcodes_completed: Optional[List[Dict]] = None,
                           s3_upload_complete: bool = False,
                           s3_upload_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Update miner mining status and progress
        
        Args:
            epoch_id: Current epoch ID
            nonce: Epoch nonce for validation
            status: Mining status (IN_PROGRESS, COMPLETED, FAILED, TIMEOUT)
            listings_scraped: Total number of listings scraped
            zipcodes_completed: List of completed zipcode info
            s3_upload_complete: Whether S3 upload is complete
            s3_upload_timestamp: When S3 upload completed
        """
        timestamp = self._get_timestamp()
        commitment = f"miner:status:{self.hotkey.ss58_address}:{epoch_id}:{timestamp}"
        signature = self._generate_signature(commitment)
        
        data = {
            'hotkey': str(self.hotkey.ss58_address),
            'signature': signature,
            'timestamp': timestamp,
            'epochId': epoch_id,
            'nonce': nonce,
            'status': status,
            's3UploadComplete': s3_upload_complete
        }
        
        if listings_scraped is not None:
            data['listingsScraped'] = listings_scraped
        
        if zipcodes_completed:
            data['zipcodesCompleted'] = zipcodes_completed
        
        if s3_upload_complete and s3_upload_timestamp:
            data['s3UploadTimestamp'] = s3_upload_timestamp
        elif s3_upload_complete:
            data['s3UploadTimestamp'] = dt.datetime.now(dt.timezone.utc).isoformat()
        
        bt.logging.info(f"Updating miner status to {status} for epoch {epoch_id}")
        
        result = self._make_request('POST', '/api/v1/zipcode-assignments/status', json=data)
        
        if result.get('success'):
            bt.logging.success(f"Miner status updated successfully: {status}")
        
        return result
    
    def get_s3_upload_credentials(self) -> Dict[str, Any]:
        """
        Get S3 upload credentials for miner data submission
        
        Returns:
            Dict containing S3 upload URL, fields, and metadata
        """
        if not self.coldkey:
            raise ValueError("Coldkey required for S3 access")
        
        timestamp = self._get_timestamp()
        commitment = f"s3:data:access:{self.coldkey.ss58_address}:{self.hotkey.ss58_address}:{timestamp}"
        signature = self._generate_signature(commitment)
        
        data = {
            'coldkey': str(self.coldkey.ss58_address),
            'hotkey': str(self.hotkey.ss58_address),
            'timestamp': timestamp,
            'signature': signature,
            'expiry': timestamp + 86400  # 24 hours
        }
        
        bt.logging.info("Requesting S3 upload credentials...")
        
        result = self._make_request('POST', '/get-folder-access', json=data)
        
        if result.get('success'):
            bt.logging.success("S3 upload credentials obtained successfully")
        
        return result
    
    # ===== VALIDATOR ENDPOINTS =====
    
    def get_validator_s3_credentials(self, epoch_id: str, purpose: str = "epoch_validation_results",
                                   estimated_size_mb: int = 25, retention_days: int = 90) -> Dict[str, Any]:
        """
        Get S3 upload credentials for validator result storage
        
        Args:
            epoch_id: Epoch ID for validation results
            purpose: Purpose of the upload
            estimated_size_mb: Estimated data size in MB
            retention_days: How long to retain the data
        """
        timestamp = self._get_timestamp()
        commitment = f"s3:validator:upload:{timestamp}"
        signature = self._generate_signature(commitment)
        
        data = {
            'hotkey': str(self.hotkey.ss58_address),
            'signature': signature,
            'timestamp': timestamp,
            'epochId': epoch_id,
            'purpose': purpose,
            'estimatedDataSizeMb': estimated_size_mb,
            'retentionDays': retention_days
        }
        
        bt.logging.info(f"Requesting validator S3 credentials for epoch {epoch_id}")
        
        result = self._make_request('POST', '/api/v1/s3-access/validator-upload', json=data)
        
        if result.get('success'):
            bt.logging.success("Validator S3 credentials obtained successfully")
        
        return result
    
    # ===== SYSTEM ENDPOINTS =====
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide statistics and current epoch information"""
        result = self._make_request('GET', '/api/v1/zipcode-assignments/stats')
        return result
    
    def check_health(self) -> Dict[str, Any]:
        """Check API server health and connectivity"""
        try:
            result = self._make_request('GET', '/healthcheck')
            return result
        except Exception as e:
            bt.logging.error(f"Health check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    # ===== UTILITY METHODS =====
    
    def wait_for_epoch_completion(self, current_epoch_id: str, check_interval: int = 60) -> Dict[str, Any]:
        """
        Wait for current epoch to complete and return next epoch info
        
        Args:
            current_epoch_id: Current epoch ID to wait for completion
            check_interval: How often to check (seconds)
        """
        bt.logging.info(f"Waiting for epoch {current_epoch_id} to complete...")
        
        while True:
            try:
                stats = self.get_system_statistics()
                current_epoch = stats.get('epochStatus', {}).get('currentEpoch', {})
                
                if current_epoch.get('id') != current_epoch_id:
                    bt.logging.success(f"Epoch {current_epoch_id} completed. New epoch: {current_epoch.get('id')}")
                    return current_epoch
                
                time_until_end = stats.get('epochStatus', {}).get('timing', {}).get('timeUntilEpochEnd', 0)
                bt.logging.info(f"Epoch {current_epoch_id} still active. Time remaining: {time_until_end}s")
                
                time.sleep(check_interval)
                
            except Exception as e:
                bt.logging.error(f"Error checking epoch status: {e}")
                time.sleep(check_interval)
    
    def get_current_epoch_info(self) -> Optional[Dict[str, Any]]:
        """Get current epoch information from system stats"""
        try:
            stats = self.get_system_statistics()
            return stats.get('epochStatus', {}).get('currentEpoch')
        except Exception as e:
            bt.logging.error(f"Failed to get current epoch info: {e}")
            return None


# Utility function for easy client creation
def create_api_client(config, wallet) -> ResiLabsAPIClient:
    """
    Create ResiLabs API client with auto-configuration based on network
    
    Args:
        config: Bittensor config object
        wallet: Bittensor wallet object
    
    Returns:
        Configured ResiLabsAPIClient instance
    """
    # Auto-configure API URL based on network
    if hasattr(config, 'netuid') and config.netuid == 428:  # Testnet
        api_base_url = "https://api-staging.resilabs.ai"  # Staging API
        bt.logging.info("Using testnet staging API endpoint")
    else:  # Mainnet
        api_base_url = "https://api.resilabs.ai"
        bt.logging.info("Using production API endpoint")
    
    # Override with config if provided
    if hasattr(config, 'resi_api_url') and config.resi_api_url:
        api_base_url = config.resi_api_url
        bt.logging.info(f"Using configured API endpoint: {api_base_url}")
    
    return ResiLabsAPIClient(
        base_url=api_base_url,
        hotkey=wallet.hotkey,
        coldkey=wallet.coldkeypub if hasattr(wallet, 'coldkeypub') else None
    )
