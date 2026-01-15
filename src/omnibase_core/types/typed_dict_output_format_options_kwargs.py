"""
TypedDict for output format options constructor arguments.

Strongly-typed representation for ModelOutputFormatOptions constructor kwargs.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

from omnibase_core.enums.enum_color_scheme import EnumColorScheme
from omnibase_core.enums.enum_table_alignment import EnumTableAlignment

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from omnibase_core.models.infrastructure.model_value import ModelValue


class TypedDictOutputFormatOptionsKwargs(TypedDict):
    """
    Strongly-typed representation of ModelOutputFormatOptions constructor arguments.

    This replaces dict[str, Any] with proper type safety for constructor kwargs
    used during configuration conversion. All fields are NotRequired since
    ModelOutputFormatOptions provides defaults for all fields.

    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Common format options
    indent_size: NotRequired[int]
    line_width: NotRequired[int]

    # Content formatting
    include_headers: NotRequired[bool]
    include_timestamps: NotRequired[bool]
    include_line_numbers: NotRequired[bool]

    # Color and styling
    color_enabled: NotRequired[bool]
    color_scheme: NotRequired[EnumColorScheme]
    highlight_errors: NotRequired[bool]

    # Data presentation
    show_metadata: NotRequired[bool]
    compact_mode: NotRequired[bool]
    verbose_details: NotRequired[bool]

    # Table formatting
    table_borders: NotRequired[bool]
    table_headers: NotRequired[bool]
    table_alignment: NotRequired[EnumTableAlignment]

    # JSON/YAML specific options
    pretty_print: NotRequired[bool]
    sort_keys: NotRequired[bool]
    escape_unicode: NotRequired[bool]

    # Pagination options
    page_size: NotRequired[int | None]
    max_items: NotRequired[int | None]

    # File output options
    append_mode: NotRequired[bool]
    create_backup: NotRequired[bool]

    # Custom format options
    custom_options: NotRequired[dict[str, ModelValue]]


# Export for use
__all__ = ["TypedDictOutputFormatOptionsKwargs"]
