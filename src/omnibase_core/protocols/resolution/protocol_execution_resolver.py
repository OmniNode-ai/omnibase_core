"""
ProtocolExecutionResolver - Protocol for execution order resolution.

This protocol defines the interface for resolving handler execution order
based on execution profiles and handler contracts. The resolution process
computes a deterministic execution plan from profile policies and contract
constraints.

Design:
    The resolver acts as the bridge between declarative configuration
    (profiles + contracts) and executable ordering. It implements the
    core principle:

        "Contracts declare constraints. Profiles declare policy. Resolver computes order."

    Resolution is:
        - Pure: No side effects, no global state access
        - Deterministic: Same inputs always produce same outputs
        - Fail-fast: Conflicts detected at validation, not runtime

    Resolution considers:
        - Profile execution policy (phases, ordering rules, tie breakers)
        - Contract execution constraints (requires_before, requires_after, must_run)
        - Cycle detection in dependency graphs
        - Phase assignment based on node archetype and constraints

Usage:
    .. code-block:: python

        from omnibase_core.protocols.resolution import ProtocolExecutionResolver
        from omnibase_core.models.contracts import (
            ModelExecutionProfile,
            ModelHandlerContract,
        )

        def build_execution_plan(
            resolver: ProtocolExecutionResolver,
            profile: ModelExecutionProfile,
            contracts: list[ModelHandlerContract],
        ) -> ModelExecutionPlan:
            '''Build execution plan from profile and contracts (sync).'''
            return resolver.resolve(profile, contracts)

Related:
    - OMN-1106: Execution Order Resolution (this protocol)
    - OMN-1108: ModelExecutionPlan (Resolution output)
    - OMN-1117: ModelHandlerContract (Handler contracts)
    - OMN-1125: ModelExecutionProfile (Execution profiles)
    - ONEX Four-Node Architecture documentation

.. versionadded:: 0.4.1
"""

from __future__ import annotations

__all__ = [
    "ProtocolExecutionResolver",
]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_execution_profile import (
        ModelExecutionProfile,
    )
    from omnibase_core.models.contracts.model_handler_contract import (
        ModelHandlerContract,
    )
    from omnibase_core.models.execution.model_execution_plan import ModelExecutionPlan


