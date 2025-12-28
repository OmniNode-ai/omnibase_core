"""
Unit tests for MixinWorkflowExecution.

Tests the workflow execution mixin for declarative orchestration.
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import (
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.mixins.mixin_workflow_execution import MixinWorkflowExecution
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


# Mock node using the mixin
class MockNodeWithWorkflowMixin(MixinWorkflowExecution):
    """Mock node implementing MixinWorkflowExecution."""

    def __init__(self):
        """Initialize mock node."""
        super().__init__()


@pytest.fixture
def workflow_definition() -> ModelWorkflowDefinition:
    """Create test workflow definition."""
    return ModelWorkflowDefinition(
        version=ModelSemVer(major=1, minor=0, patch=0),
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            version=ModelSemVer(major=1, minor=0, patch=0),
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow for workflow execution mixin",
            execution_mode="sequential",
        ),
        execution_graph=ModelExecutionGraph(
            version=ModelSemVer(major=1, minor=0, patch=0),
            nodes=[],
        ),
        coordination_rules=ModelCoordinationRules(
            version=ModelSemVer(major=1, minor=0, patch=0),
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
        ),
    )


@pytest.fixture
def simple_steps() -> list[ModelWorkflowStep]:
    """Create simple workflow steps."""
    step1_id = uuid4()
    step2_id = uuid4()
    step3_id = uuid4()

    return [
        ModelWorkflowStep(
            step_id=step1_id,
            step_name="Step 1",
            step_type="effect",
        ),
        ModelWorkflowStep(
            step_id=step2_id,
            step_name="Step 2",
            step_type="compute",
            depends_on=[step1_id],
        ),
        ModelWorkflowStep(
            step_id=step3_id,
            step_name="Step 3",
            step_type="effect",
            depends_on=[step2_id],
        ),
    ]


@pytest.fixture
def parallel_steps() -> list[ModelWorkflowStep]:
    """Create parallel workflow steps."""
    fetch_id = uuid4()
    validate_id = uuid4()
    enrich_id = uuid4()
    persist_id = uuid4()

    return [
        ModelWorkflowStep(
            step_id=fetch_id,
            step_name="Fetch Data",
            step_type="effect",
        ),
        # These can run in parallel
        ModelWorkflowStep(
            step_id=validate_id,
            step_name="Validate Schema",
            step_type="compute",
            depends_on=[fetch_id],
        ),
        ModelWorkflowStep(
            step_id=enrich_id,
            step_name="Enrich Data",
            step_type="compute",
            depends_on=[fetch_id],
        ),
        # This runs after both
        ModelWorkflowStep(
            step_id=persist_id,
            step_name="Persist Results",
            step_type="effect",
            depends_on=[validate_id, enrich_id],
        ),
    ]


@pytest.mark.unit
class TestMixinWorkflowExecution:
    """Test workflow execution mixin methods."""

    @pytest.mark.asyncio
    async def test_execute_workflow_from_contract_sequential(
        self,
        workflow_definition: ModelWorkflowDefinition,
        simple_steps: list[ModelWorkflowStep],
    ):
        """Test executing workflow from contract in sequential mode."""
        node = MockNodeWithWorkflowMixin()
        workflow_id = uuid4()

        result = await node.execute_workflow_from_contract(
            workflow_definition,
            simple_steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0
        assert len(result.actions_emitted) == 3

    @pytest.mark.asyncio
    async def test_execute_workflow_from_contract_parallel(
        self,
        workflow_definition: ModelWorkflowDefinition,
        parallel_steps: list[ModelWorkflowStep],
    ):
        """Test executing workflow from contract in parallel mode."""
        node = MockNodeWithWorkflowMixin()
        workflow_id = uuid4()

        result = await node.execute_workflow_from_contract(
            workflow_definition,
            parallel_steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 4  # All steps should complete
        assert len(result.failed_steps) == 0

    @pytest.mark.asyncio
    async def test_execute_workflow_uses_definition_execution_mode(
        self,
        workflow_definition: ModelWorkflowDefinition,
        simple_steps: list[ModelWorkflowStep],
    ):
        """Test execution uses mode from definition when not overridden."""
        node = MockNodeWithWorkflowMixin()
        workflow_id = uuid4()

        # Definition specifies sequential mode
        result = await node.execute_workflow_from_contract(
            workflow_definition, simple_steps, workflow_id
        )

        # result.metadata is now a typed ModelWorkflowResultMetadata, not a dict
        assert result.metadata is not None
        assert result.metadata.execution_mode == "sequential"

    @pytest.mark.asyncio
    async def test_execute_workflow_emits_actions(
        self,
        workflow_definition: ModelWorkflowDefinition,
        simple_steps: list[ModelWorkflowStep],
    ):
        """Test workflow execution emits actions for all steps."""
        node = MockNodeWithWorkflowMixin()
        workflow_id = uuid4()

        result = await node.execute_workflow_from_contract(
            workflow_definition, simple_steps, workflow_id
        )

        # Should have one action per step
        assert len(result.actions_emitted) == len(simple_steps)

        # All actions should have required fields
        for action in result.actions_emitted:
            assert action.action_id is not None
            assert action.action_type is not None
            assert action.target_node_type is not None
            assert action.lease_id is not None
            assert action.epoch == 0
            # workflow_id is in payload.metadata (typed payload model)
            assert "workflow_id" in action.payload.metadata
            assert action.payload.metadata["workflow_id"] == str(workflow_id)

    @pytest.mark.asyncio
    async def test_execute_workflow_tracks_execution_time(
        self,
        workflow_definition: ModelWorkflowDefinition,
        simple_steps: list[ModelWorkflowStep],
    ):
        """Test workflow execution tracks execution time."""
        node = MockNodeWithWorkflowMixin()

        result = await node.execute_workflow_from_contract(
            workflow_definition, simple_steps, uuid4()
        )

        assert result.execution_time_ms > 0
        assert isinstance(result.execution_time_ms, int)


@pytest.mark.unit
class TestMixinWorkflowValidation:
    """Test workflow validation through mixin."""

    @pytest.mark.asyncio
    async def test_validate_workflow_contract_valid(
        self,
        workflow_definition: ModelWorkflowDefinition,
        simple_steps: list[ModelWorkflowStep],
    ):
        """Test validation passes for valid workflow."""
        node = MockNodeWithWorkflowMixin()

        errors = await node.validate_workflow_contract(
            workflow_definition, simple_steps
        )

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_workflow_contract_empty_steps(
        self, workflow_definition: ModelWorkflowDefinition
    ):
        """Test validation passes for workflow with no steps (zero errors).

        Empty workflows are explicitly VALID by design per v1.0.3 Fix 29.
        The workflow executor treats empty workflows as valid and returns
        a COMPLETED status with 0 actions. This is intentional behavior per
        workflow_executor.py lines 522-524 which explicitly does NOT add an
        error for empty workflows.
        """
        node = MockNodeWithWorkflowMixin()

        errors = await node.validate_workflow_contract(workflow_definition, [])

        # v1.0.3 Fix 29: Empty workflows should pass validation with zero errors
        assert errors == [], (
            f"Empty workflow should succeed per v1.0.3 Fix 29, but got errors: {errors}"
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_contract_invalid_dependency(
        self, workflow_definition: ModelWorkflowDefinition
    ):
        """Test validation fails for invalid step dependency."""
        node = MockNodeWithWorkflowMixin()
        invalid_dep_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_name="Step 1",
                step_type="effect",
                depends_on=[invalid_dep_id],  # Non-existent dependency
            ),
        ]

        errors = await node.validate_workflow_contract(workflow_definition, steps)

        assert len(errors) > 0
        assert any("non-existent" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_validate_workflow_contract_circular_dependency(
        self, workflow_definition: ModelWorkflowDefinition
    ):
        """Test validation detects circular dependencies."""
        node = MockNodeWithWorkflowMixin()
        step1_id = uuid4()
        step2_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="Step 1",
                step_type="effect",
                depends_on=[step2_id],
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Step 2",
                step_type="effect",
                depends_on=[step1_id],
            ),
        ]

        errors = await node.validate_workflow_contract(workflow_definition, steps)

        assert len(errors) > 0
        assert any("cycle" in error.lower() for error in errors)


@pytest.mark.unit
class TestMixinExecutionOrder:
    """Test execution order computation through mixin."""

    def test_get_workflow_execution_order_simple(
        self, simple_steps: list[ModelWorkflowStep]
    ):
        """Test getting execution order for simple workflow."""
        node = MockNodeWithWorkflowMixin()

        order = node.get_workflow_execution_order(simple_steps)

        # Should have 3 steps
        assert len(order) == 3

        # Get step IDs
        step1_id = simple_steps[0].step_id
        step2_id = simple_steps[1].step_id
        step3_id = simple_steps[2].step_id

        # Check order respects dependencies
        step1_index = order.index(step1_id)
        step2_index = order.index(step2_id)
        step3_index = order.index(step3_id)

        assert step1_index < step2_index  # Step 1 before Step 2
        assert step2_index < step3_index  # Step 2 before Step 3

    def test_get_workflow_execution_order_parallel(
        self, parallel_steps: list[ModelWorkflowStep]
    ):
        """Test getting execution order for parallel workflow."""
        node = MockNodeWithWorkflowMixin()

        order = node.get_workflow_execution_order(parallel_steps)

        # Should have 4 steps
        assert len(order) == 4

        # Fetch should be first
        fetch_id = parallel_steps[0].step_id
        assert order[0] == fetch_id

        # Persist should be last
        persist_id = parallel_steps[3].step_id
        assert order[3] == persist_id

    def test_get_workflow_execution_order_with_cycle_raises_error(self):
        """Test execution order with cycle raises error."""
        node = MockNodeWithWorkflowMixin()
        step1_id = uuid4()
        step2_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="Step 1",
                step_type="effect",
                depends_on=[step2_id],
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Step 2",
                step_type="effect",
                depends_on=[step1_id],
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            node.get_workflow_execution_order(steps)

        assert "cycle" in str(exc_info.value).lower()


@pytest.mark.unit
class TestMixinStepCreation:
    """Test creating workflow steps from configuration."""

    def test_create_workflow_steps_from_config(self):
        """Test creating ModelWorkflowStep instances from config dicts."""
        node = MockNodeWithWorkflowMixin()

        step1_id = uuid4()
        step2_id = uuid4()

        steps_config = [
            {
                "step_id": step1_id,
                "step_name": "Fetch Data",
                "step_type": "effect",
                "timeout_ms": 10000,
            },
            {
                "step_id": step2_id,
                "step_name": "Process Data",
                "step_type": "compute",
                "depends_on": [step1_id],
                "timeout_ms": 15000,
            },
        ]

        steps = node.create_workflow_steps_from_config(steps_config)

        # Verify steps created
        assert len(steps) == 2
        assert all(isinstance(step, ModelWorkflowStep) for step in steps)

        # Verify first step
        assert steps[0].step_id == step1_id
        assert steps[0].step_name == "Fetch Data"
        assert steps[0].step_type == "effect"
        assert steps[0].timeout_ms == 10000

        # Verify second step
        assert steps[1].step_id == step2_id
        assert steps[1].step_name == "Process Data"
        assert steps[1].step_type == "compute"
        assert steps[1].depends_on == [step1_id]
        assert steps[1].timeout_ms == 15000

    def test_create_workflow_steps_from_config_empty(self):
        """Test creating steps from empty config."""
        node = MockNodeWithWorkflowMixin()

        steps = node.create_workflow_steps_from_config([])

        assert len(steps) == 0
        assert isinstance(steps, list)


@pytest.mark.unit
class TestMixinIntegration:
    """Test mixin integration with workflow executor."""

    @pytest.mark.asyncio
    async def test_mixin_integrates_with_executor(
        self,
        workflow_definition: ModelWorkflowDefinition,
        simple_steps: list[ModelWorkflowStep],
    ):
        """Test mixin correctly delegates to workflow executor."""
        node = MockNodeWithWorkflowMixin()
        workflow_id = uuid4()

        # Execute workflow through mixin
        result = await node.execute_workflow_from_contract(
            workflow_definition, simple_steps, workflow_id
        )

        # Verify result matches executor behavior
        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == len(simple_steps)
        assert result.skipped_steps == []  # No disabled steps
        assert len(result.actions_emitted) == len(simple_steps)

    @pytest.mark.asyncio
    async def test_mixin_handles_empty_workflow_successfully(
        self, workflow_definition: ModelWorkflowDefinition
    ):
        """Test mixin handles empty workflows successfully (empty workflows are valid).

        Empty workflows are explicitly VALID by design. The workflow executor
        returns a COMPLETED status with 0 actions when no steps are defined.
        This is intentional behavior per workflow_executor.py lines 349-368
        and 522-524.
        """
        node = MockNodeWithWorkflowMixin()
        workflow_id = uuid4()

        # Empty workflow should execute successfully
        result = await node.execute_workflow_from_contract(
            workflow_definition, [], workflow_id
        )

        # Empty workflow completes with 0 steps and 0 actions
        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 0
        assert len(result.failed_steps) == 0
        assert result.skipped_steps == []  # No steps to skip
        assert len(result.actions_emitted) == 0
