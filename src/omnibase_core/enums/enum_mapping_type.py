# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Mapping Type Enum.

Canonical enum for mapping types used in event field transformations.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumMappingType(UtilStrValueHelper, str, Enum):
    """Canonical mapping types for event field transformations."""

    DIRECT = "direct"
    TRANSFORM = "transform"
    CONDITIONAL = "conditional"
    COMPOSITE = "composite"


__all__ = ["EnumMappingType"]
