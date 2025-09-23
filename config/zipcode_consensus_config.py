"""
Configuration for Zipcode Consensus Validation System
Supports both mock and production API endpoints
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ZipcodeConsensusConfig:
    """Configuration for zipcode-based consensus validation"""
    
    # Data API Configuration (configurable URL)
    data_api_url: str = os.getenv('DATA_API_URL', 'http://localhost:8000')  # Mock server by default
    
    # Source Configuration (updated to ZILLOW_SOLD)
    enabled_sources: List[str] = field(default_factory=lambda: os.getenv('ENABLED_DATA_SOURCES', 'ZILLOW_SOLD').split(','))
    
    # Zipcode Assignment Configuration
    zipcodes_per_batch: int = int(os.getenv('ZIPCODES_PER_BATCH', '20'))
    miners_per_zipcode_batch: int = int(os.getenv('MINERS_PER_ZIPCODE_BATCH', '10'))
    batch_overlap_factor: int = int(os.getenv('BATCH_OVERLAP_FACTOR', '2'))
    max_batches_per_cycle: int = int(os.getenv('MAX_BATCHES_PER_CYCLE', '50'))
    
    # Consensus Parameters
    consensus_confidence_threshold: float = float(os.getenv('CONSENSUS_CONFIDENCE_THRESHOLD', '0.6'))
    anomaly_detection_threshold: float = float(os.getenv('ANOMALY_DETECTION_THRESHOLD', '0.3'))
    min_miners_for_consensus: int = int(os.getenv('MIN_MINERS_FOR_CONSENSUS', '6'))
    
    # S3 Integration
    use_s3_consensus: bool = os.getenv('USE_S3_CONSENSUS', 'true').lower() == 'true'
    s3_upload_timeout_minutes: int = int(os.getenv('S3_UPLOAD_TIMEOUT_MINUTES', '30'))
    s3_completion_threshold: float = float(os.getenv('S3_COMPLETION_THRESHOLD', '0.8'))
    
    # Assignment Timing
    assignment_timeout_hours: int = int(os.getenv('ASSIGNMENT_TIMEOUT_HOURS', '4'))
    assignment_cycle_hours: int = int(os.getenv('ASSIGNMENT_CYCLE_HOURS', '4'))
    expected_properties_per_zipcode: int = int(os.getenv('EXPECTED_PROPERTIES_PER_ZIPCODE', '50'))
    
    # Cold Key Diversity
    max_miners_per_coldkey: int = int(os.getenv('MAX_MINERS_PER_COLDKEY', '1'))
    min_different_coldkeys: int = int(os.getenv('MIN_DIFFERENT_COLDKEYS', '5'))
    geographic_diversity_required: bool = os.getenv('GEOGRAPHIC_DIVERSITY_REQUIRED', 'true').lower() == 'true'
    
    # Validation Strategy
    enable_validator_spot_checks: bool = os.getenv('ENABLE_VALIDATOR_SPOT_CHECKS', 'false').lower() == 'true'
    spot_check_sample_size: int = int(os.getenv('SPOT_CHECK_SAMPLE_SIZE', '5'))
    spot_check_timeout_minutes: int = int(os.getenv('SPOT_CHECK_TIMEOUT_MINUTES', '10'))
    
    # Behavioral Analysis
    enable_behavioral_analysis: bool = os.getenv('ENABLE_BEHAVIORAL_ANALYSIS', 'true').lower() == 'true'
    synchronization_threshold_seconds: int = int(os.getenv('SYNC_THRESHOLD_SECONDS', '30'))
    identical_content_penalty: float = float(os.getenv('IDENTICAL_CONTENT_PENALTY', '0.5'))
    
    # Time-based Rewards
    enable_time_based_rewards: bool = os.getenv('ENABLE_TIME_BASED_REWARDS', 'true').lower() == 'true'
    fast_response_bonus: float = float(os.getenv('FAST_RESPONSE_BONUS', '1.5'))  # <1 hour
    medium_response_bonus: float = float(os.getenv('MEDIUM_RESPONSE_BONUS', '1.2'))  # <2 hours
    slow_response_penalty: float = float(os.getenv('SLOW_RESPONSE_PENALTY', '0.8'))  # >3 hours
    
    # Monitoring and Logging
    enable_detailed_logging: bool = os.getenv('ENABLE_DETAILED_LOGGING', 'false').lower() == 'true'
    log_validation_details: bool = os.getenv('LOG_VALIDATION_DETAILS', 'false').lower() == 'true'
    log_s3_operations: bool = os.getenv('LOG_S3_OPERATIONS', 'false').lower() == 'true'
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        # Validate thresholds
        if not 0 <= self.consensus_confidence_threshold <= 1:
            raise ValueError("consensus_confidence_threshold must be between 0 and 1")
        if not 0 <= self.anomaly_detection_threshold <= 1:
            raise ValueError("anomaly_detection_threshold must be between 0 and 1")
        if not 0 <= self.s3_completion_threshold <= 1:
            raise ValueError("s3_completion_threshold must be between 0 and 1")
            
        # Validate miners per batch
        if self.miners_per_zipcode_batch < self.min_miners_for_consensus:
            raise ValueError(f"miners_per_zipcode_batch ({self.miners_per_zipcode_batch}) must be >= min_miners_for_consensus ({self.min_miners_for_consensus})")
            
        # Clean up sources list
        self.enabled_sources = [s.strip().upper() for s in self.enabled_sources if s.strip()]
        
        # Validate sources
        valid_sources = ['ZILLOW_SOLD', 'ZILLOW', 'REDFIN', 'REALTOR_COM', 'HOMES_COM']
        for source in self.enabled_sources:
            if source not in valid_sources:
                raise ValueError(f"Invalid source: {source}. Valid sources: {valid_sources}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'data_api_url': self.data_api_url,
            'enabled_sources': self.enabled_sources,
            'zipcodes_per_batch': self.zipcodes_per_batch,
            'miners_per_zipcode_batch': self.miners_per_zipcode_batch,
            'batch_overlap_factor': self.batch_overlap_factor,
            'max_batches_per_cycle': self.max_batches_per_cycle,
            'consensus_confidence_threshold': self.consensus_confidence_threshold,
            'anomaly_detection_threshold': self.anomaly_detection_threshold,
            'min_miners_for_consensus': self.min_miners_for_consensus,
            'use_s3_consensus': self.use_s3_consensus,
            's3_upload_timeout_minutes': self.s3_upload_timeout_minutes,
            's3_completion_threshold': self.s3_completion_threshold,
            'assignment_timeout_hours': self.assignment_timeout_hours,
            'assignment_cycle_hours': self.assignment_cycle_hours,
            'expected_properties_per_zipcode': self.expected_properties_per_zipcode,
            'max_miners_per_coldkey': self.max_miners_per_coldkey,
            'min_different_coldkeys': self.min_different_coldkeys,
            'geographic_diversity_required': self.geographic_diversity_required,
            'enable_validator_spot_checks': self.enable_validator_spot_checks,
            'spot_check_sample_size': self.spot_check_sample_size,
            'spot_check_timeout_minutes': self.spot_check_timeout_minutes,
            'enable_behavioral_analysis': self.enable_behavioral_analysis,
            'synchronization_threshold_seconds': self.synchronization_threshold_seconds,
            'identical_content_penalty': self.identical_content_penalty,
            'enable_time_based_rewards': self.enable_time_based_rewards,
            'fast_response_bonus': self.fast_response_bonus,
            'medium_response_bonus': self.medium_response_bonus,
            'slow_response_penalty': self.slow_response_penalty,
            'enable_detailed_logging': self.enable_detailed_logging,
            'log_validation_details': self.log_validation_details,
            'log_s3_operations': self.log_s3_operations
        }

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for this configuration"""
        return {
            'DATA_API_URL': self.data_api_url,
            'ENABLED_DATA_SOURCES': ','.join(self.enabled_sources),
            'ZIPCODES_PER_BATCH': str(self.zipcodes_per_batch),
            'MINERS_PER_ZIPCODE_BATCH': str(self.miners_per_zipcode_batch),
            'BATCH_OVERLAP_FACTOR': str(self.batch_overlap_factor),
            'MAX_BATCHES_PER_CYCLE': str(self.max_batches_per_cycle),
            'CONSENSUS_CONFIDENCE_THRESHOLD': str(self.consensus_confidence_threshold),
            'ANOMALY_DETECTION_THRESHOLD': str(self.anomaly_detection_threshold),
            'MIN_MINERS_FOR_CONSENSUS': str(self.min_miners_for_consensus),
            'USE_S3_CONSENSUS': str(self.use_s3_consensus).lower(),
            'S3_UPLOAD_TIMEOUT_MINUTES': str(self.s3_upload_timeout_minutes),
            'S3_COMPLETION_THRESHOLD': str(self.s3_completion_threshold),
            'ASSIGNMENT_TIMEOUT_HOURS': str(self.assignment_timeout_hours),
            'ASSIGNMENT_CYCLE_HOURS': str(self.assignment_cycle_hours),
            'EXPECTED_PROPERTIES_PER_ZIPCODE': str(self.expected_properties_per_zipcode),
            'MAX_MINERS_PER_COLDKEY': str(self.max_miners_per_coldkey),
            'MIN_DIFFERENT_COLDKEYS': str(self.min_different_coldkeys),
            'GEOGRAPHIC_DIVERSITY_REQUIRED': str(self.geographic_diversity_required).lower(),
            'ENABLE_VALIDATOR_SPOT_CHECKS': str(self.enable_validator_spot_checks).lower(),
            'SPOT_CHECK_SAMPLE_SIZE': str(self.spot_check_sample_size),
            'SPOT_CHECK_TIMEOUT_MINUTES': str(self.spot_check_timeout_minutes),
            'ENABLE_BEHAVIORAL_ANALYSIS': str(self.enable_behavioral_analysis).lower(),
            'SYNC_THRESHOLD_SECONDS': str(self.synchronization_threshold_seconds),
            'IDENTICAL_CONTENT_PENALTY': str(self.identical_content_penalty),
            'ENABLE_TIME_BASED_REWARDS': str(self.enable_time_based_rewards).lower(),
            'FAST_RESPONSE_BONUS': str(self.fast_response_bonus),
            'MEDIUM_RESPONSE_BONUS': str(self.medium_response_bonus),
            'SLOW_RESPONSE_PENALTY': str(self.slow_response_penalty),
            'ENABLE_DETAILED_LOGGING': str(self.enable_detailed_logging).lower(),
            'LOG_VALIDATION_DETAILS': str(self.log_validation_details).lower(),
            'LOG_S3_OPERATIONS': str(self.log_s3_operations).lower()
        }


