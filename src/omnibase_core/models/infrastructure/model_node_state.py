"""
Node state dataclass for ONEX nodes.

Simple state holder for node metadata and configuration.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_initialization_metadata import ModelInitializationMetadata

if TYPE_CHECKING:
    from omnibase_core.models.core.model_contract_content import ModelContractContent


@dataclass
class ModelNodeState:
    """Simple state holder for node metadata and configuration.

    Thread Safety:
        This dataclass is NOT thread-safe. It contains mutable fields that can
        be modified after creation:

        - **NOT Safe**: Sharing instances across threads without synchronization
        - **NOT Safe**: Modifying fields from multiple threads concurrently

        Each thread should have its own instance, or use external synchronization
        (e.g., threading.Lock) when sharing. See docs/guides/THREADING.md for
        thread-safe patterns.
    """

    contract_path: Path
    node_id: UUID
    contract_content: ModelContractContent | ModelSchemaValue | None
    container_reference: object | None
    node_name: str
    version: ModelSemVer
    node_tier: int
    node_classification: str
    event_bus: object | None
    initialization_metadata: ModelInitializationMetadata = field(
        default_factory=ModelInitializationMetadata
    )


# Export for use
__all__ = ["ModelNodeState"]
