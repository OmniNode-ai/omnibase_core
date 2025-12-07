"""
Pipeline executor for contract-driven NodeCompute v1.0.

Executes transformation pipelines with abort-on-first-failure semantics.
"""

import time
from typing import Any

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
    """Extract error type string from ModelOnexError.

    Handles both enum and string error codes.
    """
    if error.error_code is None:
        return "transformation_error"
    if hasattr(error.error_code, "value"):
        return str(error.error_code.value)
    return str(error.error_code)


def resolve_mapping_path(
    path: str, input_data: Any, step_results: dict[str, ModelComputeStepResult]
) -> Any:
    """
    Resolve a v1.0 mapping path expression.

    Supported paths:
    - $.input - Full input object
    - $.input.<field> - Direct child field of input
    - $.input.<field>.<subfield> - Nested fields
    - $.steps.<step_name>.output - Full output from a previous step

    Args:
        path: The path expression to resolve
        input_data: The original pipeline input
        step_results: Results from previously executed steps

    Returns:
        The resolved value

    Raises:
        ModelOnexError: If path is invalid or cannot be resolved
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
    input_data: Any,
    step_results: dict[str, ModelComputeStepResult],
) -> Any:
    """Execute a mapping step, building output from path expressions."""
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
    data: Any,
    schema_registry: dict[str, Any] | None = None,
) -> Any:
    """
    Execute a validation step.

    NOTE: v1.0 validation is simplified - it just passes through the data.
    Full schema validation requires schema registry integration (deferred).
    """
    if step.validation_config is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="validation_config required for validation step",
        )

    # v1.0: Pass through data (schema validation deferred)
    # In full implementation, would validate against schema_ref
    return data


def execute_pipeline_step(
    step: ModelComputePipelineStep,
    current_data: Any,
    input_data: Any,
    step_results: dict[str, ModelComputeStepResult],
) -> Any:
    """Execute a single pipeline step and return the result."""
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


def execute_compute_pipeline(
    contract: ModelComputeSubcontract,
    input_data: Any,
    context: ModelComputeExecutionContext,
) -> ModelComputePipelineResult:
    """
    Execute a compute pipeline with abort-on-first-failure semantics.

    Args:
        contract: The compute subcontract defining the pipeline
        input_data: Input data to process
        context: Execution context with operation/correlation IDs

    Returns:
        ModelComputePipelineResult with success status and all step results
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
