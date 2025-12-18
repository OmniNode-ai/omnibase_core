"""
TypedDict for output format options serialization output.

Strongly-typed representation for ModelOutputFormatOptions.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_model_value_serialized import (
        TypedDictModelValueSerialized,
    )


class TypedDictOutputFormatOptionsSerialized(TypedDict):
    """
    Strongly-typed representation of ModelOutputFormatOptions.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Common format options
    indent_size: int
    line_width: int

    # Content formatting
    include_headers: bool
    include_timestamps: bool
    include_line_numbers: bool

    # Color and styling - enum values serialized as strings
    color_enabled: bool
    color_scheme: str
    highlight_errors: bool

    # Data presentation
    show_metadata: bool
    compact_mode: bool
    verbose_details: bool

    # Table formatting
    table_borders: bool
    table_headers: bool
    table_alignment: str

    # JSON/YAML specific options
    pretty_print: bool
    sort_keys: bool
    escape_unicode: bool

    # Pagination options (nullable)
    page_size: int | None
    max_items: int | None

    # File output options
    append_mode: bool
    create_backup: bool

    # Custom format options
    custom_options: dict[str, TypedDictModelValueSerialized]


# Export for use
__all__ = ["TypedDictOutputFormatOptionsSerialized"]