@runtime_checkable
class ProtocolExecutionResolver(Protocol):
    """
    Protocol for execution order resolution.

    Defines the interface for resolving handler execution order based on
    execution profiles and handler contracts. The resolver computes a
    deterministic execution plan that satisfies all ordering constraints.

    Resolution Strategy:
        1. Extract ordering constraints from handler contracts
        2. Build dependency graph from requires_before/requires_after
        3. Detect cycles and conflicting constraints (fail-fast)
        4. Assign handlers to phases based on profile policy
        5. Apply topological sort within phases using tie breakers
        6. Return execution plan with ordered handlers per phase

    Key Properties:
        - **Pure**: No side effects - resolution depends only on inputs
        - **Deterministic**: Same profile + contracts always yield same plan
        - **Fail-fast**: Conflicts detected at resolution time, not runtime

    Thread Safety:
        Implementations should be stateless and thread-safe. The resolution
        process should not modify any shared state.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.resolution import ProtocolExecutionResolver
            from omnibase_core.models.contracts import (
                ModelExecutionProfile,
                ModelHandlerContract,
                ModelHandlerBehavior,
            )

            class SimpleExecutionResolver:
                '''Simple implementation of ProtocolExecutionResolver.'''

                def resolve(
                    self,
                    profile: ModelExecutionProfile,
                    contracts: list[ModelHandlerContract],
                ) -> ModelExecutionPlan:
                    '''Resolve execution order for handlers.'''
                    # Build dependency graph
                    graph = self._build_dependency_graph(contracts)

                    # Detect cycles
                    if self._has_cycle(graph):
                        return self._create_invalid_plan(
                            conflicts=["Circular dependency detected"]
                        )

                    # Sort by phases and dependencies
                    ordered = self._topological_sort(graph, profile.ordering_policy)

                    # Build execution plan
                    return self._create_plan(profile, ordered)

            # Verify protocol conformance
            resolver: ProtocolExecutionResolver = SimpleExecutionResolver()
            assert isinstance(resolver, ProtocolExecutionResolver)

    See Also:
        - :class:`~omnibase_core.models.contracts.model_execution_profile.ModelExecutionProfile`:
          Profile defining phases and ordering policy
        - :class:`~omnibase_core.models.contracts.model_handler_contract.ModelHandlerContract`:
          Handler contracts with execution constraints
        - :class:`~omnibase_core.models.execution.model_execution_plan.ModelExecutionPlan`:
          Resolved execution plan

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

        The resolver:
            1. Extracts constraints from each contract's execution_constraints
            2. Builds a dependency graph from requires_before/requires_after
            3. Validates the graph (cycles, conflicts)
            4. Assigns handlers to phases based on profile policy
            5. Orders handlers within phases using topological sort
            6. Applies tie breakers from ordering_policy

        Args:
            profile: Execution profile defining phases and ordering policy.
                Contains:
                - phases: List of execution phases in order
                - ordering_policy: Rules for ordering handlers within phases

            contracts: Handler contracts with execution constraints.
                Each contract may have:
                - execution_constraints.requires_before: Dependencies
                - execution_constraints.requires_after: Dependents
                - execution_constraints.must_run: Force execution
                - execution_constraints.can_run_parallel: Parallelization hint

            strict_mode: When True, missing dependency references (handler:X,
                capability:Y, tag:Z) are treated as errors instead of warnings,
                making the plan invalid. When None (default), uses the profile's
                ordering_policy.strict_mode setting.

        Returns:
            Execution plan with ordered handlers per phase.
            The returned plan contains:
            - phases: Ordered phase steps with handler IDs
            - source_profile: Reference to input profile
            - ordering_policy: Description of ordering used
            - metadata: Resolution metadata (timing, conflict info)

            If conflicts are detected (cycles, unsatisfiable constraints),
            the plan's metadata will contain conflict information and the
            plan may be empty or partial. Implementations should document
            their conflict handling strategy.

        Note:
            This method is synchronous and pure. For async resolution or
            caching, implementations should wrap this method appropriately.

            The specific conflict handling behavior (empty plan vs partial
            plan vs exception) is implementation-specific. Implementations
            should document their strategy clearly.

        Example:
            .. code-block:: python

                from omnibase_core.models.contracts import (
                    ModelExecutionProfile,
                    ModelHandlerContract,
                    ModelHandlerBehavior,
                    ModelExecutionConstraints,
                )

                # Create profile with standard phases
                profile = ModelExecutionProfile(
                    phases=["preflight", "before", "execute", "after"],
                )

                # Create handler contracts with constraints
                auth_contract = ModelHandlerContract(
                    handler_id="handler.auth",
                    name="Authentication Handler",
                    version="1.0.0",
                    input_model="models.AuthInput",
                    output_model="models.AuthOutput",
                    descriptor=ModelHandlerBehavior(node_archetype="effect"),
                )

                logging_contract = ModelHandlerContract(
                    handler_id="handler.logging",
                    name="Logging Handler",
                    version="1.0.0",
                    input_model="models.LogInput",
                    output_model="models.LogOutput",
                    descriptor=ModelHandlerBehavior(node_archetype="effect"),
                    execution_constraints=ModelExecutionConstraints(
                        requires_before=["handler:handler.auth"],
                    ),
                )

                # Resolve execution order
                plan = resolver.resolve(profile, [auth_contract, logging_contract])

                # auth runs before logging (logging depends on auth)
                handlers = plan.get_all_handler_ids()
                auth_idx = handlers.index("handler.auth")
                logging_idx = handlers.index("handler.logging")
                assert auth_idx < logging_idx

                # Strict mode example - missing dependencies become errors
                strict_plan = resolver.resolve(
                    profile, [logging_contract], strict_mode=True
                )
                # Plan is invalid because handler.auth is missing
                assert not strict_plan.is_valid
        """
        ...
