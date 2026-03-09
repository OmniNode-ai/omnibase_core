# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Handler Status Enum.

Defines the lifecycle status values for handlers in the ONEX system.
Used by HandlerStateModel to capture the logical (serializable) state
of a handler's operational status.

.. versionadded:: 0.8.0
    Added as part of OMN-4223 (HandlerStateModel — logical state only).
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerStatus(StrValueHelper, str, Enum):
    """
    Handler operational status values.

    Captures the logical lifecycle state of a handler. This enum is used
    exclusively in ``HandlerStateModel`` — a serializable snapshot of handler
    state that contains no runtime resources.

    Lifecycle Flow::

        INITIALIZING -> READY -> DEGRADED -> STOPPED
                    \\-> STOPPED  (if initialization fails)

    States:
        INITIALIZING: Handler is starting up; not yet ready to process requests.
        READY: Handler is fully initialized and processing normally.
        DEGRADED: Handler is operational but experiencing errors or reduced capacity.
        STOPPED: Handler has been shut down and is no longer processing.
    """

    INITIALIZING = "initializing"
    """Handler is starting up; not yet ready to process requests."""

    READY = "ready"
    """Handler is fully initialized and processing normally."""

    DEGRADED = "degraded"
    """Handler is operational but experiencing errors or reduced capacity."""

    STOPPED = "stopped"
    """Handler has been shut down and is no longer processing."""

    def is_terminal(self) -> bool:
        """Return True if this status is a terminal state (no further transitions expected)."""
        return self == EnumHandlerStatus.STOPPED

    def is_operational(self) -> bool:
        """Return True if the handler is in an operational (non-stopped) state."""
        return self != EnumHandlerStatus.STOPPED


__all__ = ["EnumHandlerStatus"]
