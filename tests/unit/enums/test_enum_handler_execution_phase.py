# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for EnumHandlerExecutionPhase.

Tests all aspects of the handler execution phase enumeration including:
- Value validation and integrity
- Alignment with DEFAULT_EXECUTION_PHASES
- Ordering and phase comparison
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Helper methods (get_ordered_phases, get_phase_index, is_before, is_after)
- Pydantic model compatibility
- Edge cases and error conditions
"""

import copy
import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
)


@pytest.mark.unit
class TestEnumHandlerExecutionPhase:
    """Test cases for EnumHandlerExecutionPhase basic functionality."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumHandlerExecutionPhase properly inherits from str and Enum."""
        assert issubclass(EnumHandlerExecutionPhase, str)
        assert issubclass(EnumHandlerExecutionPhase, Enum)

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = [
            "PREFLIGHT",
            "BEFORE",
            "EXECUTE",
            "AFTER",
            "EMIT",
            "FINALIZE",
        ]

        for value in expected_values:
            assert hasattr(EnumHandlerExecutionPhase, value), (
                f"Missing enum value: {value}"
            )

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumHandlerExecutionPhase.PREFLIGHT: "preflight",
            EnumHandlerExecutionPhase.BEFORE: "before",
            EnumHandlerExecutionPhase.EXECUTE: "execute",
            EnumHandlerExecutionPhase.AFTER: "after",
            EnumHandlerExecutionPhase.EMIT: "emit",
            EnumHandlerExecutionPhase.FINALIZE: "finalize",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_member_count(self) -> None:
        """Test that the enum has the expected number of members."""
        expected_count = 6
        actual_count = len(list(EnumHandlerExecutionPhase))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumHandlerExecutionPhase]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"


@pytest.mark.unit
class TestEnumHandlerExecutionPhaseAlignment:
    """Test cases for alignment with DEFAULT_EXECUTION_PHASES."""

    def test_alignment_with_default_execution_phases(self) -> None:
        """Test that enum values match DEFAULT_EXECUTION_PHASES exactly."""
        # Use tuple to match DEFAULT_EXECUTION_PHASES type (tuple for immutability)
        enum_values = tuple(phase.value for phase in EnumHandlerExecutionPhase)
        assert enum_values == DEFAULT_EXECUTION_PHASES, (
            f"Enum values {enum_values} must match DEFAULT_EXECUTION_PHASES "
            f"{DEFAULT_EXECUTION_PHASES}"
        )

    def test_all_default_phases_have_enum_member(self) -> None:
        """Test that every DEFAULT_EXECUTION_PHASE has a corresponding enum member."""
        for phase_str in DEFAULT_EXECUTION_PHASES:
            try:
                phase_enum = EnumHandlerExecutionPhase(phase_str)
                assert phase_enum.value == phase_str
            except ValueError:
                pytest.fail(f"DEFAULT_EXECUTION_PHASE '{phase_str}' has no enum member")

    def test_phase_count_matches_default(self) -> None:
        """Test that enum count matches DEFAULT_EXECUTION_PHASES count."""
        assert len(EnumHandlerExecutionPhase) == len(DEFAULT_EXECUTION_PHASES)

    def test_get_ordered_phases_matches_default(self) -> None:
        """Test that get_ordered_phases() returns phases in DEFAULT order."""
        ordered_phases = EnumHandlerExecutionPhase.get_ordered_phases()
        # Use tuple to match DEFAULT_EXECUTION_PHASES type (tuple for immutability)
        ordered_values = tuple(phase.value for phase in ordered_phases)
        assert ordered_values == DEFAULT_EXECUTION_PHASES


