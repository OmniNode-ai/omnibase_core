"""
Unit tests for enum_workflow_coordination.py.

Tests for all workflow coordination enums including EnumWorkflowStatus,
EnumAssignmentStatus, EnumExecutionPattern, and EnumFailureRecoveryStrategy.
"""

import pytest

from omnibase_core.enums.enum_workflow_coordination import (
    EnumAssignmentStatus,
    EnumExecutionPattern,
    EnumFailureRecoveryStrategy,
    EnumWorkflowStatus,
)


class TestEnumWorkflowStatus:
    """Tests for EnumWorkflowStatus enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumWorkflowStatus.CREATED
        assert EnumWorkflowStatus.RUNNING
        assert EnumWorkflowStatus.COMPLETED
        assert EnumWorkflowStatus.FAILED
        assert EnumWorkflowStatus.CANCELLED

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumWorkflowStatus.CREATED.value == "CREATED"
        assert EnumWorkflowStatus.RUNNING.value == "RUNNING"
        assert EnumWorkflowStatus.COMPLETED.value == "COMPLETED"
        assert EnumWorkflowStatus.FAILED.value == "FAILED"
        assert EnumWorkflowStatus.CANCELLED.value == "CANCELLED"

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumWorkflowStatus)
        assert len(values) == 5
        assert EnumWorkflowStatus.CREATED in values
        assert EnumWorkflowStatus.RUNNING in values
        assert EnumWorkflowStatus.COMPLETED in values
        assert EnumWorkflowStatus.FAILED in values
        assert EnumWorkflowStatus.CANCELLED in values

    def test_enum_membership(self) -> None:
        """Test enum membership check."""
        assert EnumWorkflowStatus.CREATED in EnumWorkflowStatus
        assert EnumWorkflowStatus.RUNNING in EnumWorkflowStatus
        assert EnumWorkflowStatus.COMPLETED in EnumWorkflowStatus
        assert EnumWorkflowStatus.FAILED in EnumWorkflowStatus
        assert EnumWorkflowStatus.CANCELLED in EnumWorkflowStatus

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        assert str(EnumWorkflowStatus.CREATED) == "EnumWorkflowStatus.CREATED"
        assert str(EnumWorkflowStatus.RUNNING) == "EnumWorkflowStatus.RUNNING"
        assert str(EnumWorkflowStatus.COMPLETED) == "EnumWorkflowStatus.COMPLETED"
        assert str(EnumWorkflowStatus.FAILED) == "EnumWorkflowStatus.FAILED"
        assert str(EnumWorkflowStatus.CANCELLED) == "EnumWorkflowStatus.CANCELLED"

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumWorkflowStatus("CREATED") == EnumWorkflowStatus.CREATED
        assert EnumWorkflowStatus("RUNNING") == EnumWorkflowStatus.RUNNING
        assert EnumWorkflowStatus("COMPLETED") == EnumWorkflowStatus.COMPLETED
        assert EnumWorkflowStatus("FAILED") == EnumWorkflowStatus.FAILED
        assert EnumWorkflowStatus("CANCELLED") == EnumWorkflowStatus.CANCELLED

    def test_invalid_value_lookup_raises(self) -> None:
        """Test that invalid value lookup raises ValueError."""
        with pytest.raises(ValueError):
            EnumWorkflowStatus("INVALID")

    def test_is_str_enum(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumWorkflowStatus.CREATED, str)
        assert isinstance(EnumWorkflowStatus.RUNNING, str)


class TestEnumAssignmentStatus:
    """Tests for EnumAssignmentStatus enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumAssignmentStatus.ASSIGNED
        assert EnumAssignmentStatus.EXECUTING
        assert EnumAssignmentStatus.COMPLETED
        assert EnumAssignmentStatus.FAILED

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumAssignmentStatus.ASSIGNED.value == "ASSIGNED"
        assert EnumAssignmentStatus.EXECUTING.value == "EXECUTING"
        assert EnumAssignmentStatus.COMPLETED.value == "COMPLETED"
        assert EnumAssignmentStatus.FAILED.value == "FAILED"

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumAssignmentStatus)
        assert len(values) == 4
        assert EnumAssignmentStatus.ASSIGNED in values
        assert EnumAssignmentStatus.EXECUTING in values
        assert EnumAssignmentStatus.COMPLETED in values
        assert EnumAssignmentStatus.FAILED in values

    def test_enum_membership(self) -> None:
        """Test enum membership check."""
        assert EnumAssignmentStatus.ASSIGNED in EnumAssignmentStatus
        assert EnumAssignmentStatus.EXECUTING in EnumAssignmentStatus
        assert EnumAssignmentStatus.COMPLETED in EnumAssignmentStatus
        assert EnumAssignmentStatus.FAILED in EnumAssignmentStatus

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        assert str(EnumAssignmentStatus.ASSIGNED) == "EnumAssignmentStatus.ASSIGNED"
        assert str(EnumAssignmentStatus.EXECUTING) == "EnumAssignmentStatus.EXECUTING"
        assert str(EnumAssignmentStatus.COMPLETED) == "EnumAssignmentStatus.COMPLETED"
        assert str(EnumAssignmentStatus.FAILED) == "EnumAssignmentStatus.FAILED"

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumAssignmentStatus("ASSIGNED") == EnumAssignmentStatus.ASSIGNED
        assert EnumAssignmentStatus("EXECUTING") == EnumAssignmentStatus.EXECUTING
        assert EnumAssignmentStatus("COMPLETED") == EnumAssignmentStatus.COMPLETED
        assert EnumAssignmentStatus("FAILED") == EnumAssignmentStatus.FAILED

    def test_invalid_value_lookup_raises(self) -> None:
        """Test that invalid value lookup raises ValueError."""
        with pytest.raises(ValueError):
            EnumAssignmentStatus("INVALID")

    def test_is_str_enum(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumAssignmentStatus.ASSIGNED, str)
        assert isinstance(EnumAssignmentStatus.EXECUTING, str)


