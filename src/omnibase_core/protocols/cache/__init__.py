"""
Cache protocols for distributed caching backend abstraction.

This module provides protocol definitions for cache backends that can be used
with MixinCaching for L2 (distributed) caching support.

Protocols:
    - ProtocolCacheBackend: Async cache backend interface for L2 distributed caches

Usage:
    from omnibase_core.protocols.cache import ProtocolCacheBackend

    class MyCustomBackend:
        async def get(self, key: str) -> Any | None:
            ...

        async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
            ...

        async def delete(self, key: str) -> None:
            ...

        async def clear(self) -> None:
            ...

        async def exists(self, key: str) -> bool:
            ...

.. versionadded:: 0.5.0
"""

from omnibase_core.protocols.cache.protocol_cache_backend import ProtocolCacheBackend

__all__ = ["ProtocolCacheBackend"]
