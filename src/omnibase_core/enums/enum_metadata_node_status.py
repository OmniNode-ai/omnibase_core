"""
Metadata node status enumeration.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetadataNodeStatus(StrValueHelper, str, Enum):
    """Metadata node status enumeration."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"


__all__ = ["EnumMetadataNodeStatus"]
