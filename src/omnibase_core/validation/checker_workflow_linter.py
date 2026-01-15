"""
Workflow Contract Linter.

Warning-only linter for workflow contracts. This module performs NON-SEMANTIC
validation that produces informational warnings only. It MUST NOT affect
execution or validation.

This linter is designed to catch common workflow definition issues that are
technically valid but may indicate mistakes or suboptimal patterns.

Linting Checks:
    - ``warn_unused_parallel_group`` (W001): Warns if parallel_group is set but
      execution_mode is SEQUENTIAL
    - ``warn_duplicate_step_names`` (W002): Warns if step_name (not step_id) is
      duplicated across multiple steps
    - ``warn_unreachable_steps`` (W003): Warns if a step cannot be reached from
      any root step. This includes steps that depend on non-existent steps
      (broken dependency chain) or steps in disconnected subgraphs.
    - ``warn_priority_clamping`` (W004): Warns if priority values will be clamped
      (>1000 or <1). Defensive check for bypassed Pydantic validation.
    - ``warn_isolated_steps`` (W005): Warns if a step has no incoming AND no
      outgoing edges (completely disconnected from the workflow)

Warning Overlap Notes:
    W003 (unreachable) and W005 (isolated) may both fire for the same step
    when that step has no dependencies AND no dependents. This is intentional:
    - W003 focuses on reachability from roots (graph connectivity)
    - W005 focuses on isolation (no edges at all)
    Both warnings provide complementary diagnostic information.

Result Model:
    All warnings are returned via ModelLintWarning, which provides:
    - code: Warning code (e.g., "W001")
    - message: Human-readable warning message
    - step_reference: Optional step reference for step-specific warnings
    - severity: Literal["info", "warning"] for categorization

Example:
    Basic usage for workflow linting::

        from omnibase_core.validation.checker_workflow_linter import WorkflowLinter

        linter = WorkflowLinter()
        warnings = linter.lint(workflow_definition)
        for warning in warnings:
            print(f"[{warning.code}] {warning.message}")
"""

from __future__ import annotations

from collections import Counter, deque
from typing import Literal, cast
from uuid import UUID

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.constants.constants_field_limits import MAX_BFS_ITERATIONS
from omnibase_core.enums import EnumCoreErrorCode, EnumStepType
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_lint_statistics import ModelLintStatistics
from omnibase_core.models.validation.model_lint_warning import ModelLintWarning

__all__ = [
    "WorkflowLinter",
    "MAX_BFS_ITERATIONS",
    "STEP_TYPE_MAPPING",
]

# Default maximum warnings per code before aggregation
DEFAULT_MAX_WARNINGS_PER_CODE = 10

# MAX_BFS_ITERATIONS is imported from omnibase_core.constants.constants_field_limits
# Re-exported here for API consistency.

# Step type mapping from EnumNodeType values to EnumStepType values
# Extracted to module level to avoid recreating dict for each node during extraction
# Maps node_type.value.lower() strings to valid EnumStepType values
STEP_TYPE_MAPPING: dict[str, EnumStepType] = {
    "compute_generic": EnumStepType.COMPUTE,
    "effect_generic": EnumStepType.EFFECT,
    "reducer_generic": EnumStepType.REDUCER,
    "orchestrator_generic": EnumStepType.ORCHESTRATOR,
    "transformer": EnumStepType.COMPUTE,
    "aggregator": EnumStepType.COMPUTE,
    "function": EnumStepType.COMPUTE,
    "model": EnumStepType.COMPUTE,
    "tool": EnumStepType.EFFECT,
    "agent": EnumStepType.EFFECT,
    "gateway": EnumStepType.ORCHESTRATOR,
    "validator": EnumStepType.ORCHESTRATOR,
    "workflow": EnumStepType.ORCHESTRATOR,
    "runtime_host_generic": EnumStepType.CUSTOM,
    "plugin": EnumStepType.CUSTOM,
    "schema": EnumStepType.CUSTOM,
    "node": EnumStepType.CUSTOM,
    "service": EnumStepType.CUSTOM,
    "unknown": EnumStepType.CUSTOM,
}


