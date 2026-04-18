# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelReceiptGateResult — aggregate outcome of the receipt-gate on a PR.

Returned by `validate_pr_receipts`. Used as the return type for CI output
formatting and as the contract for programmatic callers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.ticket.model_receipt_check_result import (
    ModelReceiptCheckResult,
)


class ModelReceiptGateResult(BaseModel):
    """Aggregate outcome of the receipt-gate on a PR."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    passed: bool
    skipped: bool = False
    friction_logged: bool = False
    message: str = ""
    checks: list[ModelReceiptCheckResult] = Field(default_factory=list)
    tickets_checked: list[str] = Field(default_factory=list)


__all__ = ["ModelReceiptGateResult"]
