# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for EnumHandlerRole.

Tests all aspects of the handler role enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Helper methods (values, assert_exhaustive)
- Pydantic model compatibility
- Edge cases and error conditions
"""

import copy
import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_handler_role import EnumHandlerRole
from omnibase_core.errors import ModelOnexError


@pytest.mark.unit
class TestEnumHandlerRole:
    """Test cases for EnumHandlerRole."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumHandlerRole properly inherits from str and Enum."""
        assert issubclass(EnumHandlerRole, str)
        assert issubclass(EnumHandlerRole, Enum)

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = [
            "INFRA_HANDLER",
            "NODE_HANDLER",
            "PROJECTION_HANDLER",
            "COMPUTE_HANDLER",
        ]

        for value in expected_values:
            assert hasattr(EnumHandlerRole, value), f"Missing enum value: {value}"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumHandlerRole.INFRA_HANDLER: "infra_handler",
            EnumHandlerRole.NODE_HANDLER: "node_handler",
            EnumHandlerRole.PROJECTION_HANDLER: "projection_handler",
            EnumHandlerRole.COMPUTE_HANDLER: "compute_handler",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_infra_handler_value(self) -> None:
        """Test that INFRA_HANDLER has the correct value."""
        assert EnumHandlerRole.INFRA_HANDLER.value == "infra_handler"

    def test_node_handler_value(self) -> None:
        """Test that NODE_HANDLER has the correct value."""
        assert EnumHandlerRole.NODE_HANDLER.value == "node_handler"

    def test_projection_handler_value(self) -> None:
        """Test that PROJECTION_HANDLER has the correct value."""
        assert EnumHandlerRole.PROJECTION_HANDLER.value == "projection_handler"

    def test_compute_handler_value(self) -> None:
        """Test that COMPUTE_HANDLER has the correct value."""
        assert EnumHandlerRole.COMPUTE_HANDLER.value == "compute_handler"


@pytest.mark.unit
class TestEnumHandlerRoleStr:
    """Test cases for EnumHandlerRole __str__ method."""

    def test_str_infra_handler(self) -> None:
        """Test that __str__ returns value for INFRA_HANDLER."""
        assert str(EnumHandlerRole.INFRA_HANDLER) == "infra_handler"

    def test_str_node_handler(self) -> None:
        """Test that __str__ returns value for NODE_HANDLER."""
        assert str(EnumHandlerRole.NODE_HANDLER) == "node_handler"

    def test_str_projection_handler(self) -> None:
        """Test that __str__ returns value for PROJECTION_HANDLER."""
        assert str(EnumHandlerRole.PROJECTION_HANDLER) == "projection_handler"

    def test_str_compute_handler(self) -> None:
        """Test that __str__ returns value for COMPUTE_HANDLER."""
        assert str(EnumHandlerRole.COMPUTE_HANDLER) == "compute_handler"

    def test_str_matches_value(self) -> None:
        """Test that __str__ matches .value for all members."""
        for member in EnumHandlerRole:
            assert str(member) == member.value


@pytest.mark.unit
class TestEnumHandlerRoleValues:
    """Test cases for EnumHandlerRole values() classmethod."""

    def test_values_returns_list(self) -> None:
        """Test that values() returns a list."""
        result = EnumHandlerRole.values()
        assert isinstance(result, list)

    def test_values_contains_all_members(self) -> None:
        """Test that values() contains all enum values."""
        expected = {
            "infra_handler",
            "node_handler",
            "projection_handler",
            "compute_handler",
        }
        result = set(EnumHandlerRole.values())
        assert result == expected

    def test_values_length(self) -> None:
        """Test that values() returns correct number of items."""
        assert len(EnumHandlerRole.values()) == 4

    def test_values_are_strings(self) -> None:
        """Test that all values in values() are strings."""
        for value in EnumHandlerRole.values():
            assert isinstance(value, str)


