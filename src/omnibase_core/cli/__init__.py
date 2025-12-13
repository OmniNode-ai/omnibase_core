"""CLI module for omnibase_core.

This module provides the command-line interface for omnibase_core,
including the onex entry point and runtime-host-dev command.

Usage:
    onex --help
    onex --version
    onex validate <path>

    omninode-runtime-host-dev CONTRACT.yaml  # Dev/test only
"""

from omnibase_core.cli.commands import cli
from omnibase_core.cli.runtime_host_cli import main as runtime_host_dev_main

__all__ = ["cli", "runtime_host_dev_main"]
