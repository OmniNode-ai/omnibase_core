"""
Metadata node status enumeration.
"""

from __future__ import annotations

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
