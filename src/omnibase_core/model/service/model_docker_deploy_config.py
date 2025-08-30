"""
Model for Docker deploy configuration.
"""

from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.model.service.model_docker_placement_constraints import \
    ModelDockerPlacementConstraints
from omnibase_core.model.service.model_docker_restart_policy import \
    ModelDockerRestartPolicy


class ModelDockerResourceLimits(BaseModel):
    """Resource limits for Docker services."""

    cpus: Optional[str] = Field(
        default=None, description="CPU limit (e.g., '0.5', '2')"
    )
    memory: Optional[str] = Field(
        default=None, description="Memory limit (e.g., '512M', '2G')"
    )


class ModelDockerResourceReservations(BaseModel):
    """Resource reservations for Docker services."""

    cpus: Optional[str] = Field(default=None, description="CPU reservation")
    memory: Optional[str] = Field(default=None, description="Memory reservation")


class ModelDockerResources(BaseModel):
    """Docker resource configuration."""

    limits: Optional[ModelDockerResourceLimits] = Field(
        default=None, description="Resource limits"
    )
    reservations: Optional[ModelDockerResourceReservations] = Field(
        default=None, description="Resource reservations"
    )


class ModelDockerDeployConfig(BaseModel):
    """Docker deploy configuration for compose services."""

    replicas: Optional[int] = Field(default=1, description="Number of replicas")
    resources: Optional[ModelDockerResources] = Field(
        default=None, description="Resource constraints"
    )
    restart_policy: Optional[ModelDockerRestartPolicy] = Field(
        default=None, description="Restart policy"
    )
    placement: Optional[ModelDockerPlacementConstraints] = Field(
        default=None, description="Placement constraints"
    )
