"""
Type Mapper Utility for ONEX Contract Generation.

Handles mapping of JSON Schema types to Python type annotations.
Provides consistent type string generation across all ONEX tools.
"""

import re

from omnibase.protocols.types import LogLevel

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.exceptions import OnexError
from omnibase_core.model.core.model_schema import ModelSchema


class UtilityTypeMapper:
    """
    Utility for mapping schema types to Python type strings.

    Handles:
    - Basic type mapping (string -> str, etc.)
    - Array type generation (List[T])
    - Object type mapping (Dict or ModelObjectData)
    - Reference resolution
    - Enum name generation
    """

    # Basic type mappings
    BASIC_TYPE_MAPPING = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
    }

    def __init__(self, reference_resolver=None):
        """
        Initialize the type mapper.

        Args:
            reference_resolver: Optional reference resolver for handling $refs
        """
        self.reference_resolver = reference_resolver

    def get_type_string_from_schema(self, schema: ModelSchema) -> str:
        """
        Get type string representation from schema.

        Args:
            schema: ModelSchema to convert to type string

        Returns:
            Python type string (e.g., "str", "List[int]", "ModelUser")
        """
        # Temporarily disable debug logging

        # Guard against non-ModelSchema input
        if not isinstance(schema, ModelSchema):
            emit_log_event(
                LogLevel.ERROR,
                f"Expected ModelSchema, got {type(schema)}",
                {"type": str(type(schema))},
            )
            emit_log_event(
                LogLevel.DEBUG,
                "EXIT: get_type_string_from_schema - non-ModelSchema",
                {"result": "Any"},
            )
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid input type: expected ModelSchema, got {type(schema)}",
                details={"received_type": str(type(schema))},
            )

        # Handle references
        if schema.ref:
            return self._resolve_ref_name(schema.ref)

        # Handle enums
        if schema.schema_type == "string" and schema.enum_values:
            return self.generate_enum_name_from_values(schema.enum_values)

        # Handle arrays
        if schema.schema_type == "array":
            return self.get_array_type_string(schema)

        # Handle objects
        if schema.schema_type == "object":
            return self.get_object_type_string(schema)

        # Handle string with format specifiers
        if schema.schema_type == "string" and schema.format:
            from omnibase.protocols.types import LogLevel

            from omnibase_core.core.core_structured_logging import (
                emit_log_event_sync as emit_log_event,
            )

            emit_log_event(
                LogLevel.INFO,
                f"Type mapper checking string with format: {schema.format}",
                {"schema_type": schema.schema_type, "format": schema.format},
            )
            if schema.format in ["date-time", "datetime"]:
                return "datetime"
            if schema.format == "date":
                return "date"
            if schema.format == "time":
                return "time"
            if schema.format == "uuid":
                return "UUID"

        # Handle basic types
        return self.BASIC_TYPE_MAPPING.get(schema.schema_type, "Any")

    def get_array_type_string(self, schema: ModelSchema) -> str:
        """
        Get array type string from schema.

        Args:
            schema: ModelSchema with array type

        Returns:
            Array type string (e.g., "List[str]", "List[ModelUser]")
        """
        if schema.items:
            if hasattr(schema.items, "ref") and schema.items.ref:
                ref_name = self._resolve_ref_name(schema.items.ref)
                return f"List[{ref_name}]"
            if hasattr(schema.items, "schema_type"):
                item_type = self.get_type_string_from_schema(schema.items)
                return f"List[{item_type}]"

        return "List[Any]"

    def get_object_type_string(self, schema: ModelSchema) -> str:
        """
        Get object type string from schema.

        Args:
            schema: ModelSchema with object type

        Returns:
            Object type string (e.g., "Dict[str, Any]", "ModelObjectData")
        """
        # Check if this is a dictionary with additionalProperties
        if hasattr(schema, "additional_properties") and schema.additional_properties:
            if (
                hasattr(schema, "additional_properties_type")
                and schema.additional_properties_type
            ):
                value_type = schema.additional_properties_type
                return f"Dict[str, {value_type}]"
            # ONEX COMPLIANCE: Never use Dict[str, Any]
            return "ModelObjectData"
        if schema.properties:
            # Has defined properties, use ModelObjectData for structured objects
            return "ModelObjectData"
        # Generic object - use structured type per ONEX standards
        return "ModelObjectData"

    def generate_enum_name_from_values(self, enum_values: list[str]) -> str:
        """
        Generate enum class name from enum values.

        Args:
            enum_values: List of enum string values

        Returns:
            Generated enum class name (e.g., "EnumStatus")
        """
        if not enum_values:
            return "EnumGeneric"

        # Use first value to generate name
        first_value = enum_values[0]

        # TRACE: Enum name generation
        from omnibase.protocols.types import LogLevel

        from omnibase_core.core.core_structured_logging import (
            emit_log_event_sync as emit_log_event,
        )

        emit_log_event(
            LogLevel.DEBUG,
            "🔍 TRACE: Generating enum name from values",
            {"input_values": enum_values, "first_value": first_value},
        )

        if first_value:
            # Replace hyphens with underscores first
            clean_value = first_value.replace("-", "_")

            emit_log_event(
                LogLevel.DEBUG,
                "🔍 TRACE: Processing enum name generation",
                {"after_hyphen_replacement": clean_value},
            )

            # Handle snake_case values (including those that had hyphens)
            if "_" in clean_value:
                parts = clean_value.split("_")
                generated_name = "Enum" + "".join(word.capitalize() for word in parts)
                emit_log_event(
                    LogLevel.DEBUG,
                    "🔍 TRACE: Snake case enum name generated",
                    {"snake_case_parts": parts, "generated_name": generated_name},
                )
                return generated_name
            # Handle single word values
            generated_name = f"Enum{clean_value.capitalize()}"
            emit_log_event(
                LogLevel.DEBUG,
                "🔍 TRACE: Single word enum name generated",
                {"generated_name": generated_name},
            )
            return generated_name

        return "EnumGeneric"

    def _resolve_ref_name(self, ref: str) -> str:
        """
        Resolve a $ref to a type name.

        Args:
            ref: Reference string (e.g., "#/definitions/ModelUser")

        Returns:
            Resolved type name (e.g., "ModelUser")
        """
        if self.reference_resolver:
            # Use injected resolver if available
            return self.reference_resolver.resolve_ref(ref)

        # Simple fallback resolution
        if ref.startswith("#/definitions/"):
            name = ref.split("/")[-1]
            return name if name.startswith("Model") else f"Model{name}"

        # For external refs, just use the last part
        if "#/" in ref:
            _, type_part = ref.split("#/", 1)
            name = type_part.split("/")[-1]
            return name if name.startswith("Model") else f"Model{name}"

        # No fallbacks - fail if we can't resolve the reference
        raise OnexError(
            code=CoreErrorCode.REFERENCE_ERROR,
            message=f"Unable to resolve reference: {ref}",
            details={"reference": ref},
        )

    def resolve_ref_name(self, ref: str) -> str:
        """
        Public method to resolve reference names.

        This allows the type mapper to be used as a reference resolver
        by other components.

        Args:
            ref: Reference string (e.g., "#/definitions/ModelUser")

        Returns:
            Resolved type name (e.g., "ModelUser")
        """
        return self._resolve_ref_name(ref)

    def get_import_for_type(self, type_string: str) -> str | None:
        """
        Get the import statement needed for a type string.

        Args:
            type_string: Python type string

        Returns:
            Import statement if needed, None otherwise
        """
        if type_string.startswith("List["):
            return "from typing import List"
        if type_string.startswith("Dict["):
            return "from typing import Dict"
        if type_string == "Any":
            return "from typing import Any"
        if type_string.startswith("Optional["):
            return "from typing import Optional"
        if type_string.startswith("Union["):
            return "from typing import Union"
        if type_string == "ModelObjectData":
            return (
                "from omnibase_core.model.core.model_object_data import ModelObjectData"
            )
        if type_string == "datetime":
            return "from datetime import datetime"
        if type_string == "date":
            return "from datetime import date"
        if type_string == "time":
            return "from datetime import time"
        if type_string == "UUID":
            return "from uuid import UUID"

        return None

    def is_model_type(self, type_string: str) -> bool:
        """
        Check if a type string represents a model type.

        Args:
            type_string: Python type string

        Returns:
            True if this is a model type that needs importing
        """
        # Check if it's a model type
        if type_string.startswith("Model"):
            return True

        # Check if it's an enum type
        if type_string.startswith("Enum"):
            return True

        # Check if it's inside a generic
        if "[" in type_string:
            # Extract inner type(s)
            inner = re.search(r"\[(.*)\]", type_string)
            if inner:
                inner_types = inner.group(1).split(",")
                return any(self.is_model_type(t.strip()) for t in inner_types)

        return False
