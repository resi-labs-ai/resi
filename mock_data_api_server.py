#!/usr/bin/env python3
"""
Mock Data API Server for Zipcode Block Distribution
Provides coordinated zipcode blocks for consensus validation
"""

import json
import random
import datetime as dt
import hashlib
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify
import bittensor as bt


class MockDataAPIServer:
    """Mock server that provides coordinated zipcode blocks for validators"""
    
    def __init__(self, zipcode_csv_path: str = None):
        self.app = Flask(__name__)
        
        # Load zipcodes from CSV
        if zipcode_csv_path is None:
            zipcode_csv_path = Path(__file__).parent / "scraping" / "zillow" / "zipcodes.csv"
        
        self.zipcodes = self._load_zipcodes(zipcode_csv_path)
        
        # Track active assignments and validator access
        self.active_assignments = {}
        self.validator_access_tokens = {}
        self.assignment_history = []
        
        # Configuration
        self.config = {
            'zipcodes_per_batch': 20,
            'batches_per_cycle': 50,
            'assignment_duration_hours': 4,
            'overlap_factor': 2,
            'miners_per_batch': 10,
            'sources': ['ZILLOW_SOLD'],
            'expected_properties_per_zipcode': 50
        }
        
        self._setup_routes()
    
    def _load_zipcodes(self, csv_path: Path) -> List[Dict[str, Any]]:
        """Load zipcode data from CSV file"""
        zipcodes = []
        
        if not csv_path.exists():
            # Fallback to mock data if CSV doesn't exist
            print(f"Warning: Zipcode CSV not found at {csv_path}, using mock data")
            return self._generate_mock_zipcodes()
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    zipcode = row.get('RegionName', '').strip()
                    if len(zipcode) == 5 and zipcode.isdigit():
                        zipcodes.append({
                            'zipcode': zipcode,
                            'size_rank': int(row.get('SizeRank', 99999)),
                            'state': row.get('State', ''),
                            'city': row.get('City', ''),
                            'metro': row.get('Metro', ''),
                            'county': row.get('CountyName', '')
                        })
            
            print(f"Loaded {len(zipcodes)} zipcodes from {csv_path}")
            return zipcodes
            
        except Exception as e:
            print(f"Error loading zipcodes from {csv_path}: {e}")
            return self._generate_mock_zipcodes()
    
    def _generate_mock_zipcodes(self) -> List[Dict[str, Any]]:
        """Generate mock zipcode data for testing"""
        mock_zipcodes = []
        
        # Generate some realistic zipcodes
        base_zipcodes = [
            ('77494', 'TX', 'Katy', 'Houston', 'Harris'),
            ('78701', 'TX', 'Austin', 'Austin', 'Travis'),
            ('90210', 'CA', 'Beverly Hills', 'Los Angeles', 'Los Angeles'),
            ('10001', 'NY', 'New York', 'New York', 'New York'),
            ('30309', 'GA', 'Atlanta', 'Atlanta', 'Fulton'),
            ('85001', 'AZ', 'Phoenix', 'Phoenix', 'Maricopa'),
            ('98101', 'WA', 'Seattle', 'Seattle', 'King'),
            ('60601', 'IL', 'Chicago', 'Chicago', 'Cook'),
            ('37201', 'TN', 'Nashville', 'Nashville', 'Davidson'),
            ('33101', 'FL', 'Miami Beach', 'Miami', 'Miami-Dade')
        ]
        
        for i, (zipcode, state, city, metro, county) in enumerate(base_zipcodes):
            mock_zipcodes.append({
                'zipcode': zipcode,
                'size_rank': i + 1,
                'state': state,
                'city': city,
                'metro': metro,
                'county': county
            })
        
        # Generate additional random zipcodes
        for i in range(100):
            zipcode = f"{random.randint(10000, 99999)}"
            mock_zipcodes.append({
                'zipcode': zipcode,
                'size_rank': i + 100,
                'state': random.choice(['TX', 'CA', 'FL', 'NY', 'IL']),
                'city': f'City_{i}',
                'metro': f'Metro_{i}',
                'county': f'County_{i}'
            })
        
        return mock_zipcodes
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(),
                'total_zipcodes': len(self.zipcodes),
                'active_assignments': len(self.active_assignments)
            })
        
        @self.app.route('/get-validator-access', methods=['POST'])
        def get_validator_access():
            """Authenticate validator and provide access token"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['hotkey', 'timestamp', 'signature', 'sources']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'Missing required field: {field}'}), 400
                
                hotkey = data['hotkey']
                timestamp = data['timestamp']
                signature = data['signature']
                sources = data['sources']
                
                # Validate timestamp (within 5 minutes)
                current_time = int(dt.datetime.now(dt.timezone.utc).timestamp())
                if abs(current_time - timestamp) > 300:  # 5 minutes
                    return jsonify({'error': 'Request timestamp too old or too far in future'}), 400
                
                # In a real implementation, verify the signature
                # For mock server, we'll just validate format
                if not hotkey or len(hotkey) < 40:
                    return jsonify({'error': 'Invalid hotkey format'}), 400
                
                # Generate access token
                access_token = hashlib.sha256(f"{hotkey}_{timestamp}_{random.random()}".encode()).hexdigest()
                
                # Store access token
                self.validator_access_tokens[hotkey] = {
                    'access_token': access_token,
                    'created_at': dt.datetime.now(dt.timezone.utc),
                    'expires_at': dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=6),
                    'sources': sources.split(',')
                }
                
                return jsonify({
                    'access_token': access_token,
                    'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=6)).isoformat(),
                    'expiry_seconds': 6 * 3600,
                    'sources_authorized': sources.split(','),
                    'rate_limits': {
                        'requests_per_hour': 100,
                        'max_batch_size': 50
                    }
                })
                
            except Exception as e:
                return jsonify({'error': f'Authentication failed: {str(e)}'}), 500
        
        @self.app.route('/api/v1/validator-data', methods=['GET'])
        def get_validator_data():
            """Get coordinated zipcode blocks for validators"""
            try:
                # Validate authorization
                auth_header = request.headers.get('Authorization', '')
                if not auth_header.startswith('Bearer '):
                    return jsonify({'error': 'Missing or invalid authorization header'}), 401
                
                access_token = auth_header.replace('Bearer ', '')
                
                # Find validator by access token
                validator_info = None
                for hotkey, info in self.validator_access_tokens.items():
                    if info['access_token'] == access_token:
                        if dt.datetime.now(dt.timezone.utc) > info['expires_at']:
                            return jsonify({'error': 'Access token expired'}), 401
                        validator_info = info
                        break
                
                if not validator_info:
                    return jsonify({'error': 'Invalid access token'}), 401
                
                # Get request parameters
                sources = request.args.get('sources', 'ZILLOW_SOLD').split(',')
                block_size = int(request.args.get('block_size', self.config['zipcodes_per_batch']))
                format_type = request.args.get('format', 'json')
                
                # Validate sources
                authorized_sources = validator_info['sources']
                for source in sources:
                    if source not in authorized_sources:
                        return jsonify({'error': f'Source {source} not authorized'}), 403
                
                # Generate zipcode blocks
                zipcode_blocks = self._generate_zipcode_blocks(sources, block_size)
                
                return jsonify({
                    'request_id': self._generate_request_id(),
                    'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                    'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=self.config['assignment_duration_hours'])).isoformat(),
                    'data_blocks': zipcode_blocks,
                    'assignment_config': {
                        'overlap_factor': self.config['overlap_factor'],
                        'miners_per_batch': self.config['miners_per_batch'],
                        'expected_properties_per_zipcode': self.config['expected_properties_per_zipcode'],
                        'assignment_timeout_hours': self.config['assignment_duration_hours']
                    },
                    'total_batches': len(zipcode_blocks),
                    'total_zipcodes': sum(len(batch['zipcodes']) for batch in zipcode_blocks.values())
                })
                
            except Exception as e:
                return jsonify({'error': f'Failed to generate data blocks: {str(e)}'}), 500
        
        @self.app.route('/api/v1/assignment-status', methods=['POST'])
        def update_assignment_status():
            """Endpoint for validators to report assignment completion status"""
            try:
                data = request.get_json()
                assignment_id = data.get('assignment_id')
                status = data.get('status')  # 'started', 'completed', 'failed'
                statistics = data.get('statistics', {})
                
                # Store assignment status
                self.assignment_history.append({
                    'assignment_id': assignment_id,
                    'status': status,
                    'timestamp': dt.datetime.now(dt.timezone.utc).isoformat(),
                    'statistics': statistics
                })
                
                return jsonify({'success': True, 'message': 'Status updated'})
                
            except Exception as e:
                return jsonify({'error': f'Failed to update status: {str(e)}'}), 500
        
        @self.app.route('/api/v1/statistics', methods=['GET'])
        def get_statistics():
            """Get API usage statistics"""
            return jsonify({
                'total_validators': len(self.validator_access_tokens),
                'active_assignments': len(self.active_assignments),
                'completed_assignments': len([h for h in self.assignment_history if h['status'] == 'completed']),
                'total_zipcodes_available': len(self.zipcodes),
                'server_uptime': 'mock_server',
                'last_assignment': self.assignment_history[-1] if self.assignment_history else None
            })
    
    def _generate_zipcode_blocks(self, sources: List[str], block_size: int) -> Dict[str, Any]:
        """Generate random zipcode blocks for assignment"""
        blocks = {}
        
        # Shuffle zipcodes for randomization
        available_zipcodes = self.zipcodes.copy()
        random.shuffle(available_zipcodes)
        
        # Create blocks
        num_batches = min(self.config['batches_per_cycle'], len(available_zipcodes) // block_size)
        
        for i in range(num_batches):
            batch_id = f"batch_{i:03d}"
            start_idx = i * block_size
            end_idx = min(start_idx + block_size, len(available_zipcodes))
            
            batch_zipcodes = available_zipcodes[start_idx:end_idx]
            
            blocks[batch_id] = {
                'zipcodes': [zc['zipcode'] for zc in batch_zipcodes],
                'expected_properties': len(batch_zipcodes) * self.config['expected_properties_per_zipcode'],
                'assignment_groups': self.config['overlap_factor'],
                'miners_per_group': self.config['miners_per_batch'],
                'geographic_info': {
                    'states': list(set(zc['state'] for zc in batch_zipcodes)),
                    'metros': list(set(zc['metro'] for zc in batch_zipcodes if zc['metro'])),
                    'size_ranks': [zc['size_rank'] for zc in batch_zipcodes]
                },
                'sources': sources
            }
        
        return blocks
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        timestamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S')
        random_suffix = hashlib.md5(f"{timestamp}_{random.random()}".encode()).hexdigest()[:8]
        return f"zipcode_block_{timestamp}_{random_suffix}"
    
    def run(self, host='localhost', port=8000, debug=True):
        """Run the mock server"""
        print(f"Starting Mock Data API Server on {host}:{port}")
        print(f"Loaded {len(self.zipcodes)} zipcodes")
        print(f"Health check: http://{host}:{port}/health")
        print(f"API docs available at: http://{host}:{port}/api/v1/")
        
        self.app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Mock Data API Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--zipcode-csv', help='Path to zipcode CSV file')
    
    args = parser.parse_args()
    
    server = MockDataAPIServer(zipcode_csv_path=args.zipcode_csv)
    server.run(host=args.host, port=args.port)
