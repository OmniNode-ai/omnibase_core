"""
Example validation status enumeration.
"""

from enum import Enum


class EnumExampleValidationStatus(str, Enum):
    """Validation status for examples."""

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    REQUIRES_REVIEW = "requires_review"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    ARCHIVED = "archived"