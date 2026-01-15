"""Contract Drift Details Model.

This module provides the ModelDriftDetails class for structured reporting of
contract drift, which occurs when a contract's computed fingerprint no longer
matches its registered fingerprint.

Drift Detection:
    Contract drift can occur due to:
    - Version changes (semantic version mismatch)
    - Content changes (hash mismatch)
    - Both version and content changes

The details model provides typed access to drift information, replacing
untyped dictionaries for ONEX compliance and better IDE support.

Typical Usage:
    Drift details are populated during drift detection and included in
    ModelDriftResult for debugging and migration decisions:
    - CI/CD validation pipelines
    - Contract migration tools
    - Development-time contract verification

See Also:
    CONTRACT_STABILITY_SPEC.md: Detailed specification for drift detection.
    ModelDriftResult: Parent model that contains drift details.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDriftDetails(BaseModel):
    """Structured details about contract drift.

    Provides typed fields for drift analysis, replacing untyped dictionaries
    for better type safety and IDE support. This model captures the specifics
    of what changed between expected and computed fingerprints.

    All fields are optional since drift may be detected at different levels
    of detail depending on the detection context.

    This model is immutable (frozen) to ensure drift details remain consistent
    throughout the drift handling process.

    Attributes:
        reason: Human-readable explanation of why drift was detected.
        version_match: Whether the semantic versions match (None if not checked).
        hash_match: Whether the content hashes match (None if not checked).
        expected_semver: Expected version as semver string for display.
        computed_semver: Computed version as semver string for display.
        expected_hash: Expected hash prefix from registry.
        computed_hash: Computed hash prefix from current contract.

    Example:
        >>> details = ModelDriftDetails(
        ...     reason="Content changed without version bump",
        ...     version_match=True,
        ...     hash_match=False,
        ...     expected_hash="8fa1e2b4c9d1",
        ...     computed_hash="3b2c1a9f8e7d",
        ... )
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
        from_attributes=True,  # pytest-xdist compatibility
    )


__all__ = ["ModelDriftDetails"]
