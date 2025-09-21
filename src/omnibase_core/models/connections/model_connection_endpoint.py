"""
Connection Endpoint Model.

Endpoint and addressing information for network connections.
Part of the ModelConnectionInfo restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ...enums.enum_connection_type import EnumConnectionType
from ..metadata.model_semver import ModelSemVer


class ModelConnectionEndpoint(BaseModel):
    """
    Connection endpoint information.

    Contains network addressing and protocol details
    without authentication or pooling concerns.
    """

    # Connection type and protocol
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

    # Headers and metadata
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Connection headers",
    )
    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameters",
    )

    def get_base_url(self, use_ssl: bool = False) -> str:
        """Get base URL for this endpoint."""
        scheme_map = {
            EnumConnectionType.HTTP: "https" if use_ssl else "http",
            EnumConnectionType.WEBSOCKET: "wss" if use_ssl else "ws",
            EnumConnectionType.TCP: "tcp",
            EnumConnectionType.GRPC: "grpc",
        }

        scheme = scheme_map.get(self.connection_type, "http")
        base = f"{scheme}://{self.host}:{self.port}"

        if self.path:
            base += self.path

        return base

    def add_header(self, key: str, value: str) -> None:
        """Add a connection header."""
        self.headers[key] = value

    def remove_header(self, key: str) -> None:
        """Remove a connection header."""
        self.headers.pop(key, None)

    def add_query_param(self, key: str, value: str) -> None:
        """Add a query parameter."""
        self.query_params[key] = value

    def remove_query_param(self, key: str) -> None:
        """Remove a query parameter."""
        self.query_params.pop(key, None)

    def is_local_connection(self) -> bool:
        """Check if this is a local connection."""
        return self.host in {"localhost", "127.0.0.1", "::1"}

    def validate_path_for_type(self) -> bool:
        """Validate path is appropriate for connection type."""
        if self.connection_type in [
            EnumConnectionType.HTTP,
            EnumConnectionType.WEBSOCKET,
        ]:
            return self.path is None or self.path.startswith("/")
        return True

    @classmethod
    def create_http(
        cls,
        host: str,
        port: int = 80,
        path: str | None = None,
    ) -> ModelConnectionEndpoint:
        """Create HTTP endpoint."""
        return cls(
            connection_type=EnumConnectionType.HTTP,
            protocol_version=None,
            host=host,
            port=port,
            path=path,
        )

    @classmethod
    def create_websocket(
        cls,
        host: str,
        port: int = 80,
        path: str | None = None,
    ) -> ModelConnectionEndpoint:
        """Create WebSocket endpoint."""
        return cls(
            connection_type=EnumConnectionType.WEBSOCKET,
            protocol_version=None,
            host=host,
            port=port,
            path=path,
        )

    @classmethod
    def create_tcp(
        cls,
        host: str,
        port: int,
    ) -> ModelConnectionEndpoint:
        """Create TCP endpoint."""
        return cls(
            connection_type=EnumConnectionType.TCP,
            protocol_version=None,
            host=host,
            port=port,
            path=None,
        )


# Export for use
__all__ = ["ModelConnectionEndpoint"]
