"""
Metric model.

Individual metric model with strong typing using TypeVar generics.
Follows ONEX one-model-per-file naming conventions and strong typing standards.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelMetric(BaseModel):
    """
    Strongly-typed metric model with Union-based value typing.

    Eliminates Any usage and uses Union types for supported metric values
    following ONEX strong typing standards.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    key: str = Field(default=..., description="Metric key")
    value: ModelFlexibleValue = Field(
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
    def typed_value(self) -> ModelFlexibleValue:
        """Get the strongly-typed metric value."""
        return self.value

    @classmethod
    def create_string_metric(
        cls,
        key: str,
        value: str,
        description: str | None = None,
    ) -> ModelMetric:
        """Create a string metric with strong typing."""
        return cls(
            key=key,
            value=ModelFlexibleValue.from_string(value),
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
    ) -> ModelMetric:
        """Create a numeric metric with ModelNumericValue."""
        # Convert ModelNumericValue to basic numeric type for ModelFlexibleValue
        if value.value_type == "integer":
            flexible_value = ModelFlexibleValue.from_integer(value.integer_value)
        elif value.value_type == "float":
            flexible_value = ModelFlexibleValue.from_float(value.float_value)
        else:
            # Default to float conversion for unsupported numeric types
            flexible_value = ModelFlexibleValue.from_float(
                float(value.to_python_value()),
            )

        return cls(
            key=key,
            value=flexible_value,
            unit=ModelSchemaValue.from_value(unit if unit else ""),
            description=ModelSchemaValue.from_value(description if description else ""),
        )

    @classmethod
    def create_boolean_metric(
        cls,
        key: str,
        value: bool,
        description: str | None = None,
    ) -> ModelMetric:
        """Create a boolean metric with strong typing."""
        return cls(
            key=key,
            value=ModelFlexibleValue.from_boolean(value),
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
    ) -> ModelMetric:
        """Create numeric metric from ModelNumericValue."""
        return cls.create_numeric_metric(key, value, unit, description)

    @classmethod
    def from_any_value(
        cls,
        key: str,
        value: object,
        unit: str | None = None,
        description: str | None = None,
    ) -> ModelMetric:
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# NOTE: model_rebuild() removed - Pydantic v2 handles forward references automatically
# The explicit rebuild at module level caused import failures because ModelMetadataValue
# is only available under TYPE_CHECKING guard to break circular imports
# Pydantic will rebuild the model lazily when first accessed

# Export for use
__all__ = ["ModelMetric"]
