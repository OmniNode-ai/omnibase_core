#!/usr/bin/env python3
"""
Transition Type Enum.

Enumeration for state transition types in contract-driven state management.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTransitionType(StrValueHelper, str, Enum):
    """Types of state transitions."""

    SIMPLE = "simple"  # Direct field updates
    TOOL_BASED = "tool_based"  # Delegate to tool for computation
    CONDITIONAL = "conditional"  # Apply based on conditions
    COMPOSITE = "composite"  # Combine multiple transitions


__all__ = ["EnumTransitionType"]
