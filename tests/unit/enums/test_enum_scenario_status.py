# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumScenarioStatus.

Tests all aspects of the scenario status enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Edge cases and error conditions
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_scenario_status import EnumScenarioStatus


@pytest.mark.unit
class TestEnumScenarioStatus:
    """Test cases for EnumScenarioStatus."""

    def test_enum_inherits_from_str_and_enum(self):
        """Test that EnumScenarioStatus properly inherits from str and Enum."""
        assert issubclass(EnumScenarioStatus, str)
        assert issubclass(EnumScenarioStatus, Enum)

    def test_enum_values_exist(self):
        """Test that all expected enum values exist."""
        expected_values = [
            "NOT_EXECUTED",
            "QUEUED",
            "RUNNING",
            "COMPLETED",
            "FAILED",
            "SKIPPED",
        ]

        for value in expected_values:
            assert hasattr(EnumScenarioStatus, value), f"Missing enum value: {value}"

    def test_enum_string_values(self):
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumScenarioStatus.NOT_EXECUTED: "not_executed",
            EnumScenarioStatus.QUEUED: "queued",
            EnumScenarioStatus.RUNNING: "running",
            EnumScenarioStatus.COMPLETED: "completed",
            EnumScenarioStatus.FAILED: "failed",
            EnumScenarioStatus.SKIPPED: "skipped",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_can_be_created_from_string(self):
        """Test that enum members can be created from string values."""
        assert EnumScenarioStatus("not_executed") == EnumScenarioStatus.NOT_EXECUTED
        assert EnumScenarioStatus("queued") == EnumScenarioStatus.QUEUED
        assert EnumScenarioStatus("running") == EnumScenarioStatus.RUNNING
        assert EnumScenarioStatus("completed") == EnumScenarioStatus.COMPLETED
        assert EnumScenarioStatus("failed") == EnumScenarioStatus.FAILED
        assert EnumScenarioStatus("skipped") == EnumScenarioStatus.SKIPPED

    def test_enum_string_comparison(self):
        """Test that enum members can be compared with strings."""
        assert EnumScenarioStatus.NOT_EXECUTED == "not_executed"
        assert EnumScenarioStatus.QUEUED == "queued"
        assert EnumScenarioStatus.RUNNING == "running"
        assert EnumScenarioStatus.COMPLETED == "completed"
        assert EnumScenarioStatus.FAILED == "failed"
        assert EnumScenarioStatus.SKIPPED == "skipped"

    def test_enum_member_count(self):
        """Test that the enum has the expected number of members."""
        expected_count = 6
        actual_count = len(list(EnumScenarioStatus))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self):
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumScenarioStatus]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        expected_values = {
            "not_executed",
            "queued",
            "running",
            "completed",
            "failed",
            "skipped",
        }
        actual_values = {member.value for member in EnumScenarioStatus}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self):
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumScenarioStatus("invalid_status")

    def test_enum_in_operator(self):
        """Test that 'in' operator works with enum."""
        assert EnumScenarioStatus.NOT_EXECUTED in EnumScenarioStatus
        assert EnumScenarioStatus.COMPLETED in EnumScenarioStatus

    def test_enum_hash_consistency(self):
        """Test that enum members are hashable and consistent."""
        status_set = {EnumScenarioStatus.RUNNING, EnumScenarioStatus.COMPLETED}
        assert len(status_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumScenarioStatus.RUNNING) == hash(EnumScenarioStatus.RUNNING)

    def test_enum_repr(self):
        """Test that enum members have proper string representation."""
        assert (
            repr(EnumScenarioStatus.NOT_EXECUTED)
            == "<EnumScenarioStatus.NOT_EXECUTED: 'not_executed'>"
        )
        assert (
            repr(EnumScenarioStatus.COMPLETED)
            == "<EnumScenarioStatus.COMPLETED: 'completed'>"
        )

    def test_enum_with_pydantic_compatibility(self):
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            status: EnumScenarioStatus

        # Test valid values
        model = TestModel(status=EnumScenarioStatus.RUNNING)
        assert model.status == EnumScenarioStatus.RUNNING

        # Test string initialization
        model = TestModel(status="completed")
        assert model.status == EnumScenarioStatus.COMPLETED

        # Test serialization
        data = model.model_dump()
        assert data["status"] == "completed"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.status == EnumScenarioStatus.COMPLETED

    def test_scenario_status_lifecycle_grouping(self):
        """Test semantic grouping of scenario statuses by lifecycle."""
        # Initial states
        initial_states = {EnumScenarioStatus.NOT_EXECUTED}

        # Pending states
        pending_states = {EnumScenarioStatus.QUEUED}

        # Active states
        active_states = {EnumScenarioStatus.RUNNING}

        # Final states
        final_states = {
            EnumScenarioStatus.COMPLETED,
            EnumScenarioStatus.FAILED,
            EnumScenarioStatus.SKIPPED,
        }

        all_states = initial_states | pending_states | active_states | final_states
        actual_states = set(EnumScenarioStatus)

        assert all_states == actual_states, (
            "Scenario status lifecycle categorization is complete"
        )

    def test_scenario_status_execution_outcomes(self):
        """Test categorization by execution outcomes."""
        # Success outcomes
        success_outcomes = {EnumScenarioStatus.COMPLETED}

        # Failure outcomes
        failure_outcomes = {EnumScenarioStatus.FAILED}

        # Neutral outcomes
        neutral_outcomes = {EnumScenarioStatus.SKIPPED}

        # In-progress or pending
        non_final_states = {
            EnumScenarioStatus.NOT_EXECUTED,
            EnumScenarioStatus.QUEUED,
            EnumScenarioStatus.RUNNING,
        }

        all_outcomes = (
            success_outcomes | failure_outcomes | neutral_outcomes | non_final_states
        )
        actual_states = set(EnumScenarioStatus)

        assert all_outcomes == actual_states, (
            "All scenario statuses are categorized by outcome"
        )

    def test_is_final_state_logic(self):
        """Test logic for determining if a status represents a final state."""
        final_states = {
            EnumScenarioStatus.COMPLETED,
            EnumScenarioStatus.FAILED,
            EnumScenarioStatus.SKIPPED,
        }

        non_final_states = {
            EnumScenarioStatus.NOT_EXECUTED,
            EnumScenarioStatus.QUEUED,
            EnumScenarioStatus.RUNNING,
        }

        # These sets should be mutually exclusive and cover all statuses
        assert final_states.isdisjoint(non_final_states)
        assert final_states | non_final_states == set(EnumScenarioStatus)

    def test_enum_case_sensitivity(self):
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumScenarioStatus("COMPLETED")  # Should be "completed"

        with pytest.raises(ValueError):
            EnumScenarioStatus("Completed")  # Should be "completed"

    def test_enum_serialization_json_compatible(self):
        """Test that enum values are JSON serializable."""
        import json

        for member in EnumScenarioStatus:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumScenarioStatus(deserialized)
            assert reconstructed == member


