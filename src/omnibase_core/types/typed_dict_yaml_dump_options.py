"""
TypedDict for YAML dump options.

Provides type-safe options for yaml.dump() function calls.
"""

from typing import TypedDict


class TypedDictYamlDumpOptions(TypedDict, total=False):
    """Type-safe options for yaml.dump().

    All fields are optional with sensible defaults applied in _dump_yaml_content.
    These map directly to the corresponding yaml.dump() parameters.
    """

    sort_keys: bool
    default_flow_style: bool
    allow_unicode: bool
    explicit_start: bool
    explicit_end: bool
    indent: int
    width: int


__all__ = ["TypedDictYamlDumpOptions"]
