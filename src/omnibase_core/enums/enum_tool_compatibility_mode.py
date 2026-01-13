"""Tool compatibility mode enumeration."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolCompatibilityMode(StrValueHelper, str, Enum):
    """
    Tool compatibility mode classification.

    Defines the compatibility level of tools with the system.
    """

    COMPATIBLE = "compatible"
    PARTIAL = "partial"
    INCOMPATIBLE = "incompatible"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


__all__ = ["EnumToolCompatibilityMode"]
