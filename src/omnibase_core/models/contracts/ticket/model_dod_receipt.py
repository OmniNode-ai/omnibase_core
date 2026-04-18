# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodReceipt — proof artifact for a single dod_evidence check run.

A receipt is the **only** acceptable proof that a ticket's DoD check was
executed. The receipt-gate CI check (`validate_pr_receipts.py`) blocks
merge on any PR whose linked ticket contract has dod_evidence items
without corresponding PASS receipts.

Design rule: ticket contracts declare intent (what must be proved).
Receipts declare fact (what was proved, when, by whom, with what output).
A ticket is not Done without every declared check having a PASS receipt.

Receipts are stored at:
    onex_change_control/drift/dod_receipts/<OMN-XXXX>/<evidence-item-id>/<check-type>.yaml

The path encodes ticket → evidence item → check, mirroring the contract
structure so lookup is O(1) path traversal, not search.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus

_TICKET_ID_RE = re.compile(r"^OMN-\d+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


class ModelDodReceipt(BaseModel):
    """Receipt proving a single dod_evidence check was run for a ticket.

    Frozen. Every field except ``actual_output`` is required — there is no
    such thing as an "aspirational" receipt. If a receipt exists on disk,
    it asserts the check ran with the recorded outcome.

    A receipt is consumed by the receipt-gate CI check at PR merge time
    and by ``node_dod_verify`` at ticket-close time. Both treat absence
    as identical to FAIL.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    ticket_id: str = Field(
        ..., description="Linear ticket this receipt proves (e.g., OMN-9084)"
    )
    # string-id-ok: evidence item IDs are human-readable slugs from the contract YAML (e.g., 'dod-001'), not UUIDs
    evidence_item_id: str = Field(
        ..., min_length=1, description="dod_evidence[].id this receipt covers"
    )
    check_type: str = Field(
        ...,
        min_length=1,
        description="dod_evidence[].checks[].check_type this receipt executed",
    )
    check_value: str = Field(
        ...,
        min_length=1,
        description="The original check_value from the contract (for audit parity)",
    )
    status: EnumReceiptStatus = Field(
        ..., description="PASS or FAIL — absence is also treated as FAIL"
    )
    run_timestamp: datetime = Field(
        ..., description="UTC timestamp when the check was executed"
    )
    commit_sha: str = Field(
        ...,
        description=(
            "Git commit SHA the check was executed against. Used by the "
            "receipt-gate to reject stale receipts that predate the PR head."
        ),
    )
    runner: str = Field(
        ...,
        min_length=1,
        description=(
            "Who/what ran the check — agent name, worker ID, human login, or "
            "CI job identifier. Used for audit + friction attribution."
        ),
    )
    actual_output: str | None = Field(
        default=None,
        description=(
            "Truncated output from the check (stdout, HTTP body, file content). "
            "Large outputs should be stored in a sibling file and referenced here "
            "via path. None is allowed when the check produces no output."
        ),
    )
    exit_code: int | None = Field(
        default=None,
        description="Exit code for command-type checks. None when not applicable.",
    )
    duration_ms: int | None = Field(
        default=None,
        ge=0,
        description="Wall-clock duration in milliseconds. None when not measured.",
    )
    pr_number: int | None = Field(
        default=None,
        ge=1,
        description=(
            "PR number this receipt was produced for. Used to correlate receipts "
            "to merge gate invocations. None for receipts not tied to a PR."
        ),
    )

    @field_validator("ticket_id")
    @classmethod
    def _validate_ticket_id(cls, v: str) -> str:
        if not _TICKET_ID_RE.match(v):
            raise ValueError(f"ticket_id must match OMN-\\d+, got: {v!r}")
        return v

    @field_validator("commit_sha")
    @classmethod
    def _validate_commit_sha(cls, v: str) -> str:
        # Explicit length + case checks before regex, so uppercase/short/long
        # strings fail identically on every test-runner configuration.
        if not (7 <= len(v) <= 40):
            raise ValueError(f"commit_sha must be 7-40 hex chars (git SHA), got: {v!r}")
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError(f"commit_sha must be 7-40 hex chars (git SHA), got: {v!r}")
        if not _SHA_RE.match(v):
            raise ValueError(f"commit_sha must be 7-40 hex chars (git SHA), got: {v!r}")
        return v

    @field_validator("run_timestamp")
    @classmethod
    def _validate_tz_aware(cls, v: Any) -> datetime:
        if not isinstance(v, datetime):
            raise ValueError(f"run_timestamp must be datetime, got {type(v).__name__}")
        if v.tzinfo is None:
            raise ValueError("run_timestamp must be timezone-aware (UTC)")
        return v.astimezone(UTC)


__all__ = ["ModelDodReceipt"]
