"""
Configuration model for diff storage backends.

Defines ModelDiffStorageConfiguration for configuring diff storage backends
including backend type selection, retention policies, and connection parameters.

Example:
    >>> from omnibase_core.models.diff.model_diff_storage_configuration import (
    ...     ModelDiffStorageConfiguration,
    ... )
    >>> from omnibase_core.enums.enum_state_management import EnumStorageBackend
    >>>
    >>> # Default in-memory configuration
    >>> config = ModelDiffStorageConfiguration()
    >>>
    >>> # PostgreSQL configuration
    >>> config = ModelDiffStorageConfiguration(
    ...     backend_type=EnumStorageBackend.POSTGRESQL,
    ...     retention_days=90,
    ...     max_diffs=100000,
    ...     connection_params={
    ...         "host": "localhost",
    ...         "port": "5432",
    ...         "database": "diffs",
    ...     },
    ... )

See Also:
    - :class:`~omnibase_core.enums.enum_state_management.EnumStorageBackend`:
      Available storage backend types
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory storage implementation

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_state_management import EnumStorageBackend


class ModelDiffStorageConfiguration(BaseModel):
    """
    Configuration for diff storage backends.

    Provides settings for storage backend selection, retention policies,
    capacity limits, and backend-specific connection parameters.

    Attributes:
        backend_type: The storage backend to use. Defaults to MEMORY for
            development and testing. Use POSTGRESQL or REDIS for production.
        retention_days: Number of days to retain diffs before expiration.
            Defaults to 30 days. Implementations may use this for automatic
            cleanup or TTL-based eviction.
        max_diffs: Maximum number of diffs to store. Defaults to 10000.
            When exceeded, implementations should evict oldest diffs.
        enable_compression: Whether to compress stored diff data. Defaults
            to False. Enable for storage efficiency at the cost of CPU.
        connection_params: Backend-specific connection parameters as key-value
            pairs. Contents depend on the backend type.

    Example:
        >>> from omnibase_core.models.diff.model_diff_storage_configuration import (
        ...     ModelDiffStorageConfiguration,
        ... )
        >>> from omnibase_core.enums.enum_state_management import EnumStorageBackend
        >>>
        >>> # In-memory with custom limits
        >>> config = ModelDiffStorageConfiguration(
        ...     backend_type=EnumStorageBackend.MEMORY,
        ...     retention_days=7,
        ...     max_diffs=5000,
        ... )
        >>>
        >>> # Redis configuration
        >>> config = ModelDiffStorageConfiguration(
        ...     backend_type=EnumStorageBackend.REDIS,
        ...     enable_compression=True,
        ...     connection_params={
        ...         "host": "redis.example.com",
        ...         "port": "6379",
        ...         "db": "0",
        ...     },
        ... )

    .. versionadded:: 0.6.0
        Added as part of Diff Storage Infrastructure (OMN-1149)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    backend_type: EnumStorageBackend = Field(
        default=EnumStorageBackend.MEMORY,
        description="Storage backend type (memory, postgresql, redis, file_system)",
    )

    retention_days: int = Field(
        default=30,
        ge=1,
        description="Number of days to retain diffs before expiration",
    )

    max_diffs: int = Field(
        default=10000,
        ge=100,
        description="Maximum number of diffs to store",
    )

    enable_compression: bool = Field(
        default=False,
        description="Whether to compress stored diff data",
    )

    connection_params: dict[str, str] = Field(
        default_factory=dict,
        description="Backend-specific connection parameters",
    )

    def is_memory_backend(self) -> bool:
        """
        Check if using in-memory storage backend.

        Returns:
            True if backend_type is MEMORY.
        """
        return self.backend_type == EnumStorageBackend.MEMORY

    def is_persistent_backend(self) -> bool:
        """
        Check if using a persistent storage backend.

        Returns:
            True if backend_type is POSTGRESQL, REDIS, or FILE_SYSTEM.
        """
        return self.backend_type in {
            EnumStorageBackend.POSTGRESQL,
            EnumStorageBackend.REDIS,
            EnumStorageBackend.FILE_SYSTEM,
        }

    def get_connection_param(self, key: str, default: str | None = None) -> str | None:
        """
        Get a connection parameter by key.

        Args:
            key: The parameter key to look up.
            default: Default value if key is not found.

        Returns:
            The parameter value, or default if not found.
        """
        return self.connection_params.get(key, default)


__all__ = ["ModelDiffStorageConfiguration"]
