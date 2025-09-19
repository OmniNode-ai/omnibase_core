"""
Unit tests for EnumFilterType.

Tests all aspects of the filter type enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Edge cases and error conditions
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_filter_type import EnumFilterType


class TestEnumFilterType:
    """Test cases for EnumFilterType."""

    def test_enum_inherits_from_str_and_enum(self):
        """Test that EnumFilterType properly inherits from str and Enum."""
        assert issubclass(EnumFilterType, str)
        assert issubclass(EnumFilterType, Enum)

    def test_enum_values_exist(self):
        """Test that all expected enum values exist."""
        expected_values = [
            "STRING",
            "NUMERIC",
            "DATETIME",
            "LIST",
            "METADATA",
            "STATUS",
            "COMPLEX",
        ]

        for value in expected_values:
            assert hasattr(EnumFilterType, value), f"Missing enum value: {value}"

    def test_enum_string_values(self):
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumFilterType.STRING: "string",
            EnumFilterType.NUMERIC: "numeric",
            EnumFilterType.DATETIME: "datetime",
            EnumFilterType.LIST: "list",
            EnumFilterType.METADATA: "metadata",
            EnumFilterType.STATUS: "status",
            EnumFilterType.COMPLEX: "complex",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert str(enum_member) == expected_str
            assert enum_member.value == expected_str

    def test_enum_can_be_created_from_string(self):
        """Test that enum members can be created from string values."""
        assert EnumFilterType("string") == EnumFilterType.STRING
        assert EnumFilterType("numeric") == EnumFilterType.NUMERIC
        assert EnumFilterType("datetime") == EnumFilterType.DATETIME
        assert EnumFilterType("list") == EnumFilterType.LIST
        assert EnumFilterType("metadata") == EnumFilterType.METADATA
        assert EnumFilterType("status") == EnumFilterType.STATUS
        assert EnumFilterType("complex") == EnumFilterType.COMPLEX

    def test_enum_string_comparison(self):
        """Test that enum members can be compared with strings."""
        assert EnumFilterType.STRING == "string"
        assert EnumFilterType.NUMERIC == "numeric"
        assert EnumFilterType.DATETIME == "datetime"
        assert EnumFilterType.LIST == "list"
        assert EnumFilterType.METADATA == "metadata"
        assert EnumFilterType.STATUS == "status"
        assert EnumFilterType.COMPLEX == "complex"

    def test_enum_member_count(self):
        """Test that the enum has the expected number of members."""
        expected_count = 7
        actual_count = len(list(EnumFilterType))
        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} members, got {actual_count}"

    def test_enum_member_uniqueness(self):
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumFilterType]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        expected_values = {
            "string",
            "numeric",
            "datetime",
            "list",
            "metadata",
            "status",
            "complex",
        }
        actual_values = {member.value for member in EnumFilterType}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self):
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumFilterType("invalid_filter")

    def test_enum_in_operator(self):
        """Test that 'in' operator works with enum."""
        assert EnumFilterType.STRING in EnumFilterType
        assert EnumFilterType.COMPLEX in EnumFilterType

    def test_enum_hash_consistency(self):
        """Test that enum members are hashable and consistent."""
        filter_set = {EnumFilterType.STRING, EnumFilterType.NUMERIC}
        assert len(filter_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumFilterType.STRING) == hash(EnumFilterType.STRING)

    def test_enum_repr(self):
        """Test that enum members have proper string representation."""
        assert repr(EnumFilterType.STRING) == "<EnumFilterType.STRING: 'string'>"
        assert repr(EnumFilterType.COMPLEX) == "<EnumFilterType.COMPLEX: 'complex'>"

    def test_enum_with_pydantic_compatibility(self):
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            filter_type: EnumFilterType

        # Test valid values
        model = TestModel(filter_type=EnumFilterType.STRING)
        assert model.filter_type == EnumFilterType.STRING

        # Test string initialization
        model = TestModel(filter_type="numeric")
        assert model.filter_type == EnumFilterType.NUMERIC

        # Test serialization
        data = model.model_dump()
        assert data["filter_type"] == "numeric"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.filter_type == EnumFilterType.NUMERIC

    def test_filter_type_semantic_grouping(self):
        """Test semantic grouping of filter types."""
        # Data type filters
        data_type_filters = {
            EnumFilterType.STRING,
            EnumFilterType.NUMERIC,
            EnumFilterType.DATETIME,
        }

        # Collection filters
        collection_filters = {EnumFilterType.LIST, EnumFilterType.METADATA}

        # Operational filters
        operational_filters = {EnumFilterType.STATUS, EnumFilterType.COMPLEX}

        all_filters = data_type_filters | collection_filters | operational_filters
        actual_filters = set(EnumFilterType)

        assert all_filters == actual_filters, "Filter type categorization is complete"

    def test_enum_case_sensitivity(self):
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumFilterType("STRING")  # Should be "string"

        with pytest.raises(ValueError):
            EnumFilterType("String")  # Should be "string"

    def test_enum_serialization_json_compatible(self):
        """Test that enum values are JSON serializable."""
        import json

        for member in EnumFilterType:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumFilterType(deserialized)
            assert reconstructed == member


class TestEnumFilterTypeEdgeCases:
    """Test edge cases and error conditions for EnumFilterType."""

    def test_enum_with_none_value(self):
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumFilterType(None)

    def test_enum_with_empty_string(self):
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumFilterType("")

    def test_enum_with_whitespace(self):
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumFilterType(" string ")

    def test_enum_pickling(self):
        """Test that enum members can be pickled and unpickled."""
        import pickle

        for member in EnumFilterType:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
