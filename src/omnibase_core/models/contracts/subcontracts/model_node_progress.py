"""
Node Progress Model.

Model for progress information for individual nodes in the ONEX workflow coordination system.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeProgress(BaseModel):
    """Progress information for a single node."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the node",
    )

    node_type: EnumNodeType = Field(default=..., description="Type of the node")

    progress_percent: float = Field(
        default=...,
        description="Progress percentage for this node",
        ge=0.0,
        le=100.0,
    )

    status: str = Field(default=..., description="Current status of the node")

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
