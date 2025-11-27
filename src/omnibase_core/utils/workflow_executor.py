"""
Workflow execution utilities for declarative orchestration.

Pure functions for executing workflows from ModelWorkflowDefinition.
No side effects - returns results and actions.

Typing: Strongly typed with strategic Any usage where runtime flexibility required.
"""

import logging
import time
from datetime import datetime
from uuid import UUID, uuid4

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.workflow.execution.model_declarative_workflow_result import (
    ModelDeclarativeWorkflowResult as WorkflowExecutionResult,
)
from omnibase_core.models.workflow.execution.model_declarative_workflow_step_context import (
    ModelDeclarativeWorkflowStepContext as WorkflowStepExecutionContext,
)


async def execute_workflow(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
    execution_mode: EnumExecutionMode | None = None,
) -> WorkflowExecutionResult:
    """
    Execute workflow declaratively from YAML contract.

    Pure function: (workflow_def, steps) → (result, actions)

    Args:
        workflow_definition: Workflow definition from YAML contract
        workflow_steps: List of workflow steps to execute
        workflow_id: Unique workflow execution ID
        execution_mode: Optional execution mode override

    Returns:
        WorkflowExecutionResult with emitted actions

    Raises:
        ModelOnexError: If workflow execution fails

    Example:
        Execute a data processing workflow::

            from uuid import uuid4
            from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
            from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
                ModelWorkflowDefinition,
            )

            # Define workflow
            workflow_def = ModelWorkflowDefinition(
                workflow_metadata=ModelWorkflowMetadata(
                    workflow_name="data_pipeline",
                    execution_mode="sequential",
                    timeout_ms=60000,
                )
            )

            # Define steps
            step1_id = uuid4()
            step2_id = uuid4()
            steps = [
                ModelWorkflowStep(
                    step_id=step1_id,
                    step_name="fetch_data",
                    step_type="effect",
                    enabled=True,
                ),
                ModelWorkflowStep(
                    step_id=step2_id,
                    step_name="process_data",
                    step_type="compute",
                    depends_on=[step1_id],
                    enabled=True,
                ),
            ]

            # Execute workflow
            result = await execute_workflow(
                workflow_definition=workflow_def,
                workflow_steps=steps,
                workflow_id=uuid4(),
            )

            # Check result
            print(f"Status: {result.execution_status}")
            print(f"Completed: {len(result.completed_steps)} steps")
            print(f"Actions emitted: {len(result.actions_emitted)}")
            print(f"Execution time: {result.execution_time_ms}ms")
    """
    start_time = time.perf_counter()

    # Validate workflow
    validation_errors = await validate_workflow_definition(
        workflow_definition, workflow_steps
    )
    if validation_errors:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Workflow validation failed: {', '.join(validation_errors)}",
            context={"workflow_id": str(workflow_id), "errors": validation_errors},
        )

    # Determine execution mode
    mode = execution_mode or _get_execution_mode(workflow_definition)

    # Execute based on mode
    if mode == EnumExecutionMode.SEQUENTIAL:
        result = await _execute_sequential(
            workflow_definition, workflow_steps, workflow_id
        )
    elif mode == EnumExecutionMode.PARALLEL:
        result = await _execute_parallel(
            workflow_definition, workflow_steps, workflow_id
        )
    elif mode == EnumExecutionMode.BATCH:
        result = await _execute_batch(workflow_definition, workflow_steps, workflow_id)
    else:
        # Default to sequential
        result = await _execute_sequential(
            workflow_definition, workflow_steps, workflow_id
        )

    # Calculate execution time with high precision
    # Ensure minimum 1ms to avoid zero values for very fast executions
    end_time = time.perf_counter()
    execution_time_ms = max(1, int((end_time - start_time) * 1000))
    result.execution_time_ms = execution_time_ms

    return result


