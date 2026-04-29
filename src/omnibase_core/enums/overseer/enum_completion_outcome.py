# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumCompletionOutcome — terminal outcome for overseer performance ledger (OMN-10251)."""

from __future__ import annotations

from enum import StrEnum


class EnumCompletionOutcome(StrEnum):
    """Terminal outcome for a completed task in the performance ledger."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


__all__ = ["EnumCompletionOutcome"]
