"""Model for invariant check results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelInvariantResult(BaseModel):
    """Result for a single invariant check.

    Tracks passed, failed, and total counts for a specific invariant type.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    passed: int = Field(..., ge=0, description="Number of checks that passed")
    failed: int = Field(..., ge=0, description="Number of checks that failed")
    total: int = Field(..., ge=0, description="Total number of checks performed")


__all__ = ["ModelInvariantResult"]
