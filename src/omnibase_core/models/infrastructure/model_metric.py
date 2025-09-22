"""
Metric model.

Individual metric model with universal type support using discriminated union.
Follows ONEX one-model-per-file naming conventions and strong typing standards.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...enums.enum_metric_data_type import EnumMetricDataType
from ...exceptions.onex_error import OnexError


class ModelMetric(BaseModel):
    """
    Universal metric model with strongly-typed discriminated union pattern.

    Replaces Union[str, int, float, bool] generic with discriminated union
    following ONEX strong typing standards.
    """

    key: str = Field(..., description="Metric key")
    raw_value: Any = Field(..., description="Raw metric value")
    metric_type: EnumMetricDataType = Field(
        ..., description="Data type of metric (string, numeric, boolean)"
    )
    unit: str | None = Field(
        None, description="Unit of measurement (for numeric metrics)"
    )
    description: str | None = Field(None, description="Metric description")

    @field_validator("raw_value")
    @classmethod
    def validate_raw_value(cls, v: Any, info: Any) -> Any:
        """Validate raw value matches declared metric type."""
        if "metric_type" not in info.data:
            return v

        metric_type = info.data["metric_type"]

        if metric_type == EnumMetricDataType.STRING and not isinstance(v, str):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="String metric type must contain str value",
            )
        elif metric_type == EnumMetricDataType.BOOLEAN and not isinstance(v, bool):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Boolean metric type must contain bool value",
            )
        elif metric_type == EnumMetricDataType.NUMERIC and not isinstance(
            v, (int, float)
        ):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Numeric metric type must contain int or float value",
            )

        return v

    @property
    def value(self) -> str | int | float | bool:
        """Get the typed metric value."""
        # Type is guaranteed by field_validator to be correct primitive type
        value = self.raw_value
        if isinstance(value, (str, int, float, bool)):
            return value
        # This should never happen due to validation, but satisfy mypy
        raise ValueError(f"Invalid metric value type: {type(value)}")

    @classmethod
    def create_string_metric(
        cls, key: str, value: str, description: str | None = None
    ) -> ModelMetric:
        """Create a string metric."""
        return cls(
            key=key,
            raw_value=value,
            metric_type=EnumMetricDataType.STRING,
            unit=None,
            description=description,
        )

    @classmethod
    def create_numeric_metric(
        cls,
        key: str,
        value: int | float,
        unit: str | None = None,
        description: str | None = None,
    ) -> ModelMetric:
        """Create a numeric metric."""
        return cls(
            key=key,
            raw_value=value,
            metric_type=EnumMetricDataType.NUMERIC,
            unit=unit,
            description=description,
        )

    @classmethod
    def create_boolean_metric(
        cls, key: str, value: bool, description: str | None = None
    ) -> ModelMetric:
        """Create a boolean metric."""
        return cls(
            key=key,
            raw_value=value,
            metric_type=EnumMetricDataType.BOOLEAN,
            unit=None,
            description=description,
        )

    @classmethod
    def from_any_value(
        cls,
        key: str,
        value: str | int | float | bool,
        unit: str | None = None,
        description: str | None = None,
    ) -> ModelMetric:
        """Create metric from any supported value with automatic type detection."""
        if isinstance(value, bool):  # Check bool first since bool is subclass of int
            return cls.create_boolean_metric(key, value, description)
        elif isinstance(value, str):
            return cls.create_string_metric(key, value, description)
        elif isinstance(value, (int, float)):
            return cls.create_numeric_metric(key, value, unit, description)
        else:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported metric value type: {type(value)}",
            )


# Export for use
__all__ = ["ModelMetric"]
