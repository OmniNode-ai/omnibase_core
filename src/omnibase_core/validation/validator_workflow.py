"""
Workflow Validator.

Validates workflow DAGs using Kahn's algorithm for topological sorting with:
- Cycle detection with step name reporting
- Missing dependency detection
- Isolated step detection
- Unique step name validation
- Full workflow definition validation
- Reserved execution mode validation
- Disabled step handling in DAG validation
- DAG invariant validation for disabled steps

This module provides comprehensive workflow validation utilities following
the patterns established in validator_fsm_analysis.py and dag_validator.py.

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

Security Considerations:
    Resource Exhaustion Protection:
        The MAX_DFS_ITERATIONS constant (10,000) protects against denial-of-service
        attacks from maliciously crafted workflow graphs. Without this limit, an
        attacker could submit workflows designed to cause infinite loops or excessive
        CPU consumption during cycle detection.

        If cycle detection exceeds MAX_DFS_ITERATIONS, a ModelOnexError is raised
        with detailed context including step_count, max_iterations, and last_node
        for debugging and audit logging.

        The value of 10,000 iterations is calibrated to support legitimate workflows
        with up to ~5,000 steps (worst case: each step visited twice during DFS
        traversal) while providing protection against resource exhaustion attacks.
"""

from collections import Counter, deque
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from uuid import UUID

from omnibase_core.constants.constants_field_limits import MAX_DFS_ITERATIONS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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
from omnibase_core.validation.validator_reserved_enum import validate_execution_mode
from omnibase_core.validation.validator_workflow_constants import (
    MIN_TIMEOUT_MS,
    RESERVED_STEP_TYPES,
)

# Type aliases for clarity (Python 3.12+ syntax)
type StepIdToName = Mapping[UUID, str]
type AdjacencyList = dict[UUID, list[UUID]]
type InDegreeMap = dict[UUID, int]

# =============================================================================
# Module-Level Constants
# =============================================================================

# MAX_DFS_ITERATIONS: Resource exhaustion protection constant for DFS cycle detection.
# Imported from omnibase_core.constants.constants_field_limits (canonical source).
# Re-exported from validator_workflow_constants.py for import path flexibility.
# Prevents malicious or malformed inputs from causing infinite loops in DFS.
# Value of 10,000 supports workflows with up to ~5,000 steps.
# See module docstring "Security Considerations" for full documentation.

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


