"""
Data classification enumeration.

Defines data classification levels for security and compliance.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumDataClassification(str, Enum):
    """
    Enumeration of data classification levels.

    Used for security, compliance, and data handling policies.
    """

    # Standard classification levels
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"
    TOP_SECRET = "top_secret"

    # Common aliases
    OPEN = "open"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    CLASSIFIED = "classified"

    # Default level
    UNCLASSIFIED = "unclassified"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_security_level(cls, classification: EnumDataClassification) -> int:
        """Get numeric security level (1-10, higher = more secure)."""
        mapping = {
            cls.PUBLIC: 1,
            cls.OPEN: 1,
            cls.UNCLASSIFIED: 2,
            cls.INTERNAL: 3,
            cls.PRIVATE: 4,
            cls.SENSITIVE: 5,
            cls.CONFIDENTIAL: 6,
            cls.CLASSIFIED: 7,
            cls.RESTRICTED: 8,
            cls.SECRET: 9,
            cls.TOP_SECRET: 10,
        }
        return mapping.get(classification, 2)

    @classmethod
    def is_public(cls, classification: EnumDataClassification) -> bool:
        """Check if data classification allows public access."""
        return classification in {cls.PUBLIC, cls.OPEN, cls.UNCLASSIFIED}

    @classmethod
    def requires_encryption(cls, classification: EnumDataClassification) -> bool:
        """Check if data classification requires encryption."""
        return classification in {
            cls.CONFIDENTIAL,
            cls.RESTRICTED,
            cls.SECRET,
            cls.TOP_SECRET,
            cls.CLASSIFIED,
        }

    @classmethod
    def get_retention_policy(cls, classification: EnumDataClassification) -> str:
        """Get default retention policy for classification level."""
        if classification in {cls.PUBLIC, cls.OPEN}:
            return "indefinite"
        if classification in {cls.INTERNAL, cls.PRIVATE}:
            return "7_years"
        if classification in {cls.CONFIDENTIAL, cls.SENSITIVE}:
            return "5_years"
        if classification in {cls.RESTRICTED, cls.CLASSIFIED}:
            return "3_years"
        if classification in {cls.SECRET, cls.TOP_SECRET}:
            return "1_year"
        return "default"


# Export the enum
__all__ = ["EnumDataClassification"]
