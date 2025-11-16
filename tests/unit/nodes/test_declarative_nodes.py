"""
Unit tests for declarative node base classes.

Tests NodeReducerDeclarative and NodeOrchestratorDeclarative for YAML-driven execution.
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
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
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.model_orchestrator_input import ModelOrchestratorInput
from omnibase_core.models.model_reducer_input import ModelReducerInput
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_orchestrator_declarative import (
    NodeOrchestratorDeclarative,
)
from omnibase_core.nodes.node_reducer_declarative import NodeReducerDeclarative


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def simple_fsm() -> ModelFSMSubcontract:
    """Create simple FSM contract for testing."""
    return ModelFSMSubcontract(
        state_machine_name="test_fsm",
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                description="Initial state",
                entry_actions=[],
                exit_actions=[],
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                description="Processing state",
                entry_actions=["start_processing"],
                exit_actions=["stop_processing"],
            ),
            ModelFSMStateDefinition(
                state_name="completed",
                description="Terminal state",
                is_terminal=True,
            ),
        ],
        transitions=[
            ModelFSMStateTransition(
                transition_name="start",
                from_state="idle",
                to_state="processing",
                trigger="start_event",
                conditions=[],
                actions=[],
            ),
            ModelFSMStateTransition(
                transition_name="complete",
                from_state="processing",
                to_state="completed",
                trigger="complete_event",
                conditions=[],
                actions=[],
            ),
        ],
        terminal_states=["completed"],
        error_states=[],
        persistence_enabled=True,
    )


@pytest.fixture
def simple_workflow_definition() -> ModelWorkflowDefinition:
    """Create simple workflow definition for testing."""
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow for declarative nodes",
            execution_mode="sequential",
        ),
        execution_graph=ModelExecutionGraph(nodes=[]),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
        ),
    )


class TestNodeReducerDeclarative:
    """Test declarative reducer node."""

    def test_initialization(self, test_container: ModelONEXContainer):
        """Test node initialization."""
        node = NodeReducerDeclarative(test_container)

        assert node.container is test_container
        assert node.node_id is not None
        assert node.fsm_contract is None  # No contract loaded yet

    def test_initialization_with_fsm_contract(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test node initialization with FSM contract."""

        # Create a mock contract object
        class MockContract:
            def __init__(self):
                self.state_transitions = simple_fsm

        node = NodeReducerDeclarative(test_container)
        node.contract = MockContract()  # type: ignore[assignment]
        node.__init__(test_container)  # Reinitialize with contract

        assert node.fsm_contract is not None
        assert node.fsm_contract.state_machine_name == "test_fsm"

    @pytest.mark.asyncio
    async def test_process_with_fsm(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test processing with FSM execution."""
        node = NodeReducerDeclarative(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create input with trigger
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata={"trigger": "start_event"},
        )

        result = await node.process(input_data)

        # Check FSM transition occurred
        assert result.metadata["fsm_state"] == "processing"
        assert result.metadata["fsm_success"] is True
        assert len(result.intents) > 0  # Intents emitted

    @pytest.mark.asyncio
    async def test_process_without_fsm_raises_error(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test processing without FSM contract raises error."""
        node = NodeReducerDeclarative(test_container)

        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata={"trigger": "start_event"},
        )

        with pytest.raises(ValueError) as exc_info:
            await node.process(input_data)

        assert "FSM contract not loaded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_contract(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test contract validation."""
        node = NodeReducerDeclarative(test_container)
        node.fsm_contract = simple_fsm

        errors = await node.validate_contract()

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_contract_without_fsm(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test validation without FSM contract."""
        node = NodeReducerDeclarative(test_container)

        errors = await node.validate_contract()

        assert len(errors) == 1
        assert "FSM contract not loaded" in errors[0]

    def test_get_current_state(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test getting current state."""
        node = NodeReducerDeclarative(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        state = node.get_current_state()

        assert state == "idle"

    def test_get_state_history(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test getting state history."""
        node = NodeReducerDeclarative(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        history = node.get_state_history()

        assert len(history) == 0  # No transitions yet

    @pytest.mark.asyncio
    async def test_is_complete_false_when_not_terminal(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test is_complete returns False for non-terminal state."""
        node = NodeReducerDeclarative(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        assert not node.is_complete()

    @pytest.mark.asyncio
    async def test_is_complete_true_when_terminal(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test is_complete returns True for terminal state."""
        node = NodeReducerDeclarative(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Transition to terminal state
        await node.execute_fsm_transition(simple_fsm, "start_event", {})
        await node.execute_fsm_transition(simple_fsm, "complete_event", {})

        assert node.is_complete()


class TestNodeOrchestratorDeclarative:
    """Test declarative orchestrator node."""

    def test_initialization(self, test_container: ModelONEXContainer):
        """Test node initialization."""
        node = NodeOrchestratorDeclarative(test_container)

        assert node.container is test_container
        assert node.node_id is not None
        assert node.workflow_definition is None  # No definition loaded yet

    def test_initialization_with_workflow_definition(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test node initialization with workflow definition."""

        # Create a mock contract object
        class MockWorkflowCoordination:
            def __init__(self):
                self.workflow_definition = simple_workflow_definition

        class MockContract:
            def __init__(self):
                self.workflow_coordination = MockWorkflowCoordination()

        node = NodeOrchestratorDeclarative(test_container)
        node.contract = MockContract()  # type: ignore[assignment]
        node.__init__(test_container)  # Reinitialize with contract

        assert node.workflow_definition is not None
        assert (
            node.workflow_definition.workflow_metadata.workflow_name == "test_workflow"
        )

    @pytest.mark.asyncio
    async def test_process_with_workflow(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test processing with workflow execution."""
        node = NodeOrchestratorDeclarative(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create workflow steps
        step1_id = uuid4()
        step2_id = uuid4()

        steps_config = [
            {
                "step_id": step1_id,
                "step_name": "Step 1",
                "step_type": "effect",
            },
            {
                "step_id": step2_id,
                "step_name": "Step 2",
                "step_type": "compute",
                "depends_on": [step1_id],
            },
        ]

        # Create input
        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps_config,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result = await node.process(input_data)

        # Check workflow executed
        assert result.execution_status == "completed"
        assert len(result.completed_steps) == 2
        assert len(result.actions_emitted) == 2

    @pytest.mark.asyncio
    async def test_process_without_workflow_raises_error(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test processing without workflow definition raises error."""
        node = NodeOrchestratorDeclarative(test_container)

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[],
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        with pytest.raises(ValueError) as exc_info:
            await node.process(input_data)

        assert "Workflow definition not loaded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_contract(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test contract validation."""
        node = NodeOrchestratorDeclarative(test_container)
        node.workflow_definition = simple_workflow_definition

        errors = await node.validate_contract()

        # Empty workflow has validation error
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_validate_contract_without_definition(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test validation without workflow definition."""
        node = NodeOrchestratorDeclarative(test_container)

        errors = await node.validate_contract()

        assert len(errors) == 1
        assert "Workflow definition not loaded" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_workflow_steps(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test validating workflow steps."""
        node = NodeOrchestratorDeclarative(test_container)
        node.workflow_definition = simple_workflow_definition

        steps = [
            ModelWorkflowStep(step_name="Step 1", step_type="effect"),
            ModelWorkflowStep(step_name="Step 2", step_type="compute"),
        ]

        errors = await node.validate_workflow_steps(steps)

        assert len(errors) == 0  # Valid steps

    def test_get_execution_order_for_steps(
        self,
        test_container: ModelONEXContainer,
    ):
        """Test getting execution order."""
        node = NodeOrchestratorDeclarative(test_container)

        step1_id = uuid4()
        step2_id = uuid4()

        steps = [
            ModelWorkflowStep(step_id=step1_id, step_name="Step 1", step_type="effect"),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Step 2",
                step_type="compute",
                depends_on=[step1_id],
            ),
        ]

        order = node.get_execution_order_for_steps(steps)

        assert len(order) == 2
        assert order[0] == step1_id  # Step 1 first
        assert order[1] == step2_id  # Step 2 second


class TestDeclarativeNodesIntegration:
    """Integration tests for declarative nodes."""

    @pytest.mark.asyncio
    async def test_reducer_full_workflow(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ):
        """Test complete reducer workflow."""
        node = NodeReducerDeclarative(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Verify initial state
        assert node.get_current_state() == "idle"
        assert not node.is_complete()

        # Transition to processing
        input1 = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata={"trigger": "start_event"},
        )
        result1 = await node.process(input1)
        assert result1.metadata["fsm_state"] == "processing"

        # Transition to completed
        input2 = ModelReducerInput(
            data=[4, 5, 6],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata={"trigger": "complete_event"},
        )
        result2 = await node.process(input2)
        assert result2.metadata["fsm_state"] == "completed"
        assert node.is_complete()

    @pytest.mark.asyncio
    async def test_orchestrator_parallel_workflow(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ):
        """Test parallel workflow execution."""
        # Update definition to allow parallel execution
        simple_workflow_definition.workflow_metadata.execution_mode = "parallel"
        simple_workflow_definition.coordination_rules.parallel_execution_allowed = True

        node = NodeOrchestratorDeclarative(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create parallel steps
        fetch_id = uuid4()
        validate_id = uuid4()
        enrich_id = uuid4()
        persist_id = uuid4()

        steps_config = [
            {"step_id": fetch_id, "step_name": "Fetch Data", "step_type": "effect"},
            {
                "step_id": validate_id,
                "step_name": "Validate Schema",
                "step_type": "compute",
                "depends_on": [fetch_id],
            },
            {
                "step_id": enrich_id,
                "step_name": "Enrich Data",
                "step_type": "compute",
                "depends_on": [fetch_id],
            },
            {
                "step_id": persist_id,
                "step_name": "Persist Results",
                "step_type": "effect",
                "depends_on": [validate_id, enrich_id],
            },
        ]

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps_config,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        result = await node.process(input_data)

        assert result.execution_status == "completed"
        assert len(result.completed_steps) == 4
        assert len(result.actions_emitted) == 4
