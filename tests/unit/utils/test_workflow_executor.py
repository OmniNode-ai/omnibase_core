"""
Unit tests for workflow execution utilities.

Tests the pure functions in utils/workflow_executor.py for workflow execution.
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import (
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.workflow_executor import (
    execute_workflow,
    get_execution_order,
    validate_workflow_definition,
)


@pytest.fixture
def simple_workflow_definition() -> ModelWorkflowDefinition:
    """Create simple workflow definition."""
    from omnibase_core.models.primitives.model_semver import ModelSemVer

    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow for unit tests",
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
def simple_workflow_steps() -> list[ModelWorkflowStep]:
    """Create simple workflow steps."""
    step1_id = uuid4()
    step2_id = uuid4()
    step3_id = uuid4()

    return [
        ModelWorkflowStep(
            step_id=step1_id,
            step_name="Fetch Data",
            step_type="effect",
            timeout_ms=10000,
        ),
        ModelWorkflowStep(
            step_id=step2_id,
            step_name="Process Data",
            step_type="compute",
            depends_on=[step1_id],
            timeout_ms=15000,
        ),
        ModelWorkflowStep(
            step_id=step3_id,
            step_name="Save Results",
            step_type="effect",
            depends_on=[step2_id],
            timeout_ms=8000,
        ),
    ]


@pytest.fixture
def parallel_workflow_steps() -> list[ModelWorkflowStep]:
    """Create workflow steps for parallel execution."""
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
        # These can run in parallel after fetch
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
        # This runs after both validate and enrich
        ModelWorkflowStep(
            step_id=persist_id,
            step_name="Persist Results",
            step_type="effect",
            depends_on=[validate_id, enrich_id],
        ),
    ]


class TestWorkflowExecutionSuccess:
    """Test successful workflow execution."""

    @pytest.mark.asyncio
    async def test_sequential_workflow(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test sequential workflow execution."""
        workflow_id = uuid4()

        result = await execute_workflow(
            simple_workflow_definition,
            simple_workflow_steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0
        assert len(result.actions_emitted) == 3

    @pytest.mark.asyncio
    async def test_parallel_workflow(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        parallel_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test parallel workflow execution."""
        workflow_id = uuid4()

        result = await execute_workflow(
            simple_workflow_definition,
            parallel_workflow_steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        assert result.workflow_id == workflow_id
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 4  # All steps should complete
        assert len(result.failed_steps) == 0

    @pytest.mark.asyncio
    async def test_actions_emitted(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test that actions are emitted for all steps."""
        workflow_id = uuid4()

        result = await execute_workflow(
            simple_workflow_definition,
            simple_workflow_steps,
            workflow_id,
        )

        # Should have one action per step
        assert len(result.actions_emitted) == len(simple_workflow_steps)

        # Check action properties
        for action in result.actions_emitted:
            assert action.action_id is not None
            assert action.action_type is not None
            assert action.target_node_type is not None
            assert action.lease_id is not None
            assert action.epoch == 0

    @pytest.mark.asyncio
    async def test_action_dependencies(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test that action dependencies match step dependencies."""
        workflow_id = uuid4()

        result = await execute_workflow(
            simple_workflow_definition,
            simple_workflow_steps,
            workflow_id,
        )

        # Map steps to actions
        actions_by_step_id = {
            action.metadata["correlation_id"]: action
            for action in result.actions_emitted
        }

        # Check dependencies
        for step in simple_workflow_steps:
            step_correlation_id = str(step.correlation_id)
            if step_correlation_id in actions_by_step_id:
                action = actions_by_step_id[step_correlation_id]
                assert len(action.dependencies) == len(step.depends_on)


class TestWorkflowValidation:
    """Test workflow validation."""

    @pytest.mark.asyncio
    async def test_valid_workflow(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test validation of valid workflow."""
        errors = await validate_workflow_definition(
            simple_workflow_definition, simple_workflow_steps
        )
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_empty_workflow(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ):
        """Test validation with no steps."""
        errors = await validate_workflow_definition(simple_workflow_definition, [])
        assert len(errors) > 0
        assert any("no steps" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_invalid_dependency(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ):
        """Test validation with invalid step dependency."""
        invalid_dep_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_name="Step 1",
                step_type="effect",
                depends_on=[invalid_dep_id],  # Non-existent dependency
            ),
        ]

        errors = await validate_workflow_definition(simple_workflow_definition, steps)
        assert len(errors) > 0
        assert any("non-existent" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_circular_dependency(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ):
        """Test validation detects circular dependencies."""
        step1_id = uuid4()
        step2_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="Step 1",
                step_type="effect",
                depends_on=[step2_id],  # Depends on step 2
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Step 2",
                step_type="effect",
                depends_on=[step1_id],  # Depends on step 1 - CYCLE!
            ),
        ]

        errors = await validate_workflow_definition(simple_workflow_definition, steps)
        assert len(errors) > 0
        assert any("cycle" in error.lower() for error in errors)


class TestExecutionOrder:
    """Test execution order computation."""

    def test_simple_execution_order(
        self, simple_workflow_steps: list[ModelWorkflowStep]
    ):
        """Test execution order for simple workflow."""
        order = get_execution_order(simple_workflow_steps)

        # Should have 3 steps
        assert len(order) == 3

        # Get step IDs in original order
        step1_id = simple_workflow_steps[0].step_id
        step2_id = simple_workflow_steps[1].step_id
        step3_id = simple_workflow_steps[2].step_id

        # Check execution order respects dependencies
        step1_index = order.index(step1_id)
        step2_index = order.index(step2_id)
        step3_index = order.index(step3_id)

        assert step1_index < step2_index  # Step 1 before Step 2
        assert step2_index < step3_index  # Step 2 before Step 3

    def test_parallel_execution_order(
        self, parallel_workflow_steps: list[ModelWorkflowStep]
    ):
        """Test execution order for parallel workflow."""
        order = get_execution_order(parallel_workflow_steps)

        # Should have 4 steps
        assert len(order) == 4

        # Fetch should be first
        fetch_id = parallel_workflow_steps[0].step_id
        assert order[0] == fetch_id

        # Persist should be last (depends on validate and enrich)
        persist_id = parallel_workflow_steps[3].step_id
        assert order[3] == persist_id

    def test_execution_order_with_cycle(self):
        """Test execution order with circular dependency."""
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
            get_execution_order(steps)

        assert "cycle" in str(exc_info.value).lower()


class TestDisabledSteps:
    """Test handling of disabled steps."""

    @pytest.mark.asyncio
    async def test_disabled_step_skipped(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ):
        """Test that disabled steps are skipped."""
        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="Step 1",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Step 2",
                step_type="compute",
                enabled=False,  # DISABLED
                depends_on=[step1_id],
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="Step 3",
                step_type="effect",
                enabled=True,
                depends_on=[step2_id],
            ),
        ]

        result = await execute_workflow(simple_workflow_definition, steps, uuid4())

        # Step 1 should complete
        # Step 2 should be skipped (disabled)
        # Step 3 should fail (dependency not met)
        assert len(result.completed_steps) == 1
        assert len(result.failed_steps) == 1  # Step 3 fails


