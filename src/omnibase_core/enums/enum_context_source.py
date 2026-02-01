"""
Context source enumeration.

Defines sources of context data in CLI operations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContextSource(StrValueHelper, str, Enum):
    """
    Enumeration of context data sources.

    Used to identify where context information originates.
    """

    # User sources
    USER = "user"
    USER_INPUT = "user_input"
    USER_CONFIG = "user_config"
    MANUAL = "manual"

    # System sources
    SYSTEM = "system"
    AUTOMATIC = "automatic"
    AUTO = "auto"
    GENERATED = "generated"

    # Application sources
    APPLICATION = "application"
    RUNTIME = "runtime"
    ENVIRONMENT = "environment"
    CONFIG = "config"
    SETTINGS = "settings"

    # External sources
    EXTERNAL = "external"
    API = "api"
    DATABASE = "database"
    FILE = "file"
    NETWORK = "network"

    # Special sources
    INHERITED = "inherited"
    DEFAULT = "default"
    FALLBACK = "fallback"
    UNKNOWN = "unknown"

    @classmethod
    def is_user_source(cls, source: EnumContextSource) -> bool:
        """Check if context source is user-initiated."""
        return source in {
            cls.USER,
            cls.USER_INPUT,
            cls.USER_CONFIG,
            cls.MANUAL,
        }

    @classmethod
    def is_system_source(cls, source: EnumContextSource) -> bool:
        """Check if context source is system-generated."""
        return source in {
            cls.SYSTEM,
            cls.AUTOMATIC,
            cls.AUTO,
            cls.GENERATED,
            cls.APPLICATION,
            cls.RUNTIME,
        }

    @classmethod
    def is_external_source(cls, source: EnumContextSource) -> bool:
        """Check if context source is external."""
        return source in {
            cls.EXTERNAL,
            cls.API,
            cls.DATABASE,
            cls.FILE,
            cls.NETWORK,
        }

    @classmethod
    def get_trust_level(cls, source: EnumContextSource) -> int:
        """Get trust level for source (1-10, higher = more trusted)."""
        mapping = {
            cls.USER: 9,
            cls.USER_INPUT: 8,
            cls.USER_CONFIG: 9,
            cls.MANUAL: 8,
            cls.SYSTEM: 10,
            cls.APPLICATION: 9,
            cls.RUNTIME: 8,
            cls.ENVIRONMENT: 7,
            cls.CONFIG: 8,
            cls.SETTINGS: 8,
            cls.AUTOMATIC: 7,
            cls.AUTO: 7,
            cls.GENERATED: 6,
            cls.EXTERNAL: 5,
            cls.API: 6,
            cls.DATABASE: 7,
            cls.FILE: 6,
            cls.NETWORK: 4,
            cls.INHERITED: 5,
            cls.DEFAULT: 8,
            cls.FALLBACK: 3,
            cls.UNKNOWN: 1,
        }
        return mapping.get(source, 1)


# Export the enum
__all__ = ["EnumContextSource"]
