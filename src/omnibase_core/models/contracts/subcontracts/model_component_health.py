"""
Component Health Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Provides health status tracking for individual node components.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus

from .model_component_health_detail import ModelComponentHealthDetail


class ModelComponentHealth(BaseModel):
    """Health status of an individual node component."""

    component_name: str = Field(..., description="Name of the component")

    status: EnumNodeHealthStatus = Field(
        ..., description="Health status of the component"
    )

    message: str = Field(
        ..., description="Descriptive message about the component health"
    )

    last_check: datetime = Field(
        ..., description="When this component was last checked"
    )

    check_duration_ms: int | None = Field(
        default=None,
        description="Time taken for component health check in milliseconds",
        ge=0,
    )

    details: list[ModelComponentHealthDetail] = Field(
        default_factory=list,
        description="Strongly-typed component-specific health details",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
