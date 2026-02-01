"""Unit tests for EnumScenarioStatusV2.

Tests all aspects of the scenario status enum including:
- Enum value validation
- Status classification methods (is_terminal, is_executing, is_waiting)
- Base status conversion (to_base_status, from_base_status)
- String representation
- JSON serialization compatibility
- Pydantic integration
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_base_status import EnumBaseStatus
from omnibase_core.enums.enum_scenario_status_v2 import (
    EnumScenarioStatus,
    EnumScenarioStatusV2,
)


@pytest.mark.unit
class TestEnumScenarioStatusV2:
    """Test cases for EnumScenarioStatusV2."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        # Base status values
        assert EnumScenarioStatusV2.INACTIVE.value == "inactive"
        assert EnumScenarioStatusV2.ACTIVE.value == "active"
        assert EnumScenarioStatusV2.PENDING.value == "pending"
        assert EnumScenarioStatusV2.RUNNING.value == "running"
        assert EnumScenarioStatusV2.COMPLETED.value == "completed"
        assert EnumScenarioStatusV2.FAILED.value == "failed"
        assert EnumScenarioStatusV2.VALID.value == "valid"
        assert EnumScenarioStatusV2.INVALID.value == "invalid"
        assert EnumScenarioStatusV2.UNKNOWN.value == "unknown"

        # Scenario-specific extensions
        assert EnumScenarioStatusV2.NOT_EXECUTED.value == "not_executed"
        assert EnumScenarioStatusV2.QUEUED.value == "queued"
        assert EnumScenarioStatusV2.SKIPPED.value == "skipped"

    def test_enum_count(self):
        """Test expected number of enum values."""
        assert len(EnumScenarioStatusV2) == 12

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumScenarioStatusV2.RUNNING) == "running"
        assert str(EnumScenarioStatusV2.NOT_EXECUTED) == "not_executed"
        assert str(EnumScenarioStatusV2.SKIPPED) == "skipped"

    def test_is_terminal(self):
        """Test the is_terminal class method."""
        # Terminal statuses
        terminal_statuses = [
            EnumScenarioStatusV2.COMPLETED,
            EnumScenarioStatusV2.FAILED,
            EnumScenarioStatusV2.SKIPPED,
        ]

        for status in terminal_statuses:
            assert EnumScenarioStatusV2.is_terminal(status) is True

        # Non-terminal statuses
        non_terminal_statuses = [
            EnumScenarioStatusV2.INACTIVE,
            EnumScenarioStatusV2.ACTIVE,
            EnumScenarioStatusV2.PENDING,
            EnumScenarioStatusV2.RUNNING,
            EnumScenarioStatusV2.VALID,
            EnumScenarioStatusV2.INVALID,
            EnumScenarioStatusV2.UNKNOWN,
            EnumScenarioStatusV2.NOT_EXECUTED,
            EnumScenarioStatusV2.QUEUED,
        ]

        for status in non_terminal_statuses:
            assert EnumScenarioStatusV2.is_terminal(status) is False

    def test_is_terminal_edge_cases(self):
        """Test is_terminal with edge cases and boundary conditions."""
        # Test that SKIPPED is terminal even though it's not COMPLETED or FAILED
        assert EnumScenarioStatusV2.is_terminal(EnumScenarioStatusV2.SKIPPED) is True

        # Test that VALID/INVALID are not terminal (they're quality states)
        assert EnumScenarioStatusV2.is_terminal(EnumScenarioStatusV2.VALID) is False
        assert EnumScenarioStatusV2.is_terminal(EnumScenarioStatusV2.INVALID) is False

        # Test that NOT_EXECUTED is not terminal (scenario hasn't run yet)
        assert (
            EnumScenarioStatusV2.is_terminal(EnumScenarioStatusV2.NOT_EXECUTED) is False
        )

    def test_is_executing(self):
        """Test the is_executing class method."""
        # Executing statuses
        assert EnumScenarioStatusV2.is_executing(EnumScenarioStatusV2.RUNNING) is True
        assert EnumScenarioStatusV2.is_executing(EnumScenarioStatusV2.ACTIVE) is True

        # Non-executing statuses
        non_executing = [
            EnumScenarioStatusV2.INACTIVE,
            EnumScenarioStatusV2.PENDING,
            EnumScenarioStatusV2.COMPLETED,
            EnumScenarioStatusV2.FAILED,
            EnumScenarioStatusV2.VALID,
            EnumScenarioStatusV2.INVALID,
            EnumScenarioStatusV2.UNKNOWN,
            EnumScenarioStatusV2.NOT_EXECUTED,
            EnumScenarioStatusV2.QUEUED,
            EnumScenarioStatusV2.SKIPPED,
        ]

        for status in non_executing:
            assert EnumScenarioStatusV2.is_executing(status) is False

    def test_is_executable(self):
        """Test the is_executable class method."""
        # Executable statuses (can start execution)
        executable_statuses = [
            EnumScenarioStatusV2.NOT_EXECUTED,
            EnumScenarioStatusV2.QUEUED,
            EnumScenarioStatusV2.PENDING,
            EnumScenarioStatusV2.INACTIVE,
        ]

        for status in executable_statuses:
            assert EnumScenarioStatusV2.is_executable(status) is True

        # Non-executable statuses
        non_executable = [
            EnumScenarioStatusV2.ACTIVE,
            EnumScenarioStatusV2.RUNNING,
            EnumScenarioStatusV2.COMPLETED,
            EnumScenarioStatusV2.FAILED,
            EnumScenarioStatusV2.VALID,
            EnumScenarioStatusV2.INVALID,
            EnumScenarioStatusV2.UNKNOWN,
            EnumScenarioStatusV2.SKIPPED,
        ]

        for status in non_executable:
            assert EnumScenarioStatusV2.is_executable(status) is False

    def test_requires_attention(self):
        """Test the requires_attention class method."""
        # Statuses requiring attention
        assert (
            EnumScenarioStatusV2.requires_attention(EnumScenarioStatusV2.FAILED) is True
        )
        assert (
            EnumScenarioStatusV2.requires_attention(EnumScenarioStatusV2.INVALID)
            is True
        )

        # Statuses not requiring attention
        no_attention = [
            EnumScenarioStatusV2.INACTIVE,
            EnumScenarioStatusV2.ACTIVE,
            EnumScenarioStatusV2.PENDING,
            EnumScenarioStatusV2.RUNNING,
            EnumScenarioStatusV2.COMPLETED,
            EnumScenarioStatusV2.VALID,
            EnumScenarioStatusV2.UNKNOWN,
            EnumScenarioStatusV2.NOT_EXECUTED,
            EnumScenarioStatusV2.QUEUED,
            EnumScenarioStatusV2.SKIPPED,
        ]

        for status in no_attention:
            assert EnumScenarioStatusV2.requires_attention(status) is False

    def test_is_waiting(self):
        """Test the is_waiting class method."""
        # Waiting statuses
        waiting_statuses = [
            EnumScenarioStatusV2.NOT_EXECUTED,
            EnumScenarioStatusV2.QUEUED,
            EnumScenarioStatusV2.PENDING,
        ]

        for status in waiting_statuses:
            assert EnumScenarioStatusV2.is_waiting(status) is True

        # Non-waiting statuses
        for status in EnumScenarioStatusV2:
            if status not in waiting_statuses:
                assert EnumScenarioStatusV2.is_waiting(status) is False

    def test_is_successful(self):
        """Test the is_successful class method."""
        # Successful statuses
        assert (
            EnumScenarioStatusV2.is_successful(EnumScenarioStatusV2.COMPLETED) is True
        )
        assert EnumScenarioStatusV2.is_successful(EnumScenarioStatusV2.VALID) is True

        # Non-successful statuses
        non_successful = [
            EnumScenarioStatusV2.INACTIVE,
            EnumScenarioStatusV2.ACTIVE,
            EnumScenarioStatusV2.PENDING,
            EnumScenarioStatusV2.RUNNING,
            EnumScenarioStatusV2.FAILED,
            EnumScenarioStatusV2.INVALID,
            EnumScenarioStatusV2.UNKNOWN,
            EnumScenarioStatusV2.NOT_EXECUTED,
            EnumScenarioStatusV2.QUEUED,
            EnumScenarioStatusV2.SKIPPED,
        ]

        for status in non_successful:
            assert EnumScenarioStatusV2.is_successful(status) is False

    def test_to_base_status(self):
        """Test to_base_status conversion method."""
        # Direct base status mappings
        assert EnumScenarioStatusV2.INACTIVE.to_base_status() == EnumBaseStatus.INACTIVE
        assert EnumScenarioStatusV2.ACTIVE.to_base_status() == EnumBaseStatus.ACTIVE
        assert EnumScenarioStatusV2.PENDING.to_base_status() == EnumBaseStatus.PENDING
        assert EnumScenarioStatusV2.RUNNING.to_base_status() == EnumBaseStatus.RUNNING
        assert (
            EnumScenarioStatusV2.COMPLETED.to_base_status() == EnumBaseStatus.COMPLETED
        )
        assert EnumScenarioStatusV2.FAILED.to_base_status() == EnumBaseStatus.FAILED
        assert EnumScenarioStatusV2.VALID.to_base_status() == EnumBaseStatus.VALID
        assert EnumScenarioStatusV2.INVALID.to_base_status() == EnumBaseStatus.INVALID
        assert EnumScenarioStatusV2.UNKNOWN.to_base_status() == EnumBaseStatus.UNKNOWN

        # Scenario-specific mappings
        assert (
            EnumScenarioStatusV2.NOT_EXECUTED.to_base_status()
            == EnumBaseStatus.INACTIVE
        )
        assert EnumScenarioStatusV2.QUEUED.to_base_status() == EnumBaseStatus.PENDING
        assert EnumScenarioStatusV2.SKIPPED.to_base_status() == EnumBaseStatus.INACTIVE

    def test_from_base_status(self):
        """Test from_base_status class method."""
        # Test all base status conversions
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.INACTIVE)
            == EnumScenarioStatusV2.INACTIVE
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.ACTIVE)
            == EnumScenarioStatusV2.ACTIVE
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.PENDING)
            == EnumScenarioStatusV2.PENDING
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.RUNNING)
            == EnumScenarioStatusV2.RUNNING
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.COMPLETED)
            == EnumScenarioStatusV2.COMPLETED
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.FAILED)
            == EnumScenarioStatusV2.FAILED
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.VALID)
            == EnumScenarioStatusV2.VALID
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.INVALID)
            == EnumScenarioStatusV2.INVALID
        )
        assert (
            EnumScenarioStatusV2.from_base_status(EnumBaseStatus.UNKNOWN)
            == EnumScenarioStatusV2.UNKNOWN
        )

    def test_base_status_roundtrip(self):
        """Test roundtrip conversion base -> scenario -> base for base values."""
        # All base statuses should roundtrip
        for base_status in EnumBaseStatus:
            scenario_status = EnumScenarioStatusV2.from_base_status(base_status)
            back_to_base = scenario_status.to_base_status()
            assert back_to_base == base_status, (
                f"Roundtrip failed for {base_status}: "
                f"got {back_to_base} via {scenario_status}"
            )

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumScenarioStatusV2.COMPLETED == EnumScenarioStatusV2.COMPLETED
        assert EnumScenarioStatusV2.FAILED != EnumScenarioStatusV2.COMPLETED

    def test_enum_membership(self):
        """Test enum membership checking."""
        for status in EnumScenarioStatusV2:
            assert status in EnumScenarioStatusV2

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        status = EnumScenarioStatusV2.NOT_EXECUTED
        json_str = json.dumps(status, default=str)
        assert json_str == '"not_executed"'

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class ScenarioModel(BaseModel):
            status: EnumScenarioStatusV2

        # Test valid enum assignment
        model = ScenarioModel(status=EnumScenarioStatusV2.QUEUED)
        assert model.status == EnumScenarioStatusV2.QUEUED

        # Test string assignment
        model = ScenarioModel(status="skipped")
        assert model.status == EnumScenarioStatusV2.SKIPPED

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            ScenarioModel(status="invalid_status")

    def test_compatibility_alias(self):
        """Test that EnumScenarioStatus alias works correctly."""
        assert EnumScenarioStatus is EnumScenarioStatusV2
        assert EnumScenarioStatus.COMPLETED == EnumScenarioStatusV2.COMPLETED
        assert EnumScenarioStatus.NOT_EXECUTED == EnumScenarioStatusV2.NOT_EXECUTED

    def test_status_lifecycle_consistency(self):
        """Test logical consistency of status lifecycle."""
        for status in EnumScenarioStatusV2:
            is_terminal = EnumScenarioStatusV2.is_terminal(status)
            is_executing = EnumScenarioStatusV2.is_executing(status)
            is_waiting = EnumScenarioStatusV2.is_waiting(status)
            is_executable = EnumScenarioStatusV2.is_executable(status)

            # Terminal statuses should not be executing or waiting
            if is_terminal:
                assert not is_executing, f"{status} is terminal but executing"
                assert not is_waiting, f"{status} is terminal but waiting"

            # Executing statuses should not be executable (already running)
            if is_executing:
                assert not is_executable, f"{status} is executing but also executable"

    def test_all_statuses_categorized(self):
        """Test that all statuses fall into at least one category."""
        for status in EnumScenarioStatusV2:
            categorized = (
                EnumScenarioStatusV2.is_terminal(status)
                or EnumScenarioStatusV2.is_executing(status)
                or EnumScenarioStatusV2.is_waiting(status)
                or EnumScenarioStatusV2.is_executable(status)
                or status
                in {
                    EnumScenarioStatusV2.VALID,
                    EnumScenarioStatusV2.INVALID,
                    EnumScenarioStatusV2.UNKNOWN,
                }
            )
            assert categorized, f"{status} is not categorized by any method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
