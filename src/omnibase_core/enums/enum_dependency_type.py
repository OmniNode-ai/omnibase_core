"""
Dependency Type Enum.

Dependency type classification for ONEX contract validation.
"""

from enum import Enum, unique


@unique
class EnumDependencyType(Enum):
    """Dependency type classification for ONEX contract validation."""

    PROTOCOL = "protocol"
    SERVICE = "service"
    MODULE = "module"
    EXTERNAL = "external"
