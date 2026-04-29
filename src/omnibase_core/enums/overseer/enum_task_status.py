# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumTaskStatus — FSM states for overseer task lifecycle (OMN-10251)."""

from __future__ import annotations

from enum import StrEnum


class EnumTaskStatus(StrEnum):
    """FSM states for overseer task lifecycle.

    10-member finite state machine covering the full task lifecycle
    from creation through terminal states.
    """

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


__all__ = ["EnumTaskStatus"]
