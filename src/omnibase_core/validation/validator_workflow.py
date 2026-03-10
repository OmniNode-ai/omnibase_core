# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Workflow Validator - Orchestration Module.

This module serves as the public API for workflow validation, re-exporting
all validation functions and classes from the decomposed sub-modules:

- ``validator_workflow_graph``: WorkflowValidator class (DAG validation,
  topological sort, cycle detection, dependency/isolation checks)
- ``validator_workflow_step``: Step-level validation functions
  (execution mode, step type, timeout, unique IDs, disabled step DAG)

Additionally provides ``validate_workflow_definition()`` which orchestrates
full ModelWorkflowDefinition validation across all sub-validators.

OMN-1996: Decomposed from 1269-line monolith into sub-modules.

ONEX Compliance:
    This module follows ONEX v1.0 workflow validation patterns as defined in
    CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md. Reserved execution modes
    (CONDITIONAL, STREAMING) are validated and rejected per the v1.0 contract.

Repository Boundaries (v1.0.5 Informative):
    This module is part of omnibase_core (Core layer) and follows the ONEX
    repository boundary rules:

    SPI -> Core -> Infra (dependency direction)

    - **SPI (Service Provider Interface)**: Parses YAML contracts and generates
      typed Pydantic models (ModelWorkflowDefinition, ModelWorkflowStep). SPI
      parses and preserves reserved fields during contract codegen.

    - **Core (this module)**: Receives fully typed Pydantic models from SPI/Infra.
      Provides validation functions that reject invalid configurations including
      reserved execution modes. Reserved fields are preserved in typed models
      but do not affect validation logic in v1.0.

    - **Infra (Infrastructure)**: Executes workflows using Core utilities.
      Reserved fields are ignored deterministically by the executor.

    Core does NOT parse YAML. Core does NOT coerce dicts into models.
    All models must be fully typed Pydantic instances when passed to validation.

Thread Safety:
    All functions and the WorkflowValidator class in this module are stateless
    and thread-safe. Each method call operates independently on its input
    parameters without maintaining any shared state between calls.
