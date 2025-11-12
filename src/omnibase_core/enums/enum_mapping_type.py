"""
Mapping Type Enum.

Canonical enum for mapping types used in event field transformations.
"""

from enum import Enum


class EnumMappingType(str, Enum):
    """Canonical mapping types for event field transformations."""

    DIRECT = "direct"
    TRANSFORM = "transform"
    CONDITIONAL = "conditional"
    COMPOSITE = "composite"