@pytest.mark.unit
class TestEnumHandlerExecutionPhaseOrdering:
    """Test cases for phase ordering functionality."""

    def test_preflight_is_first(self) -> None:
        """Test that PREFLIGHT is the first phase."""
        assert (
            EnumHandlerExecutionPhase.get_phase_index(
                EnumHandlerExecutionPhase.PREFLIGHT
            )
            == 0
        )

    def test_finalize_is_last(self) -> None:
        """Test that FINALIZE is the last phase."""
        phases = EnumHandlerExecutionPhase.get_ordered_phases()
        assert phases[-1] == EnumHandlerExecutionPhase.FINALIZE

    def test_complete_ordering(self) -> None:
        """Test the complete ordering: PREFLIGHT < BEFORE < EXECUTE < AFTER < EMIT < FINALIZE."""
        phases = EnumHandlerExecutionPhase.get_ordered_phases()
        expected_order = [
            EnumHandlerExecutionPhase.PREFLIGHT,
            EnumHandlerExecutionPhase.BEFORE,
            EnumHandlerExecutionPhase.EXECUTE,
            EnumHandlerExecutionPhase.AFTER,
            EnumHandlerExecutionPhase.EMIT,
            EnumHandlerExecutionPhase.FINALIZE,
        ]
        assert phases == expected_order

    def test_is_before_method(self) -> None:
        """Test the is_before() method for all phase pairs."""
        preflight = EnumHandlerExecutionPhase.PREFLIGHT
        before = EnumHandlerExecutionPhase.BEFORE
        execute = EnumHandlerExecutionPhase.EXECUTE
        after = EnumHandlerExecutionPhase.AFTER
        emit = EnumHandlerExecutionPhase.EMIT
        finalize = EnumHandlerExecutionPhase.FINALIZE

        # PREFLIGHT is before all others
        assert preflight.is_before(before)
        assert preflight.is_before(execute)
        assert preflight.is_before(after)
        assert preflight.is_before(emit)
        assert preflight.is_before(finalize)

        # EXECUTE is before AFTER, EMIT, FINALIZE but not PREFLIGHT, BEFORE
        assert not execute.is_before(preflight)
        assert not execute.is_before(before)
        assert execute.is_before(after)
        assert execute.is_before(emit)
        assert execute.is_before(finalize)

        # FINALIZE is not before any phase
        assert not finalize.is_before(preflight)
        assert not finalize.is_before(before)
        assert not finalize.is_before(execute)
        assert not finalize.is_before(after)
        assert not finalize.is_before(emit)

    def test_is_after_method(self) -> None:
        """Test the is_after() method for all phase pairs."""
        preflight = EnumHandlerExecutionPhase.PREFLIGHT
        before = EnumHandlerExecutionPhase.BEFORE
        execute = EnumHandlerExecutionPhase.EXECUTE
        after = EnumHandlerExecutionPhase.AFTER
        emit = EnumHandlerExecutionPhase.EMIT
        finalize = EnumHandlerExecutionPhase.FINALIZE

        # FINALIZE is after all others
        assert finalize.is_after(preflight)
        assert finalize.is_after(before)
        assert finalize.is_after(execute)
        assert finalize.is_after(after)
        assert finalize.is_after(emit)

        # EXECUTE is after PREFLIGHT, BEFORE but not AFTER, EMIT, FINALIZE
        assert execute.is_after(preflight)
        assert execute.is_after(before)
        assert not execute.is_after(after)
        assert not execute.is_after(emit)
        assert not execute.is_after(finalize)

        # PREFLIGHT is not after any phase
        assert not preflight.is_after(before)
        assert not preflight.is_after(execute)
        assert not preflight.is_after(after)
        assert not preflight.is_after(emit)
        assert not preflight.is_after(finalize)

    def test_same_phase_not_before_or_after_itself(self) -> None:
        """Test that a phase is neither before nor after itself."""
        for phase in EnumHandlerExecutionPhase:
            assert not phase.is_before(phase)
            assert not phase.is_after(phase)

    def test_phase_index_values(self) -> None:
        """Test that phase indices are sequential starting from 0."""
        expected_indices = {
            EnumHandlerExecutionPhase.PREFLIGHT: 0,
            EnumHandlerExecutionPhase.BEFORE: 1,
            EnumHandlerExecutionPhase.EXECUTE: 2,
            EnumHandlerExecutionPhase.AFTER: 3,
            EnumHandlerExecutionPhase.EMIT: 4,
            EnumHandlerExecutionPhase.FINALIZE: 5,
        }

        for phase, expected_index in expected_indices.items():
            actual_index = EnumHandlerExecutionPhase.get_phase_index(phase)
            assert actual_index == expected_index, (
                f"Phase {phase} should have index {expected_index}, got {actual_index}"
            )


