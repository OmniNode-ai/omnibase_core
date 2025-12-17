"""
TypedDict for ModelValue serialization output.

Strongly-typed representation for ModelValue.model_dump() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictModelValueSerialized(TypedDict):
    """
    Strongly-typed representation of ModelValue serialization output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # ModelValue fields - enum value_type serialized as string
    value_type: str
    raw_value: object


# Export for use
__all__ = ["TypedDictModelValueSerialized"]
