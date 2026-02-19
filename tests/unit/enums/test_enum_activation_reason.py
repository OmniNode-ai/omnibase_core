# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumActivationReason.

Tests all aspects of the activation reason enumeration including:
- Value validation and integrity
- Activation vs skip reason classification
- String conversion and comparison
- Enum member existence and uniqueness
- Serialization/deserialization
- Helper methods (is_activation_reason, is_skip_reason, get_*_reasons)
- Pydantic model compatibility
- Edge cases and error conditions

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import copy
import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_activation_reason import EnumActivationReason


@pytest.mark.unit
class TestEnumActivationReasonBasic:
    """Test cases for EnumActivationReason basic functionality."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumActivationReason properly inherits from str and Enum."""
        assert issubclass(EnumActivationReason, str)
        assert issubclass(EnumActivationReason, Enum)

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = [
            # Activation reasons
            "PREDICATE_TRUE",
            "ALWAYS_ACTIVE",
            "EXPLICITLY_ENABLED",
            "DEPENDENCY_SATISFIED",
            # Skip reasons
            "PREDICATE_FALSE",
            "DEPENDENCY_FAILED",
            "EXPLICITLY_DISABLED",
            "CAPABILITY_MISSING",
            "CONFLICT_DETECTED",
            "PHASE_MISMATCH",
            "TIMEOUT_EXCEEDED",
        ]

        for value in expected_values:
            assert hasattr(EnumActivationReason, value), f"Missing enum value: {value}"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumActivationReason.PREDICATE_TRUE: "predicate_true",
            EnumActivationReason.ALWAYS_ACTIVE: "always_active",
            EnumActivationReason.EXPLICITLY_ENABLED: "explicitly_enabled",
            EnumActivationReason.DEPENDENCY_SATISFIED: "dependency_satisfied",
            EnumActivationReason.PREDICATE_FALSE: "predicate_false",
            EnumActivationReason.DEPENDENCY_FAILED: "dependency_failed",
            EnumActivationReason.EXPLICITLY_DISABLED: "explicitly_disabled",
            EnumActivationReason.CAPABILITY_MISSING: "capability_missing",
            EnumActivationReason.CONFLICT_DETECTED: "conflict_detected",
            EnumActivationReason.PHASE_MISMATCH: "phase_mismatch",
            EnumActivationReason.TIMEOUT_EXCEEDED: "timeout_exceeded",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_member_count(self) -> None:
        """Test that the enum has the expected number of members."""
        expected_count = 11  # 4 activation + 7 skip
        actual_count = len(list(EnumActivationReason))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumActivationReason]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"


