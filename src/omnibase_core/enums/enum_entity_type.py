"""
Entity Type Enum.

Strongly typed entity type values for data classification.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEntityType(StrValueHelper, str, Enum):
    """
    Strongly typed entity type values for data classification.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for entity type operations.
    """

    # Core entities
    NODE = "node"
    FUNCTION = "function"
    MODEL = "model"
    SCHEMA = "schema"
    CONFIG = "config"
    METADATA = "metadata"

    # Data entities
    FILE = "file"
    DOCUMENT = "document"
    TEMPLATE = "template"
    CONTRACT = "contract"
    EXAMPLE = "example"

    # System entities
    SERVICE = "service"
    COMPONENT = "component"
    MODULE = "module"
    PACKAGE = "package"
    WORKFLOW = "workflow"

    # Infrastructure entities
    REDUCER = "reducer"
    VALIDATOR = "validator"
    GENERATOR = "generator"
    TRANSFORMER = "transformer"

    # Unknown/default
    UNKNOWN = "unknown"

    @classmethod
    def is_code_entity(cls, entity_type: EnumEntityType) -> bool:
        """Check if the entity type represents code-related entities."""
        return entity_type in {
            cls.FUNCTION,
            cls.MODEL,
            cls.SCHEMA,
            cls.MODULE,
            cls.PACKAGE,
        }

    @classmethod
    def is_data_entity(cls, entity_type: EnumEntityType) -> bool:
        """Check if the entity type represents data-related entities."""
        return entity_type in {
            cls.FILE,
            cls.DOCUMENT,
            cls.TEMPLATE,
            cls.CONTRACT,
            cls.EXAMPLE,
            cls.METADATA,
        }

    @classmethod
    def is_system_entity(cls, entity_type: EnumEntityType) -> bool:
        """Check if the entity type represents system-related entities."""
        return entity_type in {
            cls.SERVICE,
            cls.COMPONENT,
            cls.WORKFLOW,
            cls.NODE,
        }

    @classmethod
    def is_infrastructure_entity(cls, entity_type: EnumEntityType) -> bool:
        """Check if the entity type represents infrastructure entities."""
        return entity_type in {
            cls.REDUCER,
            cls.VALIDATOR,
            cls.GENERATOR,
            cls.TRANSFORMER,
        }


# Export for use
__all__ = ["EnumEntityType"]
