# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for enum_workflow_coordination.py.

Tests for workflow coordination enums including EnumAssignmentStatus,
EnumExecutionPattern, and EnumFailureRecoveryStrategy.

Note: EnumWorkflowStatus was consolidated into enum_workflow_status.py per OMN-1310.
"""

import pytest

from omnibase_core.enums.enum_workflow_coordination import (
    EnumAssignmentStatus,
    EnumExecutionPattern,
    EnumFailureRecoveryStrategy,
)
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus


@pytest.mark.unit
class TestEnumWorkflowStatus:
    """Tests for EnumWorkflowStatus enum (canonical version from enum_workflow_status.py)."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumWorkflowStatus.PENDING
        assert EnumWorkflowStatus.RUNNING
        assert EnumWorkflowStatus.COMPLETED
        assert EnumWorkflowStatus.FAILED
        assert EnumWorkflowStatus.CANCELLED
        assert EnumWorkflowStatus.PAUSED

    def test_string_representations(self) -> None:
        """Test string values are correct (lowercase per canonical spec)."""
        assert EnumWorkflowStatus.PENDING.value == "pending"
        assert EnumWorkflowStatus.RUNNING.value == "running"
        assert EnumWorkflowStatus.COMPLETED.value == "completed"
        assert EnumWorkflowStatus.FAILED.value == "failed"
        assert EnumWorkflowStatus.CANCELLED.value == "cancelled"
        assert EnumWorkflowStatus.PAUSED.value == "paused"

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumWorkflowStatus)
        assert len(values) == 6
        assert EnumWorkflowStatus.PENDING in values
        assert EnumWorkflowStatus.RUNNING in values
        assert EnumWorkflowStatus.COMPLETED in values
        assert EnumWorkflowStatus.FAILED in values
        assert EnumWorkflowStatus.CANCELLED in values
        assert EnumWorkflowStatus.PAUSED in values

    def test_enum_membership(self) -> None:
        """Test enum membership check."""
        assert EnumWorkflowStatus.PENDING in EnumWorkflowStatus
        assert EnumWorkflowStatus.RUNNING in EnumWorkflowStatus
        assert EnumWorkflowStatus.COMPLETED in EnumWorkflowStatus
        assert EnumWorkflowStatus.FAILED in EnumWorkflowStatus
        assert EnumWorkflowStatus.CANCELLED in EnumWorkflowStatus
        assert EnumWorkflowStatus.PAUSED in EnumWorkflowStatus

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values (uses value due to __str__)."""
        assert str(EnumWorkflowStatus.PENDING) == "pending"
        assert str(EnumWorkflowStatus.RUNNING) == "running"
        assert str(EnumWorkflowStatus.COMPLETED) == "completed"
        assert str(EnumWorkflowStatus.FAILED) == "failed"
        assert str(EnumWorkflowStatus.CANCELLED) == "cancelled"
        assert str(EnumWorkflowStatus.PAUSED) == "paused"

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumWorkflowStatus("pending") == EnumWorkflowStatus.PENDING
        assert EnumWorkflowStatus("running") == EnumWorkflowStatus.RUNNING
        assert EnumWorkflowStatus("completed") == EnumWorkflowStatus.COMPLETED
        assert EnumWorkflowStatus("failed") == EnumWorkflowStatus.FAILED
        assert EnumWorkflowStatus("cancelled") == EnumWorkflowStatus.CANCELLED
        assert EnumWorkflowStatus("paused") == EnumWorkflowStatus.PAUSED

    def test_invalid_value_lookup_raises(self) -> None:
        """Test that invalid value lookup raises ValueError."""
        with pytest.raises(ValueError):
            EnumWorkflowStatus("INVALID")

    def test_is_str_enum(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumWorkflowStatus.PENDING, str)
        assert isinstance(EnumWorkflowStatus.RUNNING, str)

    def test_is_terminal(self) -> None:
        """Test is_terminal class method."""
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.COMPLETED)
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.FAILED)
        assert EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.CANCELLED)
        assert not EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.PENDING)
        assert not EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.RUNNING)
        assert not EnumWorkflowStatus.is_terminal(EnumWorkflowStatus.PAUSED)

    def test_is_active(self) -> None:
        """Test is_active class method."""
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.PENDING)
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.RUNNING)
        assert EnumWorkflowStatus.is_active(EnumWorkflowStatus.PAUSED)
        assert not EnumWorkflowStatus.is_active(EnumWorkflowStatus.COMPLETED)
        assert not EnumWorkflowStatus.is_active(EnumWorkflowStatus.FAILED)
        assert not EnumWorkflowStatus.is_active(EnumWorkflowStatus.CANCELLED)


@pytest.mark.unit
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
        """Test string conversion of enum values (str() returns value due to StrValueHelper mixin)."""
        assert str(EnumAssignmentStatus.ASSIGNED) == "ASSIGNED"
        assert str(EnumAssignmentStatus.EXECUTING) == "EXECUTING"
        assert str(EnumAssignmentStatus.COMPLETED) == "COMPLETED"
        assert str(EnumAssignmentStatus.FAILED) == "FAILED"

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


@pytest.mark.unit
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
        """Test string conversion of enum values (str() returns value due to StrValueHelper mixin)."""
        assert str(EnumExecutionPattern.SEQUENTIAL) == "sequential"
        assert str(EnumExecutionPattern.PARALLEL_COMPUTE) == "parallel_compute"
        assert str(EnumExecutionPattern.PIPELINE) == "pipeline"
        assert str(EnumExecutionPattern.SCATTER_GATHER) == "scatter_gather"

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


@pytest.mark.unit
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
        """Test string conversion of enum values (str() returns value due to StrValueHelper mixin)."""
        assert str(EnumFailureRecoveryStrategy.RETRY) == "RETRY"
        assert str(EnumFailureRecoveryStrategy.ROLLBACK) == "ROLLBACK"
        assert str(EnumFailureRecoveryStrategy.COMPENSATE) == "COMPENSATE"
        assert str(EnumFailureRecoveryStrategy.ABORT) == "ABORT"

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


@pytest.mark.unit
class TestEnumWorkflowCoordinationIntegration:
    """Integration tests for workflow coordination enums."""

    def test_all_enums_are_str_enums(self) -> None:
        """Test that all workflow coordination enums inherit from str."""
        # Verify all enums can be used as strings
        assert "pending" in EnumWorkflowStatus.PENDING
        assert "ASSIGNED" in EnumAssignmentStatus.ASSIGNED
        assert "sequential" in EnumExecutionPattern.SEQUENTIAL
        assert "RETRY" in EnumFailureRecoveryStrategy.RETRY

    def test_enum_names_match_values_for_uppercase_enums(self) -> None:
        """Test that enum names match values for uppercase enums."""
        # Note: EnumWorkflowStatus uses lowercase values, so names don't match values
        # Only test enums that use UPPER_SNAKE_CASE values
        for status in EnumAssignmentStatus:
            assert status.name == status.value

        for strategy in EnumFailureRecoveryStrategy:
            assert strategy.name == strategy.value

    def test_workflow_status_uses_lowercase_values(self) -> None:
        """Test that EnumWorkflowStatus uses lowercase values (canonical spec)."""
        for status in EnumWorkflowStatus:
            assert status.value == status.value.lower()

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

    def test_shared_member_names_across_enums(self) -> None:
        """Test enums with same-named members have semantically consistent meaning."""
        # COMPLETED exists in both WorkflowStatus (lowercase) and AssignmentStatus (uppercase)
        assert EnumWorkflowStatus.COMPLETED.value == "completed"
        assert EnumAssignmentStatus.COMPLETED.value == "COMPLETED"

        # FAILED exists in both WorkflowStatus (lowercase) and AssignmentStatus (uppercase)
        assert EnumWorkflowStatus.FAILED.value == "failed"
        assert EnumAssignmentStatus.FAILED.value == "FAILED"

    def test_enum_comparison(self) -> None:
        """Test enum value comparisons."""
        # Same enum comparisons
        assert EnumWorkflowStatus.PENDING == EnumWorkflowStatus.PENDING
        assert EnumWorkflowStatus.PENDING != EnumWorkflowStatus.RUNNING

        # String comparisons (str enum feature)
        assert EnumWorkflowStatus.PENDING == "pending"
        assert EnumExecutionPattern.SEQUENTIAL == "sequential"

    def test_enum_hashing(self) -> None:
        """Test that enum values can be used in sets and as dict keys."""
        # Set usage
        status_set = {EnumWorkflowStatus.PENDING, EnumWorkflowStatus.RUNNING}
        assert len(status_set) == 2
        assert EnumWorkflowStatus.PENDING in status_set

        # Dict key usage
        status_dict = {
            EnumWorkflowStatus.PENDING: "initial",
            EnumWorkflowStatus.RUNNING: "active",
        }
        assert status_dict[EnumWorkflowStatus.PENDING] == "initial"
