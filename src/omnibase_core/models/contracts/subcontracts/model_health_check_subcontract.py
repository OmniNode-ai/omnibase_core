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

MULTIPLE CLASSES JUSTIFICATION:
This file contains 6 tightly-coupled models that form a cohesive health check interface:
- ModelComponentHealth: Individual component health
- ModelNodeHealthStatus: Overall node health
- ModelComponentHealthCollection: Aggregated component health
- ModelDependencyHealth: External dependency health
- ModelHealthCheckResult: Complete health check result
- ModelHealthCheckSubcontract: Main subcontract (must be in same file per ONEX patterns)

These models are only used together and splitting them would harm cohesion and usability.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.models.core.model_health_status import ModelHealthStatus
from omnibase_core.primitives.model_semver import ModelSemVer


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

    details: dict[str, str] = Field(
        default_factory=dict, description="Additional component-specific health details"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


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
