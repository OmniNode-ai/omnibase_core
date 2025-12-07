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
    >>> from omnibase_core.utils.compute_executor import execute_compute_pipeline
    >>> from omnibase_core.models.compute import ModelComputeExecutionContext
    >>> from uuid import uuid4
    >>>
    >>> context = ModelComputeExecutionContext(operation_id=uuid4())
    >>> result = execute_compute_pipeline(contract, input_data, context)
    >>> if result.success:
    ...     print(f"Pipeline completed in {result.processing_time_ms:.2f}ms")

See Also:
    - omnibase_core.utils.compute_transformations: Transformation functions
    - omnibase_core.models.contracts.subcontracts: Contract models
    - omnibase_core.mixins.mixin_compute_execution: Async wrapper mixin
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

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
from omnibase_core.models.compute.model_compute_step_result import ModelComputeStepResult
from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.compute_transformations import execute_transformation


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
        A string representation of the error type. Returns "transformation_error"
        if no error code is present.
    """
    if error.error_code is None:
        return "transformation_error"
    if hasattr(error.error_code, "value"):
        return str(error.error_code.value)
    return str(error.error_code)


# TODO(v1.1): Extract path resolution to shared utility - duplicated in compute_transformations.py
# Both resolve_mapping_path and transform_json_path implement similar path traversal logic.
# Refactor to a common _resolve_path utility to reduce duplication and ensure consistent behavior.
def resolve_mapping_path(
    path: str,
    input_data: Any,  # Any: accepts dict, Pydantic models, or other objects with attributes
    step_results: dict[str, ModelComputeStepResult],
) -> Any:  # Any: return type depends on the path being resolved
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
        - $.steps.<step_name>.output: Output from a previously executed step

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
        >>> resolve_mapping_path("$.steps.normalize.output", {}, step_results)
        'HELLO'
    """
    if not path.startswith("$"):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid path: must start with '$', got '{path}'",
        )

    if path == "$.input" or path == "$input":
        return input_data

    if path.startswith("$.input."):
        # Navigate into input data
        remaining = path[8:]  # Remove "$.input."
        parts = remaining.split(".")
        current = input_data

        for part in parts:
            if not part:
                continue
            if isinstance(current, dict):
                if part not in current:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        message=f"Path '{path}' not found: key '{part}' missing in input",
                    )
                current = current[part]
            # Block private attribute access for security
            elif part.startswith("_"):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Cannot access private attribute: '{part}'",
                )
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    message=f"Path '{path}' not found: cannot access '{part}'",
                )
        return current

    if path.startswith("$.steps."):
        # Navigate into step results
        remaining = path[8:]  # Remove "$.steps."
        parts = remaining.split(".", 1)
        step_name = parts[0]

        if step_name not in step_results:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Step '{step_name}' not found in executed steps",
            )

        result = step_results[step_name]

        if len(parts) == 1:
            # Return full step result
            return result.output

        sub_path = parts[1]
        if sub_path == "output":
            return result.output
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid step path: only '.output' supported, got '.{sub_path}'",
            )

    raise ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message=f"Invalid path prefix: '{path}'. Must be '$.input' or '$.steps.<name>'",
    )


def execute_mapping_step(
    step: ModelComputePipelineStep,
    input_data: Any,  # Any: accepts dict, Pydantic models, or other objects with attributes
    step_results: dict[str, ModelComputeStepResult],
) -> dict[str, Any]:  # Returns dict with field mappings; values are Any based on resolved paths
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

    result: dict[str, Any] = {}
    for output_field, path_expr in step.mapping_config.field_mappings.items():
        result[output_field] = resolve_mapping_path(path_expr, input_data, step_results)

    return result


def execute_validation_step(
    step: ModelComputePipelineStep,
    data: Any,  # Any: validation accepts any data type for schema checking
    schema_registry: dict[str, Any] | None = None,  # Any: schema definitions vary in structure
) -> Any:  # Any: returns input unchanged (v1.0 pass-through)
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

    # TODO(v1.1): Implement actual schema validation against schema_ref
    # - Integrate with schema registry for schema resolution
    # - Support JSON Schema validation
    # - Add validation error messages with path information
    # See: docs/architecture/NODECOMPUTE_VERSIONING_ROADMAP.md

    # Log warning that validation is not yet implemented
    logger.warning(
        "Validation step '%s' is using pass-through mode (v1.0). "
        "Schema validation will be implemented in v1.1.",
        step.step_name,
    )

    # v1.0: Pass through data (schema validation deferred)
    return data


def execute_pipeline_step(
    step: ModelComputePipelineStep,
    current_data: Any,  # Any: data flows through pipeline with varying types per step
    input_data: Any,  # Any: original input preserved for mapping step references
    step_results: dict[str, ModelComputeStepResult],
) -> Any:  # Any: output type depends on step_type (transformation, mapping, or validation)
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


# TODO(v1.1): Enforce pipeline_timeout_ms - currently declared in contract but not enforced.
# Add asyncio.timeout or threading.Timer wrapper to abort pipeline if execution exceeds timeout.
# See: docs/architecture/NODECOMPUTE_VERSIONING_ROADMAP.md
def execute_compute_pipeline(
    contract: ModelComputeSubcontract,
    input_data: Any,  # Any: pipeline input can be any JSON-compatible or Pydantic model
    context: ModelComputeExecutionContext,
) -> ModelComputePipelineResult:
    """
    Execute a compute pipeline with abort-on-first-failure semantics.

    Processes input data through a series of transformation, mapping, and
    validation steps defined in the contract. Execution stops at the first
    failure, with full error context preserved in the result.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.
        Each invocation operates on its own copy of the data and results.

    Execution Model:
        1. Steps are executed in definition order
        2. Disabled steps are skipped
        3. Each step receives the output of the previous step as input
        4. First failure aborts the pipeline immediately
        5. All step results and timing metrics are captured

    Args:
        contract: The compute subcontract defining the pipeline steps.
        input_data: Input data to process (dict, Pydantic model, or JSON-compatible).
        context: Execution context with operation_id and optional correlation_id
            for distributed tracing.

    Returns:
        ModelComputePipelineResult containing:
            - success: Whether all steps completed successfully
            - output: Final pipeline output (from last step), or None on failure
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
    step_results: dict[str, ModelComputeStepResult] = {}
    steps_executed: list[str] = []
    current_data = input_data

    for step in contract.pipeline:
        if not step.enabled:
            continue

        step_start = time.perf_counter()

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
                        step.transformation_type.value if step.transformation_type else None
                    ),
                ),
            )

            step_results[step.step_name] = step_result
            steps_executed.append(step.step_name)
            current_data = result_data

        except ModelOnexError as e:
            step_duration = (time.perf_counter() - step_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000

            # Record failed step
            step_result = ModelComputeStepResult(
                step_name=step.step_name,
                output=None,
                success=False,
                metadata=ModelComputeStepMetadata(
                    duration_ms=step_duration,
                    transformation_type=(
                        step.transformation_type.value if step.transformation_type else None
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

        except Exception as e:
            step_duration = (time.perf_counter() - step_start) * 1000
            total_time = (time.perf_counter() - start_time) * 1000

            step_result = ModelComputeStepResult(
                step_name=step.step_name,
                output=None,
                success=False,
                metadata=ModelComputeStepMetadata(
                    duration_ms=step_duration,
                    transformation_type=(
                        step.transformation_type.value if step.transformation_type else None
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


__all__ = [
    "resolve_mapping_path",
    "execute_mapping_step",
    "execute_validation_step",
    "execute_pipeline_step",
    "execute_compute_pipeline",
]
