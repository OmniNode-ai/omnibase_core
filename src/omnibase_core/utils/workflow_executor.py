"""
Workflow execution utilities for declarative orchestration.

Pure functions for executing workflows from ModelWorkflowDefinition.
No side effects - returns results and actions.

Typing: Strongly typed with strategic Any usage where runtime flexibility required.

Priority Clamping (Step Priority vs Action Priority):
    ModelWorkflowStep.priority allows 1-1000 for authoring-time flexibility, enabling
    fine-grained ordering hints when defining workflows. However, ModelAction.priority
    is constrained to 1-10 for execution-time scheduling by target nodes.

    This clamping is by design:
    - Step priority (1-1000): Authoring-time hint for workflow authors to express
      relative importance and ordering preferences among steps in the same wave.
    - Action priority (1-10): Execution-time constraint that target nodes use for
      scheduling decisions during actual workflow execution.

    The conversion rule is: action_priority = min(step.priority, 10)

    This is EXPECTED behavior, not an error condition. No warnings are emitted.

    See Also:
        - ModelAction.priority constraint: models/orchestrator/model_action.py
        - Architecture rationale: docs/architecture/CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md
          (Section: "Step Priority vs Action Priority")

Size Limits:
    To prevent memory exhaustion, this module enforces the following limits:
    - MAX_WORKFLOW_STEPS (default 1000): Maximum number of steps in a workflow.
      Validated during workflow validation; raises ModelOnexError if exceeded.
    - MAX_STEP_PAYLOAD_SIZE_BYTES (default 64KB): Maximum size of individual step payload.
      Validated during action creation; raises ModelOnexError if exceeded.
    - MAX_TOTAL_PAYLOAD_SIZE_BYTES (default 10MB): Maximum accumulated payload size.
      In parallel mode, raises ModelOnexError. In sequential mode, treated as
      a step failure (per error_action configuration, defaults to continue).

    These limits are configurable via environment variables for extreme workloads:
    - ONEX_MAX_WORKFLOW_STEPS: Override max workflow steps (bounds: 1-100,000)
    - ONEX_MAX_STEP_PAYLOAD_SIZE_BYTES: Override max step payload size (bounds: 1KB-10MB)
    - ONEX_MAX_TOTAL_PAYLOAD_SIZE_BYTES: Override max total payload size (bounds: 1KB-1GB)

    Invalid environment variable values log a warning and fall back to defaults.
    Bounds are enforced to prevent both DoS attacks (too-small limits causing many
    small workflows) and memory exhaustion (too-large limits).

Security Considerations:
    Compression Attacks:
        The payload size limits (MAX_STEP_PAYLOAD_SIZE_BYTES, MAX_TOTAL_PAYLOAD_SIZE_BYTES)
        are validated on the SERIALIZED JSON payload, not on compressed data. If payloads
        are transmitted compressed (e.g., gzip), they MUST be validated for size AFTER
        decompression but BEFORE processing.

        Risk: A "compression bomb" (also known as a "zip bomb" or "decompression bomb")
        is a small compressed file that expands to a massive size when decompressed.
        Without post-decompression size validation, an attacker could bypass payload
        limits by sending small compressed payloads that expand to memory-exhausting
        sizes, leading to denial-of-service (DoS) conditions.

        Mitigation:
        - Always validate payload size on the decompressed/deserialized data
        - Consider adding streaming decompression with size limits for transport layers
        - The workflow executor validates size on json.dumps() output, which is the
          serialized (uncompressed) representation
        - Transport layers that accept compressed payloads should enforce their own
          decompression limits before passing data to the workflow executor

        Reference: OWASP - Denial of Service through Resource Depletion
        (https://owasp.org/www-community/attacks/Denial_of_Service)
"""

import asyncio
import heapq
import json
import logging
import os
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
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.workflow.execution.model_declarative_workflow_result import (
    ModelDeclarativeWorkflowResult as WorkflowExecutionResult,
)
from omnibase_core.models.workflow.execution.model_declarative_workflow_step_context import (
    ModelDeclarativeWorkflowStepContext as WorkflowStepExecutionContext,
)
from omnibase_core.types.typed_dict_workflow_context import TypedDictWorkflowContext
from omnibase_core.validation.reserved_enum_validator import validate_execution_mode


