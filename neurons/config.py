# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Opentensor Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from enum import auto
import enum
from math import e
import os
import argparse
from pathlib import Path
import bittensor as bt
from loguru import logger
from common import utils

from dotenv import load_dotenv

load_dotenv()


def check_config(config: bt.config):
    r"""Checks/validates the config namespace object."""
    bt.logging.check_config(config)

    full_path = os.path.expanduser(
        "{}/{}/{}/netuid{}/{}".format(
            config.logging.logging_dir,  # TODO: change from ~/.bittensor/miners to ~/.bittensor/neurons
            config.wallet.name,
            config.wallet.hotkey,
            config.netuid,
            config.neuron.name,
        )
    )

    config.neuron.full_path = os.path.expanduser(full_path)
    if not os.path.exists(config.neuron.full_path):
        os.makedirs(config.neuron.full_path, exist_ok=True)

    if not config.neuron.dont_save_events:
        # Add custom event logger for the events.
        try:
            # Check if the level is already configured. If it isn't, a ValueError is raised.
            logger.level("EVENTS")
        except ValueError:
            logger.level("EVENTS", no=38, icon="📝")
            logger.add(
                os.path.join(config.neuron.full_path, "events.log"),
                rotation=config.neuron.events_retention_size,
                serialize=True,
                enqueue=True,
                backtrace=False,
                diagnose=False,
                level="EVENTS",
                format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
            )


class NeuronType(enum.Enum):
    MINER = auto()
    VALIDATOR = auto()


def get_vpermit_rao_limit_default(netuid: int, network: str) -> int:
    """
    Get the appropriate vpermit_rao_limit default based on netuid and network.
    For testnet 428, use 300. For all others, use 10,000.
    """
    if network == "test" and netuid == 428:
        return 300  # Lower threshold for testnet 428
    return 10_000  # Default for mainnet and other subnets


