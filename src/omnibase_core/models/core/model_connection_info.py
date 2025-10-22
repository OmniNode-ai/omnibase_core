#!/usr/bin/env python3
"""
Connection Info Model - ONEX Standards Compliant.

Strongly-typed model for connection information.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer

from omnibase_core.models.core.model_connection_metrics import ModelConnectionMetrics
from omnibase_core.models.core.model_custom_connection_properties import (
    ModelCustomConnectionProperties,
)
from omnibase_core.primitives.model_semver import ModelSemVer

# Compatibility alias
ConnectionMetrics = ModelConnectionMetrics


class ModelConnectionInfo(BaseModel):
    """
    Connection information with typed fields.
    Replaces Dict[str, Any] for connection_info fields.
    """

    # Connection identification
    connection_id: UUID = Field(default=..., description="Unique connection identifier")
    connection_type: str = Field(
        default=...,
        description="Connection type (tcp/http/websocket/grpc)",
    )
    protocol_version: ModelSemVer | None = Field(
        default=None, description="Protocol version"
    )

    # Endpoint information
    host: str = Field(default=..., description="Host address")
    port: int = Field(default=..., description="Port number")
    path: str | None = Field(default=None, description="Connection path/endpoint")

    # Authentication
    auth_type: str | None = Field(default=None, description="Authentication type")
    username: str | None = Field(default=None, description="Username")
    password: SecretStr | None = Field(default=None, description="Password (encrypted)")
    api_key: SecretStr | None = Field(default=None, description="API key (encrypted)")
    token: SecretStr | None = Field(default=None, description="Auth token (encrypted)")

    # SSL/TLS
    use_ssl: bool = Field(default=False, description="Whether to use SSL/TLS")
    ssl_verify: bool = Field(
        default=True, description="Whether to verify SSL certificates"
    )
    ssl_cert_path: str | None = Field(default=None, description="SSL certificate path")
    ssl_key_path: str | None = Field(default=None, description="SSL key path")
    ssl_ca_path: str | None = Field(default=None, description="SSL CA bundle path")

    # Connection parameters
    timeout_seconds: int = Field(default=30, description="Connection timeout")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    retry_delay_seconds: int = Field(default=1, description="Delay between retries")
    keepalive_interval: int | None = Field(
        default=None,
        description="Keepalive interval in seconds",
    )

    # Connection pooling
    pool_size: int | None = Field(default=None, description="Connection pool size")
    pool_timeout: int | None = Field(
        default=None, description="Pool timeout in seconds"
    )
    max_overflow: int | None = Field(default=None, description="Maximum pool overflow")

    # Headers and metadata
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Connection headers",
    )
    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameters",
    )

    # Connection state
    established_at: datetime | None = Field(
        default=None,
        description="Connection establishment time",
    )
    last_used_at: datetime | None = Field(default=None, description="Last usage time")
    connection_state: str = Field(
        default="disconnected",
        description="Current connection state",
    )

    # Metrics
    metrics: ModelConnectionMetrics | None = Field(
        default=None,
        description="Connection metrics",
    )

    # Custom properties
    custom_properties: ModelCustomConnectionProperties = Field(
        default_factory=lambda: ModelCustomConnectionProperties(),
        description="Custom connection properties",
    )

    model_config = ConfigDict()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict[str, Any]ionary for current standards."""
        # Use model_dump() as base and apply transformations
        data = self.model_dump(exclude_none=True)

        # Mask sensitive fields for security
        if "password" in data:
            data["password"] = "***MASKED***"
        if "api_key" in data:
            data["api_key"] = "***MASKED***"
        if "token" in data:
            data["token"] = "***MASKED***"

        # Flatten custom_properties for current standards
        if "custom_properties" in data and isinstance(data["custom_properties"], dict):
            custom_props = data.pop("custom_properties")
            # Merge non-None values back into main dict
            for key, value in custom_props.items():
                if value is not None and key not in [
                    "custom_strings",
                    "custom_numbers",
                    "custom_flags",
                ]:
                    data[key] = value

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelConnectionInfo":
        """Create from dict[str, Any]ionary for easy migration."""
        # Handle legacy format
        if "connection_id" not in data:
            data["connection_id"] = (
                f"{data.get('host', 'unknown')}:{data.get('port', 0)}"
            )
        if "connection_type" not in data:
            data["connection_type"] = "tcp"

        # Extract custom properties from flat dict
        known_fields = set(cls.model_fields.keys())
        custom_props = {}
        custom_fields_map = ModelCustomConnectionProperties.model_fields.keys()

        # Move unknown fields to custom_properties
        for key in list[Any](data.keys()):
            if key not in known_fields and key != "custom_properties":
                if key in custom_fields_map:
                    custom_props[key] = data.pop(key)

        if custom_props and "custom_properties" not in data:
            data["custom_properties"] = custom_props
        elif custom_props and isinstance(data.get("custom_properties"), dict):
            data["custom_properties"].update(custom_props)

        return cls(**data)

    def get_connection_string(self) -> str:
        """Generate connection string."""
        scheme = "https" if self.use_ssl else "http"
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:***@"

        base = f"{scheme}://{auth}{self.host}:{self.port}"
        if self.path:
            base += self.path

        return base

    def is_secure(self) -> bool:
        """Check if connection uses secure protocols."""
        return self.use_ssl or self.auth_type in ["oauth2", "jwt", "mtls"]

    @field_serializer("password", "api_key", "token")
    def serialize_secret(self, value: Any) -> str:
        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        result: str = value if isinstance(value, str) else str(value) if value else ""
        return result

    @field_serializer("established_at", "last_used_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
