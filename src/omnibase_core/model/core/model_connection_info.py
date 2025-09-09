"""
Connection info model to replace Dict[str, Any] usage for connection_info fields.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer

from omnibase_core.model.core.model_connection_metrics import ModelConnectionMetrics

# Backward compatibility alias
ConnectionMetrics = ModelConnectionMetrics


class ModelCustomConnectionProperties(BaseModel):
    """Custom properties for connection configuration."""

    # Database-specific
    database_name: str | None = Field(None, description="Database name")
    schema_name: str | None = Field(None, description="Schema name")
    charset: str | None = Field(None, description="Character set")
    collation: str | None = Field(None, description="Collation")

    # Message queue specific
    queue_name: str | None = Field(None, description="Queue/topic name")
    exchange_name: str | None = Field(None, description="Exchange name")
    routing_key: str | None = Field(None, description="Routing key")
    durable: bool | None = Field(None, description="Durable queue/exchange")

    # Cloud/service specific
    region: str | None = Field(None, description="Cloud region")
    availability_zone: str | None = Field(None, description="Availability zone")
    service_name: str | None = Field(None, description="Service name")
    instance_type: str | None = Field(None, description="Instance type")

    # Performance tuning
    max_connections: int | None = Field(None, description="Maximum connections")
    connection_limit: int | None = Field(None, description="Connection limit")
    command_timeout: int | None = Field(None, description="Command timeout")

    # Compression and optimization
    enable_compression: bool | None = Field(None, description="Enable compression")
    compression_level: int | None = Field(None, description="Compression level")
    enable_caching: bool | None = Field(None, description="Enable caching")

    # Custom string properties
    custom_strings: dict[str, str] | None = Field(
        None,
        description="Additional string properties",
    )
    # Custom numeric properties
    custom_numbers: dict[str, float] | None = Field(
        None,
        description="Additional numeric properties",
    )
    # Custom boolean flags
    custom_flags: dict[str, bool] | None = Field(
        None,
        description="Additional boolean flags",
    )


class ModelConnectionInfo(BaseModel):
    """
    Connection information with typed fields.
    Replaces Dict[str, Any] for connection_info fields.
    """

    # Connection identification
    connection_id: str = Field(..., description="Unique connection identifier")
    connection_type: str = Field(
        ...,
        description="Connection type (tcp/http/websocket/grpc)",
    )
    protocol_version: str | None = Field(None, description="Protocol version")

    # Endpoint information
    host: str = Field(..., description="Host address")
    port: int = Field(..., description="Port number")
    path: str | None = Field(None, description="Connection path/endpoint")

    # Authentication
    auth_type: str | None = Field(None, description="Authentication type")
    username: str | None = Field(None, description="Username")
    password: SecretStr | None = Field(None, description="Password (encrypted)")
    api_key: SecretStr | None = Field(None, description="API key (encrypted)")
    token: SecretStr | None = Field(None, description="Auth token (encrypted)")

    # SSL/TLS
    use_ssl: bool = Field(False, description="Whether to use SSL/TLS")
    ssl_verify: bool = Field(True, description="Whether to verify SSL certificates")
    ssl_cert_path: str | None = Field(None, description="SSL certificate path")
    ssl_key_path: str | None = Field(None, description="SSL key path")
    ssl_ca_path: str | None = Field(None, description="SSL CA bundle path")

    # Connection parameters
    timeout_seconds: int = Field(30, description="Connection timeout")
    retry_count: int = Field(3, description="Number of retry attempts")
    retry_delay_seconds: int = Field(1, description="Delay between retries")
    keepalive_interval: int | None = Field(
        None,
        description="Keepalive interval in seconds",
    )

    # Connection pooling
    pool_size: int | None = Field(None, description="Connection pool size")
    pool_timeout: int | None = Field(None, description="Pool timeout in seconds")
    max_overflow: int | None = Field(None, description="Maximum pool overflow")

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
    connection_state: str = Field(
        "disconnected",
        description="Current connection state",
    )

    # Metrics
    metrics: ModelConnectionMetrics | None = Field(
        None,
        description="Connection metrics",
    )

    # Custom properties
    custom_properties: ModelCustomConnectionProperties = Field(
        default_factory=ModelCustomConnectionProperties,
        description="Custom connection properties",
    )

    model_config = ConfigDict()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        # Use model_dump() as base and apply transformations
        data = self.model_dump(exclude_none=True)
        
        # Mask sensitive fields for security
        if "password" in data:
            data["password"] = "***MASKED***"
        if "api_key" in data:
            data["api_key"] = "***MASKED***"
        if "token" in data:
            data["token"] = "***MASKED***"

        # Flatten custom_properties for backward compatibility
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
        """Create from dictionary for easy migration."""
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
        for key in list(data.keys()):
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
    def serialize_secret(self, value):
        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        return value

    @field_serializer("established_at", "last_used_at")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
