"""
Generic typed metrics model.

Unified generic model replacing type-specific metrics variants.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T", str, int, float, bool)


class ModelTypedMetrics(BaseModel, Generic[T]):
    """Generic metrics model replacing type-specific variants."""

    metric_id: UUID = Field(..., description="UUID for metric identifier")
    metric_display_name: str = Field(
        default="",
        description="Human-readable metric name",
    )
    value: T = Field(..., description="Typed metric value")
    unit: str = Field(default="", description="Unit of measurement")
    description: str = Field(default="", description="Metric description")

    @classmethod
    def string_metric(
        cls,
        name: str,
        value: str,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[str]:
        """Create a string metric."""
        import hashlib

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[str](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    @classmethod
    def int_metric(
        cls,
        name: str,
        value: int,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[int]:
        """Create an integer metric."""
        import hashlib

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[int](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    @classmethod
    def float_metric(
        cls,
        name: str,
        value: float,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[float]:
        """Create a float metric."""
        import hashlib

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[float](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    @classmethod
    def boolean_metric(
        cls,
        name: str,
        value: bool,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[bool]:
        """Create a boolean metric."""
        import hashlib

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[bool](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelTypedMetrics"]