@pytest.mark.unit
class TestEnumHandlerExecutionPhaseSerialization:
    """Test cases for serialization and deserialization."""

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        assert EnumHandlerExecutionPhase("preflight") == (
            EnumHandlerExecutionPhase.PREFLIGHT
        )
        assert EnumHandlerExecutionPhase("before") == EnumHandlerExecutionPhase.BEFORE
        assert EnumHandlerExecutionPhase("execute") == EnumHandlerExecutionPhase.EXECUTE
        assert EnumHandlerExecutionPhase("after") == EnumHandlerExecutionPhase.AFTER
        assert EnumHandlerExecutionPhase("emit") == EnumHandlerExecutionPhase.EMIT
        assert EnumHandlerExecutionPhase("finalize") == (
            EnumHandlerExecutionPhase.FINALIZE
        )

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings.

        Note: This enum uses the `str, Enum` pattern (not StrEnum), which means
        members ARE equal to their string values at runtime. However, mypy cannot
        statically verify this. Type ignores are appropriate here.
        """
        # str, Enum values are equal to their string values at runtime
        assert EnumHandlerExecutionPhase.PREFLIGHT == "preflight"  # type: ignore[comparison-overlap]
        assert EnumHandlerExecutionPhase.BEFORE == "before"  # type: ignore[comparison-overlap]
        assert EnumHandlerExecutionPhase.EXECUTE == "execute"  # type: ignore[comparison-overlap]
        assert EnumHandlerExecutionPhase.AFTER == "after"  # type: ignore[comparison-overlap]
        assert EnumHandlerExecutionPhase.EMIT == "emit"  # type: ignore[comparison-overlap]
        assert EnumHandlerExecutionPhase.FINALIZE == "finalize"  # type: ignore[comparison-overlap]

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumHandlerExecutionPhase:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumHandlerExecutionPhase(deserialized)
            assert reconstructed == member

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            phase: EnumHandlerExecutionPhase

        # Test valid values
        model = TestModel(phase=EnumHandlerExecutionPhase.EXECUTE)
        assert model.phase == EnumHandlerExecutionPhase.EXECUTE

        # Test string initialization (Pydantic coerces string to enum at runtime)
        model = TestModel(phase="before")  # type: ignore[arg-type]
        assert model.phase == EnumHandlerExecutionPhase.BEFORE

        # Test serialization
        data = model.model_dump()
        assert data["phase"] == "before"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.phase == EnumHandlerExecutionPhase.BEFORE

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumHandlerExecutionPhase:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object


@pytest.mark.unit
class TestEnumHandlerExecutionPhaseBehavior:
    """Test cases for general enum behavior."""

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        expected_values = {
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        }
        actual_values = {member.value for member in EnumHandlerExecutionPhase}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase("INVALID_PHASE")

    def test_enum_in_operator(self) -> None:
        """Test that 'in' operator works with enum."""
        assert EnumHandlerExecutionPhase.PREFLIGHT in EnumHandlerExecutionPhase
        assert EnumHandlerExecutionPhase.FINALIZE in EnumHandlerExecutionPhase

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        phase_set = {
            EnumHandlerExecutionPhase.PREFLIGHT,
            EnumHandlerExecutionPhase.FINALIZE,
        }
        assert len(phase_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumHandlerExecutionPhase.EXECUTE) == hash(
            EnumHandlerExecutionPhase.EXECUTE
        )

    def test_enum_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumHandlerExecutionPhase.PREFLIGHT) == (
            "<EnumHandlerExecutionPhase.PREFLIGHT: 'preflight'>"
        )
        assert repr(EnumHandlerExecutionPhase.FINALIZE) == (
            "<EnumHandlerExecutionPhase.FINALIZE: 'finalize'>"
        )

    def test_enum_str_method(self) -> None:
        """Test the __str__ method returns the value."""
        assert str(EnumHandlerExecutionPhase.PREFLIGHT) == "preflight"
        assert str(EnumHandlerExecutionPhase.EXECUTE) == "execute"
        assert str(EnumHandlerExecutionPhase.FINALIZE) == "finalize"

    def test_enum_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumHandlerExecutionPhase:
            assert bool(member) is True

    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase("PREFLIGHT")  # Should be "preflight"

        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase("Preflight")  # Should be "preflight"

        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase("EXECUTE")  # Should be "execute"

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior.

        Note: mypy can statically determine that different enum members are not
        identical, and that `str, Enum` comparisons with strings are type-incompatible.
        These are runtime behavior tests, so type ignores are appropriate.
        """
        # Same enum members should be identical
        assert EnumHandlerExecutionPhase.EXECUTE is EnumHandlerExecutionPhase.EXECUTE

        # Different enum members should not be identical
        # mypy knows these are different at compile time, but we're testing runtime behavior
        assert (
            EnumHandlerExecutionPhase.PREFLIGHT
            is not EnumHandlerExecutionPhase.FINALIZE
        )  # type: ignore[comparison-overlap]

        # Equality with strings should work (str, Enum runtime behavior)
        assert EnumHandlerExecutionPhase.EXECUTE == "execute"  # type: ignore[comparison-overlap]
        assert EnumHandlerExecutionPhase.EXECUTE != "finalize"  # type: ignore[comparison-overlap]

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        phase = EnumHandlerExecutionPhase.FINALIZE
        assert isinstance(phase, str)
        assert phase == "finalize"
        assert len(phase) == 8
        assert phase.startswith("final")

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        docstring = EnumHandlerExecutionPhase.__doc__
        assert docstring is not None, "Enum should have a docstring"
        assert "execution phases" in docstring.lower()
        assert "PREFLIGHT" in docstring
        assert "FINALIZE" in docstring


