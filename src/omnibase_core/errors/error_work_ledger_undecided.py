# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed doubt about a work-ledger file that makes an answer UNDECIDED (OMN-16182)."""

from __future__ import annotations


class WorkLedgerUndecidedError(ValueError):
    """A work-ledger comparison cannot be answered, so it answers UNDECIDED.

    Raised inside ``onex-work-ledger render`` for a variable that is unset, a
    file that cannot be read or decoded, a JSON line that does not parse, or
    an md lock that was not taken in time. The command turns it into one
    ``reason=`` line and exit 2; it never escapes as a crash and never reads
    as CLEAR.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"work ledger undecided: {reason}")


__all__ = ["WorkLedgerUndecidedError"]
