from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# TYPE_CHECKING guard to break circular import with metadata layer
# Infrastructure layer should not depend on metadata at runtime
if TYPE_CHECKING:
    from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue

"""
Metric model.

Individual metric model with strong typing using TypeVar generics.
Follows ONEX one-model-per-file naming conventions and strong typing standards.
"""


class ModelMetric(BaseModel):
    """
    Strongly-typed metric model with Union-based value typing.

    Eliminates Any usage and uses Union types for supported metric values
    following ONEX strong typing standards.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    key: str = Field(default=..., description="Metric key")
    value: "ModelMetadataValue" = Field(
        default=..., description="Strongly-typed metric value"
    )
    unit: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Unit of measurement (for numeric metrics)",
    )
    description: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Metric description",
    )

    @property
    def typed_value(self) -> "ModelMetadataValue":
        """Get the strongly-typed metric value."""
        return self.value

    @classmethod
    def create_string_metric(
        cls,
        key: str,
        value: str,
        description: str | None = None,
    ) -> "ModelMetric":
        """Create a string metric with strong typing."""
        # Import at runtime to avoid circular dependency
        from omnibase_core.models.metadata.model_metadata_value import (
            ModelMetadataValue,
        )

        return cls(
            key=key,
            value=ModelMetadataValue.from_string(value),
            unit=ModelSchemaValue.from_value(""),
            description=ModelSchemaValue.from_value(description if description else ""),
        )

    @classmethod
    def create_numeric_metric(
        cls,
        key: str,
        value: ModelNumericValue,
        unit: str | None = None,
        description: str | None = None,
    ) -> "ModelMetric":
        """Create a numeric metric with ModelNumericValue."""
        # Import at runtime to avoid circular dependency
        from omnibase_core.models.metadata.model_metadata_value import (
            ModelMetadataValue,
        )

        # Convert ModelNumericValue to basic numeric type for ModelMetadataValue
        if value.value_type == "integer":
            metadata_value = ModelMetadataValue.from_int(value.integer_value)
        elif value.value_type == "float":
            metadata_value = ModelMetadataValue.from_float(value.float_value)
        else:
            # Default to float conversion for unsupported numeric types
            metadata_value = ModelMetadataValue.from_float(
                float(value.to_python_value()),
            )

        return cls(
            key=key,
            value=metadata_value,
            unit=ModelSchemaValue.from_value(unit if unit else ""),
            description=ModelSchemaValue.from_value(description if description else ""),
        )

    @classmethod
    def create_boolean_metric(
        cls,
        key: str,
        value: bool,
        description: str | None = None,
    ) -> "ModelMetric":
        """Create a boolean metric with strong typing."""
        # Import at runtime to avoid circular dependency
        from omnibase_core.models.metadata.model_metadata_value import (
            ModelMetadataValue,
        )

        return cls(
            key=key,
            value=ModelMetadataValue.from_bool(value),
            unit=ModelSchemaValue.from_value(""),
            description=ModelSchemaValue.from_value(description if description else ""),
        )

    @classmethod
    def from_numeric_value(
        cls,
        key: str,
        value: ModelNumericValue,
        unit: str | None = None,
        description: str | None = None,
    ) -> "ModelMetric":
        """Create numeric metric from ModelNumericValue."""
        return cls.create_numeric_metric(key, value, unit, description)

    @classmethod
    def from_any_value(
        cls,
        key: str,
        value: object,
        unit: str | None = None,
        description: str | None = None,
    ) -> "ModelMetric":
        """Create metric from bounded type values with automatic type detection."""
        if isinstance(value, str):
            return cls.create_string_metric(key, value, description)
        if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.create_boolean_metric(key, value, description)
        if isinstance(value, ModelNumericValue):
            return cls.create_numeric_metric(key, value, unit, description)
        if isinstance(value, (int, float)):
            numeric_value = ModelNumericValue.from_numeric(value)
            return cls.create_numeric_metric(key, numeric_value, unit, description)
        # This should not be reached with the bounded type signature
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported metric value type: {type(value)}",
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelMetric"]
