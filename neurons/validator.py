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

import copy
import json
import sys
import os
# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import torch
import numpy as np
import asyncio
import threading
import time
import os
import wandb
import subprocess
import traceback
from common.metagraph_syncer import MetagraphSyncer
from neurons.config import NeuronType, check_config, create_config
from dynamic_desirability.desirability_retrieval import sync_run_retrieval
from neurons import __spec_version__ as spec_version
from vali_utils.validator_s3_access import ValidatorS3Access
from rewards.data_value_calculator import DataValueCalculator
from rich.table import Table
from rich.console import Console
import warnings
import requests
from dotenv import load_dotenv
import bittensor as bt
from typing import Tuple
from common.organic_protocol import OrganicRequest
from common import constants
from common import utils
from vali_utils.miner_evaluator import MinerEvaluator
from vali_utils.load_balancer.validator_registry import ValidatorRegistry
from vali_utils.organic_query_processor import OrganicQueryProcessor

from vali_utils import metrics

# Import zipcode validation components
from common.resi_api_client import create_api_client
from rewards.zipcode_competitive_scorer import ZipcodeCompetitiveScorer
from vali_utils.multi_tier_validator import MultiTierValidator
from vali_utils.deterministic_consensus import DeterministicConsensus
from common.auto_updater import AutoUpdater

load_dotenv()
# Filter annoying bittensor trace logs
original_trace = bt.logging.trace

def filtered_trace(message, *args, **kwargs):
    if "Unexpected header key encountered" not in message:
        original_trace(message, *args, **kwargs)

bt.logging.trace = filtered_trace

# Filter deprecation warning and import datetime
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="datetime.datetime.utcnow() is deprecated"
)
import datetime as dt
from datetime import datetime, timezone

bt.logging.set_trace(True)


