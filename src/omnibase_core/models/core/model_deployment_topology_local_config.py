# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Deployment Topology Local Config Model

Configuration for a service running in local Docker compose mode.
"""

from pydantic import BaseModel, Field

__all__ = ["ModelDeploymentTopologyLocalConfig"]


class ModelDeploymentTopologyLocalConfig(BaseModel):
    """Local Docker compose configuration for a service."""

    model_config = {"frozen": True, "extra": "forbid"}

    compose_service: str = Field(
        description="Docker compose service name.",
    )
    host_port: int = Field(
        ge=1,
        le=65535,
        description="Host-mapped port for the service.",
    )
    compose_profile: str | None = Field(
        default=None,
        description="Optional Docker compose profile required to enable the service.",
    )
    health_check_path: str | None = Field(
        default=None,
        description="HTTP path for health check. None means TCP-only check.",
    )
    health_check_timeout_ms: int = Field(
        default=5000,
        description="Timeout in milliseconds for the health check.",
    )
