from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSensitivityLevel(StrValueHelper, str, Enum):
    """Sensitivity levels for detected information."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


__all__ = ["EnumSensitivityLevel"]
