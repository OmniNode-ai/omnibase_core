"""Safety levels for intelligent context routing protection mechanisms."""

from enum import Enum


class EnumSafetyLevel(str, Enum):
    """Safety levels for different protection mechanisms."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"
