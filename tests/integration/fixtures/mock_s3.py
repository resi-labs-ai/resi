"""
Mock S3 Infrastructure for Testing

Provides a local S3-compatible server and authentication system for testing
miner uploads and validator downloads without requiring real AWS S3.
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock
import threading
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET

import bittensor as bt


class MockS3AuthServer:
    """Mock S3 authentication server for testing"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.thread = None
        self.base_dir = tempfile.mkdtemp(prefix="mock_s3_")
        self.auth_responses = {}
        
    def start(self):
        """Start the mock S3 auth server"""
        handler = self._create_request_handler()
        self.server = socketserver.TCPServer(("", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        bt.logging.info(f"Mock S3 auth server started on port {self.port}")
    
    def stop(self):
        """Stop the mock S3 auth server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join()
        bt.logging.info("Mock S3 auth server stopped")
    
    def _create_request_handler(self):
        """Create HTTP request handler for mock auth server"""
        auth_server = self
        
        class MockS3AuthHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/get-folder-access":
                    self._handle_folder_access()
                elif self.path == "/get-miner-specific-access":
                    self._handle_miner_access()
                else:
                    self.send_error(404)
            
            def _handle_folder_access(self):
                """Handle miner folder access request"""
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    
                    # Validate required fields
                    required_fields = ['coldkey', 'hotkey', 'timestamp', 'signature']
                    if not all(field in request_data for field in required_fields):
                        self.send_error(400, "Missing required fields")
                        return
                    
                    # Create folder for this hotkey
                    hotkey = request_data['hotkey']
                    folder_path = Path(auth_server.base_dir) / hotkey
                    folder_path.mkdir(exist_ok=True)
                    
                    # Mock S3 credentials response
                    response = {
                        "folder": hotkey,
                        "access_key": f"test_access_key_{hotkey[:8]}",
                        "secret_key": f"test_secret_key_{hotkey[:8]}",
                        "session_token": f"test_session_token_{int(time.time())}",
                        "bucket": "test-bucket",
                        "prefix": f"miners/{hotkey}/",
                        "expiry": int(time.time()) + 3600  # 1 hour
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                    
                except Exception as e:
                    bt.logging.error(f"Mock S3 auth error: {e}")
                    self.send_error(500, str(e))
            
            def _handle_miner_access(self):
                """Handle validator accessing miner data"""
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    
                    miner_hotkey = request_data.get('miner_hotkey')
                    if not miner_hotkey:
                        self.send_error(400, "Missing miner_hotkey")
                        return
                    
                    # Generate mock S3 file list URL
                    miner_url = f"http://localhost:{auth_server.port}/s3-list/{miner_hotkey}"
                    
                    response = {
                        "miner_url": miner_url,
                        "access_granted": True,
                        "expiry": int(time.time()) + 3600
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                    
                except Exception as e:
                    bt.logging.error(f"Mock miner access error: {e}")
                    self.send_error(500, str(e))
            
            def do_GET(self):
                """Handle S3 file list requests"""
                if self.path.startswith("/s3-list/"):
                    miner_hotkey = self.path.split("/s3-list/")[1]
                    self._handle_s3_file_list(miner_hotkey)
                else:
                    self.send_error(404)
            
            def _handle_s3_file_list(self, miner_hotkey: str):
                """Generate mock S3 XML file list"""
                miner_dir = Path(auth_server.base_dir) / miner_hotkey
                
                # Create mock file list XML
                root = ET.Element("ListBucketResult")
                
                if miner_dir.exists():
                    for file_path in miner_dir.rglob("*.parquet"):
                        contents = ET.SubElement(root, "Contents")
                        
                        key = ET.SubElement(contents, "Key")
                        key.text = f"miners/{miner_hotkey}/{file_path.relative_to(miner_dir)}"
                        
                        last_modified = ET.SubElement(contents, "LastModified")
                        last_modified.text = datetime.now(timezone.utc).isoformat()
                        
                        size = ET.SubElement(contents, "Size")
                        size.text = str(file_path.stat().st_size if file_path.exists() else 1024)
                
                xml_content = ET.tostring(root, encoding='unicode')
                
                self.send_response(200)
                self.send_header('Content-type', 'application/xml')
                self.end_headers()
                self.wfile.write(xml_content.encode())
            
            def log_message(self, format, *args):
                """Suppress default logging"""
                pass
        
        return MockS3AuthHandler
    
    def add_miner_data(self, hotkey: str, job_id: str, data_files: List[Dict[str, Any]]):
        """Add mock data files for a miner"""
        miner_dir = Path(self.base_dir) / hotkey / job_id
        miner_dir.mkdir(parents=True, exist_ok=True)
        
        for i, file_data in enumerate(data_files):
            file_path = miner_dir / f"chunk_{i:04d}.parquet"
            # Create a dummy parquet file
            with open(file_path, 'wb') as f:
                f.write(b"mock_parquet_data")
    
    def get_miner_data_path(self, hotkey: str) -> Path:
        """Get the local path for miner data"""
        return Path(self.base_dir) / hotkey
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)


class MockS3Uploader:
    """Mock S3 uploader that saves files locally"""
    
    def __init__(self, auth_server: MockS3AuthServer):
        self.auth_server = auth_server
        
    async def upload_chunk(self, hotkey: str, job_id: str, chunk_data: bytes, chunk_index: int) -> bool:
        """Mock upload chunk to local storage"""
        try:
            miner_dir = self.auth_server.get_miner_data_path(hotkey) / job_id
            miner_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = miner_dir / f"chunk_{chunk_index:04d}.parquet"
            
            with open(file_path, 'wb') as f:
                f.write(chunk_data)
            
            bt.logging.debug(f"Mock uploaded chunk {chunk_index} for {hotkey}/{job_id}")
            return True
            
        except Exception as e:
            bt.logging.error(f"Mock upload failed: {e}")
            return False


class MockS3Validator:
    """Mock S3 validator that reads from local storage"""
    
    def __init__(self, auth_server: MockS3AuthServer):
        self.auth_server = auth_server
    
    async def get_miner_files(self, miner_hotkey: str) -> List[Dict[str, Any]]:
        """Get list of files for a miner"""
        miner_dir = self.auth_server.get_miner_data_path(miner_hotkey)
        
        files = []
        if miner_dir.exists():
            for file_path in miner_dir.rglob("*.parquet"):
                files.append({
                    'key': f"miners/{miner_hotkey}/{file_path.relative_to(miner_dir)}",
                    'size': file_path.stat().st_size,
                    'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat(),
                    'local_path': str(file_path)
                })
        
        return files
    
    async def download_file(self, miner_hotkey: str, file_key: str) -> Optional[bytes]:
        """Download a file from mock S3"""
        try:
            # Extract relative path from S3 key
            relative_path = file_key.replace(f"miners/{miner_hotkey}/", "")
            file_path = self.auth_server.get_miner_data_path(miner_hotkey) / relative_path
            
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            else:
                bt.logging.warning(f"Mock file not found: {file_path}")
                return None
                
        except Exception as e:
            bt.logging.error(f"Mock download failed: {e}")
            return None


# Global mock S3 infrastructure
_mock_s3_auth_server = None

def get_mock_s3_auth_server(port: int = 8080) -> MockS3AuthServer:
    """Get or create global mock S3 auth server"""
    global _mock_s3_auth_server
    if _mock_s3_auth_server is None:
        _mock_s3_auth_server = MockS3AuthServer(port)
        _mock_s3_auth_server.start()
    return _mock_s3_auth_server

def cleanup_mock_s3():
    """Clean up mock S3 infrastructure"""
    global _mock_s3_auth_server
    if _mock_s3_auth_server:
        _mock_s3_auth_server.stop()
        _mock_s3_auth_server.cleanup()
        _mock_s3_auth_server = None
