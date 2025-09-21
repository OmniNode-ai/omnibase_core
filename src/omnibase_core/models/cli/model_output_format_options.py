"""
Output format options model for CLI operations.

Structured replacement for dict[str, str] output format options with proper typing.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...enums.enum_color_scheme import EnumColorScheme
from ...enums.enum_table_alignment import EnumTableAlignment


class ModelOutputFormatOptions(BaseModel):
    """
    Structured model for CLI output format options.

    Replaces dict[str, str] with proper type safety for output formatting configuration.
    """

    # Common format options
    indent_size: int = Field(default=4, description="Indentation size for formatted output", ge=0, le=8)
    line_width: int = Field(default=80, description="Maximum line width for output", ge=40, le=200)

    # Content formatting
    include_headers: bool = Field(default=True, description="Include headers in output")
    include_timestamps: bool = Field(default=True, description="Include timestamps in output")
    include_line_numbers: bool = Field(default=False, description="Include line numbers in output")

    # Color and styling
    color_enabled: bool = Field(default=True, description="Enable colored output")
    color_scheme: EnumColorScheme = Field(default=EnumColorScheme.DEFAULT, description="Color scheme name")
    highlight_errors: bool = Field(default=True, description="Highlight errors in output")

    # Data presentation
    show_metadata: bool = Field(default=True, description="Show metadata in output")
    compact_mode: bool = Field(default=False, description="Use compact output format")
    verbose_details: bool = Field(default=False, description="Show verbose details")

    # Table formatting (for tabular outputs)
    table_borders: bool = Field(default=True, description="Show table borders")
    table_headers: bool = Field(default=True, description="Show table headers")
    table_alignment: EnumTableAlignment = Field(default=EnumTableAlignment.LEFT, description="Table column alignment")

    # JSON/YAML specific options
    pretty_print: bool = Field(default=True, description="Pretty print JSON/YAML output")
    sort_keys: bool = Field(default=False, description="Sort keys in JSON/YAML output")
    escape_unicode: bool = Field(default=False, description="Escape unicode characters")

    # Pagination options
    page_size: int | None = Field(None, description="Number of items per page", ge=1, le=1000)
    max_items: int | None = Field(None, description="Maximum number of items to display", ge=1)

    # File output options
    append_mode: bool = Field(default=False, description="Append to existing file instead of overwriting")
    create_backup: bool = Field(default=False, description="Create backup of existing file")

    # Custom format options (extensibility)
    custom_options: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Custom format options for specific use cases"
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

    def set_table_style(self, borders: bool = True, headers: bool = True, alignment: EnumTableAlignment = EnumTableAlignment.LEFT) -> None:
        """Configure table formatting options."""
        self.table_borders = borders
        self.table_headers = headers
        self.table_alignment = alignment

    def set_json_style(self, pretty: bool = True, sort: bool = False, escape: bool = False) -> None:
        """Configure JSON formatting options."""
        self.pretty_print = pretty
        self.sort_keys = sort
        self.escape_unicode = escape

    def set_color_scheme(self, scheme: EnumColorScheme, enabled: bool = True) -> None:
        """Configure color options."""
        self.color_scheme = scheme
        self.color_enabled = enabled

    def add_custom_option(self, key: str, value: str | int | bool) -> None:
        """Add a custom format option."""
        self.custom_options[key] = value

    def get_custom_option(self, key: str, default: str | int | bool | None = None) -> str | int | bool | None:
        """Get a custom format option."""
        return self.custom_options.get(key, default)

    def to_legacy_dict(self) -> dict[str, str]:
        """Convert to legacy dict[str, str] format for backward compatibility."""
        result = {}

        # Convert boolean fields
        result["include_headers"] = str(self.include_headers).lower()
        result["include_timestamps"] = str(self.include_timestamps).lower()
        result["include_line_numbers"] = str(self.include_line_numbers).lower()
        result["color_enabled"] = str(self.color_enabled).lower()
        result["highlight_errors"] = str(self.highlight_errors).lower()
        result["show_metadata"] = str(self.show_metadata).lower()
        result["compact_mode"] = str(self.compact_mode).lower()
        result["verbose_details"] = str(self.verbose_details).lower()
        result["table_borders"] = str(self.table_borders).lower()
        result["table_headers"] = str(self.table_headers).lower()
        result["pretty_print"] = str(self.pretty_print).lower()
        result["sort_keys"] = str(self.sort_keys).lower()
        result["escape_unicode"] = str(self.escape_unicode).lower()
        result["append_mode"] = str(self.append_mode).lower()
        result["create_backup"] = str(self.create_backup).lower()

        # Convert numeric fields
        result["indent_size"] = str(self.indent_size)
        result["line_width"] = str(self.line_width)
        if self.page_size is not None:
            result["page_size"] = str(self.page_size)
        if self.max_items is not None:
            result["max_items"] = str(self.max_items)

        # Convert string fields
        result["color_scheme"] = str(self.color_scheme)
        result["table_alignment"] = str(self.table_alignment)

        # Convert custom options
        for key, value in self.custom_options.items():
            result[f"custom_{key}"] = str(value)

        return result

    @classmethod
    def from_legacy_dict(cls, data: dict[str, str]) -> ModelOutputFormatOptions:
        """Create instance from legacy dict[str, str] format."""
        kwargs = {}
        custom_options = {}

        # Helper to safely convert string to bool
        def str_to_bool(value: str) -> bool:
            return value.lower() in ("true", "1", "yes", "on")

        # Helper to safely convert string to int
        def str_to_int(value: str, default: int) -> int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        # Convert known fields
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
            "color_scheme": ("color_scheme", lambda x: EnumColorScheme(x) if x in EnumColorScheme.__members__.values() else EnumColorScheme.DEFAULT),
            "table_alignment": ("table_alignment", lambda x: EnumTableAlignment(x) if x in EnumTableAlignment.__members__.values() else EnumTableAlignment.LEFT),
        }

        for key, value in data.items():
            if key in field_mappings:
                field_name, converter = field_mappings[key]
                kwargs[field_name] = converter(value)
            elif key.startswith("custom_"):
                custom_key = key[7:]  # Remove "custom_" prefix
                # Try to infer type from value
                if value.lower() in ("true", "false"):
                    custom_options[custom_key] = str_to_bool(value)
                elif value.isdigit():
                    custom_options[custom_key] = int(value)
                else:
                    custom_options[custom_key] = value

        if custom_options:
            kwargs["custom_options"] = custom_options

        return cls(**kwargs)


# Export for use
__all__ = ["ModelOutputFormatOptions"]