@pytest.mark.unit
class TestEnumHandlerExecutionPhaseEdgeCases:
    """Test edge cases and error conditions."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumHandlerExecutionPhase(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase("")

    def test_enum_with_whitespace(self) -> None:
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase(" execute ")

        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase("execute ")

        with pytest.raises(ValueError):
            EnumHandlerExecutionPhase(" preflight")

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        phase = EnumHandlerExecutionPhase.EXECUTE

        # Shallow copy should return the same object
        shallow_copy = copy.copy(phase)
        assert shallow_copy is phase

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(phase)
        assert deep_copy is phase

    def test_membership_testing(self) -> None:
        """Test membership testing with string values."""
        assert "preflight" in EnumHandlerExecutionPhase
        assert "before" in EnumHandlerExecutionPhase
        assert "execute" in EnumHandlerExecutionPhase
        assert "after" in EnumHandlerExecutionPhase
        assert "emit" in EnumHandlerExecutionPhase
        assert "finalize" in EnumHandlerExecutionPhase
        assert "invalid" not in EnumHandlerExecutionPhase


@pytest.mark.unit
class TestEnumHandlerExecutionPhasePropertyBased:
    """Property-based tests for EnumHandlerExecutionPhase."""

    def test_all_phases_have_valid_string_representation(self) -> None:
        """Property: Every phase has a non-empty string representation."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerExecutionPhase)))
        def check_string_representation(phase: EnumHandlerExecutionPhase) -> None:
            string_repr = str(phase)
            assert isinstance(string_repr, str)
            assert len(string_repr) > 0
            assert string_repr == phase.value

        check_string_representation()

    def test_all_phases_roundtrip_through_value(self) -> None:
        """Property: Every phase can be reconstructed from its value."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerExecutionPhase)))
        def check_roundtrip(phase: EnumHandlerExecutionPhase) -> None:
            value = phase.value
            reconstructed = EnumHandlerExecutionPhase(value)
            assert reconstructed == phase
            assert reconstructed is phase  # Same singleton instance

        check_roundtrip()

    def test_ordering_transitivity(self) -> None:
        """Property: Phase ordering is transitive (if A < B and B < C, then A < C)."""
        phases = EnumHandlerExecutionPhase.get_ordered_phases()

        for i, phase_a in enumerate(phases):
            for j, phase_b in enumerate(phases):
                for k, phase_c in enumerate(phases):
                    if phase_a.is_before(phase_b) and phase_b.is_before(phase_c):
                        assert phase_a.is_before(phase_c), (
                            f"Transitivity violation: {phase_a} < {phase_b} < {phase_c}"
                        )

    def test_json_serialization_roundtrip(self) -> None:
        """Property: Every phase survives JSON serialization roundtrip."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerExecutionPhase)))
        def check_json_roundtrip(phase: EnumHandlerExecutionPhase) -> None:
            serialized = json.dumps(phase.value)
            deserialized = json.loads(serialized)
            reconstructed = EnumHandlerExecutionPhase(deserialized)
            assert reconstructed == phase

        check_json_roundtrip()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
