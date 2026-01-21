"""Model for sample evaluation results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelSampleResult(BaseModel):
    """Result for a single sample evaluation.

    Records whether a specific sample passed all its invariant checks.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sample_id: str = Field(  # string-id-ok: sample identifier for tracing
        ..., description="Unique identifier for the sample"
    )
    passed: bool = Field(..., description="Whether the sample passed all invariants")
    invariants_checked: list[str] = Field(
        ..., description="List of invariant IDs that were checked"
    )


__all__ = ["ModelSampleResult"]
