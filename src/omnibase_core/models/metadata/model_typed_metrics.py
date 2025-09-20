"""
Generic typed metrics model.

Unified generic model replacing type-specific metrics variants.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", str, int, float, bool)


class ModelTypedMetrics(BaseModel, Generic[T]):
    """Generic metrics model replacing type-specific variants."""

    name: str = Field(..., description="Metric name")
    value: T = Field(..., description="Typed metric value")
    unit: str | None = Field(None, description="Unit of measurement")
    description: str | None = Field(None, description="Metric description")

    @classmethod
    def string_metric(
        cls,
        name: str,
        value: str,
        unit: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> "ModelTypedMetrics[str]":
        """Create a string metric."""
        return ModelTypedMetrics[str](
            name=name, value=value, unit=unit, description=description, **kwargs
        )

    @classmethod
    def int_metric(
        cls,
        name: str,
        value: int,
        unit: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> "ModelTypedMetrics[int]":
        """Create an integer metric."""
        return ModelTypedMetrics[int](
            name=name, value=value, unit=unit, description=description, **kwargs
        )

    @classmethod
    def float_metric(
        cls,
        name: str,
        value: float,
        unit: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> "ModelTypedMetrics[float]":
        """Create a float metric."""
        return ModelTypedMetrics[float](
            name=name, value=value, unit=unit, description=description, **kwargs
        )

    @classmethod
    def boolean_metric(
        cls,
        name: str,
        value: bool,
        unit: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> "ModelTypedMetrics[bool]":
        """Create a boolean metric."""
        return ModelTypedMetrics[bool](
            name=name, value=value, unit=unit, description=description, **kwargs
        )


# Export the model
__all__ = ["ModelTypedMetrics"]
