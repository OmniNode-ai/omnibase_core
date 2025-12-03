"""
Unit tests for EnumNodeKind.

Tests all aspects of the node kind enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Helper methods (is_core_node_type, is_infrastructure_type)
- Pydantic model compatibility
- Edge cases and error conditions
"""

import copy
import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind


class TestEnumNodeKind:
    """Test cases for EnumNodeKind."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumNodeKind properly inherits from str and Enum."""
        assert issubclass(EnumNodeKind, str)
        assert issubclass(EnumNodeKind, Enum)

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = [
            "EFFECT",
            "COMPUTE",
            "REDUCER",
            "ORCHESTRATOR",
            "RUNTIME_HOST",
        ]

        for value in expected_values:
            assert hasattr(EnumNodeKind, value), f"Missing enum value: {value}"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumNodeKind.EFFECT: "effect",
            EnumNodeKind.COMPUTE: "compute",
            EnumNodeKind.REDUCER: "reducer",
            EnumNodeKind.ORCHESTRATOR: "orchestrator",
            EnumNodeKind.RUNTIME_HOST: "runtime_host",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string


class TestEnumNodeKindRuntimeHost:
    """Test cases specifically for RUNTIME_HOST enum value."""

    def test_runtime_host_value(self) -> None:
        """Test that RUNTIME_HOST has the correct value."""
        assert EnumNodeKind.RUNTIME_HOST.value == "runtime_host"

    def test_runtime_host_from_string(self) -> None:
        """Test that RUNTIME_HOST can be created from string value."""
        assert EnumNodeKind("runtime_host") == EnumNodeKind.RUNTIME_HOST

    def test_runtime_host_serialization(self) -> None:
        """Test that RUNTIME_HOST serializes correctly."""
        assert str(EnumNodeKind.RUNTIME_HOST) == "runtime_host"
        assert str(EnumNodeKind.RUNTIME_HOST.value) == "runtime_host"

    def test_runtime_host_string_comparison(self) -> None:
        """Test that RUNTIME_HOST can be compared with strings."""
        assert EnumNodeKind.RUNTIME_HOST == "runtime_host"
        assert EnumNodeKind.RUNTIME_HOST != "effect"
        assert EnumNodeKind.RUNTIME_HOST != "compute"

    def test_runtime_host_is_infrastructure_type(self) -> None:
        """Test that RUNTIME_HOST is classified as infrastructure type."""
        assert EnumNodeKind.is_infrastructure_type(EnumNodeKind.RUNTIME_HOST) is True

    def test_runtime_host_is_not_core_node_type(self) -> None:
        """Test that RUNTIME_HOST is not classified as core node type."""
        assert EnumNodeKind.is_core_node_type(EnumNodeKind.RUNTIME_HOST) is False

    def test_runtime_host_json_serialization(self) -> None:
        """Test that RUNTIME_HOST is JSON serializable."""
        serialized = json.dumps(EnumNodeKind.RUNTIME_HOST.value)
        assert serialized == '"runtime_host"'

        deserialized = json.loads(serialized)
        reconstructed = EnumNodeKind(deserialized)
        assert reconstructed == EnumNodeKind.RUNTIME_HOST

    def test_runtime_host_with_pydantic(self) -> None:
        """Test that RUNTIME_HOST works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            node_kind: EnumNodeKind

        # Test enum initialization
        model = TestModel(node_kind=EnumNodeKind.RUNTIME_HOST)
        assert model.node_kind == EnumNodeKind.RUNTIME_HOST

        # Test string initialization
        model = TestModel(node_kind="runtime_host")
        assert model.node_kind == EnumNodeKind.RUNTIME_HOST

        # Test serialization
        data = model.model_dump()
        assert data["node_kind"] == "runtime_host"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.node_kind == EnumNodeKind.RUNTIME_HOST


class TestEnumNodeKindHelperMethods:
    """Test cases for EnumNodeKind helper methods."""

    def test_is_core_node_type_for_core_types(self) -> None:
        """Test that core node types are correctly identified."""
        core_types = [
            EnumNodeKind.EFFECT,
            EnumNodeKind.COMPUTE,
            EnumNodeKind.REDUCER,
            EnumNodeKind.ORCHESTRATOR,
        ]

        for node_kind in core_types:
            assert (
                EnumNodeKind.is_core_node_type(node_kind) is True
            ), f"{node_kind} should be core node type"

    def test_is_core_node_type_for_non_core_types(self) -> None:
        """Test that non-core node types are correctly identified."""
        assert EnumNodeKind.is_core_node_type(EnumNodeKind.RUNTIME_HOST) is False

    def test_is_infrastructure_type_for_infrastructure_types(self) -> None:
        """Test that infrastructure types are correctly identified."""
        assert EnumNodeKind.is_infrastructure_type(EnumNodeKind.RUNTIME_HOST) is True

    def test_is_infrastructure_type_for_non_infrastructure_types(self) -> None:
        """Test that non-infrastructure types are correctly identified."""
        non_infra_types = [
            EnumNodeKind.EFFECT,
            EnumNodeKind.COMPUTE,
            EnumNodeKind.REDUCER,
            EnumNodeKind.ORCHESTRATOR,
        ]

        for node_kind in non_infra_types:
            assert (
                EnumNodeKind.is_infrastructure_type(node_kind) is False
            ), f"{node_kind} should not be infrastructure type"


class TestEnumNodeKindSerialization:
    """Test cases for EnumNodeKind serialization and deserialization."""

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        assert EnumNodeKind("effect") == EnumNodeKind.EFFECT
        assert EnumNodeKind("compute") == EnumNodeKind.COMPUTE
        assert EnumNodeKind("reducer") == EnumNodeKind.REDUCER
        assert EnumNodeKind("orchestrator") == EnumNodeKind.ORCHESTRATOR
        assert EnumNodeKind("runtime_host") == EnumNodeKind.RUNTIME_HOST

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings."""
        assert EnumNodeKind.EFFECT == "effect"
        assert EnumNodeKind.COMPUTE == "compute"
        assert EnumNodeKind.REDUCER == "reducer"
        assert EnumNodeKind.ORCHESTRATOR == "orchestrator"
        assert EnumNodeKind.RUNTIME_HOST == "runtime_host"

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumNodeKind:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumNodeKind(deserialized)
            assert reconstructed == member

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            node_kind: EnumNodeKind

        # Test valid values
        model = TestModel(node_kind=EnumNodeKind.EFFECT)
        assert model.node_kind == EnumNodeKind.EFFECT

        # Test string initialization
        model = TestModel(node_kind="compute")
        assert model.node_kind == EnumNodeKind.COMPUTE

        # Test serialization
        data = model.model_dump()
        assert data["node_kind"] == "compute"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.node_kind == EnumNodeKind.COMPUTE


