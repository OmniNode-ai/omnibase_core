"""
Security Risk Level Enum.

Strongly typed enumeration for security risk assessment levels.
"""

from enum import Enum, unique


@unique
class EnumSecurityRiskLevel(str, Enum):
    """
    Security risk level classifications for security assessments.

    Used for categorizing overall risk levels in security analysis.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_actionable(cls, risk_level: "EnumSecurityRiskLevel") -> bool:
        """Check if the risk level requires action."""
        return risk_level in {cls.HIGH, cls.CRITICAL}

    @classmethod
    def is_severe(cls, risk_level: "EnumSecurityRiskLevel") -> bool:
        """Check if the risk level is severe."""
        return risk_level == cls.CRITICAL

    def get_severity_score(self) -> int:
        """Get numeric severity score (0-100)."""
        scores = {
            self.LOW: 25,
            self.MEDIUM: 50,
            self.HIGH: 75,
            self.CRITICAL: 100,
            self.UNKNOWN: 0,
        }
        return scores.get(self, 0)


# Export for use
__all__ = ["EnumSecurityRiskLevel"]
