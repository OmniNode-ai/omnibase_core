"""
BackendCacheRedis - Redis/Valkey implementation of ProtocolCacheBackend.

This module provides an async Redis backend for L2 distributed caching
with MixinCaching. It supports connection pooling, JSON serialization,
and TTL enforcement.

Requirements:
    The redis package is an optional dependency. Install with:
    poetry install -E cache

    Or add to pyproject.toml:
    [project.optional-dependencies]
    cache = ["redis>=5.0.0"]

Usage:
    .. code-block:: python

        from omnibase_core.backends.cache import BackendCacheRedis

        # Create and connect
        backend = BackendCacheRedis(url="redis://localhost:6379/0")
        await backend.connect()

        # Use for caching
        await backend.set("key", {"data": "value"}, ttl_seconds=300)
        data = await backend.get("key")

        # Cleanup
        await backend.close()

    Integration with MixinCaching:

    .. code-block:: python

        from omnibase_core.backends.cache import BackendCacheRedis
        from omnibase_core.mixins import MixinCaching
        from omnibase_core.nodes import NodeCompute

        backend = BackendCacheRedis(url="redis://localhost:6379/0")
        await backend.connect()

        class MyNode(NodeCompute, MixinCaching):
            def __init__(self, container):
                super().__init__(container, backend=backend)

Related:
    - OMN-1188: Redis/Valkey L2 backend for MixinCaching
    - ProtocolCacheBackend: Protocol this class implements
    - MixinCaching: Consumer of this backend

.. versionadded:: 0.5.0
"""

from __future__ import annotations

__all__ = [
    "BackendCacheRedis",
    "REDIS_AVAILABLE",
    "sanitize_redis_url",
    "sanitize_error_message",
]

import importlib
import importlib.util
import json
import logging
import re
from types import ModuleType
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

from omnibase_core.enums import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Type-only imports for static analysis (ADR-005 compliant)
# These are only evaluated by type checkers, not at runtime
if TYPE_CHECKING:
    from redis.asyncio import Redis
    from redis.asyncio.connection import ConnectionPool as ConnectionPoolType

logger = logging.getLogger(__name__)


def _check_redis_available() -> bool:
    """Check if redis package is available without violating ADR-005.

    Uses importlib.util.find_spec to check module availability without
    actually importing the transport library at module level.

    Returns:
        True if redis.asyncio is importable, False otherwise.
    """
    try:
        spec = importlib.util.find_spec("redis.asyncio")
        return spec is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


# Check if redis is available (optional dependency)
REDIS_AVAILABLE = _check_redis_available()

# Cached module references (lazily loaded via importlib)
_redis_module: ModuleType | None = None
_redis_exceptions_module: ModuleType | None = None


def _get_redis_module() -> ModuleType:
    """Lazy-load and cache redis.asyncio module.

    Uses importlib.import_module to load the redis library at runtime,
    avoiding direct import statements that would violate ADR-005.
    The module is cached after first load.

    Returns:
        The redis.asyncio module.

    Raises:
        RuntimeError: If redis package is not installed.
    """
    global _redis_module
    if _redis_module is None:
        if not REDIS_AVAILABLE:
            # error-ok: RuntimeError appropriate for missing optional dependency
            raise RuntimeError(
                "Redis package not installed. Install with: poetry install -E cache"
            )
        _redis_module = importlib.import_module("redis.asyncio")
    return _redis_module


def _get_connection_pool_class() -> type:
    """Get the ConnectionPool class from redis.asyncio.connection.

    Returns:
        The ConnectionPool class.

    Raises:
        RuntimeError: If redis package is not installed.
    """
    connection_module = importlib.import_module("redis.asyncio.connection")
    # NOTE(OMN-1302): Dynamic import returns `redis.asyncio.connection.ConnectionPool`. Safe because redis package installed.
    return connection_module.ConnectionPool  # type: ignore[no-any-return]


def _get_redis_exceptions() -> ModuleType:
    """Lazy-load and cache redis.exceptions module.

    Returns:
        The redis.exceptions module.
    """
    global _redis_exceptions_module
    if _redis_exceptions_module is None:
        _redis_exceptions_module = importlib.import_module("redis.exceptions")
    return _redis_exceptions_module


def _get_redis_error_class() -> type[Exception]:
    """Get the RedisError exception class, or Exception as fallback.

    Returns:
        RedisError class if redis is available, otherwise Exception.
    """
    if REDIS_AVAILABLE:
        # NOTE(OMN-1302): Dynamic import returns `redis.exceptions.RedisError`. Safe because redis package installed.
        return _get_redis_exceptions().RedisError  # type: ignore[no-any-return]
    return Exception


