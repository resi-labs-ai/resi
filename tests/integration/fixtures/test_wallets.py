"""
Test Wallet Generation and Management

Provides pre-generated test wallets for integration testing with proper
authentication and signing capabilities.
"""

import os
import tempfile
from typing import Dict, List, Tuple
import bittensor as bt
from pathlib import Path


class TestWalletManager:
    """Manages test wallets for integration testing"""
    
    def __init__(self, base_dir: str = None):
        """Initialize wallet manager with temporary directory"""
        if base_dir is None:
            self.base_dir = tempfile.mkdtemp(prefix="test_wallets_")
        else:
            self.base_dir = base_dir
            
        self.wallets = {}
        self._create_test_wallets()
    
    def _create_test_wallets(self):
        """Create a set of test wallets for different roles"""
        # Create wallets for different test scenarios
        wallet_configs = [
            ("test_miner_1", "miner_hotkey_1"),
            ("test_miner_2", "miner_hotkey_2"),
            ("test_miner_3", "miner_hotkey_3"),
            ("test_validator_1", "validator_hotkey_1"),
            ("test_validator_2", "validator_hotkey_2"),
            ("test_validator_3", "validator_hotkey_3"),
            ("test_organic_1", "organic_hotkey_1"),
        ]
        
        for wallet_name, hotkey_name in wallet_configs:
            wallet = bt.wallet(
                name=wallet_name,
                hotkey=hotkey_name,
                path=self.base_dir
            )
            
            # Create wallet files if they don't exist
            wallet.create_if_non_existent(
                coldkey_use_password=False,
                hotkey_use_password=False
            )
            
            self.wallets[wallet_name] = wallet
    
    def get_wallet(self, name: str) -> bt.wallet:
        """Get a test wallet by name"""
        if name not in self.wallets:
            raise ValueError(f"Test wallet '{name}' not found. Available: {list(self.wallets.keys())}")
        return self.wallets[name]
    
    def get_miner_wallets(self) -> List[bt.wallet]:
        """Get all miner test wallets"""
        return [wallet for name, wallet in self.wallets.items() if "miner" in name]
    
    def get_validator_wallets(self) -> List[bt.wallet]:
        """Get all validator test wallets"""
        return [wallet for name, wallet in self.wallets.items() if "validator" in name]
    
    def get_wallet_info(self, wallet_name: str) -> Dict[str, str]:
        """Get wallet addresses for testing"""
        wallet = self.get_wallet(wallet_name)
        return {
            'name': wallet_name,
            'coldkey': wallet.coldkey.ss58_address,
            'hotkey': wallet.hotkey.ss58_address,
            'path': self.base_dir
        }
    
    def sign_commitment(self, wallet_name: str, commitment: str) -> str:
        """Sign a commitment with a test wallet"""
        wallet = self.get_wallet(wallet_name)
        signature = wallet.hotkey.sign(commitment.encode())
        return signature.hex()
    
    def cleanup(self):
        """Clean up temporary wallet files"""
        import shutil
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)


# Global test wallet manager instance
_test_wallet_manager = None

def get_test_wallet_manager() -> TestWalletManager:
    """Get or create the global test wallet manager"""
    global _test_wallet_manager
    if _test_wallet_manager is None:
        _test_wallet_manager = TestWalletManager()
    return _test_wallet_manager

def get_test_wallet(name: str) -> bt.wallet:
    """Convenience function to get a test wallet"""
    return get_test_wallet_manager().get_wallet(name)

def get_test_miner_wallets() -> List[bt.wallet]:
    """Get all test miner wallets"""
    return get_test_wallet_manager().get_miner_wallets()

def get_test_validator_wallets() -> List[bt.wallet]:
    """Get all test validator wallets"""
    return get_test_wallet_manager().get_validator_wallets()

def cleanup_test_wallets():
    """Clean up all test wallets"""
    global _test_wallet_manager
    if _test_wallet_manager:
        _test_wallet_manager.cleanup()
        _test_wallet_manager = None
