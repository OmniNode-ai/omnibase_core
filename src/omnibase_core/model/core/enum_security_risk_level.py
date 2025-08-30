"""
Security risk level enum for security assessments.
"""

from enum import Enum


class SecurityRiskLevel(str, Enum):
    """Security risk levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
