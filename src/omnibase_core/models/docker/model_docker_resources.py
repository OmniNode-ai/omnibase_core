"""Docker Resources Model.

Docker resource configuration.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.docker.model_docker_resource_limits import (
        ModelDockerResourceLimits,
    )
    from omnibase_core.models.docker.model_docker_resource_reservations import (
        ModelDockerResourceReservations,
    )


class ModelDockerResources(BaseModel):
    """Docker resource configuration."""

    limits: "ModelDockerResourceLimits | None" = Field(
        default=None,
        description="Resource limits",
    )
    reservations: "ModelDockerResourceReservations | None" = Field(
        default=None,
        description="Resource reservations",
    )
