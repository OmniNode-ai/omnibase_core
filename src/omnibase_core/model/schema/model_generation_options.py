"""
Generation Options Model

Structured model for schema generation options that replaces Dict[str, Any] usage.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EnumGenerationMode(str, Enum):
    """Generation modes for schema operations."""

    strict = "strict"
    permissive = "permissive"
    backwards_compatible = "backwards_compatible"
    forward_compatible = "forward_compatible"


class EnumOutputFormat(str, Enum):
    """Output formats for generated content."""

    pydantic = "pydantic"
    dataclasses = "dataclasses"
    json_schema = "json_schema"
    typescript = "typescript"
    openapi = "openapi"


class ModelGenerationOptions(BaseModel):
    """
    Structured generation options model.

    Replaces Dict[str, Any] usage with proper typing for
    schema generation configuration.
    """

    # Core generation options
    mode: EnumGenerationMode = Field(
        default=EnumGenerationMode.strict,
        description="Generation mode",
    )
    output_format: EnumOutputFormat = Field(
        default=EnumOutputFormat.pydantic,
        description="Output format",
    )
    include_docs: bool = Field(
        default=True,
        description="Include documentation in generated code",
    )
    include_examples: bool = Field(
        default=False,
        description="Include examples in generated code",
    )

    # Validation options
    strict_typing: bool = Field(
        default=True,
        description="Use strict typing (no Any types)",
    )
    validate_defaults: bool = Field(
        default=True,
        description="Validate default values against schema",
    )
    allow_extra_fields: bool = Field(
        default=False,
        description="Allow extra fields not in schema",
    )

    # Code generation options
    class_prefix: str | None = Field(
        default="Model",
        description="Prefix for generated class names",
    )
    module_name: str | None = Field(
        None,
        description="Module name for generated code",
    )
    base_class: str | None = Field(
        default="BaseModel",
        description="Base class for generated models",
    )

    # File options
    one_file_per_model: bool = Field(
        default=True,
        description="Generate one file per model",
    )
    preserve_field_order: bool = Field(
        default=True,
        description="Preserve field order from schema",
    )
    generate_init_files: bool = Field(
        default=True,
        description="Generate __init__.py files",
    )

    # Advanced options
    custom_validators: list[str] = Field(
        default_factory=list,
        description="Custom validator functions to include",
    )
    excluded_fields: list[str] = Field(
        default_factory=list,
        description="Fields to exclude from generation",
    )
    field_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Custom field name mappings",
    )

    @classmethod
    def create_strict(cls) -> "ModelGenerationOptions":
        """Factory method for strict generation options."""
        return cls(
            mode=EnumGenerationMode.strict,
            strict_typing=True,
            validate_defaults=True,
            allow_extra_fields=False,
        )

    @classmethod
    def create_permissive(cls) -> "ModelGenerationOptions":
        """Factory method for permissive generation options."""
        return cls(
            mode=EnumGenerationMode.permissive,
            strict_typing=False,
            validate_defaults=False,
            allow_extra_fields=True,
        )
