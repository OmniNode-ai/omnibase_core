# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Complete violation baseline model for incremental adoption.

Baselines capture current violations so teams can adopt validation
incrementally. New violations are flagged, while baselined ones are
tracked but don't fail the build.

Related ticket: OMN-1774
"""

from __future__ import annotations

import functools
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from .model_baseline_generator import ModelBaselineGenerator
from .model_baseline_violation import ModelBaselineViolation


class ModelViolationBaseline(BaseModel):
    """Complete violation baseline for a policy.

    The baseline file format is designed for human readability (YAML)
    and version control friendliness (stable ordering, no timestamps
    that change on every run).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: str = Field(
        default="1.0",
        description="Version of the baseline file format",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this baseline was created",
    )

    policy_id: str = Field(  # string-id-ok: human-readable policy identifier
        description="ID of the policy this baseline belongs to",
    )

    generator: ModelBaselineGenerator = Field(
        description="Tool that generated this baseline",
    )

    violations: list[ModelBaselineViolation] = Field(
        default_factory=list,
        description="List of baselined violations",
    )

    def violation_count(self) -> int:
        """Return the number of violations in this baseline."""
        return len(self.violations)

    @functools.cached_property
    def _fingerprint_set(self) -> frozenset[str]:
        """Cached set of fingerprints for O(1) lookup."""
        return frozenset(v.fingerprint for v in self.violations)

    def has_violation(self, fingerprint: str) -> bool:
        """Check if a violation with the given fingerprint is baselined."""
        return fingerprint in self._fingerprint_set

    def get_violation(self, fingerprint: str) -> ModelBaselineViolation | None:
        """Get a violation by its fingerprint."""
        for v in self.violations:
            if v.fingerprint == fingerprint:
                return v
        return None


__all__ = ["ModelBaselineGenerator", "ModelBaselineViolation", "ModelViolationBaseline"]
