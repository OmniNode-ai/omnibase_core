"""
Unit tests for EnumParameterType.

Test coverage for parameter type enumeration and helper methods.
"""

from omnibase_core.enums import EnumParameterType


class TestEnumParameterType:
    """Test cases for EnumParameterType."""

    def test_enum_values(self):
        """Test all enum values are present."""
        expected_values = {
            "auto",
            "string",
            "number",
            "integer",
            "float",
            "boolean",
            "object",
            "array",
            "uuid",
            "enum",
        }
        actual_values = {param_type.value for param_type in EnumParameterType}
        assert actual_values == expected_values

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumParameterType.STRING, str)
        assert EnumParameterType.STRING == "string"

    def test_is_primitive(self):
        """Test primitive type classification."""
        primitive_types = {
            EnumParameterType.STRING,
            EnumParameterType.INTEGER,
            EnumParameterType.FLOAT,
            EnumParameterType.BOOLEAN,
        }

        for param_type in EnumParameterType:
            expected = param_type in primitive_types
            actual = EnumParameterType.is_primitive(param_type)
            assert actual == expected, f"{param_type} primitive classification failed"

    def test_is_complex(self):
        """Test complex type classification."""
        complex_types = {
            EnumParameterType.OBJECT,
            EnumParameterType.ARRAY,
        }

        for param_type in EnumParameterType:
            expected = param_type in complex_types
            actual = EnumParameterType.is_complex(param_type)
            assert actual == expected, f"{param_type} complex classification failed"

    def test_is_numeric(self):
        """Test numeric type classification."""
        numeric_types = {
            EnumParameterType.NUMBER,
            EnumParameterType.INTEGER,
            EnumParameterType.FLOAT,
        }

        for param_type in EnumParameterType:
            expected = param_type in numeric_types
            actual = EnumParameterType.is_numeric(param_type)
            assert actual == expected, f"{param_type} numeric classification failed"

    def test_is_structured(self):
        """Test structured type classification."""
        structured_types = {
            EnumParameterType.UUID,
            EnumParameterType.ENUM,
        }

        for param_type in EnumParameterType:
            expected = param_type in structured_types
            actual = EnumParameterType.is_structured(param_type)
            assert actual == expected, f"{param_type} structured classification failed"

    def test_requires_validation(self):
        """Test validation requirement classification."""
        validation_types = {
            EnumParameterType.UUID,
            EnumParameterType.ENUM,
            EnumParameterType.OBJECT,
            EnumParameterType.ARRAY,
        }

        for param_type in EnumParameterType:
            expected = param_type in validation_types
            actual = EnumParameterType.requires_validation(param_type)
            assert actual == expected, f"{param_type} validation requirement failed"

    def test_get_python_type(self):
        """Test Python type mapping."""
        python_type_map = {
            EnumParameterType.AUTO: "Any",
            EnumParameterType.STRING: "str",
            EnumParameterType.NUMBER: "float",
            EnumParameterType.INTEGER: "int",
            EnumParameterType.FLOAT: "float",
            EnumParameterType.BOOLEAN: "bool",
            EnumParameterType.OBJECT: "dict",
            EnumParameterType.ARRAY: "list",
            EnumParameterType.UUID: "str",
            EnumParameterType.ENUM: "str",
        }

        for param_type, expected_python_type in python_type_map.items():
            actual_python_type = EnumParameterType.get_python_type(param_type)
            assert actual_python_type == expected_python_type

    def test_supports_null(self):
        """Test null support classification."""
        null_support_types = {
            EnumParameterType.OBJECT,
            EnumParameterType.ARRAY,
            EnumParameterType.STRING,
        }

        for param_type in EnumParameterType:
            expected = param_type in null_support_types
            actual = EnumParameterType.supports_null(param_type)
            assert actual == expected, (
                f"{param_type} null support classification failed"
            )

    def test_str_representation(self):
        """Test string representation."""
        for param_type in EnumParameterType:
            assert str(param_type) == param_type.value
