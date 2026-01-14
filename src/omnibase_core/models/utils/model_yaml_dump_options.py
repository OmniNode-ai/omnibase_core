"""
Type-safe YAML dump options model.

This module provides the ModelYamlDumpOptions class for configuring YAML
serialization output format. It implements core protocols for serialization
and validation.

Thread Safety:
    ModelYamlDumpOptions is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

Key Features:
    - Configurable indentation and line width
    - Unicode and flow style control
    - Explicit document markers support
    - Key sorting options
    - Protocol compliance (Serializable, Validatable)

Example:
    >>> from omnibase_core.models.utils import ModelYamlDumpOptions
    >>>
    >>> # Default options for human-readable YAML
    >>> options = ModelYamlDumpOptions()
    >>> print(options.indent)  # 2
    >>>
    >>> # Compact YAML for storage
    >>> compact_options = ModelYamlDumpOptions(
    ...     indent=2,
    ...     width=80,
    ...     default_flow_style=True,
    ... )
    >>>
    >>> # YAML with explicit markers for multi-document files
    >>> multi_doc_options = ModelYamlDumpOptions(
    ...     explicit_start=True,
    ...     explicit_end=True,
    ... )

See Also:
    - omnibase_core.utils.yaml_utils: Uses these options for YAML dumping
    - omnibase_core.models.utils.model_yaml_value: YAML value wrapper
"""

from pydantic import BaseModel, ConfigDict

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelYamlDumpOptions(BaseModel):
    """
    Type-safe YAML dump options.

    Configuration model for controlling YAML serialization output format.
    Implements core protocols for serialization and validation.

    Attributes:
        sort_keys: Whether to sort dictionary keys alphabetically.
            Defaults to False (preserves insertion order).
        default_flow_style: Whether to use flow style (inline) for collections.
            When True, outputs compact ``{key: value}`` format.
            Defaults to False (block style).
        allow_unicode: Whether to allow non-ASCII characters in output.
            When True, Unicode characters are preserved.
            Defaults to True.
        explicit_start: Whether to include ``---`` document start marker.
            Useful for multi-document YAML files.
            Defaults to False.
        explicit_end: Whether to include ``...`` document end marker.
            Useful for multi-document YAML files.
            Defaults to False.
        indent: Number of spaces for each indentation level.
            Defaults to 2.
        width: Maximum line width before wrapping.
            Defaults to 120.

    Protocols Implemented:
        - Serializable: Data serialization/deserialization via serialize()
        - Validatable: Instance validation via validate_instance()
    """

    sort_keys: bool = False
    default_flow_style: bool = False
    allow_unicode: bool = True
    explicit_start: bool = False
    explicit_end: bool = False
    indent: int = 2
    width: int = 120

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        frozen=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


__all__ = ["ModelYamlDumpOptions"]
