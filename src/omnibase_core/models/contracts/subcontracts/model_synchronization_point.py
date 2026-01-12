"""
Synchronization Point Model.

Model for synchronization points in workflow execution for the ONEX workflow coordination system.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelSynchronizationPoint(BaseModel):
    """A synchronization point in workflow execution."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    point_name: str = Field(
        default=..., description="Name of the synchronization point"
    )

    timestamp: datetime = Field(
        default=..., description="When the synchronization occurred"
    )

    nodes_synchronized: int = Field(
        default=...,
        description="Number of nodes synchronized at this point",
        ge=0,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
