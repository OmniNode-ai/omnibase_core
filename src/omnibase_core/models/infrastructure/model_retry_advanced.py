"""
Advanced Retry Features Model.

Circuit breaker and advanced retry features.
Part of the ModelRetryPolicy restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_properties import ModelCustomProperties


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
    custom_properties: ModelCustomProperties = Field(
        default_factory=lambda: ModelCustomProperties(),
        description="Custom retry policy metadata using typed properties",
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

    def add_metadata(self, key: str, value: Any) -> None:
        """Add custom metadata."""
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        schema_value = ModelSchemaValue.from_value(value)
        self.custom_properties.set_custom_value(key, schema_value)

    def get_metadata(self, key: str) -> Any:
        """Get custom metadata value."""
        schema_value_result = self.custom_properties.get_custom_value(key)
        if schema_value_result.is_ok():
            return schema_value_result.unwrap().to_value()
        return None

    def remove_metadata(self, key: str) -> None:
        """Remove custom metadata."""
        self.custom_properties.remove_custom_field(key)

    def has_metadata(self, key: str) -> bool:
        """Check if metadata key exists."""
        return self.custom_properties.has_custom_field(key)

    def get_metadata_count(self) -> int:
        """Get number of metadata entries."""
        return self.custom_properties.get_field_count()

    def is_aggressive_circuit_breaker(self) -> bool:
        """Check if circuit breaker is aggressive (low threshold)."""
        return self.circuit_breaker_enabled and self.circuit_breaker_threshold <= 3

    def get_feature_summary(self) -> dict[str, str]:
        """Get summary of enabled features as string values for type safety."""
        return {
            "circuit_breaker_enabled": str(self.circuit_breaker_enabled),
            "circuit_breaker_threshold": str(self.circuit_breaker_threshold),
            "reset_timeout_seconds": str(self.circuit_breaker_reset_timeout_seconds),
            "has_description": str(bool(self.description)),
            "metadata_count": str(self.get_metadata_count()),
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
