"""
Metadata node status enumeration.

Provides strongly typed status values for metadata nodes in ONEX framework.
"""

from enum import Enum


class EnumMetadataNodeStatus(str, Enum):
    """Status of metadata nodes."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"
    DISABLED = "disabled"
