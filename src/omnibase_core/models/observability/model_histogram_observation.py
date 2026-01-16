"""Histogram metric observation model for observability."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelHistogramObservation(BaseModel):
    """Represents a histogram metric observation event.

    Histograms track distributions of values over time,
    used for latency, request sizes, etc. The value is
    recorded into appropriate buckets by the metrics backend.

    Attributes:
        name: Metric name following naming conventions (e.g., "request_duration_seconds").
        labels: Key-value pairs for metric dimensions.
        value: Observed value to record in the histogram.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Metric name (e.g., 'request_duration_seconds')",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Metric labels for dimensional filtering",
    )
    value: float = Field(
        ...,
        ge=0,
        description="Observed value (must be non-negative for histograms)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelHistogramObservation"]
