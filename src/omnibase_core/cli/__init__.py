"""CLI module for omnibase_core.

This module provides the command-line interface for omnibase_core,
including the onex entry point.

Usage:
    onex --help
    onex --version
    onex validate <path>
"""

from omnibase_core.cli.commands import cli

__all__ = ["cli"]