class WorkflowLinter:
    """
    Warning-only linter for workflow contracts.

    This linter performs non-semantic validation that produces informational
    warnings only. It MUST NOT affect execution or validation.

    All methods return lists of warnings rather than raising exceptions.
    The workflow remains valid regardless of warnings produced.

    Linting checks are designed to catch common issues like:
    - Unused configuration (parallel_group with sequential execution)
    - Duplicate names (multiple steps with same name)
    - Unreachable steps (steps with no incoming edges and not root steps)
    - Priority clamping (priority values outside valid range)
    - Isolated steps (steps with no connections)

    Warning Aggregation:
        For large workflows, the linter can aggregate warnings to prevent
        output explosion. When enabled (default), warnings are grouped by
        code and only the first N warnings per code are kept, with a summary
        warning indicating how many additional warnings were suppressed.

        Example:
            linter = WorkflowLinter(max_warnings_per_code=5, aggregate_warnings=True)
            warnings = linter.lint(large_workflow)
            # If 20 W001 warnings exist, only 5 are returned plus a summary

    Telemetry:
        Use get_statistics() to obtain telemetry data about a linting run,
        including warning counts by code and severity, timing, and step counts.

    Thread Safety:
        This class is thread-safe. All instance attributes are set during
        __init__ and are read-only thereafter. All methods are stateless
        and do not modify instance state, making concurrent calls from
        multiple threads safe. Each lint() call operates on its own local
        data structures.

    Args:
        max_warnings_per_code: Maximum number of warnings to keep per warning
            code before aggregation. Must be >= 1. Defaults to 10.
        aggregate_warnings: Whether to aggregate warnings when they exceed
            max_warnings_per_code. Defaults to True.

    Raises:
        ModelOnexError: If max_warnings_per_code is less than 1.
    """

    def __init__(
        self,
        max_warnings_per_code: int = DEFAULT_MAX_WARNINGS_PER_CODE,
        aggregate_warnings: bool = True,
    ) -> None:
        """
        Initialize the WorkflowLinter with optional aggregation settings.

        Args:
            max_warnings_per_code: Maximum number of warnings to keep per warning
                code before aggregation. Must be >= 1. Defaults to 10.
            aggregate_warnings: Whether to aggregate warnings when they exceed
                max_warnings_per_code. Defaults to True.

        Raises:
            ModelOnexError: If max_warnings_per_code is less than 1.
        """
        if max_warnings_per_code < 1:
            raise ModelOnexError(
                message=(
                    f"max_warnings_per_code must be >= 1, got {max_warnings_per_code}"
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        self._max_warnings_per_code = max_warnings_per_code
        self._aggregate_warnings = aggregate_warnings

    def lint(self, workflow: ModelWorkflowDefinition) -> list[ModelLintWarning]:
        """
        Run all linting checks and return warnings.

        This is the main entry point for workflow linting. It runs all
        linting checks and aggregates warnings into a single list.

        If warning aggregation is enabled (default), warnings are grouped by
        code and limited to max_warnings_per_code per code, with a summary
        warning for any suppressed warnings.

        Args:
            workflow: The workflow definition to lint. Must be a valid
                ModelWorkflowDefinition instance.

        Returns:
            list[ModelLintWarning]: List of all warnings detected during linting.
                Empty list if no issues found. If aggregation is enabled,
                may include summary warnings for suppressed warnings.

        Example:
            >>> linter = WorkflowLinter()
            >>> warnings = linter.lint(workflow)
            >>> for warning in warnings:
            ...     print(f"[{warning.code}] {warning.message}")
        """
        warnings: list[ModelLintWarning] = []

        # Get steps from execution graph
        steps = self._extract_steps(workflow)

        # Run all linting checks
        warnings.extend(self.warn_unused_parallel_group(workflow, steps))
        warnings.extend(self.warn_duplicate_step_names(steps))
        warnings.extend(self.warn_unreachable_steps(steps))
        warnings.extend(self.warn_priority_clamping(steps))
        warnings.extend(self.warn_isolated_steps(steps))

        # Apply warning aggregation if enabled
        if self._aggregate_warnings:
            warnings = self._aggregate_warnings_by_code(warnings)

        return warnings

    def _aggregate_warnings_by_code(
        self, warnings: list[ModelLintWarning]
    ) -> list[ModelLintWarning]:
        """
        Aggregate warnings by code to prevent output explosion.

        Groups warnings by their code and keeps only the first N warnings
        per code (where N is max_warnings_per_code). For codes that exceed
        the limit, a summary warning is added indicating how many warnings
        were suppressed.

        Severity Inheritance:
            Summary warnings inherit the most severe severity from the
            aggregated group. If ANY warning in the group has severity
            "warning", the summary uses "warning"; otherwise "info" is used.
            This ensures the summary accurately reflects the highest severity
            level of the suppressed warnings.

        Args:
            warnings: List of warnings to aggregate.

        Returns:
            list[ModelLintWarning]: Aggregated warnings with optional summaries.

        Complexity:
            Time: O(W) where W = number of warnings
            Space: O(W) for grouping warnings by code
        """
        if not warnings:
            return warnings

        # Group warnings by code
        warnings_by_code: dict[str, list[ModelLintWarning]] = {}
        for warning in warnings:
            if warning.code not in warnings_by_code:
                warnings_by_code[warning.code] = []
            warnings_by_code[warning.code].append(warning)

        # Build aggregated result
        aggregated: list[ModelLintWarning] = []

        for code in sorted(warnings_by_code.keys()):
            code_warnings = warnings_by_code[code]
            total_count = len(code_warnings)

            # Keep first N warnings
            kept_warnings = code_warnings[: self._max_warnings_per_code]
            aggregated.extend(kept_warnings)

            # Add summary if warnings were suppressed
            suppressed_count = total_count - len(kept_warnings)
            if suppressed_count > 0:
                # Determine severity from the original warnings (use most severe)
                has_warning_severity = any(
                    w.severity == "warning" for w in code_warnings
                )
                summary_severity: Literal["info", "warning"] = (
                    "warning" if has_warning_severity else "info"
                )

                aggregated.append(
                    ModelLintWarning(
                        code=code,
                        message=(
                            f"... and {suppressed_count} more similar warnings "
                            f"({total_count} total)"
                        ),
                        step_reference=None,
                        severity=summary_severity,
                    )
                )

        return aggregated

    def _extract_steps(
        self, workflow: ModelWorkflowDefinition
    ) -> list[ModelWorkflowStep]:
        """
        Extract workflow steps from the workflow definition.

        Converts ModelWorkflowNode objects from the execution graph into
        ModelWorkflowStep objects for linting purposes.

        Args:
            workflow: The workflow definition to extract steps from

        Returns:
            list[ModelWorkflowStep]: List of workflow steps extracted from
                the execution graph nodes. Each node is converted to a step
                with appropriate field mappings.

        Mapping Rules:
            - node_id -> step_id
            - node_type -> step_type (mapped to valid step_type literal)
            - dependencies -> depends_on
            - node_requirements may contain: step_name, priority, parallel_group

        Complexity:
            Time: O(N) where N = number of nodes in the execution graph
            Space: O(N) for the resulting list of steps
        """
        steps: list[ModelWorkflowStep] = []

        for node in workflow.execution_graph.nodes:
            # Map node_type to step_type using module-level constant
            # Valid step_types per v1.0.4: compute, effect, reducer, orchestrator,
            # parallel, custom. Note: "conditional" is reserved for v1.1+.
            # Handle None node_type gracefully - defaults to "custom" step type
            node_type_value = (
                node.node_type.value.lower() if node.node_type else "custom"
            )
            step_type: EnumStepType = STEP_TYPE_MAPPING.get(
                node_type_value, EnumStepType.CUSTOM
            )

            # Extract optional fields from node_requirements
            requirements = node.node_requirements
            step_name = str(requirements.get("step_name", f"node_{node.node_id}"))
            priority_raw = requirements.get("priority", 100)
            priority = (
                int(priority_raw) if isinstance(priority_raw, (int, float)) else 100
            )
            parallel_group_raw = requirements.get("parallel_group")
            parallel_group = (
                str(parallel_group_raw) if parallel_group_raw is not None else None
            )

            # Create ModelWorkflowStep from node data
            # Pydantic will validate and clamp priority values as needed
            # Cast step_type.value to Literal type expected by ModelWorkflowStep
            step_type_literal: Literal[
                "compute", "effect", "reducer", "orchestrator", "parallel", "custom"
            ] = cast(
                Literal[
                    "compute", "effect", "reducer", "orchestrator", "parallel", "custom"
                ],
                step_type.value,
            )
            step = ModelWorkflowStep(
                step_id=node.node_id,
                step_name=step_name,
                step_type=step_type_literal,
                depends_on=list(node.dependencies),
                priority=priority,
                parallel_group=parallel_group,
                correlation_id=node.node_id,
                timeout_ms=TIMEOUT_DEFAULT_MS,
                retry_count=3,
                enabled=True,
                skip_on_failure=False,
                continue_on_error=False,
                error_action="stop",
                max_memory_mb=None,
                max_cpu_percent=None,
                order_index=0,
                max_parallel_instances=1,
            )
            steps.append(step)

        return steps

    def warn_unused_parallel_group(
        self,
        workflow: ModelWorkflowDefinition,
        steps: list[ModelWorkflowStep],
    ) -> list[ModelLintWarning]:
        """
        Warn if parallel_group is set but execution_mode is SEQUENTIAL.

        This indicates a likely configuration mistake where the user has
        configured parallel groups but the workflow is set to sequential
        execution mode.

        Args:
            workflow: The workflow definition to check
            steps: List of workflow steps to validate

        Returns:
            list[ModelLintWarning]: Warnings for steps with unused parallel_group
                configurations. Empty list if no issues found.

        Complexity:
            Time: O(S) where S = number of steps
            Space: O(W) where W = number of warnings (bounded by S)
        """
        warnings: list[ModelLintWarning] = []

        # Check if execution mode is sequential
        execution_mode = workflow.workflow_metadata.execution_mode.lower()
        if execution_mode == "sequential":
            # Check each step for parallel_group configuration
            for step in steps:
                if step.parallel_group is not None:
                    warnings.append(
                        ModelLintWarning(
                            code="W001",
                            message=(
                                f"Step '{step.step_name}' has parallel_group "
                                f"'{step.parallel_group}' but execution_mode is "
                                f"SEQUENTIAL - parallel_group will be ignored"
                            ),
                            step_reference=str(step.step_id),
                            severity="warning",
                        )
                    )

        return warnings

    def warn_duplicate_step_names(
        self, steps: list[ModelWorkflowStep]
    ) -> list[ModelLintWarning]:
        """
        Warn if step_name (not step_id) is duplicated.

        While step_id uniqueness is enforced by UUID, duplicate step names
        can cause confusion and make debugging difficult.

        Args:
            steps: List of workflow steps to validate

        Returns:
            list[ModelLintWarning]: Warnings for duplicate step names. Empty list
                if all step names are unique.

        Complexity:
            Time: O(S) where S = number of steps. Uses collections.Counter which
                iterates once over all step names to build frequency counts in O(S),
                then filters duplicates in O(U) where U <= S.
            Space: O(U) where U = number of unique step names (Counter storage)
        """
        warnings: list[ModelLintWarning] = []

        if not steps:
            return warnings

        # Count occurrences of each step name
        name_counts = Counter(step.step_name for step in steps)
        duplicates = {name for name, count in name_counts.items() if count > 1}

        if duplicates:
            # Group steps by duplicate names
            for name in sorted(duplicates):
                matching_steps = [step for step in steps if step.step_name == name]
                step_ids = [str(step.step_id) for step in matching_steps]

                warnings.append(
                    ModelLintWarning(
                        code="W002",
                        message=(
                            f"Duplicate step name '{name}' found in {len(matching_steps)} "
                            f"steps: {', '.join(step_ids[:3])}"
                            + (
                                f" and {len(step_ids) - 3} more"
                                if len(step_ids) > 3
                                else ""
                            )
                        ),
                        step_reference=None,  # Applies to multiple steps
                        severity="warning",
                    )
                )

        return warnings

    def warn_unreachable_steps(
        self, steps: list[ModelWorkflowStep]
    ) -> list[ModelLintWarning]:
        """
        Warn if a step cannot be reached from any root step.

        This performs a reachability analysis using BFS from all root steps
        (steps with no dependencies). Any step that cannot be reached from
        at least one root step is considered unreachable.

        Note: This is different from isolated steps (which have no incoming
        AND no outgoing edges). Unreachable steps specifically are those that
        depend on steps that don't exist in the workflow, creating a broken
        dependency chain.

        Uses iterative tracking to prevent resource exhaustion from malicious
        or malformed inputs. If iteration count exceeds MAX_BFS_ITERATIONS,
        a ModelOnexError is raised with detailed context.

        Args:
            steps: List of workflow steps to validate

        Returns:
            list[ModelLintWarning]: Warnings for unreachable steps. Empty list
                if all steps are reachable from roots.

        Raises:
            ModelOnexError: If BFS exceeds MAX_BFS_ITERATIONS, indicating
                possible malicious input or malformed workflow. Error context
                includes step_count, max_iterations, and last_node.

        Complexity:
            Time: O(S + E) where S = steps, E = dependency edges
            Space: O(S) for tracking reachable steps and adjacency list
            Protected by MAX_BFS_ITERATIONS (10,000) to prevent resource exhaustion
        """
        warnings: list[ModelLintWarning] = []

        if not steps:
            return warnings

        # Build step lookup and adjacency list for forward traversal
        # step_id -> step for quick lookup
        step_by_id: dict[UUID, ModelWorkflowStep] = {
            step.step_id: step for step in steps
        }
        all_step_ids: set[UUID] = set(step_by_id.keys())

        # Build forward adjacency: step_id -> list of steps that depend on it
        # This allows BFS traversal from roots to descendants
        forward_edges: dict[UUID, list[UUID]] = {
            step_id: [] for step_id in all_step_ids
        }
        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in forward_edges:
                    # dep_id has an outgoing edge to step.step_id
                    forward_edges[dep_id].append(step.step_id)

        # Find root steps (no dependencies at all - truly starting points)
        # A step is a root ONLY if it has no dependencies whatsoever
        # Steps with dependencies on missing steps are NOT roots - they're unreachable
        root_step_ids: set[UUID] = set()
        for step in steps:
            if not step.depends_on:
                # No dependencies at all - this is a true root step
                root_step_ids.add(step.step_id)

        # BFS from all root steps to find reachable steps
        # Using collections.deque for O(1) popleft() - lists use O(n) for pop(0)
        # because they must shift all remaining elements. deque uses a doubly-linked
        # list structure enabling constant-time operations at both ends.
        reachable: set[UUID] = set()
        queue: deque[UUID] = deque(root_step_ids)
        reachable.update(root_step_ids)

        # Track iterations for defensive programming - prevents infinite loops
        # from malicious or malformed inputs (e.g., corrupted adjacency data)
        iterations = 0
        last_node: UUID | None = None

        while queue:
            iterations += 1

            # Resource exhaustion protection - prevent malicious/malformed inputs
            if iterations > MAX_BFS_ITERATIONS:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"BFS reachability analysis exceeded {MAX_BFS_ITERATIONS} "
                        "iterations - possible malicious input or malformed workflow"
                    ),
                    context={
                        "step_count": len(steps),
                        "max_iterations": MAX_BFS_ITERATIONS,
                        "last_node": str(last_node) if last_node else "None",
                    },
                )

            current_id = queue.popleft()
            last_node = current_id
            for next_id in forward_edges.get(current_id, []):
                if next_id not in reachable:
                    reachable.add(next_id)
                    queue.append(next_id)

        # Find unreachable steps (not roots and not reachable from roots)
        for step in steps:
            if step.step_id not in reachable:
                # This step is not reachable from any root
                # Determine why - check if it depends on missing steps
                missing_deps = [d for d in step.depends_on if d not in all_step_ids]
                if missing_deps:
                    warnings.append(
                        ModelLintWarning(
                            code="W003",
                            message=(
                                f"Step '{step.step_name}' is unreachable - it depends on "
                                f"{len(missing_deps)} step(s) not in the workflow: "
                                f"{', '.join(str(d) for d in missing_deps[:3])}"
                                + (
                                    f" and {len(missing_deps) - 3} more"
                                    if len(missing_deps) > 3
                                    else ""
                                )
                            ),
                            step_reference=str(step.step_id),
                            severity="warning",
                        )
                    )
                else:
                    # Unreachable due to being in a disconnected subgraph
                    warnings.append(
                        ModelLintWarning(
                            code="W003",
                            message=(
                                f"Step '{step.step_name}' is unreachable - it is not "
                                f"connected to any root step in the workflow"
                            ),
                            step_reference=str(step.step_id),
                            severity="warning",
                        )
                    )

        return warnings

    def warn_priority_clamping(
        self, steps: list[ModelWorkflowStep]
    ) -> list[ModelLintWarning]:
        """
        Warn if priority values will be clamped (>1000 or <1).

        Priority values outside the valid range [1, 1000] will be clamped
        at runtime, which may lead to unexpected execution order.

        Note:
            This check exists as defensive validation for edge cases where
            Pydantic field constraints (ge=1, le=1000) may be bypassed, such as:

            - Use of model_construct() to skip validation
            - Deserialization from untrusted sources with validate=False
            - Future model changes that relax constraints

            Under normal usage with validated ModelWorkflowStep instances,
            this check will never produce warnings because Pydantic enforces
            priority bounds at model creation time.

        Args:
            steps: List of workflow steps to validate

        Returns:
            list[ModelLintWarning]: Warnings for priority values that will be
                clamped. Empty list if all priorities are in valid range.

        Complexity:
            Time: O(S) where S = number of steps
            Space: O(W) where W = number of warnings (bounded by S)
        """
        warnings: list[ModelLintWarning] = []

        for step in steps:
            if step.priority > 1000:
                warnings.append(
                    ModelLintWarning(
                        code="W004",
                        message=(
                            f"Step '{step.step_name}' has priority {step.priority} "
                            f"which exceeds maximum (1000) - will be clamped to 1000"
                        ),
                        step_reference=str(step.step_id),
                        severity="warning",
                    )
                )
            elif step.priority < 1:
                warnings.append(
                    ModelLintWarning(
                        code="W004",
                        message=(
                            f"Step '{step.step_name}' has priority {step.priority} "
                            f"which is below minimum (1) - will be clamped to 1"
                        ),
                        step_reference=str(step.step_id),
                        severity="warning",
                    )
                )

        return warnings

    def warn_isolated_steps(
        self, steps: list[ModelWorkflowStep]
    ) -> list[ModelLintWarning]:
        """
        Warn if a step has no incoming AND no outgoing edges.

        An isolated step has no dependencies and no steps depending on it,
        which likely indicates a configuration error.

        Single-step workflows are exempt from this check.

        Args:
            steps: List of workflow steps to validate

        Returns:
            list[ModelLintWarning]: Warnings for isolated steps. Empty list if
                no isolated steps found.

        Complexity:
            Time: O(S) where S = number of steps
            Space: O(S) for tracking incoming/outgoing edges
        """
        warnings: list[ModelLintWarning] = []

        # Single-step workflows are exempt
        if len(steps) <= 1:
            return warnings

        # Track which steps have incoming or outgoing edges
        step_ids: set[UUID] = {step.step_id for step in steps}
        has_incoming: set[UUID] = set()
        has_outgoing: set[UUID] = set()

        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in step_ids:
                    # step has incoming edge (depends on dep_id)
                    has_incoming.add(step.step_id)
                    # dep_id has outgoing edge (something depends on it)
                    has_outgoing.add(dep_id)

        # Find isolated steps (no incoming AND no outgoing)
        for step in steps:
            if step.step_id not in has_incoming and step.step_id not in has_outgoing:
                warnings.append(
                    ModelLintWarning(
                        code="W005",
                        message=(
                            f"Step '{step.step_name}' is isolated - it has no "
                            f"dependencies and no steps depend on it"
                        ),
                        step_reference=str(step.step_id),
                        severity="warning",
                    )
                )

        return warnings

    def get_statistics(
        self,
        workflow: ModelWorkflowDefinition,
        warnings: list[ModelLintWarning],
        duration_ms: float,
    ) -> ModelLintStatistics:
        """
        Generate telemetry statistics for a linting run.

        Creates a ModelLintStatistics instance with counts by warning code
        and severity, workflow metrics, and timing information.

        Args:
            workflow: The workflow definition that was linted.
            warnings: List of warnings produced by linting.
            duration_ms: Time taken to lint the workflow in milliseconds.

        Returns:
            ModelLintStatistics: Statistics about the linting run.

        Example:
            >>> import time
            >>> linter = WorkflowLinter()
            >>> start = time.perf_counter()
            >>> warnings = linter.lint(workflow)
            >>> duration = (time.perf_counter() - start) * 1000
            >>> stats = linter.get_statistics(workflow, warnings, duration)
            >>> print(f"Found {stats.total_warnings} warnings in {stats.lint_duration_ms}ms")
        """
        # Count warnings by code
        warnings_by_code: dict[str, int] = {}
        for warning in warnings:
            warnings_by_code[warning.code] = warnings_by_code.get(warning.code, 0) + 1

        # Count warnings by severity
        warnings_by_severity: dict[str, int] = {
            "warning": 0,
            "info": 0,
        }
        for warning in warnings:
            if warning.severity in warnings_by_severity:
                warnings_by_severity[warning.severity] += 1

        # Get step count from execution graph
        step_count = len(workflow.execution_graph.nodes)

        return ModelLintStatistics(
            workflow_name=workflow.workflow_metadata.workflow_name,
            total_warnings=len(warnings),
            warnings_by_code=warnings_by_code,
            warnings_by_severity=warnings_by_severity,
            step_count=step_count,
            lint_duration_ms=duration_ms,
        )
