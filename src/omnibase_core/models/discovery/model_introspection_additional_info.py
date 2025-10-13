from typing import Any, Dict

from pydantic import Field

"\nModel for introspection additional info to replace Dict[str, Any] usage.\n"
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from omnibase_core.primitives.model_semver import ModelSemVer


class ModelIntrospectionAdditionalInfo(BaseModel):
    """
    Typed model for additional introspection information.
    Replaces Dict[str, Any] usage in introspection responses.
    """

    startup_time: datetime | None = Field(
        default=None, description="Node startup timestamp"
    )
    uptime_seconds: float | None = Field(
        default=None, description="Node uptime in seconds"
    )
    restart_count: int | None = Field(
        default=None, description="Number of times node has restarted"
    )
    node_specific_version: ModelSemVer | None = Field(
        default=None, description="Node-specific version information"
    )
    configuration_source: str | None = Field(
        default=None, description="Source of node configuration"
    )
    environment: str | None = Field(
        default=None, description="Deployment environment (dev, staging, prod)"
    )
    error_message: str | None = Field(
        default=None, description="Error message if node is in error state"
    )
    last_error_time: datetime | None = Field(
        default=None, description="Timestamp of last error"
    )
    error_count: int | None = Field(
        default=None, description="Total number of errors since startup"
    )
    custom_metrics: dict[str, Any] | None = Field(
        default=None, description="Custom metrics specific to this node type"
    )
    feature_flags: dict[str, Any] | None = Field(
        default=None, description="Feature flags enabled for this node"
    )
    model_config = ConfigDict(extra="allow")
