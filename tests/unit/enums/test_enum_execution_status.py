"""
Unit tests for EnumExecutionStatus.

Tests all aspects of the execution status enum including:
- Enum value validation
- Status classification methods (terminal, active, successful)
- String representation
- JSON serialization compatibility
- Pydantic integration
- Execution lifecycle logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus


@pytest.mark.unit
class TestEnumExecutionStatus:
    """Test cases for EnumExecutionStatus."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "PENDING": "pending",
            "RUNNING": "running",
            "COMPLETED": "completed",
            "SUCCESS": "success",
            "FAILED": "failed",
            "SKIPPED": "skipped",
            "CANCELLED": "cancelled",
            "TIMEOUT": "timeout",
            "PARTIAL": "partial",
        }

        for name, value in expected_values.items():
            status = getattr(EnumExecutionStatus, name)
            assert status.value == value
            assert str(status) == value

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumExecutionStatus.PENDING) == "pending"
        assert str(EnumExecutionStatus.RUNNING) == "running"
        assert str(EnumExecutionStatus.SUCCESS) == "success"
        assert str(EnumExecutionStatus.FAILED) == "failed"

    def test_is_terminal(self):
        """Test the is_terminal class method."""
        # Terminal statuses
        terminal_statuses = [
            EnumExecutionStatus.COMPLETED,
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.SKIPPED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        ]

        for status in terminal_statuses:
            assert EnumExecutionStatus.is_terminal(status) is True

        # Non-terminal statuses
        non_terminal_statuses = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
        ]

        for status in non_terminal_statuses:
            assert EnumExecutionStatus.is_terminal(status) is False

    def test_is_active(self):
        """Test the is_active class method."""
        # Active statuses
        active_statuses = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
        ]

        for status in active_statuses:
            assert EnumExecutionStatus.is_active(status) is True

        # Non-active statuses
        non_active_statuses = [
            EnumExecutionStatus.COMPLETED,
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.SKIPPED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        ]

        for status in non_active_statuses:
            assert EnumExecutionStatus.is_active(status) is False

    def test_is_successful(self):
        """Test the is_successful class method."""
        # Successful statuses
        successful_statuses = [
            EnumExecutionStatus.COMPLETED,
            EnumExecutionStatus.SUCCESS,
        ]

        for status in successful_statuses:
            assert EnumExecutionStatus.is_successful(status) is True

        # Non-successful statuses
        non_successful_statuses = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.SKIPPED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        ]

        for status in non_successful_statuses:
            assert EnumExecutionStatus.is_successful(status) is False

    def test_is_skipped(self):
        """Test the is_skipped class method."""
        # Only SKIPPED should return True
        assert EnumExecutionStatus.is_skipped(EnumExecutionStatus.SKIPPED) is True

        # All other statuses should return False
        non_skipped_statuses = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.COMPLETED,
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        ]

        for status in non_skipped_statuses:
            assert EnumExecutionStatus.is_skipped(status) is False

    def test_is_running(self):
        """Test the is_running class method."""
        # Only RUNNING should return True
        assert EnumExecutionStatus.is_running(EnumExecutionStatus.RUNNING) is True

        # All other statuses should return False
        non_running_statuses = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.COMPLETED,
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.SKIPPED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        ]

        for status in non_running_statuses:
            assert EnumExecutionStatus.is_running(status) is False

        # Verify distinction from is_active (which includes PENDING)
        assert EnumExecutionStatus.is_active(EnumExecutionStatus.PENDING) is True
        assert EnumExecutionStatus.is_running(EnumExecutionStatus.PENDING) is False

    def test_is_cancelled(self):
        """Test the is_cancelled class method."""
        # Only CANCELLED should return True
        assert EnumExecutionStatus.is_cancelled(EnumExecutionStatus.CANCELLED) is True

        # All other statuses should return False
        non_cancelled_statuses = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.COMPLETED,
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.SKIPPED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        ]

        for status in non_cancelled_statuses:
            assert EnumExecutionStatus.is_cancelled(status) is False

        # Verify CANCELLED is neither success nor failure
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.CANCELLED) is False
        assert EnumExecutionStatus.is_failure(EnumExecutionStatus.CANCELLED) is False

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumExecutionStatus.SUCCESS == EnumExecutionStatus.SUCCESS
        assert EnumExecutionStatus.FAILED != EnumExecutionStatus.SUCCESS
        assert EnumExecutionStatus.RUNNING == EnumExecutionStatus.RUNNING

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_statuses = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.COMPLETED,
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.SKIPPED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        ]

        for status in all_statuses:
            assert status in EnumExecutionStatus

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        statuses = list(EnumExecutionStatus)
        assert len(statuses) == 9

        status_values = [status.value for status in statuses]
        expected_values = [
            "pending",
            "running",
            "completed",
            "success",
            "failed",
            "skipped",
            "cancelled",
            "timeout",
            "partial",
        ]

        assert set(status_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        status = EnumExecutionStatus.RUNNING
        json_str = json.dumps(status, default=str)
        assert json_str == '"running"'

        # Test in dictionary
        data = {"execution_status": EnumExecutionStatus.SUCCESS}
        json_str = json.dumps(data, default=str)
        assert '"execution_status": "success"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class EnumExecutionModel(BaseModel):
            status: EnumExecutionStatus

        # Test valid enum assignment
        model = EnumExecutionModel(status=EnumExecutionStatus.COMPLETED)
        assert model.status == EnumExecutionStatus.COMPLETED

        # Test string assignment (should work due to str inheritance)
        model = EnumExecutionModel(status="running")
        assert model.status == EnumExecutionStatus.RUNNING

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            EnumExecutionModel(status="invalid_status")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class EnumExecutionModel(BaseModel):
            status: EnumExecutionStatus

        model = EnumExecutionModel(status=EnumExecutionStatus.FAILED)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"status": "failed"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"status":"failed"}'

    def test_execution_lifecycle_logic(self):
        """Test execution lifecycle state transitions and logic."""
        # Test that active and terminal states are mutually exclusive
        for status in EnumExecutionStatus:
            is_active = EnumExecutionStatus.is_active(status)
            is_terminal = EnumExecutionStatus.is_terminal(status)

            # A status cannot be both active and terminal
            assert not (is_active and is_terminal), (
                f"{status} cannot be both active and terminal"
            )

        # Test that all statuses are either active or terminal
        for status in EnumExecutionStatus:
            is_active = EnumExecutionStatus.is_active(status)
            is_terminal = EnumExecutionStatus.is_terminal(status)

            assert is_active or is_terminal, (
                f"{status} must be either active or terminal"
            )

    def test_success_status_logic(self):
        """Test success status categorization logic."""
        # Successful statuses should be terminal
        successful_statuses = [
            s for s in EnumExecutionStatus if EnumExecutionStatus.is_successful(s)
        ]
        for status in successful_statuses:
            assert EnumExecutionStatus.is_terminal(status) is True

        # Successful statuses should not be active
        for status in successful_statuses:
            assert EnumExecutionStatus.is_active(status) is False

        # Test specific success semantics
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.SUCCESS) is True
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.COMPLETED) is True
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.FAILED) is False

    def test_failure_categorization(self):
        """Test failure and error state categorization."""
        # Define failure/error states
        failure_states = [
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
        ]

        for status in failure_states:
            # Failure states should be terminal
            assert EnumExecutionStatus.is_terminal(status) is True
            # Failure states should not be active
            assert EnumExecutionStatus.is_active(status) is False
            # Failure states should not be successful
            assert EnumExecutionStatus.is_successful(status) is False

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity
        assert EnumExecutionStatus.SUCCESS.value == "success"
        assert EnumExecutionStatus.SUCCESS.value != "SUCCESS"
        assert EnumExecutionStatus.SUCCESS.value != "Success"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumExecutionStatus("invalid_status")

    def test_comprehensive_execution_scenarios(self):
        """Test comprehensive execution lifecycle scenarios."""
        # Test normal successful execution flow
        success_flow = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.SUCCESS,
        ]

        for i, status in enumerate(success_flow):
            if i < 2:  # PENDING, RUNNING
                assert EnumExecutionStatus.is_active(status) is True
                assert EnumExecutionStatus.is_terminal(status) is False
                assert EnumExecutionStatus.is_successful(status) is False
            else:  # SUCCESS
                assert EnumExecutionStatus.is_active(status) is False
                assert EnumExecutionStatus.is_terminal(status) is True
                assert EnumExecutionStatus.is_successful(status) is True

        # Test failed execution flow
        failure_flow = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.FAILED,
        ]

        final_status = failure_flow[-1]  # FAILED
        assert EnumExecutionStatus.is_active(final_status) is False
        assert EnumExecutionStatus.is_terminal(final_status) is True
        assert EnumExecutionStatus.is_successful(final_status) is False

        # Test cancelled execution
        assert EnumExecutionStatus.is_active(EnumExecutionStatus.CANCELLED) is False
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.CANCELLED) is True
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.CANCELLED) is False

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable (as string values)
        data = {"status": str(EnumExecutionStatus.TIMEOUT)}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "status: timeout" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["status"] == "timeout"

    def test_status_progression_validation(self):
        """Test logical status progression validation."""
        # Define valid status transitions
        valid_transitions = {
            EnumExecutionStatus.PENDING: [
                EnumExecutionStatus.RUNNING,
                EnumExecutionStatus.CANCELLED,
                EnumExecutionStatus.SKIPPED,
            ],
            EnumExecutionStatus.RUNNING: [
                EnumExecutionStatus.COMPLETED,
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.CANCELLED,
                EnumExecutionStatus.TIMEOUT,
            ],
        }

        # Test that terminal states have no valid transitions
        terminal_statuses = [
            s for s in EnumExecutionStatus if EnumExecutionStatus.is_terminal(s)
        ]
        for status in terminal_statuses:
            # Terminal statuses should not transition to other states
            # This is just a logical test - the enum doesn't enforce this
            assert EnumExecutionStatus.is_terminal(status) is True

    def test_to_base_status(self):
        """Test to_base_status conversion method."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # Direct mappings
        assert EnumExecutionStatus.PENDING.to_base_status() == EnumBaseStatus.PENDING
        assert EnumExecutionStatus.RUNNING.to_base_status() == EnumBaseStatus.RUNNING
        assert (
            EnumExecutionStatus.COMPLETED.to_base_status() == EnumBaseStatus.COMPLETED
        )
        assert EnumExecutionStatus.FAILED.to_base_status() == EnumBaseStatus.FAILED

        # Execution-specific mappings
        assert EnumExecutionStatus.SUCCESS.to_base_status() == EnumBaseStatus.COMPLETED
        assert EnumExecutionStatus.SKIPPED.to_base_status() == EnumBaseStatus.INACTIVE
        assert EnumExecutionStatus.CANCELLED.to_base_status() == EnumBaseStatus.INACTIVE
        assert EnumExecutionStatus.TIMEOUT.to_base_status() == EnumBaseStatus.FAILED
        assert EnumExecutionStatus.PARTIAL.to_base_status() == EnumBaseStatus.COMPLETED

    def test_from_base_status(self):
        """Test from_base_status class method."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # Test valid conversions
        assert (
            EnumExecutionStatus.from_base_status(EnumBaseStatus.PENDING)
            == EnumExecutionStatus.PENDING
        )
        assert (
            EnumExecutionStatus.from_base_status(EnumBaseStatus.RUNNING)
            == EnumExecutionStatus.RUNNING
        )
        assert (
            EnumExecutionStatus.from_base_status(EnumBaseStatus.COMPLETED)
            == EnumExecutionStatus.COMPLETED
        )
        assert (
            EnumExecutionStatus.from_base_status(EnumBaseStatus.FAILED)
            == EnumExecutionStatus.FAILED
        )
        assert (
            EnumExecutionStatus.from_base_status(EnumBaseStatus.INACTIVE)
            == EnumExecutionStatus.CANCELLED
        )
        assert (
            EnumExecutionStatus.from_base_status(EnumBaseStatus.ACTIVE)
            == EnumExecutionStatus.RUNNING
        )
        assert (
            EnumExecutionStatus.from_base_status(EnumBaseStatus.UNKNOWN)
            == EnumExecutionStatus.PENDING
        )

    def test_from_base_status_invalid(self):
        """Test from_base_status raises ValueError for unmapped values."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # VALID and INVALID don't have mappings, should raise ValueError
        with pytest.raises(ValueError):
            EnumExecutionStatus.from_base_status(EnumBaseStatus.VALID)

        with pytest.raises(ValueError):
            EnumExecutionStatus.from_base_status(EnumBaseStatus.INVALID)

    def test_base_status_roundtrip(self):
        """Test roundtrip conversion base -> execution -> base."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # These base statuses should roundtrip
        roundtrip_statuses = [
            EnumBaseStatus.PENDING,
            EnumBaseStatus.RUNNING,
            EnumBaseStatus.COMPLETED,
            EnumBaseStatus.FAILED,
        ]

        for base_status in roundtrip_statuses:
            exec_status = EnumExecutionStatus.from_base_status(base_status)
            back_to_base = exec_status.to_base_status()
            assert back_to_base == base_status, (
                f"Roundtrip failed for {base_status}: "
                f"got {back_to_base} via {exec_status}"
            )

    def test_is_terminal_edge_cases(self):
        """Test is_terminal with edge cases and boundary conditions.

        Verifies nuanced terminal state semantics for execution status:
        - PARTIAL is terminal even though it's neither full success nor failure
        - CANCELLED is terminal (intentional termination)
        - TIMEOUT is terminal (forced termination)
        """
        # PARTIAL is terminal despite being neither success nor failure
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.PARTIAL) is True
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.PARTIAL) is False
        assert EnumExecutionStatus.is_failure(EnumExecutionStatus.PARTIAL) is False

        # CANCELLED is terminal but not classified as success or failure
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.CANCELLED) is True
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.CANCELLED) is False
        assert EnumExecutionStatus.is_failure(EnumExecutionStatus.CANCELLED) is False

        # TIMEOUT is terminal and IS a failure (error condition)
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.TIMEOUT) is True
        assert EnumExecutionStatus.is_failure(EnumExecutionStatus.TIMEOUT) is True

    def test_is_terminal_mutual_exclusivity(self):
        """Test that terminal and active states are mutually exclusive.

        Every execution status must be either terminal or active, never both.
        This is a fundamental invariant of execution lifecycle semantics.
        """
        for status in EnumExecutionStatus:
            is_terminal = EnumExecutionStatus.is_terminal(status)
            is_active = EnumExecutionStatus.is_active(status)

            # XOR: exactly one must be true
            assert is_terminal != is_active, (
                f"{status} violates mutual exclusivity: "
                f"is_terminal={is_terminal}, is_active={is_active}"
            )

    def test_is_terminal_completeness(self):
        """Test that all status values are categorized by is_terminal.

        Every status must be either terminal or non-terminal (active).
        This ensures no status values are left uncategorized.
        """
        terminal_count = sum(
            1 for s in EnumExecutionStatus if EnumExecutionStatus.is_terminal(s)
        )
        active_count = sum(
            1 for s in EnumExecutionStatus if EnumExecutionStatus.is_active(s)
        )

        # All statuses should be accounted for
        assert terminal_count + active_count == len(EnumExecutionStatus)

        # Expected counts based on the enum definition
        assert (
            terminal_count == 7
        )  # COMPLETED, SUCCESS, FAILED, SKIPPED, CANCELLED, TIMEOUT, PARTIAL
        assert active_count == 2  # PENDING, RUNNING

    def test_roundtrip_serialization_all_values(self):
        """Test roundtrip serialization for all enum values.

        Ensures str(enum) -> Enum(str) works for every value.
        """
        for status in EnumExecutionStatus:
            # String roundtrip
            serialized = str(status)
            deserialized = EnumExecutionStatus(serialized)
            assert deserialized == status, (
                f"String roundtrip failed for {status}: "
                f"serialized={serialized}, deserialized={deserialized}"
            )

            # Value roundtrip
            value = status.value
            reconstructed = EnumExecutionStatus(value)
            assert reconstructed == status, (
                f"Value roundtrip failed for {status}: "
                f"value={value}, reconstructed={reconstructed}"
            )

    def test_inactive_mapping_via_base_status(self):
        """Test that INACTIVE base status maps correctly to CANCELLED.

        EnumBaseStatus.INACTIVE represents intentional deactivation,
        which maps to CANCELLED in execution context (intentional termination).
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # INACTIVE -> CANCELLED
        result = EnumExecutionStatus.from_base_status(EnumBaseStatus.INACTIVE)
        assert result == EnumExecutionStatus.CANCELLED

        # And CANCELLED -> INACTIVE roundtrip
        back_to_base = result.to_base_status()
        assert back_to_base == EnumBaseStatus.INACTIVE

    def test_all_base_status_mappings(self):
        """Test all valid base status to execution status mappings.

        Ensures complete coverage of from_base_status method.
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # All valid mappings
        valid_mappings = {
            EnumBaseStatus.PENDING: EnumExecutionStatus.PENDING,
            EnumBaseStatus.RUNNING: EnumExecutionStatus.RUNNING,
            EnumBaseStatus.COMPLETED: EnumExecutionStatus.COMPLETED,
            EnumBaseStatus.FAILED: EnumExecutionStatus.FAILED,
            EnumBaseStatus.INACTIVE: EnumExecutionStatus.CANCELLED,
            EnumBaseStatus.ACTIVE: EnumExecutionStatus.RUNNING,
            EnumBaseStatus.UNKNOWN: EnumExecutionStatus.PENDING,
        }

        for base_status, expected in valid_mappings.items():
            result = EnumExecutionStatus.from_base_status(base_status)
            assert result == expected, (
                f"Mapping failed for {base_status}: "
                f"expected={expected}, actual={result}"
            )

    def test_is_failure_method(self):
        """Test the is_failure class method exhaustively.

        Verifies that is_failure correctly identifies failure states.
        """
        failure_statuses = {
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.TIMEOUT,
        }

        for status in EnumExecutionStatus:
            expected = status in failure_statuses
            assert EnumExecutionStatus.is_failure(status) == expected, (
                f"is_failure() mismatch for {status}: "
                f"expected={expected}, actual={EnumExecutionStatus.is_failure(status)}"
            )

    def test_is_partial_method(self):
        """Test the is_partial class method.

        Verifies that only PARTIAL returns True.
        """
        for status in EnumExecutionStatus:
            expected = status == EnumExecutionStatus.PARTIAL
            assert EnumExecutionStatus.is_partial(status) == expected, (
                f"is_partial() mismatch for {status}: "
                f"expected={expected}, actual={EnumExecutionStatus.is_partial(status)}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
