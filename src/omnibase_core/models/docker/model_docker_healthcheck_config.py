"""
Model for Docker healthcheck configuration.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.docker.model_docker_healthcheck_test import (
    ModelDockerHealthcheckTest,
)


class ModelDockerHealthcheckConfig(BaseModel):
    """Docker healthcheck configuration for compose services."""

    test: ModelDockerHealthcheckTest = Field(description="Health check command")
    interval: str | None = Field(
        default="30s",
        description="Time between health checks",
    )
    timeout: str | None = Field(default="30s", description="Health check timeout")
    retries: int | None = Field(
        default=3,
        description="Number of retries before unhealthy",
    )
    start_period: str | None = Field(
        default="0s",
        description="Start period for container initialization",
    )
    disable: bool | None = Field(default=False, description="Disable health checks")
