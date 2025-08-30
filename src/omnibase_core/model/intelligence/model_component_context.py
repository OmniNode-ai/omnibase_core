"""
Component context model - Strongly typed component context structure.

Replaces Dict[str, Any] usage with strongly typed component context information.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelComponentContext(BaseModel):
    """Strongly typed component context."""

    component_id: str = Field(description="Component identifier")
    component_version: str = Field(description="Component version")
    capabilities: List[str] = Field(description="Component capabilities")
    current_state: str = Field(description="Current component state")
    health_status: str = Field(description="Component health status")
    resource_usage: Optional[float] = Field(
        default=None, description="Current resource usage percentage"
    )
    configuration_version: str = Field(
        default="1.0.0", description="Configuration version"
    )
    deployment_environment: Optional[str] = Field(
        default=None, description="Deployment environment"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Component dependencies"
    )
    service_endpoints: List[str] = Field(
        default_factory=list, description="Available service endpoints"
    )