async def validate_workflow_definition(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
) -> list[str]:
    """
    Validate workflow definition and steps for correctness.

    Pure validation function - no side effects.

    Args:
        workflow_definition: Workflow definition to validate
        workflow_steps: Workflow steps to validate

    Returns:
        List of validation errors (empty if valid)

    Example:
        Validate workflow before execution::

            from uuid import uuid4

            # Define workflow
            workflow_def = ModelWorkflowDefinition(
                workflow_metadata=ModelWorkflowMetadata(
                    workflow_name="etl_pipeline",
                    execution_mode="sequential",
                    timeout_ms=30000,
                )
            )

            # Define steps with potential issues
            step1_id = uuid4()
            steps = [
                ModelWorkflowStep(
                    step_id=step1_id,
                    step_name="extract",
                    step_type="effect",
                    depends_on=[uuid4()],  # Invalid dependency!
                    enabled=True,
                ),
            ]

            # Validate
            errors = await validate_workflow_definition(workflow_def, steps)
            if errors:
                print("Workflow validation failed:")
                for error in errors:
                    print(f"  - {error}")
                # Output: "Step 'extract' depends on non-existent step: ..."
            else:
                print("Workflow is valid")
                # Safe to execute
    """
    errors: list[str] = []

    # Validate workflow definition metadata
    if not workflow_definition.workflow_metadata.workflow_name:
        errors.append("Workflow name is required")

    if workflow_definition.workflow_metadata.execution_mode not in {
        "sequential",
        "parallel",
        "batch",
    }:
        errors.append(
            f"Invalid execution mode: {workflow_definition.workflow_metadata.execution_mode}"
        )

    if workflow_definition.workflow_metadata.timeout_ms <= 0:
        errors.append(
            f"Workflow timeout must be positive, got: {workflow_definition.workflow_metadata.timeout_ms}"
        )

    # Check workflow has steps
    if not workflow_steps:
        errors.append("Workflow has no steps defined")
        return errors

    # Check for dependency cycles
    if _has_dependency_cycles(workflow_steps):
        errors.append("Workflow contains dependency cycles")

    # Validate each step
    step_ids = {step.step_id for step in workflow_steps}
    for step in workflow_steps:
        # Check step name
        if not step.step_name:
            errors.append(f"Step {step.step_id} missing name")

        # Check dependencies reference valid steps
        for dep_id in step.depends_on:
            if dep_id not in step_ids:
                errors.append(
                    f"Step '{step.step_name}' depends on non-existent step: {dep_id}"
                )

    return errors


