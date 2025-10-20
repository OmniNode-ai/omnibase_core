"""Tool criticality enumeration."""

from enum import Enum


class EnumToolCriticality(str, Enum):
    """
    Tool criticality levels for business impact assessment.

    Defines the business criticality of tools in the system.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"
