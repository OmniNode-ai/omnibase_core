# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for EnumValidationPhase.

Tests all aspects of the validation phase enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Pydantic model compatibility
- Edge cases and error conditions

Related:
    - OMN-1128: Contract Validation Pipeline
"""

import copy
import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_validation_phase import EnumValidationPhase


@pytest.mark.unit
class TestEnumValidationPhase:
    """Test cases for EnumValidationPhase."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumValidationPhase properly inherits from str and Enum."""
        assert issubclass(EnumValidationPhase, str)
        assert issubclass(EnumValidationPhase, Enum)

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = [
            "PATCH",
            "MERGE",
            "EXPANDED",
        ]

        for value in expected_values:
            assert hasattr(EnumValidationPhase, value), f"Missing enum value: {value}"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumValidationPhase.PATCH: "patch",
            EnumValidationPhase.MERGE: "merge",
            EnumValidationPhase.EXPANDED: "expanded",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string


@pytest.mark.unit
class TestEnumValidationPhaseSerialization:
    """Test cases for EnumValidationPhase serialization and deserialization."""

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        assert EnumValidationPhase("patch") == EnumValidationPhase.PATCH
        assert EnumValidationPhase("merge") == EnumValidationPhase.MERGE
        assert EnumValidationPhase("expanded") == EnumValidationPhase.EXPANDED

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings."""
        assert EnumValidationPhase.PATCH == "patch"
        assert EnumValidationPhase.MERGE == "merge"
        assert EnumValidationPhase.EXPANDED == "expanded"

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumValidationPhase:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumValidationPhase(deserialized)
            assert reconstructed == member

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            phase: EnumValidationPhase

        # Test valid values
        model = TestModel(phase=EnumValidationPhase.PATCH)
        assert model.phase == EnumValidationPhase.PATCH

        # Test string initialization
        model = TestModel(phase="merge")
        assert model.phase == EnumValidationPhase.MERGE

        # Test serialization
        data = model.model_dump()
        assert data["phase"] == "merge"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.phase == EnumValidationPhase.MERGE


@pytest.mark.unit
class TestEnumValidationPhaseBehavior:
    """Test cases for EnumValidationPhase general behavior."""

    def test_enum_member_count(self) -> None:
        """Test that the enum has the expected number of members."""
        expected_count = 3
        actual_count = len(list(EnumValidationPhase))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumValidationPhase]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        expected_values = {
            "patch",
            "merge",
            "expanded",
        }
        actual_values = {member.value for member in EnumValidationPhase}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumValidationPhase("INVALID_PHASE")

    def test_enum_in_operator(self) -> None:
        """Test that 'in' operator works with enum."""
        assert EnumValidationPhase.PATCH in EnumValidationPhase
        assert EnumValidationPhase.MERGE in EnumValidationPhase
        assert EnumValidationPhase.EXPANDED in EnumValidationPhase

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        phase_set = {EnumValidationPhase.PATCH, EnumValidationPhase.MERGE}
        assert len(phase_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumValidationPhase.PATCH) == hash(EnumValidationPhase.PATCH)

    def test_enum_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumValidationPhase.PATCH) == "<EnumValidationPhase.PATCH: 'patch'>"
        assert repr(EnumValidationPhase.MERGE) == "<EnumValidationPhase.MERGE: 'merge'>"
        assert repr(EnumValidationPhase.EXPANDED) == (
            "<EnumValidationPhase.EXPANDED: 'expanded'>"
        )

    def test_enum_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumValidationPhase:
            assert bool(member) is True

    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumValidationPhase("PATCH")  # Should be "patch"

        with pytest.raises(ValueError):
            EnumValidationPhase("Patch")  # Should be "patch"

        with pytest.raises(ValueError):
            EnumValidationPhase("MERGE")  # Should be "merge"


@pytest.mark.unit
class TestEnumValidationPhaseEdgeCases:
    """Test edge cases and error conditions for EnumValidationPhase."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumValidationPhase(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumValidationPhase("")

    def test_enum_with_whitespace(self) -> None:
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumValidationPhase(" patch ")

        with pytest.raises(ValueError):
            EnumValidationPhase("patch ")

        with pytest.raises(ValueError):
            EnumValidationPhase(" merge")

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumValidationPhase:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        phase = EnumValidationPhase.EXPANDED

        # Shallow copy should return the same object
        shallow_copy = copy.copy(phase)
        assert shallow_copy is phase

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(phase)
        assert deep_copy is phase

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumValidationPhase.PATCH is EnumValidationPhase.PATCH

        # Different enum members should not be identical
        assert EnumValidationPhase.PATCH is not EnumValidationPhase.MERGE

        # Equality with strings should work
        assert EnumValidationPhase.PATCH == "patch"
        assert EnumValidationPhase.PATCH != "merge"

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        phase = EnumValidationPhase.EXPANDED
        assert isinstance(phase, str)
        assert phase == "expanded"
        assert len(phase) == 8
        assert phase.startswith("expand")


@pytest.mark.unit
class TestEnumValidationPhasePipelineFlow:
    """Test validation pipeline flow semantics."""

    def test_pipeline_order_semantics(self) -> None:
        """Test that phases represent the correct pipeline order."""
        # PATCH -> MERGE -> EXPANDED
        phases = list(EnumValidationPhase)

        # Verify all three phases exist
        assert EnumValidationPhase.PATCH in phases
        assert EnumValidationPhase.MERGE in phases
        assert EnumValidationPhase.EXPANDED in phases

    def test_phase_used_in_validation_results(self) -> None:
        """Test that phases can be used as dictionary keys."""
        results: dict[EnumValidationPhase, bool] = {
            EnumValidationPhase.PATCH: True,
            EnumValidationPhase.MERGE: True,
            EnumValidationPhase.EXPANDED: False,
        }

        assert results[EnumValidationPhase.PATCH] is True
        assert results[EnumValidationPhase.MERGE] is True
        assert results[EnumValidationPhase.EXPANDED] is False

    def test_phase_value_can_be_used_as_dict_key(self) -> None:
        """Test that phase string values work as dictionary keys."""
        results: dict[str, bool] = {
            EnumValidationPhase.PATCH.value: True,
            EnumValidationPhase.MERGE.value: True,
            EnumValidationPhase.EXPANDED.value: False,
        }

        assert results["patch"] is True
        assert results["merge"] is True
        assert results["expanded"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
