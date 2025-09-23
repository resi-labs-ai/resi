"""
Configuration for the enhanced validation system.
Supports both consensus-based and API-based validation.
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ValidationConfig:
    """Configuration for validation systems"""
    
    # Data API Configuration
    data_api_url: str = os.getenv('DATA_API_URL', 'https://api.resi-subnet.com')
    
    # Validation Strategy
    enable_validator_spot_checks: bool = os.getenv('ENABLE_VALIDATOR_SPOT_CHECKS', 'false').lower() == 'true'
    validation_mode: str = 'consensus'  # 'consensus' or 'api'
    
    # Consensus Parameters
    consensus_confidence_threshold: float = float(os.getenv('CONSENSUS_CONFIDENCE_THRESHOLD', '0.6'))
    anomaly_detection_threshold: float = float(os.getenv('ANOMALY_DETECTION_THRESHOLD', '0.3'))
    
    # Assignment Parameters
    miners_per_property: int = int(os.getenv('MINERS_PER_PROPERTY', '5'))
    assignment_timeout_hours: int = int(os.getenv('ASSIGNMENT_TIMEOUT_HOURS', '2'))
    max_properties_per_assignment: int = int(os.getenv('MAX_PROPERTIES_PER_ASSIGNMENT', '50'))
    
    # Data Sources
    enabled_sources: List[str] = os.getenv('ENABLED_DATA_SOURCES', 'ZILLOW_SOLD').split(',')
    block_size_per_source: int = int(os.getenv('BLOCK_SIZE_PER_SOURCE', '1000'))
    
    # Time-based Rewards
    enable_time_based_rewards: bool = os.getenv('ENABLE_TIME_BASED_REWARDS', 'true').lower() == 'true'
    fast_response_bonus: float = float(os.getenv('FAST_RESPONSE_BONUS', '1.5'))  # <30min
    medium_response_bonus: float = float(os.getenv('MEDIUM_RESPONSE_BONUS', '1.2'))  # <60min
    slow_response_penalty: float = float(os.getenv('SLOW_RESPONSE_PENALTY', '0.8'))  # >120min
    
    # Behavioral Analysis
    enable_behavioral_analysis: bool = os.getenv('ENABLE_BEHAVIORAL_ANALYSIS', 'true').lower() == 'true'
    synchronization_threshold_seconds: int = int(os.getenv('SYNC_THRESHOLD_SECONDS', '30'))
    identical_content_penalty: float = float(os.getenv('IDENTICAL_CONTENT_PENALTY', '0.5'))
    
    # Monitoring and Logging
    enable_detailed_logging: bool = os.getenv('ENABLE_DETAILED_LOGGING', 'false').lower() == 'true'
    log_validation_details: bool = os.getenv('LOG_VALIDATION_DETAILS', 'false').lower() == 'true'
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        # Set validation mode based on spot checks setting
        if self.enable_validator_spot_checks:
            self.validation_mode = 'api'
        else:
            self.validation_mode = 'consensus'
            
        # Validate thresholds
        if not 0 <= self.consensus_confidence_threshold <= 1:
            raise ValueError("consensus_confidence_threshold must be between 0 and 1")
        if not 0 <= self.anomaly_detection_threshold <= 1:
            raise ValueError("anomaly_detection_threshold must be between 0 and 1")
            
        # Validate miners per property
        if self.miners_per_property < 3:
            raise ValueError("miners_per_property must be at least 3 for consensus")
            
        # Clean up sources list
        self.enabled_sources = [s.strip().lower() for s in self.enabled_sources if s.strip()]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'data_api_url': self.data_api_url,
            'validation_mode': self.validation_mode,
            'enable_validator_spot_checks': self.enable_validator_spot_checks,
            'consensus_confidence_threshold': self.consensus_confidence_threshold,
            'anomaly_detection_threshold': self.anomaly_detection_threshold,
            'miners_per_property': self.miners_per_property,
            'assignment_timeout_hours': self.assignment_timeout_hours,
            'max_properties_per_assignment': self.max_properties_per_assignment,
            'enabled_sources': self.enabled_sources,
            'block_size_per_source': self.block_size_per_source,
            'enable_time_based_rewards': self.enable_time_based_rewards,
            'fast_response_bonus': self.fast_response_bonus,
            'medium_response_bonus': self.medium_response_bonus,
            'slow_response_penalty': self.slow_response_penalty,
            'enable_behavioral_analysis': self.enable_behavioral_analysis,
            'synchronization_threshold_seconds': self.synchronization_threshold_seconds,
            'identical_content_penalty': self.identical_content_penalty,
            'enable_detailed_logging': self.enable_detailed_logging,
            'log_validation_details': self.log_validation_details
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ValidationConfig':
        """Create configuration from dictionary"""
        return cls(**config_dict)

    def save_to_file(self, file_path: str):
        """Save configuration to file"""
        import json
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, file_path: str) -> 'ValidationConfig':
        """Load configuration from file"""
        import json
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for this configuration"""
        return {
            'DATA_API_URL': self.data_api_url,
            'ENABLE_VALIDATOR_SPOT_CHECKS': str(self.enable_validator_spot_checks).lower(),
            'CONSENSUS_CONFIDENCE_THRESHOLD': str(self.consensus_confidence_threshold),
            'ANOMALY_DETECTION_THRESHOLD': str(self.anomaly_detection_threshold),
            'MINERS_PER_PROPERTY': str(self.miners_per_property),
            'ASSIGNMENT_TIMEOUT_HOURS': str(self.assignment_timeout_hours),
            'MAX_PROPERTIES_PER_ASSIGNMENT': str(self.max_properties_per_assignment),
            'ENABLED_DATA_SOURCES': ','.join(self.enabled_sources),
            'BLOCK_SIZE_PER_SOURCE': str(self.block_size_per_source),
            'ENABLE_TIME_BASED_REWARDS': str(self.enable_time_based_rewards).lower(),
            'FAST_RESPONSE_BONUS': str(self.fast_response_bonus),
            'MEDIUM_RESPONSE_BONUS': str(self.medium_response_bonus),
            'SLOW_RESPONSE_PENALTY': str(self.slow_response_penalty),
            'ENABLE_BEHAVIORAL_ANALYSIS': str(self.enable_behavioral_analysis).lower(),
            'SYNC_THRESHOLD_SECONDS': str(self.synchronization_threshold_seconds),
            'IDENTICAL_CONTENT_PENALTY': str(self.identical_content_penalty),
            'ENABLE_DETAILED_LOGGING': str(self.enable_detailed_logging).lower(),
            'LOG_VALIDATION_DETAILS': str(self.log_validation_details).lower()
        }


