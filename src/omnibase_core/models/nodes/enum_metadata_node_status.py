"""
Metadata Node Status Enumeration.

Enumeration defining different status states for metadata nodes.
"""

from enum import Enum


class EnumMetadataNodeStatus(str, Enum):
    """Metadata node status enumeration."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"


# Export for use
__all__ = ["EnumMetadataNodeStatus"]