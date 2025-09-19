"""
Node capability level enumeration.

Provides strongly typed capability levels for ONEX nodes.
"""

from enum import Enum


class EnumNodeCapabilityLevel(str, Enum):
    """Node capability levels."""

    BASIC = "basic"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"
    EXPERIMENTAL = "experimental"
