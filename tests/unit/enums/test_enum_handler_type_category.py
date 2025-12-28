# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for EnumHandlerTypeCategory.

Tests all aspects of the handler type category enumeration including:
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

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory


@pytest.mark.unit
class TestEnumHandlerTypeCategory:
    """Test cases for EnumHandlerTypeCategory."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumHandlerTypeCategory properly inherits from str and Enum."""
        assert issubclass(EnumHandlerTypeCategory, str)
        assert issubclass(EnumHandlerTypeCategory, Enum)

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = [
            "COMPUTE",
            "EFFECT",
            "NONDETERMINISTIC_COMPUTE",
        ]

        for value in expected_values:
            assert hasattr(
                EnumHandlerTypeCategory, value
            ), f"Missing enum value: {value}"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumHandlerTypeCategory.COMPUTE: "compute",
            EnumHandlerTypeCategory.EFFECT: "effect",
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE: "nondeterministic_compute",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_compute_value(self) -> None:
        """Test that COMPUTE has the correct value."""
        assert EnumHandlerTypeCategory.COMPUTE.value == "compute"

    def test_effect_value(self) -> None:
        """Test that EFFECT has the correct value."""
        assert EnumHandlerTypeCategory.EFFECT.value == "effect"

    def test_nondeterministic_compute_value(self) -> None:
        """Test that NONDETERMINISTIC_COMPUTE has the correct value."""
        assert (
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE.value
            == "nondeterministic_compute"
        )


@pytest.mark.unit
class TestEnumHandlerTypeCategoryStr:
    """Test cases for EnumHandlerTypeCategory __str__ method."""

    def test_str_compute(self) -> None:
        """Test that __str__ returns value for COMPUTE."""
        assert str(EnumHandlerTypeCategory.COMPUTE) == "compute"

    def test_str_effect(self) -> None:
        """Test that __str__ returns value for EFFECT."""
        assert str(EnumHandlerTypeCategory.EFFECT) == "effect"

    def test_str_nondeterministic_compute(self) -> None:
        """Test that __str__ returns value for NONDETERMINISTIC_COMPUTE."""
        assert (
            str(EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE)
            == "nondeterministic_compute"
        )

    def test_str_matches_value(self) -> None:
        """Test that __str__ matches .value for all members."""
        for member in EnumHandlerTypeCategory:
            assert str(member) == member.value


@pytest.mark.unit
class TestEnumHandlerTypeCategoryValues:
    """Test cases for EnumHandlerTypeCategory values() classmethod."""

    def test_values_returns_list(self) -> None:
        """Test that values() returns a list."""
        result = EnumHandlerTypeCategory.values()
        assert isinstance(result, list)

    def test_values_contains_all_members(self) -> None:
        """Test that values() contains all enum values."""
        expected = {"compute", "effect", "nondeterministic_compute"}
        result = set(EnumHandlerTypeCategory.values())
        assert result == expected

    def test_values_length(self) -> None:
        """Test that values() returns correct number of items."""
        assert len(EnumHandlerTypeCategory.values()) == 3

    def test_values_are_strings(self) -> None:
        """Test that all values in values() are strings."""
        for value in EnumHandlerTypeCategory.values():
            assert isinstance(value, str)


@pytest.mark.unit
class TestEnumHandlerTypeCategoryAssertExhaustive:
    """Test cases for EnumHandlerTypeCategory assert_exhaustive() method."""

    def test_assert_exhaustive_raises_assertion_error(self) -> None:
        """Test that assert_exhaustive raises AssertionError."""
        # We need to pass a value that would be typed as Never
        # In practice this is used in match statements after all cases handled
        # Testing by passing an invalid value
        with pytest.raises(AssertionError) as exc_info:
            # type: ignore is needed since we're intentionally passing wrong type
            EnumHandlerTypeCategory.assert_exhaustive("invalid")  # type: ignore[arg-type]

        assert "Unhandled enum value" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_assert_exhaustive_message_contains_value(self) -> None:
        """Test that assert_exhaustive error message contains the value."""
        test_value = "test_unhandled_value"
        with pytest.raises(AssertionError) as exc_info:
            EnumHandlerTypeCategory.assert_exhaustive(test_value)  # type: ignore[arg-type]

        assert test_value in str(exc_info.value)


