from typing import Any, Dict

from pydantic import Field

"""
Model for introspection additional info to replace Dict[str, Any] usage.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelIntrospectionAdditionalInfo(BaseModel):
    """
    Typed model for additional introspection information.
    Replaces Dict[str, Any] usage in introspection responses.
    """

    # Node startup and lifecycle information
    startup_time: datetime | None = Field(None, description="Node startup timestamp")
    uptime_seconds: float | None = Field(None, description="Node uptime in seconds")
    restart_count: int | None = Field(
        None,
        description="Number of times node has restarted",
    )

    # Node-specific metadata
    node_specific_version: str | None = Field(
        None,
        description="Node-specific version information",
    )
    configuration_source: str | None = Field(
        None,
        description="Source of node configuration",
    )
    environment: str | None = Field(
        None,
        description="Deployment environment (dev, staging, prod)",
    )

    # Error information
    error_message: str | None = Field(
        None,
        description="Error message if node is in error state",
    )
    last_error_time: datetime | None = Field(
        None,
        description="Timestamp of last error",
    )
    error_count: int | None = Field(
        None,
        description="Total number of errors since startup",
    )

    # Custom fields for specific nodes
    custom_metrics: dict[str, Any] | None = Field(
        None,
        description="Custom metrics specific to this node type",
    )
    feature_flags: dict[str, Any] | None = Field(
        None,
        description="Feature flags enabled for this node",
    )

    model_config = ConfigDict(extra="allow")
