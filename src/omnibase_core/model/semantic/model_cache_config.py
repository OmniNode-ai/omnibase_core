"""
Cache configuration model for semantic query caching.

Defines configuration options for multi-tier caching including
memory cache, PostgreSQL persistence, and performance settings.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCacheConfig(BaseModel):
    """Configuration for query cache behavior."""

    # Memory cache settings
    memory_cache_size: int = Field(
        default=1000,
        ge=1,
        le=100000,
        description="Maximum number of entries in memory cache",
    )

    memory_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        le=86400,
        description="Time-to-live for memory cache entries in seconds",
    )

    # PostgreSQL cache settings (L2 cache)
    postgres_cache_enabled: bool = Field(
        default=True, description="Enable PostgreSQL L2 cache"
    )

    postgres_ttl_seconds: int = Field(
        default=86400,
        ge=3600,
        le=604800,
        description="Time-to-live for PostgreSQL cache entries in seconds",
    )

    postgres_table_prefix: str = Field(
        default="semantic_cache_",
        min_length=1,
        max_length=50,
        description="Prefix for PostgreSQL cache table names",
    )

    postgres_cleanup_interval: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Interval between cleanup operations in seconds",
    )

    # Redis cache settings (deprecated but kept for compatibility)
    redis_cache_enabled: bool = Field(
        default=False, description="Enable Redis cache (deprecated, use PostgreSQL)"
    )

    redis_key_prefix: str = Field(
        default="onex_semantic_",
        min_length=1,
        max_length=50,
        description="Prefix for Redis cache keys",
    )

    redis_ttl_seconds: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Interval for PostgreSQL cache cleanup in seconds",
    )

    use_existing_db_connection: bool = Field(
        default=True, description="Use existing ONEX database connection"
    )

    # Cache behavior
    cache_embeddings: bool = Field(
        default=True, description="Enable embedding vector caching"
    )

    cache_query_results: bool = Field(
        default=True, description="Enable query result caching"
    )

    cache_preprocessed_docs: bool = Field(
        default=True, description="Enable preprocessed document caching"
    )

    # Performance settings
    max_result_size_bytes: int = Field(
        default=1024 * 1024,  # 1MB
        ge=1024,
        le=100 * 1024 * 1024,  # 100MB
        description="Maximum size of cached results in bytes",
    )

    compress_large_results: bool = Field(
        default=True, description="Compress large cache entries"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
