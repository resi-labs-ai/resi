#!/usr/bin/env python3
"""
S3 Parquet Analyzer for Subnet 46 (RESI)
=========================================

This script allows subnet owners to analyze parquet files from S3 storage
to spot-check miner submissions and detect potential exploitation.

Features:
- Download and analyze parquet files from S3 for specific miners
- Convert parquet data to readable JSON/CSV format
- Validate data quality and detect anomalies
- Generate reports for manual inspection
- Check for duplicate data, suspicious patterns, and data freshness

Usage:
    python tools/s3_parquet_analyzer.py --miner-hotkey 5Ey8ByeiAnqsML5KuYB3jnprQFVE25KAW9sr5HXA66YhvC3E --output-dir ./analysis
    
Requirements:
    - Valid validator wallet for S3 access
    - Network connection to S3 auth service
    - pandas, pyarrow, requests
"""

import os
import sys
import json
import time
import argparse
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import bittensor as bt
from common.data import DataSource


class S3ParquetAnalyzer:
    """Analyzes parquet files from S3 storage for miner data validation."""
    
    def __init__(self, wallet_name: str = None, wallet_hotkey: str = None, netuid: int = 46, 
                 admin_mode: bool = False, s3_access_key: str = None, s3_secret_key: str = None,
                 s3_bucket: str = None, s3_region: str = "us-east-1"):
        """
        Initialize the analyzer with wallet credentials or admin S3 access.
        
        Args:
            wallet_name: Validator wallet name (for validator mode)
            wallet_hotkey: Validator hotkey name (for validator mode)
            netuid: Network UID (46 for mainnet, 428 for testnet)
            admin_mode: Use direct S3 access instead of validator auth
            s3_access_key: S3 access key ID (for admin mode)
            s3_secret_key: S3 secret access key (for admin mode)
            s3_bucket: S3 bucket name (for admin mode)
            s3_region: S3 region (for admin mode)
        """
        self.netuid = netuid
        self.admin_mode = admin_mode
        
        # Configure S3 auth URL based on network (for validator mode)
        if netuid == 428:  # Testnet
            self.s3_auth_url = "https://api-staging.resilabs.ai"
            self.network_name = "testnet"
            self.default_bucket = s3_bucket or "resi-testnet-data"
        else:  # Mainnet
            self.s3_auth_url = "https://api.resilabs.ai"
            self.network_name = "mainnet"
            self.default_bucket = s3_bucket or "resi-mainnet-data"
        
        # Initialize admin S3 client if in admin mode
        self.s3_client = None
        if admin_mode:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=s3_access_key,
                    aws_secret_access_key=s3_secret_key,
                    region_name=s3_region
                )
                self.s3_bucket = s3_bucket or self.default_bucket
                
                # Test S3 connection
                self.s3_client.head_bucket(Bucket=self.s3_bucket)
                bt.logging.info(f"Initialized admin S3 access to bucket: {self.s3_bucket}")
                
            except (ClientError, NoCredentialsError) as e:
                bt.logging.error(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
                self.admin_mode = False
        
        # Initialize wallet if provided and not in admin mode
        self.wallet = None
        if not admin_mode and wallet_name and wallet_hotkey:
            try:
                config = bt.config()
                config.wallet.name = wallet_name
                config.wallet.hotkey = wallet_hotkey
                if netuid == 428:
                    config.subtensor.network = "test"
                self.wallet = bt.wallet(config=config)
                bt.logging.info(f"Initialized wallet: {self.wallet.hotkey.ss58_address}")
            except Exception as e:
                bt.logging.error(f"Failed to initialize wallet: {e}")
                self.wallet = None
    
    def get_miner_s3_files(self, miner_hotkey: str) -> Optional[List[Dict]]:
        """
        Get list of S3 files for a specific miner.
        
        Args:
            miner_hotkey: The miner's hotkey address
            
        Returns:
            List of file metadata dictionaries or None if failed
        """
        if self.admin_mode:
            return self._get_miner_s3_files_admin(miner_hotkey)
        else:
            return self._get_miner_s3_files_validator(miner_hotkey)
    
    def _get_miner_s3_files_admin(self, miner_hotkey: str) -> Optional[List[Dict]]:
        """Get S3 files using direct admin access."""
        if not self.s3_client:
            bt.logging.error("No S3 client configured for admin access")
            return None
            
        try:
            # List objects with miner hotkey prefix
            prefix = f"data/hotkey={miner_hotkey}/"
            
            bt.logging.info(f"Listing S3 objects with prefix: {prefix}")
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            files = []
            
            for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        file_info = {
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'is_parquet': obj['Key'].endswith('.parquet')
                        }
                        
                        # Extract additional metadata from filename
                        if file_info['is_parquet']:
                            file_info.update(self._extract_parquet_metadata(obj['Key']))
                        
                        files.append(file_info)
            
            bt.logging.info(f"Found {len(files)} files, {sum(1 for f in files if f['is_parquet'])} parquet files")
            return files
            
        except ClientError as e:
            bt.logging.error(f"Error listing S3 objects for {miner_hotkey}: {str(e)}")
            return None
    
    def _get_miner_s3_files_validator(self, miner_hotkey: str) -> Optional[List[Dict]]:
        """Get S3 files using validator authentication."""
        if not self.wallet:
            bt.logging.error("No wallet configured for S3 access")
            return None
            
        try:
            # Create authentication payload
            hotkey = self.wallet.hotkey.ss58_address
            timestamp = int(time.time())
            commitment = f"s3:validator:miner:{miner_hotkey}:{timestamp}"
            signature = self.wallet.hotkey.sign(commitment.encode())
            signature_hex = signature.hex()

            payload = {
                "hotkey": hotkey,
                "timestamp": timestamp,
                "signature": signature_hex,
                "miner_hotkey": miner_hotkey
            }

            # Get miner-specific S3 access
            response = requests.post(
                f"{self.s3_auth_url}/get-miner-specific-access",
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                bt.logging.error(f"Failed to get S3 access for {miner_hotkey}: {response.status_code}")
                bt.logging.error(f"Response: {response.text}")
                return None

            access_data = response.json()
            miner_url = access_data.get('miner_url', '')
            
            if not miner_url:
                bt.logging.error(f"No miner URL provided for {miner_hotkey}")
                return None

            bt.logging.info(f"Got S3 access URL for {miner_hotkey}")
            
            # Parse S3 file list
            xml_response = requests.get(miner_url, timeout=60)
            
            if xml_response.status_code != 200:
                bt.logging.error(f"Failed to get S3 file list: {xml_response.status_code}")
                return None

            return self._parse_s3_file_list(xml_response.text)
            
        except Exception as e:
            bt.logging.error(f"Error getting S3 files for {miner_hotkey}: {str(e)}")
            return None
    
    def _parse_s3_file_list(self, xml_content: str) -> List[Dict]:
        """Parse S3 XML response to extract file metadata."""
        files = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Handle different XML namespaces
            ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
            contents = root.findall('.//s3:Contents', ns)
            
            if not contents:
                # Try without namespace
                contents = root.findall('.//Contents')
            
            for content in contents:
                key_elem = content.find('.//Key') or content.find('.//s3:Key', ns)
                size_elem = content.find('.//Size') or content.find('.//s3:Size', ns)
                modified_elem = content.find('.//LastModified') or content.find('.//s3:LastModified', ns)
                
                if key_elem is not None:
                    file_info = {
                        'key': key_elem.text,
                        'size': int(size_elem.text) if size_elem is not None else 0,
                        'last_modified': modified_elem.text if modified_elem is not None else '',
                        'is_parquet': key_elem.text.endswith('.parquet')
                    }
                    
                    # Extract additional metadata from filename
                    if file_info['is_parquet']:
                        file_info.update(self._extract_parquet_metadata(key_elem.text))
                    
                    files.append(file_info)
            
            bt.logging.info(f"Found {len(files)} files, {sum(1 for f in files if f['is_parquet'])} parquet files")
            return files
            
        except Exception as e:
            bt.logging.error(f"Error parsing S3 file list: {str(e)}")
            return []
    
    def _extract_parquet_metadata(self, file_key: str) -> Dict:
        """Extract metadata from parquet filename."""
        metadata = {
            'job_id': None,
            'timestamp': None,
            'record_count': None,
            'filename': os.path.basename(file_key)
        }
        
        try:
            # Extract job_id from path: job_id=12345/data_timestamp_count.parquet
            if 'job_id=' in file_key:
                job_part = file_key.split('job_id=')[1].split('/')[0]
                metadata['job_id'] = job_part
            
            # Extract timestamp and record count from filename
            # Format: data_YYYYMMDD_HHMMSS_count.parquet
            filename = os.path.basename(file_key)
            if filename.startswith('data_') and filename.endswith('.parquet'):
                parts = filename[5:-8].split('_')  # Remove 'data_' and '.parquet'
                if len(parts) >= 3:
                    date_part = parts[0]
                    time_part = parts[1]
                    count_part = parts[2]
                    
                    # Parse timestamp
                    timestamp_str = f"{date_part}_{time_part}"
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        metadata['timestamp'] = timestamp.isoformat()
                    except ValueError:
                        pass
                    
                    # Parse record count
                    try:
                        metadata['record_count'] = int(count_part)
                    except ValueError:
                        pass
                        
        except Exception as e:
            bt.logging.debug(f"Error extracting parquet metadata from {file_key}: {e}")
        
        return metadata
    
    def download_and_analyze_parquet(self, miner_hotkey: str, file_key: str, 
                                   output_dir: str = "./analysis") -> Optional[Dict]:
        """
        Download and analyze a specific parquet file.
        
        Args:
            miner_hotkey: The miner's hotkey
            file_key: S3 file key to download
            output_dir: Directory to save analysis results
            
        Returns:
            Analysis results dictionary
        """
        if self.admin_mode:
            return self._download_and_analyze_parquet_admin(miner_hotkey, file_key, output_dir)
        else:
            return self._download_and_analyze_parquet_validator(miner_hotkey, file_key, output_dir)
    
    def _download_and_analyze_parquet_admin(self, miner_hotkey: str, file_key: str, 
                                          output_dir: str = "./analysis") -> Optional[Dict]:
        """Download and analyze parquet using direct S3 access."""
        if not self.s3_client:
            bt.logging.error("No S3 client configured for admin access")
            return None
            
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Download file directly from S3
            local_filename = os.path.basename(file_key)
            local_path = os.path.join(output_dir, local_filename)
            
            bt.logging.info(f"Downloading {file_key} from S3...")
            self.s3_client.download_file(self.s3_bucket, file_key, local_path)
            
            bt.logging.info(f"Downloaded to {local_path}")
            
            # Analyze the parquet file
            return self._analyze_parquet_file(local_path, miner_hotkey, file_key, output_dir)
            
        except ClientError as e:
            bt.logging.error(f"Error downloading parquet from S3: {str(e)}")
            return None
        except Exception as e:
            bt.logging.error(f"Error downloading/analyzing parquet: {str(e)}")
            return None
    
    def _download_and_analyze_parquet_validator(self, miner_hotkey: str, file_key: str, 
                                              output_dir: str = "./analysis") -> Optional[Dict]:
        """Download and analyze parquet using validator authentication."""
        if not self.wallet:
            bt.logging.error("No wallet configured for S3 access")
            return None
            
        try:
            # Get presigned URL for the file
            hotkey = self.wallet.hotkey.ss58_address
            timestamp = int(time.time())
            commitment = f"s3:validator:file:{miner_hotkey}:{file_key}:{timestamp}"
            signature = self.wallet.hotkey.sign(commitment.encode())
            signature_hex = signature.hex()

            payload = {
                "hotkey": hotkey,
                "timestamp": timestamp,
                "signature": signature_hex,
                "miner_hotkey": miner_hotkey,
                "file_key": file_key
            }

            # Get presigned URL for specific file
            response = requests.post(
                f"{self.s3_auth_url}/get-file-access",
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                bt.logging.error(f"Failed to get file access: {response.status_code}")
                return None

            file_url = response.json().get('file_url')
            if not file_url:
                bt.logging.error("No file URL provided")
                return None

            # Download the parquet file
            bt.logging.info(f"Downloading {file_key}...")
            file_response = requests.get(file_url, timeout=120)
            
            if file_response.status_code != 200:
                bt.logging.error(f"Failed to download file: {file_response.status_code}")
                return None

            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Save parquet file locally
            local_filename = os.path.basename(file_key)
            local_path = os.path.join(output_dir, local_filename)
            
            with open(local_path, 'wb') as f:
                f.write(file_response.content)
            
            bt.logging.info(f"Downloaded to {local_path}")
            
            # Analyze the parquet file
            return self._analyze_parquet_file(local_path, miner_hotkey, file_key, output_dir)
            
        except Exception as e:
            bt.logging.error(f"Error downloading/analyzing parquet: {str(e)}")
            return None
    
    def _analyze_parquet_file(self, file_path: str, miner_hotkey: str, 
                            file_key: str, output_dir: str) -> Dict:
        """Analyze a parquet file and generate reports."""
        
        try:
            # Read parquet file
            df = pd.read_parquet(file_path)
            
            bt.logging.info(f"Loaded parquet with {len(df)} rows and {len(df.columns)} columns")
            
            # Basic analysis
            analysis = {
                'miner_hotkey': miner_hotkey,
                'file_key': file_key,
                'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
                'total_records': len(df),
                'columns': list(df.columns),
                'data_types': df.dtypes.to_dict(),
                'null_counts': df.isnull().sum().to_dict(),
                'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Data quality checks
            analysis['quality_checks'] = self._perform_quality_checks(df)
            
            # Sample data (first 10 rows)
            analysis['sample_data'] = df.head(10).to_dict('records')
            
            # Save readable formats
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Save as JSON
            json_path = os.path.join(output_dir, f"{base_name}_readable.json")
            df.to_json(json_path, orient='records', indent=2, date_format='iso')
            
            # Save as CSV
            csv_path = os.path.join(output_dir, f"{base_name}_readable.csv")
            df.to_csv(csv_path, index=False)
            
            # Save analysis report
            report_path = os.path.join(output_dir, f"{base_name}_analysis.json")
            with open(report_path, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            bt.logging.success(f"Analysis complete. Files saved to {output_dir}")
            bt.logging.info(f"Readable data: {json_path}, {csv_path}")
            bt.logging.info(f"Analysis report: {report_path}")
            
            return analysis
            
        except Exception as e:
            bt.logging.error(f"Error analyzing parquet file: {str(e)}")
            return {'error': str(e)}
    
    def _perform_quality_checks(self, df: pd.DataFrame) -> Dict:
        """Perform data quality checks on the DataFrame."""
        
        checks = {}
        
        try:
            # Check for duplicates
            duplicate_count = df.duplicated().sum()
            checks['duplicate_rows'] = int(duplicate_count)
            checks['duplicate_percentage'] = float(duplicate_count / len(df) * 100) if len(df) > 0 else 0
            
            # Check for suspicious patterns
            if 'uri' in df.columns:
                unique_uris = df['uri'].nunique()
                checks['unique_uris'] = int(unique_uris)
                checks['uri_reuse_ratio'] = float(len(df) / unique_uris) if unique_uris > 0 else 0
            
            # Check data freshness
            if 'datetime' in df.columns:
                try:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    now = datetime.now()
                    age_hours = (now - df['datetime'].max()).total_seconds() / 3600
                    checks['data_age_hours'] = float(age_hours)
                    checks['data_age_days'] = float(age_hours / 24)
                    
                    # Check time distribution
                    time_span_hours = (df['datetime'].max() - df['datetime'].min()).total_seconds() / 3600
                    checks['time_span_hours'] = float(time_span_hours)
                except Exception as e:
                    checks['datetime_parse_error'] = str(e)
            
            # Check for real estate specific fields
            if 'zpid' in df.columns:
                unique_properties = df['zpid'].nunique()
                checks['unique_properties'] = int(unique_properties)
                checks['property_reuse_ratio'] = float(len(df) / unique_properties) if unique_properties > 0 else 0
            
            if 'price' in df.columns:
                price_stats = df['price'].describe()
                checks['price_stats'] = {
                    'mean': float(price_stats['mean']),
                    'median': float(df['price'].median()),
                    'min': float(price_stats['min']),
                    'max': float(price_stats['max']),
                    'std': float(price_stats['std'])
                }
                
                # Check for suspicious price patterns
                zero_prices = (df['price'] == 0).sum()
                checks['zero_price_count'] = int(zero_prices)
                
                # Check for repeated prices (potential fake data)
                price_counts = df['price'].value_counts()
                most_common_price_count = price_counts.iloc[0] if len(price_counts) > 0 else 0
                checks['most_repeated_price_count'] = int(most_common_price_count)
                checks['price_repetition_ratio'] = float(most_common_price_count / len(df)) if len(df) > 0 else 0
            
            # Geographic distribution checks
            if 'zip_code' in df.columns:
                unique_zipcodes = df['zip_code'].nunique()
                checks['unique_zipcodes'] = int(unique_zipcodes)
                checks['zipcode_distribution'] = df['zip_code'].value_counts().head(10).to_dict()
            
            # Content size validation
            if 'content_size_bytes' in df.columns:
                size_stats = df['content_size_bytes'].describe()
                checks['content_size_stats'] = {
                    'mean': float(size_stats['mean']),
                    'median': float(df['content_size_bytes'].median()),
                    'min': float(size_stats['min']),
                    'max': float(size_stats['max'])
                }
                
                # Check for suspiciously uniform sizes
                size_counts = df['content_size_bytes'].value_counts()
                most_common_size_count = size_counts.iloc[0] if len(size_counts) > 0 else 0
                checks['most_repeated_size_count'] = int(most_common_size_count)
                checks['size_uniformity_ratio'] = float(most_common_size_count / len(df)) if len(df) > 0 else 0
                
        except Exception as e:
            checks['quality_check_error'] = str(e)
        
        return checks
    
    def generate_miner_report(self, miner_hotkey: str, output_dir: str = "./analysis") -> Dict:
        """
        Generate a comprehensive report for a miner.
        
        Args:
            miner_hotkey: The miner's hotkey
            output_dir: Directory to save reports
            
        Returns:
            Comprehensive miner analysis report
        """
        
        bt.logging.info(f"Generating report for miner: {miner_hotkey}")
        
        # Get all S3 files for the miner
        files = self.get_miner_s3_files(miner_hotkey)
        if not files:
            return {'error': 'Could not access miner S3 data'}
        
        # Filter parquet files
        parquet_files = [f for f in files if f.get('is_parquet', False)]
        
        if not parquet_files:
            return {'error': 'No parquet files found for miner'}
        
        bt.logging.info(f"Found {len(parquet_files)} parquet files")
        
        # Analyze recent files (last 7 days)
        recent_files = []
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for file_info in parquet_files:
            if file_info.get('timestamp'):
                try:
                    file_date = datetime.fromisoformat(file_info['timestamp'].replace('Z', '+00:00'))
                    if file_date.replace(tzinfo=None) > cutoff_date:
                        recent_files.append(file_info)
                except Exception:
                    pass
        
        if not recent_files:
            # If no recent files, take the 5 most recent
            recent_files = sorted(parquet_files, 
                                key=lambda x: x.get('last_modified', ''), 
                                reverse=True)[:5]
        
        bt.logging.info(f"Analyzing {len(recent_files)} recent files")
        
        # Create miner-specific output directory
        miner_output_dir = os.path.join(output_dir, f"miner_{miner_hotkey[:8]}")
        os.makedirs(miner_output_dir, exist_ok=True)
        
        # Analyze each recent file
        file_analyses = []
        for file_info in recent_files[:10]:  # Limit to 10 files max
            bt.logging.info(f"Analyzing {file_info['key']}")
            analysis = self.download_and_analyze_parquet(
                miner_hotkey, file_info['key'], miner_output_dir
            )
            if analysis:
                file_analyses.append(analysis)
        
        # Generate summary report
        report = {
            'miner_hotkey': miner_hotkey,
            'network': self.network_name,
            'analysis_timestamp': datetime.now().isoformat(),
            'total_files': len(files),
            'parquet_files': len(parquet_files),
            'recent_files_analyzed': len(file_analyses),
            'file_analyses': file_analyses,
            'summary_stats': self._generate_summary_stats(file_analyses),
            'red_flags': self._identify_red_flags(file_analyses)
        }
        
        # Save comprehensive report
        report_path = os.path.join(miner_output_dir, "miner_analysis_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        bt.logging.success(f"Miner report saved to: {report_path}")
        return report
    
    def _generate_summary_stats(self, file_analyses: List[Dict]) -> Dict:
        """Generate summary statistics across all analyzed files."""
        
        if not file_analyses:
            return {}
        
        stats = {
            'total_records': sum(a.get('total_records', 0) for a in file_analyses),
            'total_size_mb': sum(a.get('file_size_mb', 0) for a in file_analyses),
            'avg_records_per_file': 0,
            'duplicate_percentage_avg': 0,
            'unique_properties_total': 0
        }
        
        valid_analyses = [a for a in file_analyses if 'error' not in a]
        
        if valid_analyses:
            stats['avg_records_per_file'] = stats['total_records'] / len(valid_analyses)
            
            # Average duplicate percentage
            dup_percentages = [
                a.get('quality_checks', {}).get('duplicate_percentage', 0) 
                for a in valid_analyses
            ]
            stats['duplicate_percentage_avg'] = sum(dup_percentages) / len(dup_percentages)
            
            # Unique properties across all files
            all_unique_props = [
                a.get('quality_checks', {}).get('unique_properties', 0) 
                for a in valid_analyses
            ]
            stats['unique_properties_total'] = sum(all_unique_props)
        
        return stats
    
    def _identify_red_flags(self, file_analyses: List[Dict]) -> List[str]:
        """Identify potential red flags indicating suspicious activity."""
        
        red_flags = []
        
        for analysis in file_analyses:
            if 'error' in analysis:
                continue
                
            quality = analysis.get('quality_checks', {})
            
            # High duplicate percentage
            dup_pct = quality.get('duplicate_percentage', 0)
            if dup_pct > 50:
                red_flags.append(f"High duplicate data: {dup_pct:.1f}% duplicates in {analysis.get('file_key', 'unknown')}")
            
            # Suspicious price patterns
            price_rep_ratio = quality.get('price_repetition_ratio', 0)
            if price_rep_ratio > 0.3:
                red_flags.append(f"Suspicious price repetition: {price_rep_ratio:.1%} same price in {analysis.get('file_key', 'unknown')}")
            
            # Very old data
            data_age_days = quality.get('data_age_days', 0)
            if data_age_days > 30:
                red_flags.append(f"Stale data: {data_age_days:.1f} days old in {analysis.get('file_key', 'unknown')}")
            
            # Uniform content sizes (potential fake data)
            size_uniformity = quality.get('size_uniformity_ratio', 0)
            if size_uniformity > 0.8:
                red_flags.append(f"Uniform content sizes: {size_uniformity:.1%} same size in {analysis.get('file_key', 'unknown')}")
            
            # Too many zero prices
            total_records = analysis.get('total_records', 0)
            zero_prices = quality.get('zero_price_count', 0)
            if total_records > 0 and zero_prices / total_records > 0.1:
                red_flags.append(f"Many zero prices: {zero_prices}/{total_records} in {analysis.get('file_key', 'unknown')}")
        
        return red_flags


def main():
    """Main CLI interface."""
    
    parser = argparse.ArgumentParser(description="Analyze S3 parquet files for Subnet 46 miners")
    parser.add_argument("--miner-hotkey", required=True, help="Miner hotkey to analyze")
    
    # Validator mode arguments
    parser.add_argument("--wallet-name", help="Validator wallet name")
    parser.add_argument("--wallet-hotkey", help="Validator hotkey name")
    
    # Admin mode arguments
    parser.add_argument("--admin-mode", action="store_true", help="Use admin S3 access instead of validator auth")
    parser.add_argument("--s3-access-key", help="S3 access key ID (for admin mode)")
    parser.add_argument("--s3-secret-key", help="S3 secret access key (for admin mode)")
    parser.add_argument("--s3-bucket", help="S3 bucket name (for admin mode)")
    parser.add_argument("--s3-region", default="us-east-1", help="S3 region (for admin mode)")
    
    # Common arguments
    parser.add_argument("--netuid", type=int, default=46, help="Network UID (46=mainnet, 428=testnet)")
    parser.add_argument("--output-dir", default="./analysis", help="Output directory for analysis")
    parser.add_argument("--file-key", help="Specific file to analyze (optional)")
    parser.add_argument("--list-files", action="store_true", help="Just list files without downloading")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Validate admin mode arguments
    if args.admin_mode:
        if not args.s3_access_key or not args.s3_secret_key:
            print("Error: --admin-mode requires --s3-access-key and --s3-secret-key")
            return 1
        
        # Check for environment variables if not provided
        s3_access_key = args.s3_access_key or os.getenv('S3_ACCESS_KEY')
        s3_secret_key = args.s3_secret_key or os.getenv('S3_SECRET_KEY')
        s3_bucket = args.s3_bucket or os.getenv('S3_BUCKET')
        
        if not s3_access_key or not s3_secret_key:
            print("Error: S3 credentials not provided. Use --s3-access-key/--s3-secret-key or set S3_ACCESS_KEY/S3_SECRET_KEY environment variables")
            return 1
    
    # Configure logging
    if args.verbose:
        bt.logging.set_trace(True)
    else:
        bt.logging.set_info(True)
    
    # Initialize analyzer
    if args.admin_mode:
        analyzer = S3ParquetAnalyzer(
            netuid=args.netuid,
            admin_mode=True,
            s3_access_key=s3_access_key,
            s3_secret_key=s3_secret_key,
            s3_bucket=s3_bucket,
            s3_region=args.s3_region
        )
    else:
        analyzer = S3ParquetAnalyzer(
            wallet_name=args.wallet_name,
            wallet_hotkey=args.wallet_hotkey,
            netuid=args.netuid
        )
    
    if args.list_files:
        # Just list files
        files = analyzer.get_miner_s3_files(args.miner_hotkey)
        if files:
            print(f"\nFound {len(files)} files for miner {args.miner_hotkey}:")
            parquet_files = [f for f in files if f.get('is_parquet')]
            print(f"Parquet files: {len(parquet_files)}")
            
            for f in parquet_files:
                print(f"  {f['key']} ({f['size']} bytes, {f.get('record_count', '?')} records)")
        else:
            print("No files found or access denied")
            
    elif args.file_key:
        # Analyze specific file
        result = analyzer.download_and_analyze_parquet(
            args.miner_hotkey, args.file_key, args.output_dir
        )
        if result:
            print(f"\nAnalysis complete. Results saved to {args.output_dir}")
            if 'red_flags' in result:
                print(f"Red flags: {result['red_flags']}")
        else:
            print("Analysis failed")
            
    else:
        # Full miner analysis
        report = analyzer.generate_miner_report(args.miner_hotkey, args.output_dir)
        
        if 'error' in report:
            print(f"Error: {report['error']}")
            return 1
        
        print(f"\n=== MINER ANALYSIS REPORT ===")
        print(f"Miner: {args.miner_hotkey}")
        print(f"Network: {report['network']}")
        print(f"Access Mode: {'Admin S3' if args.admin_mode else 'Validator Auth'}")
        print(f"Total files: {report['total_files']}")
        print(f"Parquet files: {report['parquet_files']}")
        print(f"Files analyzed: {report['recent_files_analyzed']}")
        
        summary = report.get('summary_stats', {})
        print(f"\nSummary:")
        print(f"  Total records: {summary.get('total_records', 0):,}")
        print(f"  Total size: {summary.get('total_size_mb', 0):.2f} MB")
        print(f"  Avg records/file: {summary.get('avg_records_per_file', 0):.0f}")
        print(f"  Avg duplicates: {summary.get('duplicate_percentage_avg', 0):.1f}%")
        
        red_flags = report.get('red_flags', [])
        if red_flags:
            print(f"\n⚠️  RED FLAGS DETECTED ({len(red_flags)}):")
            for flag in red_flags:
                print(f"  • {flag}")
        else:
            print(f"\n✅ No red flags detected")
        
        print(f"\nDetailed report saved to: {args.output_dir}")
    
    return 0


if __name__ == "__main__":
    exit(main())
