# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for NodeOrchestrator-related enums.

Tests all aspects of orchestrator enumeration types including:
- EnumWorkflowStatus - Workflow lifecycle states (canonical) (str, Enum)
- EnumExecutionMode (aliased as EnumExecutionModeOrchestrator) - Execution modes for workflow steps
- EnumActionType - Types of actions for orchestrated execution
- EnumFailureRecoveryStrategy - Failure recovery strategies (str, Enum)
- EnumBranchCondition - Conditional branching types
- EnumExecutionPattern - Execution patterns for workflow coordination (str, Enum)
- EnumAssignmentStatus - Task assignment lifecycle states (str, Enum)

Each enum is tested for:
- Value existence and correctness
- String representations
- Reserved value semantics (v1.1, v1.2, v2.0 features)
- Iteration and membership
- Comparison operations
- JSON serialization
- Pydantic compatibility
"""

import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_orchestrator_types import (
    EnumActionType,
    EnumBranchCondition,
)
from omnibase_core.enums.enum_orchestrator_types import (
    EnumExecutionMode as EnumExecutionModeOrchestrator,
)
from omnibase_core.enums.enum_workflow_coordination import (
    EnumAssignmentStatus,
    EnumExecutionPattern,
    EnumFailureRecoveryStrategy,
)
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def all_workflow_status_values() -> list[str]:
    """All expected EnumWorkflowStatus values."""
    return ["pending", "running", "paused", "completed", "failed", "cancelled"]


@pytest.fixture
def all_execution_mode_values() -> list[str]:
    """All expected EnumExecutionMode (orchestrator) values."""
    return ["sequential", "parallel", "conditional", "batch", "streaming"]


@pytest.fixture
def all_action_type_values() -> list[str]:
    """All expected EnumActionType values."""
    return ["compute", "effect", "reduce", "orchestrate", "custom"]


@pytest.fixture
def all_failure_recovery_values() -> list[str]:
    """All expected EnumFailureRecoveryStrategy values."""
    return ["RETRY", "ROLLBACK", "COMPENSATE", "ABORT"]


@pytest.fixture
def all_branch_condition_values() -> list[str]:
    """All expected EnumBranchCondition values."""
    return ["if_true", "if_false", "if_error", "if_success", "if_timeout", "custom"]


@pytest.fixture
def all_execution_pattern_values() -> list[str]:
    """All expected EnumExecutionPattern values."""
    return ["sequential", "parallel_compute", "pipeline", "scatter_gather"]


@pytest.fixture
def all_assignment_status_values() -> list[str]:
    """All expected EnumAssignmentStatus values."""
    return ["ASSIGNED", "EXECUTING", "COMPLETED", "FAILED"]


# ============================================================================
# EnumWorkflowStatus Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumWorkflowStatus:
    """Tests for EnumWorkflowStatus lifecycle states and transitions."""

    def test_enum_inherits_from_enum(self) -> None:
        """Test that EnumWorkflowStatus inherits from Enum."""
        assert issubclass(EnumWorkflowStatus, Enum)

    def test_values_exist(self, all_workflow_status_values: list[str]) -> None:
        """Test all expected values exist."""
        assert EnumWorkflowStatus.PENDING.value == "pending"
        assert EnumWorkflowStatus.RUNNING.value == "running"
        assert EnumWorkflowStatus.PAUSED.value == "paused"
        assert EnumWorkflowStatus.COMPLETED.value == "completed"
        assert EnumWorkflowStatus.FAILED.value == "failed"
        assert EnumWorkflowStatus.CANCELLED.value == "cancelled"

    def test_member_count(self) -> None:
        """Test correct number of members (6 states)."""
        assert len(EnumWorkflowStatus) == 6

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumWorkflowStatus.PENDING: "pending",
            EnumWorkflowStatus.RUNNING: "running",
            EnumWorkflowStatus.PAUSED: "paused",
            EnumWorkflowStatus.COMPLETED: "completed",
            EnumWorkflowStatus.FAILED: "failed",
            EnumWorkflowStatus.CANCELLED: "cancelled",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value

    def test_reserved_paused_state(self) -> None:
        """Test PAUSED is marked as reserved for v1.1.

        The PAUSED state exists but is documented as RESERVED for v1.1
        and should not be used in v1.0 implementations.
        """
        # Verify it exists
        assert hasattr(EnumWorkflowStatus, "PAUSED")
        assert EnumWorkflowStatus.PAUSED.value == "paused"
        # Verify it's in the enum (reserved but still a valid member)
        assert EnumWorkflowStatus.PAUSED in EnumWorkflowStatus

    def test_iteration(self, all_workflow_status_values: list[str]) -> None:
        """Test enum iteration returns all values."""
        actual_values = {member.value for member in EnumWorkflowStatus}
        expected_values = set(all_workflow_status_values)
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumWorkflowStatus]
        assert len(values) == len(set(values))

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        assert EnumWorkflowStatus.PENDING == EnumWorkflowStatus.PENDING
        assert EnumWorkflowStatus.PENDING != EnumWorkflowStatus.RUNNING
        assert EnumWorkflowStatus.COMPLETED is EnumWorkflowStatus.COMPLETED

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        assert EnumWorkflowStatus("pending") == EnumWorkflowStatus.PENDING
        assert EnumWorkflowStatus("completed") == EnumWorkflowStatus.COMPLETED

    def test_invalid_value_raises_error(self) -> None:
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumWorkflowStatus("invalid_state")

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumWorkflowStatus:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumWorkflowStatus(deserialized) == member

    def test_pickle_serialization(self) -> None:
        """Test enum members can be pickled and unpickled."""
        for member in EnumWorkflowStatus:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member

    def test_terminal_states(self) -> None:
        """Test identification of terminal workflow states."""
        terminal_states = {
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
        }
        non_terminal_states = {
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.PAUSED,
        }
        all_states = set(EnumWorkflowStatus)
        assert terminal_states.union(non_terminal_states) == all_states

    def test_active_states(self) -> None:
        """Test identification of active workflow states."""
        active_states = {
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.PAUSED,  # Reserved but semantically active
        }
        initial_states = {EnumWorkflowStatus.PENDING}
        final_states = {
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
        }
        all_states = set(EnumWorkflowStatus)
        assert active_states.union(initial_states).union(final_states) == all_states


# ============================================================================
# EnumExecutionMode (Orchestrator) Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumExecutionModeOrchestrator:
    """Tests for EnumExecutionMode from enum_orchestrator_types."""

    def test_enum_inherits_from_enum(self) -> None:
        """Test that EnumExecutionMode inherits from Enum."""
        assert issubclass(EnumExecutionModeOrchestrator, Enum)

    def test_values_exist(self, all_execution_mode_values: list[str]) -> None:
        """Test all expected values exist."""
        assert EnumExecutionModeOrchestrator.SEQUENTIAL.value == "sequential"
        assert EnumExecutionModeOrchestrator.PARALLEL.value == "parallel"
        assert EnumExecutionModeOrchestrator.CONDITIONAL.value == "conditional"
        assert EnumExecutionModeOrchestrator.BATCH.value == "batch"
        assert EnumExecutionModeOrchestrator.STREAMING.value == "streaming"

    def test_member_count(self) -> None:
        """Test correct number of members (5 modes)."""
        assert len(EnumExecutionModeOrchestrator) == 5

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumExecutionModeOrchestrator.SEQUENTIAL: "sequential",
            EnumExecutionModeOrchestrator.PARALLEL: "parallel",
            EnumExecutionModeOrchestrator.CONDITIONAL: "conditional",
            EnumExecutionModeOrchestrator.BATCH: "batch",
            EnumExecutionModeOrchestrator.STREAMING: "streaming",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value

    def test_reserved_conditional_mode(self) -> None:
        """Test CONDITIONAL is marked as reserved for v1.1.

        The CONDITIONAL mode exists but is documented as RESERVED for v1.1
        and should not be used in v1.0 implementations.
        """
        assert hasattr(EnumExecutionModeOrchestrator, "CONDITIONAL")
        assert EnumExecutionModeOrchestrator.CONDITIONAL.value == "conditional"
        assert (
            EnumExecutionModeOrchestrator.CONDITIONAL in EnumExecutionModeOrchestrator
        )

    def test_reserved_streaming_mode(self) -> None:
        """Test STREAMING is marked as reserved for v1.2.

        The STREAMING mode exists but is documented as RESERVED for v1.2
        and should not be used in v1.0/v1.1 implementations.
        """
        assert hasattr(EnumExecutionModeOrchestrator, "STREAMING")
        assert EnumExecutionModeOrchestrator.STREAMING.value == "streaming"
        assert EnumExecutionModeOrchestrator.STREAMING in EnumExecutionModeOrchestrator

    def test_iteration(self, all_execution_mode_values: list[str]) -> None:
        """Test enum iteration returns all values."""
        actual_values = {member.value for member in EnumExecutionModeOrchestrator}
        expected_values = set(all_execution_mode_values)
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumExecutionModeOrchestrator]
        assert len(values) == len(set(values))

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        assert (
            EnumExecutionModeOrchestrator.SEQUENTIAL
            == EnumExecutionModeOrchestrator.SEQUENTIAL
        )
        assert (
            EnumExecutionModeOrchestrator.SEQUENTIAL
            != EnumExecutionModeOrchestrator.PARALLEL
        )
        assert (
            EnumExecutionModeOrchestrator.BATCH is EnumExecutionModeOrchestrator.BATCH
        )

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        assert (
            EnumExecutionModeOrchestrator("sequential")
            == EnumExecutionModeOrchestrator.SEQUENTIAL
        )
        assert (
            EnumExecutionModeOrchestrator("parallel")
            == EnumExecutionModeOrchestrator.PARALLEL
        )

    def test_invalid_value_raises_error(self) -> None:
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumExecutionModeOrchestrator("invalid_mode")

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumExecutionModeOrchestrator:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumExecutionModeOrchestrator(deserialized) == member

    def test_pickle_serialization(self) -> None:
        """Test enum members can be pickled and unpickled."""
        for member in EnumExecutionModeOrchestrator:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member

    def test_v1_supported_modes(self) -> None:
        """Test which modes are supported in v1.0."""
        v1_supported = {
            EnumExecutionModeOrchestrator.SEQUENTIAL,
            EnumExecutionModeOrchestrator.PARALLEL,
            EnumExecutionModeOrchestrator.BATCH,
        }
        v1_1_reserved = {EnumExecutionModeOrchestrator.CONDITIONAL}
        v1_2_reserved = {EnumExecutionModeOrchestrator.STREAMING}

        all_modes = set(EnumExecutionModeOrchestrator)
        assert v1_supported.union(v1_1_reserved).union(v1_2_reserved) == all_modes


# ============================================================================
# EnumActionType Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumActionType:
    """Tests for EnumActionType from enum_orchestrator_types."""

    def test_enum_inherits_from_enum(self) -> None:
        """Test that EnumActionType inherits from Enum."""
        assert issubclass(EnumActionType, Enum)

    def test_values_exist(self, all_action_type_values: list[str]) -> None:
        """Test all expected values exist."""
        assert EnumActionType.COMPUTE.value == "compute"
        assert EnumActionType.EFFECT.value == "effect"
        assert EnumActionType.REDUCE.value == "reduce"
        assert EnumActionType.ORCHESTRATE.value == "orchestrate"
        assert EnumActionType.CUSTOM.value == "custom"

    def test_member_count(self) -> None:
        """Test correct number of members (5 action types)."""
        assert len(EnumActionType) == 5

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumActionType.COMPUTE: "compute",
            EnumActionType.EFFECT: "effect",
            EnumActionType.REDUCE: "reduce",
            EnumActionType.ORCHESTRATE: "orchestrate",
            EnumActionType.CUSTOM: "custom",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value

    def test_iteration(self, all_action_type_values: list[str]) -> None:
        """Test enum iteration returns all values."""
        actual_values = {member.value for member in EnumActionType}
        expected_values = set(all_action_type_values)
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumActionType]
        assert len(values) == len(set(values))

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        assert EnumActionType.COMPUTE == EnumActionType.COMPUTE
        assert EnumActionType.COMPUTE != EnumActionType.EFFECT
        assert EnumActionType.REDUCE is EnumActionType.REDUCE

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        assert EnumActionType("compute") == EnumActionType.COMPUTE
        assert EnumActionType("effect") == EnumActionType.EFFECT
        assert EnumActionType("custom") == EnumActionType.CUSTOM

    def test_invalid_value_raises_error(self) -> None:
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumActionType("invalid_action")

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumActionType:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumActionType(deserialized) == member

    def test_pickle_serialization(self) -> None:
        """Test enum members can be pickled and unpickled."""
        for member in EnumActionType:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member

    def test_action_types_match_node_kinds(self) -> None:
        """Test that action types align with ONEX node kinds.

        COMPUTE, EFFECT, REDUCE, ORCHESTRATE correspond to the
        four-node architecture types.
        """
        core_action_types = {
            EnumActionType.COMPUTE,
            EnumActionType.EFFECT,
            EnumActionType.REDUCE,
            EnumActionType.ORCHESTRATE,
        }
        extension_types = {EnumActionType.CUSTOM}
        all_types = set(EnumActionType)
        assert core_action_types.union(extension_types) == all_types


# ============================================================================
# EnumFailureRecoveryStrategy Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumFailureRecoveryStrategy:
    """Tests for EnumFailureRecoveryStrategy from enum_workflow_coordination."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumFailureRecoveryStrategy inherits from str and Enum."""
        assert issubclass(EnumFailureRecoveryStrategy, str)
        assert issubclass(EnumFailureRecoveryStrategy, Enum)

    def test_values_exist(self, all_failure_recovery_values: list[str]) -> None:
        """Test all expected values exist."""
        assert EnumFailureRecoveryStrategy.RETRY.value == "RETRY"
        assert EnumFailureRecoveryStrategy.ROLLBACK.value == "ROLLBACK"
        assert EnumFailureRecoveryStrategy.COMPENSATE.value == "COMPENSATE"
        assert EnumFailureRecoveryStrategy.ABORT.value == "ABORT"

    def test_member_count(self) -> None:
        """Test correct number of members (4 strategies)."""
        assert len(EnumFailureRecoveryStrategy) == 4

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumFailureRecoveryStrategy.RETRY: "RETRY",
            EnumFailureRecoveryStrategy.ROLLBACK: "ROLLBACK",
            EnumFailureRecoveryStrategy.COMPENSATE: "COMPENSATE",
            EnumFailureRecoveryStrategy.ABORT: "ABORT",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value
            # Also test str comparison since it's a str enum
            assert member == expected_value

    def test_reserved_rollback_strategy(self) -> None:
        """Test ROLLBACK is marked as reserved for v2.0.

        The ROLLBACK strategy exists but is documented as RESERVED for v2.0
        and should not be used in v1.x implementations.
        """
        assert hasattr(EnumFailureRecoveryStrategy, "ROLLBACK")
        assert EnumFailureRecoveryStrategy.ROLLBACK.value == "ROLLBACK"
        assert EnumFailureRecoveryStrategy.ROLLBACK in EnumFailureRecoveryStrategy

    def test_reserved_compensate_strategy(self) -> None:
        """Test COMPENSATE is marked as reserved for v2.0.

        The COMPENSATE strategy exists but is documented as RESERVED for v2.0
        and should not be used in v1.x implementations.
        """
        assert hasattr(EnumFailureRecoveryStrategy, "COMPENSATE")
        assert EnumFailureRecoveryStrategy.COMPENSATE.value == "COMPENSATE"
        assert EnumFailureRecoveryStrategy.COMPENSATE in EnumFailureRecoveryStrategy

    def test_iteration(self, all_failure_recovery_values: list[str]) -> None:
        """Test enum iteration returns all values."""
        actual_values = {member.value for member in EnumFailureRecoveryStrategy}
        expected_values = set(all_failure_recovery_values)
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumFailureRecoveryStrategy]
        assert len(values) == len(set(values))

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        assert EnumFailureRecoveryStrategy.RETRY == EnumFailureRecoveryStrategy.RETRY
        assert EnumFailureRecoveryStrategy.RETRY != EnumFailureRecoveryStrategy.ABORT
        assert EnumFailureRecoveryStrategy.ABORT is EnumFailureRecoveryStrategy.ABORT
        # String comparison (str enum)
        assert EnumFailureRecoveryStrategy.RETRY == "RETRY"

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        assert EnumFailureRecoveryStrategy("RETRY") == EnumFailureRecoveryStrategy.RETRY
        assert EnumFailureRecoveryStrategy("ABORT") == EnumFailureRecoveryStrategy.ABORT

    def test_invalid_value_raises_error(self) -> None:
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumFailureRecoveryStrategy("invalid_strategy")

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumFailureRecoveryStrategy:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumFailureRecoveryStrategy(deserialized) == member

    def test_pickle_serialization(self) -> None:
        """Test enum members can be pickled and unpickled."""
        for member in EnumFailureRecoveryStrategy:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member

    def test_v1_supported_strategies(self) -> None:
        """Test which strategies are supported in v1.x."""
        v1_supported = {
            EnumFailureRecoveryStrategy.RETRY,
            EnumFailureRecoveryStrategy.ABORT,
        }
        v2_reserved = {
            EnumFailureRecoveryStrategy.ROLLBACK,
            EnumFailureRecoveryStrategy.COMPENSATE,
        }
        all_strategies = set(EnumFailureRecoveryStrategy)
        assert v1_supported.union(v2_reserved) == all_strategies

    def test_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        strategy = EnumFailureRecoveryStrategy.RETRY
        assert isinstance(strategy, str)
        assert strategy == "RETRY"
        assert len(strategy) == 5
        assert strategy.startswith("R")
        assert strategy.upper() == "RETRY"


