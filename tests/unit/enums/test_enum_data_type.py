"""
Unit tests for EnumDataType.

Tests all aspects of the data type enum including:
- Enum value validation
- Data type classification methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- Schema support validation
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from src.omnibase_core.enums.enum_data_type import EnumDataType


class TestEnumDataType:
    """Test cases for EnumDataType."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "JSON": "json",
            "XML": "xml",
            "TEXT": "text",
            "BINARY": "binary",
            "CSV": "csv",
            "YAML": "yaml",
        }

        for name, value in expected_values.items():
            data_type = getattr(EnumDataType, name)
            assert data_type.value == value
            assert str(data_type) == value  # Has __str__ method

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumDataType.JSON) == "json"
        assert str(EnumDataType.XML) == "xml"
        assert str(EnumDataType.TEXT) == "text"
        assert str(EnumDataType.BINARY) == "binary"

    def test_is_structured(self):
        """Test the is_structured class method."""
        # Structured data types
        structured_types = [
            EnumDataType.JSON,
            EnumDataType.XML,
            EnumDataType.CSV,
            EnumDataType.YAML,
        ]

        for data_type in structured_types:
            assert EnumDataType.is_structured(data_type) is True

        # Non-structured data types
        non_structured_types = [
            EnumDataType.TEXT,
            EnumDataType.BINARY,
        ]

        for data_type in non_structured_types:
            assert EnumDataType.is_structured(data_type) is False

    def test_is_text_based(self):
        """Test the is_text_based class method."""
        # Text-based data types
        text_based_types = [
            EnumDataType.JSON,
            EnumDataType.XML,
            EnumDataType.TEXT,
            EnumDataType.CSV,
            EnumDataType.YAML,
        ]

        for data_type in text_based_types:
            assert EnumDataType.is_text_based(data_type) is True

        # Non-text-based data types
        non_text_based_types = [
            EnumDataType.BINARY,
        ]

        for data_type in non_text_based_types:
            assert EnumDataType.is_text_based(data_type) is False

    def test_supports_schema(self):
        """Test the supports_schema class method."""
        # Data types that support schema validation
        schema_types = [
            EnumDataType.JSON,
            EnumDataType.XML,
            EnumDataType.YAML,
        ]

        for data_type in schema_types:
            assert EnumDataType.supports_schema(data_type) is True

        # Data types that don't support schema validation
        non_schema_types = [
            EnumDataType.TEXT,
            EnumDataType.BINARY,
            EnumDataType.CSV,  # CSV generally doesn't have schema validation
        ]

        for data_type in non_schema_types:
            assert EnumDataType.supports_schema(data_type) is False

    def test_data_type_categorization_logic(self):
        """Test comprehensive data type categorization logic."""
        # All schema-supporting types should be structured
        for data_type in EnumDataType:
            if EnumDataType.supports_schema(data_type):
                assert EnumDataType.is_structured(data_type) is True

        # All structured types should be text-based (in this enum)
        for data_type in EnumDataType:
            if EnumDataType.is_structured(data_type):
                assert EnumDataType.is_text_based(data_type) is True

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumDataType.JSON == EnumDataType.JSON
        assert EnumDataType.XML != EnumDataType.JSON
        assert EnumDataType.YAML == EnumDataType.YAML

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_data_types = [
            EnumDataType.JSON,
            EnumDataType.XML,
            EnumDataType.TEXT,
            EnumDataType.BINARY,
            EnumDataType.CSV,
            EnumDataType.YAML,
        ]

        for data_type in all_data_types:
            assert data_type in EnumDataType

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        data_types = list(EnumDataType)
        assert len(data_types) == 6

        data_type_values = [dt.value for dt in data_types]
        expected_values = ["json", "xml", "text", "binary", "csv", "yaml"]

        assert set(data_type_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        data_type = EnumDataType.JSON
        json_str = json.dumps(data_type, default=str)
        assert json_str == '"json"'

        # Test in dictionary
        data = {"format": EnumDataType.YAML}
        json_str = json.dumps(data, default=str)
        assert '"format": "yaml"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class EnumDataConfig(BaseModel):
            format: EnumDataType

        # Test valid enum assignment
        config = EnumDataConfig(format=EnumDataType.JSON)
        assert config.format == EnumDataType.JSON

        # Test string assignment (should work due to str inheritance)
        config = EnumDataConfig(format="xml")
        assert config.format == EnumDataType.XML

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            EnumDataConfig(format="INVALID_FORMAT")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class EnumDataConfig(BaseModel):
            format: EnumDataType

        config = EnumDataConfig(format=EnumDataType.CSV)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"format": "csv"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"format":"csv"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity - values should match exactly
        assert EnumDataType.JSON.value == "json"
        assert EnumDataType.JSON.value != "JSON"
        assert EnumDataType.BINARY.value == "binary"
        assert EnumDataType.BINARY.value != "BINARY"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumDataType("invalid_format")

    def test_comprehensive_data_processing_scenarios(self):
        """Test comprehensive data processing scenarios."""
        # Test API response format scenario
        api_format = EnumDataType.JSON
        assert EnumDataType.is_text_based(api_format) is True
        assert EnumDataType.is_structured(api_format) is True
        assert EnumDataType.supports_schema(api_format) is True

        # Test configuration file scenario
        config_format = EnumDataType.YAML
        assert EnumDataType.is_text_based(config_format) is True
        assert EnumDataType.is_structured(config_format) is True
        assert EnumDataType.supports_schema(config_format) is True

        # Test log file scenario
        log_format = EnumDataType.TEXT
        assert EnumDataType.is_text_based(log_format) is True
        assert EnumDataType.is_structured(log_format) is False
        assert EnumDataType.supports_schema(log_format) is False

        # Test binary data scenario
        binary_format = EnumDataType.BINARY
        assert EnumDataType.is_text_based(binary_format) is False
        assert EnumDataType.is_structured(binary_format) is False
        assert EnumDataType.supports_schema(binary_format) is False

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable
        data = {"data_type": EnumDataType.YAML.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "data_type: yaml" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["data_type"] == "yaml"

        # Test that the enum value equals the string
        assert EnumDataType.YAML == "yaml"

    def test_case_sensitivity_handling(self):
        """Test that case sensitivity is preserved correctly."""
        # All values are now lowercase for ONEX consistency
        lowercase_types = [
            EnumDataType.JSON,
            EnumDataType.XML,
            EnumDataType.TEXT,
            EnumDataType.CSV,
            EnumDataType.YAML,
            EnumDataType.BINARY,
        ]

        for data_type in lowercase_types:
            assert data_type.value == data_type.value.lower()

    def test_format_specific_logic(self):
        """Test format-specific logic and use cases."""
        # JSON should be good for APIs
        json_type = EnumDataType.JSON
        assert EnumDataType.is_structured(json_type) is True
        assert EnumDataType.supports_schema(json_type) is True
        assert EnumDataType.is_text_based(json_type) is True

        # XML should be good for complex documents
        xml_type = EnumDataType.XML
        assert EnumDataType.is_structured(xml_type) is True
        assert EnumDataType.supports_schema(xml_type) is True
        assert EnumDataType.is_text_based(xml_type) is True

        # CSV should be good for tabular data but no schema
        csv_type = EnumDataType.CSV
        assert EnumDataType.is_structured(csv_type) is True
        assert EnumDataType.supports_schema(csv_type) is False
        assert EnumDataType.is_text_based(csv_type) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