class TestStepMetadata:
    """Test step metadata in emitted actions."""

    @pytest.mark.asyncio
    async def test_action_contains_step_metadata(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test that emitted actions contain step metadata."""
        workflow_id = uuid4()

        result = await execute_workflow(
            simple_workflow_definition, simple_workflow_steps, workflow_id
        )

        for action in result.actions_emitted:
            # Check workflow ID in payload
            assert "workflow_id" in action.payload
            assert action.payload["workflow_id"] == str(workflow_id)

            # Check step ID in payload
            assert "step_id" in action.payload

            # Check step name in metadata
            assert "step_name" in action.metadata


class TestActionTypes:
    """Test correct action types for different step types."""

    @pytest.mark.asyncio
    async def test_step_type_to_action_type_mapping(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ):
        """Test that step types map to correct action types."""
        from omnibase_core.enums.enum_workflow_execution import EnumActionType

        steps = [
            ModelWorkflowStep(step_name="Effect Step", step_type="effect"),
            ModelWorkflowStep(step_name="Compute Step", step_type="compute"),
            ModelWorkflowStep(step_name="Reducer Step", step_type="reducer"),
        ]

        result = await execute_workflow(simple_workflow_definition, steps, uuid4())

        # Check action types
        action_types = [action.action_type for action in result.actions_emitted]
        assert EnumActionType.EFFECT in action_types
        assert EnumActionType.COMPUTE in action_types
        assert EnumActionType.REDUCE in action_types


class TestExecutionTimeTracking:
    """Test execution time tracking."""

    @pytest.mark.asyncio
    async def test_execution_time_recorded(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test that execution time is recorded."""
        result = await execute_workflow(
            simple_workflow_definition, simple_workflow_steps, uuid4()
        )

        # Execution time should be non-negative (can be 0 for very fast executions)
        assert result.execution_time_ms >= 0
        assert isinstance(result.execution_time_ms, int)


class TestMetadata:
    """Test workflow execution metadata."""

    @pytest.mark.asyncio
    async def test_sequential_metadata(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test metadata for sequential execution."""
        result = await execute_workflow(
            simple_workflow_definition,
            simple_workflow_steps,
            uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert "execution_mode" in result.metadata
        assert result.metadata["execution_mode"] == "sequential"

    @pytest.mark.asyncio
    async def test_parallel_metadata(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        parallel_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test metadata for parallel execution."""
        result = await execute_workflow(
            simple_workflow_definition,
            parallel_workflow_steps,
            uuid4(),
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        assert "execution_mode" in result.metadata
        assert result.metadata["execution_mode"] == "parallel"
