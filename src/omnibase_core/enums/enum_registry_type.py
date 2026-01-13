"""
Registry Type Enum.

Strongly typed enumeration for registry type classifications.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRegistryType(StrValueHelper, str, Enum):
    """
    Registry type classifications for ONEX registries.

    Used for categorizing different types of registries in the ONEX system.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    NODE = "node"
    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SERVICE = "service"
    GLOBAL = "global"
    LOCAL = "local"
    UNKNOWN = "unknown"

    @classmethod
    def is_component_registry(cls, registry_type: "EnumRegistryType") -> bool:
        """Check if the registry type is for components."""
        return registry_type in {
            cls.NODE,
            cls.TOOL,
            cls.VALIDATOR,
            cls.AGENT,
            cls.MODEL,
            cls.PLUGIN,
        }

    @classmethod
    def is_scope_registry(cls, registry_type: "EnumRegistryType") -> bool:
        """Check if the registry type defines scope."""
        return registry_type in {cls.GLOBAL, cls.LOCAL}


# Export for use
__all__ = ["EnumRegistryType"]
