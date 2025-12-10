"""
Health Check Subcontract Result Model.



Provides result model for Health Check Subcontract operations with comprehensive
health status information.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_component_health import (
    ModelComponentHealth,
)
from omnibase_core.models.contracts.subcontracts.model_dependency_health import (
    ModelDependencyHealth,
)
from omnibase_core.models.contracts.subcontracts.model_node_health_status import (
    ModelNodeHealthStatus,
)
from omnibase_core.models.core.model_health_check_result import ModelHealthCheckResult
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHealthCheckSubcontractResult(BaseModel):
    """
    Result model for Health Check Subcontract operations.

    Contains comprehensive health status information including node-level health,
    component health details, dependency health status, calculated health scores,
    and actionable recommendations for health improvements.

    This model extends beyond the core ModelHealthCheckResult to provide
    specialized health monitoring data for ONEX nodes with subcontract support.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (auto-generated if not provided)",
    )

    node_health: ModelNodeHealthStatus = Field(
        ...,
        description="Overall node health status with detailed metrics",
    )

    component_health: list[ModelComponentHealth] = Field(
        default_factory=list,
        description="Health status of individual node components",
    )

    dependency_health: list[ModelDependencyHealth] = Field(
        default_factory=list,
        description="Health status of external dependencies",
    )

    health_score: float = Field(
        ...,
        description="Calculated overall health score (0.0 = critical, 1.0 = perfect)",
        ge=0.0,
        le=1.0,
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations for improving health status",
    )

    core_result: ModelHealthCheckResult | None = Field(
        default=None,
        description="Optional reference to core health check result",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
