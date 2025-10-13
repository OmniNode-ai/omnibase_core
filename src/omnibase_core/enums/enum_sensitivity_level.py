from enum import Enum


class EnumSensitivityLevel(str, Enum):
    """Sensitivity levels for detected information."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