# Predefined configurations for different scenarios

# Mock Server Development Configuration
MOCK_SERVER_CONFIG = ZipcodeConsensusConfig(
    data_api_url='http://localhost:8000',
    enabled_sources=['ZILLOW_SOLD'],
    zipcodes_per_batch=5,
    miners_per_zipcode_batch=5,
    batch_overlap_factor=2,
    max_batches_per_cycle=10,
    consensus_confidence_threshold=0.5,
    anomaly_detection_threshold=0.4,
    min_miners_for_consensus=3,
    use_s3_consensus=False,  # Disable S3 for mock testing
    assignment_timeout_hours=1,
    assignment_cycle_hours=1,
    expected_properties_per_zipcode=30,
    enable_validator_spot_checks=False,
    enable_detailed_logging=True,
    log_validation_details=True
)

# Production Configuration with S3 Consensus
PRODUCTION_S3_CONSENSUS_CONFIG = ZipcodeConsensusConfig(
    data_api_url='https://api.resi-subnet.com',
    enabled_sources=['ZILLOW_SOLD'],
    zipcodes_per_batch=20,
    miners_per_zipcode_batch=10,
    batch_overlap_factor=2,
    max_batches_per_cycle=50,
    consensus_confidence_threshold=0.7,
    anomaly_detection_threshold=0.25,
    min_miners_for_consensus=6,
    use_s3_consensus=True,
    s3_upload_timeout_minutes=30,
    s3_completion_threshold=0.8,
    assignment_timeout_hours=4,
    assignment_cycle_hours=4,
    expected_properties_per_zipcode=50,
    max_miners_per_coldkey=1,
    min_different_coldkeys=5,
    enable_validator_spot_checks=False,
    enable_behavioral_analysis=True,
    enable_time_based_rewards=True,
    enable_detailed_logging=False,
    log_validation_details=False
)

# Testnet Configuration
# NOTE: Uses production data API even for testnet - only Bittensor network differs
TESTNET_CONFIG = ZipcodeConsensusConfig(
    data_api_url='https://api.resi-subnet.com',  # Production API required
    enabled_sources=['ZILLOW_SOLD'],
    zipcodes_per_batch=10,
    miners_per_zipcode_batch=7,
    batch_overlap_factor=2,
    max_batches_per_cycle=20,
    consensus_confidence_threshold=0.6,
    anomaly_detection_threshold=0.3,
    min_miners_for_consensus=4,
    use_s3_consensus=True,
    s3_upload_timeout_minutes=20,
    s3_completion_threshold=0.75,
    assignment_timeout_hours=2,
    assignment_cycle_hours=2,
    expected_properties_per_zipcode=40,
    max_miners_per_coldkey=1,
    min_different_coldkeys=3,
    enable_validator_spot_checks=True,  # Enable spot checks for testing
    spot_check_sample_size=3,
    enable_behavioral_analysis=True,
    enable_time_based_rewards=True,
    enable_detailed_logging=True,
    log_validation_details=True
)
