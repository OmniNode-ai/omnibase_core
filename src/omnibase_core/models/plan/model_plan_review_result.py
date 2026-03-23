# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelPlanReviewResult", "PlanReviewResult"]

_HEX_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-fA-F]{16}$")


class ModelPlanReviewResult(BaseModel):
    """Frozen sub-model for adversarial review results.

    Ties a review outcome to a specific document revision via its
    fingerprint, enabling convergence tracking across review passes.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    reviewer: str = Field(
        ...,
        min_length=1,
        description="Who performed the review.",
    )
    passed: bool = Field(
        ...,
        description="Whether the review passed.",
    )
    findings: list[str] = Field(
        default_factory=list,
        description="Review issues found.",
    )
    document_fingerprint: str = Field(
        ...,
        description=(
            "16-character hex fingerprint of the ModelPlanDocument at review time. "
            "Ties reviews to specific document revisions."
        ),
    )
    reviewed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the review was performed (UTC).",
    )

    @field_validator("document_fingerprint", mode="before")
    @classmethod
    def _validate_fingerprint(cls, v: str) -> str:
        """Validate that fingerprint is exactly 16 hex characters."""
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError/TypeError
            raise TypeError(
                f"document_fingerprint must be a string, got {type(v).__name__}"
            )
        normalized = v.strip().lower()
        if not _HEX_FINGERPRINT_PATTERN.match(normalized):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"document_fingerprint {v!r} must be exactly 16 hex characters "
                f"(e.g., 'a1b2c3d4e5f67890')"  # pragma: allowlist secret
            )
        return normalized

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def _enforce_utc_timezone(cls, v: Any) -> Any:
        """Enforce UTC timezone on datetime fields during deserialization.

        Naive datetimes (no timezone info) are assumed UTC and have the UTC
        timezone attached. Datetimes with a non-UTC timezone are converted
        to UTC. Already-UTC datetimes pass through unchanged.
        """
        if not isinstance(v, datetime):
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)


PlanReviewResult = ModelPlanReviewResult
