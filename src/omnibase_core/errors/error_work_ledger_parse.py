# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed failure for a work-ledger JSON line that is not a valid record (OMN-16177)."""

from __future__ import annotations


class WorkLedgerParseError(ValueError):
    """A work-ledger line could not be read as one ``ModelWorkLedgerRecord``.

    Raised for every defect, never a partial record: a line that is not one
    JSON object, an unknown ``schema`` or ``kind``, an extra or missing field,
    a naive timestamp, a duplicate key, or trailing bytes after the object.
    A reader that decides anything from the ledger treats this as UNDECIDED.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"invalid work-ledger line: {reason}")


__all__ = ["WorkLedgerParseError"]
