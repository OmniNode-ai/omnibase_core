"""Runtime plan builder for pipeline execution."""

import heapq
from collections import defaultdict

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.logging.logging_core import emit_log_event
from omnibase_core.models.pipeline import (
    ModelPhaseExecutionPlan,
    ModelPipelineExecutionPlan,
    ModelPipelineHook,
    ModelValidationWarning,
    PipelinePhase,
)
from omnibase_core.pipeline.exceptions import (
    DependencyCycleError,
    HookTypeMismatchError,
    UnknownDependencyError,
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
FAIL_FAST_PHASES: frozenset[PipelinePhase] = frozenset(
    {"preflight", "before", "execute"}
)


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
        )
        plan, warnings = builder.build()

    Thread Safety
    -------------
    **This class is NOT thread-safe.**

    Each ``BuilderExecutionPlan`` instance maintains internal state during
    the ``build()`` operation (temporary data structures for topological
    sorting). Do not share instances across threads.

    **Safe Pattern** - One builder per thread/task::

        # Each concurrent operation creates its own builder
        async def build_plan_for_request(registry: RegistryHook):
            builder = BuilderExecutionPlan(registry=registry)
            return builder.build()

        # Safe: each call uses its own builder
        plans = await asyncio.gather(
            build_plan_for_request(registry),
            build_plan_for_request(registry),
        )

    **Unsafe Pattern** - Shared builder::

        # UNSAFE - don't share builder across concurrent operations
        builder = BuilderExecutionPlan(registry=registry)

        async def worker():
            return builder.build()  # Race condition on internal state!

    **Note**: The input ``RegistryHook`` can be safely shared IF it is frozen.
    The output ``ModelPipelineExecutionPlan`` is frozen (immutable) and safe to share.

    See Also
    --------
    - docs/guides/THREADING.md for comprehensive thread safety guide
    - CLAUDE.md section "Thread Safety" for quick reference
    """

    def __init__(
        self,
        registry: RegistryHook,
        contract_category: EnumHandlerTypeCategory | None = None,
        enforce_hook_typing: bool = True,
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

    def build(self) -> tuple[ModelPipelineExecutionPlan, list[ModelValidationWarning]]:
        """
        Build an execution plan from the registry.

        Returns:
            Tuple of (execution_plan, validation_warnings).

        Raises:
            UnknownDependencyError: If a hook references an unknown dependency.
                Ensure all dependency hook_names exist within the same phase.
                Dependencies cannot span across phases (e.g., a "before" hook
                cannot depend on an "execute" hook).
            DependencyCycleError: If dependencies form a cycle.
                The error context includes the list of hook_names involved in the
                cycle. Review the dependency chain and remove circular references.
                Enable DEBUG logging for dependency graph visualization on errors.
            HookTypeMismatchError: If enforce_hook_typing=True and type mismatch.
                Either use generic hooks (handler_type_category=None) which pass
                for any contract, or ensure the hook's handler_type_category
                matches the contract_category passed to the builder.

        See Also:
            omnibase_core.pipeline.exceptions:
                Complete list of pipeline exception types including
                PipelineError (base), HookRegistryFrozenError,
                DuplicateHookError, and HookTimeoutError.
            docs/guides/PIPELINE_HOOK_REGISTRY.md:
                Comprehensive guide to hook registration, phases, dependencies,
                and execution plan building.
            docs/guides/THREADING.md:
                Thread safety considerations. Note that BuilderExecutionPlan
                instances are NOT thread-safe; use separate instances per thread
                or synchronize access.

        Note:
            When debugging dependency issues, the error context dict contains
            structured information (hook_name, unknown_dependency, cycle list, etc.)
            that can be logged or inspected programmatically.
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

            # Build hook_name -> hook mapping for this phase
            hook_map = {h.hook_name: h for h in phase_hooks}

            # Validate dependencies exist within phase
            self._validate_dependencies(phase_hooks, hook_map)

            # Topologically sort with priority tie-breaker
            sorted_hooks = self._topological_sort(phase_hooks, hook_map, phase)

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
        plan = ModelPipelineExecutionPlan(
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
                    hook_name=hook.hook_name,
                    hook_category=hook_cat_str,
                    contract_category=contract_cat_str,
                )
            warning = ModelValidationWarning.hook_type_mismatch(
                hook_name=hook.hook_name,
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
            hook_map: Mapping of hook_name to hook for this phase.

        Raises:
            UnknownDependencyError: If a dependency references unknown hook_name.
        """
        for hook in hooks:
            for dep_name in hook.dependencies:
                if dep_name not in hook_map:
                    raise UnknownDependencyError(
                        hook_name=hook.hook_name,
                        unknown_dep=dep_name,
                    )

    def _topological_sort(
        self,
        hooks: list[ModelPipelineHook],
        hook_map: dict[str, ModelPipelineHook],
        phase: PipelinePhase,
    ) -> list[ModelPipelineHook]:
        """
        Topologically sort hooks using Kahn's algorithm with priority tie-breaker.

        Algorithm: Kahn's topological sort with min-heap for stable priority ordering.
        Reference: https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm

        Args:
            hooks: List of hooks to sort.
            hook_map: Mapping of hook_name to hook.
            phase: The pipeline phase being processed.

        Returns:
            List of hooks in execution order.

        Raises:
            DependencyCycleError: If a cycle is detected.
        """
        if not hooks:
            return []

        # Build in-degree map and adjacency list
        in_degree: dict[str, int] = {h.hook_name: 0 for h in hooks}
        dependents: dict[str, list[str]] = defaultdict(list)

        for hook in hooks:
            for dep_name in hook.dependencies:
                # dep_name must execute before hook
                dependents[dep_name].append(hook.hook_name)
                in_degree[hook.hook_name] += 1

        # Initialize heap with zero in-degree hooks
        # Heap entries: (priority, hook_name) - lower priority value = earlier execution
        heap: list[tuple[int, str]] = []
        for hook in hooks:
            if in_degree[hook.hook_name] == 0:
                heapq.heappush(heap, (hook.priority, hook.hook_name))

        sorted_hooks: list[ModelPipelineHook] = []

        while heap:
            _, hook_name = heapq.heappop(heap)
            hook = hook_map[hook_name]
            sorted_hooks.append(hook)

            # Reduce in-degree for dependents
            for dependent_name in dependents[hook_name]:
                in_degree[dependent_name] -= 1
                if in_degree[dependent_name] == 0:
                    dependent_hook = hook_map[dependent_name]
                    heapq.heappush(heap, (dependent_hook.priority, dependent_name))

        # If we didn't process all hooks, there's a cycle
        if len(sorted_hooks) != len(hooks):
            # Find hooks still in cycle
            cycle_hooks = [h.hook_name for h in hooks if in_degree[h.hook_name] > 0]

            # Log dependency graph for debugging
            self._log_cycle_debug_info(phase, hooks, in_degree, cycle_hooks)

            raise DependencyCycleError(cycle=cycle_hooks)

        return sorted_hooks

    def _log_cycle_debug_info(
        self,
        phase: PipelinePhase,
        hooks: list[ModelPipelineHook],
        in_degree: dict[str, int],
        cycle_hooks: list[str],
    ) -> None:
        """
        Log dependency graph information when a cycle is detected.

        This provides debugging information to help users troubleshoot
        dependency configuration issues.

        Args:
            phase: The pipeline phase where the cycle was detected.
            hooks: All hooks in the phase.
            in_degree: In-degree counts for each hook.
            cycle_hooks: List of hook names that are part of the cycle.
        """
        # Build dependency graph lines
        graph_lines: list[str] = []
        for hook in hooks:
            deps_str = ", ".join(hook.dependencies) if hook.dependencies else "(none)"
            graph_lines.append(
                f"    {hook.hook_name}: depends_on=[{deps_str}], "
                f"in_degree={in_degree[hook.hook_name]}"
            )

        cycle_str = ", ".join(cycle_hooks)

        log_message = (
            f"Dependency cycle detected in phase '{phase}':\n"
            f"  Dependency graph:\n"
            f"{chr(10).join(graph_lines)}\n"
            f"  Hooks in cycle: {cycle_str}"
        )
        emit_log_event(EnumLogLevel.DEBUG, log_message)


__all__ = ["BuilderExecutionPlan", "FAIL_FAST_PHASES"]
