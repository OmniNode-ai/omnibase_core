"""
TypedDict for CLI execution metadata serialization output.

Strongly-typed representation for ModelCliExecutionMetadata.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_cli_execution_context_serialized import (
        TypedDictCliExecutionContextSerialized,
    )


class TypedDictCliExecutionMetadataSerialized(TypedDict):
    """
    Strongly-typed representation of ModelCliExecutionMetadata.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Custom metadata for extensibility
    custom_context: dict[str, TypedDictCliExecutionContextSerialized]
    execution_tags: list[str]


# Export for use
__all__ = ["TypedDictCliExecutionMetadataSerialized"]
