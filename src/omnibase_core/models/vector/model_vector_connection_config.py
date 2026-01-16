"""Vector store connection configuration model.

This module provides the ModelVectorConnectionConfig class for defining
connection parameters for vector store backends.

Thread Safety:
    ModelVectorConnectionConfig instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.

Security:
    The api_key field uses SecretStr to prevent accidental exposure in logs
    or error messages. Use api_key.get_secret_value() when the actual
    credential is needed.
"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class ModelVectorConnectionConfig(BaseModel):
    """Connection configuration for a vector store backend.

    This model defines the connection parameters needed to connect
    to a vector database like Qdrant, Pinecone, or Milvus.

    Attributes:
        url: The base URL of the vector store service.
        api_key: Optional API key for authentication (sensitive).
        timeout: Connection and request timeout in seconds.
        pool_size: Maximum number of concurrent connections.

    Example:
        Basic connection::

            from omnibase_core.models.vector import ModelVectorConnectionConfig

            config = ModelVectorConnectionConfig(
                url="http://localhost:6333",
            )

        With authentication::

            config = ModelVectorConnectionConfig(
                url="https://my-cluster.vectordb.io",
                api_key="sk-xxxxx",
                timeout=60.0,
                pool_size=20,
            )
    """

    url: str = Field(
        ...,
        min_length=1,
        description="Base URL of the vector store service",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for authentication (secured with SecretStr)",
    )
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=600.0,
        description="Connection and request timeout in seconds",
    )
    pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of concurrent connections",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate that the URL has a valid scheme."""
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


__all__ = ["ModelVectorConnectionConfig"]
