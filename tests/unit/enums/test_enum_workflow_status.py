# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumWorkflowStatus.

Tests all aspects of the workflow status enum including:
- Enum value validation
- Status classification methods (is_terminal, is_active, is_successful, is_error_state)
- String representation
- JSON serialization compatibility
- Pydantic integration
- Workflow lifecycle logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus


@pytest.mark.unit
class TestEnumWorkflowStatus:
    """Test cases for EnumWorkflowStatus."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "PENDING": "pending",
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
            "PAUSED": "paused",
        }

        for name, value in expected_values.items():
            status = getattr(EnumWorkflowStatus, name)
            assert status.value == value

    def test_enum_count(self):
        """Test expected number of enum values."""
        assert len(EnumWorkflowStatus) == 6

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumWorkflowStatus.PENDING) == "pending"
        assert str(EnumWorkflowStatus.RUNNING) == "running"
        assert str(EnumWorkflowStatus.COMPLETED) == "completed"
        assert str(EnumWorkflowStatus.FAILED) == "failed"
        assert str(EnumWorkflowStatus.CANCELLED) == "cancelled"
        assert str(EnumWorkflowStatus.PAUSED) == "paused"

    def test_is_terminal(self):
        """Test the is_terminal class method."""
        # Terminal statuses
        terminal_statuses = [
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
        ]

        for status in terminal_statuses:
            assert EnumWorkflowStatus.is_terminal(status) is True

        # Non-terminal statuses
        non_terminal_statuses = [
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.PAUSED,
        ]

        for status in non_terminal_statuses:
            assert EnumWorkflowStatus.is_terminal(status) is False

    def test_is_terminal_all_statuses(self):
        """Test is_terminal for every status value explicitly."""
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.PENDING) is False
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.RUNNING) is False
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.COMPLETED) is True
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.FAILED) is True
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.CANCELLED) is True
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.PAUSED) is False

    def test_is_terminal_edge_cases(self):
        """Test is_terminal with edge cases and boundary conditions.

        Verifies nuanced terminal state semantics for workflow status:
        - PAUSED is NOT terminal (workflow can resume)
        - CANCELLED is terminal (intentional termination)
        - All terminal states cannot transition to other states
        """
        # PAUSED is NOT terminal - workflow execution is suspended but can resume
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.PAUSED) is False
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.PAUSED) is True

        # CANCELLED is terminal - intentional termination, no further progress
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.CANCELLED) is True
        assert EnumWorkflowStatus.is_successful(EnumWorkflowStatus.CANCELLED) is False
        assert EnumWorkflowStatus.is_error_state(EnumWorkflowStatus.CANCELLED) is False

    def test_is_terminal_mutual_exclusivity(self):
        """Test that terminal and active states are mutually exclusive.

        Every workflow status must be either terminal or active, never both.
        This is a fundamental invariant of workflow lifecycle semantics.
        """
        for status in EnumWorkflowStatus:
            is_terminal = EnumWorkflowStatus.is_terminal(status)
            is_active = EnumWorkflowStatus.is_active(status)

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
            1 for s in EnumWorkflowStatus if EnumWorkflowStatus.is_terminal(s)
        )
        active_count = sum(
            1 for s in EnumWorkflowStatus if EnumWorkflowStatus.is_active(s)
        )

        # All statuses should be accounted for
        assert terminal_count + active_count == len(EnumWorkflowStatus)

        # Expected counts based on the enum definition
        assert terminal_count == 3  # COMPLETED, FAILED, CANCELLED
        assert active_count == 3  # PENDING, RUNNING, PAUSED

    def test_is_active(self):
        """Test the is_active class method."""
        # Active statuses
        active_statuses = [
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.PAUSED,
        ]

        for status in active_statuses:
            assert EnumWorkflowStatus.is_active(status) is True

        # Non-active statuses
        non_active_statuses = [
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
        ]

        for status in non_active_statuses:
            assert EnumWorkflowStatus.is_active(status) is False

    def test_is_active_all_statuses(self):
        """Test is_active for every status value explicitly."""
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.PENDING) is True
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.RUNNING) is True
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.COMPLETED) is False
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.FAILED) is False
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.CANCELLED) is False
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.PAUSED) is True

    def test_is_successful(self):
        """Test the is_successful class method."""
        # Only COMPLETED should return True
        assert EnumWorkflowStatus.is_successful(EnumWorkflowStatus.COMPLETED) is True

        # All other statuses should return False
        non_successful_statuses = [
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
            EnumWorkflowStatus.PAUSED,
        ]

        for status in non_successful_statuses:
            assert EnumWorkflowStatus.is_successful(status) is False

    def test_is_error_state(self):
        """Test the is_error_state class method."""
        # Only FAILED should return True
        assert EnumWorkflowStatus.is_error_state(EnumWorkflowStatus.FAILED) is True

        # All other statuses should return False
        non_error_statuses = [
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.CANCELLED,
            EnumWorkflowStatus.PAUSED,
        ]

        for status in non_error_statuses:
            assert EnumWorkflowStatus.is_error_state(status) is False

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumWorkflowStatus.COMPLETED == EnumWorkflowStatus.COMPLETED
        assert EnumWorkflowStatus.FAILED != EnumWorkflowStatus.COMPLETED
        assert EnumWorkflowStatus.RUNNING == EnumWorkflowStatus.RUNNING

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_statuses = [
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
            EnumWorkflowStatus.PAUSED,
        ]

        for status in all_statuses:
            assert status in EnumWorkflowStatus

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        statuses = list(EnumWorkflowStatus)
        assert len(statuses) == 6

        status_values = [status.value for status in statuses]
        expected_values = [
            "pending",
            "running",
            "completed",
            "failed",
            "cancelled",
            "paused",
        ]

        assert set(status_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        status = EnumWorkflowStatus.RUNNING
        json_str = json.dumps(status, default=str)
        assert json_str == '"running"'

        # Test in dictionary
        data = {"workflow_status": EnumWorkflowStatus.COMPLETED}
        json_str = json.dumps(data, default=str)
        assert '"workflow_status": "completed"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class WorkflowModel(BaseModel):
            status: EnumWorkflowStatus

        # Test valid enum assignment
        model = WorkflowModel(status=EnumWorkflowStatus.COMPLETED)
        assert model.status == EnumWorkflowStatus.COMPLETED

        # Test string assignment (should work due to str inheritance)
        model = WorkflowModel(status="running")
        assert model.status == EnumWorkflowStatus.RUNNING

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            WorkflowModel(status="invalid_status")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class WorkflowModel(BaseModel):
            status: EnumWorkflowStatus

        model = WorkflowModel(status=EnumWorkflowStatus.FAILED)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"status": "failed"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"status":"failed"}'

    def test_workflow_lifecycle_logic(self):
        """Test workflow lifecycle state transitions and logic."""
        # Test that all statuses are either active XOR terminal (mutually exclusive)
        for status in EnumWorkflowStatus:
            is_active = EnumWorkflowStatus.is_active(status)
            is_terminal = EnumWorkflowStatus.is_terminal(status)

            # A status cannot be both active and terminal
            assert not (is_active and is_terminal), (
                f"{status} cannot be both active and terminal"
            )

            # A status must be either active or terminal
            assert is_active or is_terminal, (
                f"{status} must be either active or terminal"
            )

    def test_success_status_logic(self):
        """Test success status categorization logic."""
        # Successful statuses should be terminal
        successful_statuses = [
            s for s in EnumWorkflowStatus if EnumWorkflowStatus.is_successful(s)
        ]
        for status in successful_statuses:
            assert EnumWorkflowStatus.is_terminal(status) is True

        # Successful statuses should not be active
        for status in successful_statuses:
            assert EnumWorkflowStatus.is_active(status) is False

        # Test specific success semantics
        assert EnumWorkflowStatus.is_successful(EnumWorkflowStatus.COMPLETED) is True
        assert EnumWorkflowStatus.is_successful(EnumWorkflowStatus.FAILED) is False

    def test_failure_categorization(self):
        """Test failure and error state categorization."""
        # Error states should be terminal
        error_statuses = [
            s for s in EnumWorkflowStatus if EnumWorkflowStatus.is_error_state(s)
        ]
        for status in error_statuses:
            assert EnumWorkflowStatus.is_terminal(status) is True
            assert EnumWorkflowStatus.is_active(status) is False
            assert EnumWorkflowStatus.is_successful(status) is False

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity
        assert EnumWorkflowStatus.COMPLETED.value == "completed"
        assert EnumWorkflowStatus.COMPLETED.value != "COMPLETED"
        assert EnumWorkflowStatus.COMPLETED.value != "Completed"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumWorkflowStatus("invalid_status")

    def test_comprehensive_workflow_scenarios(self):
        """Test comprehensive workflow lifecycle scenarios."""
        # Test normal successful workflow flow
        success_flow = [
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.COMPLETED,
        ]

        for i, status in enumerate(success_flow):
            if i < 2:  # PENDING, RUNNING
                assert EnumWorkflowStatus.is_active(status) is True
                assert EnumWorkflowStatus.is_terminal(status) is False
                assert EnumWorkflowStatus.is_successful(status) is False
            else:  # COMPLETED
                assert EnumWorkflowStatus.is_active(status) is False
                assert EnumWorkflowStatus.is_terminal(status) is True
                assert EnumWorkflowStatus.is_successful(status) is True

        # Test failed workflow flow
        failure_flow = [
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.FAILED,
        ]

        final_status = failure_flow[-1]  # FAILED
        assert EnumWorkflowStatus.is_active(final_status) is False
        assert EnumWorkflowStatus.is_terminal(final_status) is True
        assert EnumWorkflowStatus.is_successful(final_status) is False
        assert EnumWorkflowStatus.is_error_state(final_status) is True

        # Test paused workflow (can be resumed)
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.PAUSED) is True
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.PAUSED) is False

        # Test cancelled workflow
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.CANCELLED) is False
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.CANCELLED) is True
        assert EnumWorkflowStatus.is_successful(EnumWorkflowStatus.CANCELLED) is False
        assert EnumWorkflowStatus.is_error_state(EnumWorkflowStatus.CANCELLED) is False

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable (as string values)
        data = {"status": str(EnumWorkflowStatus.PAUSED)}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "status: paused" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["status"] == "paused"

    def test_status_progression_validation(self):
        """Test logical status progression validation."""
        # Define valid status transitions for workflows
        valid_transitions = {
            EnumWorkflowStatus.PENDING: [
                EnumWorkflowStatus.RUNNING,
                EnumWorkflowStatus.CANCELLED,
            ],
            EnumWorkflowStatus.RUNNING: [
                EnumWorkflowStatus.COMPLETED,
                EnumWorkflowStatus.FAILED,
                EnumWorkflowStatus.CANCELLED,
                EnumWorkflowStatus.PAUSED,
            ],
            EnumWorkflowStatus.PAUSED: [
                EnumWorkflowStatus.RUNNING,
                EnumWorkflowStatus.CANCELLED,
            ],
        }

        # Test that terminal states have no valid transitions defined
        # (terminal statuses should not appear in valid_transitions keys)
        terminal_statuses = [
            s for s in EnumWorkflowStatus if EnumWorkflowStatus.is_terminal(s)
        ]
        for status in terminal_statuses:
            assert status not in valid_transitions

        # Test that valid transitions are defined for active states
        for status in EnumWorkflowStatus:
            if EnumWorkflowStatus.is_active(status):
                # Active states should have defined transitions
                assert status in valid_transitions

    def test_roundtrip_serialization(self):
        """Test roundtrip serialization for all enum values.

        For str,Enum types like EnumWorkflowStatus, str(status) returns
        status.value, so we only need to test one roundtrip path.
        """
        for status in EnumWorkflowStatus:
            # Value roundtrip (str(status) == status.value for str,Enum)
            value = status.value
            reconstructed = EnumWorkflowStatus(value)
            assert reconstructed == status

    def test_cancelled_is_neither_success_nor_error(self):
        """Test that CANCELLED is neither success nor error.

        CANCELLED represents intentional termination by user or system,
        which is neither a success (work completed) nor an error (work failed).
        """
        status = EnumWorkflowStatus.CANCELLED
        assert EnumWorkflowStatus.is_terminal(status) is True
        assert EnumWorkflowStatus.is_successful(status) is False
        assert EnumWorkflowStatus.is_error_state(status) is False
        assert EnumWorkflowStatus.is_active(status) is False

    def test_paused_is_resumable(self):
        """Test that PAUSED is an active state (can be resumed).

        PAUSED workflows are not terminal - they can transition back
        to RUNNING when resumed.
        """
        status = EnumWorkflowStatus.PAUSED
        assert EnumWorkflowStatus.is_active(status) is True
        assert EnumWorkflowStatus.is_terminal(status) is False
        assert EnumWorkflowStatus.is_successful(status) is False
        assert EnumWorkflowStatus.is_error_state(status) is False
