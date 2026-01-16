"""
ProtocolCapabilityResolver - Protocol for resolving capability dependencies to provider bindings.

This protocol defines the interface for resolving capability-based dependencies
declared in handler contracts to concrete provider bindings. The resolution
process matches ModelCapabilityDependency requirements against registered
ModelProviderDescriptor instances in the provider registry.

Design:
    The resolver acts as the bridge between abstract capability requirements
    and concrete provider instances. It implements the core principle:

        "Contracts declare capabilities + constraints. Resolver matches to providers."

    Resolution considers:
        - Capability matching (exact or pattern-based)
        - Requirement filtering (must/prefer/forbid)
        - Selection policy (auto_if_unique, best_score, require_explicit)
        - Optional profile-based preferences

Usage:
    .. code-block:: python

        from omnibase_core.protocols.resolution import ProtocolCapabilityResolver
        from omnibase_core.models.capabilities import ModelCapabilityDependency

        def resolve_database(
            resolver: ProtocolCapabilityResolver,
            registry: ProtocolProviderRegistry,
        ) -> ModelBinding:
            '''Resolve a database dependency to a provider binding (sync).'''
            dep = ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
            )
            return resolver.resolve(dep, registry)

Related:
    - OMN-1152: ModelCapabilityDependency (Capability Dependencies)
    - OMN-1153: ModelProviderDescriptor (Provider Registry)
    - OMN-1156: ProtocolProviderRegistry (Provider Registry Protocol)
    - OMN-1157: ModelBinding (Resolution Bindings)
    - ONEX Four-Node Architecture documentation

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = [
    "ProtocolCapabilityResolver",
    "ProtocolProfile",
    "ProtocolProviderRegistry",
]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    # Forward references for models not yet implemented (OMN-1157, OMN-1158)
    # These will be replaced with proper imports when the models are created.
    #
    # ModelBinding: Represents a resolved binding between a capability dependency
    # and a concrete provider. Contains the provider descriptor, resolved adapter,
    # and any binding-specific configuration.
    #
    # ModelResolutionResult: Container for batch resolution results, including
    # successful bindings, failed resolutions, and diagnostic information.
    #
    # ModelProfile: Optional user/environment profile that can influence
    # resolution preferences (e.g., prefer certain regions, vendors).
    from typing import Any

    from omnibase_core.models.capabilities.model_capability_dependency import (
        ModelCapabilityDependency,
    )
    from omnibase_core.models.providers.model_provider_descriptor import (
        ModelProviderDescriptor,
    )

    # Type aliases for forward-referenced models
    ModelBinding = Any  # Will be: omnibase_core.models.bindings.model_binding
    ModelResolutionResult = (
        Any  # Will be: omnibase_core.models.resolution.model_resolution_result
    )
    ModelProfile = Any  # Will be: omnibase_core.models.profiles.model_profile


@runtime_checkable
class ProtocolProviderRegistry(Protocol):
    """Minimal interface for provider registry (full implementation in OMN-1156).

    This stub protocol defines the minimal interface required by
    ProtocolCapabilityResolver. The full ProtocolProviderRegistry will be
    implemented as part of OMN-1156 with additional registration, lifecycle,
    and health management methods.

    Note:
        This is a temporary stub. It will be replaced by the full
        ProtocolProviderRegistry from OMN-1156. The stub exists to allow
        ProtocolCapabilityResolver to be implemented and tested before
        the registry protocol is complete.

    .. versionadded:: 0.4.0
    """

    def get_providers_for_capability(
        self, capability: str
    ) -> list[ModelProviderDescriptor]:
        """Get all providers that offer a specific capability.

        Args:
            capability: The capability identifier to search for.
                Can be an exact match (e.g., "database.relational") or
                a pattern (e.g., "database.*") depending on implementation.

        Returns:
            List of provider descriptors that offer the requested capability.
            Returns empty list if no providers match.

        Example:
            .. code-block:: python

                providers = registry.get_providers_for_capability("database.relational")
                for provider in providers:
                    print(f"Found: {provider.provider_id}")
        """
        ...


@runtime_checkable
class ProtocolProfile(Protocol):
    """Protocol stub for profile until ModelProfile is implemented.

    Defines the minimal interface expected by the resolver for profile-based
    resolution preferences such as explicit bindings and provider weights.

    Note:
        This is a temporary stub that will be replaced by ModelProfile
        when that model is implemented. The stub allows the resolver
        to be implemented and tested before the profile model is complete.

    Attributes:
        profile_id: Unique identifier for this profile.
        provider_weights: Optional mapping of provider_id to weight adjustment.
        explicit_bindings: Optional mapping of alias to pinned provider_id.

    .. versionadded:: 0.4.0
    """

    @property
    def profile_id(self) -> str:
        """Get the profile ID."""
        ...

    @property
    def provider_weights(self) -> dict[str, float] | None:
        """Get provider weight adjustments."""
        ...

    @property
    def explicit_bindings(self) -> dict[str, str] | None:
        """Get explicit provider bindings by alias."""
        ...


@runtime_checkable
class ProtocolCapabilityResolver(Protocol):
    """
    Protocol for resolving capability dependencies to provider bindings.

    Defines the interface for resolving ModelCapabilityDependency instances
    to concrete ModelBinding objects. The resolution process matches
    capability requirements against providers in the registry, applying
    filters (must/prefer/forbid) and selection policies.

    Resolution Strategy:
        1. Query registry for providers matching the capability
        2. Apply ``must`` requirements - filter to providers with required attributes
        3. Apply ``forbid`` requirements - exclude providers with forbidden attributes
        4. Apply selection policy:
           - ``auto_if_unique``: Select if exactly one provider matches
           - ``best_score``: Score providers by ``prefer`` matches, select highest
           - ``require_explicit``: Require explicit binding, never auto-select
        5. Use optional profile for tie-breaking or preference boosting
        6. Return binding or raise resolution error

    Thread Safety:
        WARNING: Thread safety is implementation-specific. Callers should verify
        the thread safety guarantees of their chosen implementation. The registry
        may be modified during resolution in concurrent scenarios.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.resolution import (
                ProtocolCapabilityResolver,
                ProtocolProviderRegistry,
            )
            from omnibase_core.models.capabilities import (
                ModelCapabilityDependency,
                ModelRequirementSet,
            )

            class SimpleCapabilityResolver:
                '''Simple implementation of ProtocolCapabilityResolver.'''

                def resolve(
                    self,
                    dependency: ModelCapabilityDependency,
                    registry: ProtocolProviderRegistry,
                    profile: ModelProfile | None = None,
                ) -> ModelBinding:
                    '''Resolve a single dependency to a binding.'''
                    providers = registry.get_providers_for_capability(
                        dependency.capability
                    )

                    # Apply must/forbid filtering
                    filtered = self._apply_filters(providers, dependency.requirements)

                    # Apply selection policy
                    if dependency.selection_policy == "auto_if_unique":
                        if len(filtered) == 1:
                            return self._create_binding(filtered[0], dependency)
                        elif len(filtered) == 0:
                            raise ResolutionError("No matching provider")
                        else:
                            raise ResolutionError("Ambiguous: multiple providers match")

                    # ... handle other policies

                def resolve_all(
                    self,
                    dependencies: list[ModelCapabilityDependency],
                    registry: ProtocolProviderRegistry,
                    profile: ModelProfile | None = None,
                ) -> ModelResolutionResult:
                    '''Resolve all dependencies, returning bindings and report.'''
                    bindings = {}
                    failures = {}
                    for dep in dependencies:
                        try:
                            bindings[dep.alias] = self.resolve(dep, registry, profile)
                        except ResolutionError as e:
                            failures[dep.alias] = str(e)
                    return ModelResolutionResult(bindings=bindings, failures=failures)

            # Verify protocol conformance
            resolver: ProtocolCapabilityResolver = SimpleCapabilityResolver()
            assert isinstance(resolver, ProtocolCapabilityResolver)

    .. versionadded:: 0.4.0
    """

    def resolve(
        self,
        dependency: ModelCapabilityDependency,
        registry: ProtocolProviderRegistry,
        profile: ModelProfile | None = None,
    ) -> ModelBinding:
        """
        Resolve a single capability dependency to a provider binding.

        Attempts to find a provider matching the dependency's capability and
        requirements, then creates a binding between the dependency and the
        selected provider.

        Args:
            dependency: The capability dependency to resolve. Must have a valid
                capability identifier and may include requirements (must/prefer/
                forbid) and a selection policy.
            registry: The provider registry to search for matching providers.
                Must implement ProtocolProviderRegistry.
            profile: Optional profile for resolution preferences. Can influence
                provider selection through user/environment preferences such as
                preferred regions, vendors, or performance characteristics.

        Returns:
            A ModelBinding connecting the dependency to a resolved provider.
            The binding contains the provider descriptor, resolved adapter
            reference, and binding metadata.

        Raises:
            Resolution errors may be raised for various failure conditions:
            - No providers match the capability
            - No providers pass the must/forbid filters
            - Multiple providers match with auto_if_unique policy (ambiguous)
            - Explicit binding required but not provided

        Note:
            The specific error types and behaviors are implementation-specific.
            Implementations should document their error handling strategy.

        Example:
            .. code-block:: python

                from omnibase_core.models.capabilities import (
                    ModelCapabilityDependency,
                    ModelRequirementSet,
                )

                # Create dependency with requirements
                dep = ModelCapabilityDependency(
                    alias="db",
                    capability="database.relational",
                    requirements=ModelRequirementSet(
                        must={"supports_transactions": True},
                        prefer={"region": "us-east-1"},
                    ),
                    selection_policy="best_score",
                )

                # Resolve to binding
                binding = resolver.resolve(dep, registry)
                print(f"Resolved to: {binding.provider.provider_id}")
        """
        ...

    def resolve_all(
        self,
        dependencies: list[ModelCapabilityDependency],
        registry: ProtocolProviderRegistry,
        profile: ModelProfile | None = None,
    ) -> ModelResolutionResult:
        """
        Resolve all capability dependencies, returning bindings and a report.

        Batch resolution method that attempts to resolve multiple dependencies
        in a single operation. Returns a result object containing successful
        bindings and information about any failures.

        Args:
            dependencies: List of capability dependencies to resolve. Each
                dependency is resolved independently, and failures in one
                do not prevent resolution of others.
            registry: The provider registry to search for matching providers.
            profile: Optional profile for resolution preferences.

        Returns:
            A ModelResolutionResult containing:
            - Successful bindings mapped by dependency alias
            - Failed resolutions with error information
            - Resolution statistics and diagnostics
            - Overall success/failure status

        Note:
            Unlike ``resolve()``, this method does not raise exceptions for
            individual resolution failures. Instead, failures are captured
            in the result object, allowing partial success scenarios.

            The order of resolution is implementation-specific. Some
            implementations may resolve dependencies in parallel for
            performance, while others may use sequential resolution.

        Example:
            .. code-block:: python

                from omnibase_core.models.capabilities import ModelCapabilityDependency

                # Create multiple dependencies
                deps = [
                    ModelCapabilityDependency(
                        alias="db",
                        capability="database.relational",
                    ),
                    ModelCapabilityDependency(
                        alias="cache",
                        capability="cache.distributed",
                    ),
                    ModelCapabilityDependency(
                        alias="secrets",
                        capability="secrets.vault",
                        selection_policy="require_explicit",
                    ),
                ]

                # Resolve all at once
                result = resolver.resolve_all(deps, registry)

                # Check results
                if result.is_complete:
                    print("All dependencies resolved successfully")
                else:
                    for alias, error in result.failures.items():
                        print(f"Failed to resolve {alias}: {error}")

                # Access successful bindings
                db_binding = result.bindings.get("db")
                if db_binding:
                    print(f"Database: {db_binding.provider.adapter}")
        """
        ...
