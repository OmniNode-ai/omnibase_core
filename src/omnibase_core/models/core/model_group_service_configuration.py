from pydantic import BaseModel, Field

from omnibase_core.models.core.model_group_service_endpoint import (
    ModelGroupServiceEndpoint,
)


class ModelGroupServiceConfiguration(BaseModel):
    """Service configuration for tool groups that host HTTP services."""

    is_persistent_service: bool = Field(
        description="Whether this group hosts a persistent HTTP service",
    )
    default_port: int | None = Field(
        default=None,
        description="Default HTTP port for the group service",
    )
    http_endpoints: list["ModelGroupServiceEndpoint"] = Field(
        default_factory=list,
        description="HTTP endpoints provided by group",
    )
    websocket_endpoints: list["ModelGroupServiceEndpoint"] = Field(
        default_factory=list,
        description="WebSocket endpoints provided by group",
    )
    health_check_path: str = Field(
        default="/health",
        description="Health check endpoint path",
    )
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")


try:
    ModelGroupServiceConfiguration.model_rebuild()
except Exception:  # catch-all-ok: circular import protection during model rebuild
    pass
