# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumMetadataNodeType.

Tests all aspects of the metadata node type enum including:
- Enum value validation
- String representation
- JSON serialization compatibility
- Pydantic integration
- Enum iteration and membership
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType


@pytest.mark.unit
class TestEnumMetadataNodeType:
    """Test cases for EnumMetadataNodeType."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "FUNCTION": "function",
            "METHOD": "method",
            "CLASS": "class",
            "MODULE": "module",
            "PROPERTY": "property",
            "VARIABLE": "variable",
            "CONSTANT": "constant",
            "INTERFACE": "interface",
            "TYPE_ALIAS": "type_alias",
            "DOCUMENTATION": "documentation",
            "EXAMPLE": "example",
            "TEST": "test",
        }

        for name, value in expected_values.items():
            node_type = getattr(EnumMetadataNodeType, name)
            assert node_type.value == value

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumMetadataNodeType.FUNCTION, str)
        assert EnumMetadataNodeType.FUNCTION == "function"
        assert isinstance(EnumMetadataNodeType.CLASS, str)
        assert EnumMetadataNodeType.CLASS == "class"

    def test_string_representation(self):
        """Test string representation of enum values."""
        # Enum inherits from str, so value is accessible as string
        assert EnumMetadataNodeType.FUNCTION.value == "function"
        assert EnumMetadataNodeType.METHOD.value == "method"
        assert EnumMetadataNodeType.CLASS.value == "class"
        assert EnumMetadataNodeType.MODULE.value == "module"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumMetadataNodeType.FUNCTION == EnumMetadataNodeType.FUNCTION
        assert EnumMetadataNodeType.CLASS != EnumMetadataNodeType.METHOD
        assert EnumMetadataNodeType.VARIABLE == EnumMetadataNodeType.VARIABLE

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_node_types = [
            EnumMetadataNodeType.FUNCTION,
            EnumMetadataNodeType.METHOD,
            EnumMetadataNodeType.CLASS,
            EnumMetadataNodeType.MODULE,
            EnumMetadataNodeType.PROPERTY,
            EnumMetadataNodeType.VARIABLE,
            EnumMetadataNodeType.CONSTANT,
            EnumMetadataNodeType.INTERFACE,
            EnumMetadataNodeType.TYPE_ALIAS,
            EnumMetadataNodeType.DOCUMENTATION,
            EnumMetadataNodeType.EXAMPLE,
            EnumMetadataNodeType.TEST,
        ]

        for node_type in all_node_types:
            assert node_type in EnumMetadataNodeType

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        node_types = list(EnumMetadataNodeType)
        assert len(node_types) == 12

        node_values = [node.value for node in node_types]
        expected_values = [
            "function",
            "method",
            "class",
            "module",
            "property",
            "variable",
            "constant",
            "interface",
            "type_alias",
            "documentation",
            "example",
            "test",
        ]

        assert set(node_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        node_type = EnumMetadataNodeType.CLASS
        json_str = json.dumps(node_type, default=str)
        assert json_str == '"class"'

        # Test in dictionary
        data = {"node_type": EnumMetadataNodeType.FUNCTION}
        json_str = json.dumps(data, default=str)
        assert '"node_type": "function"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class MetadataConfig(BaseModel):
            node_type: EnumMetadataNodeType

        # Test valid enum assignment
        config = MetadataConfig(node_type=EnumMetadataNodeType.METHOD)
        assert config.node_type == EnumMetadataNodeType.METHOD

        # Test string assignment (should work due to str inheritance)
        config = MetadataConfig(node_type="class")
        assert config.node_type == EnumMetadataNodeType.CLASS

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            MetadataConfig(node_type="invalid_node_type")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class MetadataConfig(BaseModel):
            node_type: EnumMetadataNodeType

        config = MetadataConfig(node_type=EnumMetadataNodeType.INTERFACE)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"node_type": "interface"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"node_type":"interface"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity (should be case-sensitive)
        assert EnumMetadataNodeType.FUNCTION.value == "function"
        assert EnumMetadataNodeType.FUNCTION.value != "FUNCTION"
        assert EnumMetadataNodeType.FUNCTION.value != "Function"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumMetadataNodeType("invalid_value")

    def test_code_node_types(self):
        """Test code-related node types."""
        code_types = [
            EnumMetadataNodeType.FUNCTION,
            EnumMetadataNodeType.METHOD,
            EnumMetadataNodeType.CLASS,
            EnumMetadataNodeType.MODULE,
            EnumMetadataNodeType.PROPERTY,
        ]

        for node_type in code_types:
            assert node_type in EnumMetadataNodeType
            assert isinstance(node_type.value, str)

    def test_data_node_types(self):
        """Test data-related node types."""
        data_types = [
            EnumMetadataNodeType.VARIABLE,
            EnumMetadataNodeType.CONSTANT,
            EnumMetadataNodeType.TYPE_ALIAS,
        ]

        for node_type in data_types:
            assert node_type in EnumMetadataNodeType
            assert isinstance(node_type.value, str)

    def test_documentation_node_types(self):
        """Test documentation-related node types."""
        doc_types = [
            EnumMetadataNodeType.DOCUMENTATION,
            EnumMetadataNodeType.EXAMPLE,
            EnumMetadataNodeType.TEST,
        ]

        for node_type in doc_types:
            assert node_type in EnumMetadataNodeType
            assert isinstance(node_type.value, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
