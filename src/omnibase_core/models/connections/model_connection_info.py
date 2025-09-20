"""
Connection info model to replace Dict[str, Any] usage for connection_info fields.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_serializer,
    model_validator,
)

from ...enums.enum_auth_type import EnumAuthType
from ...enums.enum_connection_state import EnumConnectionState
from ...enums.enum_connection_type import EnumConnectionType
from ..connections.model_connection_metrics import ModelConnectionMetrics
from ..connections.model_custom_connection_properties import (
    ModelCustomConnectionProperties,
)
from ..metadata.model_semver import ModelSemVer


class ModelConnectionInfo(BaseModel):
    """
    Connection information with typed fields.
    Replaces Dict[str, Any] for connection_info fields.
    """

    # Connection identification
    connection_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique connection identifier",
    )
    connection_type: EnumConnectionType = Field(
        ...,
        description="Connection type (tcp/http/websocket/grpc)",
    )
    protocol_version: ModelSemVer | None = Field(None, description="Protocol version")

    # Endpoint information
    host: str = Field(
        ...,
        description="Host address (IP or hostname)",
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9.-]+$",
    )
    port: int = Field(..., description="Port number", ge=1, le=65535)
    path: str | None = Field(
        None, description="Connection path/endpoint", max_length=2048, pattern=r"^/.*$"
    )

    # Authentication
    auth_type: EnumAuthType | None = Field(None, description="Authentication type")
    username: str | None = Field(
        None,
        description="Username",
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._@-]+$",
    )
    password: SecretStr | None = Field(
        None, description="Password (encrypted)", min_length=1
    )
    api_key: SecretStr | None = Field(
        None, description="API key (encrypted)", min_length=1
    )
    token: SecretStr | None = Field(
        None, description="Auth token (encrypted)", min_length=1
    )

    # SSL/TLS
    use_ssl: bool = Field(default=False, description="Whether to use SSL/TLS")
    ssl_verify: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )
    ssl_cert_path: Path | None = Field(None, description="SSL certificate path")
    ssl_key_path: Path | None = Field(None, description="SSL key path")
    ssl_ca_path: Path | None = Field(None, description="SSL CA bundle path")

    # Connection parameters
    timeout_seconds: int = Field(
        30, description="Connection timeout in seconds", ge=1, le=3600
    )
    retry_count: int = Field(3, description="Number of retry attempts", ge=0, le=10)
    retry_delay_seconds: int = Field(
        1, description="Delay between retries in seconds", ge=0, le=60
    )
    keepalive_interval: int | None = Field(
        None, description="Keepalive interval in seconds", ge=1, le=300
    )

    # Connection pooling
    pool_size: int | None = Field(
        None, description="Connection pool size", ge=1, le=1000
    )
    pool_timeout: int | None = Field(
        None, description="Pool timeout in seconds", ge=1, le=3600
    )
    max_overflow: int | None = Field(
        None, description="Maximum pool overflow", ge=0, le=100
    )

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
        None,
        description="Connection establishment time",
    )
    last_used_at: datetime | None = Field(None, description="Last usage time")
    connection_state: EnumConnectionState = Field(
        default=EnumConnectionState.DISCONNECTED,
        description="Current connection state",
    )

    # Metrics
    metrics: ModelConnectionMetrics | None = Field(
        None,
        description="Connection metrics",
    )

    # Custom properties
    custom_properties: ModelCustomConnectionProperties = Field(
        default_factory=lambda: ModelCustomConnectionProperties(),
        description="Custom connection properties",
    )

    model_config = ConfigDict()

    @model_validator(mode="after")
    def validate_connection_consistency(self) -> "ModelConnectionInfo":
        """Validate connection configuration consistency."""
        # SSL path validation
        if self.use_ssl:
            if self.ssl_cert_path and not self.ssl_cert_path.exists():
                raise ValueError(
                    f"SSL certificate path does not exist: {self.ssl_cert_path}"
                )
            if self.ssl_key_path and not self.ssl_key_path.exists():
                raise ValueError(f"SSL key path does not exist: {self.ssl_key_path}")
            if self.ssl_ca_path and not self.ssl_ca_path.exists():
                raise ValueError(
                    f"SSL CA bundle path does not exist: {self.ssl_ca_path}"
                )

        # Authentication validation
        if self.auth_type == EnumAuthType.BASIC:
            if not self.username or not self.password:
                raise ValueError(
                    "Basic authentication requires both username and password"
                )
        elif self.auth_type == EnumAuthType.BEARER:
            if not self.token:
                raise ValueError("Bearer authentication requires a token")
        elif self.auth_type == EnumAuthType.API_KEY:
            if not self.api_key:
                raise ValueError("API key authentication requires an api_key")

        # Pool configuration validation
        if self.pool_size and self.max_overflow:
            if self.max_overflow > self.pool_size:
                raise ValueError("max_overflow cannot exceed pool_size")

        # Path validation for connection types
        if self.connection_type in [
            EnumConnectionType.HTTP,
            EnumConnectionType.WEBSOCKET,
        ]:
            if self.path and not self.path.startswith("/"):
                raise ValueError("HTTP/WebSocket path must start with '/'")

        return self

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
        return self.use_ssl or self.auth_type in {
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
            EnumAuthType.MTLS,
        }

    @field_serializer("password", "api_key", "token")
    def serialize_secret(self, value: Any) -> str:
        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        return str(value) if value else ""

    @field_serializer("established_at", "last_used_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return None
