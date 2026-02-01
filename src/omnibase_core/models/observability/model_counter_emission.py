"""Counter metric emission model for observability."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCounterEmission(BaseModel):
    """Represents a counter metric emission event.

    Counters are monotonically increasing values used to track
    cumulative counts (e.g., requests served, errors encountered).

    Attributes:
        name: Metric name following naming conventions (e.g., "http_requests_total").
        labels: Key-value pairs for metric dimensions (e.g., {"method": "GET"}).
        increment: Amount to increment the counter by. Must be positive.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Metric name (e.g., 'http_requests_total')",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Metric labels for dimensional filtering",
    )
    increment: float = Field(
        default=1.0,
        gt=0,
        description="Amount to increment counter by (must be positive)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelCounterEmission"]
