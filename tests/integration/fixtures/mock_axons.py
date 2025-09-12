"""
Mock Axon Infrastructure for Testing

Provides mock miner axons for testing validator-miner communication
without requiring real network setup or blockchain registration.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import Mock, AsyncMock
import threading
import socket
from contextlib import closing

import bittensor as bt
from common.protocol import OnDemandRequest
from common.data import DataEntity, DataSource, DataLabel
from tests.integration.fixtures.test_wallets import get_test_wallet


class MockMinerAxon:
    """Mock miner axon for testing validator communication"""
    
    def __init__(self, wallet: bt.wallet, port: int = None, data_source: DataSource = DataSource.RAPID_ZILLOW):
        self.wallet = wallet
        self.port = port or self._find_free_port()
        self.data_source = data_source
        self.axon = None
        self.data_store = []  # Mock data storage
        self.response_delay = 0.1  # Simulate network delay
        self.failure_rate = 0.0  # Simulate failure rate (0.0 = no failures)
        self.is_running = False
        
    def _find_free_port(self) -> int:
        """Find a free port for the mock axon"""
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def add_mock_data(self, entities: List[DataEntity]):
        """Add mock data entities to this miner"""
        self.data_store.extend(entities)
    
    def set_failure_rate(self, rate: float):
        """Set the failure rate for this mock miner (0.0 to 1.0)"""
        self.failure_rate = max(0.0, min(1.0, rate))
    
    def set_response_delay(self, delay: float):
        """Set response delay in seconds"""
        self.response_delay = delay
    
    async def handle_on_demand_request(self, synapse: OnDemandRequest) -> OnDemandRequest:
        """Handle on-demand data requests"""
        bt.logging.debug(f"Mock miner {self.wallet.hotkey.ss58_address} handling request: {synapse.source}")
        
        # Simulate processing delay
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        # Simulate failure
        if self.failure_rate > 0 and time.time() % 1.0 < self.failure_rate:
            bt.logging.warning(f"Mock miner {self.wallet.hotkey.ss58_address} simulating failure")
            synapse.data = []
            return synapse
        
        # Filter data based on request
        filtered_data = self._filter_data(synapse)
        
        # Convert to the format expected by validators
        response_data = []
        for entity in filtered_data[:synapse.limit]:
            response_data.append({
                'uri': entity.uri,
                'datetime': entity.datetime.isoformat(),
                'source': entity.source.value,
                'label': entity.label.value if entity.label else '',
                'content': entity.content.decode('utf-8', errors='ignore'),
                'content_size_bytes': entity.content_size_bytes
            })
        
        synapse.data = response_data
        bt.logging.debug(f"Mock miner returning {len(response_data)} items")
        return synapse
    
    def _filter_data(self, request: OnDemandRequest) -> List[DataEntity]:
        """Filter stored data based on request parameters"""
        filtered = []
        
        for entity in self.data_store:
            # Check source match
            if entity.source != DataSource[request.source.upper()]:
                continue
            
            # Check keyword match (simple contains check)
            if request.keywords:
                content_str = entity.content.decode('utf-8', errors='ignore').lower()
                if not any(keyword.lower() in content_str for keyword in request.keywords):
                    continue
            
            # Check label match
            if request.usernames and entity.label:
                if entity.label.value not in request.usernames:
                    continue
            
            # Check date range (simplified)
            if request.start_date or request.end_date:
                # For simplicity, assume all data is within range
                pass
            
            filtered.append(entity)
        
        return filtered
    
    def start(self):
        """Start the mock axon"""
        if self.is_running:
            return
        
        try:
            self.axon = bt.axon(
                wallet=self.wallet,
                port=self.port,
                ip="127.0.0.1"
            )
            
            # Attach the request handler
            self.axon.attach(
                forward_fn=self.handle_on_demand_request,
                blacklist_fn=None,
                priority_fn=None
            )
            
            self.axon.start()
            self.is_running = True
            bt.logging.info(f"Mock miner axon started on port {self.port}")
            
        except Exception as e:
            bt.logging.error(f"Failed to start mock axon: {e}")
            raise
    
    def stop(self):
        """Stop the mock axon"""
        if self.axon and self.is_running:
            self.axon.stop()
            self.is_running = False
            bt.logging.info(f"Mock miner axon stopped")
    
    def get_axon_info(self) -> bt.AxonInfo:
        """Get axon info for this mock miner"""
        return bt.AxonInfo(
            ip="127.0.0.1",
            port=self.port,
            ip_type=4,  # IPv4
            hotkey=self.wallet.hotkey.ss58_address,
            coldkey=self.wallet.coldkey.ss58_address,
            protocol=4,
            version=1
        )


class MockMinerNetwork:
    """Manages a network of mock miners for testing"""
    
    def __init__(self, num_miners: int = 3):
        self.miners = {}
        self.base_port = 9000
        self._create_mock_miners(num_miners)
    
    def _create_mock_miners(self, num_miners: int):
        """Create mock miners with test wallets"""
        from tests.integration.fixtures.test_wallets import get_test_wallet_manager
        
        wallet_manager = get_test_wallet_manager()
        miner_wallets = wallet_manager.get_miner_wallets()
        
        for i in range(min(num_miners, len(miner_wallets))):
            wallet = miner_wallets[i]
            port = self.base_port + i
            
            miner = MockMinerAxon(wallet, port)
            self.miners[wallet.hotkey.ss58_address] = miner
    
    def add_mock_data_to_all_miners(self, entities: List[DataEntity]):
        """Add mock data to all miners"""
        for miner in self.miners.values():
            miner.add_mock_data(entities)
    
    def add_mock_data_to_miner(self, hotkey: str, entities: List[DataEntity]):
        """Add mock data to a specific miner"""
        if hotkey in self.miners:
            self.miners[hotkey].add_mock_data(entities)
    
    def set_miner_failure_rate(self, hotkey: str, rate: float):
        """Set failure rate for a specific miner"""
        if hotkey in self.miners:
            self.miners[hotkey].set_failure_rate(rate)
    
    def set_all_miners_failure_rate(self, rate: float):
        """Set failure rate for all miners"""
        for miner in self.miners.values():
            miner.set_failure_rate(rate)
    
    def start_all_miners(self):
        """Start all mock miners"""
        for hotkey, miner in self.miners.items():
            try:
                miner.start()
                bt.logging.info(f"Started mock miner {hotkey[:8]}... on port {miner.port}")
            except Exception as e:
                bt.logging.error(f"Failed to start mock miner {hotkey[:8]}...: {e}")
    
    def stop_all_miners(self):
        """Stop all mock miners"""
        for miner in self.miners.values():
            miner.stop()
    
    def get_axon_infos(self) -> List[bt.AxonInfo]:
        """Get axon info for all miners"""
        return [miner.get_axon_info() for miner in self.miners.values()]
    
    def get_miner_hotkeys(self) -> List[str]:
        """Get all miner hotkeys"""
        return list(self.miners.keys())
    
    def get_miner(self, hotkey: str) -> Optional[MockMinerAxon]:
        """Get a specific mock miner"""
        return self.miners.get(hotkey)
    
    def create_mock_metagraph(self) -> bt.metagraph:
        """Create a mock metagraph with these miners"""
        # This is a simplified mock metagraph for testing
        mock_metagraph = Mock()
        mock_metagraph.hotkeys = list(self.miners.keys())
        mock_metagraph.axons = self.get_axon_infos()
        mock_metagraph.uids = list(range(len(self.miners)))
        mock_metagraph.stake = [1000.0] * len(self.miners)  # Mock stake values
        
        return mock_metagraph


# Global mock miner network
_mock_miner_network = None

def get_mock_miner_network(num_miners: int = 3) -> MockMinerNetwork:
    """Get or create global mock miner network"""
    global _mock_miner_network
    if _mock_miner_network is None:
        _mock_miner_network = MockMinerNetwork(num_miners)
    return _mock_miner_network

def cleanup_mock_miners():
    """Clean up mock miner network"""
    global _mock_miner_network
    if _mock_miner_network:
        _mock_miner_network.stop_all_miners()
        _mock_miner_network = None
