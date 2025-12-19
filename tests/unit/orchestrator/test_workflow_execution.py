import pytest

# SPDX-FileCopyrightText: 2024 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""
Sequential execution tests for NodeOrchestrator workflow executor.

Tests cover:
- Single step execution
- Linear chain execution (A -> B -> C)
- Diamond dependency patterns (A -> (B, C) -> D)
- Execution status tracking (COMPLETED, FAILED)
- Topological ordering verification
- Action emission correctness

OMN-657: Comprehensive workflow execution testing.
"""

from uuid import UUID, uuid4

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
)
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.workflow_executor import execute_workflow, get_execution_order

# Default version for test instances
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def workflow_definition() -> ModelWorkflowDefinition:
    """Create a base workflow definition for testing."""
    return ModelWorkflowDefinition(
        version=DEFAULT_VERSION,
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test_sequential_workflow",
            workflow_version=DEFAULT_VERSION,
            description="Test workflow for sequential execution tests",
            execution_mode="sequential",
            timeout_ms=60000,
        ),
        execution_graph=ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        ),
        coordination_rules=ModelCoordinationRules(
            version=DEFAULT_VERSION,
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
        ),
    )


@pytest.fixture
def single_step() -> list[ModelWorkflowStep]:
    """Create a single workflow step."""
    return [
        ModelWorkflowStep(
            step_id=uuid4(),
            step_name="single_step",
            step_type="compute",
            enabled=True,
            timeout_ms=10000,
        ),
    ]


@pytest.fixture
def linear_chain_steps() -> tuple[list[ModelWorkflowStep], list[UUID]]:
    """
    Create a linear chain of steps: A -> B -> C.

    Returns:
        Tuple of (steps list, [step_a_id, step_b_id, step_c_id])
    """
    step_a_id = uuid4()
    step_b_id = uuid4()
    step_c_id = uuid4()

    steps = [
        ModelWorkflowStep(
            step_id=step_a_id,
            step_name="step_a",
            step_type="effect",
            enabled=True,
            timeout_ms=10000,
        ),
        ModelWorkflowStep(
            step_id=step_b_id,
            step_name="step_b",
            step_type="compute",
            depends_on=[step_a_id],
            enabled=True,
            timeout_ms=10000,
        ),
        ModelWorkflowStep(
            step_id=step_c_id,
            step_name="step_c",
            step_type="reducer",
            depends_on=[step_b_id],
            enabled=True,
            timeout_ms=10000,
        ),
    ]

    return steps, [step_a_id, step_b_id, step_c_id]


@pytest.fixture
def diamond_dependency_steps() -> tuple[list[ModelWorkflowStep], dict[str, UUID]]:
    """
    Create diamond dependency pattern: A -> (B, C) -> D.

    Topology:
        A
       / \\
      B   C
       \\ /
        D

    Returns:
        Tuple of (steps list, {step_name: step_id})
    """
    step_a_id = uuid4()
    step_b_id = uuid4()
    step_c_id = uuid4()
    step_d_id = uuid4()

    steps = [
        ModelWorkflowStep(
            step_id=step_a_id,
            step_name="step_a_root",
            step_type="effect",
            enabled=True,
            timeout_ms=10000,
        ),
        ModelWorkflowStep(
            step_id=step_b_id,
            step_name="step_b_branch",
            step_type="compute",
            depends_on=[step_a_id],
            enabled=True,
            timeout_ms=10000,
        ),
        ModelWorkflowStep(
            step_id=step_c_id,
            step_name="step_c_branch",
            step_type="compute",
            depends_on=[step_a_id],
            enabled=True,
            timeout_ms=10000,
        ),
        ModelWorkflowStep(
            step_id=step_d_id,
            step_name="step_d_merge",
            step_type="reducer",
            depends_on=[step_b_id, step_c_id],
            enabled=True,
            timeout_ms=10000,
        ),
    ]

    step_ids = {
        "A": step_a_id,
        "B": step_b_id,
        "C": step_c_id,
        "D": step_d_id,
    }

    return steps, step_ids


# =============================================================================
# Single Step Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestSingleStepExecution:
    """Tests for single step workflow execution."""

    @pytest.mark.asyncio
    async def test_single_step_executes_correctly(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test that a workflow with a single step executes correctly."""
        workflow_id = uuid4()

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 1
        assert len(result.failed_steps) == 0

    @pytest.mark.asyncio
    async def test_single_step_produces_correct_action(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test that single step produces correct action."""
        workflow_id = uuid4()

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Should emit exactly one action
        assert len(result.actions_emitted) == 1

        action = result.actions_emitted[0]
        step = single_step[0]

        # Verify action properties
        assert action.action_type == EnumActionType.COMPUTE
        assert action.target_node_type == "NodeCompute"
        assert action.payload["step_name"] == step.step_name
        assert action.payload["step_id"] == str(step.step_id)
        assert action.payload["workflow_id"] == str(workflow_id)

    @pytest.mark.asyncio
    async def test_single_step_execution_status_is_completed(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test that execution_status is COMPLETED for successful single step."""
        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.failed_steps) == 0
        assert result.execution_time_ms >= 1  # Minimum 1ms

    @pytest.mark.asyncio
    async def test_single_step_metadata_recorded(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test that metadata is correctly recorded for single step execution."""
        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert "execution_mode" in result.metadata
        assert result.metadata["execution_mode"] == "sequential"
        assert "workflow_name" in result.metadata
        assert "workflow_hash" in result.metadata


# =============================================================================
# Linear Chain Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestLinearChainExecution:
    """Tests for linear chain workflow execution (A -> B -> C)."""

    @pytest.mark.asyncio
    async def test_linear_chain_executes_in_order(
        self,
        workflow_definition: ModelWorkflowDefinition,
        linear_chain_steps: tuple[list[ModelWorkflowStep], list[UUID]],
    ) -> None:
        """Test that A -> B -> C executes in correct order."""
        steps, step_ids = linear_chain_steps
        step_a_id, step_b_id, step_c_id = step_ids

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 3

        # Verify order by checking completed_steps list
        # Steps are added to completed_steps in execution order
        completed_step_ids = [UUID(s) for s in result.completed_steps]
        assert completed_step_ids.index(step_a_id) < completed_step_ids.index(step_b_id)
        assert completed_step_ids.index(step_b_id) < completed_step_ids.index(step_c_id)

    @pytest.mark.asyncio
    async def test_linear_chain_dependencies_respected(
        self,
        workflow_definition: ModelWorkflowDefinition,
        linear_chain_steps: tuple[list[ModelWorkflowStep], list[UUID]],
    ) -> None:
        """Test that dependencies are respected in linear chain."""
        steps, step_ids = linear_chain_steps

        # Get topological order
        order = get_execution_order(steps)

        # Verify topological order
        step_a_id, step_b_id, step_c_id = step_ids
        assert order.index(step_a_id) < order.index(step_b_id)
        assert order.index(step_b_id) < order.index(step_c_id)

    @pytest.mark.asyncio
    async def test_linear_chain_all_steps_complete(
        self,
        workflow_definition: ModelWorkflowDefinition,
        linear_chain_steps: tuple[list[ModelWorkflowStep], list[UUID]],
    ) -> None:
        """Test that all steps in linear chain complete."""
        steps, step_ids = linear_chain_steps

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0

        # Verify all step IDs are in completed_steps
        for step_id in step_ids:
            assert str(step_id) in result.completed_steps

    @pytest.mark.asyncio
    async def test_linear_chain_actions_have_correct_dependency_mapping(
        self,
        workflow_definition: ModelWorkflowDefinition,
        linear_chain_steps: tuple[list[ModelWorkflowStep], list[UUID]],
    ) -> None:
        """Test that actions have correct dependency mapping."""
        steps, step_ids = linear_chain_steps
        step_a_id, step_b_id, step_c_id = step_ids

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Create lookup by step_id from payload
        actions_by_step_id: dict[UUID, ModelAction] = {}
        for action in result.actions_emitted:
            step_id_str = action.payload["step_id"]
            actions_by_step_id[UUID(str(step_id_str))] = action

        # Verify action A has no dependencies
        action_a = actions_by_step_id[step_a_id]
        assert len(action_a.dependencies) == 0

        # Verify action B depends on A
        action_b = actions_by_step_id[step_b_id]
        assert step_a_id in action_b.dependencies

        # Verify action C depends on B
        action_c = actions_by_step_id[step_c_id]
        assert step_b_id in action_c.dependencies


# =============================================================================
# Diamond Dependency Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestDiamondDependencyExecution:
    """Tests for diamond dependency pattern: A -> (B, C) -> D."""

    @pytest.mark.asyncio
    async def test_diamond_pattern_executes_correctly(
        self,
        workflow_definition: ModelWorkflowDefinition,
        diamond_dependency_steps: tuple[list[ModelWorkflowStep], dict[str, UUID]],
    ) -> None:
        """Test that diamond pattern A -> (B, C) -> D executes correctly."""
        steps, _step_ids = diamond_dependency_steps

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 4
        assert len(result.failed_steps) == 0

    @pytest.mark.asyncio
    async def test_diamond_b_and_c_can_execute_after_a(
        self,
        workflow_definition: ModelWorkflowDefinition,
        diamond_dependency_steps: tuple[list[ModelWorkflowStep], dict[str, UUID]],
    ) -> None:
        """Test that B and C can both execute after A."""
        steps, step_ids = diamond_dependency_steps

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        completed_uuids = [UUID(s) for s in result.completed_steps]

        # A must be before B and C
        a_idx = completed_uuids.index(step_ids["A"])
        b_idx = completed_uuids.index(step_ids["B"])
        c_idx = completed_uuids.index(step_ids["C"])

        assert a_idx < b_idx
        assert a_idx < c_idx

    @pytest.mark.asyncio
    async def test_diamond_d_waits_for_both_b_and_c(
        self,
        workflow_definition: ModelWorkflowDefinition,
        diamond_dependency_steps: tuple[list[ModelWorkflowStep], dict[str, UUID]],
    ) -> None:
        """Test that D waits for both B and C to complete."""
        steps, step_ids = diamond_dependency_steps

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        completed_uuids = [UUID(s) for s in result.completed_steps]

        # D must be after both B and C
        b_idx = completed_uuids.index(step_ids["B"])
        c_idx = completed_uuids.index(step_ids["C"])
        d_idx = completed_uuids.index(step_ids["D"])

        assert d_idx > b_idx
        assert d_idx > c_idx

    @pytest.mark.asyncio
    async def test_diamond_topological_ordering_correct(
        self,
        diamond_dependency_steps: tuple[list[ModelWorkflowStep], dict[str, UUID]],
    ) -> None:
        """Test that topological ordering is correct for diamond pattern."""
        steps, step_ids = diamond_dependency_steps

        order = get_execution_order(steps)

        # A should be first
        assert order[0] == step_ids["A"]

        # D should be last
        assert order[-1] == step_ids["D"]

        # B and C should be in the middle (order between them is implementation-defined)
        a_idx = order.index(step_ids["A"])
        b_idx = order.index(step_ids["B"])
        c_idx = order.index(step_ids["C"])
        d_idx = order.index(step_ids["D"])

        assert a_idx < b_idx < d_idx
        assert a_idx < c_idx < d_idx

    @pytest.mark.asyncio
    async def test_diamond_actions_have_correct_dependencies(
        self,
        workflow_definition: ModelWorkflowDefinition,
        diamond_dependency_steps: tuple[list[ModelWorkflowStep], dict[str, UUID]],
    ) -> None:
        """Test that actions have correct dependencies in diamond pattern."""
        steps, step_ids = diamond_dependency_steps

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Create lookup by step_id
        actions_by_step_id: dict[UUID, ModelAction] = {}
        for action in result.actions_emitted:
            step_id_str = action.payload["step_id"]
            actions_by_step_id[UUID(str(step_id_str))] = action

        # A has no dependencies
        action_a = actions_by_step_id[step_ids["A"]]
        assert len(action_a.dependencies) == 0

        # B depends on A
        action_b = actions_by_step_id[step_ids["B"]]
        assert step_ids["A"] in action_b.dependencies

        # C depends on A
        action_c = actions_by_step_id[step_ids["C"]]
        assert step_ids["A"] in action_c.dependencies

        # D depends on both B and C
        action_d = actions_by_step_id[step_ids["D"]]
        assert step_ids["B"] in action_d.dependencies
        assert step_ids["C"] in action_d.dependencies


# =============================================================================
# Execution Status Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestExecutionStatus:
    """Tests for execution status tracking."""

    @pytest.mark.asyncio
    async def test_completed_status_on_success(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test COMPLETED status on successful execution."""
        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED

    @pytest.mark.asyncio
    async def test_failed_status_on_step_failure(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test FAILED status when a step fails."""
        from unittest.mock import patch

        step_id = uuid4()
        steps = [
            ModelWorkflowStep(
                step_id=step_id,
                step_name="failing_step",
                step_type="compute",
                enabled=True,
                error_action="continue",  # Don't stop, mark as failed
            ),
        ]

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step"
        ) as mock:
            mock.side_effect = RuntimeError("Simulated failure")

            result = await execute_workflow(
                workflow_definition=workflow_definition,
                workflow_steps=steps,
                workflow_id=uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        assert result.execution_status == EnumWorkflowState.FAILED

    @pytest.mark.asyncio
    async def test_failed_steps_tracking(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that failed steps are properly tracked."""
        from unittest.mock import patch

        failing_step_id = uuid4()
        steps = [
            ModelWorkflowStep(
                step_id=failing_step_id,
                step_name="will_fail",
                step_type="compute",
                enabled=True,
                error_action="continue",
            ),
        ]

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step"
        ) as mock:
            mock.side_effect = ValueError("Test error")

            result = await execute_workflow(
                workflow_definition=workflow_definition,
                workflow_steps=steps,
                workflow_id=uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        assert str(failing_step_id) in result.failed_steps
        assert str(failing_step_id) not in result.completed_steps

    @pytest.mark.asyncio
    async def test_skipped_steps_with_skip_on_failure(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test skip_on_failure behavior when dependency fails."""
        from unittest.mock import patch

        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="failing_step",
                step_type="compute",
                enabled=True,
                error_action="continue",  # Continue to next step
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="dependent_step",
                step_type="compute",
                depends_on=[step_a_id],
                enabled=True,
                skip_on_failure=True,
            ),
        ]

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step"
        ) as mock:
            mock.side_effect = RuntimeError("Step A fails")

            result = await execute_workflow(
                workflow_definition=workflow_definition,
                workflow_steps=steps,
                workflow_id=uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        # Step A failed
        assert str(step_a_id) in result.failed_steps

        # Step B should be in failed_steps because dependency not met
        # (even with skip_on_failure, it can't execute without its dependency)
        assert str(step_b_id) in result.failed_steps

    @pytest.mark.asyncio
    async def test_error_action_stop_halts_workflow(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that error_action='stop' halts workflow execution."""
        from unittest.mock import patch

        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="failing_step",
                step_type="compute",
                enabled=True,
                error_action="stop",  # Stop workflow on failure
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="should_not_run",
                step_type="compute",
                enabled=True,
            ),
        ]

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step"
        ) as mock:
            mock.side_effect = RuntimeError("Stop workflow")

            result = await execute_workflow(
                workflow_definition=workflow_definition,
                workflow_steps=steps,
                workflow_id=uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        # Step A failed
        assert str(step_a_id) in result.failed_steps

        # Step B should not be in any list (not executed due to stop)
        assert str(step_b_id) not in result.completed_steps

        # Workflow is FAILED
        assert result.execution_status == EnumWorkflowState.FAILED


# =============================================================================
# Topological Order Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestTopologicalOrder:
    """Tests for topological ordering of workflow steps."""

    def test_single_step_order(self, single_step: list[ModelWorkflowStep]) -> None:
        """Test topological order for single step."""
        order = get_execution_order(single_step)

        assert len(order) == 1
        assert order[0] == single_step[0].step_id

    def test_linear_chain_order(
        self, linear_chain_steps: tuple[list[ModelWorkflowStep], list[UUID]]
    ) -> None:
        """Test topological order for linear chain."""
        steps, step_ids = linear_chain_steps
        step_a_id, step_b_id, step_c_id = step_ids

        order = get_execution_order(steps)

        assert len(order) == 3
        assert order.index(step_a_id) < order.index(step_b_id)
        assert order.index(step_b_id) < order.index(step_c_id)

    def test_diamond_order(
        self, diamond_dependency_steps: tuple[list[ModelWorkflowStep], dict[str, UUID]]
    ) -> None:
        """Test topological order for diamond pattern."""
        steps, step_ids = diamond_dependency_steps

        order = get_execution_order(steps)

        assert len(order) == 4

        # A must be first
        assert order[0] == step_ids["A"]

        # D must be last
        assert order[-1] == step_ids["D"]

        # B and C must be between A and D
        a_idx = order.index(step_ids["A"])
        b_idx = order.index(step_ids["B"])
        c_idx = order.index(step_ids["C"])
        d_idx = order.index(step_ids["D"])

        assert a_idx < b_idx < d_idx
        assert a_idx < c_idx < d_idx

    def test_priority_ordering_when_no_dependencies(self) -> None:
        """Test that priority affects ordering when there are no dependencies."""
        step_low_priority = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="low_priority",
            step_type="compute",
            enabled=True,
            priority=10,  # Lower priority (higher number)
        )
        step_high_priority = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="high_priority",
            step_type="compute",
            enabled=True,
            priority=1,  # Higher priority (lower number)
        )

        # Put low priority first in list
        steps = [step_low_priority, step_high_priority]

        order = get_execution_order(steps)

        # High priority should come first (lower priority number = higher priority)
        assert order[0] == step_high_priority.step_id
        assert order[1] == step_low_priority.step_id

    def test_declaration_order_as_tiebreaker(self) -> None:
        """Test that declaration order is used as tiebreaker for equal priorities."""
        step_first = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="first",
            step_type="compute",
            enabled=True,
            priority=5,
        )
        step_second = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="second",
            step_type="compute",
            enabled=True,
            priority=5,  # Same priority
        )

        steps = [step_first, step_second]

        order = get_execution_order(steps)

        # First declared should come first
        assert order[0] == step_first.step_id
        assert order[1] == step_second.step_id


