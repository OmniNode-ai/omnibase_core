"""
URI type enumeration.

Defines ONEX URI types for the unified resource identification system.
"""

from __future__ import annotations

from enum import Enum


class EnumUriType(str, Enum):
    """
    Enumeration of ONEX URI types.

    Used for categorizing different types of resources in the ONEX ecosystem.
    """

    # Core ONEX resource types
    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    NODE = "node"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_executable(cls, uri_type: EnumUriType) -> bool:
        """Check if URI type represents an executable resource."""
        return uri_type in {cls.TOOL, cls.AGENT, cls.PLUGIN}

    @classmethod
    def is_structural(cls, uri_type: EnumUriType) -> bool:
        """Check if URI type represents a structural definition."""
        return uri_type in {cls.SCHEMA, cls.MODEL, cls.NODE}

    @classmethod
    def requires_validation(cls, uri_type: EnumUriType) -> bool:
        """Check if URI type requires validation logic."""
        return uri_type in {cls.VALIDATOR, cls.SCHEMA, cls.MODEL}

    @classmethod
    def get_resource_category(cls, uri_type: EnumUriType) -> str:
        """Get the general category of the resource type."""
        if uri_type in {cls.TOOL, cls.AGENT, cls.PLUGIN}:
            return "executable"
        elif uri_type in {cls.SCHEMA, cls.MODEL}:
            return "definition"
        elif uri_type == cls.VALIDATOR:
            return "validation"
        elif uri_type == cls.NODE:
            return "infrastructure"
        else:
            return "unknown"


# Export the enum
__all__ = ["EnumUriType"]
