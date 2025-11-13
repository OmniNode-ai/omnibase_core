"""Docker Deploy Config Model.

Docker deploy configuration for compose services.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.docker.model_docker_placement_constraints import (
        ModelDockerPlacementConstraints,
    )
    from omnibase_core.models.docker.model_docker_resources import ModelDockerResources
    from omnibase_core.models.docker.model_docker_restart_policy import (
        ModelDockerRestartPolicy,
    )


class ModelDockerDeployConfig(BaseModel):
    """Docker deploy configuration for compose services."""

    replicas: int | None = Field(default=1, description="Number of replicas")
    resources: "ModelDockerResources | None" = Field(
        default=None,
        description="Resource constraints",
    )
    restart_policy: "ModelDockerRestartPolicy | None" = Field(
        default=None,
        description="Restart policy",
    )
    placement: "ModelDockerPlacementConstraints | None" = Field(
        default=None,
        description="Placement constraints",
    )
