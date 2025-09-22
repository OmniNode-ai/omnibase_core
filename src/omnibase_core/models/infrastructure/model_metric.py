"""
Metric model.

Individual metric model with strong typing using TypeVar generics.
Follows ONEX one-model-per-file naming conventions and strong typing standards.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Bounded TypeVar for metric values
MetricValueType = TypeVar("MetricValueType", str, bool, bound=None)

from ..metadata.model_numeric_value import ModelNumericValue, NumericInput


class ModelMetric(BaseModel, Generic[MetricValueType]):
    """
    Strongly-typed metric model using TypeVar generics.

    Eliminates Any usage and discriminated union patterns in favor of
    proper generic typing following ONEX strong typing standards.
    """

    key: str = Field(..., description="Metric key")
    value: MetricValueType = Field(..., description="Strongly-typed metric value")
    unit: str | None = Field(
        None, description="Unit of measurement (for numeric metrics)"
    )
    description: str | None = Field(None, description="Metric description")

    @property
    def typed_value(self) -> MetricValueType:
        """Get the strongly-typed metric value."""
        return self.value

    @classmethod
    def create_string_metric(
        cls, key: str, value: str, description: str | None = None
    ) -> ModelMetric[str]:
        """Create a string metric with strong typing."""
        return cls[str](
            key=key,
            value=value,
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
    ) -> ModelMetric[ModelNumericValue]:
        """Create a numeric metric with ModelNumericValue."""
        return cls[ModelNumericValue](
            key=key,
            value=value,
            unit=unit,
            description=description,
        )

    @classmethod
    def create_boolean_metric(
        cls, key: str, value: bool, description: str | None = None
    ) -> ModelMetric[bool]:
        """Create a boolean metric with strong typing."""
        return cls[bool](
            key=key,
            value=value,
            unit=None,
            description=description,
        )

    @classmethod
    def from_numeric_value(
        cls,
        key: str,
        value: NumericInput,
        unit: str | None = None,
        description: str | None = None,
    ) -> ModelMetric[ModelNumericValue]:
        """Create numeric metric from ModelNumericValue, int, or float value."""
        if isinstance(value, ModelNumericValue):
            numeric_value = value
        else:
            numeric_value = ModelNumericValue.from_numeric(value)
        return cls.create_numeric_metric(key, numeric_value, unit, description)

    @classmethod
    def from_any_value(
        cls,
        key: str,
        value: Any,
        unit: str | None = None,
        description: str | None = None,
    ) -> ModelMetric[Any]:
        """Create metric from any supported type with automatic type detection."""
        if isinstance(value, str):
            return cls.create_string_metric(key, value, description)
        elif isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.create_boolean_metric(key, value, description)
        elif isinstance(value, (int, float)):
            return cls.from_numeric_value(key, value, unit, description)
        else:
            # For unsupported types, convert to string representation
            return cls.create_string_metric(key, str(value), description)


# Export for use
__all__ = ["ModelMetric"]
