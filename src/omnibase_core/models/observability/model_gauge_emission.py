"""Gauge metric emission model for observability."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelGaugeEmission(BaseModel):
    """Represents a gauge metric emission event.

    Gauges are point-in-time values that can go up or down,
    used to track current state (e.g., temperature, queue depth).

    Attributes:
        name: Metric name following naming conventions (e.g., "queue_depth").
        labels: Key-value pairs for metric dimensions.
        value: Current gauge value (can be any float, including negative).
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Metric name (e.g., 'queue_depth')",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Metric labels for dimensional filtering",
    )
    value: float = Field(
        ...,
        description="Current gauge value",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelGaugeEmission"]
