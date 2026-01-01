"""
MixinCaching - Result Caching Mixin with L1/L2 Support

Provides result caching capabilities for ONEX nodes, particularly useful for
Compute and Reducer nodes that perform expensive operations.

Features:
    - L1 Cache: In-memory cache (fast, local, no network overhead)
    - L2 Cache: Optional distributed cache via ProtocolCacheBackend
    - TTL Enforcement: Time-based expiration for both L1 and L2
    - Graceful Degradation: Falls back to L1 if L2 is unavailable

L1/L2 Coordination:
    - Read path: L1 -> L2 (populate L1 on L2 hit)
    - Write path: Write to both L1 and L2
    - Invalidation: Remove from both L1 and L2

Usage:
    .. code-block:: python

        from omnibase_core.mixins import MixinCaching
        from omnibase_core.nodes import NodeCompute

        # Basic usage (L1 only)
        class MyComputeNode(NodeCompute, MixinCaching):
            async def execute_compute(self, contract):
                cache_key = self.generate_cache_key(contract.input_data)
                cached = await self.get_cached(cache_key)
                if cached:
                    return cached

                result = await self._expensive_computation(contract)
                await self.set_cached(cache_key, result, ttl_seconds=600)
                return result

    .. code-block:: python

        from omnibase_core.backends.cache import BackendCacheRedis
        from omnibase_core.mixins import MixinCaching
        from omnibase_core.nodes import NodeCompute

        # With L2 Redis backend
        backend = BackendCacheRedis(url="redis://localhost:6379/0")
        await backend.connect()

        class MyComputeNode(NodeCompute, MixinCaching):
            def __init__(self, container):
                super().__init__(container, backend=backend)

Related:
    - OMN-1188: Redis/Valkey L2 backend for MixinCaching
    - ProtocolCacheBackend: Protocol for L2 cache backends
    - BackendCacheRedis: Default Redis implementation (in ``omnibase_core.backends.cache``)

.. versionchanged:: 0.5.0
    Added L2 cache support, TTL enforcement, and backend abstraction.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_mixin_types import TypedDictCacheStats

if TYPE_CHECKING:
    from omnibase_core.protocols.cache import ProtocolCacheBackend

logger = logging.getLogger(__name__)


class MixinCaching:
    """
    Mixin providing result caching capabilities with L1/L2 support.

    Provides an in-memory L1 cache with optional L2 distributed cache
    backend support. The L2 backend must implement ProtocolCacheBackend
    and is accessed asynchronously.

    L1/L2 Coordination:
        - **get_cached()**: Check L1 first, then L2 (populate L1 on L2 hit)
        - **set_cached()**: Write to both L1 and L2
        - **invalidate_cache()**: Remove from both L1 and L2
        - **clear_cache()**: Clear both L1 and L2

    TTL Enforcement:
        L1 cache entries include timestamp and TTL for time-based expiration.
        Expired entries are lazily removed on access.

    TTL Values:
        - ``ttl_seconds=None``: Uses ``default_ttl_seconds`` if set, otherwise no expiration.
        - ``ttl_seconds=0``: Entry expires immediately (effectively no caching for L1).
        - ``ttl_seconds > 0``: Entry expires after the specified duration.

    TTL Behavior on L2 Hit:
        When L1 is populated from an L2 cache hit, the original L2 TTL is NOT
        preserved. Instead, the L1 entry uses ``default_ttl_seconds``. This is
        because the remaining L2 TTL is not available through the cache protocol.
        As a result, L1 entries populated from L2 may expire at different times
        than the original L2 entries.

    Graceful Degradation:
        If L2 backend is unavailable or operations fail, the mixin
        falls back to L1 cache only without raising errors. Errors are
        wrapped in ModelOnexError with appropriate error codes and logged.

    Attributes:
        _cache_enabled: Whether caching is enabled
        _cache_data: L1 in-memory cache storage
        _cache_backend: Optional L2 distributed cache backend
        _default_ttl_seconds: Default TTL for cache entries

    Example:
        .. code-block:: python

            from omnibase_core.backends.cache import BackendCacheRedis
            from omnibase_core.mixins import MixinCaching
            from omnibase_core.nodes import NodeCompute

            # Create Redis backend for L2
            backend = BackendCacheRedis(url="redis://localhost:6379/0")
            await backend.connect()

            class MyNode(NodeCompute, MixinCaching):
                def __init__(self, container):
                    super().__init__(container, backend=backend)

                async def compute(self, data):
                    cache_key = self.generate_cache_key(data)

                    # Try to get from cache (L1 -> L2)
                    cached = await self.get_cached(cache_key)
                    if cached is not None:
                        return cached

                    # Compute and cache result
                    result = await self._expensive_operation(data)
                    await self.set_cached(cache_key, result, ttl_seconds=600)
                    return result

    .. versionchanged:: 0.5.0
        Added L2 backend support, TTL enforcement, and graceful degradation.
    """

    # Type: L1 cache entry format: (value, expiry_timestamp)
    # expiry_timestamp is None for entries without TTL
    _cache_data: dict[str, tuple[object, float | None]]

    def __init__(
        self,
        *args: Any,
        backend: ProtocolCacheBackend | None = None,
        default_ttl_seconds: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize caching mixin.

        Args:
            *args: Arguments passed to parent class.
            backend: Optional L2 cache backend implementing ProtocolCacheBackend.
                If None, only L1 in-memory caching is used.
            default_ttl_seconds: Default TTL for cache entries. If None,
                entries don't expire unless explicitly set.
            **kwargs: Keyword arguments passed to parent class.
        """
        super().__init__(*args, **kwargs)
        self._cache_enabled = True
        # L1 cache: key -> (value, expiry_timestamp)
        self._cache_data: dict[str, tuple[object, float | None]] = {}
        # L2 backend (optional)
        self._cache_backend: ProtocolCacheBackend | None = backend
        self._default_ttl_seconds = default_ttl_seconds

    def generate_cache_key(self, data: Any) -> str:
        """
        Generate a cache key from data.

        Args:
            data: Data to generate cache key from

        Returns:
            Cache key string (SHA256 hash)
        """
        # Serialize data to JSON and hash it
        try:
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except (TypeError, ValueError):
            # Fallback for non-serializable data
            return hashlib.sha256(str(data).encode()).hexdigest()

    def _is_expired(self, expiry: float | None) -> bool:
        """Check if a cache entry has expired."""
        if expiry is None:
            return False
        return time.time() > expiry

    def _cleanup_expired_entries(self) -> list[str]:
        """
        Remove all expired entries from L1 cache.

        Returns:
            List of keys that were removed due to expiration.
        """
        now = time.time()
        expired_keys = [
            k
            for k, (_, expiry) in self._cache_data.items()
            if expiry is not None and now > expiry
        ]
        for k in expired_keys:
            del self._cache_data[k]
        return expired_keys

    def _get_l1(self, cache_key: str) -> tuple[Any | None, bool]:
        """
        Get value from L1 cache.

        Returns:
            Tuple of (value, found). Value is None if not found or expired.
        """
        if cache_key not in self._cache_data:
            return None, False

        value, expiry = self._cache_data[cache_key]

        # Check expiry
        if self._is_expired(expiry):
            # Remove expired entry
            del self._cache_data[cache_key]
            return None, False

        return value, True

    def _compute_expiry(self, ttl_seconds: int | None) -> float | None:
        """
        Compute expiry timestamp based on TTL.

        Args:
            ttl_seconds: Time-to-live in seconds. If None, uses default_ttl_seconds.

        Returns:
            Expiry timestamp, or None for no expiration.

        Note:
            - ttl_seconds=0 means immediate expiration (entry expires at creation time)
            - ttl_seconds=None with no default means no expiration
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        if ttl is None:
            return None
        # ttl=0 means immediate expiration
        return time.time() + ttl

    def _set_l1(
        self, cache_key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        """Store value in L1 cache."""
        expiry = self._compute_expiry(ttl_seconds)
        self._cache_data[cache_key] = (value, expiry)

    def _is_backend_connected(self) -> bool:
        """
        Check if L2 backend is connected and ready for operations.

        Returns:
            True if backend is connected, False otherwise.
        """
        if self._cache_backend is None:
            return False
        # Check if backend has is_connected method and use it
        if hasattr(self._cache_backend, "is_connected"):
            return bool(self._cache_backend.is_connected())
        # If no is_connected method, assume connected if backend exists
        return True

    def _wrap_cache_error(
        self,
        exception: Exception,
        operation: str,
        cache_key: str | None = None,
    ) -> ModelOnexError:
        """
        Wrap a cache exception in ModelOnexError with appropriate error code.

        Args:
            exception: The original exception
            operation: Description of the cache operation (e.g., "get", "set", "delete")
            cache_key: The cache key involved, if applicable

        Returns:
            ModelOnexError wrapping the original exception
        """
        # Determine appropriate error code based on exception type
        if isinstance(exception, ConnectionError):
            error_code = EnumCoreErrorCode.CACHE_CONNECTION_ERROR
        elif isinstance(exception, TimeoutError):
            error_code = EnumCoreErrorCode.CACHE_TIMEOUT_ERROR
        elif isinstance(exception, OSError):
            # OSError can indicate network or connection issues
            error_code = EnumCoreErrorCode.CACHE_BACKEND_ERROR
        else:
            error_code = EnumCoreErrorCode.CACHE_OPERATION_FAILED

        context: dict[str, Any] = {"operation": operation}
        if cache_key is not None:
            context["cache_key"] = cache_key

        return ModelOnexError.from_exception(
            exception,
            error_code=error_code,
            **context,
        )

    async def get_cached(self, cache_key: str) -> Any | None:
        """
        Retrieve cached value from L1, then L2.

        Read path:
            1. Check L1 cache first (fast, in-memory)
            2. If L1 miss, check L2 cache (distributed)
            3. If L2 hit, populate L1 and return

        Args:
            cache_key: Cache key to retrieve

        Returns:
            Cached value or None if not found
        """
        if not self._cache_enabled:
            return None

        # Try L1 first
        value, found = self._get_l1(cache_key)
        if found:
            return value

        # Try L2 if available and connected
        if self._cache_backend is not None:
            if not self._is_backend_connected():
                logger.warning(
                    "L2 cache backend not connected for key '%s'",
                    cache_key,
                )
                return None

            try:
                l2_value = await self._cache_backend.get(cache_key)
                if l2_value is not None:
                    # Populate L1 from L2 hit
                    # Note: We don't know the original TTL, so use default
                    self._set_l1(cache_key, l2_value, self._default_ttl_seconds)
                    return l2_value
            except (ConnectionError, TimeoutError, OSError) as e:
                # Graceful degradation - log structured error and continue with L1 miss
                error = self._wrap_cache_error(e, "get", cache_key)
                logger.warning(
                    "L2 cache get failed for key '%s': %s",
                    cache_key,
                    error,
                )
            except Exception as e:
                # Catch any other unexpected exceptions from the backend
                error = self._wrap_cache_error(e, "get", cache_key)
                logger.warning(
                    "L2 cache get failed unexpectedly for key '%s': %s",
                    cache_key,
                    error,
                )

        return None

    async def set_cached(
        self, cache_key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        """
        Store value in cache (both L1 and L2).

        Write path:
            1. Write to L1 (in-memory)
            2. Write to L2 (distributed) if available

        Args:
            cache_key: Cache key to store under
            value: Value to cache
            ttl_seconds: Time-to-live in seconds. If None, uses default_ttl_seconds.
                If 0, entry expires immediately (effectively skips caching for L1).
        """
        if not self._cache_enabled:
            return

        # Determine TTL
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds

        # For ttl=0, skip L1 caching as it would expire immediately
        # But still write to L2 if available (L2 may handle ttl=0 differently)
        if ttl != 0:
            # Write to L1
            self._set_l1(cache_key, value, ttl)

        # Write to L2 if available and connected
        if self._cache_backend is not None:
            if not self._is_backend_connected():
                logger.warning(
                    "L2 cache backend not connected for set on key '%s'",
                    cache_key,
                )
                return

            try:
                await self._cache_backend.set(cache_key, value, ttl)
            except (ConnectionError, TimeoutError, OSError) as e:
                # Graceful degradation - log structured error and continue with L1 only
                error = self._wrap_cache_error(e, "set", cache_key)
                logger.warning(
                    "L2 cache set failed for key '%s': %s",
                    cache_key,
                    error,
                )
            except Exception as e:
                # Catch any other unexpected exceptions from the backend
                error = self._wrap_cache_error(e, "set", cache_key)
                logger.warning(
                    "L2 cache set failed unexpectedly for key '%s': %s",
                    cache_key,
                    error,
                )

    async def invalidate_cache(self, cache_key: str) -> None:
        """
        Invalidate a cache entry from both L1 and L2.

        Args:
            cache_key: Cache key to invalidate
        """
        # Remove from L1
        self._cache_data.pop(cache_key, None)

        # Remove from L2 if available and connected
        if self._cache_backend is not None:
            if not self._is_backend_connected():
                logger.warning(
                    "L2 cache backend not connected for delete on key '%s'",
                    cache_key,
                )
                return

            try:
                await self._cache_backend.delete(cache_key)
            except (ConnectionError, TimeoutError, OSError) as e:
                error = self._wrap_cache_error(e, "delete", cache_key)
                logger.warning(
                    "L2 cache delete failed for key '%s': %s",
                    cache_key,
                    error,
                )
            except Exception as e:
                # Catch any other unexpected exceptions from the backend
                error = self._wrap_cache_error(e, "delete", cache_key)
                logger.warning(
                    "L2 cache delete failed unexpectedly for key '%s': %s",
                    cache_key,
                    error,
                )

    async def clear_cache(self) -> None:
        """Clear all cache entries from both L1 and L2."""
        # Clear L1
        self._cache_data.clear()

        # Clear L2 if available and connected
        if self._cache_backend is not None:
            if not self._is_backend_connected():
                logger.warning("L2 cache backend not connected for clear operation")
                return

            try:
                await self._cache_backend.clear()
            except (ConnectionError, TimeoutError, OSError) as e:
                error = self._wrap_cache_error(e, "clear")
                logger.warning("L2 cache clear failed: %s", error)
            except Exception as e:
                # Catch any other unexpected exceptions from the backend
                error = self._wrap_cache_error(e, "clear")
                logger.warning("L2 cache clear failed unexpectedly: %s", error)

    def get_cache_stats(self) -> TypedDictCacheStats:
        """
        Get cache statistics.

        Returns:
            Typed dictionary with cache statistics including:
            - enabled: Whether caching is enabled
            - entries: Number of L1 cache entries (excluding expired)
            - keys: List of L1 cache keys

        Note:
            This method cleans up expired entries before returning statistics.
            Does not include L2 statistics. For L2 stats, check the
            backend directly if it provides a stats method.
        """
        # Clean up expired entries for accurate count using helper method
        self._cleanup_expired_entries()

        return TypedDictCacheStats(
            enabled=self._cache_enabled,
            entries=len(self._cache_data),
            keys=list(self._cache_data.keys()),
        )

    def has_l2_backend(self) -> bool:
        """Check if L2 backend is configured."""
        return self._cache_backend is not None

    def is_l2_connected(self) -> bool:
        """
        Check if L2 backend is connected and ready.

        Returns:
            True if L2 backend is configured and connected, False otherwise.
        """
        return self._is_backend_connected()
