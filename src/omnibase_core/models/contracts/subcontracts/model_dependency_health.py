"""
Dependency Health Model.



Provides health status tracking for external dependencies.

Strict typing is enforced: No Any types allowed in implementation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelDependencyHealth(BaseModel):
    """Health status of external dependencies."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    dependency_name: str = Field(..., description="Name of the external dependency")

    dependency_type: str = Field(
        ..., description="Type of dependency (database, service, protocol, etc.)"
    )

    status: EnumHealthStatus = Field(..., description="Health status of the dependency")

    endpoint: str | None = Field(
        default=None, description="Endpoint or connection string for the dependency"
    )

    last_check: datetime = Field(
        ..., description="When this dependency was last checked"
    )

    response_time_ms: int | None = Field(
        default=None,
        description="Response time for dependency check in milliseconds",
        ge=0,
    )

    error_message: str | None = Field(
        default=None, description="Error message if dependency is unhealthy"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