@pytest.mark.unit
class TestEnumHandlerTypeCategorySerialization:
    """Test cases for EnumHandlerTypeCategory serialization and deserialization."""

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        assert EnumHandlerTypeCategory("compute") == EnumHandlerTypeCategory.COMPUTE
        assert EnumHandlerTypeCategory("effect") == EnumHandlerTypeCategory.EFFECT
        assert (
            EnumHandlerTypeCategory("nondeterministic_compute")
            == EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        )

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings."""
        assert EnumHandlerTypeCategory.COMPUTE == "compute"
        assert EnumHandlerTypeCategory.EFFECT == "effect"
        assert (
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
            == "nondeterministic_compute"
        )

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumHandlerTypeCategory:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumHandlerTypeCategory(deserialized)
            assert reconstructed == member

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            category: EnumHandlerTypeCategory

        # Test valid values
        model = TestModel(category=EnumHandlerTypeCategory.COMPUTE)
        assert model.category == EnumHandlerTypeCategory.COMPUTE

        # Test string initialization
        model = TestModel(category="effect")
        assert model.category == EnumHandlerTypeCategory.EFFECT

        # Test serialization
        data = model.model_dump()
        assert data["category"] == "effect"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.category == EnumHandlerTypeCategory.EFFECT


@pytest.mark.unit
class TestEnumHandlerTypeCategoryBehavior:
    """Test cases for EnumHandlerTypeCategory general behavior."""

    def test_enum_member_count(self) -> None:
        """Test that the enum has the expected number of members."""
        expected_count = 3
        actual_count = len(list(EnumHandlerTypeCategory))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumHandlerTypeCategory]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        expected_values = {
            "compute",
            "effect",
            "nondeterministic_compute",
        }
        actual_values = {member.value for member in EnumHandlerTypeCategory}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerTypeCategory("INVALID_TYPE")

    def test_enum_in_operator(self) -> None:
        """Test that 'in' operator works with enum."""
        assert EnumHandlerTypeCategory.COMPUTE in EnumHandlerTypeCategory
        assert EnumHandlerTypeCategory.EFFECT in EnumHandlerTypeCategory
        assert (
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE in EnumHandlerTypeCategory
        )

        # Test that strings work for membership
        assert "compute" in EnumHandlerTypeCategory
        assert "effect" in EnumHandlerTypeCategory
        assert "nondeterministic_compute" in EnumHandlerTypeCategory
        assert "invalid" not in EnumHandlerTypeCategory

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        category_set = {
            EnumHandlerTypeCategory.COMPUTE,
            EnumHandlerTypeCategory.EFFECT,
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
        }
        assert len(category_set) == 3

        # Test that same enum members have same hash
        assert hash(EnumHandlerTypeCategory.COMPUTE) == hash(
            EnumHandlerTypeCategory.COMPUTE
        )

    def test_enum_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumHandlerTypeCategory.COMPUTE) == (
            "<EnumHandlerTypeCategory.COMPUTE: 'compute'>"
        )
        assert repr(EnumHandlerTypeCategory.EFFECT) == (
            "<EnumHandlerTypeCategory.EFFECT: 'effect'>"
        )
        assert repr(EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE) == (
            "<EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE: 'nondeterministic_compute'>"
        )

    def test_enum_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumHandlerTypeCategory:
            assert bool(member) is True

    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumHandlerTypeCategory("COMPUTE")  # Should be "compute"

        with pytest.raises(ValueError):
            EnumHandlerTypeCategory("Compute")  # Should be "compute"

        with pytest.raises(ValueError):
            EnumHandlerTypeCategory("EFFECT")  # Should be "effect"

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumHandlerTypeCategory.COMPUTE is EnumHandlerTypeCategory.COMPUTE

        # Different enum members should not be identical
        assert EnumHandlerTypeCategory.COMPUTE is not EnumHandlerTypeCategory.EFFECT

        # Equality with strings should work
        assert EnumHandlerTypeCategory.COMPUTE == "compute"
        assert EnumHandlerTypeCategory.COMPUTE != "effect"

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        category = EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        assert isinstance(category, str)
        assert category == "nondeterministic_compute"
        assert len(category) == 24  # "nondeterministic_compute" is 24 chars
        assert category.startswith("nondeterministic")

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumHandlerTypeCategory.__doc__ is not None
        doc_lower = EnumHandlerTypeCategory.__doc__.lower()
        # Check for key concepts in docstring
        assert "handler" in doc_lower or "classification" in doc_lower
        assert "COMPUTE" in EnumHandlerTypeCategory.__doc__
        assert "EFFECT" in EnumHandlerTypeCategory.__doc__


@pytest.mark.unit
class TestEnumHandlerTypeCategoryCategories:
    """Test cases for category semantics."""

    def test_compute_is_pure_deterministic(self) -> None:
        """Test that COMPUTE represents pure, deterministic computation."""
        # Verify docstring describes deterministic behavior
        assert EnumHandlerTypeCategory.COMPUTE.__doc__ is not None
        assert "deterministic" in EnumHandlerTypeCategory.COMPUTE.__doc__.lower()

    def test_effect_is_side_effecting(self) -> None:
        """Test that EFFECT represents side-effecting I/O operations."""
        # Verify docstring describes side effects
        assert EnumHandlerTypeCategory.EFFECT.__doc__ is not None
        doc_lower = EnumHandlerTypeCategory.EFFECT.__doc__.lower()
        assert "side" in doc_lower or "i/o" in doc_lower or "io" in doc_lower

    def test_nondeterministic_compute_is_pure_but_nondeterministic(self) -> None:
        """Test that NONDETERMINISTIC_COMPUTE is pure but non-deterministic."""
        assert EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE.__doc__ is not None
        doc_lower = EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE.__doc__.lower()
        assert "non-deterministic" in doc_lower or "nondeterministic" in doc_lower


@pytest.mark.unit
class TestEnumHandlerTypeCategoryEdgeCases:
    """Test edge cases and error conditions for EnumHandlerTypeCategory."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumHandlerTypeCategory(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumHandlerTypeCategory("")

    def test_enum_with_whitespace(self) -> None:
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumHandlerTypeCategory(" compute ")

        with pytest.raises(ValueError):
            EnumHandlerTypeCategory("compute ")

        with pytest.raises(ValueError):
            EnumHandlerTypeCategory(" effect")

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumHandlerTypeCategory:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        category = EnumHandlerTypeCategory.COMPUTE

        # Shallow copy should return the same object
        shallow_copy = copy.copy(category)
        assert shallow_copy is category

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(category)
        assert deep_copy is category

    def test_enum_ordering_behavior(self) -> None:
        """Test that enum members support ordering (inherits from str)."""
        # Since EnumHandlerTypeCategory(str, Enum), it supports string ordering
        result1 = EnumHandlerTypeCategory.COMPUTE < EnumHandlerTypeCategory.EFFECT
        result2 = EnumHandlerTypeCategory.COMPUTE > EnumHandlerTypeCategory.EFFECT

        # The results depend on string comparison of the values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)


