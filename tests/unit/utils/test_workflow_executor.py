"""
Unit tests for workflow execution utilities.

Tests the pure functions in utils/workflow_executor.py for workflow execution.
"""

from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
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


def _create_mock_workflow_step(
    step_id: UUID | None = None,
    step_name: str = "test_step",
    step_type: str = "compute",
    enabled: bool = True,
    depends_on: list[UUID] | None = None,
) -> ModelWorkflowStep:
    """Create a ModelWorkflowStep using model_construct to bypass Pydantic validation.

    This helper is used for tests that create many steps (1000+) where Pydantic
    validation overhead becomes significant. Uses model_construct() to skip
    validation while still creating proper ModelWorkflowStep instances.

    Args:
        step_id: Optional step ID (generates UUID if not provided)
        step_name: Human-readable name for the step
        step_type: Type of workflow step (compute, effect, etc.)
        enabled: Whether the step is enabled
        depends_on: List of step IDs this step depends on

    Returns:
        ModelWorkflowStep instance created without validation overhead
    """
    return ModelWorkflowStep.model_construct(
        correlation_id=uuid4(),
        step_id=step_id or uuid4(),
        step_name=step_name,
        step_type=step_type,
        timeout_ms=30000,
        retry_count=3,
        enabled=enabled,
        skip_on_failure=False,
        continue_on_error=False,
        error_action="stop",
        max_memory_mb=None,
        max_cpu_percent=None,
        priority=100,
        order_index=0,
        depends_on=depends_on if depends_on is not None else [],
        parallel_group=None,
        max_parallel_instances=1,
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


@pytest.mark.unit
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
            action.metadata.parameters["correlation_id"]: action
            for action in result.actions_emitted
        }

        # Check dependencies
        for step in simple_workflow_steps:
            step_correlation_id = str(step.correlation_id)
            if step_correlation_id in actions_by_step_id:
                action = actions_by_step_id[step_correlation_id]
                assert len(action.dependencies) == len(step.depends_on)


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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

            # Check step name in metadata parameters
            assert "step_name" in action.metadata.parameters


@pytest.mark.unit
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


@pytest.mark.unit
class TestExecuteStepErrorHandling:
    """Test error handling in parallel execution's execute_step function.

    The execute_step inner function in _execute_parallel returns errors
    in tuple format (step, None, exception) rather than propagating exceptions.
    This enables safe parallel execution where one failing step doesn't cancel
    sibling tasks.
    """

    @pytest.mark.asyncio
    async def test_execute_parallel_captures_step_errors(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify that execute_step returns errors in tuple format for parallel execution.

        When _create_action_for_step raises an exception, the step should:
        1. Not propagate the exception (no asyncio.gather failure)
        2. Appear in failed_steps list
        3. Not appear in completed_steps list
        4. Not emit an action for that step
        """
        from unittest.mock import patch

        # Create a simple step that we'll force to fail
        step_id = uuid4()
        steps = [
            ModelWorkflowStep(
                step_id=step_id,
                step_name="Failing Step",
                step_type="effect",
                enabled=True,
            ),
        ]

        # Mock _create_action_for_step to raise an exception
        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step"
        ) as mock_create_action:
            mock_create_action.side_effect = RuntimeError(
                "Simulated action creation failure"
            )

            result = await execute_workflow(
                simple_workflow_definition,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.PARALLEL,
            )

        # Verify the step failed but didn't crash the workflow
        assert str(step_id) in result.failed_steps
        assert str(step_id) not in result.completed_steps
        assert len(result.actions_emitted) == 0
        assert result.execution_status == EnumWorkflowState.FAILED

    @pytest.mark.asyncio
    async def test_execute_parallel_captures_onex_errors(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify that ModelOnexError is captured in tuple format with proper logging.

        ModelOnexError should be handled specially with error code extraction.
        """
        from unittest.mock import patch

        step_id = uuid4()
        steps = [
            ModelWorkflowStep(
                step_id=step_id,
                step_name="ONEX Error Step",
                step_type="compute",
                enabled=True,
            ),
        ]

        # Mock _create_action_for_step to raise a ModelOnexError
        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step"
        ) as mock_create_action:
            mock_create_action.side_effect = ModelOnexError(
                message="Simulated ONEX error",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={"test_key": "test_value"},
            )

            result = await execute_workflow(
                simple_workflow_definition,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.PARALLEL,
            )

        # Verify the step failed gracefully
        assert str(step_id) in result.failed_steps
        assert str(step_id) not in result.completed_steps
        assert len(result.actions_emitted) == 0
        assert result.execution_status == EnumWorkflowState.FAILED

    @pytest.mark.asyncio
    async def test_execute_parallel_mixed_success_and_failure(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify parallel execution handles mixed success/failure correctly.

        When some steps succeed and others fail in parallel:
        1. Successful steps should complete and emit actions
        2. Failed steps should be captured without crashing
        3. Overall status should be FAILED due to any failures
        """
        from unittest.mock import patch

        success_step_id = uuid4()
        fail_step_id = uuid4()

        # Two independent steps (no dependencies)
        steps = [
            ModelWorkflowStep(
                step_id=success_step_id,
                step_name="Success Step",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=fail_step_id,
                step_name="Fail Step",
                step_type="compute",
                enabled=True,
            ),
        ]

        # We need to capture the original function before patching
        from omnibase_core.utils import workflow_executor

        original_fn = workflow_executor._create_action_for_step

        def mock_fn(step, workflow_id):
            if step.step_id == fail_step_id:
                raise ValueError("Intentional failure for testing")
            return original_fn(step, workflow_id)

        with patch.object(
            workflow_executor, "_create_action_for_step", side_effect=mock_fn
        ):
            result = await execute_workflow(
                simple_workflow_definition,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.PARALLEL,
            )

        # Success step should complete
        assert str(success_step_id) in result.completed_steps
        # Fail step should be in failed_steps
        assert str(fail_step_id) in result.failed_steps
        # Should have one action (from success step)
        assert len(result.actions_emitted) == 1
        # Overall status is FAILED due to the failure
        assert result.execution_status == EnumWorkflowState.FAILED

    @pytest.mark.asyncio
    async def test_execute_parallel_error_with_stop_action(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify that error_action='stop' stops workflow after current wave.

        When a step fails with error_action='stop', the workflow should:
        1. Complete the current wave of parallel steps
        2. Not execute subsequent waves (remaining steps are NOT explicitly marked failed)
        3. The workflow terminates early with FAILED status
        """
        from unittest.mock import patch

        wave1_step_id = uuid4()
        wave2_step_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=wave1_step_id,
                step_name="Wave 1 - Fails with Stop",
                step_type="effect",
                enabled=True,
                error_action="stop",  # This should stop the workflow
            ),
            ModelWorkflowStep(
                step_id=wave2_step_id,
                step_name="Wave 2 - Should Not Run",
                step_type="compute",
                enabled=True,
                depends_on=[wave1_step_id],  # Depends on wave 1
            ),
        ]

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step"
        ) as mock_create_action:
            mock_create_action.side_effect = RuntimeError("Simulated failure with stop")

            result = await execute_workflow(
                simple_workflow_definition,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.PARALLEL,
            )

        # Wave 1 step should fail
        assert str(wave1_step_id) in result.failed_steps
        # Wave 2 step should NOT be in completed_steps (it was never executed)
        assert str(wave2_step_id) not in result.completed_steps
        # No actions should be emitted (wave 1 failed before action creation)
        assert len(result.actions_emitted) == 0
        # Overall status should be FAILED
        assert result.execution_status == EnumWorkflowState.FAILED
        # Verify fewer steps were processed than total (workflow stopped early)
        assert len(result.completed_steps) + len(result.failed_steps) < len(steps)


@pytest.mark.unit
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


