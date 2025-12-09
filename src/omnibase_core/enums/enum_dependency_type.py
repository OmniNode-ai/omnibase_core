"""
Dependency Type Enum.

Dependency type classification for ONEX contract validation.
"""

from enum import Enum


class EnumDependencyType(Enum):
    """Dependency type classification for ONEX contract validation."""

    PROTOCOL = "protocol"
    SERVICE = "service"
    MODULE = "module"
    EXTERNAL = "external"
