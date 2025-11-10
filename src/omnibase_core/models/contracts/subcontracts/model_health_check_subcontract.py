"""
Health Check Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed

Provides Pydantic models for standardized health monitoring and status reporting
for all ONEX node types, leveraging existing health infrastructure.

This subcontract provides comprehensive health check capabilities for COMPUTE,
EFFECT, REDUCER, and ORCHESTRATOR nodes, including component health monitoring,
dependency health checks, and health score calculation.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_component_health import (
    ModelComponentHealth,
)
from omnibase_core.models.contracts.subcontracts.model_component_health_collection import (
    ModelComponentHealthCollection,
)
from omnibase_core.models.contracts.subcontracts.model_dependency_health import (
    ModelDependencyHealth,
)
from omnibase_core.models.contracts.subcontracts.model_health_check_subcontract_result import (
    ModelHealthCheckSubcontractResult,
)
from omnibase_core.models.contracts.subcontracts.model_node_health_status import (
    ModelNodeHealthStatus,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHealthCheckSubcontract(BaseModel):
    """
    Health Check Subcontract for all ONEX nodes.

    Provides standardized health monitoring and status reporting capabilities
    for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    subcontract_name: str = Field(
        default="health_check_subcontract", description="Name of the subcontract"
    )

    subcontract_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the subcontract",
    )

    applicable_node_types: list[str] = Field(
        default_factory=lambda: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
        description="Node types this subcontract applies to",
    )

    # Configuration
    check_interval_ms: int = Field(
        default=30000,
        description="Health check interval in milliseconds",
        ge=5000,
        le=300000,
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
        ge=1000,
        le=30000,
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
