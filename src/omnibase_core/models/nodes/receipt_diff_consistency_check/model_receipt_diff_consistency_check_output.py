# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed output for the receipt diff-consistency COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.receipt_diff_consistency_check.model_receipt_diff_consistency_violation import (
    ModelReceiptDiffConsistencyViolation,
)


class ModelReceiptDiffConsistencyCheckOutput(BaseModel):
    """Contradicted attestations, one entry per violation, in receipt order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: list[ModelReceiptDiffConsistencyViolation] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True iff no attestation was contradicted."""
        return not self.violations
