# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dispatch Lifecycle State enum for ModelDispatchLifecycleEvent (OMN-9885)."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDispatchLifecycleState(StrValueHelper, str, Enum):
    """Canonical lifecycle states for a dispatched command.

    Eliminates self-attested dispatch success: every dispatch must reach
    one of TERMINAL_SUCCESS, TERMINAL_FAILURE, TIMEOUT, CANCELLED, or DLQ
    via the documented emitter responsibility table.
    """

    ACCEPTED = "accepted"
    STARTED = "started"
    HEARTBEAT = "heartbeat"
    TERMINAL_SUCCESS = "terminal_success"
    TERMINAL_FAILURE = "terminal_failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    DLQ = "dlq"

    def is_terminal(self) -> bool:
        """True if no further transitions are valid from this state."""
        return self in {
            EnumDispatchLifecycleState.TERMINAL_SUCCESS,
            EnumDispatchLifecycleState.TIMEOUT,
            EnumDispatchLifecycleState.CANCELLED,
            EnumDispatchLifecycleState.DLQ,
        }


__all__ = ["EnumDispatchLifecycleState"]
