"""
Tool information model for contract-based tool discovery.

Provides structured information about discovered tools from contract.yaml files.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelToolInfo:
    """Information about a discovered tool."""

    name: str
    contract_path: Path
    tool_path: Path
    version: str
    last_modified: float
