"""
Output format options model for CLI operations.

Structured replacement for dict[str, str] output format options with proper typing.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators import allow_dict_any
from omnibase_core.enums.enum_color_scheme import EnumColorScheme
from omnibase_core.enums.enum_table_alignment import EnumTableAlignment
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.utils.model_field_converter import ModelFieldConverterRegistry
from omnibase_core.types.typed_dict_output_format_options_kwargs import (
    TypedDictOutputFormatOptionsKwargs,
)
from omnibase_core.types.typed_dict_output_format_options_serialized import (
    TypedDictOutputFormatOptionsSerialized,
)

# Type alias for CLI option values - simplified to avoid primitive soup
CliOptionValueType = object
T = TypeVar("T", str, int, bool)  # Keep for generic methods


class ModelOutputFormatOptions(BaseModel):
    """
    Structured model for CLI output format options.

    Replaces dict[str, str] with proper type safety for output formatting configuration.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
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
        default=None,
        description="Number of items per page",
        ge=1,
        le=1000,
    )
    max_items: int | None = Field(
        default=None,
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
    custom_options: dict[str, ModelValue] = Field(
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
        self.custom_options[key] = ModelValue.from_any(value)

    def get_custom_option(self, key: str, default: T) -> T:
        """Get a custom format option with type safety."""
        model_value = self.custom_options.get(key)
        if model_value is None:
            return default
        # Extract underlying raw_value from ModelValue wrapper
        return cast(T, model_value.raw_value)

    @classmethod
    @allow_dict_any
    def create_from_string_data(
        cls,
        data: dict[str, str],
    ) -> ModelOutputFormatOptions:
        """Create instance from string-based configuration data."""

        # Create converter registry and register all known fields
        # This replaces the large conditional field_mappings dictionary
        registry = ModelFieldConverterRegistry()

        # Register boolean fields
        boolean_fields = [
            "include_headers",
            "include_timestamps",
            "include_line_numbers",
            "color_enabled",
            "highlight_errors",
            "show_metadata",
            "compact_mode",
            "verbose_details",
            "table_borders",
            "table_headers",
            "pretty_print",
            "sort_keys",
            "escape_unicode",
            "append_mode",
            "create_backup",
        ]
        for field in boolean_fields:
            registry.register_boolean_field(field)

        # Register integer fields with defaults
        registry.register_integer_field("indent_size", default=4, min_value=0)
        registry.register_integer_field("line_width", default=80, min_value=1)

        # Register optional integer fields (0 becomes None)
        registry.register_optional_integer_field("page_size")
        registry.register_optional_integer_field("max_items")

        # Register enum fields
        registry.register_enum_field(
            "color_scheme",
            EnumColorScheme,
            EnumColorScheme.DEFAULT,
        )
        registry.register_enum_field(
            "table_alignment",
            EnumTableAlignment,
            EnumTableAlignment.LEFT,
        )

        # Convert known fields using registry
        kwargs_dict: TypedDictOutputFormatOptionsKwargs = cast(
            TypedDictOutputFormatOptionsKwargs,
            registry.convert_data(data),
        )

        # Handle custom options separately
        custom_options: dict[str, ModelValue] = {}
        for key, value in data.items():
            if key.startswith("custom_") and not registry.has_converter(key):
                custom_key = key[7:]  # Remove "custom_" prefix
                # Infer type from value - this could also be moved to registry pattern
                if value.lower() in ("true", "false"):
                    custom_options[custom_key] = ModelValue.from_boolean(
                        value.lower() == "true",
                    )
                elif value.isdigit():
                    custom_options[custom_key] = ModelValue.from_integer(int(value))
                else:
                    custom_options[custom_key] = ModelValue.from_string(value)

        if custom_options:
            kwargs_dict["custom_options"] = custom_options

        return cls(**kwargs_dict)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    @allow_dict_any
    def serialize(self) -> TypedDictOutputFormatOptionsSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)  # type: ignore[return-value]

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelOutputFormatOptions"]
