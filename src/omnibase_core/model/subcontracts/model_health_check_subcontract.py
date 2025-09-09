"""
Health Check Subcontract Models for ONEX Nodes.

Provides Pydantic models for standardized health monitoring and status reporting
for all ONEX node types, leveraging existing health infrastructure.

Generated from health_check subcontract following ONEX patterns.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

# Import existing health models from omnibase_3
from omnibase_spi.model.health.model_health_status import ModelHealthStatus

# Import existing enums instead of duplicating
from omnibase_spi.protocols.types.core_types import HealthStatus, NodeType
from pydantic import BaseModel, Field

# Use HealthStatus from omnibase_core.enums.node instead


class ModelComponentHealth(BaseModel):
    """Health status of an individual node component."""

    component_name: str = Field(..., description="Name of the component")

    status: HealthStatus = Field(..., description="Health status of the component")

    message: str = Field(
        ..., description="Descriptive message about the component health"
    )

    last_check: datetime = Field(
        ..., description="When this component was last checked"
    )

    check_duration_ms: Optional[int] = Field(
        default=None,
        description="Time taken for component health check in milliseconds",
        ge=0,
    )

    details: dict = Field(
        default_factory=dict, description="Additional component-specific health details"
    )


class ModelNodeHealthStatus(BaseModel):
    """Overall health status of a node including all components."""

    status: HealthStatus = Field(..., description="Overall health status of the node")

    message: str = Field(..., description="Overall health status message")

    timestamp: datetime = Field(..., description="When this health check was performed")

    check_duration_ms: int = Field(
        ..., description="Total duration of health check in milliseconds", ge=0
    )

    node_type: str = Field(
        ..., description="Type of ONEX node (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)"
    )

    node_id: Optional[str] = Field(
        default=None, description="Unique identifier for this node instance"
    )


class ModelComponentHealthCollection(BaseModel):
    """Collection of component health statuses."""

    components: List[ModelComponentHealth] = Field(
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


class ModelDependencyHealth(BaseModel):
    """Health status of external dependencies."""

    dependency_name: str = Field(..., description="Name of the external dependency")

    dependency_type: str = Field(
        ..., description="Type of dependency (database, service, protocol, etc.)"
    )

    status: HealthStatus = Field(..., description="Health status of the dependency")

    endpoint: Optional[str] = Field(
        default=None, description="Endpoint or connection string for the dependency"
    )

    last_check: datetime = Field(
        ..., description="When this dependency was last checked"
    )

    response_time_ms: Optional[int] = Field(
        default=None,
        description="Response time for dependency check in milliseconds",
        ge=0,
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message if dependency is unhealthy"
    )


class ModelHealthCheckResult(BaseModel):
    """Complete result of a node health check operation."""

    node_health: ModelNodeHealthStatus = Field(
        ..., description="Overall node health status"
    )

    component_health: ModelComponentHealthCollection = Field(
        ..., description="Health status of individual components"
    )

    dependency_health: List[ModelDependencyHealth] = Field(
        default_factory=list, description="Health status of external dependencies"
    )

    health_score: float = Field(
        ..., description="Calculated health score (0.0-1.0)", ge=0.0, le=1.0
    )

    recommendations: List[str] = Field(
        default_factory=list, description="Health improvement recommendations"
    )


# Main subcontract definition model
class ModelHealthCheckSubcontract(BaseModel):
    """
    Health Check Subcontract for all ONEX nodes.

    Provides standardized health monitoring and status reporting capabilities
    for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.
    """

    subcontract_name: str = Field(
        default="health_check_subcontract", description="Name of the subcontract"
    )

    subcontract_version: str = Field(
        default="1.0.0", description="Version of the subcontract"
    )

    applicable_node_types: List[str] = Field(
        default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
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

    class Config:
        json_schema_extra = {
            "example": {
                "subcontract_name": "health_check_subcontract",
                "subcontract_version": "1.0.0",
                "applicable_node_types": [
                    "COMPUTE",
                    "EFFECT",
                    "REDUCER",
                    "ORCHESTRATOR",
                ],
                "check_interval_ms": 30000,
                "failure_threshold": 3,
                "recovery_threshold": 2,
                "timeout_ms": 5000,
                "include_dependency_checks": True,
                "include_component_checks": True,
                "enable_health_score_calculation": True,
            }
        }