@pytest.mark.unit
class TestEnumHandlerTypeCategoryPropertyBased:
    """Property-based tests using hypothesis for EnumHandlerTypeCategory."""

    def test_all_categories_have_valid_string_representation(self) -> None:
        """Property: Every EnumHandlerTypeCategory value has a non-empty string representation."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerTypeCategory)))
        def check_string_representation(category: EnumHandlerTypeCategory) -> None:
            string_repr = str(category)
            assert isinstance(string_repr, str)
            assert len(string_repr) > 0
            assert string_repr == category.value

        check_string_representation()

    def test_all_categories_roundtrip_through_value(self) -> None:
        """Property: Every EnumHandlerTypeCategory can be reconstructed from its value."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerTypeCategory)))
        def check_roundtrip(category: EnumHandlerTypeCategory) -> None:
            value = category.value
            reconstructed = EnumHandlerTypeCategory(value)
            assert reconstructed == category
            assert reconstructed is category  # Same singleton instance

        check_roundtrip()

    def test_json_serialization_roundtrip(self) -> None:
        """Property: Every EnumHandlerTypeCategory survives JSON serialization roundtrip."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerTypeCategory)))
        def check_json_roundtrip(category: EnumHandlerTypeCategory) -> None:
            serialized = json.dumps(category.value)
            deserialized = json.loads(serialized)
            reconstructed = EnumHandlerTypeCategory(deserialized)
            assert reconstructed == category

        check_json_roundtrip()

    def test_pickle_serialization_preserves_identity(self) -> None:
        """Property: Pickle serialization preserves enum identity."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerTypeCategory)))
        def check_pickle_identity(category: EnumHandlerTypeCategory) -> None:
            pickled = pickle.dumps(category)
            unpickled = pickle.loads(pickled)
            assert unpickled == category
            assert unpickled is category  # Same singleton

        check_pickle_identity()

    def test_values_classmethod_includes_all_members(self) -> None:
        """Property: values() classmethod includes all enum members."""
        from hypothesis import given
        from hypothesis import strategies as st

        all_values = EnumHandlerTypeCategory.values()

        @given(st.sampled_from(list(EnumHandlerTypeCategory)))
        def check_in_values(category: EnumHandlerTypeCategory) -> None:
            assert category.value in all_values

        check_in_values()


@pytest.mark.unit
class TestEnumHandlerTypeCategoryExhaustivenessCheck:
    """Test exhaustiveness pattern for match statements."""

    def test_exhaustive_match_pattern(self) -> None:
        """Test that all categories can be matched exhaustively."""

        def categorize(category: EnumHandlerTypeCategory) -> str:
            match category:
                case EnumHandlerTypeCategory.COMPUTE:
                    return "pure_deterministic"
                case EnumHandlerTypeCategory.EFFECT:
                    return "side_effecting"
                case EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE:
                    return "pure_nondeterministic"
                case _:
                    EnumHandlerTypeCategory.assert_exhaustive(category)

        # Test all categories are handled
        assert categorize(EnumHandlerTypeCategory.COMPUTE) == "pure_deterministic"
        assert categorize(EnumHandlerTypeCategory.EFFECT) == "side_effecting"
        assert (
            categorize(EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE)
            == "pure_nondeterministic"
        )

    def test_all_values_list_matches_iteration(self) -> None:
        """Test that values() classmethod returns same values as iteration."""
        iterated_values = [member.value for member in EnumHandlerTypeCategory]
        classmethod_values = EnumHandlerTypeCategory.values()

        assert set(iterated_values) == set(classmethod_values)
        assert len(iterated_values) == len(classmethod_values)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
