# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelReceiptCheckResult — outcome of verifying a single evidence check's receipt.

Emitted by the receipt-gate per (ticket, evidence_item, check) triple. Mutable
(extra="forbid" but not frozen) so the gate can construct it incrementally
during contract traversal.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelReceiptCheckResult(BaseModel):
    """Outcome of verifying a single evidence check's receipt."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    ticket_id: str = Field(..., min_length=1)
    # string-id-ok: evidence item IDs are human-readable contract slugs (e.g., 'dod-001'), not UUIDs
    evidence_item_id: str = Field(..., min_length=1)
    check_type: str = Field(..., min_length=1)
    passed: bool
    reason: str


__all__ = ["ModelReceiptCheckResult"]
