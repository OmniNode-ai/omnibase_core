"""
Item type enumeration for collection items.

Provides standardized item type values for item classification and filtering.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumItemType(StrValueHelper, str, Enum):
    """
    Item type enumeration for collection item classification.

    Provides standardized item type values for consistent classification
    and filtering of collection items across the system.
    """

    # Basic item types
    COLLECTION_ITEM = "collection_item"
    DATA_ITEM = "data_item"
    CONFIG_ITEM = "config_item"
    METADATA_ITEM = "metadata_item"

    # Content types
    DOCUMENT = "document"
    TEMPLATE = "template"
    EXAMPLE = "example"
    REFERENCE = "reference"

    # Code and development items
    CODE = "code"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    TEST = "test"

    # Configuration and settings
    SETTING = "setting"
    PARAMETER = "parameter"
    PROPERTY = "property"
    VARIABLE = "variable"

    # Asset types
    IMAGE = "image"
    FILE = "file"
    RESOURCE = "resource"
    ARTIFACT = "artifact"

    # System types
    SYSTEM = "system"
    COMPONENT = "component"
    SERVICE = "service"
    WORKFLOW = "workflow"

    # Default and unknown
    UNKNOWN = "unknown"
    OTHER = "other"

    def is_content_type(self) -> bool:
        """Check if this represents a content-related item type."""
        return self in {
            EnumItemType.DOCUMENT,
            EnumItemType.TEMPLATE,
            EnumItemType.EXAMPLE,
            EnumItemType.REFERENCE,
        }

    def is_code_type(self) -> bool:
        """Check if this represents a code-related item type."""
        return self in {
            EnumItemType.CODE,
            EnumItemType.FUNCTION,
            EnumItemType.CLASS,
            EnumItemType.MODULE,
            EnumItemType.TEST,
        }

    def is_config_type(self) -> bool:
        """Check if this represents a configuration-related item type."""
        return self in {
            EnumItemType.CONFIG_ITEM,
            EnumItemType.SETTING,
            EnumItemType.PARAMETER,
            EnumItemType.PROPERTY,
            EnumItemType.VARIABLE,
        }

    def is_system_type(self) -> bool:
        """Check if this represents a system-related item type."""
        return self in {
            EnumItemType.SYSTEM,
            EnumItemType.COMPONENT,
            EnumItemType.SERVICE,
            EnumItemType.WORKFLOW,
        }


# Export for use
__all__ = ["EnumItemType"]
