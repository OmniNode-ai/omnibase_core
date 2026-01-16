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

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ("EnumDashboardStatus",)


@unique
class EnumDashboardStatus(StrValueHelper, str, Enum):
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

    Properties:
        is_operational: True if status is CONNECTED.
        is_terminal: True if status is ERROR.
        requires_reconnection: True if DISCONNECTED or ERROR.
        requires_manual_intervention: True if ERROR (may need human investigation).

    Example:
        Check dashboard health::

            status = EnumDashboardStatus.DISCONNECTED
            if status.requires_reconnection:
                print("Attempting to reconnect...")

        Handle errors requiring investigation::

            status = EnumDashboardStatus.ERROR
            if status.requires_manual_intervention:
                notify_operators("Dashboard error requires investigation")
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
        return self is EnumDashboardStatus.CONNECTED

    @property
    def is_terminal(self) -> bool:
        """Check if dashboard is in a terminal/error state.

        A terminal state indicates the dashboard cannot recover
        without intervention.

        Returns:
            True if the status is ERROR, False otherwise.
        """
        return self is EnumDashboardStatus.ERROR

    @property
    def requires_reconnection(self) -> bool:
        """Check if this status indicates a reconnection attempt is appropriate.

        Returns True for statuses where reconnection may restore functionality:

        - **DISCONNECTED**: Connection was lost (e.g., network interruption,
          server restart). Reconnection is the standard recovery path and
          typically succeeds once connectivity is restored.

        - **ERROR**: Some errors are transient and recoverable via reconnection
          (e.g., network timeouts, temporary service unavailability, rate
          limiting). However, fatal errors (e.g., invalid credentials,
          misconfigured endpoints, schema mismatches) will not be resolved
          by reconnection alone.

        Note:
            Callers should inspect error context before reconnecting in ERROR
            state to distinguish transient issues from fatal configuration
            problems. Use :attr:`is_terminal` to check if the dashboard is in
            a terminal error state that may require manual intervention.

        Returns:
            True if the status is DISCONNECTED or ERROR, False otherwise.

        See Also:
            :attr:`is_terminal`: Check for fatal error states.
            :attr:`is_operational`: Check for healthy connected state.
        """
        return self in {
            EnumDashboardStatus.DISCONNECTED,
            EnumDashboardStatus.ERROR,
        }

    @property
    def requires_manual_intervention(self) -> bool:
        """Check if this status indicates manual intervention may be required.

        Returns True for ERROR state, indicating the dashboard encountered
        an error that may require manual investigation or configuration
        changes before recovery is possible.

        This differs from requires_reconnection in that:

        - **requires_reconnection**: Automatic retry/reconnect may help
          (DISCONNECTED, ERROR).
        - **requires_manual_intervention**: Human investigation likely needed
          (ERROR only).

        Use Case:
            If both requires_reconnection and requires_manual_intervention are
            True, the system should attempt reconnection but also notify
            operators for investigation in case the error is not transient.

        Returns:
            True if ERROR state, False otherwise.

        See Also:
            :attr:`requires_reconnection`: Check if reconnection is appropriate.
            :attr:`is_terminal`: Check for fatal error states.
        """
        return self is EnumDashboardStatus.ERROR
