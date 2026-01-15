"""
ProtocolToolCache - Protocol for tool cache implementations.

This protocol defines the interface for tool cache implementations,
enabling duck typing across different implementations without requiring direct
inheritance.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations (MemoryMappedToolCache in omnibase_core.cache or custom)
    satisfy the contract. This enables consistent tool caching behavior
    across the ONEX ecosystem while allowing implementation flexibility.

Thread Safety:
    WARNING: Thread safety is implementation-specific. Callers should verify
    the thread safety guarantees of their chosen implementation.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.compute import ProtocolToolCache

        def lookup_cached_tool(
            cache: ProtocolToolCache,
            tool_name: str,
        ) -> dict[str, object] | None:
            '''Look up a tool from the cache.'''
            return cache.lookup_tool(tool_name)

Related:
    - ModelONEXContainer: Primary consumer of ToolCache implementations
    - MemoryMappedToolCache: Reference implementation (optional import)

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = [
    "ProtocolToolCache",
]

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolToolCache(Protocol):
    """
    Protocol for tool cache implementations.

    Defines the interface for tool caching used by ModelONEXContainer
    to cache tool metadata for faster lookups.

    Required Methods:
        - lookup_tool: Look up tool metadata by name
        - get_cache_stats: Get current cache statistics
        - close: Clean up cache resources

    Thread Safety:
        WARNING: Implementations are NOT guaranteed to be thread-safe.
        See implementation-specific documentation for thread safety guarantees.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.compute import ProtocolToolCache

            class SimpleToolCache:
                '''Minimal tool cache implementation.'''

                def __init__(self) -> None:
                    self._cache: dict[str, dict[str, object]] = {}
                    self._hits = 0
                    self._misses = 0

                def lookup_tool(self, name: str) -> dict[str, object] | None:
                    if name in self._cache:
                        self._hits += 1
                        return self._cache[name]
                    self._misses += 1
                    return None

                def get_cache_stats(self) -> dict[str, object]:
                    return {
                        "size": len(self._cache),
                        "hits": self._hits,
                        "misses": self._misses,
                    }

                def close(self) -> None:
                    self._cache.clear()

            # Verify protocol conformance
            cache: ProtocolToolCache = SimpleToolCache()
            assert isinstance(cache, ProtocolToolCache)

    .. versionadded:: 0.4.0
    """

    def lookup_tool(self, name: str) -> dict[str, object] | None:
        """
        Look up tool metadata by name.

        Args:
            name: The name of the tool to look up

        Returns:
            Tool metadata dictionary if found, None otherwise

        Note:
            Implementations should handle cache misses gracefully
            and return None rather than raising exceptions.
        """
        ...

    def get_cache_stats(self) -> dict[str, object]:
        """
        Get current cache statistics.

        Returns:
            Dictionary containing cache statistics. Typical fields include:
            - size: Number of cached entries
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Percentage of successful lookups

        Note:
            This method is synchronous for efficient statistics retrieval.
        """
        ...

    def close(self) -> None:
        """
        Clean up cache resources.

        This method should release any held resources such as:
        - Memory-mapped files
        - File handles
        - Network connections

        Call this when shutting down the application to ensure
        proper resource cleanup.

        Note:
            After calling close(), the cache should not be used.
            Behavior of other methods after close() is undefined.
        """
        ...
