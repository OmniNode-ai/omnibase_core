"""
Unit tests for EnumNumericType.

Tests all aspects of the numeric type enum including:
- Enum value validation
- String representation
- JSON serialization compatibility
- Pydantic integration
- Enum iteration and membership
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_numeric_type import EnumNumericType


@pytest.mark.unit
class TestEnumNumericType:
    """Test cases for EnumNumericType."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "INTEGER": "integer",
            "FLOAT": "float",
            "NUMERIC": "numeric",
        }

        for name, value in expected_values.items():
            numeric_type = getattr(EnumNumericType, name)
            assert numeric_type.value == value

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumNumericType.INTEGER, str)
        assert EnumNumericType.INTEGER == "integer"
        assert isinstance(EnumNumericType.FLOAT, str)
        assert EnumNumericType.FLOAT == "float"

    def test_string_representation(self):
        """Test string representation of enum values."""
        # Enum inherits from str, so value is accessible as string
        assert EnumNumericType.INTEGER.value == "integer"
        assert EnumNumericType.FLOAT.value == "float"
        assert EnumNumericType.NUMERIC.value == "numeric"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumNumericType.INTEGER == EnumNumericType.INTEGER
        assert EnumNumericType.FLOAT != EnumNumericType.INTEGER
        assert EnumNumericType.NUMERIC == EnumNumericType.NUMERIC

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_numeric_types = [
            EnumNumericType.INTEGER,
            EnumNumericType.FLOAT,
            EnumNumericType.NUMERIC,
        ]

        for numeric_type in all_numeric_types:
            assert numeric_type in EnumNumericType

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        numeric_types = list(EnumNumericType)
        assert len(numeric_types) == 3

        numeric_values = [num.value for num in numeric_types]
        expected_values = ["integer", "float", "numeric"]

        assert set(numeric_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        numeric_type = EnumNumericType.INTEGER
        json_str = json.dumps(numeric_type, default=str)
        assert json_str == '"integer"'

        # Test in dictionary
        data = {"numeric_type": EnumNumericType.FLOAT}
        json_str = json.dumps(data, default=str)
        assert '"numeric_type": "float"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class NumericConfig(BaseModel):
            numeric_type: EnumNumericType

        # Test valid enum assignment
        config = NumericConfig(numeric_type=EnumNumericType.INTEGER)
        assert config.numeric_type == EnumNumericType.INTEGER

        # Test string assignment (should work due to str inheritance)
        config = NumericConfig(numeric_type="float")
        assert config.numeric_type == EnumNumericType.FLOAT

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            NumericConfig(numeric_type="invalid_type")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class NumericConfig(BaseModel):
            numeric_type: EnumNumericType

        config = NumericConfig(numeric_type=EnumNumericType.NUMERIC)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"numeric_type": "numeric"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"numeric_type":"numeric"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity (should be case-sensitive)
        assert EnumNumericType.INTEGER.value == "integer"
        assert EnumNumericType.INTEGER.value != "INTEGER"
        assert EnumNumericType.INTEGER.value != "Integer"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumNumericType("invalid_value")

    def test_numeric_type_semantics(self):
        """Test semantic meaning of numeric types."""
        # INTEGER accepts only int values
        assert EnumNumericType.INTEGER.value == "integer"

        # FLOAT accepts only float values
        assert EnumNumericType.FLOAT.value == "float"

        # NUMERIC accepts both int and float
        assert EnumNumericType.NUMERIC.value == "numeric"

    def test_all_values_unique(self):
        """Test that all enum values are unique."""
        values = [t.value for t in EnumNumericType]
        assert len(values) == len(set(values))

    def test_enum_names_uppercase(self):
        """Test that all enum names follow UPPERCASE convention."""
        for numeric_type in EnumNumericType:
            assert numeric_type.name.isupper()

    def test_enum_values_lowercase(self):
        """Test that all enum values are lowercase."""
        for numeric_type in EnumNumericType:
            assert numeric_type.value.islower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
