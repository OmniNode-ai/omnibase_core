"""Enum for interface surface classifications.

Categorizes the visibility surface of an interface boundary,
used for ticket-driven interface tracking [OMN-1968].
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumInterfaceSurface(StrValueHelper, str, Enum):
    """Visibility surface of an interface boundary."""

    PUBLIC_API = "public_api"
    INTERNAL_API = "internal_api"
    EVENT_SCHEMA = "event_schema"
    SPI = "spi"
    CLI = "cli"
    CONTRACT = "contract"


# Alias for cleaner imports
InterfaceSurface = EnumInterfaceSurface

__all__ = [
    "EnumInterfaceSurface",
    "InterfaceSurface",
]