class TestEnumExecutionPattern:
    """Tests for EnumExecutionPattern enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumExecutionPattern.SEQUENTIAL
        assert EnumExecutionPattern.PARALLEL_COMPUTE
        assert EnumExecutionPattern.PIPELINE
        assert EnumExecutionPattern.SCATTER_GATHER

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumExecutionPattern.SEQUENTIAL.value == "sequential"
        assert EnumExecutionPattern.PARALLEL_COMPUTE.value == "parallel_compute"
        assert EnumExecutionPattern.PIPELINE.value == "pipeline"
        assert EnumExecutionPattern.SCATTER_GATHER.value == "scatter_gather"

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumExecutionPattern)
        assert len(values) == 4
        assert EnumExecutionPattern.SEQUENTIAL in values
        assert EnumExecutionPattern.PARALLEL_COMPUTE in values
        assert EnumExecutionPattern.PIPELINE in values
        assert EnumExecutionPattern.SCATTER_GATHER in values

    def test_enum_membership(self) -> None:
        """Test enum membership check."""
        assert EnumExecutionPattern.SEQUENTIAL in EnumExecutionPattern
        assert EnumExecutionPattern.PARALLEL_COMPUTE in EnumExecutionPattern
        assert EnumExecutionPattern.PIPELINE in EnumExecutionPattern
        assert EnumExecutionPattern.SCATTER_GATHER in EnumExecutionPattern

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        assert str(EnumExecutionPattern.SEQUENTIAL) == "EnumExecutionPattern.SEQUENTIAL"
        assert (
            str(EnumExecutionPattern.PARALLEL_COMPUTE)
            == "EnumExecutionPattern.PARALLEL_COMPUTE"
        )
        assert str(EnumExecutionPattern.PIPELINE) == "EnumExecutionPattern.PIPELINE"
        assert (
            str(EnumExecutionPattern.SCATTER_GATHER)
            == "EnumExecutionPattern.SCATTER_GATHER"
        )

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumExecutionPattern("sequential") == EnumExecutionPattern.SEQUENTIAL
        assert (
            EnumExecutionPattern("parallel_compute")
            == EnumExecutionPattern.PARALLEL_COMPUTE
        )
        assert EnumExecutionPattern("pipeline") == EnumExecutionPattern.PIPELINE
        assert (
            EnumExecutionPattern("scatter_gather")
            == EnumExecutionPattern.SCATTER_GATHER
        )

    def test_invalid_value_lookup_raises(self) -> None:
        """Test that invalid value lookup raises ValueError."""
        with pytest.raises(ValueError):
            EnumExecutionPattern("invalid_pattern")

    def test_is_str_enum(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumExecutionPattern.SEQUENTIAL, str)
        assert isinstance(EnumExecutionPattern.PARALLEL_COMPUTE, str)

    def test_lowercase_values(self) -> None:
        """Test that execution pattern values are lowercase."""
        for pattern in EnumExecutionPattern:
            assert pattern.value == pattern.value.lower()


class TestEnumFailureRecoveryStrategy:
    """Tests for EnumFailureRecoveryStrategy enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumFailureRecoveryStrategy.RETRY
        assert EnumFailureRecoveryStrategy.ROLLBACK
        assert EnumFailureRecoveryStrategy.COMPENSATE
        assert EnumFailureRecoveryStrategy.ABORT

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumFailureRecoveryStrategy.RETRY.value == "RETRY"
        assert EnumFailureRecoveryStrategy.ROLLBACK.value == "ROLLBACK"
        assert EnumFailureRecoveryStrategy.COMPENSATE.value == "COMPENSATE"
        assert EnumFailureRecoveryStrategy.ABORT.value == "ABORT"

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumFailureRecoveryStrategy)
        assert len(values) == 4
        assert EnumFailureRecoveryStrategy.RETRY in values
        assert EnumFailureRecoveryStrategy.ROLLBACK in values
        assert EnumFailureRecoveryStrategy.COMPENSATE in values
        assert EnumFailureRecoveryStrategy.ABORT in values

    def test_enum_membership(self) -> None:
        """Test enum membership check."""
        assert EnumFailureRecoveryStrategy.RETRY in EnumFailureRecoveryStrategy
        assert EnumFailureRecoveryStrategy.ROLLBACK in EnumFailureRecoveryStrategy
        assert EnumFailureRecoveryStrategy.COMPENSATE in EnumFailureRecoveryStrategy
        assert EnumFailureRecoveryStrategy.ABORT in EnumFailureRecoveryStrategy

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        assert (
            str(EnumFailureRecoveryStrategy.RETRY)
            == "EnumFailureRecoveryStrategy.RETRY"
        )
        assert (
            str(EnumFailureRecoveryStrategy.ROLLBACK)
            == "EnumFailureRecoveryStrategy.ROLLBACK"
        )
        assert (
            str(EnumFailureRecoveryStrategy.COMPENSATE)
            == "EnumFailureRecoveryStrategy.COMPENSATE"
        )
        assert (
            str(EnumFailureRecoveryStrategy.ABORT)
            == "EnumFailureRecoveryStrategy.ABORT"
        )

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumFailureRecoveryStrategy("RETRY") == EnumFailureRecoveryStrategy.RETRY
        assert (
            EnumFailureRecoveryStrategy("ROLLBACK")
            == EnumFailureRecoveryStrategy.ROLLBACK
        )
        assert (
            EnumFailureRecoveryStrategy("COMPENSATE")
            == EnumFailureRecoveryStrategy.COMPENSATE
        )
        assert EnumFailureRecoveryStrategy("ABORT") == EnumFailureRecoveryStrategy.ABORT

    def test_invalid_value_lookup_raises(self) -> None:
        """Test that invalid value lookup raises ValueError."""
        with pytest.raises(ValueError):
            EnumFailureRecoveryStrategy("INVALID")

    def test_is_str_enum(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumFailureRecoveryStrategy.RETRY, str)
        assert isinstance(EnumFailureRecoveryStrategy.ABORT, str)

    def test_uppercase_values(self) -> None:
        """Test that failure recovery strategy values are uppercase."""
        for strategy in EnumFailureRecoveryStrategy:
            assert strategy.value == strategy.value.upper()


