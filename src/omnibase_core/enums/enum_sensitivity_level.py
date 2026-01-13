from enum import Enum, unique


@unique
class EnumSensitivityLevel(str, Enum):
    """Sensitivity levels for detected information."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
