# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Workflow DAG Graph Validator.

Validates workflow DAGs using Kahn's algorithm for topological sorting with:
- Cycle detection with step name reporting
- Missing dependency detection
- Isolated step detection
- Unique step name validation

``WorkflowValidator`` operates on ``ModelWorkflowStep`` instances to validate
graph structure. Extracted from ``validator_workflow.py`` (OMN-1996).

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
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
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
