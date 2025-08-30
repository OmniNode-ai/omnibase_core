"""
Model for Docker healthcheck configuration.
"""

from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.model.service.model_docker_healthcheck_test import \
    ModelDockerHealthcheckTest


class ModelDockerHealthcheckConfig(BaseModel):
    """Docker healthcheck configuration for compose services."""

    test: ModelDockerHealthcheckTest = Field(description="Health check command")
    interval: Optional[str] = Field(
        default="30s", description="Time between health checks"
    )
    timeout: Optional[str] = Field(default="30s", description="Health check timeout")
    retries: Optional[int] = Field(
        default=3, description="Number of retries before unhealthy"
    )
    start_period: Optional[str] = Field(
        default="0s", description="Start period for container initialization"
    )
    disable: Optional[bool] = Field(default=False, description="Disable health checks")
