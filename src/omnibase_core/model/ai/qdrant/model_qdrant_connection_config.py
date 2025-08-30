"""
Qdrant connection configuration model for database connections.

This model defines connection parameters for Qdrant vector database,
following ONEX canonical patterns with proper validation.
"""

from pydantic import BaseModel, Field, field_validator


class ModelQdrantConnectionConfig(BaseModel):
    """Model representing Qdrant database connection configuration."""

    host: str = Field(default="localhost", description="Qdrant server host")
    port: int = Field(default=6333, description="Qdrant server port")
    grpc_port: int | None = Field(
        None,
        description="Qdrant gRPC port for high-performance operations",
    )
    https: bool = Field(default=False, description="Use HTTPS connection")
    api_key: str | None = Field(None, description="API key for authentication")
    timeout: float = Field(default=30.0, description="Connection timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    pool_size: int = Field(default=10, description="Connection pool size")

    @field_validator("port", "grpc_port")
    @classmethod
    def validate_port(cls, v):
        if v is not None and not 1 <= v <= 65535:
            msg = "Port must be between 1 and 65535"
            raise ValueError(msg)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0:
            msg = "Timeout must be positive"
            raise ValueError(msg)
        return v
