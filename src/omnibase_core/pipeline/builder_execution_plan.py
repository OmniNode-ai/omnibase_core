# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Runtime plan builder for pipeline execution."""

import heapq
from collections import defaultdict

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.pipeline.exceptions import (
    DependencyCycleError,
    HookTypeMismatchError,
    UnknownDependencyError,
)
from omnibase_core.pipeline.models import (
    ModelExecutionPlan,
    ModelPhaseExecutionPlan,
    ModelPipelineHook,
    ModelValidationWarning,
    PipelinePhase,
)
from omnibase_core.pipeline.registry_hook import RegistryHook

# Phase fail_fast semantics:
# - preflight, before, execute: fail_fast=True (critical phases, abort on first error)
# - after, emit, finalize: fail_fast=False (cleanup/notification phases, collect all errors)
#
# Rationale:
# - preflight: Validation must pass before proceeding
# - before: Setup must succeed before main execution
# - execute: Core logic - first failure should halt further execution
# - after: Cleanup should attempt all hooks even if some fail
# - emit: Event emission should try all hooks (best effort)
# - finalize: Resource cleanup must try all hooks regardless of prior errors
FAIL_FAST_PHASES: frozenset[PipelinePhase] = frozenset({"preflight", "before", "execute"})


class BuilderExecutionPlan:
    """
    Builds execution plans from a frozen RegistryHook.

    The builder performs:
    1. Hook type validation (optional, based on contract_category)
    2. Dependency validation (unknown deps, cycles)
    3. Topological sort with priority tie-breaker (Kahn's algorithm)

    Usage:
        registry = RegistryHook()
        registry.register(hook1)
        registry.register(hook2)
        registry.freeze()

        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()
    """

    def __init__(
        self,
        registry: RegistryHook,
        contract_category: EnumHandlerTypeCategory | None = None,
        enforce_hook_typing: bool = False,
    ) -> None:
        """
        Initialize the BuilderExecutionPlan.

        Args:
            registry: A frozen RegistryHook containing registered hooks.
            contract_category: Optional handler type category from the contract.
                If None, hook type validation is skipped.
            enforce_hook_typing: If True, type mismatches raise errors.
                If False, type mismatches produce warnings.
        """
        self._registry = registry
        self._contract_category = contract_category
        self._enforce_hook_typing = enforce_hook_typing

    def build(self) -> tuple[ModelExecutionPlan, list[ModelValidationWarning]]:
        """
        Build an execution plan from the registry.

        Returns:
            Tuple of (execution_plan, validation_warnings).

        Raises:
            UnknownDependencyError: If a hook references an unknown dependency.
            DependencyCycleError: If dependencies form a cycle.
            HookTypeMismatchError: If enforce_hook_typing=True and type mismatch.
        """
        warnings: list[ModelValidationWarning] = []
        phases: dict[PipelinePhase, ModelPhaseExecutionPlan] = {}

        # Get all hooks and group by phase
        all_hooks = self._registry.get_all_hooks()
        hooks_by_phase: dict[PipelinePhase, list[ModelPipelineHook]] = defaultdict(list)

        for hook in all_hooks:
            hooks_by_phase[hook.phase].append(hook)

        # Process each phase independently
        for phase, phase_hooks in hooks_by_phase.items():
            # Validate hook typing
            phase_warnings = self._validate_hook_typing(phase_hooks)
            warnings.extend(phase_warnings)

            # Build hook_id -> hook mapping for this phase
            hook_map = {h.hook_id: h for h in phase_hooks}

            # Validate dependencies exist within phase
            self._validate_dependencies(phase_hooks, hook_map)

            # Topologically sort with priority tie-breaker
            sorted_hooks = self._topological_sort(phase_hooks, hook_map)

            # Set fail_fast explicitly based on phase semantics
            # (see FAIL_FAST_PHASES constant for rationale)
            phases[phase] = ModelPhaseExecutionPlan(
                phase=phase,
                hooks=sorted_hooks,
                fail_fast=phase in FAIL_FAST_PHASES,
            )

        contract_cat_str = (
            str(self._contract_category) if self._contract_category else None
        )
        plan = ModelExecutionPlan(
            phases=phases,
            contract_category=contract_cat_str,
        )

        return plan, warnings

    def _validate_hook_typing(
        self, hooks: list[ModelPipelineHook]
    ) -> list[ModelValidationWarning]:
        """
        Validate hook type categories against contract category.

        Args:
            hooks: List of hooks to validate.

        Returns:
            List of validation warnings (when not enforcing).

        Raises:
            HookTypeMismatchError: If enforcing and type mismatch found.
        """
        warnings: list[ModelValidationWarning] = []

        # Skip validation if no contract category
        if self._contract_category is None:
            return warnings

        for hook in hooks:
            # Generic hooks (None category) pass for any contract
            if hook.handler_type_category is None:
                continue

            # Exact match passes
            if hook.handler_type_category == self._contract_category:
                continue

            # Type mismatch
            hook_cat_str = str(hook.handler_type_category)
            contract_cat_str = str(self._contract_category)

            if self._enforce_hook_typing:
                raise HookTypeMismatchError(
                    hook_id=hook.hook_id,
                    hook_category=hook_cat_str,
                    contract_category=contract_cat_str,
                )
            warning = ModelValidationWarning.hook_type_mismatch(
                hook_id=hook.hook_id,
                hook_category=hook_cat_str,
                contract_category=contract_cat_str,
            )
            warnings.append(warning)

        return warnings

    def _validate_dependencies(
        self,
        hooks: list[ModelPipelineHook],
        hook_map: dict[str, ModelPipelineHook],
    ) -> None:
        """
        Validate that all dependencies exist within the phase.

        Args:
            hooks: List of hooks in the phase.
            hook_map: Mapping of hook_id to hook for this phase.

        Raises:
            UnknownDependencyError: If a dependency references unknown hook_id.
        """
        for hook in hooks:
            for dep_id in hook.dependencies:
                if dep_id not in hook_map:
                    raise UnknownDependencyError(
                        hook_id=hook.hook_id,
                        unknown_dep=dep_id,
                    )

    def _topological_sort(
        self,
        hooks: list[ModelPipelineHook],
        hook_map: dict[str, ModelPipelineHook],
    ) -> list[ModelPipelineHook]:
        """
        Topologically sort hooks using Kahn's algorithm with priority tie-breaker.

        Args:
            hooks: List of hooks to sort.
            hook_map: Mapping of hook_id to hook.

        Returns:
            List of hooks in execution order.

        Raises:
            DependencyCycleError: If a cycle is detected.
        """
        if not hooks:
            return []

        # Build in-degree map and adjacency list
        in_degree: dict[str, int] = {h.hook_id: 0 for h in hooks}
        dependents: dict[str, list[str]] = defaultdict(list)

        for hook in hooks:
            for dep_id in hook.dependencies:
                # dep_id must execute before hook
                dependents[dep_id].append(hook.hook_id)
                in_degree[hook.hook_id] += 1

        # Initialize heap with zero in-degree hooks
        # Heap entries: (priority, hook_id) - lower priority value = earlier execution
        heap: list[tuple[int, str]] = []
        for hook in hooks:
            if in_degree[hook.hook_id] == 0:
                heapq.heappush(heap, (hook.priority, hook.hook_id))

        sorted_hooks: list[ModelPipelineHook] = []

        while heap:
            _, hook_id = heapq.heappop(heap)
            hook = hook_map[hook_id]
            sorted_hooks.append(hook)

            # Reduce in-degree for dependents
            for dependent_id in dependents[hook_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    dependent_hook = hook_map[dependent_id]
                    heapq.heappush(heap, (dependent_hook.priority, dependent_id))

        # If we didn't process all hooks, there's a cycle
        if len(sorted_hooks) != len(hooks):
            # Find hooks still in cycle
            cycle_hooks = [h.hook_id for h in hooks if in_degree[h.hook_id] > 0]
            raise DependencyCycleError(cycle=cycle_hooks)

        return sorted_hooks


# Backwards compatibility alias
RuntimePlanBuilder = BuilderExecutionPlan

__all__ = ["BuilderExecutionPlan", "FAIL_FAST_PHASES", "RuntimePlanBuilder"]
