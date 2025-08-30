"""
Memory provider configuration models following ONEX standards.

Configuration for universal conversation memory providers.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelMemoryProviderType(str, Enum):
    """Types of memory providers."""

    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


class ModelVectorStoreType(str, Enum):
    """Supported vector store backends."""

    QDRANT = "qdrant"
    CHROMA = "chroma"
    WEAVIATE = "weaviate"
    PINECONE = "pinecone"
    MILVUS = "milvus"


class ModelAuthenticationType(str, Enum):
    """Authentication methods."""

    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    MTLS = "mtls"


class ModelVectorStoreConfig(BaseModel):
    """Configuration for vector store backend."""

    store_type: ModelVectorStoreType = Field(..., description="Type of vector store")
    host: str = Field(..., description="Vector store host")
    port: int = Field(..., description="Vector store port")

    collection_name: str = Field(
        "conversation_memory", description="Collection/index name"
    )

    use_tls: bool = Field(False, description="Use TLS for connection")
    verify_tls: bool = Field(True, description="Verify TLS certificates")

    connection_timeout_seconds: int = Field(30, description="Connection timeout")
    request_timeout_seconds: int = Field(60, description="Request timeout")

    max_connections: int = Field(10, description="Maximum connection pool size")
    retry_attempts: int = Field(3, description="Number of retry attempts")


class ModelEmbeddingProviderConfig(BaseModel):
    """Configuration for a single embedding provider."""

    provider_id: str = Field(..., description="Unique provider identifier")
    model_name: str = Field(..., description="Embedding model name")
    host: str = Field(..., description="Provider host")
    port: int = Field(..., description="Provider port")

    api_type: str = Field(..., description="API type (ollama, openai, etc.)")
    dimensions: int = Field(..., description="Embedding dimensions")

    description: str = Field(..., description="Human-readable description")
    priority: int = Field(
        ..., description="Priority for failover (lower is higher priority)"
    )

    max_text_length: int = Field(8192, description="Maximum text length for embedding")
    batch_size: int = Field(32, description="Batch size for embedding requests")

    timeout_seconds: int = Field(30, description="Request timeout")
    health_check_interval_seconds: int = Field(60, description="Health check interval")


class ModelMemoryAuthConfig(BaseModel):
    """Authentication configuration for memory API."""

    auth_type: ModelAuthenticationType = Field(..., description="Authentication method")

    api_key_header: Optional[str] = Field(None, description="API key header name")
    jwt_issuer: Optional[str] = Field(None, description="JWT issuer for validation")
    jwt_audience: Optional[str] = Field(None, description="JWT audience for validation")

    oauth2_provider_url: Optional[str] = Field(None, description="OAuth2 provider URL")
    oauth2_client_id: Optional[str] = Field(None, description="OAuth2 client ID")
    oauth2_scopes: Optional[List[str]] = Field(
        None, description="Required OAuth2 scopes"
    )

    mtls_cert_path: Optional[str] = Field(None, description="mTLS certificate path")
    mtls_key_path: Optional[str] = Field(None, description="mTLS key path")
    mtls_ca_path: Optional[str] = Field(None, description="mTLS CA certificate path")


class ModelMemoryAPIConfig(BaseModel):
    """Configuration for memory API server."""

    host: str = Field("0.0.0.0", description="API server host")
    port: int = Field(8089, description="API server port")

    base_path: str = Field("/api/v1", description="API base path")

    enable_cors: bool = Field(True, description="Enable CORS")
    cors_origins: List[str] = Field(["*"], description="Allowed CORS origins")

    enable_websocket: bool = Field(True, description="Enable WebSocket support")
    websocket_path: str = Field("/ws", description="WebSocket endpoint path")

    max_request_size_bytes: int = Field(10485760, description="Max request size (10MB)")
    request_timeout_seconds: int = Field(300, description="Request timeout")

    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(
        100, description="Rate limit per client"
    )

    auth_config: Optional[ModelMemoryAuthConfig] = Field(
        None, description="Authentication config"
    )


class ModelMemoryProviderConfig(BaseModel):
    """Complete configuration for a memory provider."""

    provider_name: str = Field(..., description="Provider name")
    provider_type: ModelMemoryProviderType = Field(..., description="Provider type")

    vector_store_config: ModelVectorStoreConfig = Field(
        ..., description="Vector store configuration"
    )
    embedding_providers: List[ModelEmbeddingProviderConfig] = Field(
        ..., description="Embedding providers"
    )

    api_config: Optional[ModelMemoryAPIConfig] = Field(
        None, description="API server configuration"
    )

    enable_caching: bool = Field(True, description="Enable result caching")
    cache_ttl_seconds: int = Field(3600, description="Cache TTL")

    enable_compression: bool = Field(True, description="Enable data compression")
    compression_algorithm: str = Field("zstd", description="Compression algorithm")

    chunk_size: int = Field(1024, description="Text chunk size")
    chunk_overlap: int = Field(200, description="Chunk overlap size")

    max_conversation_length: int = Field(
        100000, description="Maximum conversation length"
    )
    max_chunks_per_conversation: int = Field(
        100, description="Maximum chunks per conversation"
    )

    enable_sensitive_data_sanitization: bool = Field(
        True, description="Enable data sanitization"
    )
    sanitization_patterns: Optional[List[str]] = Field(
        None, description="Custom sanitization patterns"
    )

    retention_days: Optional[int] = Field(
        None, description="Data retention period in days"
    )
    enable_audit_logging: bool = Field(False, description="Enable audit logging")
