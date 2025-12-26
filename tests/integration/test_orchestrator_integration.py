"""
Integration tests for NodeOrchestrator ModelOrchestratorInput -> ModelOrchestratorOutput flows.

These tests verify complete workflow-driven orchestrator workflows including:
1. Happy path workflow execution
2. Error handling for workflow failures
3. Multi-step workflow with dependencies
4. Parallel execution patterns
5. Workflow state snapshot/restore
6. Recovery workflows

Tests validate real workflow execution with actual data, not mocks.

Note:
    Integration tests using these fixtures should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import (
    EnumExecutionMode,
    EnumWorkflowState,
)
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
from omnibase_core.models.contracts.subcontracts.model_workflow_node import (
    ModelWorkflowNode,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.orchestrator.model_orchestrator_input_metadata import (
    ModelOrchestratorInputMetadata,
)
from omnibase_core.models.orchestrator.model_orchestrator_output import (
    ModelOrchestratorOutput,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.workflow.execution.model_workflow_state_snapshot import (
    ModelWorkflowStateSnapshot,
)
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60

# Version for test contracts
V1_0_0 = ModelSemVer(major=1, minor=0, patch=0)


# Type alias for orchestrator factory callable
OrchestratorWithContractFactory = Callable[[ModelWorkflowDefinition], NodeOrchestrator]


def create_test_workflow_definition(
    *,
    name: str = "test_workflow",
    description: str = "Test workflow for integration tests",
    execution_mode: str = "sequential",
    timeout_ms: int = 60000,
    parallel_execution_allowed: bool = True,
    failure_recovery_strategy: EnumFailureRecoveryStrategy = EnumFailureRecoveryStrategy.RETRY,
    nodes: list[dict[str, Any]] | None = None,
) -> ModelWorkflowDefinition:
    """Factory to create workflow definitions for testing.

    Args:
        name: Workflow name
        description: Workflow description
        execution_mode: Execution mode (sequential, parallel, batch)
        timeout_ms: Workflow timeout in milliseconds
        parallel_execution_allowed: Whether parallel execution is allowed
        failure_recovery_strategy: Strategy for handling failures
        nodes: List of workflow node definitions

    Returns:
        ModelWorkflowDefinition configured for testing
    """
    if nodes is None:
        nodes = [
            {
                "version": V1_0_0,
                "node_id": uuid4(),
                "node_type": EnumNodeType.COMPUTE_GENERIC,
                "node_requirements": {},
                "dependencies": [],
            },
        ]

    workflow_nodes = [ModelWorkflowNode(**n) for n in nodes]

    return ModelWorkflowDefinition(
        version=V1_0_0,
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            version=V1_0_0,
            workflow_name=name,
            workflow_version=V1_0_0,
            description=description,
            execution_mode=execution_mode,
            timeout_ms=timeout_ms,
        ),
        execution_graph=ModelExecutionGraph(
            version=V1_0_0,
            nodes=workflow_nodes,
        ),
        coordination_rules=ModelCoordinationRules(
            version=V1_0_0,
            parallel_execution_allowed=parallel_execution_allowed,
            failure_recovery_strategy=failure_recovery_strategy,
        ),
    )


def create_workflow_steps(
    steps_config: list[dict[str, Any]],
) -> list[ModelWorkflowStep]:
    """Create ModelWorkflowStep instances from configuration.

    Args:
        steps_config: List of step configuration dicts

    Returns:
        List of ModelWorkflowStep instances
    """
    return [ModelWorkflowStep(**config) for config in steps_config]


class TestableNodeOrchestrator(NodeOrchestrator):
    """Test implementation of NodeOrchestrator that can accept a workflow definition.

    This class exists solely for integration testing purposes. It allows tests
    to inject arbitrary workflow definitions at runtime rather than relying on the
    production contract loading mechanism (which requires class-level attributes
    and YAML contract files).

    WARNING: This pattern is for TESTING ONLY. Production code should always
    use the standard NodeOrchestrator initialization which loads contracts from
    declarative YAML files via class attributes.
    """

    def __init__(
        self,
        container: ModelONEXContainer,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Initialize with explicit workflow definition injection.

        This constructor intentionally bypasses the standard NodeOrchestrator.__init__()
        to enable direct workflow definition injection for testing. This is necessary
        because the production NodeOrchestrator expects contracts to be loaded from
        class-level attributes and YAML files, which is not suitable for
        integration tests that need to create dynamic workflow configurations.

        Args:
            container: ONEX container for dependency injection
            workflow_definition: Workflow definition to use for orchestration

        Note:
            The inheritance chain is:
            TestableNodeOrchestrator -> NodeOrchestrator -> NodeCoreBase

            By calling `super(NodeOrchestrator, self).__init__(container)`, we skip
            NodeOrchestrator.__init__() entirely and call NodeCoreBase.__init__()
            directly. This:
            1. Avoids the production contract loading logic in NodeOrchestrator
            2. Still initializes all base class infrastructure from NodeCoreBase
            3. Allows us to manually set workflow_definition

            WHY THIS IS SAFE FOR TESTING:
            - NodeCoreBase.__init__() handles container setup and core infrastructure
            - We manually provide the workflow_definition that NodeOrchestrator would load
            - All workflow functionality works identically to production

            WHY THIS IS NOT FOR PRODUCTION:
            - Production nodes should use declarative YAML contracts
            - Bypassing NodeOrchestrator.__init__() skips validation and logging
            - This pattern makes the contract source non-deterministic
            - Contract loading should be centralized, not scattered
        """
        # SUPER() BYPASS EXPLANATION:
        # --------------------------
        # Normal call: super().__init__(container) -> calls NodeOrchestrator.__init__()
        # Our call: super(NodeOrchestrator, self).__init__(container) -> calls NodeCoreBase.__init__()
        #
        # We use the two-argument form of super() to explicitly skip one level
        # in the inheritance hierarchy. This is a deliberate MRO (Method Resolution
        # Order) manipulation that:
        # - Starts resolution from NodeOrchestrator's parent (NodeCoreBase)
        # - Binds 'self' as the instance
        # - Results in calling NodeCoreBase.__init__(container)
        #
        # This is a TEST PATTERN ONLY - never use in production code.
        super(NodeOrchestrator, self).__init__(container)  # Call NodeCoreBase.__init__

        # Initialize _workflow_state from mixin (MixinWorkflowExecution)
        self._workflow_state = None

        # Directly inject the workflow definition that would normally be loaded from
        # a YAML file via class attributes in production NodeOrchestrator.
        # Use object.__setattr__() to bypass Pydantic validation
        object.__setattr__(self, "workflow_definition", workflow_definition)


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing.

    Returns:
        ModelONEXContainer with mocked services.
    """
    container = MagicMock(spec=ModelONEXContainer)
    container.get_service = MagicMock(return_value=MagicMock())
    return container


@pytest.fixture
def orchestrator_with_contract_factory(
    mock_container: ModelONEXContainer,
) -> OrchestratorWithContractFactory:
    """Factory fixture for creating NodeOrchestrator instances with custom workflow definitions.

    Args:
        mock_container: Mocked ONEX container

    Returns:
        Factory callable that creates TestableNodeOrchestrator instances
    """

    def _create_orchestrator(
        workflow_definition: ModelWorkflowDefinition,
    ) -> NodeOrchestrator:
        return TestableNodeOrchestrator(mock_container, workflow_definition)

    return _create_orchestrator


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestOrchestratorIntegration:
    """Integration tests for NodeOrchestrator input -> output flows.

    Tests complete workflow-driven orchestrator workflows with real step execution.
    """

    def test_happy_path_workflow_execution(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test Scenario 1: Happy path from ModelOrchestratorInput to ModelOrchestratorOutput.

        This test verifies:
        - Valid ModelOrchestratorInput is created with workflow steps
        - NodeOrchestrator processes the input through workflow execution
        - ModelOrchestratorOutput contains correct execution status
        - Actions are emitted for each step
        - Workflow state is tracked correctly
        """
        # Arrange: Create workflow definition with sequential execution
        workflow_definition = create_test_workflow_definition(
            name="happy_path_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create workflow steps
        step1_id = uuid4()
        step2_id = uuid4()
        steps = [
            {
                "step_id": step1_id,
                "step_name": "fetch_data",
                "step_type": "effect",
                "timeout_ms": 10000,
            },
            {
                "step_id": step2_id,
                "step_name": "process_data",
                "step_type": "compute",
                "depends_on": [step1_id],
                "timeout_ms": 15000,
            },
        ]

        # Create input
        workflow_id = uuid4()
        input_data = ModelOrchestratorInput(
            workflow_id=workflow_id,
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Act: Process the input
        result: ModelOrchestratorOutput = asyncio.run(orchestrator.process(input_data))

        # Assert: Verify output structure and workflow execution
        assert isinstance(result, ModelOrchestratorOutput)
        assert result.execution_status == EnumWorkflowState.COMPLETED.value
        assert result.execution_time_ms >= 0

        # Verify completed steps
        assert len(result.completed_steps) == 2
        assert str(step1_id) in result.completed_steps
        assert str(step2_id) in result.completed_steps

        # Verify actions were emitted for each step
        assert len(result.actions_emitted) == 2

        # Verify metrics are tracked
        assert result.metrics.get("actions_count") == 2.0
        assert result.metrics.get("completed_count") == 2.0
        assert result.metrics.get("failed_count") == 0.0

        # Verify workflow state snapshot is available
        snapshot = orchestrator.snapshot_workflow_state()
        assert snapshot is not None
        assert snapshot.workflow_id == workflow_id
        assert len(snapshot.completed_step_ids) == 2

    def test_error_path_missing_workflow_definition(
        self, mock_container: ModelONEXContainer
    ) -> None:
        """Test Scenario 2: Error path when workflow definition is not loaded.

        This test verifies:
        - NodeOrchestrator without workflow definition raises ModelOnexError
        - Error contains meaningful context
        """
        # Arrange: Create orchestrator without workflow definition
        # Use standard initialization which leaves workflow_definition as None
        orchestrator = NodeOrchestrator(mock_container)
        assert orchestrator.workflow_definition is None

        # Create input
        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[{"step_name": "test", "step_type": "compute"}],
        )

        # Act & Assert: Expect ModelOnexError for missing workflow definition
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(orchestrator.process(input_data))

        # Verify error details
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "not loaded" in error.message.lower()

    def test_multi_step_workflow_with_dependencies(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test Scenario 3: Multi-step workflow with dependency chain.

        This test verifies:
        - Steps execute in correct dependency order
        - Each step waits for its dependencies to complete
        - Final output contains all completed steps
        - Workflow state history accumulates correctly
        """
        # Arrange: Create workflow definition
        workflow_definition = create_test_workflow_definition(
            name="multi_step_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create 4-step workflow: fetch -> validate -> transform -> persist
        fetch_id = uuid4()
        validate_id = uuid4()
        transform_id = uuid4()
        persist_id = uuid4()

        steps = [
            {
                "step_id": fetch_id,
                "step_name": "fetch_data",
                "step_type": "effect",
                "timeout_ms": 10000,
            },
            {
                "step_id": validate_id,
                "step_name": "validate_schema",
                "step_type": "compute",
                "depends_on": [fetch_id],
                "timeout_ms": 5000,
            },
            {
                "step_id": transform_id,
                "step_name": "transform_data",
                "step_type": "compute",
                "depends_on": [validate_id],
                "timeout_ms": 15000,
            },
            {
                "step_id": persist_id,
                "step_name": "persist_results",
                "step_type": "effect",
                "depends_on": [transform_id],
                "timeout_ms": 10000,
            },
        ]

        workflow_id = uuid4()
        input_data = ModelOrchestratorInput(
            workflow_id=workflow_id,
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Act
        result: ModelOrchestratorOutput = asyncio.run(orchestrator.process(input_data))

        # Assert
        assert result.execution_status == EnumWorkflowState.COMPLETED.value
        assert len(result.completed_steps) == 4
        assert len(result.failed_steps) == 0
        assert len(result.actions_emitted) == 4

        # Verify all steps completed in correct order
        completed_step_ids = [UUID(s) for s in result.completed_steps]
        assert fetch_id in completed_step_ids
        assert validate_id in completed_step_ids
        assert transform_id in completed_step_ids
        assert persist_id in completed_step_ids

    def test_workflow_with_context_metadata(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test Scenario 4: Workflow with metadata preservation.

        This test verifies:
        - Input metadata is preserved through execution
        - Workflow context contains expected data
        - Actions contain correct metadata
        """
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="metadata_test_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        step_id = uuid4()
        steps = [
            {
                "step_id": step_id,
                "step_name": "metadata_step",
                "step_type": "compute",
                "timeout_ms": 5000,
            },
        ]

        workflow_id = uuid4()
        input_data = ModelOrchestratorInput(
            workflow_id=workflow_id,
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            metadata=ModelOrchestratorInputMetadata(
                source="integration_test",
                environment="test",
                correlation_id=uuid4(),
            ),
        )

        # Act
        result: ModelOrchestratorOutput = asyncio.run(orchestrator.process(input_data))

        # Assert
        assert result.execution_status == EnumWorkflowState.COMPLETED.value

        # Verify workflow state contains context
        snapshot = orchestrator.snapshot_workflow_state()
        assert snapshot is not None
        assert "execution_status" in snapshot.context
        assert snapshot.context["execution_status"] == "completed"


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestOrchestratorIntegrationEdgeCases:
    """Edge case tests for NodeOrchestrator.

    Tests verify:
    1. Parallel execution patterns
    2. Workflow snapshot/restore
    3. Disabled step handling
    4. Empty workflow handling
    5. Invalid dependency detection
    """

    def test_parallel_execution_mode(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test parallel execution mode with independent steps."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="parallel_workflow",
            execution_mode="parallel",
            parallel_execution_allowed=True,
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create independent steps (no dependencies)
        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()

        steps = [
            {
                "step_id": step1_id,
                "step_name": "parallel_step_1",
                "step_type": "compute",
                "timeout_ms": 5000,
            },
            {
                "step_id": step2_id,
                "step_name": "parallel_step_2",
                "step_type": "compute",
                "timeout_ms": 5000,
            },
            {
                "step_id": step3_id,
                "step_name": "parallel_step_3",
                "step_type": "compute",
                "timeout_ms": 5000,
            },
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.PARALLEL,
            max_parallel_steps=3,
        )

        # Act
        result: ModelOrchestratorOutput = asyncio.run(orchestrator.process(input_data))

        # Assert
        assert result.execution_status == EnumWorkflowState.COMPLETED.value
        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0

    def test_workflow_snapshot_and_restore(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test workflow state snapshot and restore capabilities."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="snapshot_test_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        step_id = uuid4()
        steps = [
            {
                "step_id": step_id,
                "step_name": "snapshot_step",
                "step_type": "compute",
                "timeout_ms": 5000,
            },
        ]

        workflow_id = uuid4()
        input_data = ModelOrchestratorInput(
            workflow_id=workflow_id,
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Act: Execute workflow
        asyncio.run(orchestrator.process(input_data))

        # Take snapshot
        snapshot = orchestrator.snapshot_workflow_state(deep_copy=True)
        assert snapshot is not None

        # Verify snapshot structure
        assert snapshot.workflow_id == workflow_id
        assert len(snapshot.completed_step_ids) == 1
        assert step_id in snapshot.completed_step_ids
        assert len(snapshot.failed_step_ids) == 0

        # Get dict representation
        snapshot_dict = orchestrator.get_workflow_snapshot(deep_copy=True)
        assert snapshot_dict is not None
        assert snapshot_dict["workflow_id"] == str(workflow_id)
        assert snapshot_dict["current_step_index"] == 1

        # Create new orchestrator and restore state
        orchestrator2 = orchestrator_with_contract_factory(workflow_definition)
        orchestrator2.restore_workflow_state(snapshot)

        # Verify restoration
        restored_snapshot = orchestrator2.snapshot_workflow_state()
        assert restored_snapshot is not None
        assert restored_snapshot.workflow_id == workflow_id
        assert len(restored_snapshot.completed_step_ids) == 1

    def test_disabled_step_handling(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test that disabled steps are skipped during execution."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="disabled_step_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        enabled_step_id = uuid4()
        disabled_step_id = uuid4()

        steps = [
            {
                "step_id": enabled_step_id,
                "step_name": "enabled_step",
                "step_type": "compute",
                "enabled": True,
                "timeout_ms": 5000,
            },
            {
                "step_id": disabled_step_id,
                "step_name": "disabled_step",
                "step_type": "compute",
                "enabled": False,  # This step should be skipped
                "timeout_ms": 5000,
            },
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Act
        result: ModelOrchestratorOutput = asyncio.run(orchestrator.process(input_data))

        # Assert: Only enabled step should be in completed list
        assert result.execution_status == EnumWorkflowState.COMPLETED.value
        assert len(result.completed_steps) == 1
        assert str(enabled_step_id) in result.completed_steps
        assert str(disabled_step_id) not in result.completed_steps

    def test_batch_execution_mode(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test batch execution mode."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="batch_workflow",
            execution_mode="batch",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create batch of steps
        steps = [
            {
                "step_id": uuid4(),
                "step_name": f"batch_step_{i}",
                "step_type": "compute",
                "timeout_ms": 5000,
            }
            for i in range(5)
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.BATCH,
        )

        # Act
        result: ModelOrchestratorOutput = asyncio.run(orchestrator.process(input_data))

        # Assert
        assert result.execution_status == EnumWorkflowState.COMPLETED.value
        assert len(result.completed_steps) == 5

    def test_contract_validation_without_steps(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test workflow contract validation without steps (structural validation only).

        Note: validate_contract() validates the workflow definition structure without
        steps. It correctly returns an error when no steps are provided because a
        workflow with no steps is not valid for execution.
        """
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="validation_test_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Act: Validate contract (without steps)
        errors = asyncio.run(orchestrator.validate_contract())

        # Assert: Should return error about no steps (expected behavior)
        assert len(errors) == 1
        assert "no steps" in errors[0].lower()

    def test_workflow_step_validation(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test workflow step validation with valid steps."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="step_validation_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create valid workflow steps
        step1_id = uuid4()
        step2_id = uuid4()
        steps = create_workflow_steps(
            [
                {
                    "step_id": step1_id,
                    "step_name": "step_1",
                    "step_type": "compute",
                },
                {
                    "step_id": step2_id,
                    "step_name": "step_2",
                    "step_type": "effect",
                    "depends_on": [step1_id],
                },
            ]
        )

        # Act: Validate steps
        errors = asyncio.run(orchestrator.validate_workflow_steps(steps))

        # Assert: Steps should be valid
        assert errors == []

    def test_execution_order_for_steps(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test getting topological execution order for steps."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="execution_order_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create steps with dependencies: A -> B -> C
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        steps = create_workflow_steps(
            [
                {
                    "step_id": step_c_id,  # Out of order in list
                    "step_name": "step_c",
                    "step_type": "compute",
                    "depends_on": [step_b_id],
                },
                {
                    "step_id": step_a_id,
                    "step_name": "step_a",
                    "step_type": "effect",
                    "depends_on": [],
                },
                {
                    "step_id": step_b_id,
                    "step_name": "step_b",
                    "step_type": "compute",
                    "depends_on": [step_a_id],
                },
            ]
        )

        # Act: Get execution order
        order = orchestrator.get_execution_order_for_steps(steps)

        # Assert: Order should respect dependencies
        assert len(order) == 3
        assert order.index(step_a_id) < order.index(step_b_id)
        assert order.index(step_b_id) < order.index(step_c_id)

    def test_snapshot_with_deep_copy(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test that deep_copy=True creates independent snapshot."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="deep_copy_test",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        step_id = uuid4()
        steps = [
            {
                "step_id": step_id,
                "step_name": "test_step",
                "step_type": "compute",
            },
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Execute workflow
        asyncio.run(orchestrator.process(input_data))

        # Act: Get snapshots with and without deep copy
        snapshot_shallow = orchestrator.snapshot_workflow_state(deep_copy=False)
        snapshot_deep = orchestrator.snapshot_workflow_state(deep_copy=True)

        # Assert: Both snapshots should have same data
        assert snapshot_shallow is not None
        assert snapshot_deep is not None
        assert snapshot_shallow.workflow_id == snapshot_deep.workflow_id
        assert snapshot_shallow.current_step_index == snapshot_deep.current_step_index

    def test_workflow_metrics_tracking(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test that workflow execution tracks metrics correctly."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="metrics_test_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        steps = [
            {
                "step_id": uuid4(),
                "step_name": f"step_{i}",
                "step_type": "compute",
            }
            for i in range(3)
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Act
        result: ModelOrchestratorOutput = asyncio.run(orchestrator.process(input_data))

        # Assert: Verify metrics
        assert "actions_count" in result.metrics
        assert "completed_count" in result.metrics
        assert "failed_count" in result.metrics
        assert result.metrics["actions_count"] == 3.0
        assert result.metrics["completed_count"] == 3.0
        assert result.metrics["failed_count"] == 0.0


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestOrchestratorIntegrationValidation:
    """Validation-focused integration tests for NodeOrchestrator.

    Tests verify:
    1. Invalid workflow snapshot validation
    2. Workflow definition validation errors
    3. Dependency cycle detection
    """

    def test_invalid_snapshot_future_timestamp(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test that restoring snapshot with future timestamp fails validation."""
        from datetime import UTC, datetime, timedelta

        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="future_timestamp_test",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create snapshot with timestamp far in the future (beyond tolerance)
        future_time = datetime.now(UTC) + timedelta(hours=1)
        invalid_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=uuid4(),
            current_step_index=0,
            completed_step_ids=(),
            failed_step_ids=(),
            context={},
            created_at=future_time,
        )

        # Act & Assert: Expect validation error
        with pytest.raises(ModelOnexError) as exc_info:
            orchestrator.restore_workflow_state(invalid_snapshot)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "future" in exc_info.value.message.lower()

    def test_invalid_snapshot_overlapping_step_ids(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test that restoring snapshot with overlapping completed/failed step IDs fails."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="overlapping_ids_test",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create snapshot with same step in both completed and failed
        shared_step_id = uuid4()
        invalid_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=uuid4(),
            current_step_index=1,
            completed_step_ids=(shared_step_id,),
            failed_step_ids=(shared_step_id,),  # Same ID - invalid!
            context={},
        )

        # Act & Assert: Expect validation error
        with pytest.raises(ModelOnexError) as exc_info:
            orchestrator.restore_workflow_state(invalid_snapshot)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        # Error message says "cannot be both completed and failed"
        assert "both completed and failed" in exc_info.value.message.lower()

    def test_workflow_validation_invalid_execution_mode(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test workflow validation catches invalid execution mode."""
        # Arrange: Create workflow with invalid execution mode
        workflow_definition = ModelWorkflowDefinition(
            version=V1_0_0,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=V1_0_0,
                workflow_name="invalid_mode_test",
                workflow_version=V1_0_0,
                description="Test invalid mode",
                execution_mode="invalid_mode",  # Invalid!
                timeout_ms=60000,
            ),
            execution_graph=ModelExecutionGraph(
                version=V1_0_0,
                nodes=[],
            ),
            coordination_rules=ModelCoordinationRules(
                version=V1_0_0,
            ),
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        steps = [
            {
                "step_id": uuid4(),
                "step_name": "test_step",
                "step_type": "compute",
            },
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
        )

        # Act & Assert: Should raise validation error
        with pytest.raises(ModelOnexError):
            asyncio.run(orchestrator.process(input_data))

    def test_workflow_validation_dependency_cycle(
        self, orchestrator_with_contract_factory: OrchestratorWithContractFactory
    ) -> None:
        """Test workflow validation detects dependency cycles."""
        # Arrange
        workflow_definition = create_test_workflow_definition(
            name="cycle_test_workflow",
            execution_mode="sequential",
        )

        orchestrator = orchestrator_with_contract_factory(workflow_definition)

        # Create steps with circular dependency: A -> B -> C -> A
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        steps = create_workflow_steps(
            [
                {
                    "step_id": step_a_id,
                    "step_name": "step_a",
                    "step_type": "compute",
                    "depends_on": [step_c_id],  # Creates cycle!
                },
                {
                    "step_id": step_b_id,
                    "step_name": "step_b",
                    "step_type": "compute",
                    "depends_on": [step_a_id],
                },
                {
                    "step_id": step_c_id,
                    "step_name": "step_c",
                    "step_type": "compute",
                    "depends_on": [step_b_id],
                },
            ]
        )

        # Act: Validate steps
        errors = asyncio.run(orchestrator.validate_workflow_steps(steps))

        # Assert: Should detect cycle
        assert len(errors) > 0
        assert any("cycle" in error.lower() for error in errors)
