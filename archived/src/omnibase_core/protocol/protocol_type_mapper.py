"""
Protocol for Type Mapper functionality.

Defines the interface for mapping JSON Schema types to Python type strings.
Used for contract generation and model creation.
"""

from typing import Protocol

from omnibase_core.models.core.model_schema import ModelSchema


class ProtocolTypeMapper(Protocol):
    """Protocol for type mapping functionality.

    This protocol defines the interface for converting JSON Schema
    definitions to Python type strings used in generated code.
    """

    def get_type_string_from_schema(self, schema: ModelSchema) -> str:
        """Get type string representation from schema.

        Args:
            schema: ModelSchema object to convert

        Returns:
            Python type string (e.g., "str", "List[str]", "ModelFoo")
        """
        ...

    def get_array_type_string(self, schema: ModelSchema) -> str:
        """Get array type string from schema.

        Args:
            schema: Array schema with items definition

        Returns:
            Array type string (e.g., "List[str]", "List[ModelItem]")
        """
        ...

    def get_object_type_string(self, schema: ModelSchema) -> str:
        """Get object type string from schema.

        Args:
            schema: Object schema to analyze

        Returns:
            Object type string (e.g., "ModelObjectData", "ModelCustom")
        """
        ...

    def generate_enum_name_from_values(self, enum_values: list[str]) -> str:
        """Generate enum class name from enum values.

        Args:
            enum_values: List of enum values

        Returns:
            Generated enum class name (e.g., "EnumStatus")
        """
        ...

    def get_import_for_type(self, type_string: str) -> str | None:
        """Get the import statement needed for a type string.

        Args:
            type_string: Python type string to analyze

        Returns:
            Import statement if needed, None otherwise
        """
        ...

    def is_model_type(self, type_string: str) -> bool:
        """Check if a type string represents a model type.

        Args:
            type_string: Type string to check

        Returns:
            True if this is a model type (starts with Model)
        """
        ...
