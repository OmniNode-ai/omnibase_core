"""
Parsed connection information model to replace Dict[str, Any] usage in connection parsing.
"""

from typing import Any

from pydantic import BaseModel, Field

class ModelParsedConnectionInfo(BaseModel):
    """
    Parsed connection information with typed fields.
    Replaces Dict[str, Any] for parse_connection_string() returns.
    """

    # Basic connection components
    scheme: str | None = Field(
        None,
        description="Database scheme (postgresql, mysql, etc)",
    )
    host: str | None = Field(None, description="Database host")
    port: int | None = Field(None, description="Database port")
    username: str | None = Field(None, description="Username")
    password: str | None = Field(None, description="Password (should be masked)")
    database: str | None = Field(None, description="Database name")

    # Additional parameters
    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Query string parameters",
    )

    # SSL/TLS settings
    ssl_mode: str | None = Field(None, description="SSL mode")
    ssl_cert: str | None = Field(None, description="SSL certificate path")
    ssl_key: str | None = Field(None, description="SSL key path")
    ssl_ca: str | None = Field(None, description="SSL CA path")

    # Connection options
    connect_timeout: int | None = Field(
        None,
        description="Connection timeout in seconds",
    )
    command_timeout: int | None = Field(
        None,
        description="Command timeout in seconds",
    )
    pool_size: int | None = Field(None, description="Connection pool size")
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelParsedConnectionInfo":
        """Create from dictionary for easy migration."""
        return cls(**data)
