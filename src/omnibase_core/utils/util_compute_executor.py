"""
Pipeline executor for contract-driven NodeCompute v1.0.

This module provides the core pipeline execution logic for contract-driven
compute nodes. It executes transformation pipelines defined in YAML contracts
with abort-on-first-failure semantics, ensuring deterministic and traceable
data processing.

Thread Safety:
    All functions in this module are pure and stateless - safe for concurrent use.
    Each execution operates on its own data and context without modifying shared state.

Pipeline Execution Model:
    - Steps execute sequentially in definition order
    - First failure aborts the entire pipeline
    - Each step's output can be referenced by subsequent steps via path expressions
    - Full execution metrics are captured for observability

Path Expression Syntax (v1.0):
    - $.input: Full input object
    - $.input.<field>: Direct child field of input
    - $.input.<field>.<subfield>: Nested field access
    - $.steps.<step_name>.output: Output from a previous step

Step Types Supported:
    - TRANSFORMATION: Apply a transformation function to data
    - MAPPING: Build output from multiple path expressions
    - VALIDATION: Validate data against schema (v1.0: pass-through)

Example:
    >>> from omnibase_core.utils.util_compute_executor import execute_compute_pipeline
    >>> from omnibase_core.models.compute import ModelComputeExecutionContext
    >>> from uuid import uuid4
    >>>
    >>> context = ModelComputeExecutionContext(operation_id=uuid4())
    >>> result = execute_compute_pipeline(contract, input_data, context)
    >>> if result.success:
    ...     print(f"Pipeline completed in {result.processing_time_ms:.2f}ms")

See Also:
    - omnibase_core.utils.util_compute_transformations: Transformation functions
    - omnibase_core.models.contracts.subcontracts: Contract models
    - omnibase_core.mixins.mixin_compute_execution: Async wrapper mixin
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

import logging
import time
import warnings
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

from pydantic import BaseModel

from omnibase_core.types.typed_dict_mapping_result import MappingResultDict

logger = logging.getLogger(__name__)

# Type alias for pipeline data - can be dict, Pydantic model, or arbitrary object
# Note: `| object` is intentionally kept here (unlike PipelineData in types module)
# because execute_transformation() can return any type (e.g., JSON_PATH extracts
# arbitrary values from nested structures). This local type differs from the
# stricter PipelineData type alias used for documentation purposes.
PipelineDataType = dict[str, object] | BaseModel | object

from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.compute.model_compute_pipeline_result import (
    ModelComputePipelineResult,
)
from omnibase_core.models.compute.model_compute_step_metadata import (
    ModelComputeStepMetadata,
)
from omnibase_core.models.compute.model_compute_step_result import (
    ModelComputeStepResult,
)
from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_compute_transformations import execute_transformation


def _get_error_type(error: ModelOnexError) -> str:
    """
    Extract error type string from ModelOnexError.

    Converts the error code to a string representation suitable for
    inclusion in pipeline results. Handles both enum-based and string
    error codes gracefully.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        error: The ModelOnexError to extract the type from.

    Returns:
        A string representation of the error type. Returns "compute_error"
        if no error code is present.

    Note:
        The default "compute_error" is a generic fallback for pipeline errors.
        In v1.1+, this will be replaced with EnumComputeErrorType.
        See: docs/architecture/CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md
    """
    if error.error_code is None:
        # TODO(OMN-TBD): Replace with EnumComputeErrorType.COMPUTE_ERROR  [NEEDS TICKET]
        # See: docs/architecture/CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md
        return "compute_error"
    if hasattr(error.error_code, "value"):
        return str(error.error_code.value)
    return str(error.error_code)


# Use shared utility for path resolution - consolidates logic from both
# resolve_mapping_path (here) and transform_json_path (compute_transformations.py)
from omnibase_core.utils.util_compute_path_resolver import resolve_pipeline_path


def resolve_mapping_path(
    path: str,
    input_data: PipelineDataType,
    step_results: dict[str, ModelComputeStepResult],
) -> object:
    """
    Resolve a v1.0 mapping path expression to its value.

    Navigates through the pipeline's input data or previous step results
    to extract the value at the specified path. This enables steps to
    reference and combine data from multiple sources.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Supported Path Formats:
        - $.input: Returns the full input object
        - $.input.<field>: Direct child field of input
        - $.input.<field>.<subfield>: Nested field access (unlimited depth)
        - $.steps.<step_name>: Returns the step's output (shorthand, equivalent to .output)
        - $.steps.<step_name>.output: Returns the step's output (explicit form)

    Path Resolution Behavior:
        For input paths ($.input), full nested access is supported to any depth.
        For step paths ($.steps), only the step's output is accessible in v1.0.

        Note: Both `$.steps.<name>` and `$.steps.<name>.output` return the step's
        output value. The shorthand form (`$.steps.<name>`) is provided for
        convenience and is the more common usage pattern. The explicit `.output`
        suffix is supported for clarity and forward compatibility (v1.1+ may
        expose additional step result fields like `.metadata` or `.duration_ms`).

    Private Attribute Security:
        For security reasons, private attributes (those starting with "_") are
        blocked from path traversal when accessing object attributes. This prevents
        exposure of internal implementation details through path expressions.
        Dictionary keys starting with "_" ARE accessible since dictionaries
        represent user data, not internal state.

    Args:
        path: The path expression to resolve. Must start with "$".
        input_data: The original pipeline input (dict, Pydantic model, or object).
        step_results: Dictionary of results from previously executed steps,
            keyed by step name.

    Returns:
        The resolved value. Type depends on the path target.

    Raises:
        ModelOnexError: If the path is invalid or cannot be resolved:
            - VALIDATION_ERROR: Path doesn't start with "$", invalid prefix,
              or attempts to access private attributes
            - OPERATION_FAILED: Key or step not found

    Example:
        >>> step_results = {"normalize": ModelComputeStepResult(..., output="HELLO")}
        >>> # Both forms are equivalent:
        >>> resolve_mapping_path("$.steps.normalize", {}, step_results)
        'HELLO'
        >>> resolve_mapping_path("$.steps.normalize.output", {}, step_results)
        'HELLO'
    """
    # Delegate to shared path resolver utility
    # The resolve_pipeline_path function handles all path formats and returns
    # values compatible with the original resolve_mapping_path behavior
    return resolve_pipeline_path(path, input_data, step_results)


def execute_mapping_step(
    step: ModelComputePipelineStep,
    input_data: PipelineDataType,
    step_results: dict[str, ModelComputeStepResult],
) -> MappingResultDict:
    """
    Execute a mapping step, building output from path expressions.

    Mapping steps allow constructing new data structures by combining
    values from the pipeline input and previous step outputs. Each field
    in the output is populated by resolving a path expression.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        step: The pipeline step configuration containing the mapping definition.
        input_data: The original pipeline input for resolving $.input paths.
        step_results: Results from previously executed steps for resolving $.steps paths.

    Returns:
        A dictionary where keys are the output field names and values are
        the resolved path expressions.

    Raises:
        ModelOnexError: If mapping_config is missing (VALIDATION_ERROR) or
            if any path expression fails to resolve.

    Example:
        >>> # With step configured to map: {"name": "$.input.user.name", "result": "$.steps.transform.output"}
        >>> execute_mapping_step(step, {"user": {"name": "Alice"}}, step_results)
        {"name": "Alice", "result": "TRANSFORMED_VALUE"}
    """
    if step.mapping_config is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="mapping_config required for mapping step",
        )

    result: MappingResultDict = {}
    for output_field, path_expr in step.mapping_config.field_mappings.items():
        result[output_field] = resolve_mapping_path(path_expr, input_data, step_results)

    return result


def execute_validation_step[ValidationT](
    step: ModelComputePipelineStep,
    data: ValidationT,
    schema_registry: (
        Mapping[str, object] | None
    ) = None,  # schema definitions vary; reserved for v1.1
) -> ValidationT:
    """
    Execute a validation step against a schema.

    Validates the input data against a schema reference. In v1.0, this is
    a pass-through operation as full schema validation is deferred to v1.1.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    v1.0 Limitations:
        This implementation currently passes data through without validation.
        Full schema validation with JSON Schema support is planned for v1.1.

    Args:
        step: The pipeline step configuration containing the validation definition.
        data: The data to validate.
        schema_registry: Optional registry of schema definitions (reserved for v1.1).

    Returns:
        The input data, unchanged (v1.0 pass-through behavior).

    Raises:
        ModelOnexError: If validation_config is missing (VALIDATION_ERROR).

    Note:
        A warning is logged when this function is called, as validation is
        not yet implemented. See docs/architecture/NODECOMPUTE_VERSIONING_ROADMAP.md
        for the v1.1 validation implementation plan.
    """
    if step.validation_config is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="validation_config required for validation step",
        )

    # TODO(OMN-TBD): [v1.1] Implement schema validation for validation steps  [NEEDS TICKET]
    # Target: v1.1 release
    # - Integrate with schema registry for schema resolution
    # - Support JSON Schema validation
    # - Add validation error messages with path information
    # See: docs/architecture/NODECOMPUTE_VERSIONING_ROADMAP.md

    # Emit UserWarning for validation steps (Python warnings module deduplicates automatically)
    warnings.warn(
        "Validation steps are pass-through in v1.0. "
        "Schema validation will be implemented in v1.1.",
        UserWarning,
        stacklevel=2,
    )

    # Log debug-level message for each step (for troubleshooting)
    logger.debug(
        "Validation step '%s' using pass-through mode (v1.0)",
        step.step_name,
    )

    # v1.0: Pass through data (schema validation deferred)
    return data


def execute_pipeline_step(
    step: ModelComputePipelineStep,
    current_data: PipelineDataType,
    input_data: PipelineDataType,
    step_results: dict[str, ModelComputeStepResult],
) -> PipelineDataType | MappingResultDict:
    """
    Execute a single pipeline step and return the result.

    Dispatches to the appropriate step handler based on the step type.
    Supports transformation, mapping, and validation step types.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        step: The pipeline step configuration to execute.
        current_data: The current data in the pipeline (output of previous step).
        input_data: The original pipeline input (for mapping step references).
        step_results: Results from previously executed steps.

    Returns:
        The step output. Type depends on the step type:
            - TRANSFORMATION: Transformed data (type depends on transformation)
            - MAPPING: Dictionary of mapped fields
            - VALIDATION: Input data unchanged (v1.0)

    Raises:
        ModelOnexError: If the step type is unknown (OPERATION_FAILED) or
            if required configuration is missing (VALIDATION_ERROR).

    Note:
        If step.enabled is False, returns current_data unchanged.
    """
    if not step.enabled:
        return current_data

    if step.step_type == EnumComputeStepType.TRANSFORMATION:
        if step.transformation_type is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="transformation_type required for transformation step",
            )
        return execute_transformation(
            current_data,
            step.transformation_type,
            step.transformation_config,
        )

    elif step.step_type == EnumComputeStepType.MAPPING:
        return execute_mapping_step(step, input_data, step_results)

    elif step.step_type == EnumComputeStepType.VALIDATION:
        return execute_validation_step(step, current_data)

    else:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Unknown step type: {step.step_type}",
        )


def _execute_pipeline_steps(
    contract: ModelComputeSubcontract,
    input_data: PipelineDataType,
    context: ModelComputeExecutionContext,
    start_time: float,
) -> ModelComputePipelineResult:
    """
    Internal helper that executes pipeline steps without timeout wrapper.

    This function contains the core pipeline execution logic, separated from
    the timeout enforcement to allow clean timeout handling without complex
    exception propagation.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.
        Each invocation operates on its own copy of the data and results.

    Args:
        contract: The compute subcontract defining the pipeline steps.
        input_data: Input data to process (dict, Pydantic model, or JSON-compatible).
        context: Execution context with operation_id and optional correlation_id.
        start_time: The time.perf_counter() value when execution started.

    Returns:
        ModelComputePipelineResult with execution results.

    Note:
        This is an internal function. Use execute_compute_pipeline() for the
        public API with timeout enforcement.
    """
    step_results: dict[str, ModelComputeStepResult] = {}
    steps_executed: list[str] = []
    current_data = input_data

    for step in contract.pipeline:
        if not step.enabled:
            logger.debug(
                "Skipping disabled step '%s' (operation_id=%s, correlation_id=%s)",
                step.step_name,
                context.operation_id,
                context.correlation_id,
            )
            continue

        step_start = time.perf_counter()

        # Log step transition for observability
        logger.debug(
            "Executing step '%s' (type=%s, operation_id=%s, correlation_id=%s)",
            step.step_name,
            step.step_type.value if step.step_type else "unknown",
            context.operation_id,
            context.correlation_id,
        )

        try:
            result_data = execute_pipeline_step(
                step,
                current_data,
                input_data,
                step_results,
            )

            step_duration = (time.perf_counter() - step_start) * 1000

            step_result = ModelComputeStepResult(
                step_name=step.step_name,
                output=result_data,
                success=True,
                metadata=ModelComputeStepMetadata(
                    duration_ms=step_duration,
                    transformation_type=(
                        step.transformation_type.value
                        if step.transformation_type
                        else None
                    ),
                ),
            )

            step_results[step.step_name] = step_result
            steps_executed.append(step.step_name)
            current_data = result_data

            logger.debug(
                "Step '%s' completed successfully (duration_ms=%.2f, operation_id=%s)",
                step.step_name,
                step_duration,
                context.operation_id,
            )

        except ModelOnexError as e:
            step_duration = (time.perf_counter() - step_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000

            # Log structured error for observability
            error_code_str = (
                e.error_code.value
                if e.error_code is not None and hasattr(e.error_code, "value")
                else str(e.error_code)
            )
            logger.warning(
                "Pipeline step '%s' failed: %s (error_code=%s, operation_id=%s, "
                "correlation_id=%s, step_type=%s)",
                step.step_name,
                e.message,
                error_code_str,
                context.operation_id,
                context.correlation_id,
                step.step_type.value if step.step_type else "unknown",
            )

            # Record failed step
            step_result = ModelComputeStepResult(
                step_name=step.step_name,
                output=None,
                success=False,
                metadata=ModelComputeStepMetadata(
                    duration_ms=step_duration,
                    transformation_type=(
                        step.transformation_type.value
                        if step.transformation_type
                        else None
                    ),
                ),
                error_type=_get_error_type(e),
                error_message=e.message,
            )
            step_results[step.step_name] = step_result
            steps_executed.append(step.step_name)

            # Abort pipeline
            return ModelComputePipelineResult(
                success=False,
                output=None,
                processing_time_ms=total_time,
                steps_executed=steps_executed,
                step_results=step_results,
                error_type=_get_error_type(e),
                error_message=e.message,
                error_step=step.step_name,
            )

        # Pipeline error handling: Capture unexpected errors in result object
        # rather than propagating to allow callers to handle failures gracefully.
        # This enables orchestration layers to inspect errors programmatically,
        # implement retry logic, or aggregate partial results from multi-step pipelines.
        # Error is logged via logger.exception for full stack trace observability.
        except Exception as e:  # fallback-ok: pipeline executor captures errors in result object, logged via logger.exception
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            step_duration = (time.perf_counter() - step_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000

            # Log unexpected errors for observability
            # TODO(OMN-TBD): Wire context.correlation_id to structured logging  [NEEDS TICKET]
            # See: docs/architecture/CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md
            logger.exception(
                "Unexpected error in pipeline step '%s': %s (type: %s, "
                "operation_id: %s, correlation_id: %s)",
                step.step_name,
                str(e),
                type(e).__name__,
                context.operation_id,
                context.correlation_id,
            )

            step_result = ModelComputeStepResult(
                step_name=step.step_name,
                output=None,
                success=False,
                metadata=ModelComputeStepMetadata(
                    duration_ms=step_duration,
                    transformation_type=(
                        step.transformation_type.value
                        if step.transformation_type
                        else None
                    ),
                ),
                error_type="unexpected_error",
                error_message=str(e),
            )
            step_results[step.step_name] = step_result
            steps_executed.append(step.step_name)

            return ModelComputePipelineResult(
                success=False,
                output=None,
                processing_time_ms=total_time,
                steps_executed=steps_executed,
                step_results=step_results,
                error_type="unexpected_error",
                error_message=str(e),
                error_step=step.step_name,
            )

    total_time = (time.perf_counter() - start_time) * 1000

    return ModelComputePipelineResult(
        success=True,
        output=current_data,
        processing_time_ms=total_time,
        steps_executed=steps_executed,
        step_results=step_results,
    )


def execute_compute_pipeline(
    contract: ModelComputeSubcontract,
    input_data: PipelineDataType,
    context: ModelComputeExecutionContext,
) -> ModelComputePipelineResult:
    """
    Execute a compute pipeline with abort-on-first-failure semantics and timeout enforcement.

    Processes input data through a series of transformation, mapping, and
    validation steps defined in the contract. Execution stops at the first
    failure or when the pipeline_timeout_ms limit is exceeded, with full
    error context preserved in the result.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.
        Each invocation operates on its own copy of the data and results.

    Execution Model:
        1. Steps are executed in definition order
        2. Disabled steps are skipped
        3. Each step receives the output of the previous step as input
        4. First failure aborts the pipeline immediately
        5. All step results and timing metrics are captured
        6. If pipeline_timeout_ms is specified, execution is terminated when exceeded

    Timeout Enforcement:
        When contract.pipeline_timeout_ms is set (not None), the entire pipeline
        execution is wrapped with a timeout. If the timeout is exceeded:
        - A result with success=False is returned
        - error_type is set to "timeout_exceeded"
        - error_message describes the timeout and configured limit
        - processing_time_ms reflects the actual elapsed time

        Note: Timeout enforcement uses a thread pool executor which may allow
        the underlying computation to continue briefly after timeout. For
        CPU-bound operations, this is generally safe as the result is discarded.

    Error Handling:
        This function never raises exceptions to the caller. All errors (both
        expected ModelOnexError and unexpected exceptions) are captured in the
        result object with success=False. This design enables:
        - Orchestration layers to inspect errors programmatically
        - Retry logic implementation by callers
        - Partial result aggregation from multi-step pipelines
        - Graceful degradation without try/except boilerplate at call sites

        All errors are logged for observability (warning level for ModelOnexError,
        exception level with full stack trace for unexpected errors).

    Args:
        contract: The compute subcontract defining the pipeline steps.
        input_data: Input data to process (dict, Pydantic model, or JSON-compatible).
        context: Execution context with operation_id and optional correlation_id
            for distributed tracing.

    Returns:
        ModelComputePipelineResult containing:
            - success: Whether all steps completed successfully within timeout
            - output: Final pipeline output (from last step), or None on failure/timeout
            - processing_time_ms: Total execution time in milliseconds
            - steps_executed: List of step names that were executed
            - step_results: Dictionary of individual step results
            - error_type, error_message, error_step: Error details on failure

    Example:
        >>> from uuid import uuid4
        >>> context = ModelComputeExecutionContext(
        ...     operation_id=uuid4(),
        ...     correlation_id=uuid4(),
        ... )
        >>> result = execute_compute_pipeline(contract, {"text": "hello"}, context)
        >>> if result.success:
        ...     print(f"Output: {result.output}")
        ...     print(f"Completed in {result.processing_time_ms:.2f}ms")
        ... else:
        ...     print(f"Failed at step '{result.error_step}': {result.error_message}")
    """
    start_time = time.perf_counter()

    # If no timeout is configured, execute directly without wrapper overhead
    if contract.pipeline_timeout_ms is None:
        return _execute_pipeline_steps(contract, input_data, context, start_time)

    # Convert timeout from milliseconds to seconds for concurrent.futures
    timeout_seconds = contract.pipeline_timeout_ms / 1000.0

    # Use ThreadPoolExecutor with timeout enforcement
    # Note: We explicitly manage the executor lifecycle to avoid blocking on cleanup
    # when a timeout occurs. The context manager form would wait for all threads
    # to complete on exit, which defeats the purpose of timeout enforcement.
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            _execute_pipeline_steps, contract, input_data, context, start_time
        )
        # Wait for result with timeout
        return future.result(timeout=timeout_seconds)

    except FuturesTimeoutError:
        # Pipeline exceeded timeout - return failure result
        # Capture elapsed time immediately on timeout detection
        total_time = (time.perf_counter() - start_time) * 1000

        # Log the timeout for observability
        logger.warning(
            "Pipeline execution timed out after %.2fms (limit: %dms, operation_id=%s, "
            "correlation_id=%s, pipeline=%s)",
            total_time,
            contract.pipeline_timeout_ms,
            context.operation_id,
            context.correlation_id,
            contract.operation_name,
        )

        return ModelComputePipelineResult(
            success=False,
            output=None,
            processing_time_ms=total_time,
            steps_executed=[],  # Cannot reliably know which steps completed
            step_results={},  # Cannot access partial results from timed-out thread
            error_type=EnumCoreErrorCode.TIMEOUT_EXCEEDED.value,
            error_message=(
                f"Pipeline execution exceeded timeout of {contract.pipeline_timeout_ms}ms "
                f"(actual: {total_time:.2f}ms)"
            ),
            error_step=None,  # Unknown which step was running when timeout occurred
        )

    finally:
        # Shutdown executor without waiting for pending futures
        # This allows the background thread to continue (and eventually complete)
        # without blocking the caller. The thread will be cleaned up by Python's
        # garbage collection when it completes.
        executor.shutdown(wait=False)


__all__ = [
    "resolve_mapping_path",
    "execute_mapping_step",
    "execute_validation_step",
    "execute_pipeline_step",
    "execute_compute_pipeline",
]
