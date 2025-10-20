"""
Health Check Result Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Provides complete health check result aggregation.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_component_health_collection import (
    ModelComponentHealthCollection,
)
from omnibase_core.models.contracts.subcontracts.model_dependency_health import (
    ModelDependencyHealth,
)
from omnibase_core.models.contracts.subcontracts.model_node_health_status import (
    ModelNodeHealthStatus,
)


class ModelHealthCheckResult(BaseModel):
    """Complete result of a node health check operation."""

    node_health: ModelNodeHealthStatus = Field(
        ..., description="Overall node health status"
    )

    component_health: ModelComponentHealthCollection = Field(
        ..., description="Health status of individual components"
    )

    dependency_health: list[ModelDependencyHealth] = Field(
        default_factory=list, description="Health status of external dependencies"
    )

    health_score: float = Field(
        ..., description="Calculated health score (0.0-1.0)", ge=0.0, le=1.0
    )

    recommendations: list[str] = Field(
        default_factory=list, description="Health improvement recommendations"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
