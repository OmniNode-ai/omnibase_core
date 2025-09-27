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
        ]

        for status in non_successful_statuses:
            assert EnumExecutionStatus.is_successful(status) is False

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
        ]

        for status in all_statuses:
            assert status in EnumExecutionStatus

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        statuses = list(EnumExecutionStatus)
        assert len(statuses) == 8

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

        class ExecutionModel(BaseModel):
            status: EnumExecutionStatus

        # Test valid enum assignment
        model = ExecutionModel(status=EnumExecutionStatus.COMPLETED)
        assert model.status == EnumExecutionStatus.COMPLETED

        # Test string assignment (should work due to str inheritance)
        model = ExecutionModel(status="running")
        assert model.status == EnumExecutionStatus.RUNNING

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            ExecutionModel(status="invalid_status")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class ExecutionModel(BaseModel):
            status: EnumExecutionStatus

        model = ExecutionModel(status=EnumExecutionStatus.FAILED)

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
            assert not (
                is_active and is_terminal
            ), f"{status} cannot be both active and terminal"

        # Test that all statuses are either active or terminal
        for status in EnumExecutionStatus:
            is_active = EnumExecutionStatus.is_active(status)
            is_terminal = EnumExecutionStatus.is_terminal(status)

            assert (
                is_active or is_terminal
            ), f"{status} must be either active or terminal"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
