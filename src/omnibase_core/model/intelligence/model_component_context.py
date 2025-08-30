"""
Component context model - Strongly typed component context structure.

Replaces Dict[str, Any] usage with strongly typed component context information.
"""

from pydantic import BaseModel, Field


class ModelComponentContext(BaseModel):
    """Strongly typed component context."""

    component_id: str = Field(description="Component identifier")
    component_version: str = Field(description="Component version")
    capabilities: list[str] = Field(description="Component capabilities")
    current_state: str = Field(description="Current component state")
    health_status: str = Field(description="Component health status")
    resource_usage: float | None = Field(
        default=None,
        description="Current resource usage percentage",
    )
    configuration_version: str = Field(
        default="1.0.0",
        description="Configuration version",
    )
    deployment_environment: str | None = Field(
        default=None,
        description="Deployment environment",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Component dependencies",
    )
    service_endpoints: list[str] = Field(
        default_factory=list,
        description="Available service endpoints",
    )
