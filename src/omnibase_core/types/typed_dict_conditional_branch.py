"""
TypedDict for conditional branch entries.

Used in conditional transitions to specify condition/transition pairs.
"""

from typing import TypedDict

from omnibase_core.types.type_serializable_value import SerializedDict


class TypedDictConditionalBranch(TypedDict, total=False):
    """TypedDict for conditional branch entries."""

    condition: str  # The condition expression to evaluate
    transition: SerializedDict  # The transition to apply if condition matches
