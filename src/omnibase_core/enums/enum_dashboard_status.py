# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dashboard status enumeration for dashboard lifecycle states.

This module defines the lifecycle states for dashboard instances,
tracking connection status and operational readiness. Used for
monitoring dashboard health and triggering reconnection logic.

Example:
    Handle dashboard status changes::

        from omnibase_core.enums import EnumDashboardStatus

        def on_status_change(status: EnumDashboardStatus) -> None:
            if status.requires_reconnection:
                attempt_reconnect()
            elif status.is_operational:
                refresh_widgets()
"""

from enum import Enum

__all__ = ("EnumDashboardStatus",)


class EnumDashboardStatus(str, Enum):
    """Dashboard connection and lifecycle status enumeration.

    Tracks the operational state of a dashboard instance through its
    lifecycle. Status transitions typically follow: INITIALIZING ->
    CONNECTED -> DISCONNECTED (or ERROR).

    Attributes:
        INITIALIZING: Dashboard is starting up, loading configuration,
            and establishing initial connections. Widgets may not be
            rendered yet.
        CONNECTED: Dashboard is fully operational with active data
            connections. Widgets are rendering and receiving updates.
        DISCONNECTED: Dashboard has lost its data connection but may
            recover automatically. Widgets display stale data.
        ERROR: Dashboard encountered a fatal error and cannot operate.
            Manual intervention or restart may be required.

    Example:
        Check dashboard health::

            status = EnumDashboardStatus.DISCONNECTED
            if status.requires_reconnection:
                print("Attempting to reconnect...")
    """

    INITIALIZING = "initializing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    @property
    def is_operational(self) -> bool:
        """Check if dashboard is in an operational state.

        An operational dashboard has active connections and is
        rendering widgets with live data.

        Returns:
            True if the status is CONNECTED, False otherwise.
        """
        return self == EnumDashboardStatus.CONNECTED

    @property
    def is_terminal(self) -> bool:
        """Check if dashboard is in a terminal/error state.

        A terminal state indicates the dashboard cannot recover
        without intervention.

        Returns:
            True if the status is ERROR, False otherwise.
        """
        return self == EnumDashboardStatus.ERROR

    @property
    def requires_reconnection(self) -> bool:
        """Check if dashboard needs reconnection.

        Dashboards in DISCONNECTED or ERROR state should attempt
        to re-establish their data connections.

        Returns:
            True if the status is DISCONNECTED or ERROR, False otherwise.
        """
        return self in {
            EnumDashboardStatus.DISCONNECTED,
            EnumDashboardStatus.ERROR,
        }
