"""
TypedDict for transition configuration.

Used to define state field updates and transition type identifiers.
"""

from typing import TypedDict

from omnibase_core.types.type_serializable_value import SerializedDict

__all__ = ["TypedDictTransitionConfig"]


class TypedDictTransitionConfig(TypedDict, total=False):
    """TypedDict for transition configuration."""

    updates: SerializedDict  # State field updates
    type: str  # Transition type identifier
