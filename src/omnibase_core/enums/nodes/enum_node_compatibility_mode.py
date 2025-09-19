"""
Node compatibility mode enumeration.

Provides strongly typed compatibility modes for ONEX nodes.
"""

from enum import Enum


class EnumNodeCompatibilityMode(str, Enum):
    """Node compatibility modes."""

    STRICT = "strict"
    COMPATIBLE = "compatible"
    LEGACY = "legacy"
    EXPERIMENTAL = "experimental"