# =============================================================================
# Action Emission Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestActionEmission:
    """Tests for action emission in workflow execution."""

    @pytest.mark.asyncio
    async def test_actions_emitted_for_all_steps(
        self,
        workflow_definition: ModelWorkflowDefinition,
        linear_chain_steps: tuple[list[ModelWorkflowStep], list[UUID]],
    ) -> None:
        """Test that actions are emitted for all completed steps."""
        steps, _ = linear_chain_steps

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert len(result.actions_emitted) == len(steps)

    @pytest.mark.asyncio
    async def test_action_types_match_step_types(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that action types correctly map from step types."""
        steps = [
            ModelWorkflowStep(
                step_name="effect_step",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_name="compute_step",
                step_type="compute",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_name="reducer_step",
                step_type="reducer",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_name="orchestrator_step",
                step_type="orchestrator",
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Build lookup by step name
        actions_by_name: dict[str, ModelAction] = {}
        for action in result.actions_emitted:
            step_name = action.metadata.parameters["step_name"]
            actions_by_name[str(step_name)] = action

        assert actions_by_name["effect_step"].action_type == EnumActionType.EFFECT
        assert actions_by_name["compute_step"].action_type == EnumActionType.COMPUTE
        assert actions_by_name["reducer_step"].action_type == EnumActionType.REDUCE
        assert (
            actions_by_name["orchestrator_step"].action_type
            == EnumActionType.ORCHESTRATE
        )

    @pytest.mark.asyncio
    async def test_action_target_node_types_correct(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that target_node_type is correctly set on actions."""
        steps = [
            ModelWorkflowStep(
                step_name="effect_step",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_name="compute_step",
                step_type="compute",
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        actions_by_name: dict[str, ModelAction] = {}
        for action in result.actions_emitted:
            step_name = action.metadata.parameters["step_name"]
            actions_by_name[str(step_name)] = action

        assert actions_by_name["effect_step"].target_node_type == "NodeEffect"
        assert actions_by_name["compute_step"].target_node_type == "NodeCompute"

    @pytest.mark.asyncio
    async def test_action_payload_contains_workflow_context(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test that action payload contains workflow context."""
        workflow_id = uuid4()

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        action = result.actions_emitted[0]

        assert "workflow_id" in action.payload
        assert action.payload["workflow_id"] == str(workflow_id)
        assert "step_id" in action.payload
        assert "step_name" in action.payload

    @pytest.mark.asyncio
    async def test_action_metadata_contains_correlation_id(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test that action metadata contains correlation_id."""
        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        action = result.actions_emitted[0]

        assert "correlation_id" in action.metadata.parameters
        assert action.metadata.parameters["correlation_id"] == str(
            single_step[0].correlation_id
        )

    @pytest.mark.asyncio
    async def test_action_lease_and_epoch_set(
        self,
        workflow_definition: ModelWorkflowDefinition,
        single_step: list[ModelWorkflowStep],
    ) -> None:
        """Test that lease_id and epoch are set on actions."""
        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=single_step,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        action = result.actions_emitted[0]

        # lease_id should be a UUID
        assert action.lease_id is not None
        assert isinstance(action.lease_id, UUID)

        # epoch should be 0 for initial actions
        assert action.epoch == 0

    @pytest.mark.asyncio
    async def test_action_priority_clamped_to_10(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that action priority is clamped from step priority (1-1000) to (1-10)."""
        steps = [
            ModelWorkflowStep(
                step_name="high_priority_step",
                step_type="compute",
                enabled=True,
                priority=500,  # Step priority in range 1-1000
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        action = result.actions_emitted[0]

        # Priority should be clamped to max 10
        assert action.priority == 10  # min(500, 10) = 10


# =============================================================================
# Complex Workflow Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestComplexWorkflows:
    """Tests for complex workflow patterns."""

    @pytest.mark.asyncio
    async def test_multi_level_diamond_pattern(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """
        Test multi-level diamond: A -> (B,C) -> D -> (E,F) -> G.

        Topology:
            A
           / \\
          B   C
           \\ /
            D
           / \\
          E   F
           \\ /
            G
        """
        step_a = uuid4()
        step_b = uuid4()
        step_c = uuid4()
        step_d = uuid4()
        step_e = uuid4()
        step_f = uuid4()
        step_g = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a,
                step_name="A",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_b,
                step_name="B",
                step_type="compute",
                depends_on=[step_a],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_c,
                step_name="C",
                step_type="compute",
                depends_on=[step_a],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_d,
                step_name="D",
                step_type="reducer",
                depends_on=[step_b, step_c],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_e,
                step_name="E",
                step_type="compute",
                depends_on=[step_d],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_f,
                step_name="F",
                step_type="compute",
                depends_on=[step_d],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_g,
                step_name="G",
                step_type="reducer",
                depends_on=[step_e, step_f],
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 7

        # Verify ordering constraints
        completed_uuids = [UUID(s) for s in result.completed_steps]

        # A before B and C
        assert completed_uuids.index(step_a) < completed_uuids.index(step_b)
        assert completed_uuids.index(step_a) < completed_uuids.index(step_c)

        # B and C before D
        assert completed_uuids.index(step_b) < completed_uuids.index(step_d)
        assert completed_uuids.index(step_c) < completed_uuids.index(step_d)

        # D before E and F
        assert completed_uuids.index(step_d) < completed_uuids.index(step_e)
        assert completed_uuids.index(step_d) < completed_uuids.index(step_f)

        # E and F before G
        assert completed_uuids.index(step_e) < completed_uuids.index(step_g)
        assert completed_uuids.index(step_f) < completed_uuids.index(step_g)

    @pytest.mark.asyncio
    async def test_workflow_with_disabled_middle_step(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow where a middle step is disabled."""
        step_a = uuid4()
        step_b = uuid4()
        step_c = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a,
                step_name="A",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_b,
                step_name="B_disabled",
                step_type="compute",
                depends_on=[step_a],
                enabled=False,  # DISABLED
            ),
            ModelWorkflowStep(
                step_id=step_c,
                step_name="C",
                step_type="reducer",
                depends_on=[step_b],  # Depends on disabled step
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # A completes, B skipped, C fails due to unmet dependency
        assert str(step_a) in result.completed_steps
        assert str(step_b) not in result.completed_steps  # Skipped (disabled)
        assert str(step_c) in result.failed_steps  # Dependency not met

    @pytest.mark.asyncio
    async def test_parallel_branches_with_different_lengths(
        self,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """
        Test parallel branches of different lengths.

        Topology:
            A
           / \\
          B   C
          |   |
          D   E
          |
          F
           \\ /
            G

        Left branch: A -> B -> D -> F
        Right branch: A -> C -> E
        Merge: (F, E) -> G
        """
        step_a = uuid4()
        step_b = uuid4()
        step_c = uuid4()
        step_d = uuid4()
        step_e = uuid4()
        step_f = uuid4()
        step_g = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a,
                step_name="A",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_b,
                step_name="B",
                step_type="compute",
                depends_on=[step_a],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_c,
                step_name="C",
                step_type="compute",
                depends_on=[step_a],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_d,
                step_name="D",
                step_type="compute",
                depends_on=[step_b],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_e,
                step_name="E",
                step_type="compute",
                depends_on=[step_c],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_f,
                step_name="F",
                step_type="compute",
                depends_on=[step_d],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_g,
                step_name="G",
                step_type="reducer",
                depends_on=[step_f, step_e],
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            workflow_definition=workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 7

        # Verify topological constraints
        completed_uuids = [UUID(s) for s in result.completed_steps]

        # Left branch order
        assert completed_uuids.index(step_a) < completed_uuids.index(step_b)
        assert completed_uuids.index(step_b) < completed_uuids.index(step_d)
        assert completed_uuids.index(step_d) < completed_uuids.index(step_f)

        # Right branch order
        assert completed_uuids.index(step_a) < completed_uuids.index(step_c)
        assert completed_uuids.index(step_c) < completed_uuids.index(step_e)

        # G is last
        assert completed_uuids.index(step_f) < completed_uuids.index(step_g)
        assert completed_uuids.index(step_e) < completed_uuids.index(step_g)