def sanitize_redis_url(url: str) -> str:
    """
    Remove credentials from Redis URL for safe logging.

    Strips password (and optionally username) from Redis URLs to prevent
    credential leakage in logs, error messages, and monitoring systems.

    Args:
        url: Redis connection URL, potentially containing credentials.
            Format: redis://[username:password@]host[:port][/database]

    Returns:
        Sanitized URL with password replaced by '***'.
        Returns 'redis://***' if parsing fails, or original URL if no password present.

    Example:
        >>> sanitize_redis_url("redis://:secretpass@localhost:6379/0")
        'redis://:***@localhost:6379/0'
        >>> sanitize_redis_url("redis://user:pass@host:6379")
        'redis://user:***@host:6379'
        >>> sanitize_redis_url("redis://localhost:6379/0")
        'redis://localhost:6379/0'

    .. versionadded:: 0.5.0
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            # Reconstruct netloc with masked password
            if parsed.username:
                safe_netloc = f"{parsed.username}:***@{parsed.hostname}"
            else:
                safe_netloc = f":***@{parsed.hostname}"
            if parsed.port:
                safe_netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=safe_netloc))
        return url
    except (
        AttributeError,
        TypeError,
        ValueError,
    ):  # fallback-ok: use original URL if parsing fails
        return "redis://***"


# Pattern to match Redis URLs with potential credentials
# Matches redis:// or rediss:// followed by optional user:pass@ and host:port/db
_REDIS_URL_PATTERN = re.compile(
    r"(rediss?://)([^@\s]+@)?([^\s/]+)(/\d+)?",
    re.IGNORECASE,
)


def sanitize_error_message(message: str) -> str:
    """
    Sanitize error messages that may contain Redis URLs with credentials.

    Scans the message for Redis URLs and replaces any credentials with '***'.
    This prevents credential leakage when logging exception messages from
    the Redis library.

    Args:
        message: Error message that may contain Redis URLs.

    Returns:
        Sanitized message with any Redis URL credentials masked.

    Example:
        >>> sanitize_error_message("Error connecting to redis://:secret@host:6379/0")
        'Error connecting to redis://:***@host:6379/0'
        >>> sanitize_error_message("Connection refused")
        'Connection refused'

    .. versionadded:: 0.5.0
    """

    def _replace_url(match: re.Match[str]) -> str:
        scheme = match.group(1)  # redis:// or rediss://
        auth = match.group(2)  # user:pass@ or :pass@ or None
        host_port = match.group(3)  # host:port
        database = match.group(4) or ""  # /0 or empty

        if auth:
            # Has credentials - mask them
            if ":" in auth[:-1]:  # Has username:password
                username = auth.split(":")[0]
                return f"{scheme}{username}:***@{host_port}{database}"
            else:
                # Only password (:pass@) or just @ (unusual)
                return f"{scheme}:***@{host_port}{database}"
        else:
            # No credentials - return as-is
            return match.group(0)

    return _REDIS_URL_PATTERN.sub(_replace_url, message)


class BackendCacheRedis:
    """
    Redis/Valkey cache backend implementing ProtocolCacheBackend.

    Provides async cache operations with JSON serialization, connection
    pooling, and graceful error handling. All operations are designed
    to fail silently to allow MixinCaching to fall back to L1 cache.

    Thread Safety:
        This class uses async operations via redis-py's asyncio support.
        Connection pooling handles concurrent access safely.

    Attributes:
        url: Redis connection URL (e.g., "redis://localhost:6379/0")
        prefix: Optional key prefix for namespacing
        default_ttl: Default TTL in seconds (None = no expiration)

    Example:
        .. code-block:: python

            from omnibase_core.backends.cache import BackendCacheRedis

            async def main():
                # Create backend with connection pool
                backend = BackendCacheRedis(
                    url="redis://localhost:6379/0",
                    prefix="myapp:",
                    default_ttl=3600,
                )
                await backend.connect()

                try:
                    # Store with TTL
                    await backend.set("user:123", {"name": "Alice"}, ttl_seconds=300)

                    # Retrieve
                    user = await backend.get("user:123")
                    print(user)  # {"name": "Alice"}

                    # Check existence
                    exists = await backend.exists("user:123")
                    print(exists)  # True

                    # Delete
                    await backend.delete("user:123")
                finally:
                    await backend.close()

    .. versionadded:: 0.5.0
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        prefix: str = "",
        default_ttl: int | None = None,
        max_connections: int = 10,
    ) -> None:
        """
        Initialize Redis backend.

        Args:
            url: Redis connection URL. Supports redis:// and rediss:// schemes.
                Format: redis://[username:password@]host[:port][/database]
            prefix: Key prefix for namespacing. All keys will be prefixed
                with this string.
            default_ttl: Default TTL in seconds. If None, entries don't
                expire unless explicitly set.
            max_connections: Maximum connections in the pool.

        Raises:
            RuntimeError: If redis package is not installed.
        """
        if not REDIS_AVAILABLE:
            # error-ok: RuntimeError appropriate for missing optional dependency
            raise RuntimeError(
                "Redis package not installed. Install with: poetry install -E cache"
            )

        self._url = url
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._max_connections = max_connections
        self._pool: ConnectionPoolType | None = None
        self._client: Redis | None = None
        self._connected = False

    @property
    def _safe_url(self) -> str:
        """Return URL with credentials masked for safe logging."""
        return sanitize_redis_url(self._url)

    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self._prefix}{key}"

    def _validate_connection(self) -> bool:
        """
        Validate that connection is established and client is available.

        Centralizes connection state validation for all operations.
        Returns False if not connected, allowing graceful fallback.

        Returns:
            True if connection is valid and client is available.
            False if disconnected or client is None.
        """
        if not self._connected:
            return False
        if self._client is None:
            # State inconsistency - mark as disconnected
            self._connected = False
            return False
        return True

    async def __aenter__(self) -> BackendCacheRedis:
        """
        Async context manager entry - establishes connection.

        Example:
            .. code-block:: python

                async with BackendCacheRedis(url="redis://localhost:6379") as cache:
                    await cache.set("key", "value")
                # Connection automatically closed on exit

        Returns:
            Self for use in async with block.
        """
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """
        Async context manager exit - ensures connection cleanup.

        Cleanup happens regardless of whether an exception occurred,
        ensuring no resource leaks.
        """
        await self.close()

    async def connect(self) -> None:
        """
        Establish connection to Redis.

        Creates a connection pool and verifies connectivity with a ping.
        Should be called before using any cache operations.

        Raises:
            ConnectionError: If unable to connect to Redis.
            RuntimeError: If redis package is not installed.
        """
        if self._connected:
            return

        # Get redis module lazily (ADR-005 compliant)
        if not REDIS_AVAILABLE:
            # error-ok: RuntimeError appropriate for missing optional dependency
            raise RuntimeError(
                "Redis package not installed. Install with: poetry install -E cache"
            )

        redis_module = _get_redis_module()
        RedisError = _get_redis_error_class()

        try:
            self._pool = redis_module.ConnectionPool.from_url(
                self._url,
                max_connections=self._max_connections,
                decode_responses=True,
            )
            self._client = redis_module.Redis(connection_pool=self._pool)
            # Verify connection - assert for type narrowing
            assert self._client is not None  # Narrow type for pyright
            await self._client.ping()
            self._connected = True
            # Don't log URL - may contain credentials
            logger.debug("Connected to Redis")
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # Sanitize error message to prevent credential leakage
            safe_error = sanitize_error_message(str(e))
            # Use error not exception - traceback will be at caller level after re-raise
            logger.error("Failed to connect to Redis: %s", safe_error)  # noqa: TRY400
            # Cleanup on failure to prevent resource leaks
            await self._cleanup_on_connect_failure()
            raise ModelOnexError(
                message=f"Failed to connect to Redis: {safe_error}",
                error_code=EnumCoreErrorCode.CACHE_CONNECTION_ERROR,
                context={
                    "operation": "connect",
                    "cache_type": "L2",
                    "backend": "redis",
                },
            ) from e
        except Exception as e:  # boundary-ok: connection boundary must catch all
            # Sanitize error message to prevent credential leakage
            safe_error = sanitize_error_message(str(e))
            # Use error not exception - traceback will be at caller level after re-raise
            logger.error("Unexpected error connecting to Redis: %s", safe_error)  # noqa: TRY400
            await self._cleanup_on_connect_failure()
            raise ModelOnexError(
                message=f"Failed to connect to Redis: {safe_error}",
                error_code=EnumCoreErrorCode.CACHE_CONNECTION_ERROR,
                context={
                    "operation": "connect",
                    "cache_type": "L2",
                    "backend": "redis",
                    "unexpected": True,
                },
            ) from e

    async def _cleanup_on_connect_failure(self) -> None:
        """Clean up resources after a connection failure."""
        RedisError = _get_redis_error_class()
        try:
            if self._pool is not None:
                await self._pool.disconnect()
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # cleanup-resilience-ok: cleanup must complete even on expected errors
            logger.warning(
                "Error during connection cleanup: %s", sanitize_error_message(str(e))
            )
        except Exception as e:
            # cleanup-resilience-ok: catch-all ensures cleanup never fails unexpectedly
            logger.warning(
                "Unexpected error during connection cleanup: %s",
                sanitize_error_message(str(e)),
            )
        finally:
            self._pool = None
            self._client = None
            self._connected = False

    async def close(self) -> None:
        """
        Close Redis connection and cleanup resources.

        Should be called when the backend is no longer needed.
        Uses robust cleanup to ensure all resources are released
        even if individual cleanup steps fail.
        """
        RedisError = _get_redis_error_class()
        # Close client first, then pool - ensure partial failures don't prevent full cleanup
        try:
            if self._client:
                await self._client.close()
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # cleanup-resilience-ok: client cleanup must not prevent pool cleanup
            logger.warning(
                "Error closing Redis client: %s", sanitize_error_message(str(e))
            )
        except Exception as e:
            # cleanup-resilience-ok: catch-all ensures pool cleanup always runs
            logger.warning(
                "Unexpected error closing Redis client: %s",
                sanitize_error_message(str(e)),
            )
        finally:
            self._client = None

        try:
            if self._pool:
                await self._pool.disconnect()
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # cleanup-resilience-ok: pool cleanup errors should not propagate
            logger.warning(
                "Error disconnecting Redis pool: %s", sanitize_error_message(str(e))
            )
        except Exception as e:
            # cleanup-resilience-ok: catch-all ensures state is always reset
            logger.warning(
                "Unexpected error disconnecting Redis pool: %s",
                sanitize_error_message(str(e)),
            )
        finally:
            self._pool = None
            self._connected = False

        logger.debug("Disconnected from Redis")

    async def get(self, key: str) -> object | None:
        """
        Get cached value by key.

        Args:
            key: Cache key to retrieve.

        Returns:
            Cached value if found, None otherwise.
            Returns None on any error to allow graceful fallback.
        """
        if not self._validate_connection():
            return None
        # Type narrowing: _validate_connection ensures _client is not None
        assert self._client is not None

        RedisError = _get_redis_error_class()

        try:
            prefixed_key = self._make_key(key)
            data = await self._client.get(prefixed_key)
            if data is None:
                return None
            result: object = json.loads(data)
            return result
        except json.JSONDecodeError as e:
            # fallback-ok: return None for deserialization failures, allowing L1 cache fallback
            logger.warning(
                "Failed to deserialize cache value for key '%s': %s",
                key,
                sanitize_error_message(str(e)),
            )
            return None
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # fallback-ok: return None on Redis errors, allowing L1 cache fallback
            logger.warning(
                "Redis get failed for key '%s': %s", key, sanitize_error_message(str(e))
            )
            return None

    async def set(
        self, key: str, value: object, ttl_seconds: int | None = None
    ) -> None:
        """
        Store value in cache with optional TTL.

        Args:
            key: Cache key to store under.
            value: Value to cache. Must be JSON-serializable.
            ttl_seconds: Time-to-live in seconds. Uses default_ttl if None.
                If 0 or negative, the operation is skipped (no caching).

        Note:
            Zero or negative TTL values are treated as "do not cache" - the method
            returns immediately without storing. This prevents storing entries that
            would expire immediately or have invalid TTLs.
        """
        if not self._validate_connection():
            return
        # Type narrowing: _validate_connection ensures _client is not None
        assert self._client is not None

        # Determine TTL
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl

        # Skip caching entirely for zero or negative TTL values
        if ttl is not None and ttl <= 0:
            return

        RedisError = _get_redis_error_class()

        try:
            prefixed_key = self._make_key(key)
            data = json.dumps(value, default=str)

            if ttl is not None:
                await self._client.setex(prefixed_key, ttl, data)
            else:
                await self._client.set(prefixed_key, data)
        except (TypeError, ValueError) as e:
            # fallback-ok: silently skip caching on serialization failure
            logger.warning(
                "Failed to serialize cache value for key '%s': %s",
                key,
                sanitize_error_message(str(e)),
            )
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # fallback-ok: silently skip caching on Redis errors
            logger.warning(
                "Redis set failed for key '%s': %s", key, sanitize_error_message(str(e))
            )

    async def delete(self, key: str) -> None:
        """
        Delete a cache entry.

        Args:
            key: Cache key to delete.
        """
        if not self._validate_connection():
            return
        # Type narrowing: _validate_connection ensures _client is not None
        assert self._client is not None

        RedisError = _get_redis_error_class()

        try:
            prefixed_key = self._make_key(key)
            await self._client.delete(prefixed_key)
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # fallback-ok: silently ignore delete failures, cache entry may already be gone
            logger.warning(
                "Redis delete failed for key '%s': %s",
                key,
                sanitize_error_message(str(e)),
            )

    # Default batch size for SCAN operations
    SCAN_BATCH_SIZE: int = 100

    async def clear(self, batch_size: int | None = None) -> None:
        """
        Clear all cache entries with the configured prefix.

        Performance Warning:
            When a prefix is configured, this method uses Redis SCAN to find
            and delete matching keys. SCAN is O(N) where N is the total number
            of keys in the database (not just matching keys). For large datasets
            (100k+ keys), this operation may take several seconds or longer.

            Performance characteristics:
            - SCAN iterates through ALL keys in the database
            - Each batch requires a round-trip to Redis
            - Deletion is batched but still O(N) for matching keys

            Alternatives for large datasets:
            - Use a dedicated Redis database and call FLUSHDB (no prefix)
            - Use key expiration (TTL) instead of manual clearing
            - Consider Redis keyspace notifications for cache invalidation

        Args:
            batch_size: Number of keys to scan per iteration. Higher values
                reduce round-trips but increase memory usage per batch.
                Defaults to SCAN_BATCH_SIZE (100).

        Warning:
            Without a prefix, this calls FLUSHDB which deletes ALL keys
            in the current database instantly. Use with caution in shared
            Redis instances.
        """
        if not self._validate_connection():
            return
        # Type narrowing: _validate_connection ensures _client is not None
        assert self._client is not None

        effective_batch_size = (
            batch_size if batch_size is not None else self.SCAN_BATCH_SIZE
        )
        RedisError = _get_redis_error_class()

        try:
            if self._prefix:
                # Scan and delete keys with prefix
                # Note: SCAN is O(N) across ALL keys, not just matching ones
                pattern = f"{self._prefix}*"
                cursor = 0
                total_deleted = 0
                iterations = 0

                logger.debug(
                    "Starting Redis clear with prefix '%s' (batch_size=%d). "
                    "This may be slow for large datasets.",
                    self._prefix,
                    effective_batch_size,
                )

                while True:
                    cursor, keys = await self._client.scan(
                        cursor=cursor, match=pattern, count=effective_batch_size
                    )
                    if keys:
                        await self._client.delete(*keys)
                        total_deleted += len(keys)
                    iterations += 1
                    if cursor == 0:
                        break

                # Warn if the operation required many iterations (indicates large dataset)
                if iterations > 10:
                    logger.warning(
                        "Redis clear completed after %d iterations (%d keys deleted). "
                        "Consider using a dedicated database with FLUSHDB for better "
                        "performance, or increase batch_size.",
                        iterations,
                        total_deleted,
                    )
                else:
                    logger.debug(
                        "Redis clear completed: %d keys deleted in %d iterations",
                        total_deleted,
                        iterations,
                    )
            else:
                # No prefix - flush entire database
                logger.debug("Flushing entire Redis database (no prefix configured)")
                await self._client.flushdb()
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # fallback-ok: silently ignore clear failures, stale entries will expire via TTL
            logger.warning("Redis clear failed: %s", sanitize_error_message(str(e)))

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key to check.

        Returns:
            True if key exists, False otherwise.
            Returns False on any error.
        """
        if not self._validate_connection():
            return False
        # Type narrowing: _validate_connection ensures _client is not None
        assert self._client is not None

        RedisError = _get_redis_error_class()

        try:
            prefixed_key = self._make_key(key)
            result = await self._client.exists(prefixed_key)
            return bool(result > 0)
        except (ConnectionError, OSError, RedisError, TimeoutError) as e:
            # fallback-ok: return False on Redis errors, treating key as non-existent
            logger.warning(
                "Redis exists check failed for key '%s': %s",
                key,
                sanitize_error_message(str(e)),
            )
            return False

    @property
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        return self._connected

    async def ping(self) -> bool:
        """
        Ping Redis to check connection health.

        Returns:
            True if connected and responsive, False otherwise.
        """
        if not self._validate_connection():
            return False
        # Type narrowing: _validate_connection ensures _client is not None
        assert self._client is not None

        RedisError = _get_redis_error_class()
        try:
            await self._client.ping()
            return True
        except (ConnectionError, OSError, RedisError, TimeoutError):
            # fallback-ok: health check returns False on failure, does not raise
            return False
