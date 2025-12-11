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
        workflow_hash = result.metadata["workflow_hash"]
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
            result_sequential.metadata["workflow_hash"]
            == result_parallel.metadata["workflow_hash"]
        )

        # And both should match the computed hash
        expected_hash = _compute_workflow_hash(simple_workflow_definition)
        assert result_sequential.metadata["workflow_hash"] == expected_hash


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

        action = _create_action_for_step(step, uuid4())

        # Default priority (100) should be clamped to 10
        assert action.priority == 10

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
        action = _create_action_for_step(mock_step, uuid4())

        # None priority should default to 1
        assert action.priority == 1


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
