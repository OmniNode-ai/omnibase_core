"""
Enum for intelligence context types with security validation.

Provides structured, validated context type definitions for secure
cross-instance intelligence sharing in ONEX architecture.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumIntelligenceContextType(StrValueHelper, str, Enum):
    """
    Enum for intelligence context types with security validation.

    Defines allowed context types for cross-instance intelligence sharing
    with proper validation and security boundaries.
    """

    # Discovery contexts
    DISCOVERY_PATTERN = "discovery_pattern"
    DISCOVERY_SOLUTION = "discovery_solution"
    DISCOVERY_ISSUE = "discovery_issue"

    # Problem analysis contexts
    PROBLEM_DIAGNOSIS = "problem_diagnosis"
    PROBLEM_ROOT_CAUSE = "problem_root_cause"
    PROBLEM_WORKAROUND = "problem_workaround"

    # Solution contexts
    SOLUTION_IMPLEMENTATION = "solution_implementation"
    SOLUTION_OPTIMIZATION = "solution_optimization"
    SOLUTION_VALIDATION = "solution_validation"

    # Warning contexts
    WARNING_SECURITY = "warning_security"
    WARNING_PERFORMANCE = "warning_performance"
    WARNING_COMPATIBILITY = "warning_compatibility"

    # Coordination contexts
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_STATUS = "coordination_status"
    COORDINATION_HANDOFF = "coordination_handoff"


__all__ = ["EnumIntelligenceContextType"]
