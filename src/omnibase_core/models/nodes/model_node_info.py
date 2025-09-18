"""
Node information model for contract-based node discovery.

Provides structured information about discovered nodes from contract.yaml files.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelNodeInfo:
    """Information about a discovered node."""

    name: str
    contract_path: Path
    node_path: Path
    version: str
    last_modified: float