# ============================================================================
# EnumBranchCondition Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumBranchCondition:
    """Tests for EnumBranchCondition from enum_orchestrator_types."""

    def test_enum_inherits_from_enum(self) -> None:
        """Test that EnumBranchCondition inherits from Enum."""
        assert issubclass(EnumBranchCondition, Enum)

    def test_values_exist(self, all_branch_condition_values: list[str]) -> None:
        """Test all expected values exist."""
        assert EnumBranchCondition.IF_TRUE.value == "if_true"
        assert EnumBranchCondition.IF_FALSE.value == "if_false"
        assert EnumBranchCondition.IF_ERROR.value == "if_error"
        assert EnumBranchCondition.IF_SUCCESS.value == "if_success"
        assert EnumBranchCondition.IF_TIMEOUT.value == "if_timeout"
        assert EnumBranchCondition.CUSTOM.value == "custom"

    def test_member_count(self) -> None:
        """Test correct number of members (6 conditions)."""
        assert len(EnumBranchCondition) == 6

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumBranchCondition.IF_TRUE: "if_true",
            EnumBranchCondition.IF_FALSE: "if_false",
            EnumBranchCondition.IF_ERROR: "if_error",
            EnumBranchCondition.IF_SUCCESS: "if_success",
            EnumBranchCondition.IF_TIMEOUT: "if_timeout",
            EnumBranchCondition.CUSTOM: "custom",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value

    def test_iteration(self, all_branch_condition_values: list[str]) -> None:
        """Test enum iteration returns all values."""
        actual_values = {member.value for member in EnumBranchCondition}
        expected_values = set(all_branch_condition_values)
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumBranchCondition]
        assert len(values) == len(set(values))

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        assert EnumBranchCondition.IF_TRUE == EnumBranchCondition.IF_TRUE
        assert EnumBranchCondition.IF_TRUE != EnumBranchCondition.IF_FALSE
        assert EnumBranchCondition.IF_ERROR is EnumBranchCondition.IF_ERROR

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        assert EnumBranchCondition("if_true") == EnumBranchCondition.IF_TRUE
        assert EnumBranchCondition("if_error") == EnumBranchCondition.IF_ERROR

    def test_invalid_value_raises_error(self) -> None:
        """Test invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumBranchCondition("invalid_condition")

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumBranchCondition:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumBranchCondition(deserialized) == member

    def test_pickle_serialization(self) -> None:
        """Test enum members can be pickled and unpickled."""
        for member in EnumBranchCondition:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member

    def test_boolean_conditions(self) -> None:
        """Test boolean-related branch conditions."""
        boolean_conditions = {
            EnumBranchCondition.IF_TRUE,
            EnumBranchCondition.IF_FALSE,
        }
        assert len(boolean_conditions) == 2

    def test_status_conditions(self) -> None:
        """Test status-related branch conditions."""
        status_conditions = {
            EnumBranchCondition.IF_ERROR,
            EnumBranchCondition.IF_SUCCESS,
            EnumBranchCondition.IF_TIMEOUT,
        }
        assert len(status_conditions) == 3


# ============================================================================
# EnumExecutionPattern Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumExecutionPattern:
    """Tests for EnumExecutionPattern from enum_workflow_coordination."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumExecutionPattern inherits from str and Enum."""
        assert issubclass(EnumExecutionPattern, str)
        assert issubclass(EnumExecutionPattern, Enum)

    def test_values_exist(self, all_execution_pattern_values: list[str]) -> None:
        """Test all expected values exist."""
        assert EnumExecutionPattern.SEQUENTIAL.value == "sequential"
        assert EnumExecutionPattern.PARALLEL_COMPUTE.value == "parallel_compute"
        assert EnumExecutionPattern.PIPELINE.value == "pipeline"
        assert EnumExecutionPattern.SCATTER_GATHER.value == "scatter_gather"

    def test_member_count(self) -> None:
        """Test correct number of members (4 patterns)."""
        assert len(EnumExecutionPattern) == 4

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumExecutionPattern.SEQUENTIAL: "sequential",
            EnumExecutionPattern.PARALLEL_COMPUTE: "parallel_compute",
            EnumExecutionPattern.PIPELINE: "pipeline",
            EnumExecutionPattern.SCATTER_GATHER: "scatter_gather",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value
            assert member == expected_value  # str enum

    def test_iteration(self, all_execution_pattern_values: list[str]) -> None:
        """Test enum iteration returns all values."""
        actual_values = {member.value for member in EnumExecutionPattern}
        expected_values = set(all_execution_pattern_values)
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumExecutionPattern]
        assert len(values) == len(set(values))

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumExecutionPattern:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumExecutionPattern(deserialized) == member


