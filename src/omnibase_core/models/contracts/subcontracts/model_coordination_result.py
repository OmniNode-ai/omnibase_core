"""
Coordination Result Model.

Model for node coordination operation results in the ONEX workflow coordination system.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_node_assignment import ModelNodeAssignment
from .model_synchronization_point import ModelSynchronizationPoint


class ModelCoordinationResult(BaseModel):
    """Result of node coordination operation."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    coordination_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this coordination",
    )

    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Workflow this coordination belongs to",
    )

    nodes_coordinated: list[ModelNodeAssignment] = Field(
        default_factory=list,
        description="List of nodes that were coordinated",
    )

    coordination_overhead_ms: int = Field(
        default=...,
        description="Time spent on coordination overhead in milliseconds",
        ge=0,
    )

    synchronization_points: list[ModelSynchronizationPoint] = Field(
        default_factory=list,
        description="Synchronization points reached during coordination",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
