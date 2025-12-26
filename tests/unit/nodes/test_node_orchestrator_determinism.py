"""
Unit tests for NodeOrchestrator deterministic execution guarantees.

Tests that NodeOrchestrator maintains determinism:
- Same inputs produce same outputs
- Execution order is deterministic
- No global state dependencies
- State serialization produces identical results

Ticket: OMN-741
"""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
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
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

# Module-level marker
pytestmark = pytest.mark.unit


# Fixed UUIDs for deterministic testing
# Using pre-generated UUIDs ensures tests are reproducible across runs
FIXED_WORKFLOW_ID = UUID("11111111-1111-1111-1111-111111111111")
FIXED_STEP_1_ID = UUID("22222222-2222-2222-2222-222222222222")
FIXED_STEP_2_ID = UUID("33333333-3333-3333-3333-333333333333")
FIXED_STEP_3_ID = UUID("44444444-4444-4444-4444-444444444444")
FIXED_STEP_4_ID = UUID("55555555-5555-5555-5555-555555555555")
FIXED_STEP_5_ID = UUID("66666666-6666-6666-6666-666666666666")


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def simple_workflow_definition() -> ModelWorkflowDefinition:
    """Create simple workflow definition for testing."""
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow for declarative nodes",
            execution_mode="sequential",
        ),
        execution_graph=ModelExecutionGraph(
            nodes=[],
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        version=ModelSemVer(major=1, minor=0, patch=0),
    )


@pytest.fixture
def parallel_workflow_definition() -> ModelWorkflowDefinition:
    """Create workflow definition with parallel execution enabled."""
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="parallel_test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Parallel test workflow for determinism tests",
            execution_mode="parallel",
        ),
        execution_graph=ModelExecutionGraph(
            nodes=[],
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=True,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        version=ModelSemVer(major=1, minor=0, patch=0),
    )


@pytest.fixture
def sequential_steps_config() -> list[dict]:
    """Create sequential steps configuration with fixed IDs."""
    return [
        {
            "step_id": FIXED_STEP_1_ID,
            "step_name": "Step 1 - Fetch",
            "step_type": "effect",
        },
        {
            "step_id": FIXED_STEP_2_ID,
            "step_name": "Step 2 - Validate",
            "step_type": "compute",
            "depends_on": [FIXED_STEP_1_ID],
        },
        {
            "step_id": FIXED_STEP_3_ID,
            "step_name": "Step 3 - Process",
            "step_type": "compute",
            "depends_on": [FIXED_STEP_2_ID],
        },
    ]


