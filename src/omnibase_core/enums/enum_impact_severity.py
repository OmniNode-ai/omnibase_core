from enum import Enum


class EnumImpactSeverity(str, Enum):
    """Business impact severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"
