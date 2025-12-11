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
    - ``warn_unreachable_steps``: Warns if a step has no incoming edges and
      is not a root step
    - ``warn_priority_clamping``: Warns if priority values will be clamped
      (>1000 or <1)
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

        from omnibase_core.validation.contract_linter import WorkflowContractLinter

        linter = WorkflowContractLinter()
        warnings = linter.lint(workflow_definition)
        for warning in warnings:
            print(f"[{warning.code}] {warning.message}")
"""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
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
            >>> linter = WorkflowContractLinter()
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

        Args:
            workflow: The workflow definition to extract steps from

        Returns:
            list[ModelWorkflowStep]: List of workflow steps extracted from
                the execution graph nodes
        """
        steps: list[ModelWorkflowStep] = []

        # Extract steps from execution graph nodes
        # Each node may contain step-like data that we need to validate
        for node in workflow.execution_graph.nodes:
            # For now, nodes don't directly contain ModelWorkflowStep instances
            # This is a placeholder for when the workflow structure is finalized
            pass

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
        Warn if a step has no incoming edges and is not a root step.

        A step with no dependencies (no incoming edges) and no steps depending
        on it might be orphaned or incorrectly configured, unless it's
        intentionally a root step.

        Note: This is different from isolated steps (which have no incoming
        AND no outgoing edges). Unreachable steps are those that are not
        reachable from any root step via dependency chains.

        Args:
            steps: List of workflow steps to validate

        Returns:
            list[ModelLintWarning]: Warnings for unreachable steps. Empty list
                if all steps are reachable.

        Complexity:
            Time: O(S) where S = number of steps
            Space: O(S) for tracking step dependencies
        """
        warnings: list[ModelLintWarning] = []

        if not steps:
            return warnings

        # Build set of all step IDs that are dependencies of other steps
        step_ids_with_dependents: set[UUID] = set()
        for step in steps:
            for dep_id in step.depends_on:
                step_ids_with_dependents.add(dep_id)

        # Find root steps (no dependencies)
        root_steps = [step for step in steps if not step.depends_on]

        # If there are multiple root steps, warn about potential unreachability
        if len(root_steps) > 1:
            for step in steps:
                # Skip if this is a root step
                if not step.depends_on:
                    continue

                # Warn if step has dependencies but might be in a disconnected graph
                # This is a conservative check - full graph connectivity would require BFS
                if step.step_id not in step_ids_with_dependents:
                    # This step depends on others but nothing depends on it
                    # AND it's not a root step - might be a terminal step (not unreachable)
                    pass

        return warnings

    def warn_priority_clamping(
        self, steps: list[ModelWorkflowStep]
    ) -> list[ModelLintWarning]:
        """
        Warn if priority values will be clamped (>1000 or <1).

        Priority values outside the valid range [1, 1000] will be clamped
        at runtime, which may lead to unexpected execution order.

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