class Validator:
    def __init__(
        self,
        metagraph_syncer: MetagraphSyncer,
        evaluator: MinerEvaluator,
        uid: int,
        config=None,
        subtensor: bt.subtensor = None,
    ):
        """

        Args:
            metagraph_syncer (MetagraphSyncer): The syncer must already be initialized, with the initial metagraphs synced.
            evaluator (MinerEvaluator): The evaluator to evaluate miners.
            uid (int): The uid of the validator.
            config (_type_, optional): _description_. Defaults to None.
            subtensor (bt.subtensor, optional): _description_. Defaults to None.
        """
        self.metagraph_syncer = metagraph_syncer
        self.evaluator = evaluator
        self.uid = uid

        self.config = copy.deepcopy(config or create_config(NeuronType.VALIDATOR))
        check_config(self.config)

        # Auto-configure S3 auth URL based on subnet
        if self.config.netuid == 428:  # Testnet
            if self.config.s3_auth_url == "https://api.resilabs.ai":  # Default mainnet URL
                self.config.s3_auth_url = "https://api-staging.resilabs.ai"
                bt.logging.info(f"Auto-configured testnet S3 auth URL: {self.config.s3_auth_url}")
        else:  # Mainnet or other subnets
            if not hasattr(self.config, 's3_auth_url') or not self.config.s3_auth_url:
                self.config.s3_auth_url = "https://api.resilabs.ai"
                bt.logging.info(f"Auto-configured mainnet S3 auth URL: {self.config.s3_auth_url}")

        bt.logging.info(self.config)

        # The wallet holds the cryptographic key pairs for the miner.
        self.wallet = bt.wallet(config=self.config)
        bt.logging.info(f"Wallet: {self.wallet}.")

        # The subtensor is our connection to the Bittensor blockchain.
        self.subtensor = subtensor or bt.subtensor(config=self.config)
        bt.logging.info(f"Subtensor: {self.subtensor}.")

        # The metagraph holds the state of the network, letting us know about other validators and miners.
        self.metagraph = self.metagraph_syncer.get_metagraph(self.config.netuid)
        self.metagraph_syncer.register_listener(
            self._on_metagraph_updated, netuids=[self.config.netuid]
        )
        bt.logging.info(f"Metagraph: {self.metagraph}.")
        
        self.validator_registry = ValidatorRegistry(metagraph=self.metagraph, organic_whitelist=self.config.organic_whitelist)
        self.organic_processor = None

        # Create asyncio event loop to manage async tasks.
        self.loop = asyncio.get_event_loop()
        self.axon = None
        self.api = None
        self.step = 0
        self.wandb_run_start = None
        self.wandb_run = None

        # Instantiate runners
        self.should_exit: bool = False
        self.is_running: bool = False
        self.thread: threading.Thread = None
        self.lock = threading.RLock()
        self.last_eval_time = dt.datetime.utcnow()
        self.last_weights_set_time = dt.datetime.utcnow()
        self.last_weights_set_block = 0  # Track the block when weights were last set
        self.is_setup = False

        # Add counter for evaluation cycles since startup
        self.evaluation_cycles_since_startup = 0
        
        # Initialize zipcode validation components (enabled by default)
        self.zipcode_validation_enabled = not getattr(self.config, 'disable_zipcode_mining', False)
        self.api_client = None
        self.zipcode_scorer = None
        self.multi_tier_validator = None
        self.consensus_manager = None
        self.current_epoch_data = None
        
        if self.zipcode_validation_enabled:
            try:
                # Validate proxy configuration for production
                self._validate_proxy_configuration()
                
                self.api_client = create_api_client(self.config, self.wallet)
                self.zipcode_scorer = ZipcodeCompetitiveScorer()
                self.multi_tier_validator = MultiTierValidator()
                self.consensus_manager = DeterministicConsensus()
                
                # Configure proxy for scraper if provided
                if hasattr(self.config, 'proxy_url') and self.config.proxy_url:
                    self._configure_scraper_proxy()
                
                # Configure ScrapingBee if enabled
                if hasattr(self.config, 'use_scrapingbee') and self.config.use_scrapingbee:
                    self._configure_scrapingbee()
                
                # Configure BrightData if enabled
                if hasattr(self.config, 'use_brightdata') and self.config.use_brightdata:
                    self._configure_brightdata()
                
                bt.logging.success("Zipcode validation system initialized")
                
                # Test API connectivity
                health = self.api_client.check_health()
                if health.get('status') == 'ok':
                    bt.logging.success(f"API server connected: {health.get('service', 'Unknown')}")
                else:
                    bt.logging.warning("API server health check failed, but continuing...")
                    
            except Exception as e:
                bt.logging.error(f"Failed to initialize zipcode validation system: {e}")
                bt.logging.warning("Continuing without zipcode validation functionality")
                self.zipcode_validation_enabled = False

    def _validate_proxy_configuration(self):
        """
        Validate proxy configuration for production validators
        
        Validators can use proxies for Tier 3 spot-check validation to avoid IP bans
        from real estate websites during scraping verification.
        """
        # Check if proxy is configured
        has_proxy = hasattr(self.config, 'proxy_url') and self.config.proxy_url
        has_scrapingbee = hasattr(self.config, 'use_scrapingbee') and self.config.use_scrapingbee
        
        # For mainnet (netuid 46), strongly recommend proxy or ScrapingBee
        if self.config.netuid == 46:  # Mainnet
            if not has_proxy and not has_scrapingbee:
                bt.logging.warning("⚠️  NO PROXY CONFIGURED: Scraping without proxy may result in IP bans and rate limits")
                bt.logging.warning("   Recommended options:")
                bt.logging.warning("   1. Add proxy: --proxy_url http://username:password@proxy-server:port")
                bt.logging.warning("   2. Use ScrapingBee: --use_scrapingbee (requires SCRAPINGBEE_API_KEY env var)")
                bt.logging.warning("   Recommended proxy: Webshare.io Rotating Residential Proxies (100GB+ plan)")
                bt.logging.warning("   Continuing without proxy - spot-check validation may be unreliable")
            elif has_scrapingbee:
                bt.logging.success(f"✅ ScrapingBee configured for scraping")
            elif has_proxy:
                bt.logging.success(f"✅ Proxy configured: {self.config.proxy_url.split('@')[-1] if '@' in self.config.proxy_url else self.config.proxy_url}")
            
        # For testnet, proxy is optional
        elif self.config.netuid == 428:  # Testnet
            if has_scrapingbee:
                bt.logging.info(f"🔄 Testnet ScrapingBee configured")
            elif has_proxy:
                bt.logging.info(f"🔄 Testnet proxy configured: {self.config.proxy_url.split('@')[-1] if '@' in self.config.proxy_url else self.config.proxy_url}")
            else:
                bt.logging.info("ℹ️  No proxy configured for testnet - direct scraping will be attempted")
                bt.logging.info("   Consider adding: --proxy_url or --use_scrapingbee for production-like testing")

    def _configure_scraper_proxy(self):
        """
        Configure proxy settings for the validator's scraper components
        
        This ensures that Tier 3 spot-check validation uses the proxy
        to avoid IP bans from real estate websites.
        """
        try:
            import os
            
            # Set proxy environment variables for scrapers
            proxy_url = self.config.proxy_url
            
            # Handle proxy with authentication
            if hasattr(self.config, 'proxy_username') and self.config.proxy_username:
                if hasattr(self.config, 'proxy_password') and self.config.proxy_password:
                    # Format: http://username:password@proxy:port
                    if '://' in proxy_url:
                        protocol, rest = proxy_url.split('://', 1)
                        proxy_url = f"{protocol}://{self.config.proxy_username}:{self.config.proxy_password}@{rest}"
                    else:
                        proxy_url = f"http://{self.config.proxy_username}:{self.config.proxy_password}@{proxy_url}"
            
            # Set environment variables for HTTP requests
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            os.environ['http_proxy'] = proxy_url
            os.environ['https_proxy'] = proxy_url
            
            bt.logging.success("✅ Scraper proxy configuration applied")
            
        except Exception as e:
            bt.logging.error(f"Failed to configure scraper proxy: {e}")
            bt.logging.warning("Continuing without proxy - may encounter rate limits")

    def _configure_scrapingbee(self):
        """
        Configure ScrapingBee API settings for the validator's scraper components
        
        This ensures that scrapers can use ScrapingBee API for better success rates
        and to avoid IP bans from real estate websites.
        """
        try:
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            # Check if ScrapingBee API key is available
            api_key = os.getenv("SCRAPINGBEE_API_KEY")
            if not api_key:
                bt.logging.error("❌ SCRAPINGBEE_API_KEY not found in environment variables")
                bt.logging.error("   Add SCRAPINGBEE_API_KEY to your .env file or environment")
                bt.logging.error("   Get your API key from: https://www.scrapingbee.com/")
                raise ValueError("ScrapingBee API key required when --use_scrapingbee is enabled")
            
            bt.logging.success("✅ ScrapingBee API configured successfully")
            bt.logging.info("   Using ScrapingBee for validator scraping operations")
            
        except Exception as e:
            bt.logging.error(f"Failed to configure ScrapingBee: {e}")
            bt.logging.warning("Disabling ScrapingBee - falling back to proxy/direct requests")
            self.config.use_scrapingbee = False

    def _configure_brightdata(self):
        """
        Configure BrightData API settings for the validator's scraper components
        """
        try:
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            # Check if BrightData API key is available
            api_key = os.getenv("BRIGHTDATA_API_KEY")
            if not api_key:
                bt.logging.error("❌ BRIGHTDATA_API_KEY not found in environment variables")
                bt.logging.error("   Add BRIGHTDATA_API_KEY to your .env file or environment")
                bt.logging.error("   Get your API key from: https://brightdata.com/")
                raise ValueError("BrightData API key required when --use_brightdata is enabled")
            
            bt.logging.success("✅ BrightData API configured successfully")
            bt.logging.info("   Using BrightData for validator scraping operations")
            
        except Exception as e:
            bt.logging.error(f"Failed to configure BrightData: {e}")
            bt.logging.warning("Disabling BrightData - falling back to proxy/direct requests")
            self.config.use_brightdata = False

    def setup(self):
        """A one-time setup method that must be called before the Validator starts its main loop."""
        assert not self.is_setup, "Validator already setup."

        if self.config.wandb.on or not self.config.wandb.off:
            try:
                self.new_wandb_run()
            except Exception as e:
                bt.logging.exception("W&B init failed; will retry later.")
                # Do NOT flip wandb.off here; just remember there is no active run.
                self.wandb_run = None
                self.wandb_run_start = None

        metrics.VALIDATOR_INFO.info({
            "hotkey": self.wallet.hotkey.ss58_address,
            "uid": str(self.uid),
            "netuid": str(self.config.netuid),
            "version": self.get_version_tag(),
        })

        # Load any state from previous runs.
        self.load_state()

        # Getting latest dynamic lookup
        self.get_updated_lookup()

        # Serve axon to enable external connections.
        if not self.config.neuron.axon_off:
            self.serve_axon()
        else:
            bt.logging.warning("Axon off, not serving ip to chain.")

        self.organic_processor = OrganicQueryProcessor(
            wallet=self.wallet,
            metagraph=self.metagraph,
            evaluator=self.evaluator
        )
        
        self.is_setup = True

    def get_updated_lookup(self):
        try:
            t_start = time.perf_counter()
            bt.logging.info("Retrieving the latest dynamic lookup...")
            model = sync_run_retrieval(self.config)
            bt.logging.info("Model retrieved, updating value calculator...")
            self.evaluator.scorer.value_calculator = DataValueCalculator(model=model)
            bt.logging.info(f"Evaluator: {self.evaluator.scorer.value_calculator}")
            bt.logging.info(f"Updated dynamic lookup at {dt.datetime.utcnow()}")

            duration = time.perf_counter() - t_start

            metrics.DYNAMIC_DESIRABILITY_RETRIEVAL_PROCESS_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address).set(duration)
            metrics.DYNAMIC_DESIRABILITY_RETRIEVAL_LAST_SUCCESSFUL_TS.labels(hotkey=self.wallet.hotkey.ss58_address).set(int(time.time()))
        except Exception as e:
            bt.logging.error(f"Error in get_updated_lookup: {str(e)}")
            bt.logging.exception("Exception details:")

    def get_version_tag(self):
        """Fetches version tag"""
        try:
            subprocess.run(['git', 'fetch', '--tags'], check=True)
            version_tag = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0']).strip().decode('utf-8')
            return version_tag
        
        except subprocess.CalledProcessError as e:
            print(f"Couldn't fetch latest version tag: {e}")
            return "error"
        
    def get_scraper_providers(self):
        """Fetches a validator's scraper providers to display in WandB logs."""
        scrapers = self.evaluator.PREFERRED_SCRAPERS
        return scrapers

    def new_wandb_run(self):
        """Creates a new wandb run to save information to."""
        # Create a unique run id for this run.
        now = dt.datetime.now()
        run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
        name = "validator-" + str(self.uid) + "-" + run_id
        version_tag = self.get_version_tag()
        scraper_providers = self.get_scraper_providers()
    
        # Allow multiple runs in one process and only set start time after success
        self.wandb_run = wandb.init(
            name=name,
            project="resi-validators",
            entity="resi-labs-ai",
            config={
                "uid": self.uid,
                "hotkey": self.wallet.hotkey.ss58_address,
                "run_name": run_id,
                "type": "validator",
                "version": version_tag,
                "scrapers": scraper_providers
            },
            allow_val_change=True,
            anonymous="allow",
            reinit=True,
            resume="never", # force a brand-new run ID on each rotation
            settings=wandb.Settings(start_method="thread"),
        )
    
        # Start time after successful init so rotation scheduling is correct
        self.wandb_run_start = now
    
        bt.logging.debug(f"Started a new wandb run: {name}")


    def run(self):
        """
        Initiates and manages the main loop for the validator, which
    
        1. Evaluates miners
        2. Periodically writes the latest scores to the chain
        3. Saves state
        """
        assert self.is_setup, "Validator must be setup before running."
    
        # Check that validator is registered on the network.
        utils.assert_registered(self.wallet, self.metagraph)
    
        bt.logging.info(
            f"Running validator {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}."
        )
    
        bt.logging.info(f"Validator starting at block: {self.block}.")
    
        while not self.should_exit:
            try:
                t_start = time.perf_counter()
    
                bt.logging.debug(
                    f"Validator running on step({self.step}) block({self.block})."
                )
    
                # Ensure validator hotkey is still registered on the network.
                utils.assert_registered(self.wallet, self.metagraph)
    
                # Evaluate the next batch of miners.
                next_batch_delay_secs = self.loop.run_until_complete(
                    self.evaluator.run_next_eval_batch()
                )
                self._on_eval_batch_complete()
    
                # Maybe set weights.
                if self.should_set_weights():
                    self.set_weights()
    
                # Always save state.
                self.save_state()
    
                # Update to the latest desirability list after each evaluation.
                self.get_updated_lookup()
    
                self.step += 1
    
                metrics.MAIN_LOOP_ITERATIONS_TOTAL.labels(hotkey=self.wallet.hotkey.ss58_address).inc()
                metrics.MAIN_LOOP_LAST_SUCCESS_TS.labels(hotkey=self.wallet.hotkey.ss58_address).set(int(time.time()))
                metrics.MAIN_LOOP_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address).set(time.perf_counter() - t_start)
    
                wait_time = max(0.0, float(next_batch_delay_secs))
                if wait_time > 0:
                    bt.logging.info(
                        f"Finished full evaluation loop early. Waiting {wait_time} seconds until running next evaluation loop."
                    )
                    time.sleep(wait_time)
    
                if (self.config.wandb.on or not self.config.wandb.off) and self.wandb_run is None:
                    try:
                        self.new_wandb_run()
                        bt.logging.info("W&B: started new run successfully")
                    except Exception as e:
                        bt.logging.error(f"W&B init retry failed: {e}")

                # Rotation with retry (only when we actually have a start time)
                if (self.config.wandb.on or not self.config.wandb.off) and (self.wandb_run_start is not None) and \
                ((dt.datetime.now() - self.wandb_run_start) >= dt.timedelta(hours=3)):

                    try:
                        self.new_wandb_run()
                        bt.logging.info("W&B: rotated run successfully")
                    except Exception as e:
                        bt.logging.error(f"W&B rotation failed; keeping current run active: {e}")

            except KeyboardInterrupt:
                self.axon.stop()
                if self.wandb_run:
                    self.wandb_run.finish()
            except Exception as err:
                metrics.MAIN_LOOP_ERRORS_TOTAL.labels(hotkey=self.wallet.hotkey.ss58_address).inc()
                bt.logging.error("Error during validation", str(err))

    def run_in_background_thread(self):
        """
        Starts the validator's operations in a background thread upon entering the context.
        This method facilitates the use of the validator in a 'with' statement.
        """

        # Setup the Validator.
        self.setup()

        if not self.is_running:
            bt.logging.debug("Starting validator in background thread.")
            self.should_exit = False
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.is_running = True
            bt.logging.debug("Started.")

    def stop_run_thread(self):
        """
        Stops the validator's operations that are running in the background thread.
        """
        if self.is_running:
            bt.logging.debug("Stopping validator in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped.")

    def __enter__(self):
        self.run_in_background_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Stops the validator's background operations upon exiting the context.
        This method facilitates the use of the validator in a 'with' statement.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
                      None if the context was exited without an exception.
            exc_value: The instance of the exception that caused the context to be exited.
                       None if the context was exited without an exception.
            traceback: A traceback object encoding the stack trace.
                       None if the context was exited without an exception.
        """
        if self.is_running:
            bt.logging.debug("Stopping validator in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False

            # Cleanup loggers
            if self.wandb_run:
                self.wandb_run.finish()
            bt.logging.debug("Stopped.")

    def serve_axon(self):
        """Serve axon to enable external connections."""

        try:
            self.axon = bt.axon(wallet=self.wallet, config=self.config)
            # Import and attach organic synapse
            self.axon.attach(
                forward_fn=self.process_organic_query,
                blacklist_fn=self.organic_blacklist,
                priority_fn=self.organic_priority
            )

            self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor).start()
            if self.config.neuron.api_on:
                try:
                    bt.logging.info("Starting Validator API...")
                    from vali_utils.api.server import ValidatorAPI
                    self.api = ValidatorAPI(self, port=self.config.neuron.api_port)
                    self.api.start()
                    # Start monitoring to auto-restart if it fails
                    self._start_api_monitoring()

                except ValueError as e:
                    bt.logging.error(f"Failed to start API: {str(e)}")
                    bt.logging.info("Validator will continue running without API.")
                    self.config.neuron.api_on = False

            bt.logging.info(
                f"Serving validator axon {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}."
            )
        except Exception as e:
            bt.logging.error(f"Failed to setup Axon: {e}.")
            sys.exit(1)

    def _on_metagraph_updated(self, metagraph: bt.metagraph, netuid: int):
        """Processes an update to the metagraph"""
        with self.lock:
            assert netuid == self.config.netuid
            self.metagraph = copy.deepcopy(metagraph)

        # Validator Health Checks
        hotkey = self.wallet.hotkey.ss58_address

        # Resolve current UID from hotkey (survives dereg/re-reg)
        try:
            uid = metagraph.hotkeys.index(hotkey)
            registered = 1
        except ValueError:
            uid = None
            registered = 0

        metrics.BITTENSOR_VALIDATOR_REGISTERED.labels(hotkey=hotkey).set(registered)

        # Set vtrust + block diff since last update only when registered; otherwise zero them
        if registered:
            try:
                vtrust = float(metagraph.validator_trust[uid])
            except Exception:
                vtrust = 0.0

            try:
                head_block = int(getattr(metagraph, "block", 0))
                last_update = int(metagraph.last_update[uid])
                block_diff = max(0, head_block - last_update) if head_block and last_update else 0
            except Exception:
                block_diff = 0
        else:
            vtrust = 0.0
            block_diff = 0

        metrics.BITTENSOR_VALIDATOR_VTRUST.labels(hotkey=hotkey).set(vtrust)
        metrics.BITTENSOR_VALIDATOR_BLOCK_DIFFERENCE.labels(hotkey=hotkey).set(block_diff)
        metrics.METAGRAPH_LAST_UPDATE_TS.labels(hotkey=hotkey).set(int(time.time()))

    def _on_eval_batch_complete(self):
        with self.lock:
            self.evaluation_cycles_since_startup += 1
            self.last_eval_time = dt.datetime.utcnow()

    def is_healthy(self) -> bool:
        """Returns true if the validator is healthy and is evaluating Miners."""
        with self.lock:
            return dt.datetime.utcnow() - self.last_eval_time < dt.timedelta(minutes=35)

    def should_set_weights(self) -> bool:
        # Check if enough epoch blocks have elapsed since the last epoch.
        if self.config.neuron.disable_set_weights:
            return False

        with self.lock:
            current_block = self.block
            blocks_per_weight_cycle = 1200  # Set weights every 1200 blocks (4 hours)
            
            # Calculate blocks since last weight setting
            blocks_since_last_weights = current_block - self.last_weights_set_block
            
            if self.last_weights_set_block == 0:
                epoch_length = self.config.neuron.epoch_length
                min_blocks_required = max(epoch_length, blocks_per_weight_cycle)
                if blocks_since_last_weights < min_blocks_required:
                    bt.logging.debug(
                        f"First weight setting: waiting for {min_blocks_required} blocks "
                        f"(epoch_length={epoch_length}, blocks_per_weight_cycle={blocks_per_weight_cycle}), "
                        f"current={blocks_since_last_weights}"
                    )
                    return False
                bt.logging.info(
                    f"First weight setting: current_block={current_block}, "
                    f"blocks_since_start={blocks_since_last_weights}, "
                    f"min_blocks_required={min_blocks_required}"
                )
                return True
            
            # Check if 3600 blocks have passed since last weight setting
            if blocks_since_last_weights >= blocks_per_weight_cycle:
                bt.logging.info(
                    f"{blocks_per_weight_cycle}-block cycle reached: current_block={current_block}, "
                    f"last_weights_set_block={self.last_weights_set_block}, "
                    f"blocks_since_last_weights={blocks_since_last_weights}"
                )
                return True
            
            # Log current status for debugging
            bt.logging.debug(
                f"Weight setting check: current_block={current_block}, "
                f"last_weights_set_block={self.last_weights_set_block}, "
                f"blocks_since_last_weights={blocks_since_last_weights}, "
                f"blocks_per_weight_cycle={blocks_per_weight_cycle}"
            )
            
            return False

    def _start_api_monitoring(self):
        """Start a lightweight monitor to auto-restart API if it becomes unreachable"""

        master_key = os.getenv('MASTER_KEY')

        def monitor_api():
            consecutive_failures = 0
            max_failures = 3  # Restart after 3 consecutive failures

            while not self.should_exit:
                if not hasattr(self, 'api') or not self.api:
                    time.sleep(60 * 20)
                    continue

                try:
                    # Try a simple local request to check if API is responding
                    response = requests.get(
                        f"http://localhost:{self.config.neuron.api_port}/api/v1/monitoring/system-status",
                        headers={"X-API-Key": master_key},
                        timeout=10
                    )

                    if response.status_code == 200:
                        # API is working, reset failure counter
                        consecutive_failures = 0
                    else:
                        # HTTP error
                        consecutive_failures += 1
                        bt.logging.warning(f"API health check returned status {response.status_code}")
                except requests.RequestException:
                    # Connection error (most likely API is down)
                    consecutive_failures += 1
                    bt.logging.warning(f"API server not responding ({consecutive_failures}/{max_failures})")

                # If too many consecutive failures, restart API
                if consecutive_failures >= max_failures:
                    bt.logging.warning(f"API server unresponsive for {consecutive_failures} checks, restarting...")

                    try:
                        # Stop API if it's running
                        if hasattr(self.api, 'stop'):
                            self.api.stop()

                        # Wait a moment
                        time.sleep(2)

                        # Start API again
                        if hasattr(self.api, 'start'):
                            self.api.start()

                        bt.logging.info("API server restarted")
                        consecutive_failures = 0
                    except Exception as e:
                        bt.logging.error(f"Error restarting API server: {str(e)}")

                # Check every 30 minutes
                time.sleep(30 * 60)

        # Start monitoring in background thread
        thread = threading.Thread(target=monitor_api, daemon=True)
        thread.start()
        bt.logging.info("API monitoring started")

    def set_weights(self):
        """
        Sets the validator weights to the metagraph hotkeys based on the scores it has received from the miners. The weights determine the trust and incentive level the validator assigns to miner nodes on the network.
        """
        bt.logging.info("Attempting to set weights.")

        scorer = self.evaluator.get_scorer()
        scores = scorer.get_scores()
        credibilities = scorer.get_credibilities()

        # Check if scores contains any NaN values and log a warning if it does.
        if torch.isnan(scores).any():
            bt.logging.warning(
                f"Scores contain NaN values. This may be due to a lack of responses from miners, or a bug in your reward functions."
            )

        # Calculate the average reward for each uid across non-zero values.
        # Replace any NaN values with 0.
        raw_weights = torch.nn.functional.normalize(scores, p=1, dim=0)

        # Calculate what 75% of total weight would be
        total_weight = raw_weights.sum().item()
        burn_weight_portion = 0.75 * total_weight  # 75% goes to burn

        # Create new weights array with burn entry
        final_weights = torch.zeros(len(raw_weights) + 1, dtype=torch.float32)

        # Set burn weight (75% of total)
        final_weights[0] = burn_weight_portion
        
        if final_weights[0] == 0:
            final_weights[0] = 1

        # Set miner weights (25% of original weights, proportionally distributed)
        remaining_weight = total_weight - burn_weight_portion
        if remaining_weight > 0:
            # Scale down miner weights proportionally to fill remaining 25%
            miner_weights = raw_weights * (remaining_weight / raw_weights.sum().item())
            final_weights[1:] = miner_weights

        # Create corresponding UIDs array with burn UID first
        uids_np = np.array(self.metagraph.uids, dtype=np.int64)
        final_uids = np.concatenate([[238], uids_np])

        # set self.uid weight to 0 if not already
        if self.uid < len(self.metagraph.uids) and self.uid + 1 < len(final_weights):
            if final_weights[self.uid + 1] != 0:
                final_weights[self.uid + 1] = 0

        bt.logging.info(f"Burn applied: 75% of total weight ({burn_weight_portion:.4f}) redirected to UID 238")

        # Extend credibilities to match (burn entry has no credibility)
        extended_credibilities = torch.cat([torch.tensor([0.0]), credibilities.squeeze()])

        # Use final weights instead of raw_weights for processing
        raw_weights = final_weights

        # Process the raw weights to final_weights via subtensor limitations.
        (
            processed_weight_uids,
            processed_weights,
        ) = bt.utils.weight_utils.process_weights_for_netuid(
            uids=torch.tensor(final_uids, dtype=torch.int64).to("cpu"),
            weights=raw_weights.detach().cpu().numpy().astype(np.float32),
            netuid=self.config.netuid,
            subtensor=self.subtensor,
            metagraph=self.metagraph,
        )

        table = Table(title="All Weights")
        table.add_column("uid", justify="right", style="cyan", no_wrap=True)
        table.add_column("weight", style="magenta")
        table.add_column("score", style="magenta")
        table.add_column("credibility", style="magenta")
        uids_and_weights = list(
            zip(processed_weight_uids.tolist(), processed_weights.tolist())
        )
        # Sort by weights descending.
        sorted_uids_and_weights = sorted(
            uids_and_weights, key=lambda x: x[1], reverse=True
        )
        for uid, weight in sorted_uids_and_weights:
            # Handle burn UID (238) specially in display
            if uid == 238:
                table.add_row(
                    str(uid) + " (BURN)",
                    str(round(weight, 4)),
                    "BURN",
                    "N/A",
                )
            else:
                # Display original score for miner UIDs
                original_score = scores[uid].item() if uid < len(scores) else 0
                table.add_row(
                    str(uid),
                    str(round(weight, 4)),
                    str(int(original_score)),
                    str(round(extended_credibilities[uid + 1].item(), 4)),
                )
        console = Console()
        console.print(table)


        # Set the weights on chain via our subtensor connection.
        t0 = time.perf_counter()
        success, message = self.subtensor.set_weights(
            wallet=self.wallet,
            netuid=self.config.netuid,
            uids=processed_weight_uids,
            weights=processed_weights,
            wait_for_finalization=False,
            version_key=spec_version,
        )
        
        with self.lock:
            self.last_weights_set_time = dt.datetime.utcnow()
            self.last_weights_set_block = self.block

        bt.logging.success("Finished setting weights.")

        metric_status = 'ok' if success else 'fail'
        metrics.SET_WEIGHTS_SUBTENSOR_DURATION.labels(hotkey=self.wallet.hotkey.ss58_address, status=metric_status).observe(time.perf_counter() - t0)
        metrics.SET_WEIGHTS_LAST_TS.labels(hotkey=self.wallet.hotkey.ss58_address, status=metric_status).set(int(time.time()))

    @property
    def block(self):
        return utils.ttl_get_block(self)

    def save_state(self):
        """Saves the state of the validator to a file."""
        bt.logging.trace("Saving validator state.")

        self.evaluator.save_state()

    def load_state(self):
        """Loads the state of the validator from a file."""
        bt.logging.info("Loading validator state.")

        self.evaluator.load_state()

    async def process_organic_query(self, synapse: OrganicRequest) -> OrganicRequest:
        """
        Process organic queries through the validator axon.
        Delegates to OrganicQueryProcessor for actual processing.
        """
        if not self.organic_processor:
            synapse.status = "error"
            synapse.meta = {"error": "Organic query processor not initialized"}
            synapse.data = []
            return synapse
        
        t_start = time.perf_counter() 
        self.organic_processor.update_metagraph(self.evaluator.metagraph)
        synapse_resp = await self.organic_processor.process_organic_query(synapse)

        metrics.ORGANIC_QUERY_PROCESS_DURATION.labels(request_source=synapse.source, response_status=synapse_resp.status).observe(time.perf_counter() - t_start)

        try:
            json_str = json.dumps(synapse_resp.data)
            size_bytes = len(json_str.encode('utf-8'))

            metrics.ORGANIC_QUERY_RESPONSE_SIZE.labels(request_source=synapse.source, response_status=synapse_resp.status).observe(size_bytes)
        except (TypeError, ValueError) as e:  # JSON serialization errors
            bt.logging.debug("Failed to serialize synapse response data to JSON. Skipping metrics.ORGANIC_QUERY_RESPONSE_BYTES observation")

        metrics.ORGANIC_QUERY_REQUESTS_TOTAL.labels(request_source=synapse.source, response_status=synapse_resp.status).inc()
        return synapse_resp

    async def organic_blacklist(self, synapse: OrganicRequest) -> Tuple[bool, str]:
        """
        Simplified blacklist function that only checks whitelist membership
        """
        # Only allow hotkeys in the whitelist
        if hasattr(self.config, 'organic_whitelist') and self.config.organic_whitelist:
            if synapse.dendrite.hotkey in self.config.organic_whitelist:
                return False, "Request accepted from whitelisted hotkey"
            else:
                return True, f"Sender {synapse.dendrite.hotkey} not in whitelist"

        # If no whitelist is defined, reject all requests
        return True, "No whitelist configured"

    def organic_priority(self, synapse: OrganicRequest) -> float:
        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        priority = float(self.metagraph.S[caller_uid])
        bt.logging.trace(
            f"Prioritizing {synapse.dendrite.hotkey} with value: {priority}.",
        )
        return priority
    
    def run_epoch_validation(self):
        """
        Deterministic epoch validation ensuring all validators reach same results
        
        This method:
        1. Waits for epoch completion
        2. Downloads miner submissions from S3
        3. Processes each zipcode with multi-tier validation
        4. Calculates proportional weights
        5. Verifies consensus with other validators
        6. Updates Bittensor weights
        """
        if not self.zipcode_validation_enabled or not self.api_client:
            bt.logging.warning("Zipcode validation not enabled")
            return
        
        bt.logging.info("Starting epoch validation cycle...")
        
        while not self.should_exit:
            try:
                # Wait for epoch to complete
                current_epoch = self.api_client.get_current_epoch_info()
                
                if not current_epoch:
                    bt.logging.info("No current epoch available, waiting...")
                    time.sleep(300)  # Wait 5 minutes
                    continue
                
                epoch_id = current_epoch.get('id')
                epoch_status = current_epoch.get('status')
                
                # Check if epoch is completed or near completion
                if epoch_status == 'ACTIVE':
                    # Wait for epoch to complete
                    time_until_end = current_epoch.get('timeUntilEpochEnd', 0)
                    if time_until_end > 300:  # More than 5 minutes left
                        bt.logging.info(f"Epoch {epoch_id} still active, waiting {time_until_end}s")
                        time.sleep(min(300, time_until_end))
                        continue
                
                # Check if this is a new epoch we haven't processed
                if (not self.current_epoch_data or 
                    self.current_epoch_data.get('epoch_id') != epoch_id):
                    
                    bt.logging.info(f"Processing completed epoch: {epoch_id}")
                    
                    # Download epoch submissions by zipcode
                    zipcode_submissions = self.download_epoch_submissions_by_zipcode(epoch_id)
                    
                    if not zipcode_submissions:
                        bt.logging.warning(f"No submissions found for epoch {epoch_id}")
                        time.sleep(300)
                        continue
                    
                    # Get epoch nonce for deterministic validation
                    epoch_nonce = current_epoch.get('nonce', epoch_id)
                    
                    # Process each zipcode with multi-tier validation
                    all_zipcode_results = []
                    
                    for zipcode, submissions in zipcode_submissions.items():
                        bt.logging.info(f"Validating {len(submissions)} submissions for zipcode {zipcode}")
                        
                        # Get expected listings for this zipcode
                        expected_listings = self.get_expected_listings_for_zipcode(zipcode, epoch_id)
                        
                        # Validate and rank submissions for this zipcode
                        zipcode_result = self.zipcode_scorer.validate_and_rank_zipcode_submissions(
                            zipcode=zipcode,
                            submissions=submissions,
                            expected_listings=expected_listings,
                            epoch_nonce=epoch_nonce
                        )
                        
                        all_zipcode_results.append(zipcode_result)
                    
                    # Calculate final proportional weights across all zipcodes
                    final_scores = self.zipcode_scorer.calculate_epoch_proportional_weights(all_zipcode_results)
                    
                    # Calculate consensus hash for verification
                    consensus_hash = self.consensus_manager.calculate_consensus_hash(final_scores, epoch_nonce)
                    
                    # Create validation result with consensus data
                    validation_result = self.consensus_manager.create_validation_result_with_consensus(
                        epoch_id=epoch_id,
                        final_scores=final_scores,
                        zipcode_results=all_zipcode_results,
                        epoch_nonce=epoch_nonce
                    )
                    validation_result['validator_hotkey'] = self.wallet.hotkey.ss58_address
                    
                    # Upload validation results to S3
                    self.upload_validation_results(validation_result)
                    
                    # Verify consensus across validators
                    consensus_result = self.consensus_manager.verify_consensus_across_validators(
                        epoch_id, consensus_hash
                    )
                    
                    # Handle consensus verification
                    if consensus_result['consensus_status'] in ['PERFECT_CONSENSUS', 'MAJORITY_CONSENSUS']:
                        bt.logging.success(f"Consensus achieved: {consensus_result['consensus_status']}")
                        
                        # Update Bittensor weights with final scores
                        self.update_bittensor_weights_from_zipcode_scores(final_scores['miner_scores'])
                        
                        # Store epoch data for next iteration
                        self.current_epoch_data = {
                            'epoch_id': epoch_id,
                            'consensus_hash': consensus_hash,
                            'final_scores': final_scores
                        }
                        
                    else:
                        bt.logging.error(f"Consensus failed: {consensus_result['consensus_status']}")
                        self.consensus_manager.handle_consensus_failure(epoch_id, consensus_result)
                
                # Wait before checking for next epoch
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                bt.logging.error(f"Error in epoch validation cycle: {e}")
                bt.logging.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def download_epoch_submissions_by_zipcode(self, epoch_id: str) -> dict:
        """
        Download and organize miner submissions by zipcode for an epoch
        
        Args:
            epoch_id: Epoch ID to download submissions for
            
        Returns:
            Dict mapping zipcode -> list of miner submissions
        """
        try:
            bt.logging.info(f"Downloading submissions for epoch {epoch_id}")
            
            # Get list of active miners from metagraph
            active_miners = []
            for uid, hotkey in enumerate(self.evaluator.metagraph.hotkeys):
                if self.evaluator.metagraph.S[uid] > 0:  # Has stake
                    active_miners.append(hotkey)
            
            bt.logging.info(f"Checking {len(active_miners)} active miners for epoch {epoch_id} submissions")
            
            # Download submissions from each miner
            zipcode_submissions = {}
            successful_downloads = 0
            
            for miner_hotkey in active_miners:
                try:
                    miner_submissions = self._download_miner_epoch_data(epoch_id, miner_hotkey)
                    
                    if miner_submissions:
                        successful_downloads += 1
                        
                        # Organize by zipcode
                        for zipcode, submission_data in miner_submissions.items():
                            if zipcode not in zipcode_submissions:
                                zipcode_submissions[zipcode] = []
                            
                            # Add miner info to submission
                            submission_data['miner_hotkey'] = miner_hotkey
                            zipcode_submissions[zipcode].append(submission_data)
                            
                        bt.logging.debug(f"Downloaded {len(miner_submissions)} zipcode submissions from {miner_hotkey[:8]}...")
                    
                except Exception as miner_error:
                    bt.logging.debug(f"No epoch data from miner {miner_hotkey[:8]}...: {miner_error}")
                    continue
            
            bt.logging.info(f"Downloaded epoch {epoch_id} data from {successful_downloads} miners across {len(zipcode_submissions)} zipcodes")
            
            return zipcode_submissions
            
        except Exception as e:
            bt.logging.error(f"Failed to download epoch submissions: {e}")
            return {}
    
    def _download_miner_epoch_data(self, epoch_id: str, miner_hotkey: str) -> dict:
        """
        Download epoch data from a specific miner
        
        Args:
            epoch_id: Epoch ID
            miner_hotkey: Miner's hotkey
            
        Returns:
            Dict mapping zipcode -> submission data
        """
        try:
            # Use existing ValidatorS3Access to get miner data
            miner_url = asyncio.run(self.s3_reader.get_miner_specific_access(miner_hotkey))
            
            if not miner_url:
                return {}
            
            # Download and parse S3 file list
            import requests
            response = requests.get(miner_url, timeout=30)
            
            if response.status_code != 200:
                return {}
            
            # Parse S3 XML to find epoch-specific files
            epoch_files = self._parse_epoch_files_from_s3_xml(response.text, epoch_id, miner_hotkey, miner_url)
            
            if not epoch_files:
                return {}
            
            # Download and parse each epoch file
            miner_epoch_data = {}
            
            for file_info in epoch_files:
                try:
                    file_data = self._download_and_parse_epoch_file(file_info)
                    
                    if file_data and 'zipcode' in file_data:
                        zipcode = file_data['zipcode']
                        miner_epoch_data[zipcode] = file_data
                        
                except Exception as file_error:
                    bt.logging.debug(f"Failed to download epoch file {file_info.get('key', 'unknown')}: {file_error}")
                    continue
            
            return miner_epoch_data
            
        except Exception as e:
            bt.logging.debug(f"Error downloading miner epoch data from {miner_hotkey[:8]}...: {e}")
            return {}
    
    def _parse_epoch_files_from_s3_xml(self, xml_content: str, epoch_id: str, miner_hotkey: str, miner_url: str) -> list:
        """
        Parse S3 XML response to find epoch-specific files
        
        Args:
            xml_content: S3 XML response
            epoch_id: Target epoch ID
            miner_hotkey: Miner's hotkey
            miner_url: Base URL for downloading miner files
            
        Returns:
            List of epoch file info
        """
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            namespace = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
            
            epoch_files = []
            
            for content in root.findall('.//s3:Contents', namespace):
                key_elem = content.find('s3:Key', namespace)
                size_elem = content.find('s3:Size', namespace)
                modified_elem = content.find('s3:LastModified', namespace)
                
                if key_elem is not None:
                    key = key_elem.text
                    
                    # Look for epoch-specific files
                    # Expected pattern: data/hotkey={miner_hotkey}/epoch={epoch_id}/zipcode={zipcode}/data_*.json
                    if (f'epoch={epoch_id}' in key and 
                        f'hotkey={miner_hotkey}' in key and 
                        key.endswith('.json')):
                        
                        # Extract zipcode from path
                        zipcode = None
                        if 'zipcode=' in key:
                            zipcode_part = key.split('zipcode=')[1].split('/')[0]
                            zipcode = zipcode_part
                        
                        file_info = {
                            'key': key,
                            'size': int(size_elem.text) if size_elem is not None else 0,
                            'last_modified': modified_elem.text if modified_elem is not None else '',
                            'zipcode': zipcode,
                            'download_url': f"{miner_url.split('?')[0]}/{key}?{miner_url.split('?')[1]}" if '?' in miner_url else f"{miner_url}/{key}"
                        }
                        
                        epoch_files.append(file_info)
            
            return epoch_files
            
        except Exception as e:
            bt.logging.error(f"Error parsing S3 XML for epoch files: {e}")
            return []
    
    def _download_and_parse_epoch_file(self, file_info: dict) -> dict:
        """
        Download and parse an individual epoch file
        
        Args:
            file_info: File information from S3
            
        Returns:
            Parsed file data
        """
        try:
            import requests
            import json
            
            # Download the file
            response = requests.get(file_info['download_url'], timeout=30)
            
            if response.status_code != 200:
                return {}
            
            # Parse JSON data
            file_data = json.loads(response.text)
            
            # Validate required fields
            required_fields = ['epoch_id', 'zipcode', 'miner_hotkey', 'listings']
            if not all(field in file_data for field in required_fields):
                bt.logging.warning(f"Epoch file missing required fields: {file_info['key']}")
                return {}
            
            # Add file metadata
            file_data['file_info'] = {
                'key': file_info['key'],
                'size': file_info['size'],
                'last_modified': file_info['last_modified']
            }
            
            return file_data
            
        except Exception as e:
            bt.logging.error(f"Error downloading epoch file {file_info.get('key', 'unknown')}: {e}")
            return {}
    
    def get_expected_listings_for_zipcode(self, zipcode: str, epoch_id: str) -> int:
        """
        Get expected number of listings for a zipcode in an epoch
        
        Args:
            zipcode: Target zipcode
            epoch_id: Epoch ID
            
        Returns:
            Expected number of listings
        """
        try:
            # First, check if we have cached epoch assignment data
            if (self.current_epoch_data and 
                self.current_epoch_data.get('epoch_id') == epoch_id):
                
                for zipcode_info in self.current_epoch_data.get('zipcodes', []):
                    if zipcode_info['zipcode'] == zipcode:
                        expected = zipcode_info['expectedListings']
                        bt.logging.debug(f"Found cached expected listings for {zipcode}: {expected}")
                        return expected
            
            # If not cached or different epoch, try to get current assignments from API
            if self.api_client:
                try:
                    assignments = self.api_client.get_current_zipcode_assignments()
                    
                    if assignments.get('success') and assignments.get('epochId') == epoch_id:
                        # Cache the assignments for future use
                        self.current_epoch_data = {
                            'epoch_id': epoch_id,
                            'zipcodes': assignments.get('zipcodes', []),
                            'nonce': assignments.get('nonce'),
                            'cached_at': datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Find the specific zipcode
                        for zipcode_info in assignments.get('zipcodes', []):
                            if zipcode_info['zipcode'] == zipcode:
                                expected = zipcode_info['expectedListings']
                                bt.logging.info(f"Retrieved expected listings for {zipcode}: {expected}")
                                return expected
                        
                        bt.logging.warning(f"Zipcode {zipcode} not found in current epoch assignments")
                    else:
                        bt.logging.warning(f"API returned assignments for different epoch or failed")
                        
                except Exception as api_error:
                    bt.logging.error(f"Failed to get zipcode assignments from API: {api_error}")
            
            # Fallback: Use historical average or reasonable default based on zipcode
            default_expected = self._get_default_expected_listings(zipcode)
            bt.logging.warning(f"Using default expected listings for {zipcode}: {default_expected}")
            return default_expected
            
        except Exception as e:
            bt.logging.error(f"Failed to get expected listings for {zipcode}: {e}")
            return 250  # Ultimate fallback
    
    def _get_default_expected_listings(self, zipcode: str) -> int:
        """
        Get reasonable default expected listings based on zipcode characteristics
        
        This could be enhanced with historical data or zipcode population data
        """
        try:
            # For now, use simple heuristics based on zipcode patterns
            # This could be replaced with actual historical data
            
            # Major metropolitan areas (rough approximation)
            major_metro_patterns = [
                '100', '101', '102',  # NYC area
                '900', '901', '902',  # LA area  
                '606', '607', '608',  # Chicago area
                '770', '771', '772',  # Atlanta area
                '191', '192', '193',  # Philadelphia area
            ]
            
            zipcode_prefix = zipcode[:3] if len(zipcode) >= 3 else zipcode
            
            if any(zipcode.startswith(pattern) for pattern in major_metro_patterns):
                return 400  # Higher expected for major metros
            elif zipcode_prefix in ['750', '751', '752', '753']:  # Texas
                return 350
            elif zipcode_prefix in ['330', '331', '332']:  # Florida
                return 300
            else:
                return 250  # Standard default
                
        except Exception as e:
            bt.logging.error(f"Error in default expected listings calculation: {e}")
            return 250
    
    def upload_validation_results(self, validation_result: dict):
        """
        Upload validation results to S3 for consensus verification
        
        Args:
            validation_result: Complete validation result with consensus data
        """
        try:
            epoch_id = validation_result['epoch_id']
            bt.logging.info(f"Uploading validation results for epoch {epoch_id}")
            
            # Get S3 credentials for validator upload
            s3_creds = self.api_client.get_validator_s3_credentials(
                epoch_id=epoch_id,
                purpose="epoch_validation_results"
            )
            
            if not s3_creds.get('success'):
                bt.logging.error("Failed to get validator S3 credentials")
                return False
            
            # Upload validation results to S3 using validator S3 credentials
            upload_success = self._upload_validation_results_to_s3(validation_result, s3_creds)

            if upload_success:
                bt.logging.success(f"Successfully uploaded validation results for epoch {epoch_id}")
                return True
            else:
                bt.logging.error(f"Failed to upload validation results for epoch {epoch_id}")
                return False
            
        except Exception as e:
            bt.logging.error(f"Failed to upload validation results: {e}")
            return False

    def _upload_validation_results_to_s3(self, validation_result: dict, s3_creds: dict) -> bool:
        """
        Upload validation results to S3 using the provided credentials

        Args:
            validation_result: Complete validation result with consensus data
            s3_creds: S3 credentials from API client

        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            # Create temporary file with validation results
            import tempfile

            # Create a filename for the validation results
            epoch_id = validation_result['epoch_id']
            validator_hotkey = validation_result['validator_hotkey']
            timestamp = int(time.time())

            # Create filename: validation_results_epoch_{epoch_id}_{validator_hotkey[:8]}_{timestamp}.json
            filename = f"validation_results_epoch_{epoch_id}_{validator_hotkey[:8]}_{timestamp}.json"
            s3_key = f"validator_results/{filename}"

            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(validation_result, temp_file, indent=2, default=str)
                temp_file_path = temp_file.name

            try:
                # Upload using S3 credentials
                upload_success = self._perform_s3_upload(temp_file_path, s3_key, s3_creds)

                if upload_success:
                    bt.logging.success(f"Validation results uploaded to S3: {s3_key}")
                    return True
                else:
                    bt.logging.error(f"Failed to upload validation results to S3: {s3_key}")
                    return False

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        except Exception as e:
            bt.logging.error(f"Error uploading validation results to S3: {e}")
            return False

    def _perform_s3_upload(self, file_path: str, s3_key: str, s3_creds: dict) -> bool:
        """
        Perform the actual S3 upload using the provided credentials

        Args:
            file_path: Local file path to upload
            s3_key: S3 object key (path in bucket)
            s3_creds: S3 credentials with url and fields

        Returns:
            bool: True if upload successful
        """
        try:
            # Check if credentials have the expected format
            if 'url' not in s3_creds or 'fields' not in s3_creds:
                bt.logging.error(f"Invalid S3 credentials format: missing 'url' or 'fields'")
                return False

            # Prepare form data
            post_data = dict(s3_creds['fields'])
            post_data['key'] = s3_key

            # Upload file
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    s3_creds['url'],
                    data=post_data,
                    files=files,
                    timeout=60  # Longer timeout for potentially large files
                )

            if response.status_code == 204:
                bt.logging.success(f"S3 upload successful: {s3_key}")
                return True
            else:
                bt.logging.error(f"S3 upload failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            bt.logging.error(f"S3 upload exception for {file_path}: {e}")
            return False

    def update_bittensor_weights_from_zipcode_scores(self, miner_scores: dict):
        """
        Update Bittensor weights based on zipcode competitive scores
        
        Args:
            miner_scores: Dict mapping miner hotkey -> normalized score
        """
        try:
            bt.logging.info(f"Updating Bittensor weights for {len(miner_scores)} miners")
            
            # Convert miner scores to weight tensor
            metagraph = self.evaluator.metagraph
            weights = torch.zeros(len(metagraph.hotkeys))
            
            for hotkey, score in miner_scores.items():
                try:
                    uid = metagraph.hotkeys.index(hotkey)
                    weights[uid] = score
                except ValueError:
                    bt.logging.warning(f"Miner {hotkey[:8]} not found in metagraph")
                    continue
            
            # Normalize weights to sum to 1.0
            if weights.sum() > 0:
                weights = weights / weights.sum()
            
            bt.logging.info(f"Setting weights for {(weights > 0).sum()} miners")
            
            # Use existing weight setting mechanism
            self.set_weights(weights)
            
        except Exception as e:
            bt.logging.error(f"Failed to update Bittensor weights: {e}")


def main():
    """Main constructs the validator with its dependencies."""

    config = create_config(NeuronType.VALIDATOR)
    check_config(config=config)

    bt.logging(config=config, logging_dir=config.full_path)

    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(netuid=config.netuid)
    wallet = bt.wallet(config=config)

    # Get the wallet's UID, if registered.
    utils.assert_registered(wallet, metagraph)
    uid = utils.get_uid(wallet, metagraph)

    # Create the metagraph syncer and perform the initial sync.
    metagraph_syncer = MetagraphSyncer(subtensor, config={config.netuid: 20 * 60})
    # Perform an initial sync of all tracked metagraphs.
    metagraph_syncer.do_initial_sync()
    metagraph_syncer.start()

    s3_reader = ValidatorS3Access(wallet=wallet, s3_auth_url=config.s3_auth_url)
    evaluator = MinerEvaluator(
        config=config, uid=uid, metagraph_syncer=metagraph_syncer, s3_reader=s3_reader
    )

    # Initialize auto-updater if enabled
    auto_updater = None
    # argparse converts --auto-update to auto_update in the config
    if getattr(config, 'auto_update', False):
        auto_updater = AutoUpdater(config, check_interval_hours=3.0)
        auto_updater.start()
        bt.logging.info("Auto-updater enabled. Will check for updates every 3 hours.")

    try:
        with Validator(
            metagraph_syncer=metagraph_syncer,
            evaluator=evaluator,
            uid=uid,
            config=config,
            subtensor=subtensor,
        ) as validator:
            while True:
                if not validator.is_healthy():
                    bt.logging.error("Validator is unhealthy. Restarting.")
                    # Sys.exit() may not shutdown the process because it'll wait for other threads
                    # to complete. Use os._exit() instead.
                    os._exit(1)
                bt.logging.trace("Validator running...", time.time())
                time.sleep(60)
    finally:
        # Stop auto-updater when validator exits
        if auto_updater:
            auto_updater.stop()


# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    main()
