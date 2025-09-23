"""
Output format options model for CLI operations.

Structured replacement for dict[str, str] output format options with proper typing.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from pydantic import BaseModel, Field

from ..infrastructure.model_cli_value import ModelCliValue

# Decorator to allow dict[str, Any] usage with justification
F = TypeVar("F", bound=Callable[..., Any])

# Generic type for custom option values
T = TypeVar("T", str, int, bool)


def allow_dict_any(func: F) -> F:
    """
    Decorator to allow dict[str, Any] usage in specific functions.

    This should only be used when:
    1. Converting untyped external data to typed internal models
    2. Complex conversion functions where intermediate dicts need flexibility
    3. Legacy integration where gradual typing is being applied

    Justification: This function converts string-based configuration data
    to properly typed model fields, requiring temporary dict[str, Any] storage.
    """
    return func


from ...enums.enum_color_scheme import EnumColorScheme
from ...enums.enum_table_alignment import EnumTableAlignment
from ..common.model_schema_value import ModelSchemaValue


class ModelOutputFormatOptions(BaseModel):
    """
    Structured model for CLI output format options.

    Replaces dict[str, str] with proper type safety for output formatting configuration.
    """

    # Common format options
    indent_size: int = Field(
        default=4,
        description="Indentation size for formatted output",
        ge=0,
        le=8,
    )
    line_width: int = Field(
        default=80,
        description="Maximum line width for output",
        ge=40,
        le=200,
    )

    # Content formatting
    include_headers: bool = Field(default=True, description="Include headers in output")
    include_timestamps: bool = Field(
        default=True,
        description="Include timestamps in output",
    )
    include_line_numbers: bool = Field(
        default=False,
        description="Include line numbers in output",
    )

    # Color and styling
    color_enabled: bool = Field(default=True, description="Enable colored output")
    color_scheme: EnumColorScheme = Field(
        default=EnumColorScheme.DEFAULT,
        description="Color scheme name",
    )
    highlight_errors: bool = Field(
        default=True,
        description="Highlight errors in output",
    )

    # Data presentation
    show_metadata: bool = Field(default=True, description="Show metadata in output")
    compact_mode: bool = Field(default=False, description="Use compact output format")
    verbose_details: bool = Field(default=False, description="Show verbose details")

    # Table formatting (for tabular outputs)
    table_borders: bool = Field(default=True, description="Show table borders")
    table_headers: bool = Field(default=True, description="Show table headers")
    table_alignment: EnumTableAlignment = Field(
        default=EnumTableAlignment.LEFT,
        description="Table column alignment",
    )

    # JSON/YAML specific options
    pretty_print: bool = Field(
        default=True,
        description="Pretty print JSON/YAML output",
    )
    sort_keys: bool = Field(default=False, description="Sort keys in JSON/YAML output")
    escape_unicode: bool = Field(default=False, description="Escape unicode characters")

    # Pagination options
    page_size: int | None = Field(
        None,
        description="Number of items per page",
        ge=1,
        le=1000,
    )
    max_items: int | None = Field(
        None,
        description="Maximum number of items to display",
        ge=1,
    )

    # File output options
    append_mode: bool = Field(
        default=False,
        description="Append to existing file instead of overwriting",
    )
    create_backup: bool = Field(
        default=False,
        description="Create backup of existing file",
    )

    # Custom format options (extensibility)
    custom_options: dict[str, ModelCliValue] = Field(
        default_factory=dict,
        description="Custom format options for specific use cases",
    )

    def set_compact_mode(self) -> None:
        """Configure options for compact output."""
        self.compact_mode = True
        self.include_headers = False
        self.include_timestamps = False
        self.show_metadata = False
        self.table_borders = False
        self.verbose_details = False

    def set_verbose_mode(self) -> None:
        """Configure options for verbose output."""
        self.verbose_details = True
        self.show_metadata = True
        self.include_timestamps = True
        self.include_line_numbers = True
        self.compact_mode = False

    def set_minimal_mode(self) -> None:
        """Configure options for minimal output."""
        self.include_headers = False
        self.include_timestamps = False
        self.include_line_numbers = False
        self.show_metadata = False
        self.table_borders = False
        self.color_enabled = False
        self.compact_mode = True

    def set_table_style(
        self,
        borders: bool = True,
        headers: bool = True,
        alignment: EnumTableAlignment = EnumTableAlignment.LEFT,
    ) -> None:
        """Configure table formatting options."""
        self.table_borders = borders
        self.table_headers = headers
        self.table_alignment = alignment

    def set_json_style(
        self,
        pretty: bool = True,
        sort: bool = False,
        escape: bool = False,
    ) -> None:
        """Configure JSON formatting options."""
        self.pretty_print = pretty
        self.sort_keys = sort
        self.escape_unicode = escape

    def set_color_scheme(self, scheme: EnumColorScheme, enabled: bool = True) -> None:
        """Configure color options."""
        self.color_scheme = scheme
        self.color_enabled = enabled

    def add_custom_option(self, key: str, value: T) -> None:
        """Add a custom format option."""
        self.custom_options[key] = ModelCliValue.from_any(value)

    def get_custom_option(self, key: str, default: T) -> T:
        """Get a custom format option with type safety."""
        return cast(T, self.custom_options.get(key, default))

    @classmethod
    @allow_dict_any
    def create_from_string_data(
        cls,
        data: dict[str, str],
    ) -> ModelOutputFormatOptions:
        """Create instance from string-based configuration data."""

        # Helper to safely convert string to bool
        def str_to_bool(value: str) -> bool:
            return value.lower() in ("true", "1", "yes", "on")

        # Helper to safely convert string to int
        def str_to_int(value: str, default: int) -> int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        # Transform string data structure to proper typed fields
        kwargs: dict[str, Any] = {}
        custom_options: dict[str, ModelCliValue] = {}

        # Convert known fields with proper type handling
        field_mappings = {
            "include_headers": ("include_headers", str_to_bool),
            "include_timestamps": ("include_timestamps", str_to_bool),
            "include_line_numbers": ("include_line_numbers", str_to_bool),
            "color_enabled": ("color_enabled", str_to_bool),
            "highlight_errors": ("highlight_errors", str_to_bool),
            "show_metadata": ("show_metadata", str_to_bool),
            "compact_mode": ("compact_mode", str_to_bool),
            "verbose_details": ("verbose_details", str_to_bool),
            "table_borders": ("table_borders", str_to_bool),
            "table_headers": ("table_headers", str_to_bool),
            "pretty_print": ("pretty_print", str_to_bool),
            "sort_keys": ("sort_keys", str_to_bool),
            "escape_unicode": ("escape_unicode", str_to_bool),
            "append_mode": ("append_mode", str_to_bool),
            "create_backup": ("create_backup", str_to_bool),
            "indent_size": ("indent_size", lambda x: str_to_int(x, 4)),
            "line_width": ("line_width", lambda x: str_to_int(x, 80)),
            "page_size": ("page_size", lambda x: str_to_int(x, 0) if x else None),
            "max_items": ("max_items", lambda x: str_to_int(x, 0) if x else None),
            "color_scheme": (
                "color_scheme",
                lambda x: (
                    EnumColorScheme(x)
                    if x in EnumColorScheme.__members__.values()
                    else EnumColorScheme.DEFAULT
                ),
            ),
            "table_alignment": (
                "table_alignment",
                lambda x: (
                    EnumTableAlignment(x)
                    if x in EnumTableAlignment.__members__.values()
                    else EnumTableAlignment.LEFT
                ),
            ),
        }

        for key, value in data.items():
            if key in field_mappings:
                field_name, converter = field_mappings[key]
                kwargs[field_name] = converter(value)
            elif key.startswith("custom_"):
                custom_key = key[7:]  # Remove "custom_" prefix
                # Try to infer type from value
                if value.lower() in ("true", "false"):
                    custom_options[custom_key] = ModelCliValue.from_boolean(
                        str_to_bool(value)
                    )
                elif value.isdigit():
                    custom_options[custom_key] = ModelCliValue.from_integer(int(value))
                else:
                    custom_options[custom_key] = ModelCliValue.from_string(value)

        if custom_options:
            kwargs["custom_options"] = custom_options

        return cls(**kwargs)


# Export for use
__all__ = ["ModelOutputFormatOptions"]
