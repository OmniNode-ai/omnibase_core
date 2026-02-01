"""
Connection Pool Model.

Connection pooling and timeout configuration for network connections.
Part of the ModelConnectionInfo restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelConnectionPool(BaseModel):
    """
    Connection pooling configuration.

    Contains pool size, timeouts, and connection management settings
    without endpoint or authentication concerns.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    # Connection parameters
    timeout_seconds: int = Field(
        default=30,
        description="Connection timeout in seconds",
        ge=1,
        le=3600,
    )
    retry_count: int = Field(
        default=3, description="Number of retry attempts", ge=0, le=10
    )
    retry_delay_seconds: int = Field(
        default=1,
        description="Delay between retries in seconds",
        ge=0,
        le=60,
    )
    keepalive_interval: int | None = Field(
        default=None,
        description="Keepalive interval in seconds",
        ge=1,
        le=300,
    )

    # Connection pooling
    pool_size: int | None = Field(
        default=None,
        description="Connection pool size",
        ge=1,
        le=1000,
    )
    pool_timeout: int | None = Field(
        default=None,
        description="Pool timeout in seconds",
        ge=1,
        le=3600,
    )
    max_overflow: int | None = Field(
        default=None,
        description="Maximum pool overflow",
        ge=0,
        le=100,
    )

    @model_validator(mode="after")
    def validate_pool_configuration(self) -> ModelConnectionPool:
        """Validate pool configuration consistency."""
        if self.pool_size and self.max_overflow:
            if self.max_overflow > self.pool_size:
                raise ModelOnexError(
                    message="max_overflow cannot exceed pool_size",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        return self

    def is_pooling_enabled(self) -> bool:
        """Check if connection pooling is enabled."""
        return self.pool_size is not None

    def get_total_pool_capacity(self) -> int | None:
        """Get total pool capacity including overflow."""
        if self.pool_size is None:
            return None
        return self.pool_size + (self.max_overflow or 0)

    def get_retry_configuration(self) -> dict[str, int]:
        """Get retry configuration."""
        return {
            "max_retries": self.retry_count,
            "retry_delay": self.retry_delay_seconds,
        }

    def get_timeout_configuration(self) -> dict[str, int | None]:
        """Get timeout configuration."""
        return {
            "connection_timeout": self.timeout_seconds,
            "pool_timeout": self.pool_timeout,
            "keepalive_interval": self.keepalive_interval,
        }

    def is_aggressive_retry(self) -> bool:
        """Check if retry configuration is aggressive (>5 retries)."""
        return self.retry_count > 5

    def has_keepalive(self) -> bool:
        """Check if keepalive is configured."""
        return self.keepalive_interval is not None

    def enable_pooling(
        self,
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_timeout: int | None = None,
    ) -> None:
        """Enable connection pooling with specified configuration."""
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout

    def disable_pooling(self) -> None:
        """Disable connection pooling."""
        self.pool_size = None
        self.pool_timeout = None
        self.max_overflow = None

    @classmethod
    def create_single_connection(cls) -> ModelConnectionPool:
        """Create configuration for single connection (no pooling)."""
        return cls(
            timeout_seconds=30,
            retry_count=3,
            retry_delay_seconds=1,
            keepalive_interval=None,
            pool_size=None,
            pool_timeout=None,
            max_overflow=None,
        )

    @classmethod
    def create_small_pool(cls) -> ModelConnectionPool:
        """Create small connection pool configuration."""
        return cls(
            timeout_seconds=30,
            retry_count=3,
            retry_delay_seconds=1,
            keepalive_interval=None,
            pool_size=5,
            max_overflow=2,
            pool_timeout=30,
        )

    @classmethod
    def create_large_pool(cls) -> ModelConnectionPool:
        """Create large connection pool configuration."""
        return cls(
            timeout_seconds=30,
            retry_count=3,
            retry_delay_seconds=1,
            keepalive_interval=None,
            pool_size=20,
            max_overflow=10,
            pool_timeout=60,
        )

    @classmethod
    def create_aggressive_retry(cls) -> ModelConnectionPool:
        """Create configuration with aggressive retry settings."""
        return cls(
            timeout_seconds=60,
            retry_count=10,
            retry_delay_seconds=2,
            keepalive_interval=None,
            pool_size=None,
            pool_timeout=None,
            max_overflow=None,
        )

    @classmethod
    def create_quick_timeout(cls) -> ModelConnectionPool:
        """Create configuration with quick timeouts."""
        return cls(
            timeout_seconds=5,
            retry_count=1,
            retry_delay_seconds=1,
            keepalive_interval=None,
            pool_size=None,
            pool_timeout=None,
            max_overflow=None,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
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


# Export for use
__all__ = ["ModelConnectionPool"]
