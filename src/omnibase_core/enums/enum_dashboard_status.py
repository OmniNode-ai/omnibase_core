# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dashboard status enumeration for dashboard lifecycle states."""

from enum import Enum

__all__ = ["EnumDashboardStatus"]


class EnumDashboardStatus(str, Enum):
    """Dashboard connection and lifecycle status values.

    Tracks the operational state of a dashboard instance.
    """

    INITIALIZING = "initializing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    @property
    def is_operational(self) -> bool:
        """Check if dashboard is in an operational state."""
        return self == EnumDashboardStatus.CONNECTED

    @property
    def is_terminal(self) -> bool:
        """Check if dashboard is in a terminal/error state."""
        return self == EnumDashboardStatus.ERROR

    @property
    def requires_reconnection(self) -> bool:
        """Check if dashboard needs reconnection."""
        return self in {
            EnumDashboardStatus.DISCONNECTED,
            EnumDashboardStatus.ERROR,
        }