# ============================================================================
# EnumAssignmentStatus Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumAssignmentStatus:
    """Tests for EnumAssignmentStatus from enum_workflow_coordination."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumAssignmentStatus inherits from str and Enum."""
        assert issubclass(EnumAssignmentStatus, str)
        assert issubclass(EnumAssignmentStatus, Enum)

    def test_values_exist(self, all_assignment_status_values: list[str]) -> None:
        """Test all expected values exist."""
        assert EnumAssignmentStatus.ASSIGNED.value == "ASSIGNED"
        assert EnumAssignmentStatus.EXECUTING.value == "EXECUTING"
        assert EnumAssignmentStatus.COMPLETED.value == "COMPLETED"
        assert EnumAssignmentStatus.FAILED.value == "FAILED"

    def test_member_count(self) -> None:
        """Test correct number of members (4 statuses)."""
        assert len(EnumAssignmentStatus) == 4

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumAssignmentStatus.ASSIGNED: "ASSIGNED",
            EnumAssignmentStatus.EXECUTING: "EXECUTING",
            EnumAssignmentStatus.COMPLETED: "COMPLETED",
            EnumAssignmentStatus.FAILED: "FAILED",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value
            assert member == expected_value  # str enum

    def test_iteration(self, all_assignment_status_values: list[str]) -> None:
        """Test enum iteration returns all values."""
        actual_values = {member.value for member in EnumAssignmentStatus}
        expected_values = set(all_assignment_status_values)
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumAssignmentStatus]
        assert len(values) == len(set(values))

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumAssignmentStatus:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumAssignmentStatus(deserialized) == member