class WorkflowValidator:
    """
    Validates workflow DAGs using Kahn's algorithm.

    Provides:
    - Topological sorting with Kahn's algorithm
    - Cycle detection with step name reporting
    - Missing dependency validation
    - Isolated step detection
    - Unique step name validation

    Thread Safety:
        This class is stateless and thread-safe. Multiple threads can safely
        use the same instance concurrently since all methods operate only on
        their input parameters without maintaining any shared state.

    ONEX Compliance:
        Implements validation patterns as specified in ONEX v1.0 workflow
        coordination contracts.

    Example:
        Basic usage::

            validator = WorkflowValidator()
            result = validator.validate_workflow(steps)
            if not result.is_valid:
                for error in result.errors:
                    print(f"Error: {error}")
    """

    def _build_step_id_to_name_map(
        self, steps: list[ModelWorkflowStep]
    ) -> dict[UUID, str]:
        """
        Build a mapping from step IDs to step names.

        Args:
            steps: List of workflow steps to process

        Returns:
            dict[UUID, str]: Mapping from step ID to step name

        Complexity:
            Time: O(n) where n = number of steps
            Space: O(n) for the resulting dictionary
        """
        return {step.step_id: step.step_name for step in steps}

    def _build_adjacency_list_and_in_degree(
        self, steps: list[ModelWorkflowStep]
    ) -> tuple[AdjacencyList, InDegreeMap, AbstractSet[UUID]]:
        """
        Build adjacency list and in-degree map for topological sort.

        The adjacency list maps: dependency -> list of dependents
        (i.e., if B depends on A, then edges[A] contains B)

        Args:
            steps: List of workflow steps

        Returns:
            Tuple of (adjacency_list, in_degree_map, step_ids_set)

        Complexity:
            Time: O(V + E) where V = steps and E = total dependency edges
            Space: O(V + E) for adjacency list and in-degree map
        """
        step_ids: set[UUID] = {step.step_id for step in steps}
        edges: AdjacencyList = {step_id: [] for step_id in step_ids}
        in_degree: InDegreeMap = dict.fromkeys(step_ids, 0)

        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in step_ids:
                    # dep_id -> step.step_id (dependency points to dependent)
                    edges[dep_id].append(step.step_id)
                    in_degree[step.step_id] += 1

        return edges, in_degree, step_ids

    def topological_sort(self, steps: list[ModelWorkflowStep]) -> list[UUID]:
        """
        Perform topological sort using Kahn's algorithm.

        Args:
            steps: List of workflow steps to sort

        Returns:
            List of step IDs in valid topological order

        Raises:
            ModelOnexError: If the workflow contains cycles. Error context includes
                step_count, sorted_count, and unsorted_step_ids.

        Complexity:
            Time: O(V + E) where V = number of steps and E = number of edges
            Space: O(V) for queue and result list
        """
        if not steps:
            return []

        edges, in_degree, step_ids = self._build_adjacency_list_and_in_degree(steps)

        # Kahn's algorithm - use deque for O(1) queue operations
        queue: deque[UUID] = deque(
            step_id for step_id, degree in in_degree.items() if degree == 0
        )
        result: list[UUID] = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If result doesn't contain all steps, there's a cycle
        if len(result) != len(step_ids):
            # Find which steps couldn't be sorted (involved in cycles)
            unsorted_ids = step_ids - set(result)
            step_id_to_name = self._build_step_id_to_name_map(steps)
            unsorted_names = [step_id_to_name[sid] for sid in unsorted_ids]
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_CYCLE_DETECTED,
                message=(
                    f"Workflow contains cycles - cannot perform topological sort. "
                    f"Steps involved in cycles: {', '.join(sorted(unsorted_names))}"
                ),
                step_count=len(steps),
                sorted_count=len(result),
                unsorted_step_names=sorted(unsorted_names),
            )

        return result

    def detect_cycles(
        self, steps: list[ModelWorkflowStep]
    ) -> ModelCycleDetectionResult:
        """
        Detect cycles in the workflow DAG using DFS-based cycle detection.

        CRITICAL: Error messages include step names, not just IDs.

        Uses iterative tracking to prevent resource exhaustion from malicious
        or malformed inputs. If iteration count exceeds MAX_DFS_ITERATIONS,
        a ModelOnexError is raised with detailed context.

        Args:
            steps: List of workflow steps to check

        Returns:
            ModelCycleDetectionResult with cycle information including step names

        Raises:
            ModelOnexError: If cycle detection exceeds MAX_DFS_ITERATIONS,
                indicating possible malicious input or malformed workflow.
                Error context includes step_count, max_iterations, and last_node.

        Complexity:
            Time: O(V + E) where V = number of steps and E = number of edges
            Space: O(V) for visited sets and recursion stack
            Protected by MAX_DFS_ITERATIONS (10,000) to prevent resource exhaustion
        """
        if not steps:
            return ModelCycleDetectionResult(
                has_cycle=False,
                cycle_description="",
                cycle_step_ids=[],
            )

        step_id_to_name = self._build_step_id_to_name_map(steps)
        step_ids: set[UUID] = set(step_id_to_name.keys())

        # Build adjacency list: step -> list of its dependencies
        # (i.e., if B depends on A, then edges[B] contains A)
        edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}

        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in step_ids:
                    edges[step.step_id].append(dep_id)

        # DFS-based cycle detection with path tracking
        visited: set[UUID] = set()
        rec_stack: set[UUID] = set()
        cycle_path: list[UUID] = []
        iterations = 0  # Track iterations for resource exhaustion protection

        def find_cycle_dfs(node: UUID, path: list[UUID]) -> bool:
            """DFS to find cycle, tracking the path."""
            nonlocal cycle_path, iterations
            iterations += 1

            # Resource exhaustion protection - prevent malicious/malformed inputs
            if iterations > MAX_DFS_ITERATIONS:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.ORCHESTRATOR_EXEC_ITERATION_LIMIT_EXCEEDED,
                    message=(
                        f"Cycle detection exceeded {MAX_DFS_ITERATIONS} iterations - "
                        "possible malicious input or malformed workflow"
                    ),
                    step_count=len(steps),
                    max_iterations=MAX_DFS_ITERATIONS,
                    last_node=str(node),
                )

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    if find_cycle_dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle - extract the cycle portion
                    cycle_start_idx = path.index(neighbor)
                    cycle_path = path[cycle_start_idx:] + [neighbor]
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for step_id in step_ids:
            if step_id not in visited:
                if find_cycle_dfs(step_id, []):
                    # Build cycle description with step names
                    cycle_names = [step_id_to_name[sid] for sid in cycle_path]
                    cycle_description = "Cycle detected: " + " -> ".join(cycle_names)
                    return ModelCycleDetectionResult(
                        has_cycle=True,
                        cycle_description=cycle_description,
                        cycle_step_ids=list(cycle_path[:-1]),  # Exclude duplicate end
                    )

        return ModelCycleDetectionResult(
            has_cycle=False,
            cycle_description="",
            cycle_step_ids=[],
        )

    def validate_dependencies(
        self, steps: list[ModelWorkflowStep]
    ) -> ModelDependencyValidationResult:
        """
        Validate that all step dependencies exist.

        Args:
            steps: List of workflow steps to validate

        Returns:
            ModelDependencyValidationResult with missing dependency information
            including error_message with step names for debugging

        Complexity:
            Time: O(n * d) where n = steps and d = avg dependencies per step
            Space: O(n) for tracking missing dependencies
        """
        if not steps:
            return ModelDependencyValidationResult(
                is_valid=True,
                missing_dependencies=[],
                error_message="",
            )

        valid_step_ids: set[UUID] = {step.step_id for step in steps}
        missing_deps: list[UUID] = []
        # Track which step has which missing dependencies for detailed error context
        step_to_missing_deps: dict[str, list[str]] = {}

        for step in steps:
            step_missing: list[str] = []
            for dep_id in step.depends_on:
                if dep_id not in valid_step_ids:
                    if dep_id not in missing_deps:
                        missing_deps.append(dep_id)
                    step_missing.append(str(dep_id))
            if step_missing:
                step_to_missing_deps[step.step_name] = step_missing

        if missing_deps:
            # Build detailed error message showing each step and its missing deps
            details = [
                f"'{name}' -> [{', '.join(deps)}]"
                for name, deps in step_to_missing_deps.items()
            ]
            error_message = f"Steps with missing dependencies: {'; '.join(details)}"
            return ModelDependencyValidationResult(
                is_valid=False,
                missing_dependencies=missing_deps,
                error_message=error_message,
            )

        return ModelDependencyValidationResult(
            is_valid=True,
            missing_dependencies=[],
            error_message="",
        )

    def detect_isolated_steps(
        self, steps: list[ModelWorkflowStep]
    ) -> ModelIsolatedStepResult:
        """
        Detect isolated steps (no incoming AND no outgoing edges).

        Single-step workflows are exempt from isolation detection.

        Args:
            steps: List of workflow steps to check

        Returns:
            ModelIsolatedStepResult with isolated step information

        Complexity:
            Time: O(n * d) where n = steps and d = avg dependencies per step
            Space: O(n) for tracking edge connectivity
        """
        # Single-step or empty workflows are exempt
        if len(steps) <= 1:
            return ModelIsolatedStepResult(
                isolated_steps=[],
                isolated_step_names="",
            )

        step_id_to_name = self._build_step_id_to_name_map(steps)
        step_ids: set[UUID] = set(step_id_to_name.keys())

        # Track which steps have incoming or outgoing edges
        has_incoming: set[UUID] = set()
        has_outgoing: set[UUID] = set()

        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in step_ids:
                    # step has incoming edge (depends on dep_id)
                    has_incoming.add(step.step_id)
                    # dep_id has outgoing edge (something depends on it)
                    has_outgoing.add(dep_id)

        # Isolated = no incoming AND no outgoing
        isolated_ids: list[UUID] = []
        isolated_names: list[str] = []

        for step_id in step_ids:
            if step_id not in has_incoming and step_id not in has_outgoing:
                isolated_ids.append(step_id)
                isolated_names.append(step_id_to_name[step_id])

        return ModelIsolatedStepResult(
            isolated_steps=isolated_ids,
            isolated_step_names=", ".join(isolated_names) if isolated_names else "",
        )

    def validate_unique_names(
        self, steps: list[ModelWorkflowStep]
    ) -> ModelUniqueNameResult:
        """
        Validate that all step names are unique.

        Args:
            steps: List of workflow steps to validate

        Returns:
            ModelUniqueNameResult with duplicate name information

        Complexity:
            Time: O(n) for counting names
            Space: O(n) for Counter storage
        """
        if not steps:
            return ModelUniqueNameResult(
                is_valid=True,
                duplicate_names=[],
            )

        name_counts = Counter(step.step_name for step in steps)
        duplicates = [name for name, count in name_counts.items() if count > 1]

        return ModelUniqueNameResult(
            is_valid=len(duplicates) == 0,
            duplicate_names=duplicates,
        )

    def validate_workflow(
        self, steps: list[ModelWorkflowStep]
    ) -> ModelWorkflowValidationResult:
        """
        Perform complete workflow validation.

        v1.0.4 Normative (Fix 44): Errors MUST be in deterministic priority order:
        1. Structural errors (step-structural) - catches basic data issues
        2. Dependency errors (missing step references) - catches reference issues
        3. Graph errors (cycle detection) - catches circular dependencies
        4. Warnings (isolated step detection) - non-blocking issues
        5. Topological sort (if no cycles) - compute execution order

        v1.0.4 Normative (Fix 48): Duplicate step_name values are ALLOWED.
        Only step_id must be unique. step_name duplicates are reported as
        WARNINGS, not errors.

        Note: Unlike validate_workflow_definition(), this method does NOT validate
        execution mode (reserved mode check). Use validate_workflow_definition()
        for complete ModelWorkflowDefinition validation including mode validation.

        Args:
            steps: List of workflow steps to validate

        Returns:
            ModelWorkflowValidationResult with complete validation results including:
            - is_valid: True if no errors (warnings don't affect validity)
            - errors: Ordered list of error messages
            - warnings: Non-critical issues (isolated steps, duplicate names)
            - has_cycles: True if circular dependencies detected
            - topological_order: Valid execution order (empty if cycles)

        Complexity:
            Time: O(V + E) dominated by cycle detection and topological sort
            Space: O(V + E) for adjacency lists and result structures
        """
        errors: list[str] = []
        warnings: list[str] = []

        # v1.0.4 Fix 48: Duplicate step_name is ALLOWED (only step_id must be unique).
        # Duplicate names are now reported as WARNINGS, not errors.
        unique_result = self.validate_unique_names(steps)
        if not unique_result.is_valid:
            warnings.append(
                f"Duplicate step names (allowed per v1.0.4 Fix 48): "
                f"{', '.join(unique_result.duplicate_names)}"
            )

        # v1.0.4 Fix 44: Dependency errors come second in priority order
        dep_result = self.validate_dependencies(steps)
        if not dep_result.is_valid:
            errors.append(dep_result.error_message)

        # 3. Cycle detection
        cycle_result = self.detect_cycles(steps)
        if cycle_result.has_cycle:
            errors.append(cycle_result.cycle_description)

        # 4. Isolated step detection
        isolated_result = self.detect_isolated_steps(steps)
        if isolated_result.isolated_steps:
            warnings.append(
                f"Isolated steps detected: {isolated_result.isolated_step_names}"
            )

        # 5. Topological sort (only if no cycles)
        topological_order: list[UUID] = []
        if not cycle_result.has_cycle:
            try:
                topological_order = self.topological_sort(steps)
            except ModelOnexError as e:
                # Defensive: This should not happen since we already checked for cycles.
                # If it does occur, record it as an unexpected validation error.
                errors.append(f"Unexpected topological sort error: {e.message}")

        # Determine overall validity
        # v1.0.4 Fix 48: Duplicate step_name is ALLOWED (only step_id must be unique).
        # Valid = no cycles, no missing dependencies
        # Isolated steps and duplicate names are warnings, not errors
        is_valid = not cycle_result.has_cycle and dep_result.is_valid

        return ModelWorkflowValidationResult(
            is_valid=is_valid,
            has_cycles=cycle_result.has_cycle,
            topological_order=topological_order,
            missing_dependencies=dep_result.missing_dependencies,
            isolated_steps=isolated_result.isolated_steps,
            duplicate_names=unique_result.duplicate_names,
            errors=errors,
            warnings=warnings,
        )


# ============================================================================
# Public Validation Functions (OMN-655)
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

            from omnibase_core.validation.workflow_validator import (
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
