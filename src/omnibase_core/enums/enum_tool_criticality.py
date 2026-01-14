"""Tool criticality enumeration."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolCriticality(StrValueHelper, str, Enum):
    """
    Tool criticality levels for business impact assessment.

    Defines the business criticality of tools in the system.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


__all__ = ["EnumToolCriticality"]