# Predefined configurations for different scenarios

CONSENSUS_ONLY_CONFIG = ValidationConfig(
    enable_validator_spot_checks=False,
    consensus_confidence_threshold=0.6,
    anomaly_detection_threshold=0.3,
    miners_per_property=10,  # Increased for zipcode batches
    enabled_sources=['ZILLOW_SOLD'],
    enable_behavioral_analysis=True,
    enable_time_based_rewards=True
)

API_VALIDATION_CONFIG = ValidationConfig(
    enable_validator_spot_checks=True,
    consensus_confidence_threshold=0.8,  # Higher threshold since we have API validation
    anomaly_detection_threshold=0.2,     # Lower threshold to trigger API validation more often
    miners_per_property=5,               # Fewer miners needed when API validating
    enabled_sources=['ZILLOW_SOLD'],
    enable_behavioral_analysis=True,
    enable_time_based_rewards=True
)

DEVELOPMENT_CONFIG = ValidationConfig(
    data_api_url='http://localhost:8000',
    enable_validator_spot_checks=False,
    consensus_confidence_threshold=0.5,  # Lower threshold for testing
    anomaly_detection_threshold=0.4,
    miners_per_property=5,               # Fewer miners for testing
    enabled_sources=['ZILLOW_SOLD'],
    assignment_timeout_hours=1,          # Shorter timeout for testing
    block_size_per_source=10,           # Smaller blocks for testing
    enable_detailed_logging=True,
    log_validation_details=True
)

PRODUCTION_CONFIG = ValidationConfig(
    enable_validator_spot_checks=False,  # Start with consensus only
    consensus_confidence_threshold=0.7,
    anomaly_detection_threshold=0.25,
    miners_per_property=10,              # Increased for zipcode batches
    enabled_sources=['ZILLOW_SOLD'],
    assignment_timeout_hours=4,          # Longer for zipcode scraping
    block_size_per_source=20,           # Zipcodes per batch
    enable_behavioral_analysis=True,
    enable_time_based_rewards=True,
    enable_detailed_logging=False,
    log_validation_details=False
)
