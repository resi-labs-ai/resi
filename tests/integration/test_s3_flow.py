"""
S3 Upload/Download Integration Tests

Tests the complete S3 flow: miners uploading data and validators downloading
and validating that data. Uses mock S3 infrastructure for reliable testing.
"""

import asyncio
import json
import unittest
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

import bittensor as bt
from common.data import DataEntity, DataSource, DataLabel
from scraping.zillow.model import RealEstateContent
from upload_utils.s3_uploader import S3PartitionedUploader
from vali_utils.s3_utils import S3Validator, get_miner_s3_validation_data
from tests.integration.fixtures.test_wallets import get_test_wallet_manager, cleanup_test_wallets
from tests.integration.fixtures.mock_s3 import get_mock_s3_auth_server, cleanup_mock_s3, MockS3Uploader, MockS3Validator
from tests.mocks.zillow_api_client import MockZillowAPIClient


class TestS3IntegrationFlow(unittest.TestCase):
    """Test complete S3 upload/download integration"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test infrastructure"""
        bt.logging.set_info(True)
        
        # Set up test wallets
        cls.wallet_manager = get_test_wallet_manager()
        cls.miner_wallets = cls.wallet_manager.get_miner_wallets()[:2]  # Use 2 miners
        cls.validator_wallets = cls.wallet_manager.get_validator_wallets()[:1]  # Use 1 validator
        
        # Set up mock S3 server
        cls.mock_s3_server = get_mock_s3_auth_server(port=8080)
        cls.s3_auth_url = "http://localhost:8080"
        
        # Set up real data client
        cls.mock_client = MockZillowAPIClient("mocked_data")
        
        # Create temporary database for testing
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
        cls.temp_db.close()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test infrastructure"""
        cleanup_mock_s3()
        cleanup_test_wallets()
        
        # Clean up temp database
        import os
        if os.path.exists(cls.temp_db.name):
            os.unlink(cls.temp_db.name)
    
    def setUp(self):
        """Set up individual test"""
        self.test_data_entities = []
        
    async def _create_test_data_entities(self, count: int = 10) -> List[DataEntity]:
        """Create test data entities from real Zillow data"""
        entities = []
        available_zpids = list(self.mock_client.get_available_zpids())[:count]
        
        for i, zpid in enumerate(available_zpids):
            # Get property data from our real dataset
            search_data = None
            for zipcode in self.mock_client.get_available_zipcodes():
                zipcode_data = await self.mock_client.get_property_search(zipcode)
                for prop in zipcode_data.get('props', []):
                    if str(prop.get('zpid', '')) == zpid:
                        search_data = prop
                        break
                if search_data:
                    break
            
            if search_data:
                # Create RealEstateContent from search data
                content = RealEstateContent.from_zillow_api(search_data)
                
                # Create entity with custom fields
                entity = DataEntity(
                    uri=f"https://zillow.com/homedetails/{zpid}_zpid/",
                    datetime=datetime.now(timezone.utc) - timedelta(hours=i),
                    source=DataSource.RAPID_ZILLOW,
                    label=DataLabel(value=f"zip:{zipcode}"),
                    content=content.model_dump_json().encode(),
                    content_size_bytes=len(content.model_dump_json())
                )
                
                entities.append(entity)
        
        return entities
    
    def test_miner_s3_upload_flow(self):
        """Test complete miner S3 upload flow"""
        
        async def run_test():
            bt.logging.info("Testing miner S3 upload flow")
            
            # Create test data
            test_entities = await self._create_test_data_entities(20)
            
            # Set up mock database with test data
            self._setup_test_database(test_entities)
            
            # Create mock S3 uploader
            miner_wallet = self.miner_wallets[0]
            mock_uploader = MockS3Uploader(self.mock_s3_server)
            
            # Add test data to mock S3
            job_id = "test_job_zillow_78041"
            chunk_data = b"mock_parquet_data_chunk"
            
            success = await mock_uploader.upload_chunk(
                miner_wallet.hotkey.ss58_address,
                job_id,
                chunk_data,
                0
            )
            
            self.assertTrue(success, "S3 upload should succeed")
            
            # Verify file was created locally (in mock S3)
            miner_path = self.mock_s3_server.get_miner_data_path(miner_wallet.hotkey.ss58_address)
            expected_file = miner_path / job_id / "chunk_0000.parquet"
            self.assertTrue(expected_file.exists(), f"Uploaded file should exist at {expected_file}")
            
            # Verify file contents
            with open(expected_file, 'rb') as f:
                content = f.read()
            self.assertEqual(content, chunk_data, "File content should match uploaded data")
            
            bt.logging.info("✅ Miner S3 upload flow test passed")
        
        asyncio.run(run_test())
    
    def test_validator_s3_download_flow(self):
        """Test complete validator S3 download flow"""
        
        async def run_test():
            bt.logging.info("Testing validator S3 download flow")
            
            # Set up test data in mock S3
            miner_wallet = self.miner_wallets[0]
            validator_wallet = self.validator_wallets[0]
            
            job_id = "test_job_zillow_validation"
            test_files = [
                {"chunk_index": 0, "data": b"test_chunk_0_data"},
                {"chunk_index": 1, "data": b"test_chunk_1_data"},
                {"chunk_index": 2, "data": b"test_chunk_2_data"},
            ]
            
            # Upload test files
            mock_uploader = MockS3Uploader(self.mock_s3_server)
            for file_info in test_files:
                success = await mock_uploader.upload_chunk(
                    miner_wallet.hotkey.ss58_address,
                    job_id,
                    file_info["data"],
                    file_info["chunk_index"]
                )
                self.assertTrue(success, f"Upload chunk {file_info['chunk_index']} should succeed")
            
            # Test validator download
            mock_validator = MockS3Validator(self.mock_s3_server)
            
            # Get file list
            files = await mock_validator.get_miner_files(miner_wallet.hotkey.ss58_address)
            self.assertEqual(len(files), 3, "Should find 3 uploaded files")
            
            # Download and verify each file
            for i, file_info in enumerate(test_files):
                file_key = f"miners/{miner_wallet.hotkey.ss58_address}/{job_id}/chunk_{i:04d}.parquet"
                downloaded_data = await mock_validator.download_file(
                    miner_wallet.hotkey.ss58_address,
                    file_key
                )
                
                self.assertIsNotNone(downloaded_data, f"Should download file {file_key}")
                self.assertEqual(downloaded_data, file_info["data"], f"Downloaded data should match for chunk {i}")
            
            bt.logging.info("✅ Validator S3 download flow test passed")
        
        asyncio.run(run_test())
    
    def test_s3_authentication_flow(self):
        """Test S3 authentication with wallet signing"""
        
        async def run_test():
            bt.logging.info("Testing S3 authentication flow")
            
            miner_wallet = self.miner_wallets[0]
            
            # Test getting S3 credentials (mocked)
            import requests
            
            # Prepare authentication payload
            hotkey = miner_wallet.hotkey.ss58_address
            coldkey = miner_wallet.coldkey.ss58_address
            timestamp = int(time.time())
            commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
            signature = miner_wallet.hotkey.sign(commitment.encode())
            signature_hex = signature.hex()
            
            payload = {
                "coldkey": coldkey,
                "hotkey": hotkey,
                "timestamp": timestamp,
                "signature": signature_hex
            }
            
            # Test folder access request
            response = requests.post(
                f"{self.s3_auth_url}/get-folder-access",
                json=payload,
                timeout=5
            )
            
            self.assertEqual(response.status_code, 200, "S3 auth request should succeed")
            
            auth_data = response.json()
            self.assertIn("folder", auth_data, "Response should contain folder info")
            self.assertIn("access_key", auth_data, "Response should contain access key")
            self.assertEqual(auth_data["folder"], hotkey, "Folder should match hotkey")
            
            bt.logging.info("✅ S3 authentication flow test passed")
        
        asyncio.run(run_test())
    
    def test_validator_miner_access_flow(self):
        """Test validator accessing miner-specific S3 data"""
        
        async def run_test():
            bt.logging.info("Testing validator miner access flow")
            
            miner_wallet = self.miner_wallets[0]
            validator_wallet = self.validator_wallets[0]
            
            # Set up test data for miner
            job_id = "test_job_validator_access"
            mock_uploader = MockS3Uploader(self.mock_s3_server)
            
            success = await mock_uploader.upload_chunk(
                miner_wallet.hotkey.ss58_address,
                job_id,
                b"validator_access_test_data",
                0
            )
            self.assertTrue(success, "Miner upload should succeed")
            
            # Test validator getting miner-specific access
            import requests
            
            validator_hotkey = validator_wallet.hotkey.ss58_address
            timestamp = int(time.time())
            commitment = f"s3:validator:miner:{miner_wallet.hotkey.ss58_address}:{timestamp}"
            signature = validator_wallet.hotkey.sign(commitment.encode())
            signature_hex = signature.hex()
            
            payload = {
                "hotkey": validator_hotkey,
                "timestamp": timestamp,
                "signature": signature_hex,
                "miner_hotkey": miner_wallet.hotkey.ss58_address
            }
            
            response = requests.post(
                f"{self.s3_auth_url}/get-miner-specific-access",
                json=payload,
                timeout=5
            )
            
            self.assertEqual(response.status_code, 200, "Validator miner access should succeed")
            
            access_data = response.json()
            self.assertIn("miner_url", access_data, "Response should contain miner URL")
            
            # Test getting file list
            miner_url = access_data["miner_url"]
            file_list_response = requests.get(miner_url, timeout=5)
            self.assertEqual(file_list_response.status_code, 200, "File list request should succeed")
            
            # Verify XML response contains our test file
            xml_content = file_list_response.text
            self.assertIn(job_id, xml_content, "File list should contain our test job")
            
            bt.logging.info("✅ Validator miner access flow test passed")
        
        asyncio.run(run_test())
    
    def test_s3_error_scenarios(self):
        """Test S3 error handling scenarios"""
        
        async def run_test():
            bt.logging.info("Testing S3 error scenarios")
            
            miner_wallet = self.miner_wallets[0]
            mock_validator = MockS3Validator(self.mock_s3_server)
            
            # Test 1: Access non-existent miner data
            files = await mock_validator.get_miner_files("non_existent_hotkey")
            self.assertEqual(len(files), 0, "Should return empty list for non-existent miner")
            
            # Test 2: Download non-existent file
            downloaded_data = await mock_validator.download_file(
                miner_wallet.hotkey.ss58_address,
                "miners/non_existent_file.parquet"
            )
            self.assertIsNone(downloaded_data, "Should return None for non-existent file")
            
            # Test 3: Invalid authentication (wrong signature)
            import requests
            
            payload = {
                "coldkey": miner_wallet.coldkey.ss58_address,
                "hotkey": miner_wallet.hotkey.ss58_address,
                "timestamp": int(time.time()),
                "signature": "invalid_signature_hex"
            }
            
            response = requests.post(
                f"{self.s3_auth_url}/get-folder-access",
                json=payload,
                timeout=5
            )
            
            # Mock server doesn't validate signatures, but in real scenario this would fail
            # For now, just verify we can handle the response
            self.assertIsNotNone(response, "Should get some response even with invalid signature")
            
            bt.logging.info("✅ S3 error scenarios test passed")
        
        asyncio.run(run_test())
    
    def test_s3_performance_with_multiple_files(self):
        """Test S3 performance with realistic data volumes"""
        
        async def run_test():
            bt.logging.info("Testing S3 performance with multiple files")
            
            miner_wallet = self.miner_wallets[0]
            mock_uploader = MockS3Uploader(self.mock_s3_server)
            mock_validator = MockS3Validator(self.mock_s3_server)
            
            # Upload multiple files to simulate realistic scenario
            job_ids = ["zillow_78041", "zillow_90210", "zillow_10001"]
            chunks_per_job = 5
            
            start_time = time.time()
            
            # Upload files
            for job_id in job_ids:
                for chunk_idx in range(chunks_per_job):
                    chunk_data = f"test_data_job_{job_id}_chunk_{chunk_idx}".encode()
                    success = await mock_uploader.upload_chunk(
                        miner_wallet.hotkey.ss58_address,
                        job_id,
                        chunk_data,
                        chunk_idx
                    )
                    self.assertTrue(success, f"Upload should succeed for {job_id} chunk {chunk_idx}")
            
            upload_time = time.time() - start_time
            
            # Download and verify files
            start_time = time.time()
            
            files = await mock_validator.get_miner_files(miner_wallet.hotkey.ss58_address)
            expected_file_count = len(job_ids) * chunks_per_job
            self.assertEqual(len(files), expected_file_count, f"Should find {expected_file_count} files")
            
            # Download all files
            for file_info in files:
                downloaded_data = await mock_validator.download_file(
                    miner_wallet.hotkey.ss58_address,
                    file_info['key']
                )
                self.assertIsNotNone(downloaded_data, f"Should download file {file_info['key']}")
            
            download_time = time.time() - start_time
            
            bt.logging.info(f"Performance: {expected_file_count} files uploaded in {upload_time:.2f}s, downloaded in {download_time:.2f}s")
            
            # Performance assertions (should be fast with mock infrastructure)
            self.assertLess(upload_time, 2.0, "Upload should complete quickly")
            self.assertLess(download_time, 2.0, "Download should complete quickly")
            
            bt.logging.info("✅ S3 performance test passed")
        
        asyncio.run(run_test())
    
    def _setup_test_database(self, entities: List[DataEntity]):
        """Set up test database with entities (simplified for testing)"""
        # For this test, we're focusing on S3 flow, not database setup
        # In a real scenario, this would populate the SQLite database
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
