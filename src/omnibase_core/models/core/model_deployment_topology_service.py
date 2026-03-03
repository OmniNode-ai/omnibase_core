# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Deployment Topology Service Model

Represents a single service entry in the deployment topology, binding
a deployment mode to optional local Docker compose configuration.
"""

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_deployment_mode import EnumDeploymentMode
from omnibase_core.models.core.model_deployment_topology_local_config import (
    ModelDeploymentTopologyLocalConfig,
)

__all__ = ["ModelDeploymentTopologyService"]


class ModelDeploymentTopologyService(BaseModel):
    """A single service entry in the deployment topology."""

    model_config = {"frozen": True, "extra": "forbid"}

    mode: EnumDeploymentMode = Field(
        description="Deployment mode for this service.",
    )
    local: ModelDeploymentTopologyLocalConfig | None = Field(
        default=None,
        description="Local Docker compose configuration. Required when mode=LOCAL, must be None otherwise.",
    )

    @model_validator(mode="after")
    def validate_mode_local_consistency(self) -> "ModelDeploymentTopologyService":
        """Enforce I2: LOCAL requires local config; non-LOCAL requires local=None."""
        if self.mode == EnumDeploymentMode.LOCAL and self.local is None:
            raise ValueError(
                "mode=LOCAL requires a local config (local must not be None)."
            )
        if self.mode != EnumDeploymentMode.LOCAL and self.local is not None:
            raise ValueError(
                f"mode={self.mode} requires local=None, but local config was provided."
            )
        return self
