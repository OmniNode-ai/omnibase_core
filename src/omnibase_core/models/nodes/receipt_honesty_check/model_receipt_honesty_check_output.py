# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed output for the receipt honesty COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_finding import (
    ModelReceiptHonestyFinding,
)


class ModelReceiptHonestyCheckOutput(BaseModel):
    """Per-receipt findings, in scan order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: list[ModelReceiptHonestyFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True iff no receipt has an honesty violation."""
        return not self.findings
