# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input of the work-ledger fold COMPUTE node (OMN-19405, typed work ledger T4)."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

__all__ = ["ModelWorkLedgerFoldInput"]


class ModelWorkLedgerFoldInput(BaseModel):
    """The complete lines of a JSON-lines work ledger, and the instant to judge leases at.

    The lines are raw text so that the fold itself decides what an unparseable
    line means (UNDECIDED), rather than a reader silently dropping it. Reading
    the file, and leaving out an unterminated final line that a writer has not
    finished, is the caller's effect boundary (``complete_ledger_lines``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    lines: tuple[str, ...] = Field(
        default=(),
        description="Complete ledger lines, each one canonical JSON record.",
    )
    as_of: AwareDatetime | None = Field(
        default=None,
        description=(
            "Instant against which a surface lease's expires_at is judged. None "
            "marks no lease expired. Expiry never releases a lease either way."
        ),
    )
