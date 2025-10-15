"""
Node Health Status Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Provides overall health status tracking for ONEX nodes.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus


class ModelNodeHealthStatus(BaseModel):
    """Overall health status of a node including all components."""

    status: EnumNodeHealthStatus = Field(
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