def _get_limit_from_env(env_var: str, default: int, min_val: int, max_val: int) -> int:
    """Get limit from environment variable with bounds checking.

    Args:
        env_var: Environment variable name
        default: Default value if env var not set
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Validated limit value
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    try:
        int_value = int(value)
        return max(min_val, min(int_value, max_val))
    except ValueError:
        logging.warning(
            f"Invalid value for {env_var}: {value}, using default {default}"
        )
        return default


# Workflow execution limits (OMN-670: Security hardening)
# Configurable via environment variables for extreme workloads
# Bounds prevent both too-small (DoS via many small workflows) and too-large (memory exhaustion) values
MAX_WORKFLOW_STEPS = _get_limit_from_env(
    "ONEX_MAX_WORKFLOW_STEPS", default=1000, min_val=1, max_val=100000
)
MAX_STEP_PAYLOAD_SIZE_BYTES = _get_limit_from_env(
    "ONEX_MAX_STEP_PAYLOAD_SIZE_BYTES",
    default=64 * 1024,
    min_val=1024,
    max_val=10 * 1024 * 1024,
)
MAX_TOTAL_PAYLOAD_SIZE_BYTES = _get_limit_from_env(
    "ONEX_MAX_TOTAL_PAYLOAD_SIZE_BYTES",
    default=10 * 1024 * 1024,
    min_val=1024,
    max_val=1024 * 1024 * 1024,
)


def _log_payload_metrics(
    workflow_id: UUID,
    step_id: UUID,
    step_name: str,
    payload_size: int,
    total_payload_size: int,
) -> None:
    """Log payload size metrics for observability.

    In production, these structured logs can be captured by log aggregators
    (DataDog, Splunk, etc.) and converted to metrics. This approach avoids
    adding external metric dependencies to the core library.

    Args:
        workflow_id: Workflow execution ID
        step_id: Step ID
        step_name: Step name for context
        payload_size: Size of this step's payload in bytes
        total_payload_size: Cumulative payload size for the workflow
    """
    # Only log at DEBUG level to avoid noise in production
    # Structured format enables log-based metrics extraction
    logging.debug(
        "workflow_payload_metrics",
        extra={
            "metric_type": "payload_size",
            "workflow_id": str(workflow_id),
            "step_id": str(step_id),
            "step_name": step_name,
            "payload_size_bytes": payload_size,
            "total_payload_size_bytes": total_payload_size,
            "payload_size_pct_of_limit": round(
                payload_size / MAX_STEP_PAYLOAD_SIZE_BYTES * 100, 2
            ),
            "total_payload_pct_of_limit": round(
                total_payload_size / MAX_TOTAL_PAYLOAD_SIZE_BYTES * 100, 2
            ),
        },
    )


def _log_workflow_completion_metrics(
    workflow_id: UUID,
    workflow_name: str,
    total_payload_size: int,
    step_count: int,
    execution_mode: str,
) -> None:
    """Log workflow completion metrics for observability.

    Summarizes workflow execution with aggregated payload statistics.
    In production, these structured logs can be captured by log aggregators
    (DataDog, Splunk, etc.) and converted to metrics.

    Args:
        workflow_id: Workflow execution ID
        workflow_name: Workflow name for context
        total_payload_size: Total accumulated payload size in bytes
        step_count: Number of steps executed
        execution_mode: Execution mode (sequential, parallel, batch)
    """
    logging.debug(
        "workflow_completion_metrics",
        extra={
            "metric_type": "workflow_complete",
            "workflow_id": str(workflow_id),
            "workflow_name": workflow_name,
            "total_payload_size_bytes": total_payload_size,
            "step_count": step_count,
            "execution_mode": execution_mode,
            "avg_payload_size_bytes": total_payload_size // step_count
            if step_count > 0
            else 0,
            "total_payload_pct_of_limit": round(
                total_payload_size / MAX_TOTAL_PAYLOAD_SIZE_BYTES * 100, 2
            ),
        },
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

    # Compute workflow hash for integrity verification after validation passes
    workflow_hash = _compute_workflow_hash(workflow_definition)

    # Determine execution mode
    mode = execution_mode or _get_execution_mode(workflow_definition)

    # Validate execution mode (reject reserved modes per v1.0 contract)
    validate_execution_mode(mode)

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

    # Add workflow hash to metadata for integrity verification
    result.metadata["workflow_hash"] = workflow_hash

    return result


async def validate_workflow_definition(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
) -> list[str]:
    """
    Validate workflow definition and steps for correctness.

    Pure validation function - no side effects.

    Enforces the following limits (OMN-670: Security hardening):
    - MAX_WORKFLOW_STEPS: Maximum number of steps allowed in a workflow
    - Dependencies must reference existing steps
    - No dependency cycles allowed

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

    # Validate step count limit (OMN-670: Security hardening)
    # SECURITY: Short-circuit immediately on step count overflow to prevent DoS.
    # Without early return, an attacker could submit workflows with millions of steps
    # and the validation would still iterate through all steps for dependency cycle
    # detection and per-step validation, causing CPU exhaustion.
    if len(workflow_steps) > MAX_WORKFLOW_STEPS:
        errors.append(
            f"Workflow exceeds maximum step limit: {len(workflow_steps)} steps > {MAX_WORKFLOW_STEPS} maximum"
        )
        return errors  # DoS mitigation: skip all subsequent expensive validation

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
    """
    Execute workflow steps sequentially.

    Steps are executed one at a time in topological order (respecting dependencies).
    Each step's output is available to subsequent steps via workflow context.

    Args:
        workflow_definition: Workflow definition from YAML contract.
        workflow_steps: List of workflow steps to execute.
        workflow_id: Unique workflow execution ID.

    Returns:
        WorkflowExecutionResult with completed/failed steps and emitted actions.

    Raises:
        ModelOnexError: If workflow validation fails during setup.

    Note:
        Total payload limit violations (MAX_TOTAL_PAYLOAD_SIZE_BYTES) are caught
        by the step error handler and treated as step failures per the step's
        error_action configuration (default: 'continue'). The workflow returns
        FAILED status rather than raising the error. This differs from parallel
        mode, which raises ModelOnexError immediately for payload limit violations.

        Individual step payload limit violations (MAX_STEP_PAYLOAD_SIZE_BYTES) are
        also caught and treated as step failures in the same manner.
    """
    completed_steps: list[str] = []
    failed_steps: list[str] = []
    all_actions: list[ModelAction] = []
    completed_step_ids: set[UUID] = set()
    step_outputs: dict[UUID, object] = {}
    total_payload_size = 0  # Track total payload size (OMN-670: Security hardening)

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
            # Build workflow context from prior step outputs for data flow
            workflow_context = _build_workflow_context(
                workflow_id, completed_step_ids, step_outputs
            )

            # Create context with workflow context for inter-step data access
            context = WorkflowStepExecutionContext(
                step, workflow_id, completed_step_ids, workflow_context
            )

            # Emit action for this step (returns tuple with payload size to avoid
            # redundant JSON serialization - OMN-670: Performance optimization)
            action, action_payload_size = _create_action_for_step(step, workflow_id)
            all_actions.append(action)

            # Track total payload size (OMN-670: Security hardening)
            # Note: action_payload_size comes from _create_action_for_step to avoid
            # redundant json.dumps() call
            total_payload_size += action_payload_size

            # Log payload metrics for observability (OMN-670: Metrics)
            _log_payload_metrics(
                workflow_id=workflow_id,
                step_id=step.step_id,
                step_name=step.step_name,
                payload_size=action_payload_size,
                total_payload_size=total_payload_size,
            )

            if total_payload_size > MAX_TOTAL_PAYLOAD_SIZE_BYTES:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.WORKFLOW_TOTAL_PAYLOAD_EXCEEDED,
                    message=f"Workflow total payload exceeds limit: {total_payload_size} bytes > {MAX_TOTAL_PAYLOAD_SIZE_BYTES} byte limit",
                    context={
                        "workflow_id": str(workflow_id),
                        "total_size": total_payload_size,
                        "limit": MAX_TOTAL_PAYLOAD_SIZE_BYTES,
                    },
                )

            # Mark step as completed
            context.completed_at = datetime.now()
            completed_steps.append(str(step.step_id))
            completed_step_ids.add(step.step_id)

            # Store step output for subsequent steps (action payload serves as output)
            step_outputs[step.step_id] = action.payload

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

    # Log workflow completion metrics (OMN-670: Metrics)
    _log_workflow_completion_metrics(
        workflow_id=workflow_id,
        workflow_name=workflow_definition.workflow_metadata.workflow_name,
        total_payload_size=total_payload_size,
        step_count=len(completed_steps),
        execution_mode="sequential",
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
    """
    Execute workflow steps in parallel (respecting dependencies).

    Steps are executed in waves based on dependency order. Within each wave,
    all steps with met dependencies run concurrently via asyncio.gather.
    Steps in the same wave cannot see each other's outputs (they run in parallel),
    but can access outputs from prior waves via workflow context.

    Args:
        workflow_definition: Workflow definition from YAML contract.
        workflow_steps: List of workflow steps to execute.
        workflow_id: Unique workflow execution ID.

    Returns:
        WorkflowExecutionResult with completed/failed steps and emitted actions.

    Raises:
        ModelOnexError: If workflow validation fails during setup, or if total
            payload limit (MAX_TOTAL_PAYLOAD_SIZE_BYTES) is exceeded. Unlike
            sequential mode, payload limit violations in parallel mode fail
            the entire workflow immediately after all wave steps complete,
            raising ModelOnexError rather than treating it as a step failure.

    Note:
        The error handling behavior differs from sequential mode:
        - Sequential mode: Payload limit violations are caught and treated as
          step failures per error_action configuration (workflow returns FAILED).
        - Parallel mode: Payload limit violations raise ModelOnexError immediately
          after the current wave completes (error propagates to caller).

        This difference exists because parallel execution processes all steps in a
        wave simultaneously, making per-step error handling less meaningful when
        the aggregate payload exceeds the limit.

        Individual step errors (including MAX_STEP_PAYLOAD_SIZE_BYTES violations)
        are still handled per-step and respect the error_action configuration.
    """
    completed_steps: list[str] = []
    failed_steps: list[str] = []
    all_actions: list[ModelAction] = []
    completed_step_ids: set[UUID] = set()
    step_outputs: dict[UUID, object] = {}
    should_stop = False
    total_payload_size = 0  # Track total payload size (OMN-670: Security hardening)

    # Log workflow execution start
    logging.info(
        f"Starting parallel execution of workflow '{workflow_definition.workflow_metadata.workflow_name}' ({workflow_id})"
    )

    async def execute_step(
        step: ModelWorkflowStep,
        wave_context: TypedDictWorkflowContext,
    ) -> tuple[ModelWorkflowStep, ModelAction | None, int, Exception | None]:
        """
        Execute a single workflow step asynchronously.

        Inner async function designed for parallel execution via asyncio.gather.
        Returns a tuple pattern that enables safe error handling in concurrent
        contexts without raising exceptions that would cancel sibling tasks.

        Args:
            step: The workflow step to execute, containing step metadata,
                configuration, and dependency information.
            wave_context: Workflow context with outputs from prior waves,
                enabling data flow between steps across wave boundaries.

        Returns:
            A 4-tuple of (step, action, payload_size, error) where:
            - step: The original ModelWorkflowStep (always present for correlation)
            - action: ModelAction if execution succeeded, None if failed
            - payload_size: Size in bytes of the JSON payload (0 if failed)
            - error: Exception if execution failed, None if succeeded

            Exactly one of action/error will be None (mutually exclusive).
            This tuple pattern allows the caller to process results from
            asyncio.gather without individual try/except blocks per task.

            The payload_size is returned to avoid redundant JSON serialization
            in the caller (OMN-670: Performance optimization).

        Note:
            This function catches all exceptions and returns them in the tuple
            rather than re-raising. This is intentional for parallel execution:
            - Prevents one failing step from canceling other parallel steps
            - Allows batch processing of all results after gather completes
            - Caller is responsible for logging and handling returned errors
            - wave_context provides read-only access to prior wave outputs
        """
        try:
            # Create step execution context with workflow context for data access
            # TODO(OMN-656): Use _context for step execution logic that needs prior outputs.
            # Currently scaffolded for future use cases:
            # - Accessing prior wave outputs via _context.workflow_context
            # - Tracking step timing via _context.started_at/_context.completed_at
            # - Error context via _context.error
            # The sequential execution path uses context.completed_at; parallel path
            # will need similar integration when step execution becomes more complex.
            _context = WorkflowStepExecutionContext(
                step, workflow_id, completed_step_ids, wave_context
            )

            # Create action for this step (returns tuple with payload size to avoid
            # redundant JSON serialization - OMN-670: Performance optimization)
            action, payload_size = _create_action_for_step(step, workflow_id)
            return (step, action, payload_size, None)
        except Exception as e:  # fallback-ok: parallel execution returns error in tuple for caller handling
            return (step, None, 0, e)

    # For parallel execution, we execute in waves based on dependencies
    # Filter out disabled steps entirely - they are skipped, not failed
    remaining_steps = [step for step in workflow_steps if step.enabled]

    while remaining_steps and not should_stop:
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

        # Build workflow context for this wave from prior wave outputs
        # Steps in the same wave cannot see each other's outputs (they run in parallel)
        wave_context = _build_workflow_context(
            workflow_id, completed_step_ids, step_outputs
        )

        # Execute all ready steps in parallel using asyncio.gather
        tasks = [
            asyncio.create_task(execute_step(step, wave_context))
            for step in ready_steps
        ]
        results = await asyncio.gather(*tasks)

        # Process results from parallel execution
        for step, action, action_payload_size, error in results:
            if error is None and action is not None:
                # Step succeeded - check payload size BEFORE marking completed
                # Track total payload size (OMN-670: Security hardening)
                # Note: action_payload_size comes from _create_action_for_step via execute_step
                # to avoid redundant json.dumps() call (OMN-670: Performance optimization)
                total_payload_size += action_payload_size

                # Log payload metrics for observability (OMN-670: Metrics)
                _log_payload_metrics(
                    workflow_id=workflow_id,
                    step_id=step.step_id,
                    step_name=step.step_name,
                    payload_size=action_payload_size,
                    total_payload_size=total_payload_size,
                )

                if total_payload_size > MAX_TOTAL_PAYLOAD_SIZE_BYTES:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.WORKFLOW_TOTAL_PAYLOAD_EXCEEDED,
                        message=f"Workflow total payload exceeds limit: {total_payload_size} bytes > {MAX_TOTAL_PAYLOAD_SIZE_BYTES} byte limit",
                        context={
                            "workflow_id": str(workflow_id),
                            "total_size": total_payload_size,
                            "limit": MAX_TOTAL_PAYLOAD_SIZE_BYTES,
                        },
                    )

                # Payload size check passed - now mark step completed
                all_actions.append(action)
                completed_steps.append(str(step.step_id))
                completed_step_ids.add(step.step_id)
                # Store step output for subsequent waves (action payload serves as output)
                step_outputs[step.step_id] = action.payload
            else:
                # Step failed
                failed_steps.append(str(step.step_id))

                if isinstance(error, ModelOnexError):
                    # Handle expected ONEX errors
                    error_code_value: str | None = None
                    if error.error_code is not None:
                        error_code_value = (
                            error.error_code.value
                            if hasattr(error.error_code, "value")
                            else str(error.error_code)
                        )
                    logging.warning(
                        f"Workflow '{workflow_definition.workflow_metadata.workflow_name}' step '{step.step_name}' ({step.step_id}) failed: {error.message}",
                        extra={
                            "error_code": error_code_value,
                            "context": error.context,
                        },
                        exc_info=True,
                    )
                else:
                    # Broad exception catch justified for workflow orchestration:
                    # - Workflow steps execute external code with unknown exception types
                    # - Production workflows require resilient error handling
                    # - All failures logged with full traceback for debugging
                    # - Failed steps tracked; execution continues per error_action config
                    logging.exception(
                        f"Workflow '{workflow_definition.workflow_metadata.workflow_name}' step '{step.step_name}' ({step.step_id}) failed with unexpected error: {error}"
                    )

                if step.error_action == "stop":
                    # Stop entire workflow after processing current wave
                    should_stop = True

        # Remove processed steps
        remaining_steps = [s for s in remaining_steps if s not in ready_steps]

    status = (
        EnumWorkflowState.COMPLETED if not failed_steps else EnumWorkflowState.FAILED
    )

    # Log workflow completion metrics (OMN-670: Metrics)
    _log_workflow_completion_metrics(
        workflow_id=workflow_id,
        workflow_name=workflow_definition.workflow_metadata.workflow_name,
        total_payload_size=total_payload_size,
        step_count=len(completed_steps),
        execution_mode="parallel",
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
    """
    Execute workflow with batching.

    Delegates to sequential execution internally, adding batch-specific metadata.
    Error handling behavior follows sequential mode semantics.

    Args:
        workflow_definition: Workflow definition from YAML contract.
        workflow_steps: List of workflow steps to execute.
        workflow_id: Unique workflow execution ID.

    Returns:
        WorkflowExecutionResult with batch metadata (execution_mode='batch', batch_size).

    Raises:
        ModelOnexError: If workflow validation fails during setup.

    Note:
        Since batch mode uses sequential execution internally, payload limit
        violations (MAX_TOTAL_PAYLOAD_SIZE_BYTES) are handled as step failures
        per the step's error_action configuration, not raised as exceptions.
        See _execute_sequential for detailed error handling semantics.
    """
    # For batch mode, use sequential execution with batching metadata
    result = await _execute_sequential(workflow_definition, workflow_steps, workflow_id)
    result.metadata["execution_mode"] = "batch"
    result.metadata["batch_size"] = len(workflow_steps)
    return result


def _build_workflow_context(
    workflow_id: UUID,
    completed_step_ids: set[UUID],
    step_outputs: dict[UUID, object],
) -> TypedDictWorkflowContext:
    """
    Build workflow execution context for subsequent steps.

    Aggregates outputs from completed steps and provides workflow-level
    metadata for step execution context. This context is passed to steps
    during sequential/parallel execution to enable data flow between steps.

    Args:
        workflow_id: Unique workflow execution ID
        completed_step_ids: Set of step IDs that have completed successfully
        step_outputs: Dict mapping step IDs to their outputs

    Returns:
        TypedDictWorkflowContext with workflow metadata and step outputs containing:
        - workflow_id: String representation of workflow ID
        - completed_steps: List of completed step IDs as strings
        - step_outputs: Dict of step outputs keyed by step ID strings
        - step_count: Number of completed steps

    Example:
        Build context for a step that depends on previous outputs::

            from uuid import uuid4

            workflow_id = uuid4()
            step1_id = uuid4()
            step2_id = uuid4()

            # After step1 and step2 complete
            completed_step_ids = {step1_id, step2_id}
            step_outputs = {
                step1_id: {"data": [1, 2, 3]},
                step2_id: {"processed": True},
            }

            # Build context for step3
            context = _build_workflow_context(
                workflow_id=workflow_id,
                completed_step_ids=completed_step_ids,
                step_outputs=step_outputs,
            )

            # context contains:
            # {
            #     "workflow_uuid_str": "<workflow UUID as string>",
            #     "completed_steps": ["<step1 UUID>", "<step2 UUID>"],
            #     "step_outputs": {
            #         "<step1 UUID>": {"data": [1, 2, 3]},
            #         "<step2 UUID>": {"processed": True},
            #     },
            #     "step_count": 2,
            # }
    """
    # Convert step IDs to strings for JSON compatibility
    completed_steps_list = [str(step_id) for step_id in completed_step_ids]

    # Convert step outputs dict keys to strings for JSON compatibility
    outputs_with_str_keys: dict[str, object] = {
        str(step_id): output for step_id, output in step_outputs.items()
    }

    return TypedDictWorkflowContext(
        workflow_uuid_str=str(workflow_id),
        completed_steps=completed_steps_list,
        step_outputs=outputs_with_str_keys,
        step_count=len(completed_step_ids),
    )


def _json_default_for_workflow(obj: object) -> str:
    """
    Custom JSON default handler for workflow payloads.

    Only allows specific types commonly used in workflows:
    - UUID: Serialized to string representation
    - datetime: Serialized to ISO format string

    All other non-JSON-native types raise TypeError to catch programming errors.

    Args:
        obj: The object to serialize

    Returns:
        String representation for allowed types

    Raises:
        TypeError: For unsupported types (caught by json.dumps)
    """
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    # error-ok: TypeError is required by json.dumps default= contract
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _validate_json_payload(
    payload: dict[str, object], context: str = "", *, strict: bool = False
) -> None:
    """
    Validate that payload is JSON-serializable.

    Ensures payloads can be safely transmitted over event systems and stored
    in JSON-based persistence layers. Called during action creation to fail
    fast if payload contains non-serializable objects.

    Serialization Behavior:
        By default (strict=False), allows common workflow types (UUID, datetime)
        to be serialized automatically. This is the recommended mode for workflow
        payloads where these types are common.

        In strict mode (strict=True), no default serializer is used. Only native
        JSON types (dict, list, str, int, float, bool, None) are accepted. Use
        strict mode when you need to ensure the payload contains only primitive types.

        Note: Other non-JSON types (lambdas, custom objects, etc.) will fail
        validation in both modes, which is the desired behavior to catch
        programming errors early.

    Used by:
        _create_action_for_step: Validates action payloads before ModelAction creation

    Args:
        payload: The payload dict to validate
        context: Optional context for error messages (e.g., step name)
        strict: If True, use strict JSON validation (no default serializer).
                If False (default), allow UUID/datetime via custom handler.

    Raises:
        ModelOnexError: If payload is not JSON-serializable

    Example:
        Validate a payload before action creation::

            from uuid import uuid4
            from datetime import datetime

            # With strict=False (default), UUIDs and datetimes are allowed
            payload = {
                "workflow_id": uuid4(),  # UUID object - serialized via str()
                "timestamp": datetime.now(),  # datetime - serialized to ISO format
                "step_name": "process_data",
            }
            _validate_json_payload(payload, context="process_data")  # passes

            # With strict=True, only native JSON types allowed
            strict_payload = {
                "workflow_id": str(uuid4()),  # Must be string
                "step_name": "process_data",
            }
            _validate_json_payload(strict_payload, context="strict_step", strict=True)

            # This will raise ModelOnexError in both modes
            invalid_payload = {"lambda": lambda x: x}  # Not JSON-serializable
            _validate_json_payload(invalid_payload, context="bad_step")
    """
    try:
        if strict:
            json.dumps(payload)
        else:
            # Use custom handler for UUID/datetime, reject all other non-JSON types
            json.dumps(payload, default=_json_default_for_workflow)
    except (TypeError, ValueError) as e:
        context_suffix = f" for step '{context}'" if context else ""
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Payload is not JSON-serializable{context_suffix}: {e}",
            context={"payload_keys": list(payload.keys()), "step_context": context},
        ) from e


