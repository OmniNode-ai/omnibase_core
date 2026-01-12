"""
Advanced Retry Features Model.

Circuit breaker and advanced retry features.
Part of the ModelRetryPolicy restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties


class ModelRetryAdvanced(BaseModel):
    """
    Advanced retry features and circuit breaker configuration.

    Contains circuit breaker settings and metadata
    without basic retry configuration concerns.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
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
    description: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
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

    def add_metadata(self, key: str, value: object) -> None:
        """Add custom metadata with bounded type values."""

        schema_value = ModelSchemaValue.from_value(value)
        # Convert ModelSchemaValue back to primitive and ensure it's a valid PrimitiveValueType
        raw_value = schema_value.to_value()
        if isinstance(raw_value, str):
            self.custom_properties.set_custom_value(key, raw_value)
        else:
            # For non-primitive types, convert to string representation
            self.custom_properties.set_custom_string(key, str(raw_value))

    def get_metadata(self, key: str) -> object:
        """Get custom metadata value with bounded return type."""
        # Use get_custom_value_wrapped to get ModelResult with is_ok() and unwrap() methods
        schema_value_result = self.custom_properties.get_custom_value_wrapped(key)
        if schema_value_result.is_ok():
            value = schema_value_result.unwrap().to_value()
            # Ensure bounded return type
            if isinstance(value, (str, int, float, bool)):
                return value
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
            "has_description": str(
                bool(
                    (
                        self.description.to_value()
                        if isinstance(self.description.to_value(), str)
                        and self.description.to_value()
                        else False
                    ),
                ),
            ),
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
            description=ModelSchemaValue.from_value(description if description else ""),
        )

    @classmethod
    def create_simple(
        cls,
        description: str | None = None,
    ) -> ModelRetryAdvanced:
        """Create simple advanced configuration."""
        return cls(
            circuit_breaker_enabled=False,
            description=ModelSchemaValue.from_value(description if description else ""),
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            TypeError: If value type is invalid
            Exception: If execution logic fails
        """
        # Update any relevant execution fields with runtime validation
        for key, value in kwargs.items():
            if hasattr(self, key) and isinstance(value, (str, int, float, bool)):
                setattr(self, key, value)
        return True

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            TypeError: If value type is invalid
            Exception: If configuration logic fails
        """
        # Configure with runtime validation for type safety
        for key, value in kwargs.items():
            if hasattr(self, key) and isinstance(value, (str, int, float, bool)):
                setattr(self, key, value)
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelRetryAdvanced"]
