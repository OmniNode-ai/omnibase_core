"""TypedDictYamlDumpKwargs.

TypedDict for YAML dump keyword arguments.

This provides type-safe kwargs for yaml.dump() calls without using dict[str, Any].
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictYamlDumpKwargs(TypedDict, total=False):
    """
    Type-safe keyword arguments for yaml.dump().

    All fields are optional (total=False) to allow partial kwargs.

    Attributes:
        sort_keys: Whether to sort dictionary keys
        default_flow_style: Whether to use flow style for collections
        allow_unicode: Whether to allow non-ASCII characters
        explicit_start: Whether to include document start marker
        explicit_end: Whether to include document end marker
        indent: Number of spaces for indentation
        width: Maximum line width
        default_style: Default style for scalars
        canonical: Whether to use canonical YAML format
        line_break: Line break character
        encoding: Output encoding
        tags: Custom tags mapping
        Dumper: Custom Dumper class
    """

    sort_keys: bool
    default_flow_style: bool | None
    allow_unicode: bool
    explicit_start: bool
    explicit_end: bool
    indent: int | None
    width: int | None
    default_style: str | None
    canonical: bool | None
    line_break: str | None
    encoding: str | None


__all__ = ["TypedDictYamlDumpKwargs"]
