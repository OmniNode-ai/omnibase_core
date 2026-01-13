"""
Dependency Type Enum.

Dependency type classification for ONEX contract validation.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDependencyType(StrValueHelper, str, Enum):
    """Dependency type classification for ONEX contract validation."""

    PROTOCOL = "protocol"
    SERVICE = "service"
    MODULE = "module"
    EXTERNAL = "external"
