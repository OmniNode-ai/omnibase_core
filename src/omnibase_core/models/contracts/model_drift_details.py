"""Contract Drift Details Model.

Provides structured details about contract drift for typed access.

See: CONTRACT_STABILITY_SPEC.md for detailed specification.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDriftDetails(BaseModel):
    """Structured details about contract drift.

    Provides typed fields for drift details (replaces untyped dict) for ONEX compliance.
    """

    reason: str | None = Field(
        default=None,
        description="Human-readable reason for drift",
    )
    version_match: bool | None = Field(
        default=None,
        description="Whether versions match",
    )
    hash_match: bool | None = Field(
        default=None,
        description="Whether hashes match",
    )
    expected_semver: str | None = Field(
        default=None,
        description="Expected version as semver string for display",
    )
    computed_semver: str | None = Field(
        default=None,
        description="Computed version as semver string for display",
    )
    expected_hash: str | None = Field(
        default=None,
        description="Expected hash prefix",
    )
    computed_hash: str | None = Field(
        default=None,
        description="Computed hash prefix",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )


__all__ = ["ModelDriftDetails"]
