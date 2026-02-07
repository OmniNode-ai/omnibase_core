"""Enum for definition format classifications.

Specifies the format in which an interface definition is expressed,
used for ticket-driven interface tracking [OMN-1968].
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDefinitionFormat(StrValueHelper, str, Enum):
    """Format of an interface definition artifact."""

    PYTHON = "python"
    YAML = "yaml"
    JSON = "json"
    PROTO = "proto"
    MARKDOWN = "markdown"


# Alias for cleaner imports
DefinitionFormat = EnumDefinitionFormat

__all__ = [
    "EnumDefinitionFormat",
    "DefinitionFormat",
]