@pytest.mark.unit
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
        assert result.metadata["execution_mode"].get_string() == "sequential"

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
        assert result.metadata["execution_mode"].get_string() == "parallel"

    @pytest.mark.asyncio
    async def test_workflow_hash_in_metadata(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test that workflow hash is included in result metadata for integrity verification."""
        from omnibase_core.utils.workflow_executor import _compute_workflow_hash

        result = await execute_workflow(
            simple_workflow_definition,
            simple_workflow_steps,
            uuid4(),
        )

        # Verify workflow_hash is present in metadata
        assert "workflow_hash" in result.metadata

        # Verify the hash is a valid SHA-256 hex string (64 characters)
        workflow_hash = result.metadata["workflow_hash"].get_string()
        assert isinstance(workflow_hash, str)
        assert len(workflow_hash) == 64
        assert all(c in "0123456789abcdef" for c in workflow_hash)

        # Verify the hash matches what we would compute from the workflow definition
        expected_hash = _compute_workflow_hash(simple_workflow_definition)
        assert workflow_hash == expected_hash

    @pytest.mark.asyncio
    async def test_workflow_hash_consistent_across_execution_modes(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
        simple_workflow_steps: list[ModelWorkflowStep],
    ):
        """Test that workflow hash is consistent regardless of execution mode."""
        from omnibase_core.utils.workflow_executor import _compute_workflow_hash

        # Execute with sequential mode
        result_sequential = await execute_workflow(
            simple_workflow_definition,
            simple_workflow_steps,
            uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Execute with parallel mode
        result_parallel = await execute_workflow(
            simple_workflow_definition,
            simple_workflow_steps,
            uuid4(),
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Both should have the same workflow hash (based on definition, not execution)
        assert (
            result_sequential.metadata["workflow_hash"].get_string()
            == result_parallel.metadata["workflow_hash"].get_string()
        )

        # And both should match the computed hash
        expected_hash = _compute_workflow_hash(simple_workflow_definition)
        assert result_sequential.metadata["workflow_hash"].get_string() == expected_hash


@pytest.mark.unit
class TestBuildWorkflowContext:
    """Tests for _build_workflow_context function."""

    def test_empty_completed_steps(self) -> None:
        """Test context with no completed steps."""
        from omnibase_core.utils.workflow_executor import _build_workflow_context

        workflow_id = uuid4()
        completed_step_ids: set[UUID] = set()
        step_outputs: dict[UUID, object] = {}

        context = _build_workflow_context(workflow_id, completed_step_ids, step_outputs)

        assert context["workflow_uuid_str"] == str(workflow_id)
        assert context["completed_steps"] == []
        assert context["step_outputs"] == {}
        assert context["step_count"] == 0

    def test_single_completed_step(self) -> None:
        """Test context with single completed step and output."""
        from omnibase_core.utils.workflow_executor import _build_workflow_context

        workflow_id = uuid4()
        step1_id = uuid4()
        completed_step_ids = {step1_id}
        step_outputs = {step1_id: {"data": [1, 2, 3]}}

        context = _build_workflow_context(workflow_id, completed_step_ids, step_outputs)

        assert context["workflow_uuid_str"] == str(workflow_id)
        assert str(step1_id) in context["completed_steps"]
        assert len(context["completed_steps"]) == 1
        assert context["step_outputs"][str(step1_id)] == {"data": [1, 2, 3]}
        assert context["step_count"] == 1

    def test_multiple_completed_steps(self) -> None:
        """Test context with multiple completed steps and outputs."""
        from omnibase_core.utils.workflow_executor import _build_workflow_context

        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()

        completed_step_ids = {step1_id, step2_id, step3_id}
        step_outputs: dict[UUID, object] = {
            step1_id: {"extracted": "value1"},
            step2_id: {"processed": True, "count": 42},
            step3_id: None,
        }

        context = _build_workflow_context(workflow_id, completed_step_ids, step_outputs)

        assert context["workflow_uuid_str"] == str(workflow_id)
        assert len(context["completed_steps"]) == 3
        assert str(step1_id) in context["completed_steps"]
        assert str(step2_id) in context["completed_steps"]
        assert str(step3_id) in context["completed_steps"]
        assert context["step_outputs"][str(step1_id)] == {"extracted": "value1"}
        assert context["step_outputs"][str(step2_id)] == {
            "processed": True,
            "count": 42,
        }
        assert context["step_outputs"][str(step3_id)] is None
        assert context["step_count"] == 3

    def test_step_outputs_without_all_completed_steps(self) -> None:
        """Test context handles partial outputs (not all steps have outputs)."""
        from omnibase_core.utils.workflow_executor import _build_workflow_context

        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()

        # Step 2 completed but has no output in step_outputs dict
        completed_step_ids = {step1_id, step2_id}
        step_outputs: dict[UUID, object] = {step1_id: {"result": "success"}}

        context = _build_workflow_context(workflow_id, completed_step_ids, step_outputs)

        assert context["step_count"] == 2
        assert len(context["completed_steps"]) == 2
        # Only step1 has output
        assert len(context["step_outputs"]) == 1
        assert str(step1_id) in context["step_outputs"]


@pytest.mark.unit
class TestValidateJsonPayload:
    """Tests for _validate_json_payload function."""

    def test_valid_payload_passes(self) -> None:
        """Test valid JSON payload does not raise."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        payload = {
            "workflow_id": str(uuid4()),
            "step_id": str(uuid4()),
            "step_name": "process_data",
            "count": 42,
            "enabled": True,
            "tags": ["a", "b", "c"],
            "nested": {"key": "value"},
        }

        # Should not raise
        _validate_json_payload(payload, context="test_step")

    def test_empty_payload_passes(self) -> None:
        """Test empty payload is valid."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        _validate_json_payload({}, context="empty_step")

    def test_invalid_lambda_raises_error(self) -> None:
        """Test lambda in payload raises ModelOnexError."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        invalid_payload: dict[str, object] = {"func": lambda x: x}

        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(invalid_payload, context="bad_step")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "not JSON-serializable" in exc_info.value.message
        assert "bad_step" in exc_info.value.message
        # Context is nested in additional_context due to ModelOnexError's **context pattern
        assert exc_info.value.context is not None
        additional_ctx = exc_info.value.context.get("additional_context", {})
        inner_ctx = additional_ctx.get("context", {})
        assert "func" in inner_ctx.get("payload_keys", [])
        assert inner_ctx.get("step_context") == "bad_step"

    def test_invalid_custom_object_raises_error(self) -> None:
        """Test non-serializable custom object raises ModelOnexError."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        class CustomClass:
            pass

        invalid_payload: dict[str, object] = {"obj": CustomClass()}

        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(invalid_payload, context="custom_obj_step")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "not JSON-serializable" in exc_info.value.message
        assert "custom_obj_step" in exc_info.value.message

    def test_error_message_without_context(self) -> None:
        """Test error message when no context is provided."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        invalid_payload: dict[str, object] = {"func": lambda x: x}

        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(invalid_payload, context="")

        # Should not include "for step" when context is empty
        assert "for step" not in exc_info.value.message
        assert "not JSON-serializable" in exc_info.value.message

    def test_nested_invalid_object_raises_error(self) -> None:
        """Test deeply nested non-serializable object is detected."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        invalid_payload: dict[str, object] = {
            "level1": {
                "level2": {
                    "level3": lambda x: x,
                }
            }
        }

        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(invalid_payload, context="nested_step")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_uuid_passes_in_permissive_mode(self) -> None:
        """Test UUID objects are accepted in default permissive mode (strict=False)."""
        from datetime import datetime

        from omnibase_core.utils.workflow_executor import _validate_json_payload

        payload: dict[str, object] = {
            "workflow_id": uuid4(),  # Raw UUID object
            "step_id": uuid4(),
            "step_name": "test_step",
        }

        # Should not raise - UUIDs serialized via default=str
        _validate_json_payload(payload, context="uuid_step")

    def test_datetime_passes_in_permissive_mode(self) -> None:
        """Test datetime objects are accepted in default permissive mode (strict=False)."""
        from datetime import datetime

        from omnibase_core.utils.workflow_executor import _validate_json_payload

        payload: dict[str, object] = {
            "created_at": datetime.now(),
            "step_name": "test_step",
        }

        # Should not raise - datetimes serialized via default=str
        _validate_json_payload(payload, context="datetime_step")

    def test_uuid_fails_in_strict_mode(self) -> None:
        """Test UUID objects are rejected in strict mode."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        payload: dict[str, object] = {
            "workflow_id": uuid4(),  # Raw UUID - not allowed in strict mode
        }

        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(payload, context="strict_uuid", strict=True)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "not JSON-serializable" in exc_info.value.message

    def test_datetime_fails_in_strict_mode(self) -> None:
        """Test datetime objects are rejected in strict mode."""
        from datetime import datetime

        from omnibase_core.utils.workflow_executor import _validate_json_payload

        payload: dict[str, object] = {
            "created_at": datetime.now(),
        }

        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(payload, context="strict_datetime", strict=True)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "not JSON-serializable" in exc_info.value.message

    def test_lambda_fails_even_in_permissive_mode(self) -> None:
        """Test lambda still fails in permissive mode (default=str doesn't help)."""
        from omnibase_core.utils.workflow_executor import _validate_json_payload

        invalid_payload: dict[str, object] = {"func": lambda x: x}

        # Lambda should fail even with strict=False because json.dumps
        # tries to call str() on it, which doesn't produce valid JSON
        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(invalid_payload, context="lambda_step", strict=False)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.unit
