"""
Retry Configuration Model.

Core retry configuration settings grouped logically.
Part of the ModelRetryPolicy restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_retry_backoff_strategy import EnumRetryBackoffStrategy
from omnibase_core.exceptions.onex_error import OnexError


class ModelRetryConfig(BaseModel):
    """
    Core retry configuration settings.

    Groups basic retry parameters, backoff strategy, and jitter settings
    without execution tracking or advanced features.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Core retry configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=100,
    )
    base_delay_seconds: float = Field(
        default=1.0,
        description="Base delay between retries in seconds",
        ge=0.1,
        le=3600.0,
    )

    # Backoff strategy
    backoff_strategy: EnumRetryBackoffStrategy = Field(
        default=EnumRetryBackoffStrategy.EXPONENTIAL,
        description="Retry backoff strategy",
    )
    backoff_multiplier: float = Field(
        default=2.0,
        description="Multiplier for exponential/linear backoff",
        ge=1.0,
        le=10.0,
    )
    max_delay_seconds: float = Field(
        default=300.0,
        description="Maximum delay between retries",
        ge=1.0,
        le=3600.0,
    )

    # Jitter configuration
    jitter_enabled: bool = Field(
        default=True,
        description="Whether to add random jitter to delays",
    )
    jitter_max_seconds: float = Field(
        default=1.0,
        description="Maximum jitter to add/subtract",
        ge=0.0,
        le=60.0,
    )

    @model_validator(mode="after")
    def validate_max_delay(self) -> Self:
        """
        Validate max delay is greater than or equal to base delay.

        Uses @model_validator(mode='after') to ensure both fields are always
        available (no fallback pattern).

        Returns:
            The validated model instance if validation passes.

        Raises:
            OnexError: If max_delay_seconds is less than base_delay_seconds.
        """
        if self.max_delay_seconds < self.base_delay_seconds:
            msg = "Max delay must be greater than or equal to base delay"
            raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)
        return self

    def get_strategy_name(self) -> str:
        """Get human-readable strategy name."""
        return self.backoff_strategy.value.replace("_", " ").title()

    def is_aggressive(self) -> bool:
        """Check if retry configuration is aggressive."""
        return self.max_retries > 5 or self.max_delay_seconds > 300

    def is_quick_retry(self) -> bool:
        """Check if configuration favors quick retries."""
        return self.base_delay_seconds < 1.0 and self.max_delay_seconds < 10.0

    @classmethod
    def create_quick(cls) -> ModelRetryConfig:
        """Create quick retry configuration."""
        return cls(
            max_retries=3,
            base_delay_seconds=0.5,
            max_delay_seconds=5.0,
            backoff_strategy=EnumRetryBackoffStrategy.LINEAR,
        )

    @classmethod
    def create_aggressive(cls) -> ModelRetryConfig:
        """Create aggressive retry configuration."""
        return cls(
            max_retries=10,
            base_delay_seconds=2.0,
            max_delay_seconds=600.0,
            backoff_strategy=EnumRetryBackoffStrategy.EXPONENTIAL,
            backoff_multiplier=3.0,
        )

    @classmethod
    def create_conservative(cls) -> ModelRetryConfig:
        """Create conservative retry configuration."""
        return cls(
            max_retries=2,
            base_delay_seconds=5.0,
            max_delay_seconds=60.0,
            backoff_strategy=EnumRetryBackoffStrategy.FIXED,
        )

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelRetryConfig"]