class TestEnumNodeKindBehavior:
    """Test cases for EnumNodeKind general behavior."""

    def test_enum_member_count(self) -> None:
        """Test that the enum has the expected number of members."""
        expected_count = 5
        actual_count = len(list(EnumNodeKind))
        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} members, got {actual_count}"

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumNodeKind]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        expected_values = {
            "effect",
            "compute",
            "reducer",
            "orchestrator",
            "runtime_host",
        }
        actual_values = {member.value for member in EnumNodeKind}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumNodeKind("INVALID_TYPE")

    def test_enum_in_operator(self) -> None:
        """Test that 'in' operator works with enum."""
        assert EnumNodeKind.EFFECT in EnumNodeKind
        assert EnumNodeKind.RUNTIME_HOST in EnumNodeKind

        # Test that strings work with member values
        effect_member = EnumNodeKind.EFFECT
        assert effect_member.value == "effect"

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        node_set = {EnumNodeKind.EFFECT, EnumNodeKind.RUNTIME_HOST}
        assert len(node_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumNodeKind.EFFECT) == hash(EnumNodeKind.EFFECT)

    def test_enum_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumNodeKind.EFFECT) == "<EnumNodeKind.EFFECT: 'effect'>"
        assert repr(EnumNodeKind.RUNTIME_HOST) == (
            "<EnumNodeKind.RUNTIME_HOST: 'runtime_host'>"
        )

    def test_enum_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumNodeKind:
            assert bool(member) is True

    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumNodeKind("EFFECT")  # Should be "effect"

        with pytest.raises(ValueError):
            EnumNodeKind("Effect")  # Should be "effect"

        with pytest.raises(ValueError):
            EnumNodeKind("RUNTIME_HOST")  # Should be "runtime_host"

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumNodeKind.EFFECT is EnumNodeKind.EFFECT

        # Different enum members should not be identical
        assert EnumNodeKind.EFFECT is not EnumNodeKind.RUNTIME_HOST

        # Equality with strings should work
        assert EnumNodeKind.EFFECT == "effect"
        assert EnumNodeKind.EFFECT != "runtime_host"

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        node_kind = EnumNodeKind.RUNTIME_HOST
        assert isinstance(node_kind, str)
        assert node_kind == "runtime_host"
        assert len(node_kind) == 12
        assert node_kind.startswith("runtime")

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert "four-node architecture" in EnumNodeKind.__doc__


class TestEnumNodeKindEdgeCases:
    """Test edge cases and error conditions for EnumNodeKind."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumNodeKind(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumNodeKind("")

    def test_enum_with_whitespace(self) -> None:
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumNodeKind(" effect ")

        with pytest.raises(ValueError):
            EnumNodeKind("effect ")

        with pytest.raises(ValueError):
            EnumNodeKind(" runtime_host")

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumNodeKind:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        node_kind = EnumNodeKind.RUNTIME_HOST

        # Shallow copy should return the same object
        shallow_copy = copy.copy(node_kind)
        assert shallow_copy is node_kind

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(node_kind)
        assert deep_copy is node_kind

    def test_enum_ordering_behavior(self) -> None:
        """Test that enum members support ordering (inherits from str)."""
        # Since EnumNodeKind(str, Enum), it supports string ordering
        result1 = EnumNodeKind.EFFECT < EnumNodeKind.RUNTIME_HOST
        result2 = EnumNodeKind.EFFECT > EnumNodeKind.RUNTIME_HOST

        # The results depend on string comparison of the values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