def _create_action_for_step(
    step: ModelWorkflowStep,
    workflow_id: UUID,
) -> tuple[ModelAction, int]:
    """
    Create action for workflow step.

    Enforces payload size limit (OMN-670: Security hardening):
    - MAX_STEP_PAYLOAD_SIZE_BYTES: Maximum size of individual step payload

    Args:
        step: Workflow step to create action for
        workflow_id: Parent workflow ID

    Returns:
        Tuple of (ModelAction, payload_size_bytes) where payload_size_bytes is
        the UTF-8 encoded size of the JSON payload. This avoids redundant
        serialization in callers that need to track total payload size.

    Raises:
        ModelOnexError: If payload is not JSON-serializable or exceeds size limit
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

    # Priority clamping: step priority (1-1000, authoring-time hint) -> action priority (1-10, execution-time constraint)
    # This is expected schema boundary conversion, not an error. See module docstring and
    # docs/architecture/CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md (Section: "Step Priority vs Action Priority")
    action_priority = min(step.priority, 10) if step.priority else 1

    # Build payload
    payload: dict[str, object] = {
        "workflow_id": str(workflow_id),
        "step_id": str(step.step_id),
        "step_name": step.step_name,
    }

    # Serialize payload once for both validation and size checking (OMN-670: Performance optimization)
    # This replaces the previous two-step approach that called json.dumps() twice
    try:
        payload_json = json.dumps(payload, default=_json_default_for_workflow)
    except (TypeError, ValueError) as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Payload is not JSON-serializable for step '{step.step_name}': {e}",
            context={
                "payload_keys": list(payload.keys()),
                "step_context": step.step_name,
            },
        ) from e

    # Validate payload size (OMN-670: Security hardening)
    payload_bytes = payload_json.encode("utf-8")
    payload_size = len(payload_bytes)
    if payload_size > MAX_STEP_PAYLOAD_SIZE_BYTES:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.WORKFLOW_PAYLOAD_SIZE_EXCEEDED,
            message=f"Step payload exceeds size limit: {payload_size} bytes > {MAX_STEP_PAYLOAD_SIZE_BYTES} byte limit",
            context={
                "step_id": str(step.step_id),
                "step_name": step.step_name,
                "payload_size": payload_size,
                "limit": MAX_STEP_PAYLOAD_SIZE_BYTES,
            },
        )

    # Create typed metadata with step context
    action_metadata = ModelActionMetadata()
    action_metadata.parameters = {
        "step_name": step.step_name,
        "correlation_id": str(step.correlation_id),
    }

    action = ModelAction(
        action_id=uuid4(),
        action_type=action_type,
        target_node_type=target_node_type,
        payload=payload,
        dependencies=step.depends_on,
        priority=action_priority,
        timeout_ms=step.timeout_ms,
        lease_id=uuid4(),
        epoch=0,
        retry_count=step.retry_count,
        metadata=action_metadata,
        created_at=datetime.now(),
    )

    return (action, payload_size)


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

    Uses Kahn's algorithm for topological sorting with priority-aware ordering.
    When multiple steps have zero in-degree (ready to execute), they are ordered by:
    1. Clamped priority (min(priority, 10)) - lower value = higher priority
    2. Declaration order (index in workflow_steps list) - earlier = first

    Args:
        workflow_steps: Workflow steps to order

    Returns:
        List of step IDs in topological order, respecting both dependencies
        and priority/declaration order for steps with equal dependencies.
    """
    # Build step_id to (clamped_priority, declaration_index) mapping for heap ordering.
    # Lower values = higher priority in heap, so we use priority directly.
    # Priority clamping: step priority (1-1000, authoring-time hint) -> clamped (1-10) for consistent
    # ordering with action priority (1-10, execution-time constraint). Default to 1 if None.
    # See: docs/architecture/CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md (Section: "Step Priority vs Action Priority")
    step_order_key: dict[UUID, tuple[int, int]] = {}
    for idx, step in enumerate(workflow_steps):
        clamped_priority = min(step.priority, 10) if step.priority is not None else 1
        step_order_key[step.step_id] = (clamped_priority, idx)

    # Build adjacency list and in-degree map
    step_ids = {step.step_id for step in workflow_steps}
    edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}
    in_degree: dict[UUID, int] = dict.fromkeys(step_ids, 0)

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id in step_ids:
                edges[dep_id].append(step.step_id)
                in_degree[step.step_id] += 1

    # Kahn's algorithm with priority queue for ordering
    # Heap entries: (clamped_priority, declaration_index, step_id)
    # Using tuple comparison: lower priority value first, then lower index first
    heap: list[tuple[int, int, UUID]] = []
    for step_id, degree in in_degree.items():
        if degree == 0:
            priority, idx = step_order_key[step_id]
            heapq.heappush(heap, (priority, idx, step_id))

    result: list[UUID] = []

    while heap:
        _, _, node = heapq.heappop(heap)
        result.append(node)

        for neighbor in edges.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                priority, idx = step_order_key[neighbor]
                heapq.heappush(heap, (priority, idx, neighbor))

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


