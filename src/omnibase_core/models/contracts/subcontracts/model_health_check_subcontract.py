"""
Health Check Subcontract Model.



Provides Pydantic models for standardized health monitoring and status reporting
for all ONEX node types, leveraging existing health infrastructure.

This subcontract provides comprehensive health check capabilities for COMPUTE,
EFFECT, REDUCER, and ORCHESTRATOR nodes, including component health monitoring,
dependency health checks, and health score calculation.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import (
    TIMEOUT_DEFAULT_MS,
    TIMEOUT_LONG_MS,
    TIMEOUT_MIN_MS,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHealthCheckSubcontract(BaseModel):
    """
    Health Check Subcontract for all ONEX nodes.

    Provides standardized health monitoring and status reporting capabilities
    for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    subcontract_name: str = Field(
        default="health_check_subcontract", description="Name of the subcontract"
    )

    subcontract_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the subcontract (MUST be provided in YAML contract)",
    )

    applicable_node_types: list[str] = Field(
        default_factory=lambda: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
        description="Node types this subcontract applies to",
    )

    # Configuration
    check_interval_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Health check interval in milliseconds",
        ge=5000,
        le=TIMEOUT_LONG_MS,  # Max 5 minutes (TIMEOUT_LONG_MS)
    )

    failure_threshold: int = Field(
        default=3,
        description="Number of failed checks before marking as unhealthy",
        ge=1,
        le=10,
    )

    recovery_threshold: int = Field(
        default=2,
        description="Number of successful checks before marking as recovered",
        ge=1,
        le=10,
    )

    timeout_ms: int = Field(
        default=5000,
        description="Timeout for individual health checks in milliseconds",
        ge=TIMEOUT_MIN_MS,
        le=TIMEOUT_DEFAULT_MS,
    )

    include_dependency_checks: bool = Field(
        default=True, description="Whether to include external dependency health checks"
    )

    include_component_checks: bool = Field(
        default=True,
        description="Whether to include individual component health checks",
    )

    enable_health_score_calculation: bool = Field(
        default=True, description="Whether to calculate overall health scores"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
