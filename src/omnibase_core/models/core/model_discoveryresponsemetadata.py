from typing import Any

from pydantic import BaseModel, Field
from uuid import UUID
from omnibase_core.models.core.model_semver import ModelSemVer


class ModelDiscoveryResponseModelMetadata(BaseModel):
    """Metadata for discovery response messages."""

    request_id: UUID = Field(default=..., description="Original request identifier")
    node_id: UUID = Field(default=..., description="Responding node identifier")
    introspection: dict[str, Any] = Field(
        default=..., description="Node introspection data"
    )
    health_status: str = Field(default=..., description="Current health status")
    capabilities: list[str] = Field(default=..., description="Node capabilities")
    node_type: str = Field(default=..., description="Node type classification")
    version: ModelSemVer = Field(default=..., description="Node version")
    event_channels: list[str] = Field(
        default=..., description="Supported event channels"
    )
    response_time_ms: float = Field(
        default=..., description="Response time in milliseconds"
    )
