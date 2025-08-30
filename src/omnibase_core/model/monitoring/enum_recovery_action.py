"""
Enum for recovery actions.

Automated recovery actions for monitoring.
"""

from enum import Enum


class EnumRecoveryAction(str, Enum):
    """Automated recovery actions."""

    RESTART_AGENT = "restart_agent"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    THROTTLE = "throttle"
    EMERGENCY_STOP = "emergency_stop"
    FAILOVER = "failover"
    ROLLBACK = "rollback"
    CIRCUIT_BREAK = "circuit_break"
    QUOTA_REALLOCATE = "quota_reallocate"
    NOTIFY_HUMAN = "notify_human"
