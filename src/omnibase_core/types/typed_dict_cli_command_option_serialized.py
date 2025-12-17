"""
TypedDict for CLI command option serialization output.

Strongly-typed representation for ModelCliCommandOption.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictCliCommandOptionSerialized(TypedDict):
    """
    Strongly-typed representation of ModelCliCommandOption.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Option identification - UUID serialized as string
    option_id: str
    option_display_name: str | None
    value: object
    value_type: str  # enum serialized as string

    # Option metadata
    is_flag: bool
    is_required: bool
    is_multiple: bool

    # Validation
    description: str
    valid_choices: list[str]


# Export for use
__all__ = ["TypedDictCliCommandOptionSerialized"]
