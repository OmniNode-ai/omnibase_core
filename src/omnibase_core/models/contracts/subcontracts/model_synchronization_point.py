from pydantic import Field

"""
Synchronization Point Model - ONEX Standards Compliant.

Model for synchronization points in workflow execution for the ONEX workflow coordination system.
"""

from datetime import datetime

from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelSynchronizationPoint(BaseModel):
    """A synchronization point in workflow execution."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Model version",
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