@pytest.mark.unit
class TestEnumHandlerRoleAssertExhaustive:
    """Test cases for EnumHandlerRole assert_exhaustive() method."""

    def test_assert_exhaustive_raises_model_onex_error(self) -> None:
        """Test that assert_exhaustive raises ModelOnexError."""
        # We need to pass a value that would be typed as Never
        # In practice this is used in match statements after all cases handled
        # Testing by passing an invalid value
        with pytest.raises(ModelOnexError) as exc_info:
            # type: ignore is needed since we're intentionally passing wrong type
            EnumHandlerRole.assert_exhaustive("invalid")  # type: ignore[arg-type]

        assert "Unhandled enum value" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_assert_exhaustive_message_contains_value(self) -> None:
        """Test that assert_exhaustive error message contains the value."""
        test_value = "test_unhandled_value"
        with pytest.raises(ModelOnexError) as exc_info:
            EnumHandlerRole.assert_exhaustive(test_value)  # type: ignore[arg-type]

        assert test_value in str(exc_info.value)


@pytest.mark.unit
class TestEnumHandlerRoleSerialization:
    """Test cases for EnumHandlerRole serialization and deserialization."""

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        assert EnumHandlerRole("infra_handler") == EnumHandlerRole.INFRA_HANDLER
        assert EnumHandlerRole("node_handler") == EnumHandlerRole.NODE_HANDLER
        assert (
            EnumHandlerRole("projection_handler") == EnumHandlerRole.PROJECTION_HANDLER
        )
        assert EnumHandlerRole("compute_handler") == EnumHandlerRole.COMPUTE_HANDLER

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings."""
        assert EnumHandlerRole.INFRA_HANDLER == "infra_handler"
        assert EnumHandlerRole.NODE_HANDLER == "node_handler"
        assert EnumHandlerRole.PROJECTION_HANDLER == "projection_handler"
        assert EnumHandlerRole.COMPUTE_HANDLER == "compute_handler"

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumHandlerRole:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumHandlerRole(deserialized)
            assert reconstructed == member

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            role: EnumHandlerRole

        # Test valid values
        model = TestModel(role=EnumHandlerRole.INFRA_HANDLER)
        assert model.role == EnumHandlerRole.INFRA_HANDLER

        # Test string initialization
        model = TestModel(role="node_handler")
        assert model.role == EnumHandlerRole.NODE_HANDLER

        # Test serialization
        data = model.model_dump()
        assert data["role"] == "node_handler"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.role == EnumHandlerRole.NODE_HANDLER


@pytest.mark.unit
class TestEnumHandlerRoleBehavior:
    """Test cases for EnumHandlerRole general behavior."""

    def test_enum_member_count(self) -> None:
        """Test that the enum has the expected number of members."""
        expected_count = 4
        actual_count = len(list(EnumHandlerRole))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumHandlerRole]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        expected_values = {
            "infra_handler",
            "node_handler",
            "projection_handler",
            "compute_handler",
        }
        actual_values = {member.value for member in EnumHandlerRole}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerRole("INVALID_ROLE")

    def test_enum_in_operator(self) -> None:
        """Test that 'in' operator works with enum."""
        assert EnumHandlerRole.INFRA_HANDLER in EnumHandlerRole
        assert EnumHandlerRole.NODE_HANDLER in EnumHandlerRole
        assert EnumHandlerRole.PROJECTION_HANDLER in EnumHandlerRole
        assert EnumHandlerRole.COMPUTE_HANDLER in EnumHandlerRole

        # Test that strings work for membership
        assert "infra_handler" in EnumHandlerRole
        assert "node_handler" in EnumHandlerRole
        assert "projection_handler" in EnumHandlerRole
        assert "compute_handler" in EnumHandlerRole
        assert "invalid" not in EnumHandlerRole

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        role_set = {
            EnumHandlerRole.INFRA_HANDLER,
            EnumHandlerRole.NODE_HANDLER,
            EnumHandlerRole.PROJECTION_HANDLER,
            EnumHandlerRole.COMPUTE_HANDLER,
        }
        assert len(role_set) == 4

        # Test that same enum members have same hash
        assert hash(EnumHandlerRole.INFRA_HANDLER) == hash(
            EnumHandlerRole.INFRA_HANDLER
        )

    def test_enum_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumHandlerRole.INFRA_HANDLER) == (
            "<EnumHandlerRole.INFRA_HANDLER: 'infra_handler'>"
        )
        assert repr(EnumHandlerRole.NODE_HANDLER) == (
            "<EnumHandlerRole.NODE_HANDLER: 'node_handler'>"
        )
        assert repr(EnumHandlerRole.PROJECTION_HANDLER) == (
            "<EnumHandlerRole.PROJECTION_HANDLER: 'projection_handler'>"
        )
        assert repr(EnumHandlerRole.COMPUTE_HANDLER) == (
            "<EnumHandlerRole.COMPUTE_HANDLER: 'compute_handler'>"
        )

    def test_enum_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumHandlerRole:
            assert bool(member) is True

    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumHandlerRole("INFRA_HANDLER")  # Should be "infra_handler"

        with pytest.raises(ValueError):
            EnumHandlerRole("Infra_Handler")  # Should be "infra_handler"

        with pytest.raises(ValueError):
            EnumHandlerRole("NODE_HANDLER")  # Should be "node_handler"

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumHandlerRole.INFRA_HANDLER is EnumHandlerRole.INFRA_HANDLER

        # Different enum members should not be identical
        assert EnumHandlerRole.INFRA_HANDLER is not EnumHandlerRole.NODE_HANDLER

        # Equality with strings should work
        assert EnumHandlerRole.INFRA_HANDLER == "infra_handler"
        assert EnumHandlerRole.INFRA_HANDLER != "node_handler"

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        role = EnumHandlerRole.PROJECTION_HANDLER
        assert isinstance(role, str)
        assert role == "projection_handler"
        assert len(role) == 18  # "projection_handler" is 18 chars
        assert role.startswith("projection")

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumHandlerRole.__doc__ is not None
        doc_lower = EnumHandlerRole.__doc__.lower()
        # Check for key concepts in docstring
        assert "handler" in doc_lower or "role" in doc_lower
        assert "INFRA_HANDLER" in EnumHandlerRole.__doc__
        assert "NODE_HANDLER" in EnumHandlerRole.__doc__


@pytest.mark.unit
class TestEnumHandlerRoleRoles:
    """Test cases for role semantics."""

    def test_infra_handler_is_infrastructure(self) -> None:
        """Test that INFRA_HANDLER represents infrastructure/transport handlers."""
        # Verify docstring describes infrastructure behavior
        assert EnumHandlerRole.INFRA_HANDLER.__doc__ is not None
        doc_lower = EnumHandlerRole.INFRA_HANDLER.__doc__.lower()
        assert "protocol" in doc_lower or "transport" in doc_lower

    def test_node_handler_is_event_processing(self) -> None:
        """Test that NODE_HANDLER represents event processing handlers."""
        # Verify docstring describes event processing
        assert EnumHandlerRole.NODE_HANDLER.__doc__ is not None
        doc_lower = EnumHandlerRole.NODE_HANDLER.__doc__.lower()
        assert "event" in doc_lower or "business" in doc_lower

    def test_projection_handler_is_read_model(self) -> None:
        """Test that PROJECTION_HANDLER represents projection/read model handlers."""
        assert EnumHandlerRole.PROJECTION_HANDLER.__doc__ is not None
        doc_lower = EnumHandlerRole.PROJECTION_HANDLER.__doc__.lower()
        assert "projection" in doc_lower or "read" in doc_lower

    def test_compute_handler_is_pure_computation(self) -> None:
        """Test that COMPUTE_HANDLER represents pure computation handlers."""
        assert EnumHandlerRole.COMPUTE_HANDLER.__doc__ is not None
        doc_lower = EnumHandlerRole.COMPUTE_HANDLER.__doc__.lower()
        assert "pure" in doc_lower or "computation" in doc_lower


@pytest.mark.unit
class TestEnumHandlerRoleEdgeCases:
    """Test edge cases and error conditions for EnumHandlerRole."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumHandlerRole(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumHandlerRole("")

    def test_enum_with_whitespace(self) -> None:
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumHandlerRole(" infra_handler ")

        with pytest.raises(ValueError):
            EnumHandlerRole("infra_handler ")

        with pytest.raises(ValueError):
            EnumHandlerRole(" node_handler")

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumHandlerRole:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        role = EnumHandlerRole.INFRA_HANDLER

        # Shallow copy should return the same object
        shallow_copy = copy.copy(role)
        assert shallow_copy is role

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(role)
        assert deep_copy is role

    def test_enum_ordering_behavior(self) -> None:
        """Test that enum members support ordering (inherits from str)."""
        # Since EnumHandlerRole(str, Enum), it supports string ordering
        result1 = EnumHandlerRole.COMPUTE_HANDLER < EnumHandlerRole.INFRA_HANDLER
        result2 = EnumHandlerRole.COMPUTE_HANDLER > EnumHandlerRole.INFRA_HANDLER

        # The results depend on string comparison of the values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)


