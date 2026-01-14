"""
Namespace strategy enumeration for ONEX framework.

Defines the available strategies for namespace handling in ONEX components.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNamespaceStrategy(StrValueHelper, str, Enum):
    """Enumeration of namespace strategies."""

    ONEX_DEFAULT = "onex_default"
    """Use ONEX default namespace strategy."""

    HIERARCHICAL = "hierarchical"
    """Use hierarchical namespace organization."""

    FLAT = "flat"
    """Use flat namespace organization."""

    CUSTOM = "custom"
    """Use custom namespace strategy."""


__all__ = ["EnumNamespaceStrategy"]
