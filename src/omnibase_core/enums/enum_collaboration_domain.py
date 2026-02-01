"""
Enum for collaboration domains with security validation.

Provides structured collaboration domain definitions for secure
cross-instance collaboration in ONEX intelligence architecture.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCollaborationDomain(StrValueHelper, str, Enum):
    """
    Enum for collaboration domains with security validation.

    Defines allowed collaboration domains for secure cross-instance
    intelligence sharing and coordination.
    """

    # Development domains
    FRONTEND_DEVELOPMENT = "frontend_development"
    BACKEND_DEVELOPMENT = "backend_development"
    INFRASTRUCTURE = "infrastructure"
    DATABASE = "database"

    # Quality assurance domains
    TESTING = "testing"
    SECURITY_ANALYSIS = "security_analysis"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    CODE_REVIEW = "code_review"

    # Analysis domains
    PROBLEM_DIAGNOSIS = "problem_diagnosis"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"

    # Documentation domains
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    USER_DOCUMENTATION = "user_documentation"
    API_DOCUMENTATION = "api_documentation"

    # Project management domains
    TASK_COORDINATION = "task_coordination"
    PROGRESS_TRACKING = "progress_tracking"
    RESOURCE_PLANNING = "resource_planning"


__all__ = ["EnumCollaborationDomain"]
