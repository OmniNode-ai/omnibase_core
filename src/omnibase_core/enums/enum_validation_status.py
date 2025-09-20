"""
Validation status enumeration for validation operations.

Provides strongly typed validation status values for validation result tracking.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumValidationStatus(str, Enum):
    """
    Strongly typed validation status for validation operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_successful(cls, status: "EnumValidationStatus") -> bool:
        """Check if the validation status is successful."""
        return status in {cls.VALID, cls.WARNING}

    @classmethod
    def is_failed(cls, status: "EnumValidationStatus") -> bool:
        """Check if the validation status is failed."""
        return status in {cls.INVALID, cls.ERROR}

    @classmethod
    def is_incomplete(cls, status: "EnumValidationStatus") -> bool:
        """Check if the validation status is incomplete."""
        return status in {cls.PENDING, cls.PARTIAL, cls.SKIPPED}

    @classmethod
    def is_terminated(cls, status: "EnumValidationStatus") -> bool:
        """Check if the validation status is terminated."""
        return status in {cls.EXPIRED, cls.CANCELLED}

    @classmethod
    def requires_attention(cls, status: "EnumValidationStatus") -> bool:
        """Check if the validation status requires attention."""
        return status in {cls.INVALID, cls.ERROR, cls.WARNING, cls.EXPIRED}

    @classmethod
    def is_actionable(cls, status: "EnumValidationStatus") -> bool:
        """Check if the validation status is actionable."""
        return status not in {cls.SKIPPED, cls.CANCELLED, cls.UNKNOWN}


# Export for use
__all__ = ["EnumValidationStatus"]