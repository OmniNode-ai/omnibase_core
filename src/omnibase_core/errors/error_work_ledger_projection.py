# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed fault of the work-ledger projection read surface (OMN-20002)."""

from __future__ import annotations


class WorkLedgerProjectionError(ValueError):
    """The projection snapshot could not be read as a complete, fresh ledger.

    Raised for an unset URL, an unreachable or timed-out host, a non-200
    answer (an unknown topic is a 404), a body that is not the documented
    page, a page loop that does not end, and a snapshot the service marks
    stale. ``kind`` is a short token for the header (``unconfigured``,
    ``unreachable``, ``http-<status>``, ``invalid``, ``stale``); ``reason`` is
    the one-line text that ends up in a ``reason=`` line. A reader never
    treats this as CLEAR: it falls back to the local buffer (``--source
    auto``) or answers UNDECIDED.
    """

    def __init__(self, kind: str, reason: str) -> None:
        self.kind = kind
        self.reason = reason
        super().__init__(f"work ledger projection fault ({kind}): {reason}")


__all__ = ["WorkLedgerProjectionError"]
