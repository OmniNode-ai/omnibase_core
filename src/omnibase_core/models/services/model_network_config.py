# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Network configuration model for service deployment.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.runtime.model_network_defaults import (
    packaged_network_defaults,
)


class ModelNetworkConfig(BaseModel):
    """Network configuration for service deployment."""

    model_config = ConfigDict(extra="forbid")

    port: int = Field(default=8080, description="Service port", ge=1024, le=65535)
    host: str = Field(
        default_factory=lambda: packaged_network_defaults().service_bind_host,
        description="Service host",
    )
    expose_port: bool = Field(default=True, description="Expose port to host")
    network_name: str | None = Field(default=None, description="Docker network name")
