"""
ServiceRegistryProvider - In-memory thread-safe registry for provider descriptors.

This module provides the ServiceRegistryProvider class for managing ModelProviderDescriptor
instances at runtime. The registry supports registration, lookup, and filtering
of providers by capability and tags.

Thread Safety:
    All operations are protected by threading.RLock for reentrant safety.
    The registry can be safely accessed from multiple threads concurrently.

Insertion Order:
    Python 3.7+ dict maintains insertion order. The registry preserves this
    order for deterministic iteration via list_all().

Scale and Performance:
    This registry is designed for small to medium-sized deployments with fewer
    than 1,000 registered providers. At this scale, the simple locking strategy
    provides excellent performance with minimal contention.

    The lock is held during iteration in methods like find_by_capability(),
    find_by_tags(), list_all(), and list_capabilities(). This is intentional
    to provide consistent snapshots, but means:

    - Concurrent reads block each other during iteration
    - Write operations (register/unregister) block until iteration completes
    - For registries exceeding 1,000 entries, consider:
        * Sharding by capability namespace (e.g., "database.*" vs "cache.*")
        * Read-write locks (RWLock) for read-heavy workloads
        * Copy-on-write snapshots for iteration

    Typical use cases (provider discovery, capability matching) rarely exceed
    100-200 providers, making this implementation well-suited for most deployments.

Related:
    - OMN-1156: Provider registry implementation
    - ModelProviderDescriptor: The model stored in this registry

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ServiceRegistryProvider"]

import threading
from typing import TYPE_CHECKING
from uuid import UUID

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.providers.model_provider_descriptor import (
        ModelProviderDescriptor,
    )


class ServiceRegistryProvider:
    """In-memory thread-safe registry for provider descriptors.

    Provides CRUD operations for ModelProviderDescriptor instances with
    thread safety via RLock. Maintains insertion order for deterministic
    iteration. Rejects duplicate provider_id unless replace=True.

    Attributes:
        _providers: Internal dict mapping provider_id (as str) to descriptors.
        _lock: RLock for thread-safe access.

    Example:
        .. code-block:: python

            from uuid import uuid4
            from omnibase_core.services.registry.service_registry_provider import ServiceRegistryProvider
            from omnibase_core.models.providers import ModelProviderDescriptor

            # Create registry and provider
            registry = ServiceRegistryProvider()
            provider = ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="test.Adapter",
                connection_ref="env://TEST",
                tags=["production", "primary"],
            )

            # Register provider
            registry.register(provider)

            # Lookup by ID (accepts UUID directly)
            found = registry.get(provider.provider_id)
            assert found is not None

            # Find by capability
            db_providers = registry.find_by_capability("database.relational")
            assert len(db_providers) == 1

            # Find by tags
            prod_providers = registry.find_by_tags(["production"])
            assert len(prod_providers) == 1

    Thread Safety:
        All public methods are protected by an RLock (reentrant lock).
        This allows the same thread to call registry methods from within
        other registry method calls without deadlock.

    Scale Constraints:
        Designed for < 1,000 entries. Lock is held during iteration
        (find_by_capability, find_by_tags, list_all, list_capabilities),
        which is acceptable at this scale. For larger registries, consider
        sharding or read-write locks.

    .. versionadded:: 0.4.0
    """

    def __init__(self) -> None:
        """Initialize an empty ServiceRegistryProvider.

        Creates an empty provider registry with a reentrant lock for
        thread-safe operations.
        """
        # Type annotation uses forward reference (string) due to
        # `from __future__ import annotations`. The actual type is
        # imported only in TYPE_CHECKING block to avoid circular imports.
        self._providers: dict[str, ModelProviderDescriptor] = {}
        self._lock = threading.RLock()

    def register(
        self,
        provider: ModelProviderDescriptor,
        replace: bool = False,
    ) -> None:
        """Register a provider descriptor.

        Adds a provider to the registry. By default, rejects duplicates
        (same provider_id). Use replace=True to overwrite existing entries.

        Args:
            provider: The provider descriptor to register.
            replace: If True, replace existing provider with same ID.
                If False (default), raise ModelOnexError for duplicates.

        Raises:
            ModelOnexError: If provider_id already exists and replace=False.
                Raised with error code EnumCoreErrorCode.DUPLICATE_REGISTRATION
                and context containing the duplicate provider_id.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()

                # First registration succeeds
                registry.register(provider)

                # Duplicate raises ModelOnexError without replace=True
                registry.register(provider)  # Raises ModelOnexError!

                # Replace existing
                updated_provider = provider.model_copy(update={"tags": ["updated"]})
                registry.register(updated_provider, replace=True)  # OK

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        self._register_impl(provider, replace)

    @standard_error_handling("Provider registration")
    def _register_impl(
        self, provider: ModelProviderDescriptor, replace: bool = False
    ) -> None:
        """Internal implementation of provider registration."""
        provider_id = str(provider.provider_id)

        with self._lock:
            if provider_id in self._providers and not replace:
                raise ModelOnexError(
                    message=f"Provider '{provider_id}' already registered. "
                    "Use replace=True to overwrite.",
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                    context={"provider_id": provider_id},
                )
            self._providers[provider_id] = provider

    def unregister(self, provider_id: UUID) -> bool:
        """Unregister a provider by ID.

        Removes the provider with the given ID from the registry.

        Args:
            provider_id: The provider UUID to remove.

        Returns:
            True if the provider was found and removed, False if not found.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()
                registry.register(provider)

                # Remove returns True (accepts UUID directly)
                removed = registry.unregister(provider.provider_id)
                assert removed is True

                # Removing again returns False
                removed = registry.unregister(provider.provider_id)
                assert removed is False

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        str_id = str(provider_id)
        with self._lock:
            return self._providers.pop(str_id, None) is not None

    def get(self, provider_id: UUID) -> ModelProviderDescriptor | None:
        """Get a provider by ID.

        Retrieves the provider with the given ID.

        Args:
            provider_id: The provider UUID to look up.

        Returns:
            The ModelProviderDescriptor if found, None otherwise.

        Example:
            .. code-block:: python

                from uuid import UUID

                registry = ServiceRegistryProvider()
                registry.register(provider)

                # Found (accepts UUID directly)
                found = registry.get(provider.provider_id)
                assert found is not None

                # Not found
                nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
                missing = registry.get(nil_uuid)
                assert missing is None

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        str_id = str(provider_id)
        with self._lock:
            return self._providers.get(str_id)

    def find_by_capability(self, capability: str) -> list[ModelProviderDescriptor]:
        """Find all providers that offer a specific capability.

        Searches for providers whose capabilities list contains the
        exact capability string.

        Args:
            capability: The capability identifier to search for.
                Must be an exact match (e.g., "database.relational").

        Returns:
            List of providers offering the capability. Empty list if none found.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()
                registry.register(db_provider)  # has "database.relational"
                registry.register(cache_provider)  # has "cache.redis"

                # Find database providers
                db_providers = registry.find_by_capability("database.relational")
                assert len(db_providers) == 1

                # No match returns empty list
                storage_providers = registry.find_by_capability("storage.s3")
                assert len(storage_providers) == 0

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        return self._find_by_capability_impl(capability)

    @standard_error_handling("Provider capability search")
    def _find_by_capability_impl(
        self, capability: str
    ) -> list[ModelProviderDescriptor]:
        """Internal implementation of find_by_capability."""
        with self._lock:
            # Lock held during iteration - acceptable for < 1,000 entries.
            # For larger registries, consider sharding by capability namespace.
            return [p for p in self._providers.values() if capability in p.capabilities]

    def find_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
    ) -> list[ModelProviderDescriptor]:
        """Find providers by tags.

        Searches for providers based on their tags.

        Args:
            tags: List of tags to search for.
            match_all: If True, provider must have ALL specified tags.
                If False (default), provider must have ANY of the tags.

        Returns:
            List of matching providers. Empty list if none found.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()
                # provider1 has tags: ["production", "primary"]
                # provider2 has tags: ["staging"]
                registry.register(provider1)
                registry.register(provider2)

                # Any match (default)
                results = registry.find_by_tags(["production", "staging"])
                assert len(results) == 2  # Both match at least one tag

                # All must match
                results = registry.find_by_tags(
                    ["production", "primary"],
                    match_all=True,
                )
                assert len(results) == 1  # Only provider1 has both

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        # Empty tags list matches nothing - searching for no tags means no results.
        # This also avoids Python's vacuous truth where all([]) returns True.
        if not tags:
            return []

        def matches(provider: ModelProviderDescriptor) -> bool:
            if match_all:
                return all(tag in provider.tags for tag in tags)
            return any(tag in provider.tags for tag in tags)

        with self._lock:
            # Lock held during iteration - acceptable for < 1,000 entries.
            return [p for p in self._providers.values() if matches(p)]

    def list_all(self) -> list[ModelProviderDescriptor]:
        """List all registered providers.

        Returns all providers in insertion order (deterministic iteration).

        Returns:
            List of all registered providers. Empty list if none registered.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()
                registry.register(provider1)
                registry.register(provider2)

                all_providers = registry.list_all()
                assert len(all_providers) == 2
                assert all_providers[0] == provider1  # Insertion order

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        with self._lock:
            # Lock held during iteration - acceptable for < 1,000 entries.
            # Returns a snapshot copy independent of registry mutations.
            return list(self._providers.values())

    def list_capabilities(self) -> set[str]:
        """List all unique capabilities across all providers.

        Aggregates capabilities from all registered providers into a set.

        Returns:
            Set of all unique capability identifiers.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()
                # provider1: ["database.relational", "database.postgresql"]
                # provider2: ["cache.redis", "database.relational"]
                registry.register(provider1)
                registry.register(provider2)

                capabilities = registry.list_capabilities()
                assert capabilities == {
                    "database.relational",
                    "database.postgresql",
                    "cache.redis",
                }

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        with self._lock:
            # Lock held during iteration - acceptable for < 1,000 entries.
            return {cap for p in self._providers.values() for cap in p.capabilities}

    def __len__(self) -> int:
        """Return the number of registered providers.

        Returns:
            int: Count of registered providers.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()
                assert len(registry) == 0

                registry.register(provider)
                assert len(registry) == 1

        .. versionadded:: 0.4.0
        """
        with self._lock:
            return len(self._providers)

    def __contains__(self, provider_id: UUID) -> bool:
        """Check if a provider ID is registered.

        Args:
            provider_id: The provider UUID to check.

        Returns:
            bool: True if registered, False otherwise.

        Example:
            .. code-block:: python

                from uuid import UUID

                registry = ServiceRegistryProvider()
                registry.register(provider)

                assert provider.provider_id in registry
                nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
                assert nil_uuid not in registry

        .. versionadded:: 0.4.0
        """
        str_id = str(provider_id)
        with self._lock:
            return str_id in self._providers

    def clear(self) -> None:
        """Remove all registered providers.

        Clears the registry, removing all providers.

        Example:
            .. code-block:: python

                registry = ServiceRegistryProvider()
                registry.register(provider1)
                registry.register(provider2)
                assert len(registry) == 2

                registry.clear()
                assert len(registry) == 0

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 0.4.0
        """
        with self._lock:
            self._providers.clear()

    def __repr__(self) -> str:
        """Return a string representation for debugging.

        Returns:
            str: Format "ServiceRegistryProvider(providers=N)"
        """
        with self._lock:
            return f"ServiceRegistryProvider(providers={len(self._providers)})"
