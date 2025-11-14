"""
Tool information model for contract-based tool discovery.

Provides structured information about discovered tools from contract.yaml files.
"""

from dataclasses import dataclass
from pathlib import Path

from omnibase_core.models.primitives.model_semver import ModelSemVer


@dataclass
class ModelToolInfo:
    """Information about a discovered tool."""

    name: str
    contract_path: Path
    tool_path: Path
    version: ModelSemVer
    last_modified: float
