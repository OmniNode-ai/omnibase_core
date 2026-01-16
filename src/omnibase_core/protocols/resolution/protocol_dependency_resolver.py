"""
ProtocolDependencyResolver - Protocol for capability-based dependency resolution.

This protocol defines the interface for resolving dependencies based on
capability, intent, or protocol rather than hardcoded module paths.
This enables auto-discovery and loose coupling between nodes.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations satisfy the contract. This enables consistent
    dependency resolution across the ONEX ecosystem while allowing
    implementation flexibility.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.resolution import ProtocolDependencyResolver
        from omnibase_core.models.contracts import ModelDependencySpec

        async def resolve_dependencies(
            resolver: ProtocolDependencyResolver,
            specs: list[ModelDependencySpec],
        ) -> dict[str, object]:
            '''Resolve multiple dependencies using the resolver.'''
            return await resolver.resolve_all(specs)

Related:
    - OMN-1123: ModelDependencySpec (Capability-Based Dependencies)
    - ModelDependencySpec: The specification model for dependencies
    - ONEX Four-Node Architecture documentation

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = [
    "ProtocolDependencyResolver",
]

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_dependency_spec import ModelDependencySpec


@runtime_checkable
class ProtocolDependencyResolver(Protocol):
    """
    Protocol for capability-based dependency resolution.

    Defines the interface for resolving dependencies by capability, intent,
    or protocol rather than hardcoded module paths. Implementations should
    use the discovery methods specified in ModelDependencySpec to find
    matching services.

    Resolution Strategy:
        1. Check capability filter - match against registered capabilities
        2. Check intent_types filter - match against registered intent handlers
        3. Check protocol filter - match against registered protocols
        4. Apply contract_type filter if specified
        5. Apply state filter (default: ACTIVE)
        6. Apply selection_strategy for multiple matches
        7. Fall back to fallback_module if no match found

    Thread Safety:
        WARNING: Thread safety is implementation-specific. Callers should verify
        the thread safety guarantees of their chosen implementation.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.resolution import ProtocolDependencyResolver
            from omnibase_core.models.contracts import ModelDependencySpec

            class SimpleDependencyResolver:
                '''Simple implementation of ProtocolDependencyResolver.'''

                def __init__(self) -> None:
                    self._registry: dict[str, Any] = {}

                async def resolve(self, spec: ModelDependencySpec) -> Any | None:
                    '''Resolve a single dependency.'''
                    if spec.capability and spec.capability in self._registry:
                        return self._registry[spec.capability]
                    return None

                async def resolve_all(
                    self, specs: list[ModelDependencySpec]
                ) -> dict[str, Any]:
                    '''Resolve multiple dependencies.'''
                    results: dict[str, Any] = {}
                    for spec in specs:
                        results[spec.name] = await self.resolve(spec)
                    return results

            # Verify protocol conformance
            resolver: ProtocolDependencyResolver = SimpleDependencyResolver()
            assert isinstance(resolver, ProtocolDependencyResolver)

    .. versionadded:: 0.4.0
    """

    async def resolve(self, spec: ModelDependencySpec) -> Any | None:
        """
        Resolve a single dependency specification.

        Attempts to find a service matching the discovery criteria specified
        in the ModelDependencySpec. Uses capability, intent_types, and/or
        protocol filters to locate matching services.

        Args:
            spec: The dependency specification describing what to find.
                  Must have at least one discovery method (capability,
                  intent_types, or protocol) specified.

        Returns:
            The resolved service if found, or None if no match is found
            and no fallback_module is specified. If fallback_module is
            specified, implementations should attempt to load and return
            that module when no capability match is found.

        Note:
            Implementations may vary in how they handle:
            - Multiple discovery methods (AND vs OR logic)
            - Selection strategy when multiple matches exist
            - Fallback behavior when no match is found

        Example:
            .. code-block:: python

                spec = ModelDependencySpec(
                    name="event_bus",
                    type="protocol",
                    capability="event.publishing",
                )
                service = await resolver.resolve(spec)
                if service:
                    service.publish(event)
        """
        ...

    async def resolve_all(self, specs: list[ModelDependencySpec]) -> dict[str, object]:
        """
        Resolve multiple dependency specifications.

        Resolves all provided specifications and returns a dictionary
        mapping dependency names to resolved services (or None if not found).

        Args:
            specs: List of dependency specifications to resolve.

        Returns:
            Dictionary mapping each spec's name to its resolved service.
            If a dependency cannot be resolved and has no fallback,
            its value will be None.

        Note:
            The dictionary keys correspond to the ``name`` field of each
            ModelDependencySpec. If multiple specs have the same name,
            later values will overwrite earlier ones.

        Example:
            .. code-block:: python

                specs = [
                    ModelDependencySpec(
                        name="event_bus",
                        type="protocol",
                        capability="event.publishing",
                    ),
                    ModelDependencySpec(
                        name="logger",
                        type="protocol",
                        capability="logging.structured",
                    ),
                ]
                services = await resolver.resolve_all(specs)
                event_bus = services["event_bus"]
                logger = services["logger"]
        """
        ...
