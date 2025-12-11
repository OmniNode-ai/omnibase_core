"""
Workflow Contract Linter.

Warning-only linter for workflow contracts. This module performs NON-SEMANTIC
validation that produces informational warnings only. It MUST NOT affect
execution or validation.

This linter is designed to catch common workflow definition issues that are
technically valid but may indicate mistakes or suboptimal patterns.

Linting Checks:
    - ``warn_unused_parallel_group``: Warns if parallel_group is set but
      execution_mode is SEQUENTIAL
    - ``warn_duplicate_step_names``: Warns if step_name (not step_id) is
      duplicated across multiple steps
    - ``warn_unreachable_steps``: Warns if a step depends on non-existent
      steps, creating a broken dependency chain
    - ``warn_priority_clamping``: Warns if priority values will be clamped
      (>1000 or <1). Defensive check for bypassed Pydantic validation.
    - ``warn_isolated_steps``: Warns if a step has no incoming AND no
      outgoing edges

Result Model:
    All warnings are returned via ModelLintWarning, which provides:
    - code: Warning code (e.g., "W001")
    - message: Human-readable warning message
    - step_reference: Optional step reference for step-specific warnings
    - severity: Literal["info", "warning"] for categorization

Example:
    Basic usage for workflow linting::

        from omnibase_core.validation.workflow_linter import WorkflowLinter

        linter = WorkflowLinter()
        warnings = linter.lint(workflow_definition)
        for warning in warnings:
            print(f"[{warning.code}] {warning.message}")
"""

from __future__ import annotations

from collections import Counter
from typing import Literal
from uuid import UUID

from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

# Type alias for valid step types
StepTypeLiteral = Literal[
    "compute", "effect", "reducer", "orchestrator", "conditional", "parallel", "custom"
]
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.validation.model_lint_warning import ModelLintWarning

__all__ = ["WorkflowLinter"]


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
    """

    def lint(self, workflow: ModelWorkflowDefinition) -> list[ModelLintWarning]:
        """
        Run all linting checks and return warnings.

        This is the main entry point for workflow linting. It runs all
        linting checks and aggregates warnings into a single list.

        Args:
            workflow: The workflow definition to lint. Must be a valid
                ModelWorkflowDefinition instance.

        Returns:
            list[ModelLintWarning]: List of all warnings detected during linting.
                Empty list if no issues found.

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

        return warnings

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
        """
        steps: list[ModelWorkflowStep] = []

        for node in workflow.execution_graph.nodes:
            # Map node_type to step_type
            # Valid step_types: compute, effect, reducer, orchestrator,
            #                   conditional, parallel, custom
            node_type_value = node.node_type.value.lower()
            step_type_mapping: dict[str, StepTypeLiteral] = {
                "compute_generic": "compute",
                "effect_generic": "effect",
                "reducer_generic": "reducer",
                "orchestrator_generic": "orchestrator",
                "transformer": "compute",
                "aggregator": "compute",
                "function": "compute",
                "model": "compute",
                "tool": "effect",
                "agent": "effect",
                "gateway": "orchestrator",
                "validator": "orchestrator",
                "workflow": "orchestrator",
                "runtime_host_generic": "custom",
                "plugin": "custom",
                "schema": "custom",
                "node": "custom",
                "service": "custom",
                "unknown": "custom",
            }
            step_type: StepTypeLiteral = step_type_mapping.get(
                node_type_value, "custom"
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
            step = ModelWorkflowStep(
                step_id=node.node_id,
                step_name=step_name,
                step_type=step_type,
                depends_on=list(node.dependencies),
                priority=priority,
                parallel_group=parallel_group,
                correlation_id=node.node_id,
                timeout_ms=30000,
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
            Time: O(S) where S = number of steps
            Space: O(U) where U = number of unique step names
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

        Args:
            steps: List of workflow steps to validate

        Returns:
            list[ModelLintWarning]: Warnings for unreachable steps. Empty list
                if all steps are reachable from roots.

        Complexity:
            Time: O(S + E) where S = steps, E = dependency edges
            Space: O(S) for tracking reachable steps and adjacency list
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
        reachable: set[UUID] = set()
        queue: list[UUID] = list(root_step_ids)
        reachable.update(root_step_ids)

        while queue:
            current_id = queue.pop(0)
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
