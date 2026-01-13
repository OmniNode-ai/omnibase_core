"""
EnumOverheadType: Enumeration of overhead types.

This enum defines the overhead types for performance profiles.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOverheadType(StrValueHelper, str, Enum):
    """Overhead types for performance profiles."""

    NONE = "none"
    FILE_IO = "file_io"
    NETWORK_AUTH = "network_auth"
    API_CALLS = "api_calls"
