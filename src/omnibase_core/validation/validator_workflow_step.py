# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Workflow Step-Level Validators.

Provides validation functions for individual workflow steps and step collections:
- Execution mode string validation (reject reserved modes)
- Step type validation (reject reserved types)
- Step timeout validation
- Unique step ID validation
- DAG validation with disabled step handling

Extracted from ``validator_workflow.py`` as part of OMN-1996 decomposition.

ONEX Compliance:
    This module follows ONEX v1.0 workflow validation patterns as defined in
    CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md. Reserved execution modes
    (CONDITIONAL, STREAMING) are validated and rejected per the v1.0 contract.

Thread Safety:
    All functions in this module are stateless and thread-safe. Each function
    operates independently on its input parameters without maintaining any
    shared state between calls.
"""

from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_reserved_enum import validate_execution_mode
from omnibase_core.validation.validator_workflow_constants import (
    MIN_TIMEOUT_MS,
    RESERVED_STEP_TYPES,
)
from omnibase_core.validation.validator_workflow_graph import WorkflowValidator

# Reserved execution modes that are not yet implemented per ONEX v1.0 contract.
# These modes will raise ModelOnexError when used in validate_execution_mode_string.
# Using frozenset for immutability and O(1) membership testing.
RESERVED_EXECUTION_MODES: frozenset[str] = frozenset({"conditional", "streaming"})

# Accepted execution modes that are currently supported.
# Using tuple for immutability and ordered iteration (for consistent error messages).
ACCEPTED_EXECUTION_MODES: tuple[str, ...] = ("sequential", "parallel", "batch")

# Accepted step types that are currently supported in v1.0.
# Using tuple for immutability and ordered iteration.
# NOTE: RESERVED_STEP_TYPES and MIN_TIMEOUT_MS are imported from validator_workflow_constants.
ACCEPTED_STEP_TYPES: tuple[str, ...] = (
    "compute",
    "effect",
    "reducer",
    "orchestrator",
    "parallel",
    "custom",
)

__all__ = [
    "validate_unique_step_ids",
    "validate_dag_with_disabled_steps",
    "validate_execution_mode_string",
    "validate_step_type",
    "validate_step_timeout",
    # Constants (defined in this module)
    "RESERVED_EXECUTION_MODES",
    "ACCEPTED_EXECUTION_MODES",
    "ACCEPTED_STEP_TYPES",
]


def validate_unique_step_ids(steps: list[ModelWorkflowStep]) -> list[str]:
    """
    Detect duplicate step IDs in workflow steps.

    Validates that all step IDs are unique within the workflow. Duplicate
    step IDs create ambiguity and are not allowed.

    Thread Safety:
        This function is stateless and thread-safe. It operates only on
        the provided steps parameter without any shared mutable state.

    Args:
        steps: List of workflow steps to validate. Each step must have a
            valid step_id UUID field.

    Returns:
        list[str]: Sorted list of error messages describing duplicate step IDs.
            Empty list if all step IDs are unique. Each error message includes
            the duplicate UUID and the number of occurrences.

    Complexity:
        Time: O(n) where n = number of steps. We iterate through all steps
            once to count occurrences, then once more to filter duplicates.
        Space: O(n) for the id_counts dictionary storing counts for each
            unique step ID.

    Example:
        >>> from uuid import UUID
        >>> step1 = ModelWorkflowStep(step_id=UUID(...), step_name="step1", ...)
        >>> step2 = ModelWorkflowStep(step_id=UUID(...), step_name="step2", ...)
        >>> step3 = ModelWorkflowStep(step_id=step1.step_id, step_name="step3", ...)
        >>> errors = validate_unique_step_ids([step1, step2, step3])
        >>> print(errors)
        ['Duplicate step_id found 2 times: <uuid>']
    """
    if not steps:
        return []

    # Count occurrences of each step ID
    id_counts: dict[UUID, int] = {}
    for step in steps:
        id_counts[step.step_id] = id_counts.get(step.step_id, 0) + 1

    # Find IDs that appear more than once
    errors: list[str] = []
    for step_id, count in sorted(id_counts.items(), key=lambda x: str(x[0])):
        if count > 1:
            errors.append(f"Duplicate step_id found {count} times: {step_id}")

    return errors


def validate_dag_with_disabled_steps(steps: list[ModelWorkflowStep]) -> list[str]:
    """
    Validate DAG structure considering disabled steps.

    Validates workflow DAG while excluding disabled steps from the graph.
    Disabled steps are filtered out before cycle detection and dependency
    validation, allowing workflows to contain disabled steps without breaking
    the DAG structure.

    This function performs validation in deterministic priority order:
    1. Structural errors: Duplicate step IDs (validate_unique_step_ids)
    2. Disabled dependency errors: Dependencies on disabled steps
    3. Missing dependency errors: Dependencies on non-existent steps
    4. Cycle errors: Circular dependencies in enabled steps

    IMPORTANT: Errors are returned in priority order (not alphabetically sorted).
    This allows callers to address the most fundamental issues first (structural),
    then dependency issues, then graph issues (cycles). Within each priority level,
    errors may be sorted for deterministic output.

    Thread Safety:
        This function is stateless and thread-safe. It creates a new
        WorkflowValidator instance for each call and operates only on
        the provided steps parameter without any shared mutable state.

    Args:
        steps: List of all workflow steps, including both enabled and disabled.
            Each step must have an 'enabled' boolean field.

    Returns:
        list[str]: Priority-ordered list of validation error messages. Empty list
            if the enabled steps form a valid DAG. Error messages include:
            - Priority 1: Duplicate step ID errors (structural)
            - Priority 2: Dependencies on disabled steps
            - Priority 3: Missing dependency errors (references to non-existent steps)
            - Priority 4: Cycle detection errors with step names

    Complexity:
        Time: O(V + E) where V = number of enabled steps and E = number of edges.
            Filtering is O(n), cycle detection is O(V + E), dependency validation
            is O(n).
        Space: O(V) for adjacency lists and visited sets.

    Example:
        Workflow with disabled step that would create cycle::

            from uuid import uuid4
            step1_id = uuid4()
            step2_id = uuid4()
            step3_id = uuid4()

            steps = [
                ModelWorkflowStep(
                    step_id=step1_id,
                    step_name="step1",
                    enabled=True,
                    depends_on=[step2_id],
                ),
                ModelWorkflowStep(
                    step_id=step2_id,
                    step_name="step2",
                    enabled=True,
                    depends_on=[],
                ),
                ModelWorkflowStep(
                    step_id=step3_id,
                    step_name="step3",
                    enabled=False,  # Disabled
                    depends_on=[step1_id],  # Would create cycle if enabled
                ),
            ]

            errors = validate_dag_with_disabled_steps(steps)
            # Returns [] - no errors because step3 is disabled
    """
    if not steps:
        return []

    errors: list[str] = []

    # Priority 1: Check for duplicate step IDs (structural error)
    duplicate_errors = validate_unique_step_ids(steps)
    errors.extend(duplicate_errors)

    # Filter to only enabled steps
    enabled_steps = [step for step in steps if step.enabled]

    # If no enabled steps, nothing to validate
    if not enabled_steps:
        return errors

    # Build ID sets for categorizing dependencies
    enabled_step_ids = {step.step_id for step in enabled_steps}
    all_step_ids = {step.step_id for step in steps}
    disabled_step_ids = all_step_ids - enabled_step_ids

    # Priority 2: Check dependencies on disabled steps (before general dep validation)
    # This is separate from "missing" dependencies - disabled deps exist but are not active
    disabled_dep_errors: set[str] = set()  # Use set to prevent duplicates
    for step in enabled_steps:
        for dep_id in step.depends_on:
            if dep_id in disabled_step_ids:
                disabled_dep_errors.add(
                    f"Step '{step.step_name}' depends on disabled step: {dep_id}"
                )
    errors.extend(sorted(disabled_dep_errors))

    # Priority 3: Dependency validation for truly missing dependencies
    # Filter out disabled deps from each step before validation to avoid duplicate errors
    steps_with_filtered_deps: list[ModelWorkflowStep] = []
    for step in enabled_steps:
        filtered_deps = [d for d in step.depends_on if d not in disabled_step_ids]
        # Create new step with filtered dependencies for validation
        # This prevents "missing dependency" errors for deps on disabled steps
        # (which are already reported above as a different error category)
        step_copy = ModelWorkflowStep(
            step_id=step.step_id,
            step_name=step.step_name,
            step_type=step.step_type,
            depends_on=filtered_deps,
            enabled=step.enabled,
        )
        steps_with_filtered_deps.append(step_copy)

    validator = WorkflowValidator()
    dep_result = validator.validate_dependencies(steps_with_filtered_deps)
    if not dep_result.is_valid:
        errors.append(dep_result.error_message)

    # Priority 4: Cycle detection (enabled steps only, with original deps)
    cycle_result = validator.detect_cycles(enabled_steps)
    if cycle_result.has_cycle:
        errors.append(cycle_result.cycle_description)

    # v1.0.1 Fix 20: DAG Invariant for Disabled Steps (Normative)
    # Disabled steps MUST NOT create hidden cycles. The full graph (including
    # disabled steps) MUST remain acyclic. This ensures:
    # - No cycles are revealed when steps are re-enabled
    # - The graph structure is always valid regardless of enabled/disabled state
    # - Workflow definitions are portable and predictable
    full_graph_cycle_result = validator.detect_cycles(steps)
    if full_graph_cycle_result.has_cycle and not cycle_result.has_cycle:
        # Hidden cycle: only visible when including disabled steps
        errors.append(
            f"Hidden cycle involving disabled steps: {full_graph_cycle_result.cycle_description}"
        )

    # Return errors in validation priority order (NOT alphabetically sorted)
    # NOTE: "Priority order" here refers to ERROR CATEGORIES, not step execution
    # priority. Step execution uses declaration order per v1.0.2 Fix 5.
    # Error validation priority ordering is maintained by the append order above:
    # 1. Duplicate step IDs (structural)
    # 2. Dependencies on disabled steps
    # 3. Missing dependencies
    # 4. Cycle detection
    return errors


def validate_execution_mode_string(mode: str) -> None:
    """
    Validate execution mode string and reject reserved modes.

    This function validates raw string execution modes, typically from YAML configs
    or user input. For type-safe validation when you already have an EnumExecutionMode
    instance, use validate_execution_mode (from reserved_enum_validator) instead.

    **When to use which function:**

    - ``validate_execution_mode_string(mode: str)``: Use when parsing YAML configs,
      JSON payloads, or any string-based input where the mode hasn't been converted
      to an enum yet. This is the appropriate choice for ModelWorkflowDefinition
      validation where execution_mode is stored as a string.

    - ``validate_execution_mode(mode: EnumExecutionMode)``: Use when you
      already have a typed EnumExecutionMode value (e.g., from a Pydantic model
      with enum field). Provides compile-time type safety.

    Both functions enforce the same validation rules (reject CONDITIONAL and STREAMING)
    but operate on different input types.

    Allowed modes: sequential, parallel, batch
    Reserved modes: conditional, streaming

    Reserved Mode Rationale:
        CONDITIONAL and STREAMING are reserved for future ONEX versions because they
        require additional infrastructure not yet implemented:

        - **CONDITIONAL**: Requires runtime expression evaluation, branching logic,
          and conditional step skipping based on workflow state. The current
          sequential/parallel/batch modes do not support dynamic flow control.

        - **STREAMING**: Requires continuous data flow handling, backpressure
          management, and stream-oriented step execution. The current implementation
          assumes discrete step boundaries with complete inputs/outputs.

        These modes are defined in the ONEX v1.0 contract as placeholders for
        future capability expansion. See CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md
        for the full specification.

    Thread Safety:
        This function is stateless and thread-safe. It performs only read operations
        on constant data (reserved_modes set) and has no shared mutable state.

    Args:
        mode: The execution mode string to validate. Case-insensitive.

    Raises:
        ModelOnexError: In two cases (two-step validation):
            1. **Step 1 - Unrecognized mode**: If the mode string is not a valid
               EnumExecutionMode value. Error code: VALIDATION_ERROR with
               "Unrecognized execution mode" message. This means the mode is
               completely unknown (e.g., "foobar", "invalid"). Error context includes:
               - mode: The unrecognized mode that was provided
               - reserved_modes: List of reserved mode names
               - accepted_modes: List of accepted mode names

            2. **Step 2 - Reserved mode**: If the execution mode is
               CONDITIONAL or STREAMING (reserved for future ONEX versions).
               These are valid enum values but not accepted in v1.0.
               This step delegates to ``validate_execution_mode`` (from
               ``reserved_enum_validator``) which raises the error.
               Error code: VALIDATION_ERROR with "reserved" message. Error context:
               - mode: The reserved mode value
               - reserved_modes: List of reserved mode names
               - accepted_modes: List of accepted mode names
               - version: The version the mode is reserved for (e.g., "v1.1+", "v1.2+")

    Complexity:
        Time: O(1) - set lookup
        Space: O(1) - constant storage

    See Also:
        validate_execution_mode: Type-safe validation for EnumExecutionMode.
            Located in omnibase_core.validation.reserved_enum_validator.

    Example:
        Valid modes::

            validate_execution_mode_string("sequential")  # OK
            validate_execution_mode_string("parallel")    # OK
            validate_execution_mode_string("batch")       # OK

        Unrecognized mode strings (completely unknown modes)::

            validate_execution_mode_string("foobar")  # Raises "Unrecognized execution mode"
            validate_execution_mode_string("unknown")  # Raises "Unrecognized execution mode"

        Reserved modes (valid enum values but not accepted in v1.0)::

            validate_execution_mode_string("conditional")  # Raises "reserved for v1.1+"
            validate_execution_mode_string("streaming")    # Raises "reserved for v1.2+"

        Handling validation errors::

            try:
                validate_execution_mode_string(workflow.execution_mode)
            except ModelOnexError as e:
                print(f"Error: {e.message}")
                # Output: "Execution mode 'conditional' is reserved..."
    """
    mode_lower = mode.lower()

    # Step 1: Validate that the string is a valid EnumExecutionMode value
    try:
        mode_enum = EnumExecutionMode(mode_lower)
    except ValueError:
        # Unrecognized mode string - not a valid execution mode
        # Note: "Unrecognized" means the mode is not a valid EnumExecutionMode value
        # at all. This is different from "reserved" modes which are valid enum values
        # but not accepted in v1.0.
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_INVALID_EXECUTION_MODE,
            message=(
                f"Unrecognized execution mode '{mode}'. "
                f"Accepted modes: {', '.join(ACCEPTED_EXECUTION_MODES)}. "
                f"Reserved for future versions: {', '.join(sorted(RESERVED_EXECUTION_MODES))}"
            ),
            mode=mode,
            reserved_modes=list(RESERVED_EXECUTION_MODES),
            accepted_modes=list(ACCEPTED_EXECUTION_MODES),
        )

    # Step 2: Delegate to the enum-based validator for reserved mode validation
    # This follows DRY principle - single source of truth for reserved mode logic
    validate_execution_mode(mode_enum)


def validate_step_type(step_type: str, step_name: str = "") -> None:
    """
    Validate step type and reject reserved types.

    Fix 40 (v1.0.3): step_type="conditional" MUST raise ModelOnexError in v1.0.
    Conditional nodes are reserved for v1.1.

    Allowed step types: compute, effect, reducer, orchestrator, parallel, custom
    Reserved step types: conditional

    Thread Safety:
        This function is stateless and thread-safe. It performs only read operations
        on constant data (RESERVED_STEP_TYPES set) and has no shared mutable state.

    Args:
        step_type: The step type string to validate. Case-insensitive.
        step_name: Optional step name for error context.

    Raises:
        ModelOnexError: If the step type is "conditional" (reserved for v1.1).
            Error code: VALIDATION_ERROR with detailed message.
            Error context includes:
            - step_type: The reserved step type that was provided
            - step_name: The step name (if provided)
            - reserved_step_types: List of reserved step type names
            - accepted_step_types: List of accepted step type names

    Complexity:
        Time: O(1) - set lookup
        Space: O(1) - constant storage

    Example:
        Valid step types (v1.0.4: compute, effect, reducer, orchestrator, parallel, custom)::

            validate_step_type("compute", "my_step")       # OK
            validate_step_type("effect", "fetch_data")     # OK
            validate_step_type("reducer", "aggregate")     # OK
            validate_step_type("orchestrator", "workflow") # OK
            validate_step_type("parallel", "batch")        # OK
            validate_step_type("custom", "user_defined")   # OK

        Reserved step types::

            validate_step_type("conditional", "branch_step")
            # Raises ModelOnexError: "step_type 'conditional' is reserved for v1.1"
    """
    step_type_lower = step_type.lower()

    if step_type_lower in RESERVED_STEP_TYPES:
        step_context = f" for step '{step_name}'" if step_name else ""
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_STEP_TYPE,
            message=(
                f"step_type '{step_type}' is reserved for v1.1{step_context}. "
                f"Accepted step types in v1.0: {', '.join(ACCEPTED_STEP_TYPES)}. "
                "Conditional nodes require expression evaluation infrastructure "
                "not yet implemented."
            ),
            step_type=step_type,
            step_name=step_name,
            reserved_step_types=list(RESERVED_STEP_TYPES),
            accepted_step_types=list(ACCEPTED_STEP_TYPES),
        )


def validate_step_timeout(timeout_ms: int, step_name: str = "") -> None:
    """
    Validate step timeout value.

    Fix 38 (v1.0.3): timeout_ms MUST be >= 100 per schema.
    Any value <100 MUST raise ModelOnexError (structural validation).

    Thread Safety:
        This function is stateless and thread-safe.

    Args:
        timeout_ms: The timeout value in milliseconds to validate.
        step_name: Optional step name for error context.

    Raises:
        ModelOnexError: If timeout_ms < MIN_TIMEOUT_MS (100).
            Error code: VALIDATION_ERROR with detailed message.
            Error context includes:
            - timeout_ms: The invalid timeout value
            - step_name: The step name (if provided)
            - minimum_timeout_ms: The minimum allowed value

    Complexity:
        Time: O(1)
        Space: O(1)

    Example:
        Valid timeout values::

            validate_step_timeout(100)    # OK - minimum valid
            validate_step_timeout(30000)  # OK - default value
            validate_step_timeout(300000) # OK - maximum value

        Invalid timeout values::

            validate_step_timeout(0)   # Raises ModelOnexError
            validate_step_timeout(99)  # Raises ModelOnexError
            validate_step_timeout(-1)  # Raises ModelOnexError
    """
    if timeout_ms < MIN_TIMEOUT_MS:
        step_context = f" for step '{step_name}'" if step_name else ""
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
            message=(
                f"timeout_ms value {timeout_ms} is below minimum{step_context}. "
                f"timeout_ms MUST be >= {MIN_TIMEOUT_MS}ms per ONEX v1.0.3 schema."
            ),
            timeout_ms=timeout_ms,
            step_name=step_name,
            minimum_timeout_ms=MIN_TIMEOUT_MS,
        )
