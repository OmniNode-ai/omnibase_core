#!/usr/bin/env python3
"""
Transition Type Enum.

Enumeration for state transition types in contract-driven state management.
"""

from enum import Enum


class EnumTransitionType(str, Enum):
    """Types of state transitions."""

    SIMPLE = "simple"  # Direct field updates
    TOOL_BASED = "tool_based"  # Delegate to tool for computation
    CONDITIONAL = "conditional"  # Apply based on conditions
    COMPOSITE = "composite"  # Combine multiple transitions
