"""Business impact severity levels for risk assessment and prioritization."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumImpactSeverity(StrValueHelper, str, Enum):
    """Business impact severity levels.

    Used for classifying the business impact of issues, incidents, or changes.
    Distinct from EnumSeverity (system/logging severity) - this measures business impact.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


__all__ = ["EnumImpactSeverity"]