@pytest.mark.unit
class TestEnumActivationReasonClassification:
    """Test cases for activation vs skip reason classification."""

    def test_activation_reasons_are_classified_correctly(self) -> None:
        """Test that activation reasons return True for is_activation_reason()."""
        activation_reasons = [
            EnumActivationReason.PREDICATE_TRUE,
            EnumActivationReason.ALWAYS_ACTIVE,
            EnumActivationReason.EXPLICITLY_ENABLED,
            EnumActivationReason.DEPENDENCY_SATISFIED,
        ]

        for reason in activation_reasons:
            assert reason.is_activation_reason(), (
                f"{reason} should be an activation reason"
            )
            assert not reason.is_skip_reason(), f"{reason} should not be a skip reason"

    def test_skip_reasons_are_classified_correctly(self) -> None:
        """Test that skip reasons return True for is_skip_reason()."""
        skip_reasons = [
            EnumActivationReason.PREDICATE_FALSE,
            EnumActivationReason.DEPENDENCY_FAILED,
            EnumActivationReason.EXPLICITLY_DISABLED,
            EnumActivationReason.CAPABILITY_MISSING,
            EnumActivationReason.CONFLICT_DETECTED,
            EnumActivationReason.PHASE_MISMATCH,
            EnumActivationReason.TIMEOUT_EXCEEDED,
        ]

        for reason in skip_reasons:
            assert reason.is_skip_reason(), f"{reason} should be a skip reason"
            assert not reason.is_activation_reason(), (
                f"{reason} should not be an activation reason"
            )

    def test_get_activation_reasons_returns_correct_list(self) -> None:
        """Test that get_activation_reasons() returns all activation reasons."""
        activation_reasons = EnumActivationReason.get_activation_reasons()

        expected = [
            EnumActivationReason.PREDICATE_TRUE,
            EnumActivationReason.ALWAYS_ACTIVE,
            EnumActivationReason.EXPLICITLY_ENABLED,
            EnumActivationReason.DEPENDENCY_SATISFIED,
        ]

        assert activation_reasons == expected
        assert len(activation_reasons) == 4

    def test_get_skip_reasons_returns_correct_list(self) -> None:
        """Test that get_skip_reasons() returns all skip reasons."""
        skip_reasons = EnumActivationReason.get_skip_reasons()

        expected = [
            EnumActivationReason.PREDICATE_FALSE,
            EnumActivationReason.DEPENDENCY_FAILED,
            EnumActivationReason.EXPLICITLY_DISABLED,
            EnumActivationReason.CAPABILITY_MISSING,
            EnumActivationReason.CONFLICT_DETECTED,
            EnumActivationReason.PHASE_MISMATCH,
            EnumActivationReason.TIMEOUT_EXCEEDED,
        ]

        assert skip_reasons == expected
        assert len(skip_reasons) == 7

    def test_all_reasons_are_either_activation_or_skip(self) -> None:
        """Test that every reason is classified as either activation or skip."""
        for reason in EnumActivationReason:
            is_activation = reason.is_activation_reason()
            is_skip = reason.is_skip_reason()

            # Must be one or the other, not both
            assert is_activation != is_skip, (
                f"{reason} must be either activation or skip, not both"
            )

    def test_get_reasons_lists_cover_all_members(self) -> None:
        """Test that activation + skip reasons cover all enum members."""
        activation = set(EnumActivationReason.get_activation_reasons())
        skip = set(EnumActivationReason.get_skip_reasons())
        all_reasons = set(EnumActivationReason)

        assert activation | skip == all_reasons, (
            "Activation and skip reasons should cover all members"
        )
        assert activation & skip == set(), (
            "Activation and skip reasons should not overlap"
        )


