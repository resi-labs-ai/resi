# The MIT License (MIT)
# Copyright © 2025 Resi Labs

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

"""
Auto-updater module for validator nodes.
Automatically checks for updates and restarts the PM2 process when updates are available.
"""

import os
import subprocess
import time
import threading
import json
import bittensor as bt
from pathlib import Path
from typing import Optional


class AutoUpdater:
    """Handles automatic updates for validator nodes."""
    
    def __init__(self, config, check_interval_hours: float = 3.0):
        """
        Initialize the auto-updater.
        
        Args:
            config: Bittensor config object
            check_interval_hours: How often to check for updates (default: 3 hours)
        """
        self.config = config
        self.check_interval_seconds = check_interval_hours * 3600
        self.project_root = Path(__file__).parent.parent
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.validator_name: Optional[str] = None
        
    def _detect_validator_name(self) -> Optional[str]:
        """Try to auto-detect the validator name from PM2 processes by matching PID."""
        try:
            current_pid = os.getpid()
            
            # Query PM2 for process info in JSON format
            result = subprocess.run(
                ["pm2", "jlist"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                processes = json.loads(result.stdout)
                
                # Match by PID
                for proc in processes:
                    if proc.get("pid") == current_pid:
                        process_name = proc.get("name")
                        if process_name:
                            bt.logging.info(f"Detected PM2 process name: {process_name} (PID: {current_pid})")
                            return process_name
        except json.JSONDecodeError as e:
            bt.logging.warning(f"Failed to parse PM2 JSON output: {e}")
        except Exception as e:
            bt.logging.warning(f"Failed to detect validator name: {e}")
        
        return None
    
    def _get_current_commit(self) -> Optional[str]:
        """Get the current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            bt.logging.warning(f"Failed to get current commit: {e}")
        return None
    
    def _check_for_updates(self) -> bool:
        """Check if there are updates available on the remote."""
        try:
            # Fetch latest changes
            result = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                bt.logging.warning(f"Failed to fetch from origin: {result.stderr}")
                return False
            
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False
            
            current_branch = result.stdout.strip()
            
            # Check if there are differences
            result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..origin/{current_branch}"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                count = int(result.stdout.strip())
                return count > 0
            
        except Exception as e:
            bt.logging.warning(f"Error checking for updates: {e}")
        
        return False
    
    def _has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "diff-index", "--quiet", "HEAD", "--"],
                cwd=self.project_root,
                timeout=10
            )
            return result.returncode != 0
        except Exception as e:
            bt.logging.warning(f"Error checking for uncommitted changes: {e}")
            return False
    
    def _stash_changes(self) -> bool:
        """Stash uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "stash"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            bt.logging.warning(f"Error stashing changes: {e}")
            return False
    
    def _pop_stash(self) -> bool:
        """Restore stashed changes."""
        try:
            result = subprocess.run(
                ["git", "stash", "pop"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            bt.logging.warning(f"Error popping stash: {e}")
            return False
    
    def _pull_updates(self) -> bool:
        """Pull latest changes from the current branch."""
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False
            
            current_branch = result.stdout.strip()
            
            # Pull changes
            result = subprocess.run(
                ["git", "pull", "origin", current_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                bt.logging.info(f"Successfully pulled latest changes from {current_branch}")
                return True
            else:
                bt.logging.error(f"Failed to pull changes: {result.stderr}")
                return False
                
        except Exception as e:
            bt.logging.error(f"Error pulling updates: {e}")
            return False
    
    def _check_requirements_changed(self, old_commit: str) -> bool:
        """Check if requirements.txt changed between commits."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", old_commit, "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return "requirements.txt" in result.stdout
        except Exception as e:
            bt.logging.warning(f"Error checking requirements.txt changes: {e}")
        
        return False
    
    def _update_dependencies(self) -> bool:
        """Update Python dependencies if virtual environment exists."""
        venv_path = self.project_root / ".venv" / "bin" / "activate"
        
        if not venv_path.exists():
            bt.logging.warning("Virtual environment not found, skipping dependency update")
            return False
        
        try:
            # Use pip install -e . in the virtual environment
            # We need to activate the venv and run pip
            pip_path = self.project_root / ".venv" / "bin" / "pip"
            
            if pip_path.exists():
                result = subprocess.run(
                    [str(pip_path), "install", "-e", ".", "--quiet"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                if result.returncode == 0:
                    bt.logging.info("Dependencies updated successfully")
                    return True
                else:
                    bt.logging.warning(f"Failed to update dependencies: {result.stderr}")
                    return False
            else:
                bt.logging.warning("pip not found in virtual environment")
                return False
                
        except Exception as e:
            bt.logging.warning(f"Error updating dependencies: {e}")
            return False
    
    def _restart_pm2_process(self, process_name: str) -> bool:
        """Restart the PM2 process."""
        try:
            result = subprocess.run(
                ["pm2", "restart", process_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                bt.logging.info(f"Successfully restarted PM2 process: {process_name}")
                return True
            else:
                bt.logging.error(f"Failed to restart PM2 process: {result.stderr}")
                return False
                
        except Exception as e:
            bt.logging.error(f"Error restarting PM2 process: {e}")
            return False
    
    def _wait_for_process_healthy(self, process_name: str, max_attempts: int = 30) -> bool:
        """Wait for the PM2 process to become healthy."""
        for attempt in range(max_attempts):
            try:
                result = subprocess.run(
                    ["pm2", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    if process_name in output and "online" in output:
                        # Wait a bit more to ensure it stays online
                        time.sleep(3)
                        result = subprocess.run(
                            ["pm2", "list"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0 and "online" in result.stdout:
                            bt.logging.info(f"Process {process_name} is running and stable")
                            return True
                
                time.sleep(1)
                
            except Exception as e:
                bt.logging.warning(f"Error checking process health: {e}")
                time.sleep(1)
        
        bt.logging.error(f"Process {process_name} failed to start properly after {max_attempts} seconds")
        return False
    
    def perform_update(self) -> bool:
        """
        Perform a complete update cycle.
        
        Returns:
            True if update was successful, False otherwise
        """
        bt.logging.info("=== Starting Auto-Update ===")
        
        # Detect validator name if not set
        if not self.validator_name:
            self.validator_name = self._detect_validator_name()
            if not self.validator_name:
                bt.logging.error("Could not detect validator name. Skipping update.")
                return False
        
        bt.logging.info(f"Validator: {self.validator_name}")
        
        # Check if validator is running
        try:
            result = subprocess.run(
                ["pm2", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0 or self.validator_name not in result.stdout:
                bt.logging.error(f"Validator '{self.validator_name}' not found in PM2 processes")
                return False
        except Exception as e:
            bt.logging.error(f"Error checking PM2 processes: {e}")
            return False
        
        # Store old commit
        old_commit = self._get_current_commit()
        
        # Check for uncommitted changes
        stashed = False
        if self._has_uncommitted_changes():
            bt.logging.warning("Uncommitted changes detected. Stashing...")
            if self._stash_changes():
                stashed = True
                bt.logging.info("Changes stashed")
            else:
                bt.logging.warning("Failed to stash changes")
        
        # Pull updates
        if not self._pull_updates():
            # Try to restore stash if pull failed
            if stashed:
                self._pop_stash()
            return False
        
        # Restore stashed changes if we stashed them
        if stashed:
            bt.logging.info("Restoring stashed changes...")
            if not self._pop_stash():
                bt.logging.warning("Could not automatically restore stashed changes")
                bt.logging.info("You can manually restore them with: git stash pop")
        
        # Check if requirements.txt changed and update dependencies
        if old_commit and self._check_requirements_changed(old_commit):
            bt.logging.info("requirements.txt changed, updating dependencies...")
            self._update_dependencies()
        else:
            bt.logging.info("No dependency changes detected")
        
        # Restart PM2 process
        bt.logging.info("Restarting PM2 validator process...")
        if not self._restart_pm2_process(self.validator_name):
            return False
        
        # Wait for process to become healthy
        bt.logging.info("Waiting for validator to become healthy...")
        if not self._wait_for_process_healthy(self.validator_name):
            return False
        
        bt.logging.info("=== Auto-Update Complete ===")
        return True
    
    def _update_loop(self):
        """Main update loop that runs in a separate thread."""
        bt.logging.info(f"Auto-updater started. Checking for updates every {self.check_interval_seconds / 3600:.1f} hours")
        
        # Wait a bit before first check to let validator fully start
        time.sleep(300)  # 5 minutes initial delay
        
        while self.running:
            try:
                # Check for updates
                if self._check_for_updates():
                    bt.logging.info("Updates available. Performing update...")
                    self.perform_update()
                else:
                    bt.logging.debug("No updates available")
                
                # Sleep for the check interval
                time.sleep(self.check_interval_seconds)
                
            except Exception as e:
                bt.logging.error(f"Error in auto-updater loop: {e}")
                # Sleep for a shorter interval on error before retrying
                time.sleep(60)
    
    def start(self):
        """Start the auto-updater in a background thread."""
        if self.running:
            bt.logging.warning("Auto-updater is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        bt.logging.info("Auto-updater thread started")
    
    def stop(self):
        """Stop the auto-updater."""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        bt.logging.info("Auto-updater stopped")

