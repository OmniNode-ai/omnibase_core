"""
Dependency Health Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Provides health status tracking for external dependencies.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus


class ModelDependencyHealth(BaseModel):
    """Health status of external dependencies."""

    dependency_name: str = Field(..., description="Name of the external dependency")

    dependency_type: str = Field(
        ..., description="Type of dependency (database, service, protocol, etc.)"
    )

    status: EnumNodeHealthStatus = Field(
        ..., description="Health status of the dependency"
    )

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