"""

from uuid import UUID

from omnibase_core.constants.constants_field_limits import MAX_DFS_ITERATIONS
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.validation.model_cycle_detection_result import (
    ModelCycleDetectionResult,
)
from omnibase_core.models.validation.model_dependency_validation_result import (
    ModelDependencyValidationResult,
)
from omnibase_core.models.validation.model_isolated_step_result import (
    ModelIsolatedStepResult,
)
from omnibase_core.models.validation.model_unique_name_result import (
    ModelUniqueNameResult,
)
from omnibase_core.models.validation.model_workflow_validation_result import (
    ModelWorkflowValidationResult,
)
from omnibase_core.validation.validator_workflow_constants import (
    MIN_TIMEOUT_MS,
    RESERVED_STEP_TYPES,
)
from omnibase_core.validation.validator_workflow_graph import WorkflowValidator
from omnibase_core.validation.validator_workflow_step import (
    ACCEPTED_EXECUTION_MODES,
    ACCEPTED_STEP_TYPES,
    RESERVED_EXECUTION_MODES,
    validate_dag_with_disabled_steps,
    validate_execution_mode_string,
    validate_step_timeout,
    validate_step_type,
    validate_unique_step_ids,
)

__all__ = [
    "WorkflowValidator",
    # Re-export result models for convenience
    "ModelWorkflowValidationResult",
    "ModelCycleDetectionResult",
    "ModelDependencyValidationResult",
    "ModelIsolatedStepResult",
    "ModelUniqueNameResult",
    # Public validation functions (OMN-655)
    "validate_workflow_definition",
    "validate_unique_step_ids",
    "validate_dag_with_disabled_steps",
    "validate_execution_mode_string",
    "validate_step_type",
    "validate_step_timeout",
    # Constants (defined in this module)
    "RESERVED_EXECUTION_MODES",
    "ACCEPTED_EXECUTION_MODES",
    "ACCEPTED_STEP_TYPES",
    # Re-exported from validator_workflow_constants (canonical source)
    "MAX_DFS_ITERATIONS",
    "RESERVED_STEP_TYPES",
    "MIN_TIMEOUT_MS",
]


# ============================================================================
# Workflow Definition Validation (Orchestration)
# ============================================================================


def validate_workflow_definition(
    workflow: ModelWorkflowDefinition,
) -> ModelWorkflowValidationResult:
    """
    Validate complete workflow definition with comprehensive error detection.

    Performs comprehensive validation of workflow definition including:
    - Structural validation (required fields, metadata)
    - Execution mode validation (reject reserved modes)
    - Step uniqueness validation (duplicate step IDs)
    - DAG validation considering disabled steps
    - Dependency validation
    - Cycle detection

    All errors are returned in a deterministic priority order:
    1. Mode errors (reserved execution modes - raises exception)
    2. Structural errors (missing required fields)
    3. Dependency errors (missing step references)
    4. Cycle errors (circular dependencies)

    Thread Safety:
        This function is stateless and thread-safe. It creates a new
        WorkflowValidator instance for each call and operates only on
        the provided workflow parameter without any shared mutable state.

    Args:
        workflow: The workflow definition to validate. Must be a valid
            ModelWorkflowDefinition instance with metadata and execution graph.

    Returns:
        ModelWorkflowValidationResult: Comprehensive validation result with
            prioritized errors and warnings. The result includes:
            - is_valid: True if all validations pass
            - errors: Deterministically ordered error messages
            - warnings: Non-critical issues (isolated steps, etc.)
            - has_cycles: True if circular dependencies detected
            - topological_order: Valid execution order (if no cycles)
            - missing_dependencies: List of missing dependency IDs
            - isolated_steps: Steps with no incoming/outgoing edges
            - duplicate_names: Duplicate step names (if any)

    Raises:
        ModelOnexError: If execution mode is CONDITIONAL or STREAMING
            (reserved modes not yet implemented). This is raised BEFORE
            returning the validation result.

    Example:
        Basic workflow validation::

            from omnibase_core.validation.validator_workflow import (
                validate_workflow_definition
            )

            result = validate_workflow_definition(workflow_def)
            if not result.is_valid:
                for error in result.errors:
                    print(f"Validation Error: {error}")
            else:
                print("Workflow is valid and ready for execution")

        Handling reserved mode errors::

            try:
                result = validate_workflow_definition(workflow_def)
            except ModelOnexError as e:
                if e.error_code == EnumCoreErrorCode.VALIDATION_ERROR:
                    print(f"Reserved mode error: {e.message}")
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Priority 1: Execution mode validation (raises exception for reserved modes)
    # This is done FIRST because reserved modes should fail fast before any other
    # validation occurs
    validate_execution_mode_string(workflow.workflow_metadata.execution_mode)

    # Priority 2: Structural validation
    if not workflow.workflow_metadata.workflow_name:
        errors.append("Workflow name is required")

    if workflow.workflow_metadata.timeout_ms <= 0:
        errors.append(
            f"Workflow timeout must be positive, got: {workflow.workflow_metadata.timeout_ms}"
        )

    # Check if nodes exist in execution graph
    if not workflow.execution_graph.nodes:
        errors.append("Workflow has no nodes defined in execution graph")
        # Return early - no nodes to validate
        return ModelWorkflowValidationResult(
            is_valid=False,
            has_cycles=False,
            topological_order=[],
            missing_dependencies=[],
            isolated_steps=[],
            duplicate_names=[],
            errors=errors,
            warnings=warnings,
        )

    # Convert ModelWorkflowNode objects to ModelWorkflowStep for validation
    # ModelWorkflowNode has: node_id, node_type, dependencies
    # ModelWorkflowStep needs: step_id, step_name, step_type, depends_on
    steps: list[ModelWorkflowStep] = []
    for node in workflow.execution_graph.nodes:
        # Convert node_type enum to step_type string
        node_type_str = node.node_type.value if node.node_type else "custom"
        # Map node types to valid step types
        step_type_map: dict[str, str] = {
            "compute": "compute",
            "effect": "effect",
            "reducer": "reducer",
            "orchestrator": "orchestrator",
        }
        step_type = step_type_map.get(node_type_str.lower(), "custom")

        step = ModelWorkflowStep(
            step_id=node.node_id,
            step_name=f"node_{node.node_id}",  # Generate name from node_id
            # NOTE(OMN-1302): Step type from dict lookup with fallback. Safe because validated by model.
            step_type=step_type,  # type: ignore[arg-type]
            depends_on=node.dependencies,
            enabled=True,  # ModelWorkflowNode doesn't have enabled field
        )
        steps.append(step)

    # Use WorkflowValidator to perform comprehensive validation
    validator = WorkflowValidator()

    # Priority 3: Dependency validation (missing dependencies)
    dep_result = validator.validate_dependencies(steps)
    if not dep_result.is_valid:
        errors.append(dep_result.error_message)

    # Priority 4: Cycle detection
    cycle_result = validator.detect_cycles(steps)
    if cycle_result.has_cycle:
        errors.append(cycle_result.cycle_description)

    # Additional validation: isolated nodes (as warnings)
    isolated_result = validator.detect_isolated_steps(steps)
    if isolated_result.isolated_steps:
        warnings.append(
            f"Isolated nodes detected: {isolated_result.isolated_step_names}"
        )

    # Compute topological order if no cycles
    # Note: If cycle detection passed, topological_sort should succeed since both
    # use the same underlying graph structure. We remove the defensive try/except
    # as it silently hides potential issues - if topological_sort fails after
    # detect_cycles passes, that indicates a bug in the validator itself.
    topological_order: list[UUID] = []
    if not cycle_result.has_cycle:
        topological_order = validator.topological_sort(steps)

    return ModelWorkflowValidationResult(
        is_valid=len(errors) == 0,
        has_cycles=cycle_result.has_cycle,
        topological_order=topological_order,
        missing_dependencies=dep_result.missing_dependencies,
        isolated_steps=isolated_result.isolated_steps,
        duplicate_names=[],  # Node IDs are UUIDs, no duplicate name check needed
        errors=errors,
        warnings=warnings,
    )
