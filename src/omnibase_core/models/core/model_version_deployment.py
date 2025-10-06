"""
Version Deployment Model - Tier 3 Metadata.

Pydantic model for deployment-specific configuration.
"""

from pydantic import BaseModel, Field


class ModelVersionDeployment(BaseModel):
    """Deployment-specific configuration."""

    docker_image: str | None = Field(
        default=None,
        description="Docker image reference if containerized",
    )
    resource_requirements: dict[str, str] = Field(
        default_factory=dict,
        description="Resource requirements for deployment",
    )
    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Required environment variables",
    )
    port_mappings: dict[str, int] = Field(
        default_factory=dict,
        description="Port mapping requirements",
    )
    health_check_endpoint: str = Field(
        default="/health",
        description="Health check endpoint path",
    )
    startup_timeout: int = Field(default=30, description="Startup timeout in seconds")