@pytest.mark.unit
class TestEnumScenarioStatusEdgeCases:
    """Test edge cases and error conditions for EnumScenarioStatus."""

    def test_enum_with_none_value(self):
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumScenarioStatus(None)

    def test_enum_with_empty_string(self):
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumScenarioStatus("")

    def test_enum_with_whitespace(self):
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumScenarioStatus(" running ")

    def test_enum_pickling(self):
        """Test that enum members can be pickled and unpickled."""
        import importlib
        import pickle

        # Re-import the enum module to ensure consistent class reference
        # This fixes pickle issues in pytest-xdist where module caching
        # can cause enum identity mismatches across worker processes
        enum_module = importlib.import_module(
            "omnibase_core.enums.enum_scenario_status"
        )
        EnumClass = enum_module.EnumScenarioStatus

        for member in EnumClass:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            # Identity check - enum members should be singletons
            assert unpickled is member

    def test_enum_workflow_transitions(self):
        """Test that enum supports typical workflow transitions."""
        # Test common transition patterns
        typical_flow = [
            EnumScenarioStatus.NOT_EXECUTED,
            EnumScenarioStatus.QUEUED,
            EnumScenarioStatus.RUNNING,
            EnumScenarioStatus.COMPLETED,
        ]

        # Ensure all states in typical flow exist
        for status in typical_flow:
            assert status in EnumScenarioStatus

        # Alternative ending states
        alternative_endings = [EnumScenarioStatus.FAILED, EnumScenarioStatus.SKIPPED]
        for status in alternative_endings:
            assert status in EnumScenarioStatus


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
