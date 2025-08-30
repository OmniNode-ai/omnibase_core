"""
ONEX-compliant model for connection pool configuration.

Configuration model for managing HTTP connection pools to external services.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelConnectionPoolConfig(BaseModel):
    """
    Connection pool configuration model.

    Defines parameters for HTTP connection pooling to external services
    like Ollama, improving performance and resource utilization.
    """

    service_name: str = Field(..., description="Name of the service")
    max_connections: int = Field(
        10, description="Maximum number of connections in pool"
    )
    max_idle_connections: int = Field(5, description="Maximum idle connections to keep")
    connection_timeout: float = Field(30.0, description="Connection timeout in seconds")
    read_timeout: float = Field(300.0, description="Read timeout in seconds")
    idle_timeout: float = Field(60.0, description="Idle connection timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(0.5, description="Backoff factor for retries")
    keepalive_enabled: bool = Field(True, description="Enable HTTP keepalive")
    pool_cleanup_interval: int = Field(
        30, description="Pool cleanup interval in seconds"
    )

    # SSL/TLS settings
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    ssl_cert_path: Optional[str] = Field(None, description="Path to SSL certificate")
    ssl_key_path: Optional[str] = Field(None, description="Path to SSL private key")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "service_name": "ollama_api",
                "max_connections": 10,
                "max_idle_connections": 5,
                "connection_timeout": 30.0,
                "read_timeout": 300.0,
                "idle_timeout": 60.0,
                "max_retries": 3,
                "retry_backoff_factor": 0.5,
                "keepalive_enabled": True,
                "pool_cleanup_interval": 30,
                "verify_ssl": True,
                "ssl_cert_path": None,
                "ssl_key_path": None,
            }
        }