class TestVerifyWorkflowIntegrity:
    """Tests for verify_workflow_integrity function."""

    def test_none_hash_skips_verification(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that None expected_hash skips verification."""
        from omnibase_core.utils.workflow_executor import verify_workflow_integrity

        # Should not raise - verification is skipped
        verify_workflow_integrity(simple_workflow_definition, expected_hash=None)

    def test_matching_hash_passes(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that matching hash passes verification."""
        from omnibase_core.utils.workflow_executor import (
            _compute_workflow_hash,
            verify_workflow_integrity,
        )

        # Compute the actual hash first
        actual_hash = _compute_workflow_hash(simple_workflow_definition)

        # Should not raise - hashes match
        verify_workflow_integrity(simple_workflow_definition, expected_hash=actual_hash)

    def test_mismatched_hash_raises_error(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that mismatched hash raises ModelOnexError with proper context."""
        from omnibase_core.utils.workflow_executor import verify_workflow_integrity

        wrong_hash = "invalid_hash_that_does_not_match"

        with pytest.raises(ModelOnexError) as exc_info:
            verify_workflow_integrity(
                simple_workflow_definition, expected_hash=wrong_hash
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "hash mismatch" in exc_info.value.message.lower()
        # Context is nested: additional_context -> context -> {expected_hash, actual_hash, ...}
        # due to ModelOnexError's **context pattern
        assert exc_info.value.context is not None
        additional_ctx = exc_info.value.context.get("additional_context", {})
        inner_ctx = additional_ctx.get("context", {})
        assert inner_ctx.get("expected_hash") == wrong_hash
        assert "actual_hash" in inner_ctx
        assert (
            inner_ctx.get("workflow_name")
            == simple_workflow_definition.workflow_metadata.workflow_name
        )


@pytest.mark.unit
class TestComputeWorkflowHash:
    """Tests for _compute_workflow_hash function."""

    def test_hash_is_deterministic(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that hash computation is deterministic."""
        from omnibase_core.utils.workflow_executor import _compute_workflow_hash

        hash1 = _compute_workflow_hash(simple_workflow_definition)
        hash2 = _compute_workflow_hash(simple_workflow_definition)

        assert hash1 == hash2

    def test_hash_is_sha256_format(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that hash is a valid SHA-256 hex string."""
        from omnibase_core.utils.workflow_executor import _compute_workflow_hash

        hash_value = _compute_workflow_hash(simple_workflow_definition)

        # SHA-256 produces 64 hex characters
        assert len(hash_value) == 64
        # Should only contain hex characters
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_different_definitions_produce_different_hashes(
        self, simple_workflow_definition: ModelWorkflowDefinition
    ) -> None:
        """Test that different workflow definitions produce different hashes."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.utils.workflow_executor import _compute_workflow_hash

        hash1 = _compute_workflow_hash(simple_workflow_definition)

        # Create a different workflow definition
        different_definition = ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="different_workflow",  # Different name
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Different workflow description",
                execution_mode="parallel",  # Different mode
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

        hash2 = _compute_workflow_hash(different_definition)

        assert hash1 != hash2


@pytest.mark.unit
class TestPriorityOrderingIntegration:
    """Integration tests for priority ordering in real workflow execution.

    These tests verify that priority ordering works end-to-end through actual
    workflow execution, not just the internal _get_topological_order function.
    """

    @pytest.mark.asyncio
    async def test_sequential_workflow_respects_priority_ordering(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify sequential workflow execution emits actions in priority order.

        When executing a sequential workflow with independent steps (no dependencies),
        higher priority steps (lower priority value) should be executed first,
        and their actions should be emitted in priority order.
        """
        workflow_id = uuid4()

        # Create independent steps with different priorities
        low_priority_id = uuid4()
        medium_priority_id = uuid4()
        high_priority_id = uuid4()

        # Declare in reverse priority order to ensure sorting is actually applied
        steps = [
            ModelWorkflowStep(
                step_id=low_priority_id,
                step_name="Low Priority Step",
                step_type="effect",
                priority=10,  # Lowest importance (highest number)
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=medium_priority_id,
                step_name="Medium Priority Step",
                step_type="compute",
                priority=5,
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=high_priority_id,
                step_name="High Priority Step",
                step_type="reducer",
                priority=1,  # Highest importance (lowest number)
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 3
        assert len(result.actions_emitted) == 3

        # Extract step IDs from actions in emission order
        emitted_step_ids = [
            UUID(action.payload["step_id"]) for action in result.actions_emitted
        ]

        # Verify priority order: high (1), medium (5), low (10)
        assert emitted_step_ids[0] == high_priority_id, (
            f"Expected high priority step first, got {emitted_step_ids[0]}"
        )
        assert emitted_step_ids[1] == medium_priority_id, (
            f"Expected medium priority step second, got {emitted_step_ids[1]}"
        )
        assert emitted_step_ids[2] == low_priority_id, (
            f"Expected low priority step third, got {emitted_step_ids[2]}"
        )

        # Also verify action priorities are set correctly
        assert result.actions_emitted[0].priority == 1
        assert result.actions_emitted[1].priority == 5
        assert result.actions_emitted[2].priority == 10

    @pytest.mark.asyncio
    async def test_parallel_workflow_respects_priority_in_wave(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify parallel workflow execution respects priority within a wave.

        In parallel execution, steps are grouped into "waves" based on dependencies.
        Within a single wave (all steps have their dependencies met), the actions
        should be processed/emitted in priority order, with higher priority steps
        (lower priority value) coming first.
        """
        workflow_id = uuid4()

        # Create a workflow with one parent step and multiple child steps
        # All children depend on parent, so they form a single wave after parent
        parent_id = uuid4()
        low_priority_child_id = uuid4()
        medium_priority_child_id = uuid4()
        high_priority_child_id = uuid4()

        steps = [
            # Parent step - executed first
            ModelWorkflowStep(
                step_id=parent_id,
                step_name="Parent Step",
                step_type="effect",
                priority=1,
                enabled=True,
            ),
            # Children declared in reverse priority order
            ModelWorkflowStep(
                step_id=low_priority_child_id,
                step_name="Low Priority Child",
                step_type="compute",
                priority=10,  # Lowest importance
                depends_on=[parent_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=medium_priority_child_id,
                step_name="Medium Priority Child",
                step_type="compute",
                priority=5,
                depends_on=[parent_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=high_priority_child_id,
                step_name="High Priority Child",
                step_type="reducer",
                priority=1,  # Highest importance
                depends_on=[parent_id],
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 4
        assert len(result.actions_emitted) == 4

        # Extract step IDs from actions in emission order
        emitted_step_ids = [
            UUID(action.payload["step_id"]) for action in result.actions_emitted
        ]

        # First action should be parent (wave 1)
        assert emitted_step_ids[0] == parent_id, (
            f"Expected parent step first, got {emitted_step_ids[0]}"
        )

        # Remaining actions are wave 2 (all children depend on parent)
        # Within wave 2, they should be in priority order
        wave2_actions = result.actions_emitted[1:]

        # Verify action priorities are set correctly for the wave
        action_priorities = [
            (a.priority, UUID(a.payload["step_id"])) for a in wave2_actions
        ]

        # Group by step ID for verification
        priority_by_step = {
            step_id: priority for priority, step_id in action_priorities
        }
        assert priority_by_step[high_priority_child_id] == 1
        assert priority_by_step[medium_priority_child_id] == 5
        assert priority_by_step[low_priority_child_id] == 10

    @pytest.mark.asyncio
    async def test_sequential_workflow_priority_with_dependencies(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify dependencies take precedence over priority in sequential execution.

        When steps have dependencies, the topological order is respected first,
        then priority is used to order steps at the same dependency level.
        """
        workflow_id = uuid4()

        # Create a diamond dependency pattern:
        #       A (low priority)
        #      / \
        #     B   C (B high priority, C low priority)
        #      \ /
        #       D (depends on both B and C)
        step_a_id = uuid4()
        step_b_id = uuid4()  # High priority
        step_c_id = uuid4()  # Low priority
        step_d_id = uuid4()

        steps = [
            # Declare in non-priority order
            ModelWorkflowStep(
                step_id=step_c_id,
                step_name="Step C (Low Priority)",
                step_type="compute",
                priority=10,
                depends_on=[step_a_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="Step A (Root)",
                step_type="effect",
                priority=5,
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_d_id,
                step_name="Step D (Final)",
                step_type="reducer",
                priority=1,
                depends_on=[step_b_id, step_c_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="Step B (High Priority)",
                step_type="compute",
                priority=1,  # Highest priority at level 2
                depends_on=[step_a_id],
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 4
        assert len(result.actions_emitted) == 4

        # Extract step IDs from actions in emission order
        emitted_step_ids = [
            UUID(action.payload["step_id"]) for action in result.actions_emitted
        ]

        # Step A must be first (no dependencies)
        assert emitted_step_ids[0] == step_a_id, "Step A (root) must execute first"

        # Step D must be last (depends on B and C)
        assert emitted_step_ids[3] == step_d_id, "Step D (final) must execute last"

        # Steps B and C can be in either order based on priority
        # B has priority 1, C has priority 10, so B should come before C
        b_index = emitted_step_ids.index(step_b_id)
        c_index = emitted_step_ids.index(step_c_id)
        assert b_index < c_index, (
            f"Step B (priority 1) should execute before Step C (priority 10). "
            f"B index: {b_index}, C index: {c_index}"
        )

    @pytest.mark.asyncio
    async def test_sequential_workflow_action_priority_values(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify emitted actions have correct priority values from steps.

        The ModelAction priority is clamped to 1-10 range from ModelWorkflowStep's
        1-1000 range. This test verifies the clamping behavior in end-to-end execution.
        """
        workflow_id = uuid4()

        # Create steps with priorities spanning the full range
        step_normal_id = uuid4()
        step_over_10_id = uuid4()
        step_way_over_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_normal_id,
                step_name="Normal Priority",
                step_type="effect",
                priority=5,  # Within 1-10 range
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_over_10_id,
                step_name="Priority Over 10",
                step_type="compute",
                priority=50,  # Should be clamped to 10
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_way_over_id,
                step_name="Priority Way Over",
                step_type="reducer",
                priority=500,  # Should be clamped to 10
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.actions_emitted) == 3

        # Map actions by step ID
        actions_by_step_id = {
            UUID(a.payload["step_id"]): a for a in result.actions_emitted
        }

        # Verify priority values on emitted actions
        assert actions_by_step_id[step_normal_id].priority == 5, (
            "Normal priority should remain unchanged"
        )
        assert actions_by_step_id[step_over_10_id].priority == 10, (
            "Priority 50 should be clamped to 10"
        )
        assert actions_by_step_id[step_way_over_id].priority == 10, (
            "Priority 500 should be clamped to 10"
        )


@pytest.mark.unit
class TestPriorityOrdering:
    """Tests for priority-aware topological ordering in _get_topological_order."""

    def test_equal_priority_ordered_by_declaration_order(self) -> None:
        """Test steps with equal priority are ordered by declaration order."""
        from omnibase_core.utils.workflow_executor import _get_topological_order

        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()

        # All steps have same priority (default 1) and no dependencies
        # Should be ordered by declaration order: step1, step2, step3
        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="Step 1",
                step_type="effect",
                priority=5,  # Same priority
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Step 2",
                step_type="compute",
                priority=5,  # Same priority
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="Step 3",
                step_type="reducer",
                priority=5,  # Same priority
            ),
        ]

        order = _get_topological_order(steps)

        # All at same priority, so declaration order should be preserved
        assert order[0] == step1_id
        assert order[1] == step2_id
        assert order[2] == step3_id

    def test_different_priorities_ordered_by_priority(self) -> None:
        """Test steps with different priorities are ordered by priority (lower first)."""
        from omnibase_core.utils.workflow_executor import _get_topological_order

        low_priority_id = uuid4()
        medium_priority_id = uuid4()
        high_priority_id = uuid4()

        # Different priorities, no dependencies
        # Lower priority value = higher importance, should be first
        steps = [
            ModelWorkflowStep(
                step_id=low_priority_id,
                step_name="Low Priority",
                step_type="effect",
                priority=10,  # Lowest importance (highest number)
            ),
            ModelWorkflowStep(
                step_id=medium_priority_id,
                step_name="Medium Priority",
                step_type="compute",
                priority=5,
            ),
            ModelWorkflowStep(
                step_id=high_priority_id,
                step_name="High Priority",
                step_type="reducer",
                priority=1,  # Highest importance (lowest number)
            ),
        ]

        order = _get_topological_order(steps)

        # Should be ordered: high (1), medium (5), low (10)
        assert order[0] == high_priority_id
        assert order[1] == medium_priority_id
        assert order[2] == low_priority_id

    def test_priority_clamped_to_10(self) -> None:
        """Test that priority values over 10 are clamped to 10."""
        from omnibase_core.utils.workflow_executor import _get_topological_order

        step1_id = uuid4()
        step2_id = uuid4()

        # Both have priority > 10, should be clamped to 10
        # Then ordered by declaration order
        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="Step 1",
                step_type="effect",
                priority=100,  # Clamped to 10
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Step 2",
                step_type="compute",
                priority=1000,  # Also clamped to 10
            ),
        ]

        order = _get_topological_order(steps)

        # Both clamped to 10, so declaration order: step1, step2
        assert order[0] == step1_id
        assert order[1] == step2_id

    def test_priority_with_dependencies(self) -> None:
        """Test that dependencies take precedence over priority."""
        from omnibase_core.utils.workflow_executor import _get_topological_order

        first_step_id = uuid4()
        second_step_id = uuid4()

        # second_step has higher priority but depends on first_step
        # first_step must come first regardless of priority
        steps = [
            ModelWorkflowStep(
                step_id=second_step_id,
                step_name="Second (High Priority)",
                step_type="compute",
                priority=1,  # Highest priority
                depends_on=[first_step_id],  # But depends on first
            ),
            ModelWorkflowStep(
                step_id=first_step_id,
                step_name="First (Low Priority)",
                step_type="effect",
                priority=10,  # Lower priority
            ),
        ]

        order = _get_topological_order(steps)

        # first_step must come before second_step due to dependency
        assert order.index(first_step_id) < order.index(second_step_id)

    def test_priority_ordering_among_independent_steps_with_shared_dependency(
        self,
    ) -> None:
        """Test priority ordering for independent steps that share a dependency."""
        from omnibase_core.utils.workflow_executor import _get_topological_order

        parent_id = uuid4()
        high_priority_child_id = uuid4()
        low_priority_child_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=parent_id,
                step_name="Parent",
                step_type="effect",
                priority=1,
            ),
            ModelWorkflowStep(
                step_id=low_priority_child_id,
                step_name="Low Priority Child",
                step_type="compute",
                priority=10,
                depends_on=[parent_id],
            ),
            ModelWorkflowStep(
                step_id=high_priority_child_id,
                step_name="High Priority Child",
                step_type="reducer",
                priority=1,
                depends_on=[parent_id],
            ),
        ]

        order = _get_topological_order(steps)

        # Parent first (due to dependency)
        assert order[0] == parent_id
        # High priority child (1) before low priority child (10)
        assert order.index(high_priority_child_id) < order.index(low_priority_child_id)

    def test_default_priority_uses_model_default(self) -> None:
        """Test that default priority (100) is clamped to 10 in topological order."""
        from omnibase_core.utils.workflow_executor import _get_topological_order

        default_priority_id = uuid4()
        high_priority_id = uuid4()

        # Create steps where one uses default priority (100) and another has explicit high priority (1)
        # Default priority (100) should be clamped to 10
        steps = [
            ModelWorkflowStep(
                step_id=default_priority_id,
                step_name="Default Priority Step",
                step_type="compute",
                # priority defaults to 100, clamped to 10
            ),
            ModelWorkflowStep(
                step_id=high_priority_id,
                step_name="High Priority Step",
                step_type="effect",
                priority=1,  # Highest priority
            ),
        ]

        order = _get_topological_order(steps)

        # High priority (1) should come before default priority (100 clamped to 10)
        assert order.index(high_priority_id) < order.index(default_priority_id)

    def test_default_priority_in_create_action_for_step(self) -> None:
        """Test that _create_action_for_step clamps default priority (100) to 10."""
        from omnibase_core.utils.workflow_executor import _create_action_for_step

        step = ModelWorkflowStep(
            step_name="Test Step",
            step_type="effect",
            # priority defaults to 100
        )

        action, payload_size = _create_action_for_step(step, uuid4())

        # Default priority (100) should be clamped to 10
        assert action.priority == 10
        # Payload size should be returned and be positive
        assert payload_size > 0

    def test_priority_none_handling_in_topological_order(self) -> None:
        """Test that _get_topological_order handles None priority defensively.

        Note: ModelWorkflowStep currently defines priority as int with default=100,
        so None is not valid input. However, the code defensively handles None
        to guard against future model changes.
        """
        from unittest.mock import MagicMock

        from omnibase_core.utils.workflow_executor import _get_topological_order

        # Create mock steps with None priority to test defensive handling
        step1_id = uuid4()
        step2_id = uuid4()

        mock_step1 = MagicMock(spec=ModelWorkflowStep)
        mock_step1.step_id = step1_id
        mock_step1.priority = None  # Simulating None priority
        mock_step1.depends_on = []

        mock_step2 = MagicMock(spec=ModelWorkflowStep)
        mock_step2.step_id = step2_id
        mock_step2.priority = 10  # Explicit priority
        mock_step2.depends_on = []

        # Should not raise TypeError when priority is None
        order = _get_topological_order([mock_step1, mock_step2])

        # Step with None priority (defaults to 1) should come before step with priority 10
        assert order.index(step1_id) < order.index(step2_id)

    def test_priority_none_handling_in_create_action(self) -> None:
        """Test that _create_action_for_step handles None priority defensively.

        Note: ModelWorkflowStep currently defines priority as int with default=100,
        so None is not valid input. However, the code defensively handles None
        to guard against future model changes.
        """
        from unittest.mock import MagicMock

        from omnibase_core.utils.workflow_executor import _create_action_for_step

        # Create mock step with None priority to test defensive handling
        mock_step = MagicMock(spec=ModelWorkflowStep)
        mock_step.step_id = uuid4()
        mock_step.step_name = "Mock Step"
        mock_step.step_type = "effect"
        mock_step.priority = None  # Simulating None priority
        mock_step.depends_on = []
        mock_step.timeout_ms = 5000
        mock_step.retry_count = 0
        mock_step.correlation_id = uuid4()

        # Should not raise TypeError when priority is None
        action, payload_size = _create_action_for_step(mock_step, uuid4())

        # None priority should default to 1
        assert action.priority == 1
        # Payload size should be returned and be positive
        assert payload_size > 0


@pytest.mark.unit
class TestWorkflowContextIntegration:
    """Tests for workflow context integration in execution flow."""

    @pytest.mark.asyncio
    async def test_sequential_execution_builds_context_with_step_outputs(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify sequential execution tracks step outputs for context building.

        The workflow executor should:
        1. Build workflow context for each step from prior outputs
        2. Store action payloads as step outputs after completion
        3. Make prior outputs available to subsequent steps
        """
        workflow_id = uuid4()
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
                depends_on=[step1_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="Step 3",
                step_type="reducer",
                depends_on=[step2_id],
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 3

        # Verify each action's payload contains expected data
        for action in result.actions_emitted:
            assert "workflow_id" in action.payload
            assert action.payload["workflow_id"] == str(workflow_id)
            assert "step_id" in action.payload
            assert "step_name" in action.payload

    @pytest.mark.asyncio
    async def test_parallel_execution_builds_context_per_wave(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify parallel execution builds context at wave boundaries.

        In parallel execution:
        1. Steps in the same wave execute simultaneously
        2. Context is built once per wave from prior wave outputs
        3. Steps in subsequent waves can access prior wave outputs
        """
        workflow_id = uuid4()

        # Create a workflow with clear wave structure:
        # Wave 1: step_a, step_b (no dependencies)
        # Wave 2: step_c, step_d (depend on wave 1)
        # Wave 3: step_e (depends on wave 2)
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()
        step_d_id = uuid4()
        step_e_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="Wave 1 - A",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="Wave 1 - B",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_c_id,
                step_name="Wave 2 - C",
                step_type="compute",
                depends_on=[step_a_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_d_id,
                step_name="Wave 2 - D",
                step_type="compute",
                depends_on=[step_b_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_e_id,
                step_name="Wave 3 - E",
                step_type="reducer",
                depends_on=[step_c_id, step_d_id],
                enabled=True,
            ),
        ]

        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 5
        assert len(result.actions_emitted) == 5

        # Verify step_e (wave 3) completed after its dependencies
        completed_step_ids = [UUID(s) for s in result.completed_steps]
        step_e_index = completed_step_ids.index(step_e_id)
        step_c_index = completed_step_ids.index(step_c_id)
        step_d_index = completed_step_ids.index(step_d_id)

        # step_e should appear after both step_c and step_d
        assert step_e_index > step_c_index
        assert step_e_index > step_d_index

    @pytest.mark.asyncio
    async def test_step_context_receives_workflow_context(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify ModelDeclarativeWorkflowStepContext receives workflow_context.

        The step context should have access to the workflow context with
        prior step outputs, enabling data flow between steps.
        """
        from omnibase_core.models.workflow.execution.model_declarative_workflow_step_context import (
            ModelDeclarativeWorkflowStepContext,
        )
        from omnibase_core.types.typed_dict_workflow_context import (
            TypedDictWorkflowContext,
        )

        workflow_id = uuid4()
        step_id = uuid4()
        prior_step_id = uuid4()

        step = ModelWorkflowStep(
            step_id=step_id,
            step_name="Test Step",
            step_type="compute",
            enabled=True,
        )

        completed_steps = {prior_step_id}
        workflow_context = TypedDictWorkflowContext(
            workflow_uuid_str=str(workflow_id),
            completed_steps=[str(prior_step_id)],
            step_outputs={str(prior_step_id): {"data": [1, 2, 3]}},
            step_count=1,
        )

        # Create step context with workflow context
        context = ModelDeclarativeWorkflowStepContext(
            step=step,
            workflow_id=workflow_id,
            completed_steps=completed_steps,
            workflow_context=workflow_context,
        )

        # Verify workflow context is accessible
        assert context.workflow_context is not None
        assert context.workflow_context["workflow_uuid_str"] == str(workflow_id)
        assert len(context.workflow_context["completed_steps"]) == 1
        assert context.workflow_context["step_outputs"][str(prior_step_id)] == {
            "data": [1, 2, 3]
        }

    @pytest.mark.asyncio
    async def test_step_context_without_workflow_context(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify ModelDeclarativeWorkflowStepContext works without workflow_context.

        For backward compatibility, workflow_context should be optional.
        """
        from omnibase_core.models.workflow.execution.model_declarative_workflow_step_context import (
            ModelDeclarativeWorkflowStepContext,
        )

        workflow_id = uuid4()
        step_id = uuid4()

        step = ModelWorkflowStep(
            step_id=step_id,
            step_name="Test Step",
            step_type="compute",
            enabled=True,
        )

        # Create step context without workflow context (backward compatible)
        context = ModelDeclarativeWorkflowStepContext(
            step=step,
            workflow_id=workflow_id,
            completed_steps=set(),
        )

        # Verify workflow context is None
        assert context.workflow_context is None
        assert context.step == step
        assert context.workflow_id == workflow_id


@pytest.mark.performance
@pytest.mark.unit
class TestWorkflowExecutorPerformance:
    """Performance tests for workflow executor with large workflows.

    These tests validate that the workflow executor can handle large workflows
    (100+ steps) efficiently and within reasonable time bounds.

    Test Patterns:
        - Linear chain: A -> B -> C -> ... (sequential dependencies)
        - Wide parallel: All steps independent (maximum parallelism)
        - Mixed: Combination of sequential and parallel dependencies
        - Diamond: A -> [B,C,D] -> E (fan-out, fan-in pattern)
    """

    def _create_large_workflow_steps(
        self,
        num_steps: int,
        pattern: str = "mixed",
    ) -> list[ModelWorkflowStep]:
        """Create a large workflow for performance testing.

        Args:
            num_steps: Number of steps to create
            pattern: Dependency pattern - "linear" (chain), "parallel" (no deps),
                     "mixed" (combination), "diamond" (fan-out/fan-in)

        Returns:
            List of ModelWorkflowStep with the specified dependency pattern
        """
        steps: list[ModelWorkflowStep] = []
        step_ids: list[UUID] = [uuid4() for _ in range(num_steps)]

        if pattern == "linear":
            # Linear chain: each step depends on the previous
            for i, step_id in enumerate(step_ids):
                depends_on = [step_ids[i - 1]] if i > 0 else []
                steps.append(
                    ModelWorkflowStep(
                        step_id=step_id,
                        step_name=f"Step {i}",
                        step_type="compute" if i % 2 == 0 else "effect",
                        depends_on=depends_on,
                        enabled=True,
                    )
                )

        elif pattern == "parallel":
            # All steps independent - maximum parallelism
            for i, step_id in enumerate(step_ids):
                steps.append(
                    ModelWorkflowStep(
                        step_id=step_id,
                        step_name=f"Step {i}",
                        step_type="compute" if i % 2 == 0 else "effect",
                        depends_on=[],
                        enabled=True,
                    )
                )

        elif pattern == "diamond":
            # Diamond pattern: root -> fan-out -> fan-in -> tail
            # Structure: root -> [wave1 steps] -> [wave2 steps] -> ... -> final
            if num_steps < 4:
                # Fall back to linear for very small workflows
                return self._create_large_workflow_steps(num_steps, "linear")

            # First step is root (no dependencies)
            root_id = step_ids[0]
            steps.append(
                ModelWorkflowStep(
                    step_id=root_id,
                    step_name="Root",
                    step_type="effect",
                    depends_on=[],
                    enabled=True,
                )
            )

            # Calculate wave sizes (fan-out, middle, fan-in)
            middle_count = num_steps - 2  # Exclude root and final
            wave_size = max(1, middle_count // 3)

            # Fan-out wave: depends on root
            fan_out_ids: list[UUID] = []
            for i in range(1, min(1 + wave_size, num_steps - 1)):
                step_id = step_ids[i]
                fan_out_ids.append(step_id)
                steps.append(
                    ModelWorkflowStep(
                        step_id=step_id,
                        step_name=f"FanOut {i}",
                        step_type="compute",
                        depends_on=[root_id],
                        enabled=True,
                    )
                )

            # Middle waves: depends on fan-out
            middle_ids: list[UUID] = []
            current_deps = fan_out_ids if fan_out_ids else [root_id]
            for i in range(1 + wave_size, num_steps - 1 - wave_size):
                step_id = step_ids[i]
                middle_ids.append(step_id)
                # Each middle step depends on one step from previous wave
                dep_idx = (i - 1 - wave_size) % len(current_deps)
                steps.append(
                    ModelWorkflowStep(
                        step_id=step_id,
                        step_name=f"Middle {i}",
                        step_type="reducer",
                        depends_on=[current_deps[dep_idx]],
                        enabled=True,
                    )
                )
            if middle_ids:
                current_deps = middle_ids

            # Fan-in wave: depends on middle/fan-out steps
            fan_in_ids: list[UUID] = []
            for i in range(num_steps - 1 - wave_size, num_steps - 1):
                if i <= 0:
                    continue
                step_id = step_ids[i]
                fan_in_ids.append(step_id)
                # Fan-in depends on subset of current_deps
                dep_count = min(3, len(current_deps))
                deps = current_deps[:dep_count]
                steps.append(
                    ModelWorkflowStep(
                        step_id=step_id,
                        step_name=f"FanIn {i}",
                        step_type="compute",
                        depends_on=deps,
                        enabled=True,
                    )
                )

            # Final step: depends on all fan-in steps
            final_id = step_ids[-1]
            final_deps = fan_in_ids if fan_in_ids else current_deps
            steps.append(
                ModelWorkflowStep(
                    step_id=final_id,
                    step_name="Final",
                    step_type="effect",
                    depends_on=final_deps,
                    enabled=True,
                )
            )

        else:  # "mixed" pattern
            # Mixed pattern: alternating sequential chains and parallel groups
            # Structure: [parallel group] -> [sequential chain] -> [parallel group] -> ...
            group_size = max(1, num_steps // 10)  # 10 groups

            current_group_deps: list[UUID] = []
            i = 0

            while i < num_steps:
                # Parallel group: all depend on previous group's last step(s)
                parallel_end = min(i + group_size, num_steps)
                parallel_ids: list[UUID] = []

                for j in range(i, parallel_end):
                    step_id = step_ids[j]
                    parallel_ids.append(step_id)
                    # Each parallel step depends on ALL previous group deps
                    steps.append(
                        ModelWorkflowStep(
                            step_id=step_id,
                            step_name=f"Parallel {j}",
                            step_type="compute",
                            depends_on=current_group_deps.copy(),
                            enabled=True,
                        )
                    )

                i = parallel_end

                # Sequential chain: linear dependencies
                if i < num_steps:
                    chain_end = min(i + group_size, num_steps)
                    prev_id = parallel_ids[-1] if parallel_ids else None
                    chain_ids: list[UUID] = []

                    for j in range(i, chain_end):
                        step_id = step_ids[j]
                        chain_ids.append(step_id)
                        deps = [prev_id] if prev_id else parallel_ids
                        steps.append(
                            ModelWorkflowStep(
                                step_id=step_id,
                                step_name=f"Chain {j}",
                                step_type="effect",
                                depends_on=deps,
                                enabled=True,
                            )
                        )
                        prev_id = step_id

                    i = chain_end
                    # Next parallel group depends on end of chain
                    current_group_deps = [chain_ids[-1]] if chain_ids else parallel_ids
                else:
                    current_group_deps = parallel_ids

        return steps

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sequential_execution_100_steps(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test sequential execution handles 100 steps efficiently.

        Performance target: <5 seconds for 100 sequential steps.
        This validates that sequential overhead per step is minimal.
        """
        import time

        workflow_id = uuid4()
        steps = self._create_large_workflow_steps(100, pattern="linear")

        start_time = time.perf_counter()
        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        elapsed_time = time.perf_counter() - start_time

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 100
        assert len(result.actions_emitted) == 100
        assert len(result.failed_steps) == 0

        # Performance assertion: should complete in under 5 seconds
        # This is generous to account for CI variability
        assert elapsed_time < 5.0, (
            f"Sequential execution of 100 steps took {elapsed_time:.2f}s, "
            f"expected <5.0s"
        )

        # Verify execution time is recorded
        assert result.execution_time_ms > 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_parallel_execution_100_steps(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test parallel execution handles 100 independent steps efficiently.

        Performance target: <3 seconds for 100 parallel steps.
        Parallel execution of independent steps should be faster than sequential.
        """
        import time

        workflow_id = uuid4()
        steps = self._create_large_workflow_steps(100, pattern="parallel")

        start_time = time.perf_counter()
        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )
        elapsed_time = time.perf_counter() - start_time

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 100
        assert len(result.actions_emitted) == 100
        assert len(result.failed_steps) == 0

        # Performance assertion: parallel should be fast
        # All steps execute in a single wave
        assert elapsed_time < 3.0, (
            f"Parallel execution of 100 steps took {elapsed_time:.2f}s, expected <3.0s"
        )

        # Verify metadata indicates parallel execution
        assert result.metadata["execution_mode"].get_string() == "parallel"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mixed_workflow_100_steps(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test mixed dependency patterns with 100 steps.

        Performance target: <5 seconds for 100 mixed-dependency steps.
        Mixed patterns should handle both sequential chains and parallel groups.
        """
        import time

        workflow_id = uuid4()
        steps = self._create_large_workflow_steps(100, pattern="mixed")

        start_time = time.perf_counter()
        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )
        elapsed_time = time.perf_counter() - start_time

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 100
        assert len(result.actions_emitted) == 100
        assert len(result.failed_steps) == 0

        # Performance assertion
        assert elapsed_time < 5.0, (
            f"Mixed execution of 100 steps took {elapsed_time:.2f}s, expected <5.0s"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_diamond_workflow_100_steps(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test diamond (fan-out/fan-in) pattern with 100 steps.

        Performance target: <5 seconds for 100 diamond-pattern steps.
        Diamond patterns test the executor's ability to handle
        complex dependency graphs with multiple convergence points.
        """
        import time

        workflow_id = uuid4()
        steps = self._create_large_workflow_steps(100, pattern="diamond")

        start_time = time.perf_counter()
        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )
        elapsed_time = time.perf_counter() - start_time

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 100
        assert len(result.actions_emitted) == 100
        assert len(result.failed_steps) == 0

        # Performance assertion
        assert elapsed_time < 5.0, (
            f"Diamond execution of 100 steps took {elapsed_time:.2f}s, expected <5.0s"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_workflow_200_steps_sequential(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test sequential execution scales to 200 steps.

        Performance target: <10 seconds for 200 sequential steps.
        This tests linear scaling behavior.
        """
        import time

        workflow_id = uuid4()
        steps = self._create_large_workflow_steps(200, pattern="linear")

        start_time = time.perf_counter()
        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        elapsed_time = time.perf_counter() - start_time

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 200
        assert len(result.actions_emitted) == 200

        # Performance assertion: should scale linearly
        assert elapsed_time < 10.0, (
            f"Sequential execution of 200 steps took {elapsed_time:.2f}s, "
            f"expected <10.0s"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_workflow_200_steps_parallel(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test parallel execution scales to 200 independent steps.

        Performance target: <5 seconds for 200 parallel steps.
        Parallel execution should scale sub-linearly with more steps.
        """
        import time

        workflow_id = uuid4()
        steps = self._create_large_workflow_steps(200, pattern="parallel")

        start_time = time.perf_counter()
        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )
        elapsed_time = time.perf_counter() - start_time

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 200
        assert len(result.actions_emitted) == 200

        # Performance assertion: parallel should remain fast
        assert elapsed_time < 5.0, (
            f"Parallel execution of 200 steps took {elapsed_time:.2f}s, expected <5.0s"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_topological_sort_performance_100_steps(self) -> None:
        """Test that topological sorting is efficient for large workflows.

        Performance target: <100ms for topological sort of 100 steps.
        The topological sort should be O(V+E), not a bottleneck.
        """
        import time

        steps = self._create_large_workflow_steps(100, pattern="mixed")

        start_time = time.perf_counter()
        order = get_execution_order(steps)
        elapsed_time = time.perf_counter() - start_time

        # Verify correct ordering
        assert len(order) == 100

        # Performance assertion: topological sort should be fast
        assert elapsed_time < 0.1, (
            f"Topological sort of 100 steps took {elapsed_time * 1000:.2f}ms, "
            f"expected <100ms"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_validation_performance_100_steps(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that workflow validation is efficient for large workflows.

        Performance target: <100ms for validation of 100 steps.
        Validation should not be a bottleneck.
        """
        import time

        steps = self._create_large_workflow_steps(100, pattern="mixed")

        start_time = time.perf_counter()
        errors = await validate_workflow_definition(simple_workflow_definition, steps)
        elapsed_time = time.perf_counter() - start_time

        # Verify no errors
        assert len(errors) == 0

        # Performance assertion: validation should be fast
        assert elapsed_time < 0.1, (
            f"Validation of 100 steps took {elapsed_time * 1000:.2f}ms, expected <100ms"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_cycle_detection_performance(self) -> None:
        """Test that cycle detection is efficient for large acyclic graphs.

        Performance target: <100ms for cycle detection on 100 steps.
        DFS-based cycle detection should be O(V+E).
        """
        import time

        # Create a large workflow with no cycles
        steps = self._create_large_workflow_steps(100, pattern="linear")

        # Validate (which includes cycle detection)
        from omnibase_core.utils.workflow_executor import _has_dependency_cycles

        start_time = time.perf_counter()
        has_cycles = _has_dependency_cycles(steps)
        elapsed_time = time.perf_counter() - start_time

        # Verify no cycles
        assert not has_cycles

        # Performance assertion
        assert elapsed_time < 0.1, (
            f"Cycle detection for 100 steps took {elapsed_time * 1000:.2f}ms, "
            f"expected <100ms"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_efficiency_large_workflow(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that large workflows don't cause excessive memory usage.

        This test creates a large workflow and verifies execution completes
        without memory-related issues. The workflow result should contain
        all expected data structures without excessive overhead.
        """
        workflow_id = uuid4()
        steps = self._create_large_workflow_steps(150, pattern="mixed")

        result = await execute_workflow(
            simple_workflow_definition,
            steps,
            workflow_id,
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        # Verify all steps completed
        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 150
        assert len(result.actions_emitted) == 150

        # Verify each action has expected structure
        for action in result.actions_emitted:
            assert action.action_id is not None
            assert action.action_type is not None
            assert "workflow_id" in action.payload
            assert "step_id" in action.payload

        # Verify metadata is present
        assert "execution_mode" in result.metadata
        assert "workflow_hash" in result.metadata

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_speedup(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that parallel execution provides speedup over sequential.

        For independent steps, parallel execution should be significantly
        faster than sequential execution.
        """
        import time

        workflow_id = uuid4()
        # Use parallel pattern to maximize benefit of parallel execution
        steps = self._create_large_workflow_steps(50, pattern="parallel")

        # Sequential execution
        seq_start = time.perf_counter()
        seq_result = await execute_workflow(
            simple_workflow_definition,
            steps.copy(),  # Use copy to avoid state pollution
            workflow_id,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        seq_time = time.perf_counter() - seq_start

        # Parallel execution
        par_start = time.perf_counter()
        par_result = await execute_workflow(
            simple_workflow_definition,
            steps.copy(),
            uuid4(),  # Different workflow ID
            execution_mode=EnumExecutionMode.PARALLEL,
        )
        par_time = time.perf_counter() - par_start

        # Both should complete successfully
        assert seq_result.execution_status == EnumWorkflowState.COMPLETED
        assert par_result.execution_status == EnumWorkflowState.COMPLETED

        # Parallel should be faster (or at least not significantly slower)
        # We allow some tolerance since the executor's async nature may vary
        # Note: In this executor, both are fast since no actual I/O is done,
        # but parallel should still have lower overhead for action aggregation
        assert par_time <= seq_time * 1.5, (
            f"Parallel ({par_time:.3f}s) should not be significantly slower "
            f"than sequential ({seq_time:.3f}s)"
        )


@pytest.mark.unit
class TestWorkflowSizeLimits:
    """Tests for workflow size limits and DoS prevention.

    These tests verify that the workflow executor handles large workflows
    gracefully without hanging, excessive memory usage, or causing denial
    of service conditions. The focus is on correctness and graceful handling
    rather than raw performance (see TestWorkflowExecutorPerformance for that).

    Test Scenarios:
        - Large number of workflow steps (up to 100 steps)
        - Deep sequential dependency chains
        - Wide fan-in dependencies (many deps per step)
        - Execution order determinism
    """

    @pytest.mark.asyncio
    async def test_large_workflow_step_count(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow with large number of steps completes or fails gracefully.

        This tests that the system can handle workflows with many steps
        without hanging or causing memory issues. All steps are independent
        (no dependencies) to test maximum parallel processing.
        """
        num_steps = 100  # Reasonable upper bound for unit tests

        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name=f"step_{i}",
                step_type="compute",
                enabled=True,
                depends_on=[],
                priority=1,
            )
            for i in range(num_steps)
        ]

        workflow_id = uuid4()

        # Should complete without timeout or memory issues
        result = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps,
            workflow_id=workflow_id,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == num_steps
        assert len(result.actions_emitted) == num_steps
        assert len(result.failed_steps) == 0

    @pytest.mark.asyncio
    async def test_workflow_with_deep_dependency_chain(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow with deep dependency chain (sequential dependencies).

        Tests that linear dependency chains don't cause stack overflow
        or excessive recursion. Each step depends on the previous one,
        creating a chain of 50 sequential steps.
        """
        num_steps = 50  # Deep chain

        step_ids = [uuid4() for _ in range(num_steps)]
        steps = []

        for i, step_id in enumerate(step_ids):
            depends_on = [step_ids[i - 1]] if i > 0 else []
            steps.append(
                ModelWorkflowStep(
                    step_id=step_id,
                    step_name=f"step_{i}",
                    step_type="compute",
                    enabled=True,
                    depends_on=depends_on,
                    priority=1,
                )
            )

        workflow_id = uuid4()

        result = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps,
            workflow_id=workflow_id,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == num_steps
        assert len(result.actions_emitted) == num_steps

        # Verify execution order respects dependencies
        completed_step_ids = [UUID(s) for s in result.completed_steps]
        for i in range(1, num_steps):
            prev_index = completed_step_ids.index(step_ids[i - 1])
            curr_index = completed_step_ids.index(step_ids[i])
            assert prev_index < curr_index, (
                f"Step {i - 1} should complete before step {i}"
            )

    @pytest.mark.asyncio
    async def test_workflow_with_many_dependencies_per_step(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow where a step depends on many other steps.

        Tests fan-in pattern where one step waits for many predecessors.
        This verifies the executor handles wide dependency graphs without
        issues.
        """
        num_predecessors = 20

        # Create predecessor steps (no dependencies)
        predecessor_ids = [uuid4() for _ in range(num_predecessors)]
        predecessor_steps = [
            ModelWorkflowStep(
                step_id=step_id,
                step_name=f"predecessor_{i}",
                step_type="compute",
                enabled=True,
                depends_on=[],
                priority=1,
            )
            for i, step_id in enumerate(predecessor_ids)
        ]

        # Create final step that depends on all predecessors
        final_step_id = uuid4()
        final_step = ModelWorkflowStep(
            step_id=final_step_id,
            step_name="final_step",
            step_type="compute",
            enabled=True,
            depends_on=predecessor_ids,
            priority=1,
        )

        steps = predecessor_steps + [final_step]
        workflow_id = uuid4()

        result = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps,
            workflow_id=workflow_id,
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == num_predecessors + 1
        assert len(result.actions_emitted) == num_predecessors + 1

        # Verify final step completed last
        completed_step_ids = [UUID(s) for s in result.completed_steps]
        final_index = completed_step_ids.index(final_step_id)

        # All predecessors should have completed before final step
        for pred_id in predecessor_ids:
            pred_index = completed_step_ids.index(pred_id)
            assert pred_index < final_index, (
                f"Predecessor {pred_id} should complete before final step"
            )

    @pytest.mark.asyncio
    async def test_execution_order_determinism_with_large_workflow(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that execution order is deterministic for large workflows.

        Important for debugging and reproducibility. When running the same
        workflow twice with the same steps (using fixed step IDs), the
        execution order should be identical.
        """
        num_steps = 30

        # Create fixed step IDs for reproducibility
        step_ids = [uuid4() for _ in range(num_steps)]

        def create_steps() -> list[ModelWorkflowStep]:
            return [
                ModelWorkflowStep(
                    step_id=step_ids[i],
                    step_name=f"step_{i}",
                    step_type="compute",
                    enabled=True,
                    depends_on=[],
                    priority=(i % 10) + 1,  # Varying priorities 1-10
                )
                for i in range(num_steps)
            ]

        # Execute twice with same workflow steps
        result1 = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=create_steps(),
            workflow_id=uuid4(),
        )

        result2 = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=create_steps(),
            workflow_id=uuid4(),
        )

        # Both should complete successfully
        assert result1.execution_status == EnumWorkflowState.COMPLETED
        assert result2.execution_status == EnumWorkflowState.COMPLETED

        # Completed steps should be in same order (deterministic)
        assert result1.completed_steps == result2.completed_steps, (
            "Execution order should be deterministic for same workflow"
        )

    @pytest.mark.asyncio
    async def test_workflow_with_multiple_fan_in_points(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow with multiple fan-in convergence points.

        Creates a complex dependency graph with multiple layers:
        Layer 1: Independent roots (A, B, C, D)
        Layer 2: Fan-in points (E depends on A,B; F depends on C,D)
        Layer 3: Final fan-in (G depends on E,F)

        This tests the executor's ability to handle complex DAGs.
        """
        # Layer 1: Roots
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()
        step_d_id = uuid4()

        # Layer 2: Fan-in points
        step_e_id = uuid4()
        step_f_id = uuid4()

        # Layer 3: Final fan-in
        step_g_id = uuid4()

        steps = [
            # Layer 1
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="root_a",
                step_type="effect",
                enabled=True,
                depends_on=[],
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="root_b",
                step_type="effect",
                enabled=True,
                depends_on=[],
            ),
            ModelWorkflowStep(
                step_id=step_c_id,
                step_name="root_c",
                step_type="effect",
                enabled=True,
                depends_on=[],
            ),
            ModelWorkflowStep(
                step_id=step_d_id,
                step_name="root_d",
                step_type="effect",
                enabled=True,
                depends_on=[],
            ),
            # Layer 2
            ModelWorkflowStep(
                step_id=step_e_id,
                step_name="fanin_e",
                step_type="compute",
                enabled=True,
                depends_on=[step_a_id, step_b_id],
            ),
            ModelWorkflowStep(
                step_id=step_f_id,
                step_name="fanin_f",
                step_type="compute",
                enabled=True,
                depends_on=[step_c_id, step_d_id],
            ),
            # Layer 3
            ModelWorkflowStep(
                step_id=step_g_id,
                step_name="final_g",
                step_type="reducer",
                enabled=True,
                depends_on=[step_e_id, step_f_id],
            ),
        ]

        result = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 7
        assert len(result.failed_steps) == 0

        # Verify layer ordering
        completed_step_ids = [UUID(s) for s in result.completed_steps]

        # Layer 2 steps should complete after their Layer 1 dependencies
        e_index = completed_step_ids.index(step_e_id)
        a_index = completed_step_ids.index(step_a_id)
        b_index = completed_step_ids.index(step_b_id)
        assert e_index > a_index
        assert e_index > b_index

        f_index = completed_step_ids.index(step_f_id)
        c_index = completed_step_ids.index(step_c_id)
        d_index = completed_step_ids.index(step_d_id)
        assert f_index > c_index
        assert f_index > d_index

        # Layer 3 step should complete last
        g_index = completed_step_ids.index(step_g_id)
        assert g_index > e_index
        assert g_index > f_index

    @pytest.mark.asyncio
    async def test_workflow_graceful_validation_failure(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that large workflows with validation errors fail gracefully.

        Verifies the executor properly validates and rejects workflows
        with issues (like missing dependencies) without crashing.
        """
        num_steps = 50
        nonexistent_dep_id = uuid4()  # Dependency that doesn't exist

        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name=f"step_{i}",
                step_type="compute",
                enabled=True,
                # First step depends on non-existent step
                depends_on=[nonexistent_dep_id] if i == 0 else [],
                priority=1,
            )
            for i in range(num_steps)
        ]

        # Should raise validation error, not hang
        with pytest.raises(ModelOnexError) as exc_info:
            await execute_workflow(
                workflow_definition=simple_workflow_definition,
                workflow_steps=steps,
                workflow_id=uuid4(),
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "non-existent" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_workflow_with_varying_step_types(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test large workflow with mix of step types.

        Verifies that the executor correctly handles workflows with
        different step types (effect, compute, reducer, orchestrator)
        without type-specific issues at scale.
        """
        num_steps = 40
        step_types = ["effect", "compute", "reducer", "orchestrator"]

        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name=f"step_{i}",
                step_type=step_types[i % len(step_types)],
                enabled=True,
                depends_on=[],
                priority=1,
            )
            for i in range(num_steps)
        ]

        result = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == num_steps
        assert len(result.actions_emitted) == num_steps

        # Verify action types are correctly mapped
        from omnibase_core.enums.enum_workflow_execution import EnumActionType

        action_types_found = {action.action_type for action in result.actions_emitted}
        assert EnumActionType.EFFECT in action_types_found
        assert EnumActionType.COMPUTE in action_types_found
        assert EnumActionType.REDUCE in action_types_found
        assert EnumActionType.ORCHESTRATE in action_types_found


@pytest.mark.unit
class TestWorkflowSizeLimitEnforcement:
    """Tests for workflow size limit enforcement (OMN-670).

    These tests verify the security hardening limits added in OMN-670:
    - MAX_WORKFLOW_STEPS (1000): Maximum number of steps in a workflow
    - MAX_STEP_PAYLOAD_SIZE_BYTES (64KB): Maximum size of individual step payload
    - MAX_TOTAL_PAYLOAD_SIZE_BYTES (10MB): Maximum accumulated payload size

    Limits are validated during workflow execution to prevent memory exhaustion.
    """

    @pytest.mark.asyncio
    async def test_validate_workflow_definition_step_count_at_limit(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow with exactly MAX_WORKFLOW_STEPS steps passes validation."""
        from omnibase_core.utils.workflow_executor import MAX_WORKFLOW_STEPS

        # Create workflow with exactly 1000 steps (at limit)
        # Uses model_construct to bypass Pydantic validation for performance
        steps = [
            _create_mock_workflow_step(step_name=f"step_{i}")
            for i in range(MAX_WORKFLOW_STEPS)
        ]

        # Validation should pass (empty error list)
        errors = await validate_workflow_definition(simple_workflow_definition, steps)
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

    @pytest.mark.asyncio
    async def test_validate_workflow_definition_step_count_exceeds_limit(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow exceeding MAX_WORKFLOW_STEPS fails validation."""
        from omnibase_core.utils.workflow_executor import MAX_WORKFLOW_STEPS

        # Create workflow with 1001 steps (exceeds limit)
        # Uses model_construct to bypass Pydantic validation for performance
        steps = [
            _create_mock_workflow_step(step_name=f"step_{i}")
            for i in range(MAX_WORKFLOW_STEPS + 1)
        ]

        # Validation should fail with step limit error
        errors = await validate_workflow_definition(simple_workflow_definition, steps)
        assert len(errors) > 0
        assert any("exceeds maximum step limit" in error for error in errors), (
            f"Expected 'exceeds maximum step limit' error, got: {errors}"
        )

    @pytest.mark.asyncio
    async def test_step_payload_size_under_limit(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test step payload under MAX_STEP_PAYLOAD_SIZE_BYTES passes.

        The payload includes workflow_id, step_id, and step_name fields.
        We use a reasonable step_name that produces a payload well under 64KB.
        """
        # Create a step with a normal name (well under limit)
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="normal_step_name",
            step_type="effect",
            enabled=True,
        )

        # Workflow should execute successfully with normal payload
        result = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=[step],
            workflow_id=uuid4(),
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 1
        assert len(result.actions_emitted) == 1

    def test_step_payload_size_exceeds_limit(self) -> None:
        """Test step payload exceeding MAX_STEP_PAYLOAD_SIZE_BYTES raises error.

        Note: ModelWorkflowStep.step_name has a max length of 200 characters,
        so we cannot exceed 64KB with a real step. We test the _create_action_for_step
        function directly using a mock step to verify the limit enforcement logic.
        """
        from unittest.mock import MagicMock

        from omnibase_core.utils.workflow_executor import (
            MAX_STEP_PAYLOAD_SIZE_BYTES,
            _create_action_for_step,
        )

        # Create a mock step with an extremely long name (bypassing Pydantic validation)
        mock_step = MagicMock(spec=ModelWorkflowStep)
        mock_step.step_id = uuid4()
        mock_step.step_name = "x" * (MAX_STEP_PAYLOAD_SIZE_BYTES + 1000)  # Exceeds 64KB
        mock_step.step_type = "effect"
        mock_step.priority = 1
        mock_step.depends_on = []
        mock_step.timeout_ms = 5000
        mock_step.retry_count = 0
        mock_step.correlation_id = uuid4()

        # Should raise ModelOnexError with WORKFLOW_PAYLOAD_SIZE_EXCEEDED
        with pytest.raises(ModelOnexError) as exc_info:
            _create_action_for_step(mock_step, uuid4())

        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.WORKFLOW_PAYLOAD_SIZE_EXCEEDED
        )
        assert "payload exceeds size limit" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_total_payload_size_exceeds_limit_sequential(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test total payload exceeding limit in sequential execution is handled gracefully.

        Note: With ModelWorkflowStep.step_name limited to 200 chars and
        MAX_WORKFLOW_STEPS limited to 1000, the maximum possible total payload
        is ~300KB (well under 10MB). We mock _create_action_for_step to return
        actions with large payloads to trigger the limit.

        In sequential execution, the limit error is caught by the step error handler
        and treated as a step failure with 'continue' behavior (the default).
        The workflow returns FAILED status rather than raising the error.
        """
        from unittest.mock import patch

        from omnibase_core.utils.workflow_executor import (
            MAX_TOTAL_PAYLOAD_SIZE_BYTES,
            _create_action_for_step,
        )

        # Create a normal workflow (within all model limits)
        num_steps = 20
        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name=f"step_{i}",
                step_type="compute",
                enabled=True,
            )
            for i in range(num_steps)
        ]

        # Each action will have a ~550KB payload, so 20 steps = ~11MB > 10MB limit
        large_payload_size = MAX_TOTAL_PAYLOAD_SIZE_BYTES // (num_steps - 1)
        call_count = 0

        def mock_create_action(step, workflow_id):
            """Create action with large payload to exceed total limit."""
            nonlocal call_count
            call_count += 1
            action, _ = _create_action_for_step(step, workflow_id)
            # Inject large data into payload (simulating future payload expansion)
            action.payload["large_data"] = "x" * large_payload_size
            # Return tuple with updated payload size
            import json

            new_payload_size = len(json.dumps(action.payload).encode("utf-8"))
            return (action, new_payload_size)

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step",
            side_effect=mock_create_action,
        ):
            # In sequential execution, the error is caught and handled gracefully
            # The workflow returns with FAILED status
            result = await execute_workflow(
                workflow_definition=simple_workflow_definition,
                workflow_steps=steps,
                workflow_id=uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        # Workflow should fail but not raise an exception
        assert result.execution_status == EnumWorkflowState.FAILED
        # Some steps should have completed before the limit was hit
        assert len(result.completed_steps) > 0
        # At least one step should have failed (the one that exceeded the limit)
        assert len(result.failed_steps) > 0
        # Verify some steps were processed before limit was hit
        assert call_count > 1, "Multiple steps should be processed before limit is hit"

    @pytest.mark.asyncio
    async def test_total_payload_size_exceeds_limit_parallel(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test total payload exceeding limit in parallel execution raises error.

        Note: Similar to sequential test, we mock _create_action_for_step to
        return actions with large payloads to trigger the 10MB total limit.
        """
        from unittest.mock import patch

        from omnibase_core.utils.workflow_executor import (
            MAX_TOTAL_PAYLOAD_SIZE_BYTES,
            _create_action_for_step,
        )

        # Create a normal workflow (within all model limits)
        num_steps = 20
        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name=f"step_{i}",
                step_type="compute",
                enabled=True,
            )
            for i in range(num_steps)
        ]

        # Each action will have a ~550KB payload
        large_payload_size = MAX_TOTAL_PAYLOAD_SIZE_BYTES // (num_steps - 1)
        call_count = 0

        def mock_create_action(step, workflow_id):
            """Create action with large payload to exceed total limit."""
            nonlocal call_count
            call_count += 1
            action, _ = _create_action_for_step(step, workflow_id)
            action.payload["large_data"] = "x" * large_payload_size
            # Return tuple with updated payload size
            import json

            new_payload_size = len(json.dumps(action.payload).encode("utf-8"))
            return (action, new_payload_size)

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step",
            side_effect=mock_create_action,
        ):
            with pytest.raises(ModelOnexError) as exc_info:
                await execute_workflow(
                    workflow_definition=simple_workflow_definition,
                    workflow_steps=steps,
                    workflow_id=uuid4(),
                    execution_mode=EnumExecutionMode.PARALLEL,
                )

        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.WORKFLOW_TOTAL_PAYLOAD_EXCEEDED
        )
        assert "total payload exceeds limit" in exc_info.value.message.lower()
        # Verify some steps were processed before limit was hit
        assert call_count > 1, "Multiple steps should be processed before limit is hit"

    @pytest.mark.asyncio
    async def test_total_payload_size_exceeds_limit_batch(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test total payload exceeding limit in batch execution is handled gracefully.

        Note: Batch mode internally uses sequential execution (see workflow_executor.py
        line 742), so the behavior should be identical to sequential - the limit error
        is caught and treated as a step failure with FAILED status returned.

        This test verifies that batch mode correctly inherits the graceful error
        handling from sequential execution rather than raising an exception.
        """
        from unittest.mock import patch

        from omnibase_core.utils.workflow_executor import (
            MAX_TOTAL_PAYLOAD_SIZE_BYTES,
            _create_action_for_step,
        )

        # Create a normal workflow (within all model limits)
        num_steps = 20
        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name=f"step_{i}",
                step_type="compute",
                enabled=True,
            )
            for i in range(num_steps)
        ]

        # Each action will have a ~550KB payload, so 20 steps = ~11MB > 10MB limit
        large_payload_size = MAX_TOTAL_PAYLOAD_SIZE_BYTES // (num_steps - 1)
        call_count = 0

        def mock_create_action(step, workflow_id):
            """Create action with large payload to exceed total limit."""
            nonlocal call_count
            call_count += 1
            action, _ = _create_action_for_step(step, workflow_id)
            # Inject large data into payload (simulating future payload expansion)
            action.payload["large_data"] = "x" * large_payload_size
            # Return tuple with updated payload size
            import json

            new_payload_size = len(json.dumps(action.payload).encode("utf-8"))
            return (action, new_payload_size)

        with patch(
            "omnibase_core.utils.workflow_executor._create_action_for_step",
            side_effect=mock_create_action,
        ):
            # In batch execution (which uses sequential internally), the error is
            # caught and handled gracefully. The workflow returns with FAILED status.
            result = await execute_workflow(
                workflow_definition=simple_workflow_definition,
                workflow_steps=steps,
                workflow_id=uuid4(),
                execution_mode=EnumExecutionMode.BATCH,
            )

        # Workflow should fail but not raise an exception
        assert result.execution_status == EnumWorkflowState.FAILED
        # Some steps should have completed before the limit was hit
        assert len(result.completed_steps) > 0
        # At least one step should have failed (the one that exceeded the limit)
        assert len(result.failed_steps) > 0
        # Verify some steps were processed before limit was hit
        assert call_count > 1, "Multiple steps should be processed before limit is hit"
        # Verify batch metadata is present (batch mode adds this)
        assert result.metadata.get("execution_mode").get_string() == "batch"
        assert (
            result.metadata.get("batch_size").get_number().to_python_value()
            == num_steps
        )

    def test_constants_exported(self) -> None:
        """Test that size limit constants are exported in __all__."""
        from omnibase_core.utils.workflow_executor import (
            MAX_STEP_PAYLOAD_SIZE_BYTES,
            MAX_TOTAL_PAYLOAD_SIZE_BYTES,
            MAX_WORKFLOW_STEPS,
        )

        assert MAX_WORKFLOW_STEPS == 1000
        assert MAX_STEP_PAYLOAD_SIZE_BYTES == 64 * 1024  # 64KB
        assert MAX_TOTAL_PAYLOAD_SIZE_BYTES == 10 * 1024 * 1024  # 10MB

    def test_error_codes_available(self) -> None:
        """Test that workflow limit error codes exist."""
        assert hasattr(EnumCoreErrorCode, "WORKFLOW_STEP_LIMIT_EXCEEDED")
        assert hasattr(EnumCoreErrorCode, "WORKFLOW_PAYLOAD_SIZE_EXCEEDED")
        assert hasattr(EnumCoreErrorCode, "WORKFLOW_TOTAL_PAYLOAD_EXCEEDED")

    @pytest.mark.asyncio
    async def test_workflow_under_all_limits_succeeds(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that workflow well under all limits executes successfully.

        Verifies that normal workflows are not affected by the size limits.
        """
        # Create a normal workflow with 10 steps
        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name=f"normal_step_{i}",
                step_type="compute",
                enabled=True,
            )
            for i in range(10)
        ]

        result = await execute_workflow(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps,
            workflow_id=uuid4(),
        )

        assert result.execution_status == EnumWorkflowState.COMPLETED
        assert len(result.completed_steps) == 10
        assert len(result.actions_emitted) == 10
        assert len(result.failed_steps) == 0

    @pytest.mark.asyncio
    async def test_step_limit_validation_includes_count_in_error(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that step limit validation error includes the actual count."""
        from omnibase_core.utils.workflow_executor import MAX_WORKFLOW_STEPS

        # Create workflow exceeding limit by 1 (minimum needed to trigger error)
        # Uses model_construct to bypass Pydantic validation for performance
        num_steps = MAX_WORKFLOW_STEPS + 1
        steps = [
            _create_mock_workflow_step(step_name=f"step_{i}") for i in range(num_steps)
        ]

        errors = await validate_workflow_definition(simple_workflow_definition, steps)

        # Error should include both the actual count and the limit
        assert len(errors) > 0
        step_limit_error = next((e for e in errors if "maximum step limit" in e), None)
        assert step_limit_error is not None
        assert str(num_steps) in step_limit_error
        assert str(MAX_WORKFLOW_STEPS) in step_limit_error

    @pytest.mark.asyncio
    async def test_step_limit_short_circuits_validation(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that step limit validation short-circuits to prevent DoS.

        When step count exceeds MAX_WORKFLOW_STEPS, validation should return
        immediately with only the step count error. This prevents attackers from
        causing CPU exhaustion by submitting workflows with millions of steps
        that would otherwise trigger expensive cycle detection and per-step
        validation.

        Security: OMN-670 - DoS mitigation via validation short-circuit
        """
        from omnibase_core.utils.workflow_executor import MAX_WORKFLOW_STEPS

        # Create workflow with steps that would have other validation errors
        # (invalid dependencies) if validation continued past the step count check
        # Uses model_construct to bypass Pydantic validation for performance
        num_steps = MAX_WORKFLOW_STEPS + 1
        invalid_dep_id = uuid4()  # Non-existent dependency
        steps = [
            _create_mock_workflow_step(
                step_name=f"step_{i}",
                depends_on=[
                    invalid_dep_id
                ],  # Would fail dep validation if not short-circuited
            )
            for i in range(num_steps)
        ]

        errors = await validate_workflow_definition(simple_workflow_definition, steps)

        # Should return ONLY the step limit error due to short-circuit
        # If validation continued, we would see additional errors for:
        # - Invalid dependencies (num_steps errors - one per step)
        # Without short-circuit, this would be 1 + num_steps errors
        assert len(errors) == 1, (
            f"Expected exactly 1 error (step limit), got {len(errors)} errors. "
            f"Short-circuit validation failed - other validations ran. Errors: {errors[:5]}..."
        )
        assert "maximum step limit" in errors[0]
        assert str(num_steps) in errors[0]