def get_execution_order(
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
        Determine execution order for workflow with dependencies::

            from uuid import uuid4

            # Define steps with dependencies
            step_a = uuid4()  # No dependencies
            step_b = uuid4()  # Depends on A
            step_c = uuid4()  # Depends on B
            step_d = uuid4()  # Depends on A (parallel with B)

            steps = [
                ModelWorkflowStep(
                    step_id=step_c,
                    step_name="step_c",
                    depends_on=[step_b],
                    step_type="compute",
                    enabled=True,
                ),
                ModelWorkflowStep(
                    step_id=step_a,
                    step_name="step_a",
                    depends_on=[],
                    step_type="effect",
                    enabled=True,
                ),
                ModelWorkflowStep(
                    step_id=step_b,
                    step_name="step_b",
                    depends_on=[step_a],
                    step_type="compute",
                    enabled=True,
                ),
                ModelWorkflowStep(
                    step_id=step_d,
                    step_name="step_d",
                    depends_on=[step_a],
                    step_type="reducer",
                    enabled=True,
                ),
            ]

            # Get execution order
            order = get_execution_order(steps)
            # Result: [step_a, step_b, step_d, step_c]
            # or:     [step_a, step_d, step_b, step_c]
            # (B and D can run in parallel after A)

            print("Execution order:")
            for step_id in order:
                step = next(s for s in steps if s.step_id == step_id)
                print(f"  {step.step_name}")
    """
    if _has_dependency_cycles(workflow_steps):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Cannot compute execution order: workflow contains cycles",
            context={},
        )

    return _get_topological_order(workflow_steps)


# Private helper functions


def _get_execution_mode(
    workflow_definition: ModelWorkflowDefinition,
) -> EnumExecutionMode:
    """Extract execution mode from workflow metadata."""
    mode_str = workflow_definition.workflow_metadata.execution_mode
    mode_map = {
        "sequential": EnumExecutionMode.SEQUENTIAL,
        "parallel": EnumExecutionMode.PARALLEL,
        "batch": EnumExecutionMode.BATCH,
    }
    return mode_map.get(mode_str, EnumExecutionMode.SEQUENTIAL)


async def _execute_sequential(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
) -> WorkflowExecutionResult:
    """Execute workflow steps sequentially."""
    completed_steps: list[str] = []
    failed_steps: list[str] = []
    all_actions: list[ModelAction] = []
    completed_step_ids: set[UUID] = set()

    # Log workflow execution start
    logging.info(
        f"Starting sequential execution of workflow '{workflow_definition.workflow_metadata.workflow_name}' ({workflow_id})"
    )

    # Get topological order for dependency-aware execution
    execution_order = _get_topological_order(workflow_steps)

    # Create step lookup
    steps_by_id = {step.step_id: step for step in workflow_steps}

    for step_id in execution_order:
        step = steps_by_id.get(step_id)
        if not step:
            continue

        # Check if step should be skipped
        if not step.enabled:
            continue

        # Check dependencies are met
        if not _dependencies_met(step, completed_step_ids):
            failed_steps.append(str(step.step_id))
            continue

        try:
            # Create context
            context = WorkflowStepExecutionContext(
                step, workflow_id, completed_step_ids
            )

            # Emit action for this step
            action = _create_action_for_step(step, workflow_id)
            all_actions.append(action)

            # Mark step as completed
            context.completed_at = datetime.now()
            completed_steps.append(str(step.step_id))
            completed_step_ids.add(step.step_id)

        except ModelOnexError as e:
            # Handle expected ONEX errors
            failed_steps.append(str(step.step_id))
            # Extract error code value safely
            error_code_value: str | None = None
            if e.error_code is not None:
                error_code_value = (
                    e.error_code.value
                    if hasattr(e.error_code, "value")
                    else str(e.error_code)
                )
            logging.warning(
                f"Workflow '{workflow_definition.workflow_metadata.workflow_name}' step '{step.step_name}' ({step.step_id}) failed: {e.message}",
                extra={"error_code": error_code_value, "context": e.context},
                exc_info=True,
            )

            # Handle based on error action
            if step.error_action == "stop":
                break
            if step.error_action == "continue":
                continue
            # For other error actions, continue for now

        except Exception as e:
            # Broad exception catch justified for workflow orchestration:
            # - Workflow steps execute external code with unknown exception types
            # - Production workflows require resilient error handling
            # - All failures logged with full traceback for debugging
            # - Failed steps tracked; execution continues per error_action config
            failed_steps.append(str(step.step_id))
            logging.exception(
                f"Workflow '{workflow_definition.workflow_metadata.workflow_name}' step '{step.step_name}' ({step.step_id}) failed with unexpected error: {e}"
            )

            # Handle based on error action
            if step.error_action == "stop":
                break
            if step.error_action == "continue":
                continue
            # For other error actions, continue for now

    # Determine final status
    status = (
        EnumWorkflowState.COMPLETED if not failed_steps else EnumWorkflowState.FAILED
    )

    return WorkflowExecutionResult(
        workflow_id=workflow_id,
        execution_status=status,
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        actions_emitted=all_actions,
        execution_time_ms=0,  # Will be set by caller
        metadata={
            "execution_mode": "sequential",
            "workflow_name": workflow_definition.workflow_metadata.workflow_name,
        },
    )


async def _execute_parallel(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
) -> WorkflowExecutionResult:
    """Execute workflow steps in parallel (respecting dependencies)."""
    completed_steps: list[str] = []
    failed_steps: list[str] = []
    all_actions: list[ModelAction] = []
    completed_step_ids: set[UUID] = set()

    # Log workflow execution start
    logging.info(
        f"Starting parallel execution of workflow '{workflow_definition.workflow_metadata.workflow_name}' ({workflow_id})"
    )

    # For parallel execution, we execute in waves based on dependencies
    # Filter out disabled steps entirely - they are skipped, not failed
    remaining_steps = [step for step in workflow_steps if step.enabled]

    while remaining_steps:
        # Find steps with met dependencies
        ready_steps = [
            step
            for step in remaining_steps
            if _dependencies_met(step, completed_step_ids)
        ]

        if not ready_steps:
            # No progress can be made - remaining steps have unmet dependencies
            for step in remaining_steps:
                failed_steps.append(str(step.step_id))
            break

        # Execute ready steps (in parallel conceptually, but we emit actions)
        for step in ready_steps:
            try:
                # Emit action for this step
                action = _create_action_for_step(step, workflow_id)
                all_actions.append(action)

                # Mark as completed
                completed_steps.append(str(step.step_id))
                completed_step_ids.add(step.step_id)

            except ModelOnexError as e:
                # Handle expected ONEX errors
                failed_steps.append(str(step.step_id))
                # Extract error code value safely
                error_code_value: str | None = None
                if e.error_code is not None:
                    error_code_value = (
                        e.error_code.value
                        if hasattr(e.error_code, "value")
                        else str(e.error_code)
                    )
                logging.warning(
                    f"Workflow '{workflow_definition.workflow_metadata.workflow_name}' step '{step.step_name}' ({step.step_id}) failed: {e.message}",
                    extra={"error_code": error_code_value, "context": e.context},
                    exc_info=True,
                )

                if step.error_action == "stop":
                    # Stop entire workflow
                    remaining_steps = []
                    break

            except Exception as e:
                # Broad exception catch justified for workflow orchestration:
                # - Workflow steps execute external code with unknown exception types
                # - Production workflows require resilient error handling
                # - All failures logged with full traceback for debugging
                # - Failed steps tracked; execution continues per error_action config
                failed_steps.append(str(step.step_id))
                logging.exception(
                    f"Workflow '{workflow_definition.workflow_metadata.workflow_name}' step '{step.step_name}' ({step.step_id}) failed with unexpected error: {e}"
                )

                if step.error_action == "stop":
                    # Stop entire workflow
                    remaining_steps = []
                    break

        # Remove processed steps
        remaining_steps = [s for s in remaining_steps if s not in ready_steps]

    status = (
        EnumWorkflowState.COMPLETED if not failed_steps else EnumWorkflowState.FAILED
    )

    return WorkflowExecutionResult(
        workflow_id=workflow_id,
        execution_status=status,
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        actions_emitted=all_actions,
        execution_time_ms=0,
        metadata={
            "execution_mode": "parallel",
            "workflow_name": workflow_definition.workflow_metadata.workflow_name,
        },
    )


async def _execute_batch(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
) -> WorkflowExecutionResult:
    """Execute workflow with batching."""
    # For batch mode, use sequential execution with batching metadata
    result = await _execute_sequential(workflow_definition, workflow_steps, workflow_id)
    result.metadata["execution_mode"] = "batch"
    result.metadata["batch_size"] = len(workflow_steps)
    return result


def _create_action_for_step(
    step: ModelWorkflowStep,
    workflow_id: UUID,
) -> ModelAction:
    """
    Create action for workflow step.

    Args:
        step: Workflow step to create action for
        workflow_id: Parent workflow ID

    Returns:
        ModelAction for step execution
    """
    # Map step type to action type
    action_type_map = {
        "compute": EnumActionType.COMPUTE,
        "effect": EnumActionType.EFFECT,
        "reducer": EnumActionType.REDUCE,
        "orchestrator": EnumActionType.ORCHESTRATE,
        "custom": EnumActionType.CUSTOM,
    }

    action_type = action_type_map.get(step.step_type, EnumActionType.CUSTOM)

    # Determine target node type from step type
    target_node_type_map = {
        "compute": "NodeCompute",
        "effect": "NodeEffect",
        "reducer": "NodeReducer",
        "orchestrator": "NodeOrchestrator",
        "custom": "NodeCustom",
    }
    target_node_type = target_node_type_map.get(step.step_type, "NodeCustom")

    # Cap priority to ModelAction's max value of 10
    # ModelWorkflowStep allows 1-1000, but ModelAction only allows 1-10
    action_priority = min(step.priority, 10) if step.priority else 1

    return ModelAction(
        action_id=uuid4(),
        action_type=action_type,
        target_node_type=target_node_type,
        payload={
            "workflow_id": str(workflow_id),
            "step_id": str(step.step_id),
            "step_name": step.step_name,
        },
        dependencies=step.depends_on,
        priority=action_priority,
        timeout_ms=step.timeout_ms,
        lease_id=uuid4(),
        epoch=0,
        retry_count=step.retry_count,
        metadata={
            "step_name": step.step_name,
            "correlation_id": str(step.correlation_id),
        },
        created_at=datetime.now(),
    )


def _dependencies_met(
    step: ModelWorkflowStep,
    completed_step_ids: set[UUID],
) -> bool:
    """Check if all step dependencies are met."""
    return all(dep_id in completed_step_ids for dep_id in step.depends_on)


def _get_topological_order(
    workflow_steps: list[ModelWorkflowStep],
) -> list[UUID]:
    """
    Get topological ordering of steps based on dependencies.

    Uses Kahn's algorithm for topological sorting.

    Args:
        workflow_steps: Workflow steps to order

    Returns:
        List of step IDs in topological order
    """
    # Build adjacency list and in-degree map
    step_ids = {step.step_id for step in workflow_steps}
    edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}
    in_degree: dict[UUID, int] = {step_id: 0 for step_id in step_ids}

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id in step_ids:
                edges[dep_id].append(step.step_id)
                in_degree[step.step_id] += 1

    # Kahn's algorithm
    queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
    result: list[UUID] = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for neighbor in edges.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


def _has_dependency_cycles(
    workflow_steps: list[ModelWorkflowStep],
) -> bool:
    """
    Check if workflow contains dependency cycles.

    Uses DFS-based cycle detection.

    Args:
        workflow_steps: Workflow steps to check

    Returns:
        True if cycles detected, False otherwise
    """
    # Build adjacency list
    step_ids = {step.step_id for step in workflow_steps}
    edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id in step_ids:
                # Note: dependency is reversed - we go FROM dependent TO dependency
                edges[step.step_id].append(dep_id)

    # DFS-based cycle detection
    visited: set[UUID] = set()
    rec_stack: set[UUID] = set()

    def has_cycle_dfs(node: UUID) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in edges.get(node, []):
            if neighbor not in visited:
                if has_cycle_dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for step_id in step_ids:
        if step_id not in visited:
            if has_cycle_dfs(step_id):
                return True

    return False


# Public API
__all__ = [
    "WorkflowExecutionResult",
    "execute_workflow",
    "get_execution_order",
    "validate_workflow_definition",
]
