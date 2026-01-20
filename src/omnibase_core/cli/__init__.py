"""CLI module for omnibase_core.

This module provides the command-line interface for omnibase_core,
including the onex entry point and runtime-host-dev command.

Usage:
    onex --help
    onex --version
    onex validate <path>
    onex contract --help
    onex demo --help

    omninode-runtime-host-dev CONTRACT.yaml  # Dev/test only
"""

from omnibase_core.cli.cli_commands import cli
from omnibase_core.cli.cli_contract import contract
from omnibase_core.cli.cli_demo import demo
from omnibase_core.cli.cli_runtime_host import main as runtime_host_dev_main

__all__ = ["cli", "contract", "demo", "runtime_host_dev_main"]
