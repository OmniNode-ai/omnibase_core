# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed failure for a work event that cannot be rendered as an md row (OMN-16182)."""

from __future__ import annotations


class WorkLedgerRenderError(ValueError):
    """A work event cannot be rendered as one row of the md ledger.

    Raised when the row would break the md row grammar for a structural
    reason the renderer can see: a reference to an event it was not given, a
    reference to the wrong kind of event, a lane that is not one grammar
    token, a surface hold with no expiry, a surface release with no result, a
    correction that names nothing. The appender treats it as a refusal and
    writes nothing; ``render --repair`` answers UNDECIDED and writes nothing.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"cannot render work-ledger row: {reason}")


__all__ = ["WorkLedgerRenderError"]
