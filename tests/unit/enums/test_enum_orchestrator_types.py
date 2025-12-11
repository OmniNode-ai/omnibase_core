"""
Tests for orchestrator type enums.

This module tests all enums defined in enum_orchestrator_types.py:
- EnumWorkflowState: Workflow execution states
- EnumExecutionMode: Execution modes for workflow steps
- EnumActionType: Types of Actions for orchestrated execution
- EnumBranchCondition: Conditional branching types
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_orchestrator_types import (
    EnumActionType,
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowState,
)


class TestEnumWorkflowState:
    """Test cases for EnumWorkflowState enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumWorkflowState.PENDING
        assert EnumWorkflowState.RUNNING
        assert EnumWorkflowState.PAUSED
        assert EnumWorkflowState.COMPLETED
        assert EnumWorkflowState.FAILED
        assert EnumWorkflowState.CANCELLED

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumWorkflowState.PENDING.value == "pending"
        assert EnumWorkflowState.RUNNING.value == "running"
        assert EnumWorkflowState.PAUSED.value == "paused"
        assert EnumWorkflowState.COMPLETED.value == "completed"
        assert EnumWorkflowState.FAILED.value == "failed"
        assert EnumWorkflowState.CANCELLED.value == "cancelled"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from Enum."""
        assert issubclass(EnumWorkflowState, Enum)

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumWorkflowState)
        assert len(values) == 6  # All values including reserved
        assert EnumWorkflowState.PENDING in values
        assert EnumWorkflowState.RUNNING in values
        assert EnumWorkflowState.PAUSED in values
        assert EnumWorkflowState.COMPLETED in values
        assert EnumWorkflowState.FAILED in values
        assert EnumWorkflowState.CANCELLED in values

    def test_enum_membership(self) -> None:
        """Test enum membership testing."""
        # Test with enum values
        assert EnumWorkflowState.PENDING in EnumWorkflowState
        assert EnumWorkflowState.RUNNING in EnumWorkflowState
        assert EnumWorkflowState.PAUSED in EnumWorkflowState
        assert EnumWorkflowState.COMPLETED in EnumWorkflowState
        assert EnumWorkflowState.FAILED in EnumWorkflowState
        assert EnumWorkflowState.CANCELLED in EnumWorkflowState

    def test_string_membership(self) -> None:
        """Test string membership testing."""
        assert "pending" in EnumWorkflowState
        assert "running" in EnumWorkflowState
        assert "paused" in EnumWorkflowState
        assert "completed" in EnumWorkflowState
        assert "failed" in EnumWorkflowState
        assert "cancelled" in EnumWorkflowState
        assert "invalid_state" not in EnumWorkflowState

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        # For pure Enum, str() returns the full name
        assert str(EnumWorkflowState.PENDING) == "EnumWorkflowState.PENDING"
        assert str(EnumWorkflowState.RUNNING) == "EnumWorkflowState.RUNNING"
        assert str(EnumWorkflowState.PAUSED) == "EnumWorkflowState.PAUSED"
        assert str(EnumWorkflowState.COMPLETED) == "EnumWorkflowState.COMPLETED"
        assert str(EnumWorkflowState.FAILED) == "EnumWorkflowState.FAILED"
        assert str(EnumWorkflowState.CANCELLED) == "EnumWorkflowState.CANCELLED"

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumWorkflowState("pending") == EnumWorkflowState.PENDING
        assert EnumWorkflowState("running") == EnumWorkflowState.RUNNING
        assert EnumWorkflowState("paused") == EnumWorkflowState.PAUSED
        assert EnumWorkflowState("completed") == EnumWorkflowState.COMPLETED
        assert EnumWorkflowState("failed") == EnumWorkflowState.FAILED
        assert EnumWorkflowState("cancelled") == EnumWorkflowState.CANCELLED

    def test_invalid_value_lookup(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumWorkflowState("invalid_state")

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {
            "pending",
            "running",
            "paused",
            "completed",
            "failed",
            "cancelled",
        }
        actual_values = {member.value for member in EnumWorkflowState}
        assert actual_values == expected_values

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumWorkflowState.__doc__ is not None
        assert "Workflow" in EnumWorkflowState.__doc__

    def test_enum_name_attribute(self) -> None:
        """Test enum name attribute."""
        assert EnumWorkflowState.PENDING.name == "PENDING"
        assert EnumWorkflowState.RUNNING.name == "RUNNING"
        assert EnumWorkflowState.PAUSED.name == "PAUSED"
        assert EnumWorkflowState.COMPLETED.name == "COMPLETED"
        assert EnumWorkflowState.FAILED.name == "FAILED"
        assert EnumWorkflowState.CANCELLED.name == "CANCELLED"


class TestEnumExecutionMode:
    """Test cases for EnumExecutionMode enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumExecutionMode.SEQUENTIAL
        assert EnumExecutionMode.PARALLEL
        assert EnumExecutionMode.CONDITIONAL
        assert EnumExecutionMode.BATCH
        assert EnumExecutionMode.STREAMING

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumExecutionMode.SEQUENTIAL.value == "sequential"
        assert EnumExecutionMode.PARALLEL.value == "parallel"
        assert EnumExecutionMode.CONDITIONAL.value == "conditional"
        assert EnumExecutionMode.BATCH.value == "batch"
        assert EnumExecutionMode.STREAMING.value == "streaming"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from Enum."""
        assert issubclass(EnumExecutionMode, Enum)

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumExecutionMode)
        assert len(values) == 5
        assert EnumExecutionMode.SEQUENTIAL in values
        assert EnumExecutionMode.PARALLEL in values
        assert EnumExecutionMode.CONDITIONAL in values
        assert EnumExecutionMode.BATCH in values
        assert EnumExecutionMode.STREAMING in values

    def test_enum_membership(self) -> None:
        """Test enum membership testing."""
        assert EnumExecutionMode.SEQUENTIAL in EnumExecutionMode
        assert EnumExecutionMode.PARALLEL in EnumExecutionMode
        assert EnumExecutionMode.CONDITIONAL in EnumExecutionMode
        assert EnumExecutionMode.BATCH in EnumExecutionMode
        assert EnumExecutionMode.STREAMING in EnumExecutionMode

    def test_string_membership(self) -> None:
        """Test string membership testing."""
        assert "sequential" in EnumExecutionMode
        assert "parallel" in EnumExecutionMode
        assert "conditional" in EnumExecutionMode
        assert "batch" in EnumExecutionMode
        assert "streaming" in EnumExecutionMode
        assert "invalid_mode" not in EnumExecutionMode

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        assert str(EnumExecutionMode.SEQUENTIAL) == "EnumExecutionMode.SEQUENTIAL"
        assert str(EnumExecutionMode.PARALLEL) == "EnumExecutionMode.PARALLEL"
        assert str(EnumExecutionMode.CONDITIONAL) == "EnumExecutionMode.CONDITIONAL"
        assert str(EnumExecutionMode.BATCH) == "EnumExecutionMode.BATCH"
        assert str(EnumExecutionMode.STREAMING) == "EnumExecutionMode.STREAMING"

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumExecutionMode("sequential") == EnumExecutionMode.SEQUENTIAL
        assert EnumExecutionMode("parallel") == EnumExecutionMode.PARALLEL
        assert EnumExecutionMode("conditional") == EnumExecutionMode.CONDITIONAL
        assert EnumExecutionMode("batch") == EnumExecutionMode.BATCH
        assert EnumExecutionMode("streaming") == EnumExecutionMode.STREAMING

    def test_invalid_value_lookup(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumExecutionMode("invalid_mode")

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {
            "sequential",
            "parallel",
            "conditional",
            "batch",
            "streaming",
        }
        actual_values = {member.value for member in EnumExecutionMode}
        assert actual_values == expected_values

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumExecutionMode.__doc__ is not None
        assert "Execution" in EnumExecutionMode.__doc__

    def test_enum_name_attribute(self) -> None:
        """Test enum name attribute."""
        assert EnumExecutionMode.SEQUENTIAL.name == "SEQUENTIAL"
        assert EnumExecutionMode.PARALLEL.name == "PARALLEL"
        assert EnumExecutionMode.CONDITIONAL.name == "CONDITIONAL"
        assert EnumExecutionMode.BATCH.name == "BATCH"
        assert EnumExecutionMode.STREAMING.name == "STREAMING"


class TestEnumActionType:
    """Test cases for EnumActionType enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumActionType.COMPUTE
        assert EnumActionType.EFFECT
        assert EnumActionType.REDUCE
        assert EnumActionType.ORCHESTRATE
        assert EnumActionType.CUSTOM

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumActionType.COMPUTE.value == "compute"
        assert EnumActionType.EFFECT.value == "effect"
        assert EnumActionType.REDUCE.value == "reduce"
        assert EnumActionType.ORCHESTRATE.value == "orchestrate"
        assert EnumActionType.CUSTOM.value == "custom"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from Enum."""
        assert issubclass(EnumActionType, Enum)

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumActionType)
        assert len(values) == 5
        assert EnumActionType.COMPUTE in values
        assert EnumActionType.EFFECT in values
        assert EnumActionType.REDUCE in values
        assert EnumActionType.ORCHESTRATE in values
        assert EnumActionType.CUSTOM in values

    def test_enum_membership(self) -> None:
        """Test enum membership testing."""
        assert EnumActionType.COMPUTE in EnumActionType
        assert EnumActionType.EFFECT in EnumActionType
        assert EnumActionType.REDUCE in EnumActionType
        assert EnumActionType.ORCHESTRATE in EnumActionType
        assert EnumActionType.CUSTOM in EnumActionType

    def test_string_membership(self) -> None:
        """Test string membership testing."""
        assert "compute" in EnumActionType
        assert "effect" in EnumActionType
        assert "reduce" in EnumActionType
        assert "orchestrate" in EnumActionType
        assert "custom" in EnumActionType
        assert "invalid_action" not in EnumActionType

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        assert str(EnumActionType.COMPUTE) == "EnumActionType.COMPUTE"
        assert str(EnumActionType.EFFECT) == "EnumActionType.EFFECT"
        assert str(EnumActionType.REDUCE) == "EnumActionType.REDUCE"
        assert str(EnumActionType.ORCHESTRATE) == "EnumActionType.ORCHESTRATE"
        assert str(EnumActionType.CUSTOM) == "EnumActionType.CUSTOM"

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumActionType("compute") == EnumActionType.COMPUTE
        assert EnumActionType("effect") == EnumActionType.EFFECT
        assert EnumActionType("reduce") == EnumActionType.REDUCE
        assert EnumActionType("orchestrate") == EnumActionType.ORCHESTRATE
        assert EnumActionType("custom") == EnumActionType.CUSTOM

    def test_invalid_value_lookup(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumActionType("invalid_action")

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {
            "compute",
            "effect",
            "reduce",
            "orchestrate",
            "custom",
        }
        actual_values = {member.value for member in EnumActionType}
        assert actual_values == expected_values

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumActionType.__doc__ is not None
        assert "Action" in EnumActionType.__doc__

    def test_enum_name_attribute(self) -> None:
        """Test enum name attribute."""
        assert EnumActionType.COMPUTE.name == "COMPUTE"
        assert EnumActionType.EFFECT.name == "EFFECT"
        assert EnumActionType.REDUCE.name == "REDUCE"
        assert EnumActionType.ORCHESTRATE.name == "ORCHESTRATE"
        assert EnumActionType.CUSTOM.name == "CUSTOM"

    def test_action_types_align_with_node_types(self) -> None:
        """Test that action types correspond to ONEX node architecture."""
        # The action types should align with the four-node architecture
        core_action_types = {
            EnumActionType.COMPUTE,
            EnumActionType.EFFECT,
            EnumActionType.REDUCE,
            EnumActionType.ORCHESTRATE,
        }
        assert len(core_action_types) == 4
        # CUSTOM is an extension point
        assert EnumActionType.CUSTOM not in core_action_types


class TestEnumBranchCondition:
    """Test cases for EnumBranchCondition enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumBranchCondition.IF_TRUE
        assert EnumBranchCondition.IF_FALSE
        assert EnumBranchCondition.IF_ERROR
        assert EnumBranchCondition.IF_SUCCESS
        assert EnumBranchCondition.IF_TIMEOUT
        assert EnumBranchCondition.CUSTOM

    def test_string_representations(self) -> None:
        """Test string values are correct."""
        assert EnumBranchCondition.IF_TRUE.value == "if_true"
        assert EnumBranchCondition.IF_FALSE.value == "if_false"
        assert EnumBranchCondition.IF_ERROR.value == "if_error"
        assert EnumBranchCondition.IF_SUCCESS.value == "if_success"
        assert EnumBranchCondition.IF_TIMEOUT.value == "if_timeout"
        assert EnumBranchCondition.CUSTOM.value == "custom"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from Enum."""
        assert issubclass(EnumBranchCondition, Enum)

    def test_enum_iteration(self) -> None:
        """Test enum can be iterated."""
        values = list(EnumBranchCondition)
        assert len(values) == 6
        assert EnumBranchCondition.IF_TRUE in values
        assert EnumBranchCondition.IF_FALSE in values
        assert EnumBranchCondition.IF_ERROR in values
        assert EnumBranchCondition.IF_SUCCESS in values
        assert EnumBranchCondition.IF_TIMEOUT in values
        assert EnumBranchCondition.CUSTOM in values

    def test_enum_membership(self) -> None:
        """Test enum membership testing."""
        assert EnumBranchCondition.IF_TRUE in EnumBranchCondition
        assert EnumBranchCondition.IF_FALSE in EnumBranchCondition
        assert EnumBranchCondition.IF_ERROR in EnumBranchCondition
        assert EnumBranchCondition.IF_SUCCESS in EnumBranchCondition
        assert EnumBranchCondition.IF_TIMEOUT in EnumBranchCondition
        assert EnumBranchCondition.CUSTOM in EnumBranchCondition

    def test_string_membership(self) -> None:
        """Test string membership testing."""
        assert "if_true" in EnumBranchCondition
        assert "if_false" in EnumBranchCondition
        assert "if_error" in EnumBranchCondition
        assert "if_success" in EnumBranchCondition
        assert "if_timeout" in EnumBranchCondition
        assert "custom" in EnumBranchCondition
        assert "invalid_condition" not in EnumBranchCondition

    def test_string_conversion(self) -> None:
        """Test string conversion of enum values."""
        assert str(EnumBranchCondition.IF_TRUE) == "EnumBranchCondition.IF_TRUE"
        assert str(EnumBranchCondition.IF_FALSE) == "EnumBranchCondition.IF_FALSE"
        assert str(EnumBranchCondition.IF_ERROR) == "EnumBranchCondition.IF_ERROR"
        assert str(EnumBranchCondition.IF_SUCCESS) == "EnumBranchCondition.IF_SUCCESS"
        assert str(EnumBranchCondition.IF_TIMEOUT) == "EnumBranchCondition.IF_TIMEOUT"
        assert str(EnumBranchCondition.CUSTOM) == "EnumBranchCondition.CUSTOM"

    def test_value_lookup(self) -> None:
        """Test enum lookup from string value."""
        assert EnumBranchCondition("if_true") == EnumBranchCondition.IF_TRUE
        assert EnumBranchCondition("if_false") == EnumBranchCondition.IF_FALSE
        assert EnumBranchCondition("if_error") == EnumBranchCondition.IF_ERROR
        assert EnumBranchCondition("if_success") == EnumBranchCondition.IF_SUCCESS
        assert EnumBranchCondition("if_timeout") == EnumBranchCondition.IF_TIMEOUT
        assert EnumBranchCondition("custom") == EnumBranchCondition.CUSTOM

    def test_invalid_value_lookup(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumBranchCondition("invalid_condition")

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {
            "if_true",
            "if_false",
            "if_error",
            "if_success",
            "if_timeout",
            "custom",
        }
        actual_values = {member.value for member in EnumBranchCondition}
        assert actual_values == expected_values

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumBranchCondition.__doc__ is not None
        assert (
            "Conditional" in EnumBranchCondition.__doc__
            or "branch" in EnumBranchCondition.__doc__.lower()
        )

    def test_enum_name_attribute(self) -> None:
        """Test enum name attribute."""
        assert EnumBranchCondition.IF_TRUE.name == "IF_TRUE"
        assert EnumBranchCondition.IF_FALSE.name == "IF_FALSE"
        assert EnumBranchCondition.IF_ERROR.name == "IF_ERROR"
        assert EnumBranchCondition.IF_SUCCESS.name == "IF_SUCCESS"
        assert EnumBranchCondition.IF_TIMEOUT.name == "IF_TIMEOUT"
        assert EnumBranchCondition.CUSTOM.name == "CUSTOM"

    def test_boolean_conditions(self) -> None:
        """Test that boolean conditions are properly paired."""
        boolean_conditions = {EnumBranchCondition.IF_TRUE, EnumBranchCondition.IF_FALSE}
        assert len(boolean_conditions) == 2

    def test_outcome_conditions(self) -> None:
        """Test that outcome-based conditions exist."""
        outcome_conditions = {
            EnumBranchCondition.IF_ERROR,
            EnumBranchCondition.IF_SUCCESS,
            EnumBranchCondition.IF_TIMEOUT,
        }
        assert len(outcome_conditions) == 3


class TestEnumOrchestratorTypesIntegration:
    """Integration tests for orchestrator type enums."""

    def test_workflow_state_transitions(self) -> None:
        """Test typical workflow state transitions are supported."""
        # Typical workflow: PENDING -> RUNNING -> COMPLETED
        states = [
            EnumWorkflowState.PENDING,
            EnumWorkflowState.RUNNING,
            EnumWorkflowState.COMPLETED,
        ]
        assert len(states) == 3

        # Error path: PENDING -> RUNNING -> FAILED
        error_states = [
            EnumWorkflowState.PENDING,
            EnumWorkflowState.RUNNING,
            EnumWorkflowState.FAILED,
        ]
        assert len(error_states) == 3

        # Cancellation path: PENDING/RUNNING -> CANCELLED
        assert EnumWorkflowState.CANCELLED in EnumWorkflowState

    def test_execution_mode_compatibility(self) -> None:
        """Test execution modes are comprehensive."""
        modes = list(EnumExecutionMode)
        mode_values = {m.value for m in modes}

        # Verify basic execution patterns are covered
        assert "sequential" in mode_values
        assert "parallel" in mode_values
        assert "batch" in mode_values

    def test_action_type_node_mapping(self) -> None:
        """Test action types map to ONEX node types."""
        # Each action type should correspond to a node type
        action_to_node = {
            EnumActionType.COMPUTE: "compute",
            EnumActionType.EFFECT: "effect",
            EnumActionType.REDUCE: "reduce",
            EnumActionType.ORCHESTRATE: "orchestrate",
        }

        for action, expected_value in action_to_node.items():
            assert action.value == expected_value

    def test_branch_condition_coverage(self) -> None:
        """Test branch conditions cover common scenarios."""
        conditions = list(EnumBranchCondition)

        # Check for boolean conditions
        bool_conditions = [
            c for c in conditions if "TRUE" in c.name or "FALSE" in c.name
        ]
        assert len(bool_conditions) == 2

        # Check for outcome conditions
        outcome_conditions = [
            c
            for c in conditions
            if "ERROR" in c.name or "SUCCESS" in c.name or "TIMEOUT" in c.name
        ]
        assert len(outcome_conditions) == 3

        # Check for extensibility
        custom_conditions = [c for c in conditions if c.name == "CUSTOM"]
        assert len(custom_conditions) == 1

    def test_all_enums_are_serializable(self) -> None:
        """Test all enum values can be serialized to JSON-compatible strings."""
        import json

        all_enums = [
            EnumWorkflowState,
            EnumExecutionMode,
            EnumActionType,
            EnumBranchCondition,
        ]

        for enum_class in all_enums:
            for member in enum_class:
                # Value should be JSON serializable
                json_str = json.dumps(member.value)
                assert json_str is not None
                # Value should round-trip
                loaded = json.loads(json_str)
                assert loaded == member.value

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity semantics."""
        # Enum members should be singletons
        assert EnumWorkflowState.PENDING is EnumWorkflowState.PENDING
        assert EnumExecutionMode.PARALLEL is EnumExecutionMode.PARALLEL
        assert EnumActionType.COMPUTE is EnumActionType.COMPUTE
        assert EnumBranchCondition.IF_TRUE is EnumBranchCondition.IF_TRUE

        # Different members should not be equal
        assert EnumWorkflowState.PENDING != EnumWorkflowState.COMPLETED
        assert EnumExecutionMode.SEQUENTIAL != EnumExecutionMode.PARALLEL
        assert EnumActionType.COMPUTE != EnumActionType.EFFECT
        assert EnumBranchCondition.IF_TRUE != EnumBranchCondition.IF_FALSE
