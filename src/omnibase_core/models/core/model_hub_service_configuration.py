#!/usr/bin/env python3
"""
Hub Service Configuration Model.

Strongly-typed model for service configuration in hubs.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_hub_http_endpoint import ModelHubHttpEndpoint
from omnibase_core.models.core.model_hub_websocket_endpoint import (
    ModelHubWebSocketEndpoint,
)


class ModelHubServiceConfiguration(BaseModel):
    """Service configuration section from contracts."""

    is_persistent_service: bool | None = Field(
        default=True,
        description="Whether hub runs as persistent service",
    )
    http_endpoints: list[ModelHubHttpEndpoint] | None = Field(
        default_factory=list,
        description="HTTP endpoints provided by hub",
    )
    websocket_endpoints: list[ModelHubWebSocketEndpoint] | None = Field(
        default_factory=list,
        description="WebSocket endpoints provided by hub",
    )
    default_port: int | None = Field(default=None, description="Default service port")
