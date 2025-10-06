"""
Data classification enum for ONEX security policies.
"""

import enum


class EnumDataClassification(enum.StrEnum):
    """Data classification levels for security and compliance."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
