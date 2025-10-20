"""Tool compatibility mode enumeration."""

from enum import Enum


class EnumToolCompatibilityMode(str, Enum):
    """
    Tool compatibility mode classification.

    Defines the compatibility level of tools with the system.
    """

    COMPATIBLE = "compatible"
    PARTIAL = "partial"
    INCOMPATIBLE = "incompatible"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
