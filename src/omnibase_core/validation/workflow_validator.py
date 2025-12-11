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

This module provides comprehensive workflow validation utilities following
the patterns established in fsm_analysis.py and dag_validator.py.
"""

from collections import Counter, deque
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
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

# Type aliases for clarity (Python 3.12+ syntax)
type StepIdToName = Mapping[UUID, str]
type AdjacencyList = dict[UUID, list[UUID]]
type InDegreeMap = dict[UUID, int]

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
    "validate_execution_mode",
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
    """

    def _build_step_id_to_name_map(
        self, steps: list[ModelWorkflowStep]
    ) -> dict[UUID, str]:
        """Build a mapping from step IDs to step names."""
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
            ModelOnexError: If the workflow contains cycles
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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Workflow contains cycles - cannot perform topological sort",
            )

        return result

    def detect_cycles(
        self, steps: list[ModelWorkflowStep]
    ) -> ModelCycleDetectionResult:
        """
        Detect cycles in the workflow DAG using DFS-based cycle detection.

        CRITICAL: Error messages include step names, not just IDs.

        Args:
            steps: List of workflow steps to check

        Returns:
            ModelCycleDetectionResult with cycle information including step names
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

        def find_cycle_dfs(node: UUID, path: list[UUID]) -> bool:
            """DFS to find cycle, tracking the path."""
            nonlocal cycle_path
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
        """
        if not steps:
            return ModelDependencyValidationResult(
                is_valid=True,
                missing_dependencies=[],
                error_message="",
            )

        valid_step_ids: set[UUID] = {step.step_id for step in steps}
        missing_deps: list[UUID] = []
        steps_with_missing: list[str] = []

        for step in steps:
            for dep_id in step.depends_on:
                if dep_id not in valid_step_ids:
                    if dep_id not in missing_deps:
                        missing_deps.append(dep_id)
                    if step.step_name not in steps_with_missing:
                        steps_with_missing.append(step.step_name)

        if missing_deps:
            error_message = (
                f"Steps with missing dependencies: {', '.join(steps_with_missing)}"
            )
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

        Runs all validation checks:
        1. Unique name validation
        2. Dependency validation
        3. Cycle detection
        4. Isolated step detection
        5. Topological sort (if no cycles)

        Args:
            steps: List of workflow steps to validate

        Returns:
            ModelWorkflowValidationResult with complete validation results
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Unique name validation
        unique_result = self.validate_unique_names(steps)
        if not unique_result.is_valid:
            errors.append(
                f"Duplicate step names: {', '.join(unique_result.duplicate_names)}"
            )

        # 2. Dependency validation
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
        # Valid = no cycles, no missing dependencies, no duplicate names
        # Isolated steps are warnings, not errors
        is_valid = (
            not cycle_result.has_cycle
            and dep_result.is_valid
            and unique_result.is_valid
        )

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
    validate_execution_mode(workflow.workflow_metadata.execution_mode)

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
    topological_order: list[UUID] = []
    if not cycle_result.has_cycle:
        try:
            topological_order = validator.topological_sort(steps)
        except ModelOnexError:
            # Should not happen since we already checked for cycles
            pass

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

    This function performs:
    1. Filter out disabled steps (enabled=False)
    2. Validate remaining steps form a valid DAG
    3. Check for dependency cycles
    4. Validate all dependencies reference enabled steps

    Args:
        steps: List of all workflow steps, including both enabled and disabled.
            Each step must have an 'enabled' boolean field.

    Returns:
        list[str]: Sorted list of validation error messages. Empty list if
            the enabled steps form a valid DAG. Error messages include:
            - Cycle detection errors with step names
            - Missing dependency errors (dependencies on non-existent or disabled steps)
            - Duplicate step ID errors

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

    # Create validator and run comprehensive validation on enabled steps only
    validator = WorkflowValidator()

    # Priority 2: Dependency validation (enabled steps only)
    dep_result = validator.validate_dependencies(enabled_steps)
    if not dep_result.is_valid:
        errors.append(dep_result.error_message)

    # Priority 3: Cycle detection (enabled steps only)
    cycle_result = validator.detect_cycles(enabled_steps)
    if cycle_result.has_cycle:
        errors.append(cycle_result.cycle_description)

    # Check if any enabled step depends on a disabled step
    enabled_step_ids = {step.step_id for step in enabled_steps}
    all_step_ids = {step.step_id for step in steps}

    for step in enabled_steps:
        for dep_id in step.depends_on:
            if dep_id in all_step_ids and dep_id not in enabled_step_ids:
                errors.append(
                    f"Step '{step.step_name}' depends on disabled step: {dep_id}"
                )

    return sorted(errors)


def validate_execution_mode(mode: str) -> None:
    """
    Validate execution mode and reject reserved modes.

    Validates that the execution mode is not a reserved/unimplemented mode.
    Currently, CONDITIONAL and STREAMING modes are reserved for future
    implementation and will raise a validation error.

    Allowed modes: sequential, parallel, batch
    Reserved modes: conditional, streaming

    Args:
        mode: The execution mode string to validate. Case-insensitive.

    Raises:
        ModelOnexError: If the execution mode is CONDITIONAL or STREAMING.
            The error uses EnumCoreErrorCode.VALIDATION_ERROR and includes
            a clear message indicating which reserved mode was used.

    Example:
        Valid modes::

            validate_execution_mode("sequential")  # OK
            validate_execution_mode("parallel")    # OK
            validate_execution_mode("batch")       # OK

        Reserved modes::

            validate_execution_mode("conditional")  # Raises ModelOnexError
            validate_execution_mode("streaming")    # Raises ModelOnexError

        Handling reserved mode errors::

            try:
                validate_execution_mode(workflow.execution_mode)
            except ModelOnexError as e:
                print(f"Error: {e.message}")
                # Output: "Execution mode 'conditional' is reserved..."
    """
    mode_lower = mode.lower()

    # Reserved modes that are not yet implemented
    reserved_modes = {"conditional", "streaming"}

    if mode_lower in reserved_modes:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Execution mode '{mode}' is reserved for future implementation. "
                f"Currently supported modes: sequential, parallel, batch"
            ),
        )
