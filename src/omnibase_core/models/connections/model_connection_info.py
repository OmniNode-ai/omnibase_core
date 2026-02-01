"""
Connection info model to replace Dict[str, Any] usage for connection_info fields.

Restructured to use composition of focused sub-models instead of
excessive string fields in a single large model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.enums.enum_connection_state import EnumConnectionState
from omnibase_core.models.connections.model_connection_auth import ModelConnectionAuth
from omnibase_core.models.connections.model_connection_endpoint import (
    ModelConnectionEndpoint,
)
from omnibase_core.models.connections.model_connection_metrics import (
    ModelConnectionMetrics,
)
from omnibase_core.models.connections.model_connection_pool import ModelConnectionPool
from omnibase_core.models.connections.model_connection_security import (
    ModelConnectionSecurity,
)
from omnibase_core.models.connections.model_custom_connection_properties import (
    ModelCustomConnectionProperties,
)
from omnibase_core.types import SerializedDict


class ModelConnectionInfo(BaseModel):
    """
    Connection information with typed fields.

    Restructured to use composition of focused sub-models:
    - endpoint: Network addressing and protocol details
    - auth: Authentication configuration
    - security: SSL/TLS settings
    - pool: Connection pooling and timeouts
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    # Connection identification
    connection_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique connection identifier",
    )

    # Composed sub-models for focused concerns
    endpoint: ModelConnectionEndpoint = Field(
        default=...,
        description="Connection endpoint configuration",
    )
    auth: ModelConnectionAuth = Field(
        default_factory=lambda: ModelConnectionAuth.create_no_auth(),
        description="Authentication configuration",
    )
    security: ModelConnectionSecurity = Field(
        default_factory=lambda: ModelConnectionSecurity.create_insecure(),
        description="Security and SSL configuration",
    )
    pool: ModelConnectionPool = Field(
        default_factory=lambda: ModelConnectionPool.create_single_connection(),
        description="Connection pooling configuration",
    )

    # Connection state
    established_at: datetime | None = Field(
        default=None,
        description="Connection establishment time",
    )
    last_used_at: datetime | None = Field(default=None, description="Last usage time")
    connection_state: EnumConnectionState = Field(
        default=EnumConnectionState.DISCONNECTED,
        description="Current connection state",
    )

    # Metrics and custom properties
    metrics: ModelConnectionMetrics | None = Field(
        default=None,
        description="Connection metrics",
    )
    custom_properties: ModelCustomConnectionProperties = Field(
        default_factory=lambda: ModelCustomConnectionProperties(),
        description="Custom connection properties",
    )

    # Delegation properties
    @property
    def host(self) -> str:
        """Get host from endpoint."""
        return self.endpoint.host

    @property
    def port(self) -> int:
        """Get port from endpoint."""
        return self.endpoint.port

    @property
    def connection_type(self) -> str:
        """Get connection type from endpoint."""
        return self.endpoint.connection_type

    @property
    def use_ssl(self) -> bool:
        """Get SSL flag from security."""
        return self.security.use_ssl

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    def get_connection_string(self) -> str:
        """Generate connection string."""
        auth = ""
        if self.auth.username and self.auth.password:
            auth = f"{self.auth.username}:***@"

        return self.endpoint.get_base_url(self.security.use_ssl) + (
            auth if auth else ""
        )

    def is_secure(self) -> bool:
        """Check if connection uses secure protocols."""
        return self.security.is_secure_connection() or self.auth.is_secure_auth()

    def validate_configuration(self) -> bool:
        """Validate the complete connection configuration.

        Note: Pool and security sub-models are validated at construction time
        and on every field assignment (via validate_assignment=True), so
        explicit re-validation is not needed here.
        """
        # Validate endpoint path for connection type
        if not self.endpoint.validate_path_for_type():
            return False

        # Validate authentication requirements
        if not self.auth.validate_auth_requirements():
            return False

        # Pool and security models are already validated:
        # - At construction via model_validator(mode="after")
        # - On field assignment via validate_assignment=True in model_config

        return True

    def mark_connected(self) -> None:
        """Mark connection as established."""
        self.connection_state = EnumConnectionState.CONNECTED
        self.established_at = datetime.now()

    def mark_disconnected(self) -> None:
        """Mark connection as disconnected."""
        self.connection_state = EnumConnectionState.DISCONNECTED

    def mark_used(self) -> None:
        """Mark connection as recently used."""
        self.last_used_at = datetime.now()

    @field_serializer("established_at", "last_used_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None

    @classmethod
    def create_http(
        cls,
        host: str,
        port: int = 80,
        path: str | None = None,
        use_ssl: bool = False,
    ) -> ModelConnectionInfo:
        """Create HTTP connection."""
        endpoint = ModelConnectionEndpoint.create_http(host, port, path)
        security = (
            ModelConnectionSecurity.create_secure()
            if use_ssl
            else ModelConnectionSecurity.create_insecure()
        )
        return cls(
            endpoint=endpoint,
            security=security,
            established_at=None,
            last_used_at=None,
            metrics=None,
        )

    @classmethod
    def create_websocket(
        cls,
        host: str,
        port: int = 80,
        path: str | None = None,
        use_ssl: bool = False,
    ) -> ModelConnectionInfo:
        """Create WebSocket connection."""
        endpoint = ModelConnectionEndpoint.create_websocket(host, port, path)
        security = (
            ModelConnectionSecurity.create_secure()
            if use_ssl
            else ModelConnectionSecurity.create_insecure()
        )
        return cls(
            endpoint=endpoint,
            security=security,
            established_at=None,
            last_used_at=None,
            metrics=None,
        )

    @classmethod
    def create_with_auth(
        cls,
        endpoint: ModelConnectionEndpoint,
        auth: ModelConnectionAuth,
        security: ModelConnectionSecurity | None = None,
        pool: ModelConnectionPool | None = None,
    ) -> ModelConnectionInfo:
        """Create connection with custom authentication."""
        return cls(
            endpoint=endpoint,
            auth=auth,
            security=security or ModelConnectionSecurity.create_insecure(),
            pool=pool or ModelConnectionPool.create_single_connection(),
            established_at=None,
            last_used_at=None,
            metrics=None,
        )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)
