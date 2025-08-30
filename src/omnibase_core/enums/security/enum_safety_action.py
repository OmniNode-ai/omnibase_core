"""Safety actions for intelligent context routing protection mechanisms."""

from enum import Enum


class EnumSafetyAction(str, Enum):
    """Safety actions that can be taken when violations are detected."""

    MONITOR = "monitor"
    ALERT = "alert"
    THROTTLE = "throttle"
    ISOLATE = "isolate"
    ROLLBACK = "rollback"
    EMERGENCY_STOP = "emergency_stop"
