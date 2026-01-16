"""
ExecutionResolver - Pure function implementation of execution order resolution.

This module implements ProtocolExecutionResolver, providing deterministic
topological ordering of handlers based on execution profiles and contract
constraints.

Core Design Principles:
    - Pure function: No side effects, no global state, no I/O
    - Deterministic: Same inputs ALWAYS produce same outputs (stable sort)
    - Fail-fast: Returns plan with is_valid=False and conflicts, never raises
    - No registries: Resolution is purely based on inputs (profile + contracts)

Algorithm:
    1. Build dependency graph from requires_before/requires_after constraints
    2. Resolve constraint references (capability:X, handler:Y, tag:Z)
    3. Detect cycles using depth-first search
    4. Apply Kahn's algorithm for topological ordering
    5. Use tie-breakers for handlers with equal ordering
    6. Assign handlers to phases based on profile configuration

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - ProtocolExecutionResolver: The protocol this class implements
    - ModelExecutionPlan: The output model

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Literal

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)
from omnibase_core.models.contracts.model_execution_profile import ModelExecutionProfile
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.execution.model_execution_conflict import (
    ModelExecutionConflict,
)
from omnibase_core.models.execution.model_execution_plan import ModelExecutionPlan
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep
from omnibase_core.models.execution.model_resolution_metadata import (
    ModelResolutionMetadata,
)
from omnibase_core.models.execution.model_tie_breaker_decision import (
    ModelTieBreakerDecision,
)
from omnibase_core.resolution._resolver_dependency_graph import _DependencyGraph
from omnibase_core.resolution._resolver_handler_info import _HandlerInfo

# Version of the resolver for tracking
_RESOLVER_VERSION = "0.4.1"


class ExecutionResolver:
    """
    Pure function implementation of execution order resolution.

    Implements ProtocolExecutionResolver to provide deterministic ordering
    of handlers based on execution profiles and contract constraints.

    The resolver:
        1. Extracts constraints from each contract's execution_constraints
        2. Builds a dependency graph from requires_before/requires_after
        3. Validates the graph (cycles, conflicts)
        4. Assigns handlers to phases based on profile policy
        5. Orders handlers within phases using topological sort
        6. Applies tie breakers from ordering_policy

    Thread Safety:
        This class is stateless and thread-safe. Each call to resolve()
        operates independently on its inputs.

    Example:
        >>> resolver = ExecutionResolver()
        >>> plan = resolver.resolve(profile, contracts)
        >>> if plan.is_valid:
        ...     for phase in plan.phases:
        ...         print(f"{phase.phase}: {phase.handler_ids}")
        ... else:
        ...     for conflict in plan.conflicts:
        ...         print(f"Conflict: {conflict.message}")

    See Also:
        - ProtocolExecutionResolver: The protocol this implements
        - ModelExecutionPlan: The output model

    .. versionadded:: 0.4.1
    """

    def resolve(
        self,
        profile: ModelExecutionProfile,
        contracts: list[ModelHandlerContract],
        strict_mode: bool | None = None,
    ) -> ModelExecutionPlan:
        """
        Resolve execution order for handlers.

        Computes a deterministic execution plan from the profile's execution
        policy and the contracts' execution constraints. The resolution process
        is pure (no side effects) and deterministic (same inputs yield same outputs).

        Args:
            profile: Execution profile defining phases and ordering policy.
            contracts: Handler contracts with execution constraints.
            strict_mode: When True, missing dependency references are treated as
                errors instead of warnings, making the plan invalid. When None
                (default), uses the profile's ordering_policy.strict_mode setting.

        Returns:
            Execution plan with ordered handlers per phase. If conflicts are
            detected, the plan will have is_valid=False and contain the
            conflicts list.
        """
        started_at = datetime.now(UTC)
        conflicts: list[ModelExecutionConflict] = []
        tie_breaker_decisions: list[ModelTieBreakerDecision] = []
        total_constraints_evaluated = 0

        # Determine effective strict mode: explicit parameter takes precedence
        effective_strict_mode = (
            strict_mode
            if strict_mode is not None
            else profile.ordering_policy.strict_mode
        )

        # Handle empty contracts case
        if not contracts:
            return self._create_empty_plan(
                profile=profile,
                started_at=started_at,
                tie_breaker_decisions=tie_breaker_decisions,
            )

        # Build handler info lookup
        handler_info_map = self._build_handler_info_map(contracts)

        # Build resolution indices for constraint matching
        handler_by_capability = self._build_capability_index(handler_info_map)
        handler_by_tag = self._build_tag_index(handler_info_map)

        # Build dependency graph
        graph, constraint_conflicts = self._build_dependency_graph(
            handler_info_map=handler_info_map,
            handler_by_capability=handler_by_capability,
            handler_by_tag=handler_by_tag,
            strict_mode=effective_strict_mode,
        )
        conflicts.extend(constraint_conflicts)
        total_constraints_evaluated += self._count_constraints(handler_info_map)

        # Detect cycles
        cycle_conflicts = self._detect_cycles(graph)
        conflicts.extend(cycle_conflicts)

        # If we have blocking conflicts (cycles), return invalid plan
        if any(c.is_blocking() for c in conflicts):
            return self._create_invalid_plan(
                profile=profile,
                conflicts=conflicts,
                started_at=started_at,
                total_constraints_evaluated=total_constraints_evaluated,
                handler_count=len(contracts),
                tie_breaker_decisions=tie_breaker_decisions,
            )

        # Perform topological sort
        sorted_handlers, sort_tie_decisions = self._topological_sort(
            graph=graph,
            handler_info_map=handler_info_map,
            ordering_policy=profile.ordering_policy,
        )
        tie_breaker_decisions.extend(sort_tie_decisions)

        # Assign handlers to phases
        phases = self._assign_to_phases(
            sorted_handlers=sorted_handlers,
            profile_phases=profile.phases,
            handler_info_map=handler_info_map,
        )

        # Create successful plan
        return self._create_valid_plan(
            profile=profile,
            phases=phases,
            started_at=started_at,
            total_constraints_evaluated=total_constraints_evaluated,
            tie_breaker_decisions=tie_breaker_decisions,
            conflicts=conflicts,  # May have warnings
        )

    # =========================================================================
    # Internal Methods - Index Building
    # =========================================================================

    def _build_handler_info_map(
        self,
        contracts: list[ModelHandlerContract],
    ) -> dict[str, _HandlerInfo]:
        """
        Build handler info lookup from contracts.

        Creates a dictionary mapping handler IDs to their extracted info,
        including priority, tags, capabilities, and execution constraints.

        Args:
            contracts: List of handler contracts to process.

        Returns:
            Dictionary mapping handler_id to _HandlerInfo for each contract.
        """
        result: dict[str, _HandlerInfo] = {}
        for contract in contracts:
            # Extract priority from metadata (default to 0 - higher number = lower priority)
            priority_raw = contract.metadata.get("priority", 0)
            priority = (
                int(priority_raw) if isinstance(priority_raw, (int, float)) else 0
            )

            result[contract.handler_id] = _HandlerInfo(
                handler_id=contract.handler_id,
                priority=priority,
                tags=list(contract.tags),
                capability_outputs=list(contract.capability_outputs),
                has_must_run=(
                    contract.execution_constraints.must_run
                    if contract.execution_constraints
                    else False
                ),
                constraints=contract.execution_constraints,
            )
        return result

    def _build_capability_index(
        self,
        handler_info_map: dict[str, _HandlerInfo],
    ) -> dict[str, list[str]]:
        """
        Build capability to handler_ids index.

        Creates a reverse index mapping capability names to the list of
        handler IDs that provide that capability. Used for resolving
        ``capability:X`` constraint references.

        Args:
            handler_info_map: Handler info lookup built from contracts.

        Returns:
            Dictionary mapping capability name to list of handler IDs.
        """
        result: dict[str, list[str]] = defaultdict(list)
        for handler_id, info in handler_info_map.items():
            for capability in info.capability_outputs:
                result[capability].append(handler_id)
        return dict(result)

    def _build_tag_index(
        self,
        handler_info_map: dict[str, _HandlerInfo],
    ) -> dict[str, list[str]]:
        """
        Build tag to handler_ids index.

        Creates a reverse index mapping tag names to the list of handler IDs
        that have that tag. Used for resolving ``tag:X`` constraint references.

        Args:
            handler_info_map: Handler info lookup built from contracts.

        Returns:
            Dictionary mapping tag name to list of handler IDs.
        """
        result: dict[str, list[str]] = defaultdict(list)
        for handler_id, info in handler_info_map.items():
            for tag in info.tags:
                result[tag].append(handler_id)
        return dict(result)

    def _count_constraints(
        self,
        handler_info_map: dict[str, _HandlerInfo],
    ) -> int:
        """
        Count total constraints evaluated.

        Sums all requires_before and requires_after constraints across all
        handlers. Used for resolution metadata reporting.

        Args:
            handler_info_map: Handler info lookup built from contracts.

        Returns:
            Total number of constraint references across all handlers.
        """
        count = 0
        for info in handler_info_map.values():
            if info.constraints:
                count += len(info.constraints.requires_before)
                count += len(info.constraints.requires_after)
        return count

    # =========================================================================
    # Internal Methods - Dependency Graph
    # =========================================================================

    def _build_dependency_graph(
        self,
        handler_info_map: dict[str, _HandlerInfo],
        handler_by_capability: dict[str, list[str]],
        handler_by_tag: dict[str, list[str]],
        strict_mode: bool = False,
    ) -> tuple[_DependencyGraph, list[ModelExecutionConflict]]:
        """
        Build dependency graph from handler constraints.

        Processes requires_before and requires_after constraints from each
        handler's execution_constraints, resolving symbolic references
        (capability:X, handler:Y, tag:Z) to concrete handler IDs.

        Args:
            handler_info_map: Handler info lookup built from contracts.
            handler_by_capability: Capability to handler_ids index.
            handler_by_tag: Tag to handler_ids index.
            strict_mode: When True, missing dependencies are errors instead of
                warnings.

        Returns:
            Tuple of (dependency_graph, conflicts). The graph contains nodes
            for all handlers and directed edges representing ordering
            constraints. Conflicts are warnings (or errors in strict mode)
            for unresolved references.
        """
        graph = _DependencyGraph()
        conflicts: list[ModelExecutionConflict] = []

        # Add all handlers as nodes
        for handler_id in handler_info_map:
            graph.nodes.add(handler_id)

        # Process constraints for each handler
        for handler_id, info in handler_info_map.items():
            if not info.constraints:
                continue

            # Process requires_before: this handler must run AFTER dependencies
            for ref in info.constraints.requires_before:
                dep_handlers, ref_conflict = self._resolve_constraint_ref(
                    ref=ref,
                    source_handler=handler_id,
                    handler_info_map=handler_info_map,
                    handler_by_capability=handler_by_capability,
                    handler_by_tag=handler_by_tag,
                    is_before=True,
                    strict_mode=strict_mode,
                )
                if ref_conflict:
                    conflicts.append(ref_conflict)
                    continue

                for dep_handler_id in dep_handlers:
                    if dep_handler_id != handler_id:  # No self-edges
                        graph.edges[handler_id].add(dep_handler_id)
                        graph.reverse_edges[dep_handler_id].add(handler_id)

            # Process requires_after: dependents must run AFTER this handler
            for ref in info.constraints.requires_after:
                dep_handlers, ref_conflict = self._resolve_constraint_ref(
                    ref=ref,
                    source_handler=handler_id,
                    handler_info_map=handler_info_map,
                    handler_by_capability=handler_by_capability,
                    handler_by_tag=handler_by_tag,
                    is_before=False,
                    strict_mode=strict_mode,
                )
                if ref_conflict:
                    conflicts.append(ref_conflict)
                    continue

                for dep_handler_id in dep_handlers:
                    if dep_handler_id != handler_id:  # No self-edges
                        # dep_handler_id must run AFTER handler_id
                        graph.edges[dep_handler_id].add(handler_id)
                        graph.reverse_edges[handler_id].add(dep_handler_id)

        return graph, conflicts

    def _resolve_constraint_ref(
        self,
        ref: str,
        source_handler: str,
        handler_info_map: dict[str, _HandlerInfo],
        handler_by_capability: dict[str, list[str]],
        handler_by_tag: dict[str, list[str]],
        is_before: bool,
        strict_mode: bool = False,
    ) -> tuple[list[str], ModelExecutionConflict | None]:
        """
        Resolve a constraint reference to handler IDs.

        Args:
            ref: The constraint reference (e.g., "capability:auth")
            source_handler: The handler that declared this constraint
            handler_info_map: Handler info lookup
            handler_by_capability: Capability index
            handler_by_tag: Tag index
            is_before: True if this is a requires_before constraint
            strict_mode: When True, missing dependencies are errors instead of
                warnings.

        Returns:
            Tuple of (resolved_handler_ids, conflict_if_any).
        """
        parts = ref.split(":", 1)
        if len(parts) != 2:
            return [], None  # Should not happen due to validation

        prefix, value = parts

        # Determine severity based on strict mode
        severity: Literal["error", "warning"] = "error" if strict_mode else "warning"

        if prefix == "handler":
            # Direct handler reference
            if value in handler_info_map:
                return [value], None
            # Handler not found - create conflict
            return [], ModelExecutionConflict(
                conflict_type="missing_dependency",
                severity=severity,
                message=f"Handler '{value}' referenced in constraint not found",
                handler_ids=(source_handler,),
                constraint_refs=(ref,),
                suggested_resolution=f"Ensure handler '{value}' is included in contracts",
            )

        if prefix == "capability":
            handlers = handler_by_capability.get(value, [])
            if handlers:
                return handlers, None
            # Capability not found - create conflict
            return [], ModelExecutionConflict(
                conflict_type="missing_dependency",
                severity=severity,
                message=f"No handlers provide capability '{value}'",
                handler_ids=(source_handler,),
                constraint_refs=(ref,),
                suggested_resolution=f"Add a handler that provides capability '{value}'",
            )

        if prefix == "tag":
            handlers = handler_by_tag.get(value, [])
            if handlers:
                return handlers, None
            # Tag not found - create conflict
            return [], ModelExecutionConflict(
                conflict_type="missing_dependency",
                severity=severity,
                message=f"No handlers have tag '{value}'",
                handler_ids=(source_handler,),
                constraint_refs=(ref,),
                suggested_resolution=f"Add tag '{value}' to a handler",
            )

        # Unknown prefix - should not happen due to validation
        return [], None

    # =========================================================================
    # Internal Methods - Cycle Detection
    # =========================================================================

    def _detect_cycles(
        self,
        graph: _DependencyGraph,
    ) -> list[ModelExecutionConflict]:
        """
        Detect cycles in the dependency graph using DFS.

        Uses depth-first search with a recursion stack to identify circular
        dependencies. Each detected cycle produces an error-severity conflict
        with the cycle path for debugging.

        Note:
            **Fail-Fast Behavior**: This method returns immediately after
            detecting the FIRST cycle. If multiple independent cycles exist
            in the graph, only one is reported. This is intentional:

            - A single cycle is sufficient to invalidate the execution plan
            - Early return avoids complex state management after cycle detection
            - Performance is improved by not traversing the entire graph
            - Users should fix the reported cycle and re-run to find others

            For comprehensive cycle/SCC detection, consider Tarjan's algorithm
            as a future enhancement.

        Args:
            graph: Dependency graph with nodes and edges.

        Returns:
            List containing at most ONE cycle conflict. The list format is
            maintained for API consistency, but will contain either zero
            (no cycles) or exactly one conflict (first cycle found).

        See Also:
            ModelExecutionConflict: Documents this fail-fast behavior
        """
        conflicts: list[ModelExecutionConflict] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            """DFS to find a cycle. Returns cycle path if found."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in sorted(graph.edges.get(node, set())):
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle - extract the cycle path
                    cycle_start = path.index(neighbor)
                    cycle_path = path[cycle_start:] + [neighbor]
                    return cycle_path

            path.pop()
            rec_stack.remove(node)
            return None

        # Process all nodes (sorted for determinism)
        for node in sorted(graph.nodes):
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    # Build a readable message
                    cycle_str = " -> ".join(cycle)
                    conflicts.append(
                        ModelExecutionConflict(
                            conflict_type="cycle",
                            severity="error",
                            message=f"Circular dependency detected: {cycle_str}",
                            handler_ids=tuple(cycle[:-1]),  # Unique handlers in cycle
                            cycle_path=tuple(cycle),
                            suggested_resolution=(
                                "Remove one of the dependencies to break the cycle"
                            ),
                        )
                    )
                    # One blocking cycle is sufficient to invalidate the plan.
                    # Return immediately to avoid complex state management.
                    return conflicts

        return conflicts

    # =========================================================================
    # Internal Methods - Topological Sort
    # =========================================================================

    def _topological_sort(
        self,
        graph: _DependencyGraph,
        handler_info_map: dict[str, _HandlerInfo],
        ordering_policy: ModelExecutionOrderingPolicy,
    ) -> tuple[list[str], list[ModelTieBreakerDecision]]:
        """
        Perform topological sort with deterministic tie-breaking.

        Uses Kahn's algorithm with tie-breaking for handlers with equal
        indegree.

        Returns:
            Tuple of (sorted_handler_ids, tie_breaker_decisions).
        """
        tie_decisions: list[ModelTieBreakerDecision] = []

        # Calculate in-degrees (count of dependencies for each node)
        in_degree: dict[str, int] = {}
        for node in graph.nodes:
            # Count edges to nodes in the graph (dependencies)
            in_degree[node] = sum(
                1 for d in graph.edges.get(node, set()) if d in graph.nodes
            )

        # Find nodes with no dependencies
        ready: list[str] = [node for node, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while ready:
            # Sort ready nodes using tie-breakers for determinism
            if len(ready) > 1:
                ready_sorted, decision = self._apply_tie_breakers(
                    candidates=ready,
                    handler_info_map=handler_info_map,
                    ordering_policy=ordering_policy,
                    phase="global",  # Phase not yet determined
                )
                if decision:
                    tie_decisions.append(decision)
                ready = ready_sorted

            # Take the first ready node
            node = ready.pop(0)
            result.append(node)

            # Update in-degrees for dependents
            for dependent in sorted(graph.reverse_edges.get(node, set())):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        ready.append(dependent)

        return result, tie_decisions

    def _apply_tie_breakers(
        self,
        candidates: list[str],
        handler_info_map: dict[str, _HandlerInfo],
        ordering_policy: ModelExecutionOrderingPolicy,
        phase: str,
    ) -> tuple[list[str], ModelTieBreakerDecision | None]:
        """
        Apply tie-breakers to sort candidates with equal ordering constraints.

        Returns:
            Tuple of (sorted_candidates, tie_breaker_decision_if_needed).
        """
        if len(candidates) <= 1:
            return candidates, None

        original_order = list(candidates)
        sorted_candidates = list(candidates)
        tie_breaker_used: str | None = None
        reason: str | None = None

        for tie_breaker in ordering_policy.tie_breakers:
            if tie_breaker == "priority":
                # Sort by priority (lower number = higher priority = runs first)
                # Secondary sort by handler_id for determinism
                sorted_candidates = sorted(
                    sorted_candidates,
                    key=lambda h: (
                        handler_info_map[h].priority,
                        h,  # Secondary sort by name for stability
                    ),
                )
                # Record if this changed the order (for metadata tracking)
                if sorted_candidates != original_order:
                    tie_breaker_used = "priority"
                    first = sorted_candidates[0]
                    reason = f"{first} has priority={handler_info_map[first].priority}"
                # Always break after priority - it provides a complete ordering
                break

            if tie_breaker == "alphabetical":
                # Sort alphabetically by handler_id
                sorted_candidates = sorted(sorted_candidates)
                if sorted_candidates != original_order:
                    tie_breaker_used = "alphabetical"
                    first = sorted_candidates[0]
                    reason = f"{first} is alphabetically first"
                break

        # Record a decision if the first element changed (leader changed)
        decision: ModelTieBreakerDecision | None = None
        if sorted_candidates[0] != original_order[0] and tie_breaker_used:
            decision = ModelTieBreakerDecision(
                phase=phase,
                handler_ids=original_order,
                tie_breaker_used=tie_breaker_used,
                winning_handler=sorted_candidates[0],
                reason=reason,
            )

        # Always return the sorted candidates - the sort is deterministic
        return sorted_candidates, decision

    # =========================================================================
    # Internal Methods - Phase Assignment
    # =========================================================================

    def _assign_to_phases(
        self,
        sorted_handlers: list[str],
        profile_phases: tuple[str, ...],
        handler_info_map: dict[str, _HandlerInfo],
    ) -> list[ModelPhaseStep]:
        """
        Assign handlers to execution phases.

        Currently, all handlers are assigned to the EXECUTE phase since phase
        hints are not yet supported in ModelHandlerContract.execution_constraints.
        Future versions may support explicit phase assignment via handler contract
        hints, allowing handlers to declare their target phase (e.g., PREFLIGHT
        for validation, FINALIZE for cleanup).

        Args:
            sorted_handlers: Handlers in dependency order.
            profile_phases: Phase names from profile.
            handler_info_map: Handler info lookup.

        Returns:
            List of ModelPhaseStep with handlers assigned.
        """
        # Map profile phase names to enum values
        phase_name_to_enum: dict[str, EnumHandlerExecutionPhase] = {
            "preflight": EnumHandlerExecutionPhase.PREFLIGHT,
            "before": EnumHandlerExecutionPhase.BEFORE,
            "execute": EnumHandlerExecutionPhase.EXECUTE,
            "after": EnumHandlerExecutionPhase.AFTER,
            "emit": EnumHandlerExecutionPhase.EMIT,
            "finalize": EnumHandlerExecutionPhase.FINALIZE,
        }

        # For now, assign all handlers to EXECUTE phase
        # This preserves the topological order
        execute_phase = phase_name_to_enum.get(
            "execute", EnumHandlerExecutionPhase.EXECUTE
        )

        # Build phase steps for all phases
        phases: list[ModelPhaseStep] = []
        for phase_name in profile_phases:
            phase_enum = phase_name_to_enum.get(phase_name)
            if phase_enum is None:
                continue

            if phase_enum == execute_phase:
                # Assign all handlers to execute phase
                phases.append(
                    ModelPhaseStep(
                        phase=phase_enum,
                        handler_ids=sorted_handlers,
                        ordering_rationale="Topological sort based on dependency constraints",
                    )
                )
            else:
                # Empty phase step
                phases.append(
                    ModelPhaseStep(
                        phase=phase_enum,
                        handler_ids=[],
                    )
                )

        return phases

    # =========================================================================
    # Internal Methods - Statistics
    # =========================================================================

    def _compute_tie_breaker_statistics(
        self,
        tie_breaker_decisions: list[ModelTieBreakerDecision],
    ) -> dict[str, int]:
        """
        Compute statistics on tie-breaker usage.

        Counts how often each tie-breaker type was applied during resolution.
        This provides insight into which tie-breakers are most frequently used.

        Args:
            tie_breaker_decisions: List of tie-breaker decisions made during
                resolution.

        Returns:
            Dictionary mapping tie-breaker type to count of applications.
            For example: {"priority": 5, "alphabetical": 12}
        """
        stats: dict[str, int] = {}
        for decision in tie_breaker_decisions:
            tie_breaker = decision.tie_breaker_used
            stats[tie_breaker] = stats.get(tie_breaker, 0) + 1
        return stats

    # =========================================================================
    # Internal Methods - Plan Creation
    # =========================================================================

    def _create_empty_plan(
        self,
        profile: ModelExecutionProfile,
        started_at: datetime,
        tie_breaker_decisions: list[ModelTieBreakerDecision],
    ) -> ModelExecutionPlan:
        """
        Create an empty but valid plan for empty contract list.

        Args:
            profile: Execution profile used for resolution.
            started_at: Timestamp when resolution started.
            tie_breaker_decisions: List of tie-breaker decisions made.

        Returns:
            Empty execution plan with is_valid=True.

        Note:
            source_profile is set to None because ModelExecutionProfile does not
            have a name/identifier field. The ordering_policy.strategy is used
            as a proxy identifier in resolution_metadata.
        """
        completed_at = datetime.now(UTC)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        return ModelExecutionPlan(
            phases=[],
            source_profile=None,
            ordering_policy=profile.ordering_policy.strategy,
            created_at=completed_at,
            resolution_metadata=ModelResolutionMetadata(
                strategy=profile.ordering_policy.strategy,
                tie_breaker_order=list(profile.ordering_policy.tie_breakers),
                tie_breaker_decisions=tie_breaker_decisions,
                deterministic=profile.ordering_policy.deterministic_seed,
                resolution_started_at=started_at,
                resolution_completed_at=completed_at,
                resolution_duration_ms=duration_ms,
                total_handlers_resolved=0,
                total_constraints_evaluated=0,
                phases_with_handlers=0,
                tie_breaker_statistics=self._compute_tie_breaker_statistics(
                    tie_breaker_decisions
                ),
                resolver_ver=_RESOLVER_VERSION,
            ),
            conflicts=[],
            is_valid=True,
        )

    def _create_invalid_plan(
        self,
        profile: ModelExecutionProfile,
        conflicts: list[ModelExecutionConflict],
        started_at: datetime,
        total_constraints_evaluated: int,
        handler_count: int,
        tie_breaker_decisions: list[ModelTieBreakerDecision],
    ) -> ModelExecutionPlan:
        """
        Create an invalid plan due to conflicts.

        Args:
            profile: Execution profile used for resolution.
            conflicts: List of blocking conflicts that caused invalidation.
            started_at: Timestamp when resolution started.
            total_constraints_evaluated: Number of constraints processed.
            handler_count: Number of handlers in the input contracts.
            tie_breaker_decisions: List of tie-breaker decisions made.

        Returns:
            Execution plan with is_valid=False and populated conflicts.

        Note:
            source_profile is set to None because ModelExecutionProfile does not
            have a name/identifier field. The ordering_policy.strategy is used
            as a proxy identifier in resolution_metadata.
        """
        completed_at = datetime.now(UTC)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        return ModelExecutionPlan(
            phases=[],
            source_profile=None,
            ordering_policy=profile.ordering_policy.strategy,
            created_at=completed_at,
            resolution_metadata=ModelResolutionMetadata(
                strategy=profile.ordering_policy.strategy,
                tie_breaker_order=list(profile.ordering_policy.tie_breakers),
                tie_breaker_decisions=tie_breaker_decisions,
                deterministic=profile.ordering_policy.deterministic_seed,
                resolution_started_at=started_at,
                resolution_completed_at=completed_at,
                resolution_duration_ms=duration_ms,
                total_handlers_resolved=0,
                total_constraints_evaluated=total_constraints_evaluated,
                phases_with_handlers=0,
                tie_breaker_statistics=self._compute_tie_breaker_statistics(
                    tie_breaker_decisions
                ),
                resolver_ver=_RESOLVER_VERSION,
            ),
            conflicts=conflicts,
            is_valid=False,
        )

    def _create_valid_plan(
        self,
        profile: ModelExecutionProfile,
        phases: list[ModelPhaseStep],
        started_at: datetime,
        total_constraints_evaluated: int,
        tie_breaker_decisions: list[ModelTieBreakerDecision],
        conflicts: list[ModelExecutionConflict],
    ) -> ModelExecutionPlan:
        """
        Create a valid execution plan.

        Args:
            profile: Execution profile used for resolution.
            phases: List of phase steps with assigned handlers.
            started_at: Timestamp when resolution started.
            total_constraints_evaluated: Number of constraints processed.
            tie_breaker_decisions: List of tie-breaker decisions made.
            conflicts: List of non-blocking conflicts (warnings).

        Returns:
            Execution plan with is_valid=True and ordered phases.

        Note:
            source_profile is set to None because ModelExecutionProfile does not
            have a name/identifier field. The ordering_policy.strategy is used
            as a proxy identifier in resolution_metadata.
        """
        completed_at = datetime.now(UTC)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        # Count handlers and phases with handlers
        total_handlers = sum(len(p.handler_ids) for p in phases)
        phases_with_handlers = sum(1 for p in phases if p.handler_ids)

        return ModelExecutionPlan(
            phases=phases,
            source_profile=None,
            ordering_policy=profile.ordering_policy.strategy,
            created_at=completed_at,
            resolution_metadata=ModelResolutionMetadata(
                strategy=profile.ordering_policy.strategy,
                tie_breaker_order=list(profile.ordering_policy.tie_breakers),
                tie_breaker_decisions=tie_breaker_decisions,
                deterministic=profile.ordering_policy.deterministic_seed,
                resolution_started_at=started_at,
                resolution_completed_at=completed_at,
                resolution_duration_ms=duration_ms,
                total_handlers_resolved=total_handlers,
                total_constraints_evaluated=total_constraints_evaluated,
                phases_with_handlers=phases_with_handlers,
                tie_breaker_statistics=self._compute_tie_breaker_statistics(
                    tie_breaker_decisions
                ),
                resolver_ver=_RESOLVER_VERSION,
            ),
            conflicts=conflicts,
            is_valid=not any(c.is_blocking() for c in conflicts),
        )


__all__ = [
    "ExecutionResolver",
]
