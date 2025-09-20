"""
Unit tests for EnumArtifactType.

Tests all aspects of the artifact type enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Edge cases and error conditions
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_artifact_type import EnumArtifactType


class TestEnumArtifactType:
    """Test cases for EnumArtifactType."""

    def test_enum_inherits_from_str_and_enum(self):
        """Test that EnumArtifactType properly inherits from str and Enum."""
        assert issubclass(EnumArtifactType, str)
        assert issubclass(EnumArtifactType, Enum)

    def test_enum_values_exist(self):
        """Test that all expected enum values exist."""
        expected_values = [
            "TOOL",
            "VALIDATOR",
            "AGENT",
            "MODEL",
            "PLUGIN",
            "SCHEMA",
            "CONFIG",
        ]

        for value in expected_values:
            assert hasattr(EnumArtifactType, value), f"Missing enum value: {value}"

    def test_enum_string_values(self):
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumArtifactType.TOOL: "TOOL",
            EnumArtifactType.VALIDATOR: "VALIDATOR",
            EnumArtifactType.AGENT: "AGENT",
            EnumArtifactType.MODEL: "MODEL",
            EnumArtifactType.PLUGIN: "PLUGIN",
            EnumArtifactType.SCHEMA: "SCHEMA",
            EnumArtifactType.CONFIG: "CONFIG",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_can_be_created_from_string(self):
        """Test that enum members can be created from string values."""
        assert EnumArtifactType("TOOL") == EnumArtifactType.TOOL
        assert EnumArtifactType("VALIDATOR") == EnumArtifactType.VALIDATOR
        assert EnumArtifactType("AGENT") == EnumArtifactType.AGENT
        assert EnumArtifactType("MODEL") == EnumArtifactType.MODEL
        assert EnumArtifactType("PLUGIN") == EnumArtifactType.PLUGIN
        assert EnumArtifactType("SCHEMA") == EnumArtifactType.SCHEMA
        assert EnumArtifactType("CONFIG") == EnumArtifactType.CONFIG

    def test_enum_string_comparison(self):
        """Test that enum members can be compared with strings."""
        assert EnumArtifactType.TOOL == "TOOL"
        assert EnumArtifactType.VALIDATOR == "VALIDATOR"
        assert EnumArtifactType.AGENT == "AGENT"
        assert EnumArtifactType.MODEL == "MODEL"
        assert EnumArtifactType.PLUGIN == "PLUGIN"
        assert EnumArtifactType.SCHEMA == "SCHEMA"
        assert EnumArtifactType.CONFIG == "CONFIG"

    def test_enum_member_count(self):
        """Test that the enum has the expected number of members."""
        expected_count = 7
        actual_count = len(list(EnumArtifactType))
        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} members, got {actual_count}"

    def test_enum_member_uniqueness(self):
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumArtifactType]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        expected_values = {
            "TOOL",
            "VALIDATOR",
            "AGENT",
            "MODEL",
            "PLUGIN",
            "SCHEMA",
            "CONFIG",
        }
        actual_values = {member.value for member in EnumArtifactType}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self):
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumArtifactType("INVALID_TYPE")

    def test_enum_in_operator(self):
        """Test that 'in' operator works with enum."""
        assert EnumArtifactType.TOOL in EnumArtifactType
        assert EnumArtifactType.VALIDATOR in EnumArtifactType

        # Test that strings work with member values
        tool_member = EnumArtifactType.TOOL
        assert "TOOL" == tool_member.value

    def test_enum_hash_consistency(self):
        """Test that enum members are hashable and consistent."""
        artifact_set = {EnumArtifactType.TOOL, EnumArtifactType.VALIDATOR}
        assert len(artifact_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumArtifactType.TOOL) == hash(EnumArtifactType.TOOL)

    def test_enum_repr(self):
        """Test that enum members have proper string representation."""
        assert repr(EnumArtifactType.TOOL) == "<EnumArtifactType.TOOL: 'TOOL'>"
        assert (
            repr(EnumArtifactType.VALIDATOR)
            == "<EnumArtifactType.VALIDATOR: 'VALIDATOR'>"
        )

    def test_enum_bool_evaluation(self):
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumArtifactType:
            assert bool(member) is True

    def test_enum_serialization_json_compatible(self):
        """Test that enum values are JSON serializable."""
        import json

        for member in EnumArtifactType:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumArtifactType(deserialized)
            assert reconstructed == member

    def test_enum_case_sensitivity(self):
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumArtifactType("tool")  # Should be "TOOL"

        with pytest.raises(ValueError):
            EnumArtifactType("Tool")  # Should be "TOOL"

    def test_enum_with_pydantic_compatibility(self):
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            artifact_type: EnumArtifactType

        # Test valid values
        model = TestModel(artifact_type=EnumArtifactType.TOOL)
        assert model.artifact_type == EnumArtifactType.TOOL

        # Test string initialization
        model = TestModel(artifact_type="VALIDATOR")
        assert model.artifact_type == EnumArtifactType.VALIDATOR

        # Test serialization
        data = model.model_dump()
        assert data["artifact_type"] == "VALIDATOR"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.artifact_type == EnumArtifactType.VALIDATOR

    def test_enum_equality_and_identity(self):
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumArtifactType.TOOL is EnumArtifactType.TOOL

        # Different enum members should not be identical
        assert EnumArtifactType.TOOL is not EnumArtifactType.VALIDATOR

        # Equality with strings should work
        assert EnumArtifactType.TOOL == "TOOL"
        assert EnumArtifactType.TOOL != "VALIDATOR"

    def test_enum_ordering_behavior(self):
        """Test that enum members support ordering (inherits from str)."""
        # Since EnumArtifactType(str, Enum), it supports string ordering
        result1 = EnumArtifactType.TOOL < EnumArtifactType.VALIDATOR
        result2 = EnumArtifactType.TOOL > EnumArtifactType.VALIDATOR

        # The results depend on string comparison of the values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_artifact_type_model_integration(self):
        """Test integration with ModelArtifactTypeConfig."""
        from omnibase_core.models.core.model_artifact_type_config import (
            ModelArtifactTypeConfig,
        )

        # Test valid enum usage
        config = ModelArtifactTypeConfig(name=EnumArtifactType.TOOL)
        assert config.name == EnumArtifactType.TOOL

        # Test string initialization
        config2 = ModelArtifactTypeConfig(name="VALIDATOR")
        assert config2.name == EnumArtifactType.VALIDATOR

        # Test serialization/deserialization
        data = config.model_dump()
        assert data["name"] == "TOOL"

        reconstructed = ModelArtifactTypeConfig.model_validate(data)
        assert reconstructed.name == EnumArtifactType.TOOL


class TestEnumArtifactTypeEdgeCases:
    """Test edge cases and error conditions for EnumArtifactType."""

    def test_enum_with_none_value(self):
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumArtifactType(None)

    def test_enum_with_empty_string(self):
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumArtifactType("")

    def test_enum_with_whitespace(self):
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumArtifactType(" TOOL ")

        with pytest.raises(ValueError):
            EnumArtifactType("TOOL ")

    def test_enum_pickling(self):
        """Test that enum members can be pickled and unpickled."""
        import pickle

        for member in EnumArtifactType:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self):
        """Test enum behavior with copy operations."""
        import copy

        artifact_type = EnumArtifactType.TOOL

        # Shallow copy should return the same object
        shallow_copy = copy.copy(artifact_type)
        assert shallow_copy is artifact_type

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(artifact_type)
        assert deep_copy is artifact_type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