@pytest.mark.unit
class TestEnumHandlerRolePropertyBased:
    """Property-based tests using hypothesis for EnumHandlerRole."""

    def test_all_roles_have_valid_string_representation(self) -> None:
        """Property: Every EnumHandlerRole value has a non-empty string representation."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerRole)))
        def check_string_representation(role: EnumHandlerRole) -> None:
            string_repr = str(role)
            assert isinstance(string_repr, str)
            assert len(string_repr) > 0
            assert string_repr == role.value

        check_string_representation()

    def test_all_roles_roundtrip_through_value(self) -> None:
        """Property: Every EnumHandlerRole can be reconstructed from its value."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerRole)))
        def check_roundtrip(role: EnumHandlerRole) -> None:
            value = role.value
            reconstructed = EnumHandlerRole(value)
            assert reconstructed == role
            assert reconstructed is role  # Same singleton instance

        check_roundtrip()

    def test_json_serialization_roundtrip(self) -> None:
        """Property: Every EnumHandlerRole survives JSON serialization roundtrip."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerRole)))
        def check_json_roundtrip(role: EnumHandlerRole) -> None:
            serialized = json.dumps(role.value)
            deserialized = json.loads(serialized)
            reconstructed = EnumHandlerRole(deserialized)
            assert reconstructed == role

        check_json_roundtrip()

    def test_pickle_serialization_preserves_identity(self) -> None:
        """Property: Pickle serialization preserves enum identity."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerRole)))
        def check_pickle_identity(role: EnumHandlerRole) -> None:
            pickled = pickle.dumps(role)
            unpickled = pickle.loads(pickled)
            assert unpickled == role
            assert unpickled is role  # Same singleton

        check_pickle_identity()

    def test_values_classmethod_includes_all_members(self) -> None:
        """Property: values() classmethod includes all enum members."""
        from hypothesis import given
        from hypothesis import strategies as st

        all_values = EnumHandlerRole.values()

        @given(st.sampled_from(list(EnumHandlerRole)))
        def check_in_values(role: EnumHandlerRole) -> None:
            assert role.value in all_values

        check_in_values()


