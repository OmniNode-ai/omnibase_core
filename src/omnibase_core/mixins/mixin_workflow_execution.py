"""
Mixin for workflow execution from YAML contracts.

Enables orchestrator nodes to execute workflows declaratively from
ModelWorkflowDefinition.

Typing: Strongly typed with strategic Any usage for mixin kwargs and configuration dicts.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.workflow.execution.model_workflow_state_snapshot import (
        ModelWorkflowStateSnapshot,
    )
    from omnibase_core.types.typed_dict_mixin_types import TypedDictWorkflowStepConfig

    # These imports are for type hints only - actual imports are done lazily in methods
    # to avoid circular import with workflow_executor
    from omnibase_core.utils.util_workflow_executor import (
        WorkflowExecutionResult,
    )

from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.types.type_workflow_context import WorkflowContextType

# Type aliases for workflow executor functions.
# These use string forward references for WorkflowExecutionResult since it's
# imported lazily to avoid circular imports. At runtime, the actual callables
# from workflow_executor module are stored.

# execute_workflow: async (definition, steps, workflow_id, mode?) -> WorkflowExecutionResult
ExecuteWorkflowFunc = Callable[
    [ModelWorkflowDefinition, list[ModelWorkflowStep], UUID, EnumExecutionMode | None],
    Coroutine[object, object, "WorkflowExecutionResult"],
]

# get_execution_order: sync (steps) -> list[UUID]
GetExecutionOrderFunc = Callable[[list[ModelWorkflowStep]], list[UUID]]

# validate_workflow_definition: async (definition, steps) -> list[str]
ValidateWorkflowDefinitionFunc = Callable[
    [ModelWorkflowDefinition, list[ModelWorkflowStep]],
    Coroutine[object, object, list[str]],
]

# Module-level cache for lazy imports to avoid repeated import overhead.
# Populated on first access by _get_workflow_executor().
_workflow_executor_cache: (
    tuple[
        type[WorkflowExecutionResult],
        ExecuteWorkflowFunc,
        GetExecutionOrderFunc,
        ValidateWorkflowDefinitionFunc,
    ]
    | None
) = None


# Lazy import helper to avoid circular import with workflow_executor
def _get_workflow_executor() -> tuple[
    type[WorkflowExecutionResult],
    ExecuteWorkflowFunc,
    GetExecutionOrderFunc,
    ValidateWorkflowDefinitionFunc,
]:
    """
    Lazily import workflow_executor to avoid circular import.

    Uses module-level cache (_workflow_executor_cache) to memoize imports
    on first access, avoiding repeated import overhead on subsequent calls.
    """
    global _workflow_executor_cache

    if _workflow_executor_cache is not None:
        return _workflow_executor_cache

    from omnibase_core.utils.util_workflow_executor import (
        WorkflowExecutionResult,
        execute_workflow,
        get_execution_order,
        validate_workflow_definition,
    )

    _workflow_executor_cache = (
        WorkflowExecutionResult,
        execute_workflow,
        get_execution_order,
        validate_workflow_definition,
    )

    return _workflow_executor_cache


# Module-level cache for lazy-imported ModelWorkflowStateSnapshot class.
# This avoids repeated import overhead when update_workflow_state() is called frequently.
_workflow_state_snapshot_class: type | None = None


def _get_workflow_state_snapshot_class() -> type:
    """Get the ModelWorkflowStateSnapshot class, importing lazily and caching."""
    global _workflow_state_snapshot_class
    if _workflow_state_snapshot_class is None:
        from omnibase_core.models.workflow.execution.model_workflow_state_snapshot import (
            ModelWorkflowStateSnapshot,
        )

        _workflow_state_snapshot_class = ModelWorkflowStateSnapshot
    return _workflow_state_snapshot_class


class MixinWorkflowExecution:
    """
    Mixin providing workflow execution capabilities from YAML contracts.

    Enables orchestrator nodes to execute workflows declaratively without
    custom code. Workflow coordination is driven entirely by contract.

    Usage:
        class NodeMyOrchestrator(NodeOrchestrator, MixinWorkflowExecution):
            # No custom workflow code needed - driven by YAML contract
            pass

    Pattern:
        This mixin tracks workflow state via ModelWorkflowStateSnapshot.
        Delegates execution to pure functions while maintaining state for
        serialization and replay capabilities.

    Attributes:
        _workflow_state: Current workflow state snapshot, or None if no
            workflow execution is in progress.
    """

    # Type annotation for workflow state tracking (see __init__ for population details)
    _workflow_state: ModelWorkflowStateSnapshot | None

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize workflow execution mixin.

        Args:
            **kwargs: Passed to super().__init__()
        """
        super().__init__(**kwargs)
        # Initialize workflow state tracking
        self._workflow_state = None
        # NOTE: _workflow_state is populated by:
        # 1. execute_workflow_from_contract() - automatically captures state after
        #    each workflow step execution (completed/failed step IDs, context)
        # 2. update_workflow_state() - manual state updates for custom workflows
        # 3. restore_workflow_state() - restoring from a persisted snapshot
        # The state remains None until one of these methods is called.

    def update_workflow_state(
        self,
        workflow_id: UUID | None,
        current_step_index: int,
        completed_step_ids: list[UUID] | tuple[UUID, ...] | None = None,
        failed_step_ids: list[UUID] | tuple[UUID, ...] | None = None,
        context: WorkflowContextType | None = None,
    ) -> None:
        """
        Update workflow state tracking for serialization and replay.

        Creates a new workflow state snapshot that can be retrieved via
        `snapshot_workflow_state()`. This method is called automatically
        after `execute_workflow_from_contract()` completes, but can also
        be called manually to track intermediate workflow progress.

        Args:
            workflow_id: Unique workflow execution ID.
            current_step_index: Index of the current/completed step.
            completed_step_ids: Sequence of completed step UUIDs (list or tuple).
            failed_step_ids: Sequence of failed step UUIDs (list or tuple).
            context: Additional workflow context data.

        Example:
            ```python
            from uuid import uuid4

            # Manual state tracking during workflow execution
            orchestrator.update_workflow_state(
                workflow_id=uuid4(),
                current_step_index=1,
                completed_step_ids=[step1_id],
                context={"key": "value"},
            )

            # State is now available for serialization
            snapshot = orchestrator.snapshot_workflow_state()
            assert snapshot is not None
            assert snapshot.current_step_index == 1
            ```

        Note:
            This method creates a new immutable snapshot. The previous
            state is replaced, not merged. Step IDs are stored as tuples
            for immutability.
        """
        # Use memoized getter to avoid repeated import overhead.
        # The TYPE_CHECKING import provides type hints; this provides the runtime class.
        snapshot_class = _get_workflow_state_snapshot_class()

        self._workflow_state = snapshot_class(
            workflow_id=workflow_id,
            current_step_index=current_step_index,
            completed_step_ids=tuple(completed_step_ids) if completed_step_ids else (),
            failed_step_ids=tuple(failed_step_ids) if failed_step_ids else (),
            context=context or {},
        )

    async def execute_workflow_from_contract(
        self,
        workflow_definition: ModelWorkflowDefinition,
        workflow_steps: list[ModelWorkflowStep],
        workflow_id: UUID,
        execution_mode: EnumExecutionMode | None = None,
    ) -> WorkflowExecutionResult:
        """
        Execute workflow from YAML contract.

        Pure function delegation: delegates to utils/util_workflow_executor.execute_workflow()
        which returns (result, actions) without side effects.

        After execution completes, automatically updates the internal workflow state
        (`_workflow_state`) with the execution results. This state can be retrieved
        via `snapshot_workflow_state()` for serialization, debugging, or replay.

        Args:
            workflow_definition: Workflow definition from node contract
            workflow_steps: Workflow steps to execute
            workflow_id: Unique workflow execution ID
            execution_mode: Optional execution mode override

        Returns:
            WorkflowExecutionResult with emitted actions

        Example:
            result = await self.execute_workflow_from_contract(
                self.contract.workflow_coordination.workflow_definition,
                workflow_steps=[...],
                workflow_id=uuid4(),
            )

            # Check result
            if result.execution_status == EnumWorkflowStatus.COMPLETED:
                print(f"Workflow completed: {len(result.actions_emitted)} actions")
                # Process actions (emitted to target nodes)
                for action in result.actions_emitted:
                    print(f"Action: {action.action_type} -> {action.target_node_type}")

            # Workflow state is automatically captured for serialization
            snapshot = self.snapshot_workflow_state()
            if snapshot:
                print(f"Completed steps: {len(snapshot.completed_step_ids)}")
        """
        # Lazy import to avoid circular import with workflow_executor
        _, execute_workflow, _, _ = _get_workflow_executor()
        result = await execute_workflow(
            workflow_definition,
            workflow_steps,
            workflow_id,
            execution_mode,
        )

        # Automatically capture workflow state after execution for serialization/replay
        # Convert string step IDs back to UUIDs for the snapshot
        completed_ids = [UUID(step_id) for step_id in result.completed_steps]
        failed_ids = [UUID(step_id) for step_id in result.failed_steps]

        # Metadata is always present when result comes from execute_workflow().
        # All internal execution paths (_execute_sequential, _execute_parallel,
        # _execute_batch) explicitly create ModelWorkflowResultMetadata.
        # The Optional type in ModelDeclarativeWorkflowResult exists for API
        # flexibility (direct instantiation), not for the execute_workflow() path.
        assert result.metadata is not None, (
            "execute_workflow() must always return result with metadata; "
            "this indicates a bug in workflow_executor.py"
        )

        self.update_workflow_state(
            workflow_id=workflow_id,
            current_step_index=len(completed_ids) + len(failed_ids),
            completed_step_ids=completed_ids,
            failed_step_ids=failed_ids,
            context={
                "execution_status": result.execution_status.value,
                "execution_time_ms": result.execution_time_ms,
                "actions_count": len(result.actions_emitted),
                **result.metadata.model_dump(exclude_unset=True),
            },
        )

        return result

    async def validate_workflow_contract(
        self,
        workflow_definition: ModelWorkflowDefinition,
        workflow_steps: list[ModelWorkflowStep],
    ) -> list[str]:
        """
        Validate workflow contract for correctness.

        Pure function delegation: delegates to utils/util_workflow_executor.validate_workflow_definition()

        Args:
            workflow_definition: Workflow definition to validate
            workflow_steps: Workflow steps to validate

        Returns:
            List of validation errors (empty if valid)

        Example:
            errors = await self.validate_workflow_contract(
                self.contract.workflow_coordination.workflow_definition,
                workflow_steps=[...]
            )

            if errors:
                print(f"Workflow validation failed: {errors}")
            else:
                print("Workflow contract is valid!")
        """
        # Lazy import to avoid circular import with workflow_executor
        _, _, _, validate_workflow_definition = _get_workflow_executor()
        # Cast to satisfy mypy since validate_workflow_definition returns Any from lazy import
        validation_result: list[str] = await validate_workflow_definition(
            workflow_definition, workflow_steps
        )
        return validation_result

    def get_workflow_execution_order(
        self,
        workflow_steps: list[ModelWorkflowStep],
    ) -> list[UUID]:
        """
        Get topological execution order for workflow steps.

        Args:
            workflow_steps: Workflow steps to order

        Returns:
            List of step IDs in execution order

        Raises:
            ModelOnexError: If workflow contains cycles

        Example:
            steps = [...]
            order = self.get_workflow_execution_order(steps)
            print(f"Execution order: {order}")
        """
        # Lazy import to avoid circular import with workflow_executor
        _, _, get_execution_order, _ = _get_workflow_executor()
        # Cast to satisfy mypy since get_execution_order returns Any from lazy import
        execution_order: list[UUID] = get_execution_order(workflow_steps)
        return execution_order

    def create_workflow_steps_from_config(
        self,
        steps_config: list[TypedDictWorkflowStepConfig],
    ) -> list[ModelWorkflowStep]:
        """
        Create ModelWorkflowStep instances from configuration dictionaries.

        Helper method for converting YAML/dict config to typed models.

        Args:
            steps_config: List of step configuration dictionaries

        Returns:
            List of ModelWorkflowStep instances

        Example:
            steps_config = [
                TypedDictWorkflowStepConfig(
                    step_name="Fetch Data",
                    step_type="effect",
                    timeout_ms=10000,
                ),
                TypedDictWorkflowStepConfig(
                    step_name="Process Data",
                    step_type="compute",
                    depends_on=[...],
                ),
            ]
            steps = self.create_workflow_steps_from_config(steps_config)
        """

        workflow_steps: list[ModelWorkflowStep] = []

        for step_config in steps_config:
            # NOTE(OMN-1302): TypedDict compatible with ** unpacking but mypy cannot verify at call site.
            # Safe because ModelWorkflowStep validates fields.
            step = ModelWorkflowStep(**step_config)  # type: ignore[arg-type]
            workflow_steps.append(step)

        return workflow_steps
