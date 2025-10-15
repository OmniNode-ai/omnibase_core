"""
Component Health Collection Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Provides aggregated component health status tracking.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_component_health import (
    ModelComponentHealth,
)


class ModelComponentHealthCollection(BaseModel):
    """Collection of component health statuses."""

    components: list[ModelComponentHealth] = Field(
        default_factory=list, description="List of component health statuses"
    )

    healthy_count: int = Field(
        default=0, description="Number of healthy components", ge=0
    )

    degraded_count: int = Field(
        default=0, description="Number of degraded components", ge=0
    )

    unhealthy_count: int = Field(
        default=0, description="Number of unhealthy components", ge=0
    )

    total_components: int = Field(
        default=0, description="Total number of components checked", ge=0
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