@pytest.fixture
def complex_dependency_steps_config() -> list[dict]:
    """Create steps with complex dependency graph (diamond pattern)."""
    # Diamond pattern:
    #      Step 1
    #      /    \
    #   Step 2  Step 3
    #      \    /
    #      Step 4
    return [
        {
            "step_id": FIXED_STEP_1_ID,
            "step_name": "Step 1 - Root",
            "step_type": "effect",
        },
        {
            "step_id": FIXED_STEP_2_ID,
            "step_name": "Step 2 - Left Branch",
            "step_type": "compute",
            "depends_on": [FIXED_STEP_1_ID],
        },
        {
            "step_id": FIXED_STEP_3_ID,
            "step_name": "Step 3 - Right Branch",
            "step_type": "compute",
            "depends_on": [FIXED_STEP_1_ID],
        },
        {
            "step_id": FIXED_STEP_4_ID,
            "step_name": "Step 4 - Merge",
            "step_type": "reducer",
            "depends_on": [FIXED_STEP_2_ID, FIXED_STEP_3_ID],
        },
    ]


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeOrchestratorDeterministicOutput:
    """Test that same inputs always produce same outputs."""

    @pytest.mark.asyncio
    async def test_same_workflow_produces_same_completed_steps(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that same workflow steps produce same completed steps list."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Run workflow twice with identical inputs
        input_data_1 = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        input_data_2 = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_1 = await node.process(input_data_1)
        result_2 = await node.process(input_data_2)

        # Completed steps should be identical
        assert result_1.completed_steps == result_2.completed_steps
        assert result_1.execution_status == result_2.execution_status

    @pytest.mark.asyncio
    async def test_same_workflow_produces_same_actions_count(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that same workflow produces same number of actions."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data_1 = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        input_data_2 = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_1 = await node.process(input_data_1)
        result_2 = await node.process(input_data_2)

        # Actions emitted count should be deterministic
        assert len(result_1.actions_emitted) == len(result_2.actions_emitted)
        assert len(result_1.actions_emitted) == 3  # 3 steps

    @pytest.mark.asyncio
    async def test_same_workflow_produces_same_action_types(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that same workflow produces actions with same types."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_1 = await node.process(input_data)
        result_2 = await node.process(input_data)

        # Action types should be in same order
        action_types_1 = [action.action_type for action in result_1.actions_emitted]
        action_types_2 = [action.action_type for action in result_2.actions_emitted]

        assert action_types_1 == action_types_2

    @pytest.mark.asyncio
    async def test_same_workflow_produces_same_target_node_types(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that same workflow produces actions with same target node types."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_1 = await node.process(input_data)
        result_2 = await node.process(input_data)

        # Target node types should be in same order
        targets_1 = [action.target_node_type for action in result_1.actions_emitted]
        targets_2 = [action.target_node_type for action in result_2.actions_emitted]

        assert targets_1 == targets_2
        assert targets_1 == ["NodeEffect", "NodeCompute", "NodeCompute"]

    @pytest.mark.asyncio
    async def test_same_workflow_produces_consistent_metrics(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that same workflow produces consistent metrics counts."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_1 = await node.process(input_data)
        result_2 = await node.process(input_data)

        # Metrics should match (counts are deterministic)
        assert result_1.metrics["actions_count"] == result_2.metrics["actions_count"]
        assert (
            result_1.metrics["completed_count"] == result_2.metrics["completed_count"]
        )
        assert result_1.metrics["failed_count"] == result_2.metrics["failed_count"]


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeOrchestratorExecutionOrderDeterminism:
    """Test that execution order is deterministic."""

    def test_get_execution_order_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        sequential_steps_config: list[dict],
    ):
        """Test that get_execution_order_for_steps returns deterministic order."""
        node = NodeOrchestrator(test_container)

        # Create workflow steps from config
        steps = [
            ModelWorkflowStep(
                step_id=config["step_id"],
                step_name=config["step_name"],
                step_type=config["step_type"],
                depends_on=config.get("depends_on", []),
            )
            for config in sequential_steps_config
        ]

        # Run multiple times
        order_1 = node.get_execution_order_for_steps(steps)
        order_2 = node.get_execution_order_for_steps(steps)
        order_3 = node.get_execution_order_for_steps(steps)

        # All orders should be identical
        assert order_1 == order_2 == order_3
        # Sequential dependency chain should maintain order
        assert order_1 == [FIXED_STEP_1_ID, FIXED_STEP_2_ID, FIXED_STEP_3_ID]

    def test_get_execution_order_complex_graph_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        complex_dependency_steps_config: list[dict],
    ):
        """Test execution order determinism with complex dependency graph."""
        node = NodeOrchestrator(test_container)

        steps = [
            ModelWorkflowStep(
                step_id=config["step_id"],
                step_name=config["step_name"],
                step_type=config["step_type"],
                depends_on=config.get("depends_on", []),
            )
            for config in complex_dependency_steps_config
        ]

        # Run multiple times
        orders = [node.get_execution_order_for_steps(steps) for _ in range(5)]

        # All orders should be identical
        for order in orders[1:]:
            assert order == orders[0]

        # Step 1 must come first, Step 4 must come last
        for order in orders:
            assert order[0] == FIXED_STEP_1_ID
            assert order[-1] == FIXED_STEP_4_ID
            # Steps 2 and 3 must come before 4
            step_4_idx = order.index(FIXED_STEP_4_ID)
            assert order.index(FIXED_STEP_2_ID) < step_4_idx
            assert order.index(FIXED_STEP_3_ID) < step_4_idx

    def test_get_execution_order_respects_declaration_order(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test that execution order respects declaration order for equal priority."""
        node = NodeOrchestrator(test_container)

        # Steps with no dependencies (all can run first)
        # Should maintain declaration order
        steps = [
            ModelWorkflowStep(
                step_id=FIXED_STEP_1_ID,
                step_name="Step A",
                step_type="effect",
            ),
            ModelWorkflowStep(
                step_id=FIXED_STEP_2_ID,
                step_name="Step B",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=FIXED_STEP_3_ID,
                step_name="Step C",
                step_type="compute",
            ),
        ]

        orders = [node.get_execution_order_for_steps(steps) for _ in range(5)]

        # All orders should be identical and match declaration order
        for order in orders:
            assert order == [FIXED_STEP_1_ID, FIXED_STEP_2_ID, FIXED_STEP_3_ID]

    def test_get_execution_order_respects_priority(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test that execution order respects priority for steps with no dependencies."""
        node = NodeOrchestrator(test_container)

        # Steps with different priorities, no dependencies
        steps = [
            ModelWorkflowStep(
                step_id=FIXED_STEP_1_ID,
                step_name="Low Priority",
                step_type="effect",
                priority=5,
            ),
            ModelWorkflowStep(
                step_id=FIXED_STEP_2_ID,
                step_name="High Priority",
                step_type="compute",
                priority=1,
            ),
            ModelWorkflowStep(
                step_id=FIXED_STEP_3_ID,
                step_name="Medium Priority",
                step_type="compute",
                priority=3,
            ),
        ]

        orders = [node.get_execution_order_for_steps(steps) for _ in range(5)]

        # All orders should be identical
        for order in orders[1:]:
            assert order == orders[0]

        # Lower priority value = higher priority = comes first
        assert orders[0][0] == FIXED_STEP_2_ID  # priority 1
        assert orders[0][1] == FIXED_STEP_3_ID  # priority 3
        assert orders[0][2] == FIXED_STEP_1_ID  # priority 5

    @pytest.mark.asyncio
    async def test_sequential_execution_maintains_order(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that sequential execution maintains exact defined order."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=sequential_steps_config,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result = await node.process(input_data)

        # Completed steps should be in dependency order
        assert len(result.completed_steps) == 3
        # Steps complete in dependency order
        completed_order = result.completed_steps
        assert completed_order.index(str(FIXED_STEP_1_ID)) < completed_order.index(
            str(FIXED_STEP_2_ID)
        )
        assert completed_order.index(str(FIXED_STEP_2_ID)) < completed_order.index(
            str(FIXED_STEP_3_ID)
        )

    @pytest.mark.asyncio
    async def test_step_order_shuffled_produces_same_execution_order(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test that shuffled step input order produces same execution order."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Original order
        steps_original = [
            {
                "step_id": FIXED_STEP_1_ID,
                "step_name": "Step 1",
                "step_type": "effect",
            },
            {
                "step_id": FIXED_STEP_2_ID,
                "step_name": "Step 2",
                "step_type": "compute",
                "depends_on": [FIXED_STEP_1_ID],
            },
            {
                "step_id": FIXED_STEP_3_ID,
                "step_name": "Step 3",
                "step_type": "compute",
                "depends_on": [FIXED_STEP_2_ID],
            },
        ]

        # Shuffled order (Step 3 first, then Step 1, then Step 2)
        steps_shuffled = [
            {
                "step_id": FIXED_STEP_3_ID,
                "step_name": "Step 3",
                "step_type": "compute",
                "depends_on": [FIXED_STEP_2_ID],
            },
            {
                "step_id": FIXED_STEP_1_ID,
                "step_name": "Step 1",
                "step_type": "effect",
            },
            {
                "step_id": FIXED_STEP_2_ID,
                "step_name": "Step 2",
                "step_type": "compute",
                "depends_on": [FIXED_STEP_1_ID],
            },
        ]

        input_original = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=steps_original,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        input_shuffled = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=steps_shuffled,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_original = await node.process(input_original)
        result_shuffled = await node.process(input_shuffled)

        # Both should have same completed steps (order respects dependencies)
        assert set(result_original.completed_steps) == set(
            result_shuffled.completed_steps
        )
        # Dependency order is preserved in both
        for result in [result_original, result_shuffled]:
            completed = result.completed_steps
            assert completed.index(str(FIXED_STEP_1_ID)) < completed.index(
                str(FIXED_STEP_2_ID)
            )
            assert completed.index(str(FIXED_STEP_2_ID)) < completed.index(
                str(FIXED_STEP_3_ID)
            )


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeOrchestratorNoGlobalStateDependencies:
    """Test that results don't depend on global state."""

    @pytest.mark.asyncio
    async def test_multiple_instances_produce_same_results(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that multiple orchestrator instances produce same results."""
        # Create multiple independent instances
        node_1 = NodeOrchestrator(test_container)
        node_1.workflow_definition = simple_workflow_definition

        node_2 = NodeOrchestrator(test_container)
        node_2.workflow_definition = simple_workflow_definition

        node_3 = NodeOrchestrator(test_container)
        node_3.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Run on different instances
        result_1 = await node_1.process(input_data)
        result_2 = await node_2.process(input_data)
        result_3 = await node_3.process(input_data)

        # All should produce same results
        assert (
            result_1.completed_steps
            == result_2.completed_steps
            == result_3.completed_steps
        )
        assert (
            result_1.execution_status
            == result_2.execution_status
            == result_3.execution_status
        )
        assert (
            len(result_1.actions_emitted)
            == len(result_2.actions_emitted)
            == len(result_3.actions_emitted)
        )

    @pytest.mark.asyncio
    async def test_execution_not_affected_by_previous_execution(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test that previous execution doesn't affect subsequent execution."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # First execution with one set of steps
        steps_first = [
            {
                "step_id": FIXED_STEP_1_ID,
                "step_name": "First Run Step",
                "step_type": "effect",
            },
        ]

        input_first = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps_first,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        await node.process(input_first)

        # Second execution with different steps
        steps_second = [
            {
                "step_id": FIXED_STEP_2_ID,
                "step_name": "Second Run Step 1",
                "step_type": "effect",
            },
            {
                "step_id": FIXED_STEP_3_ID,
                "step_name": "Second Run Step 2",
                "step_type": "compute",
                "depends_on": [FIXED_STEP_2_ID],
            },
        ]

        input_second = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps_second,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_second = await node.process(input_second)

        # Second execution should work independently
        assert result_second.execution_status == "completed"
        assert len(result_second.completed_steps) == 2
        assert str(FIXED_STEP_2_ID) in result_second.completed_steps
        assert str(FIXED_STEP_3_ID) in result_second.completed_steps

    @pytest.mark.asyncio
    async def test_different_containers_produce_same_results(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that different containers produce same results."""
        # Create separate containers
        container_1 = ModelONEXContainer()
        container_2 = ModelONEXContainer()

        node_1 = NodeOrchestrator(container_1)
        node_1.workflow_definition = simple_workflow_definition

        node_2 = NodeOrchestrator(container_2)
        node_2.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_1 = await node_1.process(input_data)
        result_2 = await node_2.process(input_data)

        # Both should produce identical results
        assert result_1.completed_steps == result_2.completed_steps
        assert result_1.execution_status == result_2.execution_status

    @pytest.mark.asyncio
    async def test_repeated_execution_same_node_same_results(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that repeated execution on same node produces same results."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Run 5 times on same node
        results = [await node.process(input_data) for _ in range(5)]

        # All results should match
        first_result = results[0]
        for result in results[1:]:
            assert result.completed_steps == first_result.completed_steps
            assert result.execution_status == first_result.execution_status
            assert len(result.actions_emitted) == len(first_result.actions_emitted)


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeOrchestratorStateSerializationDeterminism:
    """Test that state serialization produces identical behavior."""

    @pytest.mark.asyncio
    async def test_workflow_definition_serialization_roundtrip(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that serialized/deserialized workflow produces same results."""
        # Serialize and deserialize workflow definition
        serialized = simple_workflow_definition.model_dump()
        restored_definition = ModelWorkflowDefinition.model_validate(serialized)

        # Run with original
        node_original = NodeOrchestrator(test_container)
        node_original.workflow_definition = simple_workflow_definition

        # Run with restored
        node_restored = NodeOrchestrator(test_container)
        node_restored.workflow_definition = restored_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result_original = await node_original.process(input_data)
        result_restored = await node_restored.process(input_data)

        # Results should be identical
        assert result_original.completed_steps == result_restored.completed_steps
        assert result_original.execution_status == result_restored.execution_status

    @pytest.mark.asyncio
    async def test_input_serialization_roundtrip(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that serialized/deserialized input produces same results."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create input and serialize
        original_input = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Serialize and restore
        serialized = original_input.model_dump()
        restored_input = ModelOrchestratorInput.model_validate(serialized)

        result_original = await node.process(original_input)
        result_restored = await node.process(restored_input)

        # Results should be identical
        assert result_original.completed_steps == result_restored.completed_steps
        assert result_original.execution_status == result_restored.execution_status

    @pytest.mark.asyncio
    async def test_workflow_step_serialization_roundtrip(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test that serialized/deserialized workflow steps produce same execution order."""
        node = NodeOrchestrator(test_container)

        # Create steps
        original_steps = [
            ModelWorkflowStep(
                step_id=FIXED_STEP_1_ID,
                step_name="Step 1",
                step_type="effect",
            ),
            ModelWorkflowStep(
                step_id=FIXED_STEP_2_ID,
                step_name="Step 2",
                step_type="compute",
                depends_on=[FIXED_STEP_1_ID],
            ),
        ]

        # Serialize and restore
        restored_steps = [
            ModelWorkflowStep.model_validate(step.model_dump())
            for step in original_steps
        ]

        order_original = node.get_execution_order_for_steps(original_steps)
        order_restored = node.get_execution_order_for_steps(restored_steps)

        # Orders should be identical
        assert order_original == order_restored

    @pytest.mark.asyncio
    async def test_output_metrics_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
        sequential_steps_config: list[dict],
    ):
        """Test that output metrics are deterministic after serialization roundtrip."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(sequential_steps_config),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result = await node.process(input_data)

        # Serialize output to dict
        serialized_output = result.model_dump()

        # Metrics should be preserved exactly in serialized form
        assert serialized_output["metrics"] == result.metrics
        assert serialized_output["completed_steps"] == result.completed_steps
        assert serialized_output["failed_steps"] == result.failed_steps

    def test_workflow_definition_hash_is_deterministic(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test that workflow definition hash is deterministic."""
        # Compute hash multiple times
        hash_1 = simple_workflow_definition.compute_workflow_hash()
        hash_2 = simple_workflow_definition.compute_workflow_hash()
        hash_3 = simple_workflow_definition.compute_workflow_hash()

        # All hashes should be identical
        assert hash_1 == hash_2 == hash_3

    def test_equivalent_workflow_definitions_have_same_hash(
        self,
    ):
        """Test that equivalent workflow definitions produce same hash."""
        # Create two equivalent workflow definitions
        def_1 = ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="identical_workflow",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Same workflow",
                execution_mode="sequential",
            ),
            execution_graph=ModelExecutionGraph(
                nodes=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            coordination_rules=ModelCoordinationRules(
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        def_2 = ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="identical_workflow",
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Same workflow",
                execution_mode="sequential",
            ),
            execution_graph=ModelExecutionGraph(
                nodes=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            coordination_rules=ModelCoordinationRules(
                parallel_execution_allowed=False,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        # Hashes should be identical for equivalent definitions
        assert def_1.compute_workflow_hash() == def_2.compute_workflow_hash()


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeOrchestratorParallelExecutionDeterminism:
    """Test determinism in parallel execution mode."""

    @pytest.mark.asyncio
    async def test_parallel_execution_produces_deterministic_completion_set(
        self,
        test_container: ModelONEXContainer,
        parallel_workflow_definition: ModelWorkflowDefinition,
        complex_dependency_steps_config: list[dict],
    ):
        """Test that parallel execution produces deterministic set of completed steps."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = parallel_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(complex_dependency_steps_config),
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Run multiple times
        results = [await node.process(input_data) for _ in range(5)]

        # All should complete same steps (order may vary in parallel)
        first_completed_set = set(results[0].completed_steps)
        for result in results[1:]:
            assert set(result.completed_steps) == first_completed_set

    @pytest.mark.asyncio
    async def test_parallel_execution_produces_deterministic_action_count(
        self,
        test_container: ModelONEXContainer,
        parallel_workflow_definition: ModelWorkflowDefinition,
        complex_dependency_steps_config: list[dict],
    ):
        """Test that parallel execution produces deterministic action count."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = parallel_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(complex_dependency_steps_config),
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Run multiple times
        results = [await node.process(input_data) for _ in range(5)]

        # All should emit same number of actions
        expected_count = len(results[0].actions_emitted)
        for result in results[1:]:
            assert len(result.actions_emitted) == expected_count

    @pytest.mark.asyncio
    async def test_parallel_respects_dependency_constraints(
        self,
        test_container: ModelONEXContainer,
        parallel_workflow_definition: ModelWorkflowDefinition,
        complex_dependency_steps_config: list[dict],
    ):
        """Test that parallel execution respects dependency constraints."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = parallel_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=deepcopy(complex_dependency_steps_config),
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        result = await node.process(input_data)

        # Verify dependency order constraints
        completed = result.completed_steps

        # All steps must be present in completed list
        assert str(FIXED_STEP_1_ID) in completed, "Root step 1 must be completed"
        assert str(FIXED_STEP_2_ID) in completed, "Step 2 must be completed"
        assert str(FIXED_STEP_3_ID) in completed, "Step 3 must be completed"
        assert str(FIXED_STEP_4_ID) in completed, "Step 4 must be completed"

        # Verify dependency ordering: Step 1 must appear before Steps 2 and 3
        # (Step 1 is the root that Steps 2 and 3 depend on)
        step_1_idx = completed.index(str(FIXED_STEP_1_ID))
        step_2_idx = completed.index(str(FIXED_STEP_2_ID))
        step_3_idx = completed.index(str(FIXED_STEP_3_ID))
        step_4_idx = completed.index(str(FIXED_STEP_4_ID))

        assert step_1_idx < step_2_idx, (
            "Step 1 must complete before Step 2 (dependency)"
        )
        assert step_1_idx < step_3_idx, (
            "Step 1 must complete before Step 3 (dependency)"
        )

        # Verify Step 4 (merge) comes after both Step 2 and Step 3
        assert step_2_idx < step_4_idx, (
            "Step 2 must complete before Step 4 (dependency)"
        )
        assert step_3_idx < step_4_idx, (
            "Step 3 must complete before Step 4 (dependency)"
        )


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeOrchestratorEdgeCases:
    """Test edge cases for determinism."""

    @pytest.mark.asyncio
    async def test_empty_steps_produces_deterministic_error(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test that empty steps list produces deterministic validation error."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=[],
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Should consistently raise validation error
        with pytest.raises(ModelOnexError) as exc_1:
            await node.process(input_data)

        with pytest.raises(ModelOnexError) as exc_2:
            await node.process(input_data)

        # Both errors should have same message pattern
        assert (
            "no steps" in str(exc_1.value).lower()
            or "validation" in str(exc_1.value).lower()
        )
        assert str(exc_1.value) == str(exc_2.value)

    @pytest.mark.asyncio
    async def test_single_step_workflow_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test that single step workflow produces deterministic results."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        single_step = [
            {
                "step_id": FIXED_STEP_1_ID,
                "step_name": "Only Step",
                "step_type": "effect",
            },
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=single_step,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        results = [await node.process(input_data) for _ in range(3)]

        # All should produce identical results
        for result in results:
            assert result.completed_steps == [str(FIXED_STEP_1_ID)]
            assert len(result.actions_emitted) == 1

    @pytest.mark.asyncio
    async def test_disabled_steps_handled_deterministically(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test that disabled steps are handled deterministically."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        steps_with_disabled = [
            {
                "step_id": FIXED_STEP_1_ID,
                "step_name": "Enabled Step 1",
                "step_type": "effect",
            },
            {
                "step_id": FIXED_STEP_2_ID,
                "step_name": "Disabled Step",
                "step_type": "compute",
                "enabled": False,
            },
            {
                "step_id": FIXED_STEP_3_ID,
                "step_name": "Enabled Step 2",
                "step_type": "compute",
                "depends_on": [FIXED_STEP_1_ID],  # Doesn't depend on disabled step
            },
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=FIXED_WORKFLOW_ID,
            steps=steps_with_disabled,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        results = [await node.process(input_data) for _ in range(3)]

        # Disabled step should not appear in completed steps
        for result in results:
            assert str(FIXED_STEP_2_ID) not in result.completed_steps
            # Other steps should complete
            assert str(FIXED_STEP_1_ID) in result.completed_steps
            assert str(FIXED_STEP_3_ID) in result.completed_steps
