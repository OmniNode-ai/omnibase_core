"""
EnumOverheadType: Enumeration of overhead types.

This enum defines the overhead types for performance profiles.
"""

from enum import Enum


class EnumOverheadType(Enum):
    """Overhead types for performance profiles."""

    NONE = "none"
    FILE_IO = "file_io"
    NETWORK_AUTH = "network_auth"
    API_CALLS = "api_calls"