class TestEnumWorkflowCoordinationIntegration:
    """Integration tests for workflow coordination enums."""

    def test_all_enums_are_str_enums(self) -> None:
        """Test that all workflow coordination enums inherit from str."""
        # Verify all enums can be used as strings
        assert "CREATED" in EnumWorkflowStatus.CREATED
        assert "ASSIGNED" in EnumAssignmentStatus.ASSIGNED
        assert "sequential" in EnumExecutionPattern.SEQUENTIAL
        assert "RETRY" in EnumFailureRecoveryStrategy.RETRY

    def test_enum_names_match_values_for_uppercase_enums(self) -> None:
        """Test that enum names match values for uppercase enums."""
        for status in EnumWorkflowStatus:
            assert status.name == status.value

        for status in EnumAssignmentStatus:
            assert status.name == status.value

        for strategy in EnumFailureRecoveryStrategy:
            assert strategy.name == strategy.value

    def test_execution_pattern_names_are_uppercase(self) -> None:
        """Test that ExecutionPattern enum names are uppercase."""
        for pattern in EnumExecutionPattern:
            assert pattern.name == pattern.name.upper()

    def test_enum_value_uniqueness(self) -> None:
        """Test that all enum values within each enum are unique."""
        workflow_values = [s.value for s in EnumWorkflowStatus]
        assert len(workflow_values) == len(set(workflow_values))

        assignment_values = [s.value for s in EnumAssignmentStatus]
        assert len(assignment_values) == len(set(assignment_values))

        execution_values = [p.value for p in EnumExecutionPattern]
        assert len(execution_values) == len(set(execution_values))

        recovery_values = [s.value for s in EnumFailureRecoveryStrategy]
        assert len(recovery_values) == len(set(recovery_values))

    def test_shared_value_names_across_enums(self) -> None:
        """Test enums with same-named values have consistent semantics."""
        # COMPLETED exists in both WorkflowStatus and AssignmentStatus
        assert EnumWorkflowStatus.COMPLETED.value == "COMPLETED"
        assert EnumAssignmentStatus.COMPLETED.value == "COMPLETED"

        # FAILED exists in both WorkflowStatus and AssignmentStatus
        assert EnumWorkflowStatus.FAILED.value == "FAILED"
        assert EnumAssignmentStatus.FAILED.value == "FAILED"

    def test_enum_comparison(self) -> None:
        """Test enum value comparisons."""
        # Same enum comparisons
        assert EnumWorkflowStatus.CREATED == EnumWorkflowStatus.CREATED
        assert EnumWorkflowStatus.CREATED != EnumWorkflowStatus.RUNNING

        # String comparisons (str enum feature)
        assert EnumWorkflowStatus.CREATED == "CREATED"
        assert EnumExecutionPattern.SEQUENTIAL == "sequential"

    def test_enum_hashing(self) -> None:
        """Test that enum values can be used in sets and as dict keys."""
        # Set usage
        status_set = {EnumWorkflowStatus.CREATED, EnumWorkflowStatus.RUNNING}
        assert len(status_set) == 2
        assert EnumWorkflowStatus.CREATED in status_set

        # Dict key usage
        status_dict = {
            EnumWorkflowStatus.CREATED: "initial",
            EnumWorkflowStatus.RUNNING: "active",
        }
        assert status_dict[EnumWorkflowStatus.CREATED] == "initial"