def add_args(neuron_type: NeuronType, parser):
    """
    Adds relevant arguments to the parser for operation.
    """
    # Netuid Arg: The netuid of the subnet to connect to.
    parser.add_argument("--netuid", type=int, help="Subnet netuid", default=13)

    parser.add_argument(
        "--neuron.epoch_length",
        type=int,
        help="The default epoch length (how often we sync the metagraph, measured in 12 second blocks).",
        default=360,  # 360 blocks = 72 minutes (12 seconds per block)
    )

    parser.add_argument(
        "--neuron.events_retention_size",
        type=str,
        help="Events retention size.",
        default="2 GB",
    )

    parser.add_argument(
        "--neuron.dont_save_events",
        action="store_true",
        help="If set, we dont save events to a log file.",
        default=False,
    )

    parser.add_argument(
        "--vpermit_rao_limit",
        type=int,
        help="Set this flag to specify the minimum stake a validator needs to be recognized by a miner.",
        default=10_000, #TODO: change based on feedback
    )

    parser.add_argument(
        "--s3_auth_url",
        type=str,
        help="URL of the S3 authentication service",
        default="https://api.resilabs.ai"  # ResiLabs S3 Auth Server for Mainnet
    )
    
    # Zipcode mining configuration (enabled by default)
    parser.add_argument(
        "--disable_zipcode_mining",
        action="store_true",
        help="Disable zipcode-based competitive mining (legacy mode)",
        default=False,
    )
    
    parser.add_argument(
        "--resi_api_url",
        type=str,
        help="URL of the ResiLabs API server for zipcode assignments",
        default=None,  # Auto-configured based on netuid
    )
    
    # Proxy configuration for validators (required for spot-check validation)
    parser.add_argument(
        "--proxy_url",
        type=str,
        help="HTTP/HTTPS proxy URL for validator spot-check scraping (REQUIRED for production)",
        default=None,
    )
    
    # ScrapingBee configuration for validators
    parser.add_argument(
        "--use_scrapingbee",
        action="store_true", 
        help="Use ScrapingBee API for scraping instead of direct requests (requires SCRAPINGBEE_API_KEY env var)",
        default=False,
    )
    
    parser.add_argument(
        "--proxy_username",
        type=str,
        help="Proxy authentication username",
        default=None,
    )
    
    parser.add_argument(
        "--proxy_password",
        type=str,
        help="Proxy authentication password",
        default=None,
    )

    if neuron_type == NeuronType.VALIDATOR:
        parser.add_argument(
            "--neuron.axon_off",
            "--axon_off",
            action="store_true",
            # Note: the validator needs to serve an Axon with their IP or they may
            #   be blacklisted by the firewall of serving peers on the network.
            help="Set this flag to not attempt to serve an Axon.",
            default=False,
        )
        parser.add_argument(
            "--wandb.off",
            action="store_true",
            help="Set this flag to disable logging to wandb.",
            default=True, # Disabled by default - wandb is expensive and buggy for 24/7 logging
        )
        
        parser.add_argument(
            "--wandb.on",
            action="store_true",
            help="Enable wandb logging (overrides --wandb.off).",
            default=False,
        )

        parser.add_argument(
            "--neuron.disable_set_weights",
            action="store_true",
            help="Set this flag to disable setting the weights to network."
        )

        parser.add_argument(
            "--s3_results_path",
            action="store_true",
            help="Set this flag to select the location where you want to store your S3 validation data",
            default=os.path.join(Path(os.path.dirname(__file__)).parent, "s3_validation.parquet"),
        )

        parser.add_argument(
            "--neuron.api_on",
            action="store_true",
            help="Enable the validator API server",
            default=False,
        )

        parser.add_argument(
            "--neuron.api_port",
            type=int,
            help="Port for the validator API server",
            default=8000,
        )

        parser.add_argument(
            "--organic_whitelist",
            nargs="+",
            help="Whitelist of hotkeys allowed for organic requests",
            default=['5CzCCUzF3h5Eq3fNAr696YGRZvETYTnUHDcL16C3c9cpmbtE',
                     '5HEU7ksVSKoCHY3SVcRkJYyGRKTUtKEfCDk5m5QgJUBA4F3F'], #uids 89 and 232
        )

        parser.add_argument(
            "--organic_min_stake",
            type=float,
            help="Minimum stake required for organic requests",
            default=10000.0,
        )

        parser.add_argument(
            "--max_targets",
            type=int,
            help="Maximum number of miners to validate per cycle",
            default=256,
        )

    elif neuron_type == NeuronType.MINER:
        parser.add_argument(
            "--neuron.database_name",
            type=str,
            help="The name of the database.",
            default="SqliteMinerStorage.sqlite",
        )

        parser.add_argument(
            "--neuron.max_database_size_gb_hint",
            type=int,
            help="Hint for the size of the database to target in GBs. Expect additional some additional overhead.",
            # We intentionally choose a large default to avoid Miner's accidentally deleting data when they
            # run with the default value.
            default=250,
        )

        root_dir = Path(os.path.dirname(__file__)).parent
        default_file = os.path.join(
            os.path.join(root_dir, "scraping/config/scraping_config.json"),
        )
        encoding_default_file = os.path.join(
            os.path.join(root_dir, "upload_utils/encoding_key.json"),
        )

        private_encoding_default_file = os.path.join(
            os.path.join(root_dir, "upload_utils/private_encoding_key.json"),
        )

        state_default_file = os.path.join(
            os.path.join(root_dir, "upload_utils/state_file.json"),
        )

        parser.add_argument(
            "--neuron.scraping_config_file",
            type=str,
            help="The location of the scraping config JSON file to use",
            default=default_file,
        )

        parser.add_argument(
            "--use_uploader",
            action="store_true",
            help="Enable S3 data uploading (enabled by default, use --no_use_uploader to disable)",
            default=True
        )
        
        parser.add_argument(
            "--no_use_uploader",
            action="store_true",
            help="Disable S3 data uploading",
            default=False
        )

        parser.add_argument(
            "--gravity",
            action="store_true",
            help="Set this flag to true to retrieve updated desirabilities, stored in total.json",
            default=False
        )

        parser.add_argument(
            "--encoding_key_json_file",
            type=str,
            help="The location of the encoding keys JSON file to use",
            default=encoding_default_file
        )

        parser.add_argument(
            "--private_encoding_key_json_file",
            type=str,
            help="The location of the encoding keys JSON file to use",
            default=private_encoding_default_file
        )

        parser.add_argument(
            "--miner_upload_state_file",
            type=str,
            help="The location of the state uploading JSON file to use",
            default=state_default_file
        )

        parser.add_argument(
            "--offline",
            action="store_true",
            help="Set this flag to true to run the miner in offline mode.",
            default=False,
        )
    else:
        raise ValueError(f"Invalid neuron type: {neuron_type}")


def create_config(neuron_type: NeuronType):
    """
    Returns the configuration for the NeuronType
    """
    parser = argparse.ArgumentParser()
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)
    bt.axon.add_args(parser)
    add_args(neuron_type, parser)

    config = bt.config(parser)
    
    # Apply dynamic vpermit_rao_limit based on network and netuid
    if not hasattr(config, 'vpermit_rao_limit') or config.vpermit_rao_limit == 10_000:
        # Only override if using the default value
        network = getattr(config.subtensor, 'network', 'finney')
        netuid = getattr(config, 'netuid', 13)
        config.vpermit_rao_limit = get_vpermit_rao_limit_default(netuid, network)

    return config
