"""
Data classification enum for ONEX security policies.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDataClassification(StrValueHelper, str, Enum):
    """Data classification levels for security and compliance."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"
    TOP_SECRET = "top_secret"
    OPEN = "open"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    CLASSIFIED = "classified"
    UNCLASSIFIED = "unclassified"

    @classmethod
    def get_security_level(cls, classification: "EnumDataClassification") -> int:
        """
        Get the numeric security level for a classification.

        Args:
            classification: The classification to get the security level for

        Returns:
            Integer security level from 1 (lowest) to 10 (highest)
        """
        security_levels = {
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
        return security_levels.get(classification, 1)

    @classmethod
    def is_public(cls, classification: "EnumDataClassification") -> bool:
        """
        Check if the classification is considered public.

        Args:
            classification: The classification to check

        Returns:
            True if public, False otherwise
        """
        public_classifications = {cls.PUBLIC, cls.OPEN, cls.UNCLASSIFIED}
        return classification in public_classifications

    @classmethod
    def requires_encryption(cls, classification: "EnumDataClassification") -> bool:
        """
        Check if the classification requires encryption.

        Args:
            classification: The classification to check

        Returns:
            True if encryption is required, False otherwise
        """
        encrypted_classifications = {
            cls.CONFIDENTIAL,
            cls.RESTRICTED,
            cls.SECRET,
            cls.TOP_SECRET,
            cls.CLASSIFIED,
        }
        return classification in encrypted_classifications

    @classmethod
    def get_retention_policy(cls, classification: "EnumDataClassification") -> str:
        """
        Get the retention policy for a classification.

        Args:
            classification: The classification to get the retention policy for

        Returns:
            Retention policy string (e.g., "indefinite", "7_years", "5_years", "3_years", "1_year")
        """
        retention_policies = {
            cls.PUBLIC: "indefinite",
            cls.OPEN: "indefinite",
            cls.UNCLASSIFIED: "indefinite",
            cls.INTERNAL: "7_years",
            cls.PRIVATE: "7_years",
            cls.CONFIDENTIAL: "5_years",
            cls.SENSITIVE: "5_years",
            cls.RESTRICTED: "3_years",
            cls.CLASSIFIED: "3_years",
            cls.SECRET: "1_year",
            cls.TOP_SECRET: "1_year",
        }
        return retention_policies.get(classification, "indefinite")
