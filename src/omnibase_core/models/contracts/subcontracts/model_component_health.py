"""
Component Health Model.



Provides health status tracking for individual node components.

Strict typing is enforced: No Any types allowed in implementation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_component_health_detail import ModelComponentHealthDetail


class ModelComponentHealth(BaseModel):
    """Health status of an individual node component."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    component_name: str = Field(..., description="Name of the component")

    status: EnumHealthStatus = Field(..., description="Health status of the component")

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
