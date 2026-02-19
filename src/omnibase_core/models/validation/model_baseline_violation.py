# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Individual violation model for baselines.

Captures a single violation with its fingerprint and metadata.

Related ticket: OMN-1774
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelBaselineViolation(BaseModel):
    """A single violation captured in the baseline.

    Violations are identified by their fingerprint - a hash of the
    violation's stable properties (rule_id, file_path, symbol).
    Severity is NOT included because it's a rule property, not a
    violation property.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    fingerprint: str = Field(
        description="Hash identifying this specific violation",
    )

    rule_id: str = Field(  # string-id-ok: references rule_id from RuleRegistry
        description="ID of the rule that produced this violation",
    )

    file_path: str = Field(
        description="Path to the file where violation was found",
    )

    symbol: str = Field(
        description="Symbol or import that caused the violation",
    )

    message: str = Field(
        description="Human-readable violation message",
    )

    first_seen: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this violation was first detected",
    )


__all__ = ["ModelBaselineViolation"]
