"""
TypedDict for CLI execution context serialization output.

Strongly-typed representation for ModelCliExecutionContext.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictCliExecutionContextSerialized(TypedDict):
    """
    Strongly-typed representation of ModelCliExecutionContext.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Context identification
    key: str
    value: object

    # Context metadata - enum values serialized as strings
    context_type: str
    is_persistent: bool
    priority: int

    # Tracking - datetime serialized as ISO string
    created_at: str
    updated_at: str

    # Validation
    description: str
    source: str


# Export for use
__all__ = ["TypedDictCliExecutionContextSerialized"]
