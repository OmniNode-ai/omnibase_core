"""
Parsed connection information model to replace Dict[str, Any] usage in connection parsing.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelParsedConnectionInfo(BaseModel):
    """
    Parsed connection information with typed fields.
    Replaces Dict[str, Any] for parse_connection_string() returns.
    """

    # Basic connection components
    scheme: Optional[str] = Field(
        None, description="Database scheme (postgresql, mysql, etc)"
    )
    host: Optional[str] = Field(None, description="Database host")
    port: Optional[int] = Field(None, description="Database port")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password (should be masked)")
    database: Optional[str] = Field(None, description="Database name")

    # Additional parameters
    query_params: Dict[str, str] = Field(
        default_factory=dict, description="Query string parameters"
    )

    # SSL/TLS settings
    ssl_mode: Optional[str] = Field(None, description="SSL mode")
    ssl_cert: Optional[str] = Field(None, description="SSL certificate path")
    ssl_key: Optional[str] = Field(None, description="SSL key path")
    ssl_ca: Optional[str] = Field(None, description="SSL CA path")

    # Connection options
    connect_timeout: Optional[int] = Field(
        None, description="Connection timeout in seconds"
    )
    command_timeout: Optional[int] = Field(
        None, description="Command timeout in seconds"
    )
    pool_size: Optional[int] = Field(None, description="Connection pool size")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelParsedConnectionInfo":
        """Create from dictionary for easy migration."""
        return cls(**data)
