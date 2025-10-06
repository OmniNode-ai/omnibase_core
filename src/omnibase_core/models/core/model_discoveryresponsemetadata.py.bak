from typing import Any

from pydantic import BaseModel, Field


class ModelDiscoveryResponseModelMetadata(BaseModel):
    """Metadata for discovery response messages."""

    request_id: str = Field(..., description="Original request identifier")
    node_id: str = Field(..., description="Responding node identifier")
    introspection: dict[str, Any] = Field(..., description="Node introspection data")
    health_status: str = Field(..., description="Current health status")
    capabilities: list[str] = Field(..., description="Node capabilities")
    node_type: str = Field(..., description="Node type classification")
    version: str = Field(..., description="Node version")
    event_channels: list[str] = Field(..., description="Supported event channels")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
