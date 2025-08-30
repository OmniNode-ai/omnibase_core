"""
Model for Docker deploy configuration.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.service.model_docker_placement_constraints import (
    ModelDockerPlacementConstraints,
)
from omnibase_core.model.service.model_docker_restart_policy import (
    ModelDockerRestartPolicy,
)


class ModelDockerResourceLimits(BaseModel):
    """Resource limits for Docker services."""

    cpus: str | None = Field(
        default=None,
        description="CPU limit (e.g., '0.5', '2')",
    )
    memory: str | None = Field(
        default=None,
        description="Memory limit (e.g., '512M', '2G')",
    )


class ModelDockerResourceReservations(BaseModel):
    """Resource reservations for Docker services."""

    cpus: str | None = Field(default=None, description="CPU reservation")
    memory: str | None = Field(default=None, description="Memory reservation")


class ModelDockerResources(BaseModel):
    """Docker resource configuration."""

    limits: ModelDockerResourceLimits | None = Field(
        default=None,
        description="Resource limits",
    )
    reservations: ModelDockerResourceReservations | None = Field(
        default=None,
        description="Resource reservations",
    )


class ModelDockerDeployConfig(BaseModel):
    """Docker deploy configuration for compose services."""

    replicas: int | None = Field(default=1, description="Number of replicas")
    resources: ModelDockerResources | None = Field(
        default=None,
        description="Resource constraints",
    )
    restart_policy: ModelDockerRestartPolicy | None = Field(
        default=None,
        description="Restart policy",
    )
    placement: ModelDockerPlacementConstraints | None = Field(
        default=None,
        description="Placement constraints",
    )
