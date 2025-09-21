"""
Advanced Retry Features Model.

Circuit breaker and advanced retry features.
Part of the ModelRetryPolicy restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelRetryAdvanced(BaseModel):
    """
    Advanced retry features and circuit breaker configuration.

    Contains circuit breaker settings and metadata
    without basic retry configuration concerns.
    """

    # Advanced configuration
    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Whether to enable circuit breaker pattern",
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        description="Consecutive failures before opening circuit",
        ge=1,
    )
    circuit_breaker_reset_timeout_seconds: float = Field(
        default=60.0,
        description="Time before attempting to close circuit",
        ge=1.0,
    )

    # Metadata
    description: str | None = Field(
        default=None,
        description="Human-readable policy description",
    )
    custom_metadata: dict[str, str | int | bool | float] = Field(
        default_factory=dict,
        description="Custom retry policy metadata",
    )

    def is_circuit_breaker_enabled(self) -> bool:
        """Check if circuit breaker is enabled."""
        return self.circuit_breaker_enabled

    def should_open_circuit(self, consecutive_failures: int) -> bool:
        """Check if circuit should be opened."""
        return (
            self.circuit_breaker_enabled
            and consecutive_failures >= self.circuit_breaker_threshold
        )

    def get_circuit_reset_delay(self) -> float:
        """Get circuit breaker reset delay."""
        return self.circuit_breaker_reset_timeout_seconds

    def add_metadata(self, key: str, value: str | int | bool | float) -> None:
        """Add custom metadata."""
        self.custom_metadata[key] = value

    def get_metadata(self, key: str) -> str | int | bool | float | None:
        """Get custom metadata value."""
        return self.custom_metadata.get(key)

    def remove_metadata(self, key: str) -> None:
        """Remove custom metadata."""
        self.custom_metadata.pop(key, None)

    def has_metadata(self, key: str) -> bool:
        """Check if metadata key exists."""
        return key in self.custom_metadata

    def get_metadata_count(self) -> int:
        """Get number of metadata entries."""
        return len(self.custom_metadata)

    def is_aggressive_circuit_breaker(self) -> bool:
        """Check if circuit breaker is aggressive (low threshold)."""
        return self.circuit_breaker_enabled and self.circuit_breaker_threshold <= 3

    def get_feature_summary(self) -> dict[str, bool | int | float]:
        """Get summary of enabled features."""
        return {
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "reset_timeout_seconds": self.circuit_breaker_reset_timeout_seconds,
            "has_description": bool(self.description),
            "metadata_count": self.get_metadata_count(),
        }

    @classmethod
    def create_with_circuit_breaker(
        cls,
        threshold: int = 5,
        reset_timeout: float = 60.0,
        description: str | None = None,
    ) -> ModelRetryAdvanced:
        """Create with circuit breaker enabled."""
        return cls(
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=threshold,
            circuit_breaker_reset_timeout_seconds=reset_timeout,
            description=description,
        )

    @classmethod
    def create_simple(
        cls,
        description: str | None = None,
    ) -> ModelRetryAdvanced:
        """Create simple advanced configuration."""
        return cls(
            circuit_breaker_enabled=False,
            description=description,
        )


# Export for use
__all__ = ["ModelRetryAdvanced"]