@pytest.mark.unit
class TestEnumHandlerRoleExhaustivenessCheck:
    """Test exhaustiveness pattern for match statements."""

    def test_exhaustive_match_pattern(self) -> None:
        """Test that all roles can be matched exhaustively."""

        def get_router(role: EnumHandlerRole) -> str:
            match role:
                case EnumHandlerRole.INFRA_HANDLER:
                    return "infra_router"
                case EnumHandlerRole.NODE_HANDLER:
                    return "event_router"
                case EnumHandlerRole.PROJECTION_HANDLER:
                    return "projection_router"
                case EnumHandlerRole.COMPUTE_HANDLER:
                    return "compute_router"
                case _:
                    EnumHandlerRole.assert_exhaustive(role)

        # Test all roles are handled
        assert get_router(EnumHandlerRole.INFRA_HANDLER) == "infra_router"
        assert get_router(EnumHandlerRole.NODE_HANDLER) == "event_router"
        assert get_router(EnumHandlerRole.PROJECTION_HANDLER) == "projection_router"
        assert get_router(EnumHandlerRole.COMPUTE_HANDLER) == "compute_router"

    def test_all_values_list_matches_iteration(self) -> None:
        """Test that values() classmethod returns same values as iteration."""
        iterated_values = [member.value for member in EnumHandlerRole]
        classmethod_values = EnumHandlerRole.values()

        assert set(iterated_values) == set(classmethod_values)
        assert len(iterated_values) == len(classmethod_values)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
