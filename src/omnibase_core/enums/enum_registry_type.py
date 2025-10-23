"""
Registry Type Enum.

Strongly typed enumeration for registry type classifications.
"""

from enum import Enum, unique


@unique
class EnumRegistryType(str, Enum):
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

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

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