def _compute_workflow_hash(workflow_definition: ModelWorkflowDefinition) -> str:
    """
    Compute SHA-256 hash of workflow definition for integrity verification.

    Delegates to ModelWorkflowDefinition.compute_workflow_hash() for consistency.
    The model's method excludes the workflow_hash field from computation to:
    - Prevent circular dependency (setting hash doesn't change the hash)
    - Support idempotent hash computation for persistence/caching

    Args:
        workflow_definition: Workflow definition to hash

    Returns:
        Hex string of SHA-256 hash

    Example:
        Compute hash for integrity verification::

            workflow_def = ModelWorkflowDefinition(...)
            hash_value = _compute_workflow_hash(workflow_def)
            # Store hash_value with contract for later verification
    """
    return workflow_definition.compute_workflow_hash()


def verify_workflow_integrity(
    workflow_definition: ModelWorkflowDefinition,
    expected_hash: str | None,
) -> None:
    """
    Verify workflow definition integrity against expected hash.

    Compares computed hash with expected hash to detect tampering.
    If expected_hash is None, verification is skipped to support
    contracts that don't include hash metadata.

    Args:
        workflow_definition: Workflow definition to verify
        expected_hash: Expected hash (if None, skip verification)

    Raises:
        ModelOnexError: If hash mismatch detected (tamper detection)

    Example:
        Verify contract integrity before execution::

            workflow_def = ModelWorkflowDefinition(...)
            stored_hash = "abc123..."  # From contract metadata

            # This will raise if tampered
            verify_workflow_integrity(workflow_def, stored_hash)
    """
    # Skip verification when no expected hash is provided
    if expected_hash is None:
        return

    # Compute actual hash
    actual_hash = _compute_workflow_hash(workflow_definition)

    # Compare hashes
    if actual_hash != expected_hash:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Workflow integrity check failed: hash mismatch detected",
            context={
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "workflow_name": workflow_definition.workflow_metadata.workflow_name,
            },
        )


# Public API
__all__ = [
    "MAX_STEP_PAYLOAD_SIZE_BYTES",
    "MAX_TOTAL_PAYLOAD_SIZE_BYTES",
    "MAX_WORKFLOW_STEPS",
    "WorkflowExecutionResult",
    "execute_workflow",
    "get_execution_order",
    "validate_workflow_definition",
    "verify_workflow_integrity",
]
