"""Enum for definition location classifications.

Specifies where an interface definition is stored -- inline within
the ticket contract or as a file reference to an external source,
used for ticket-driven interface tracking [OMN-1968].
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDefinitionLocation(StrValueHelper, str, Enum):
    """Location where an interface definition is stored."""

    INLINE = "inline"
    FILE_REF = "file_ref"


# Alias for cleaner imports
DefinitionLocation = EnumDefinitionLocation

__all__ = [
    "EnumDefinitionLocation",
    "DefinitionLocation",
]
