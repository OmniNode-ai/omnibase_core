"""Model for validation failure details."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelFailureDetail(BaseModel):
    """Details about a single validation failure.

    Captures the context of a failed invariant check including sample ID,
    invariant ID, and comparison values.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sample_id: str = Field(  # string-id-ok: sample identifier for tracing
        ..., description="ID of the sample that failed"
    )
    invariant_id: str = Field(  # string-id-ok: invariant identifier
        ..., description="ID of the invariant that was violated"
    )
    expected: str | None = Field(
        default=None, description="Expected value (if applicable)"
    )
    actual: str | None = Field(default=None, description="Actual value observed")
    message: str | None = Field(
        default=None, description="Human-readable failure message"
    )


__all__ = ["ModelFailureDetail"]
