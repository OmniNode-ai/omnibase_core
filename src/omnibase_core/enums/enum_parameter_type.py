"""
Parameter Type Enum.

Strongly typed parameter type values for ONEX architecture parameter validation.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumParameterType(str, Enum):
    """
    Strongly typed parameter type values for ONEX architecture.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for parameter validation operations.
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    UUID = "uuid"
    ENUM = "enum"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_primitive(cls, param_type: EnumParameterType) -> bool:
        """Check if the parameter type is a primitive type."""
        return param_type in {
            cls.STRING,
            cls.INTEGER,
            cls.FLOAT,
            cls.BOOLEAN,
        }

    @classmethod
    def is_complex(cls, param_type: EnumParameterType) -> bool:
        """Check if the parameter type is a complex type."""
        return param_type in {
            cls.OBJECT,
            cls.ARRAY,
        }

    @classmethod
    def is_numeric(cls, param_type: EnumParameterType) -> bool:
        """Check if the parameter type represents numeric data."""
        return param_type in {
            cls.INTEGER,
            cls.FLOAT,
        }

    @classmethod
    def is_structured(cls, param_type: EnumParameterType) -> bool:
        """Check if the parameter type represents structured data."""
        return param_type in {
            cls.UUID,
            cls.ENUM,
        }

    @classmethod
    def requires_validation(cls, param_type: EnumParameterType) -> bool:
        """Check if the parameter type requires special validation."""
        return param_type in {
            cls.UUID,
            cls.ENUM,
            cls.OBJECT,
            cls.ARRAY,
        }

    @classmethod
    def get_python_type(cls, param_type: EnumParameterType) -> str:
        """Get the corresponding Python type string."""
        type_map = {
            cls.STRING: "str",
            cls.INTEGER: "int",
            cls.FLOAT: "float",
            cls.BOOLEAN: "bool",
            cls.OBJECT: "dict",
            cls.ARRAY: "list",
            cls.UUID: "str",  # UUID as string representation
            cls.ENUM: "str",  # Enum as string value
        }
        return type_map.get(param_type, "Any")

    @classmethod
    def supports_null(cls, param_type: EnumParameterType) -> bool:
        """Check if the parameter type supports null/None values."""
        # All types can be optional, but primitives are typically not nullable by default
        return param_type in {
            cls.OBJECT,
            cls.ARRAY,
            cls.STRING,  # Empty string vs None distinction
        }


# Export for use
__all__ = ["EnumParameterType"]