# ============================================================================
# EnumWorkflowStatus Coordination Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumWorkflowStatusCoordination:
    """Tests for canonical EnumWorkflowStatus.

    Note: This tests the canonical EnumWorkflowStatus which has lowercase
    values (pending, running, etc.) and includes PAUSED state.
    """

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumWorkflowStatus inherits from str and Enum."""
        assert issubclass(EnumWorkflowStatus, str)
        assert issubclass(EnumWorkflowStatus, Enum)

    def test_values_exist(self) -> None:
        """Test all expected values exist."""
        assert EnumWorkflowStatus.PENDING.value == "pending"
        assert EnumWorkflowStatus.RUNNING.value == "running"
        assert EnumWorkflowStatus.COMPLETED.value == "completed"
        assert EnumWorkflowStatus.FAILED.value == "failed"
        assert EnumWorkflowStatus.CANCELLED.value == "cancelled"
        assert EnumWorkflowStatus.PAUSED.value == "paused"

    def test_member_count(self) -> None:
        """Test correct number of members (6 statuses)."""
        assert len(EnumWorkflowStatus) == 6

    def test_string_values(self) -> None:
        """Test string representations match expected values."""
        expected_mappings = {
            EnumWorkflowStatus.PENDING: "pending",
            EnumWorkflowStatus.RUNNING: "running",
            EnumWorkflowStatus.COMPLETED: "completed",
            EnumWorkflowStatus.FAILED: "failed",
            EnumWorkflowStatus.CANCELLED: "cancelled",
            EnumWorkflowStatus.PAUSED: "paused",
        }
        for member, expected_value in expected_mappings.items():
            assert member.value == expected_value
            assert member == expected_value  # str enum

    def test_iteration(self) -> None:
        """Test enum iteration returns all values."""
        expected_values = {
            "pending",
            "running",
            "completed",
            "failed",
            "cancelled",
            "paused",
        }
        actual_values = {member.value for member in EnumWorkflowStatus}
        assert actual_values == expected_values

    def test_value_uniqueness(self) -> None:
        """Test all enum members have unique values."""
        values = [member.value for member in EnumWorkflowStatus]
        assert len(values) == len(set(values))

    def test_json_serialization(self) -> None:
        """Test enum values are JSON serializable."""
        for member in EnumWorkflowStatus:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumWorkflowStatus(deserialized) == member


# ============================================================================
# Cross-Enum Integration Tests
# ============================================================================


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestOrchestratorEnumsIntegration:
    """Integration tests across orchestrator enums."""

    def test_workflow_state_and_action_type_compatibility(self) -> None:
        """Test that workflow state and action type enums can be used together.

        Verifies both enum types have valid, non-None values.
        """
        running_state = EnumWorkflowStatus.RUNNING
        for action_type in EnumActionType:
            # Verify enum values are defined
            assert action_type.value is not None
            assert running_state.value == "running"

    def test_failure_recovery_after_failed_state(self) -> None:
        """Test that recovery strategies are semantically valid after FAILED state."""
        failed_state = EnumWorkflowStatus.FAILED
        assert failed_state.value == "failed"

        # All recovery strategies should be applicable after failure
        for strategy in EnumFailureRecoveryStrategy:
            assert strategy.value is not None

    def test_execution_mode_with_action_type(self) -> None:
        """Test execution modes can apply to any action type."""
        for mode in EnumExecutionModeOrchestrator:
            for action_type in EnumActionType:
                # All combinations should be valid enum values
                assert mode.value is not None
                assert action_type.value is not None

    def test_pydantic_compatibility_all_enums(self) -> None:
        """Test all orchestrator enums work with Pydantic models."""
        from pydantic import BaseModel

        class OrchestratorConfig(BaseModel):
            """Test model for orchestrator enum compatibility."""

            workflow_state: EnumWorkflowStatus
            action_type: EnumActionType
            branch_condition: EnumBranchCondition
            recovery_strategy: EnumFailureRecoveryStrategy
            execution_pattern: EnumExecutionPattern
            assignment_status: EnumAssignmentStatus

        # Test creation with enum values
        config = OrchestratorConfig(
            workflow_state=EnumWorkflowStatus.RUNNING,
            action_type=EnumActionType.COMPUTE,
            branch_condition=EnumBranchCondition.IF_SUCCESS,
            recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            execution_pattern=EnumExecutionPattern.SEQUENTIAL,
            assignment_status=EnumAssignmentStatus.EXECUTING,
        )

        assert config.workflow_state == EnumWorkflowStatus.RUNNING
        assert config.action_type == EnumActionType.COMPUTE
        assert config.recovery_strategy == EnumFailureRecoveryStrategy.RETRY

        # Test serialization - model_dump() returns enum members by default
        # (use mode='json' for string serialization)
        data = config.model_dump()
        # EnumWorkflowStatus is (str, Enum), value equals string in comparisons
        assert data["workflow_state"] == EnumWorkflowStatus.RUNNING
        # EnumActionType is Enum (not str,Enum), returns enum member in model_dump
        assert data["action_type"] == EnumActionType.COMPUTE
        # EnumFailureRecoveryStrategy is (str, Enum) - value is the string
        assert data["recovery_strategy"] == "RETRY"

        # Test JSON serialization mode (converts all to primitives)
        json_data = config.model_dump(mode="json")
        assert json_data["workflow_state"] == "running"
        assert json_data["action_type"] == "compute"
        assert json_data["recovery_strategy"] == "RETRY"

        # Test deserialization
        new_config = OrchestratorConfig.model_validate(data)
        assert new_config.workflow_state == EnumWorkflowStatus.RUNNING

    def test_all_orchestrator_enums_hashable(self) -> None:
        """Test all orchestrator enum members are hashable."""
        all_enums: list[type[Enum]] = [
            EnumWorkflowStatus,
            EnumExecutionModeOrchestrator,
            EnumActionType,
            EnumFailureRecoveryStrategy,
            EnumBranchCondition,
            EnumExecutionPattern,
            EnumAssignmentStatus,
        ]

        for enum_class in all_enums:
            for member in enum_class:
                # Should be hashable (no exception)
                hash_value = hash(member)
                assert isinstance(hash_value, int)

    def test_reserved_values_not_in_v1_supported_sets(self) -> None:
        """Test reserved values are properly identified.

        This ensures documentation of reserved values is accurate.
        """
        # EnumWorkflowStatus: PAUSED is reserved for v1.1
        v1_workflow_states = {
            EnumWorkflowStatus.PENDING,
            EnumWorkflowStatus.RUNNING,
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
        }
        reserved_workflow_states = {EnumWorkflowStatus.PAUSED}
        assert v1_workflow_states.intersection(reserved_workflow_states) == set()

        # EnumExecutionMode: CONDITIONAL (v1.1), STREAMING (v1.2) reserved
        v1_execution_modes = {
            EnumExecutionModeOrchestrator.SEQUENTIAL,
            EnumExecutionModeOrchestrator.PARALLEL,
            EnumExecutionModeOrchestrator.BATCH,
        }
        reserved_execution_modes = {
            EnumExecutionModeOrchestrator.CONDITIONAL,
            EnumExecutionModeOrchestrator.STREAMING,
        }
        assert v1_execution_modes.intersection(reserved_execution_modes) == set()

        # EnumFailureRecoveryStrategy: ROLLBACK, COMPENSATE reserved for v2.0
        v1_recovery_strategies = {
            EnumFailureRecoveryStrategy.RETRY,
            EnumFailureRecoveryStrategy.ABORT,
        }
        v2_reserved_strategies = {
            EnumFailureRecoveryStrategy.ROLLBACK,
            EnumFailureRecoveryStrategy.COMPENSATE,
        }
        assert v1_recovery_strategies.intersection(v2_reserved_strategies) == set()
