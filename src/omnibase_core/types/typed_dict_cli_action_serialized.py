"""
TypedDict for CLI action serialization output.

Strongly-typed representation for ModelCliAction.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictCliActionSerialized(TypedDict):
    """
    Strongly-typed representation of ModelCliAction.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Uses aliases as serialize() calls model_dump(by_alias=True).
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # UUID fields serialized as strings
    action_id: str
    # Note: action_name_id is excluded from serialization (exclude=True in model)
    action_name: str  # Alias for action_display_name
    node_id: str
    node_name: str  # Alias for node_display_name
    description: str
    deprecated: bool
    category: str | None  # EnumActionCategory serialized as string or None


# Export for use
__all__ = ["TypedDictCliActionSerialized"]
