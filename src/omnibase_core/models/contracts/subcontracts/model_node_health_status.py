"""
Node Health Status Model.



Provides overall health status tracking for ONEX nodes.

Strict typing is enforced: No Any types allowed in implementation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeHealthStatus(BaseModel):
    """Overall health status of a node including all components."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    status: EnumHealthStatus = Field(
        ..., description="Overall health status of the node"
    )

    message: str = Field(..., description="Overall health status message")

    timestamp: datetime = Field(..., description="When this health check was performed")

    check_duration_ms: int = Field(
        ..., description="Total duration of health check in milliseconds", ge=0
    )

    node_type: str = Field(
        ..., description="Type of ONEX node (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)"
    )

    node_id: UUID | None = Field(
        default=None, description="Unique identifier for this node instance"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