@pytest.mark.unit
class TestEnumActivationReasonSerialization:
    """Test cases for serialization and deserialization."""

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        assert EnumActivationReason("predicate_true") == (
            EnumActivationReason.PREDICATE_TRUE
        )
        assert EnumActivationReason("always_active") == (
            EnumActivationReason.ALWAYS_ACTIVE
        )
        assert EnumActivationReason("predicate_false") == (
            EnumActivationReason.PREDICATE_FALSE
        )
        assert EnumActivationReason("dependency_failed") == (
            EnumActivationReason.DEPENDENCY_FAILED
        )

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings."""
        assert EnumActivationReason.PREDICATE_TRUE == "predicate_true"
        assert EnumActivationReason.ALWAYS_ACTIVE == "always_active"
        assert EnumActivationReason.PREDICATE_FALSE == "predicate_false"
        assert EnumActivationReason.CONFLICT_DETECTED == "conflict_detected"

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumActivationReason:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            reconstructed = EnumActivationReason(deserialized)
            assert reconstructed == member

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            reason: EnumActivationReason

        # Test valid values
        model = TestModel(reason=EnumActivationReason.PREDICATE_TRUE)
        assert model.reason == EnumActivationReason.PREDICATE_TRUE

        # Test string initialization
        model = TestModel(reason="always_active")
        assert model.reason == EnumActivationReason.ALWAYS_ACTIVE

        # Test serialization
        data = model.model_dump()
        assert data["reason"] == "always_active"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.reason == EnumActivationReason.ALWAYS_ACTIVE

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumActivationReason:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object


@pytest.mark.unit
class TestEnumActivationReasonBehavior:
    """Test cases for general enum behavior."""

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        expected_values = {
            "predicate_true",
            "always_active",
            "explicitly_enabled",
            "dependency_satisfied",
            "predicate_false",
            "dependency_failed",
            "explicitly_disabled",
            "capability_missing",
            "conflict_detected",
            "phase_mismatch",
            "timeout_exceeded",
        }
        actual_values = {member.value for member in EnumActivationReason}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumActivationReason("INVALID_REASON")

    def test_enum_in_operator(self) -> None:
        """Test that 'in' operator works with enum."""
        assert EnumActivationReason.PREDICATE_TRUE in EnumActivationReason
        assert EnumActivationReason.CONFLICT_DETECTED in EnumActivationReason

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        reason_set = {
            EnumActivationReason.PREDICATE_TRUE,
            EnumActivationReason.PREDICATE_FALSE,
        }
        assert len(reason_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumActivationReason.ALWAYS_ACTIVE) == hash(
            EnumActivationReason.ALWAYS_ACTIVE
        )

    def test_enum_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumActivationReason.PREDICATE_TRUE) == (
            "<EnumActivationReason.PREDICATE_TRUE: 'predicate_true'>"
        )
        assert repr(EnumActivationReason.CONFLICT_DETECTED) == (
            "<EnumActivationReason.CONFLICT_DETECTED: 'conflict_detected'>"
        )

    def test_enum_str_method(self) -> None:
        """Test the __str__ method returns the value."""
        assert str(EnumActivationReason.PREDICATE_TRUE) == "predicate_true"
        assert str(EnumActivationReason.ALWAYS_ACTIVE) == "always_active"
        assert str(EnumActivationReason.CONFLICT_DETECTED) == "conflict_detected"

    def test_enum_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumActivationReason:
            assert bool(member) is True

    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumActivationReason("PREDICATE_TRUE")  # Should be "predicate_true"

        with pytest.raises(ValueError):
            EnumActivationReason("Predicate_True")  # Should be "predicate_true"

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert (
            EnumActivationReason.PREDICATE_TRUE is EnumActivationReason.PREDICATE_TRUE
        )

        # Different enum members should not be identical
        assert (
            EnumActivationReason.PREDICATE_TRUE
            is not EnumActivationReason.PREDICATE_FALSE
        )

        # Equality with strings should work
        assert EnumActivationReason.PREDICATE_TRUE == "predicate_true"
        assert EnumActivationReason.PREDICATE_TRUE != "predicate_false"

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        reason = EnumActivationReason.PREDICATE_TRUE
        assert isinstance(reason, str)
        assert reason == "predicate_true"
        assert len(reason) == 14
        assert reason.startswith("predicate")

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert "activation" in EnumActivationReason.__doc__.lower()
        assert "skip" in EnumActivationReason.__doc__.lower()


@pytest.mark.unit
class TestEnumActivationReasonEdgeCases:
    """Test edge cases and error conditions."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumActivationReason(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumActivationReason("")

    def test_enum_with_whitespace(self) -> None:
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumActivationReason(" predicate_true ")

        with pytest.raises(ValueError):
            EnumActivationReason("predicate_true ")

        with pytest.raises(ValueError):
            EnumActivationReason(" always_active")

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        reason = EnumActivationReason.PREDICATE_TRUE

        # Shallow copy should return the same object
        shallow_copy = copy.copy(reason)
        assert shallow_copy is reason

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(reason)
        assert deep_copy is reason

    def test_membership_testing(self) -> None:
        """Test membership testing with string values."""
        assert "predicate_true" in EnumActivationReason
        assert "always_active" in EnumActivationReason
        assert "predicate_false" in EnumActivationReason
        assert "conflict_detected" in EnumActivationReason
        assert "invalid" not in EnumActivationReason


@pytest.mark.unit
class TestEnumActivationReasonSemantics:
    """Test semantic relationships between reasons."""

    def test_predicate_true_false_are_inverses(self) -> None:
        """Test that PREDICATE_TRUE and PREDICATE_FALSE are logical inverses."""
        assert EnumActivationReason.PREDICATE_TRUE.is_activation_reason()
        assert EnumActivationReason.PREDICATE_FALSE.is_skip_reason()

    def test_explicitly_enabled_disabled_are_inverses(self) -> None:
        """Test that EXPLICITLY_ENABLED and EXPLICITLY_DISABLED are inverses."""
        assert EnumActivationReason.EXPLICITLY_ENABLED.is_activation_reason()
        assert EnumActivationReason.EXPLICITLY_DISABLED.is_skip_reason()

    def test_dependency_satisfied_failed_are_inverses(self) -> None:
        """Test that DEPENDENCY_SATISFIED and DEPENDENCY_FAILED are inverses."""
        assert EnumActivationReason.DEPENDENCY_SATISFIED.is_activation_reason()
        assert EnumActivationReason.DEPENDENCY_FAILED.is_skip_reason()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
