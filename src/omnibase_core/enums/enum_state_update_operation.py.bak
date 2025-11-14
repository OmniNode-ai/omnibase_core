"""
State Update Operation Enum.

Operations that can be performed on state fields.
"""

from enum import Enum


class EnumStateUpdateOperation(str, Enum):
    """Operations that can be performed on state fields."""

    SET = "set"  # Replace field value
    MERGE = "merge"  # Merge with existing value (for dict[str, Any]s)
    APPEND = "append"  # Append to list[Any]
    INCREMENT = "increment"  # Increment numeric value
    DECREMENT = "decrement"  # Decrement numeric value
    DELETE = "delete"  # Remove field from state
