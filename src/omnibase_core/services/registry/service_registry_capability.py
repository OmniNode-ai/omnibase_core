"""
ServiceRegistryCapability - Thread-safe registry for capability metadata.

This module provides an in-memory thread-safe registry for ModelCapabilityMetadata
instances. The registry stores capability metadata for documentation and discovery
purposes, keyed by the semantic capability identifier.

Thread Safety:
    All operations are protected by an RLock for thread-safe access.
    RLock allows re-entrant locking from the same thread.

Ordering:
    The registry maintains insertion order (via dict ordering in Python 3.7+),
    ensuring deterministic iteration order for list_all() and find_by_tags().

Scale and Performance:
    This registry is designed for small to medium-sized deployments with fewer
    than 1,000 registered capabilities. At this scale, the simple locking strategy
    provides excellent performance with minimal contention.

    The lock is held during iteration in methods like find_by_tags() and list_all().
    This is intentional to provide consistent snapshots, but means:

    - Concurrent reads block each other during iteration
    - Write operations (register/unregister) block until iteration completes
    - For registries exceeding 1,000 entries, consider:
        * Sharding by capability namespace (e.g., "database.*" vs "cache.*")
        * Read-write locks (RWLock) for read-heavy workloads
        * Copy-on-write snapshots for iteration

    Typical use cases (capability discovery, provider matching) rarely exceed
    100-200 capabilities, making this implementation well-suited for most deployments.

OMN-1156: ServiceRegistryCapability implementation.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ServiceRegistryCapability"]

import threading

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.capabilities.model_capability_metadata import (
    ModelCapabilityMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ServiceRegistryCapability:
    """
    In-memory thread-safe registry for capability metadata.

    This registry stores ModelCapabilityMetadata instances keyed by their
    semantic capability identifier (e.g., "database.relational"). It provides
    thread-safe operations for registration, lookup, and filtering.

    Thread Safety:
        All public methods are protected by an RLock, ensuring thread-safe
        access from multiple threads. The RLock allows re-entrant calls from
        the same thread.

    Ordering:
        The registry maintains insertion order. list_all() and find_by_tags()
        return capabilities in the order they were registered.

    Scale Constraints:
        Designed for < 1,000 entries. Lock is held during iteration (find_by_tags,
        list_all), which is acceptable at this scale. For larger registries,
        consider sharding or read-write locks.

    Example:
        .. code-block:: python

            from omnibase_core.services.registry.service_registry_capability import (
                ServiceRegistryCapability,
            )
            from omnibase_core.models.capabilities.model_capability_metadata import (
                ModelCapabilityMetadata,
            )
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            registry = ServiceRegistryCapability()

            # Register a capability
            cap = ModelCapabilityMetadata(
                capability="database.relational",
                name="Relational Database",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="SQL-based relational database",
                tags=("storage", "sql"),
            )
            registry.register(cap)

            # Look up by ID
            found = registry.get("database.relational")

            # Find by tags
            sql_caps = registry.find_by_tags(["sql"])

    Attributes:
        _capabilities: Internal dict mapping capability ID to metadata.
        _lock: RLock for thread synchronization.

    .. versionadded:: 0.4.0
    """

    def __init__(self) -> None:
        """
        Initialize an empty ServiceRegistryCapability.

        Creates an empty registry with a fresh RLock for thread synchronization.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()
                assert len(registry.list_all()) == 0
        """
        self._capabilities: dict[str, ModelCapabilityMetadata] = {}
        self._lock = threading.RLock()

    def register(
        self, capability: ModelCapabilityMetadata, replace: bool = False
    ) -> None:
        """
        Register a capability in the registry.

        Adds the capability metadata to the registry, keyed by its capability
        identifier. If a capability with the same ID already exists and
        replace=False, raises ModelOnexError. If replace=True, the existing
        capability is overwritten.

        Args:
            capability: The ModelCapabilityMetadata instance to register.
            replace: If True, allows overwriting an existing capability.
                If False (default), raises ModelOnexError on duplicate.

        Raises:
            ModelOnexError: If capability.capability already exists in the
                registry and replace=False. Raised with error code
                EnumCoreErrorCode.DUPLICATE_REGISTRATION and context
                containing the duplicate capability identifier.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()

                # Register a new capability
                registry.register(cap)

                # This raises ModelOnexError (duplicate)
                registry.register(cap)  # Raises!

                # This succeeds (replace=True)
                registry.register(cap, replace=True)

        Thread Safety:
            This method is protected by an RLock and is thread-safe.

        .. versionadded:: 0.4.0
        """
        self._register_impl(capability, replace)

    @standard_error_handling("Capability registration")
    def _register_impl(
        self, capability: ModelCapabilityMetadata, replace: bool = False
    ) -> None:
        """Internal implementation of capability registration."""
        with self._lock:
            if capability.capability in self._capabilities and not replace:
                raise ModelOnexError(
                    message=f"Capability '{capability.capability}' already registered. "
                    "Use replace=True to overwrite.",
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                    context={"capability": capability.capability},
                )
            self._capabilities[capability.capability] = capability

    def unregister(
        self, capability_id: str
    ) -> bool:  # id-ok: semantic capability identifier
        """
        Unregister a capability by its ID.

        Removes the capability with the given ID from the registry. Returns
        True if the capability was found and removed, False if it was not
        found.

        Args:
            capability_id: The semantic capability identifier to remove.

        Returns:
            bool: True if the capability was found and removed, False if
                the capability_id was not in the registry.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()
                registry.register(cap)

                # Remove the capability
                removed = registry.unregister("database.relational")
                assert removed is True

                # Try to remove again
                removed = registry.unregister("database.relational")
                assert removed is False

        Thread Safety:
            This method is protected by an RLock and is thread-safe.

        .. versionadded:: 0.4.0
        """
        with self._lock:
            return self._capabilities.pop(capability_id, None) is not None

    def get(
        self, capability_id: str
    ) -> ModelCapabilityMetadata | None:  # id-ok: semantic capability identifier
        """
        Get capability metadata by ID.

        Looks up a capability by its semantic identifier and returns the
        metadata if found, or None if not found.

        Args:
            capability_id: The semantic capability identifier to look up.

        Returns:
            ModelCapabilityMetadata: The capability metadata if found.
            None: If no capability with that ID exists.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()
                registry.register(cap)

                # Found
                found = registry.get("database.relational")
                assert found is not None

                # Not found
                missing = registry.get("nonexistent")
                assert missing is None

        Thread Safety:
            This method is protected by an RLock and is thread-safe.

        .. versionadded:: 0.4.0
        """
        with self._lock:
            return self._capabilities.get(capability_id)

    def list_all(self) -> list[ModelCapabilityMetadata]:
        """
        List all registered capabilities.

        Returns a list of all capabilities in the registry, in insertion
        order. Returns an empty list if the registry is empty.

        Returns:
            list[ModelCapabilityMetadata]: All registered capabilities
                in insertion order.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()
                registry.register(cap1)
                registry.register(cap2)

                all_caps = registry.list_all()
                assert len(all_caps) == 2
                assert all_caps[0] == cap1
                assert all_caps[1] == cap2

        Thread Safety:
            This method is protected by an RLock and returns a snapshot
            (copy) of the current capabilities. The returned list is
            independent of the registry state.

        .. versionadded:: 0.4.0
        """
        return self._list_all_impl()

    @standard_error_handling("Capability listing")
    def _list_all_impl(self) -> list[ModelCapabilityMetadata]:
        """Internal implementation of list_all."""
        with self._lock:
            # Lock held during iteration - acceptable for < 1,000 entries.
            # Returns a snapshot copy independent of registry mutations.
            return list(self._capabilities.values())

    def find_by_tags(
        self, tags: list[str], match_all: bool = False
    ) -> list[ModelCapabilityMetadata]:
        """
        Find capabilities by tags.

        Searches for capabilities that have matching tags. By default
        (match_all=False), returns capabilities that have ANY of the
        specified tags. If match_all=True, returns only capabilities
        that have ALL of the specified tags.

        Args:
            tags: List of tags to search for. Must not be empty for
                match_all=True to produce meaningful results.
            match_all: If True, capabilities must have ALL specified tags.
                If False (default), capabilities must have ANY specified tag.

        Returns:
            list[ModelCapabilityMetadata]: Capabilities matching the tag
                criteria, in insertion order. Empty list if no matches.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()
                # Register capabilities with different tags
                registry.register(cap_with_tags_sql_storage)
                registry.register(cap_with_tags_nosql_storage)
                registry.register(cap_with_tags_cache)

                # Find any with "storage" tag
                storage_caps = registry.find_by_tags(["storage"])
                assert len(storage_caps) == 2

                # Find any with "sql" OR "cache" tags
                some_caps = registry.find_by_tags(["sql", "cache"])
                assert len(some_caps) == 2  # sql_storage and cache

                # Find only with both "sql" AND "storage" tags
                sql_storage = registry.find_by_tags(
                    ["sql", "storage"], match_all=True
                )
                assert len(sql_storage) == 1

        Thread Safety:
            This method is protected by an RLock and is thread-safe.

        .. versionadded:: 0.4.0
        """
        return self._find_by_tags_impl(tags, match_all)

    @standard_error_handling("Capability tag search")
    def _find_by_tags_impl(
        self, tags: list[str], match_all: bool = False
    ) -> list[ModelCapabilityMetadata]:
        """Internal implementation of find_by_tags."""
        with self._lock:
            # Empty tag list matches nothing - avoids Python's `all([]) == True` trap
            # which would otherwise cause match_all=True to return ALL items.
            if not tags:
                return []

            def matches(cap: ModelCapabilityMetadata) -> bool:
                if match_all:
                    return all(tag in cap.tags for tag in tags)
                return any(tag in cap.tags for tag in tags)

            # Lock held during iteration - acceptable for < 1,000 entries.
            # For larger registries, consider sharding by namespace.
            return [c for c in self._capabilities.values() if matches(c)]

    @property
    def count(self) -> int:
        """
        Get the number of registered capabilities.

        Returns:
            int: The number of capabilities in the registry.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()
                assert registry.count == 0

                registry.register(cap)
                assert registry.count == 1

        Thread Safety:
            This property is protected by an RLock and is thread-safe.

        .. versionadded:: 0.4.0
        """
        with self._lock:
            return len(self._capabilities)

    def clear(self) -> None:
        """
        Remove all capabilities from the registry.

        Clears the registry, removing all registered capabilities.

        Example:
            .. code-block:: python

                registry = ServiceRegistryCapability()
                registry.register(cap1)
                registry.register(cap2)
                assert registry.count == 2

                registry.clear()
                assert registry.count == 0

        Thread Safety:
            This method is protected by an RLock and is thread-safe.

        .. versionadded:: 0.4.0
        """
        with self._lock:
            self._capabilities.clear()

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns:
            str: Format "ServiceRegistryCapability[count=N]"
        """
        return f"ServiceRegistryCapability[count={self.count}]"

    def __repr__(self) -> str:
        """
        Detailed representation for debugging.

        Returns:
            str: Format with capability IDs.
        """
        with self._lock:
            ids = list(self._capabilities.keys())
            if len(ids) > 5:
                ids_repr = f"<{len(ids)} capabilities>"
            else:
                ids_repr = repr(ids)
            return f"ServiceRegistryCapability(capabilities={ids_repr})"
