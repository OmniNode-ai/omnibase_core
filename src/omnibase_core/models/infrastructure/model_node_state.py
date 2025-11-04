from __future__ import annotations

import uuid

from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Node state dataclass for ONEX nodes.

Simple state holder for node metadata and configuration.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass
class ModelNodeState:
    """Simple state holder for node metadata and configuration."""

    contract_path: Path
    node_id: UUID
    contract_content: Any
    container_reference: Any | None
    node_name: str
    version: ModelSemVer
    node_tier: int
    node_classification: str
    event_bus: object | None
    initialization_metadata: dict[str, Any]


# Export for use
__all__ = ["ModelNodeState"]
