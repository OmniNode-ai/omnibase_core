"""
Metric model.

Individual metric model with strong typing using TypeVar generics.
Follows ONEX one-model-per-file naming conventions and strong typing standards.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_numeric_value import ModelNumericValue

# Import metadata value for type-safe metric handling
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue


class ModelMetric(BaseModel):
    """
    Strongly-typed metric model with Union-based value typing.

    Eliminates Any usage and uses Union types for supported metric values
    following ONEX strong typing standards.
    """

    key: str = Field(..., description="Metric key")
    value: ModelMetadataValue = Field(..., description="Strongly-typed metric value")
    unit: str | None = Field(
        None,
        description="Unit of measurement (for numeric metrics)",
    )
    description: str | None = Field(None, description="Metric description")

    @property
    def typed_value(self) -> ModelMetadataValue:
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
            value=ModelMetadataValue.from_string(value),
            unit=None,
            description=description,
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
        # Convert ModelNumericValue to basic numeric type for ModelMetadataValue
        if value.value_type == "integer":
            metadata_value = ModelMetadataValue.from_int(value.integer_value)
        elif value.value_type == "float":
            metadata_value = ModelMetadataValue.from_float(value.float_value)
        else:
            # Default to float conversion for unsupported numeric types
            metadata_value = ModelMetadataValue.from_float(
                float(value.to_python_value())
            )

        return cls(
            key=key,
            value=metadata_value,
            unit=unit,
            description=description,
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
            value=ModelMetadataValue.from_bool(value),
            unit=None,
            description=description,
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
        value: Any,
        unit: str | None = None,
        description: str | None = None,
    ) -> ModelMetric:
        """Create metric from any supported type with automatic type detection."""
        if isinstance(value, str):
            return cls.create_string_metric(key, value, description)
        if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.create_boolean_metric(key, value, description)
        if isinstance(value, ModelNumericValue):
            return cls.create_numeric_metric(key, value, unit, description)
        if isinstance(value, (int, float)):
            numeric_value = ModelNumericValue.from_numeric(value)
            return cls.create_numeric_metric(key, numeric_value, unit, description)
        # Convert unsupported types to string representation
        return cls.create_string_metric(key, str(value), description)


# Export for use
__all__ = ["ModelMetric"]
