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

import json
import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

# Check if redis is available (optional dependency)
try:
    import redis.asyncio as aioredis
    from redis.asyncio.connection import ConnectionPool
    from redis.exceptions import RedisError

    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None  # type: ignore[assignment]
    ConnectionPool = None  # type: ignore[assignment,misc]
    RedisError = Exception  # type: ignore[assignment,misc]
    REDIS_AVAILABLE = False

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from redis.asyncio.connection import ConnectionPool as ConnectionPoolType

logger = logging.getLogger(__name__)


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
        Returns original URL if parsing fails or no password present.

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
    except Exception:
        # If URL parsing fails, return a generic safe string
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
            raise RuntimeError(
                "Redis package not installed. Install with: poetry install -E cache"
            )

        self._url = url
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._max_connections = max_connections
        self._pool: ConnectionPoolType | None = None
        self._client: Redis[str] | None = None
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

        # Type guard: verify redis is available at runtime
        if aioredis is None or ConnectionPool is None:
            raise RuntimeError(
                "Redis package not installed. Install with: poetry install -E cache"
            )

        try:
            self._pool = aioredis.ConnectionPool.from_url(
                self._url,
                max_connections=self._max_connections,
                decode_responses=True,
            )
            self._client = aioredis.Redis(connection_pool=self._pool)
            # Verify connection - assert for type narrowing
            assert self._client is not None  # Narrow type for pyright
            await self._client.ping()
            self._connected = True
            # Don't log URL - may contain credentials
            logger.debug("Connected to Redis")
        except (RedisError, ConnectionError, TimeoutError, OSError) as e:
            # Sanitize error message to prevent credential leakage
            safe_error = sanitize_error_message(str(e))
            # Use error not exception - traceback will be at caller level after re-raise
            logger.error("Failed to connect to Redis: %s", safe_error)  # noqa: TRY400
            # Cleanup on failure to prevent resource leaks
            await self._cleanup_on_connect_failure()
            raise ConnectionError(f"Failed to connect to Redis: {safe_error}") from e
        except Exception as e:
            # Sanitize error message to prevent credential leakage
            safe_error = sanitize_error_message(str(e))
            # Catch unexpected errors during connection setup
            # Use error not exception - traceback will be at caller level after re-raise
            logger.error("Unexpected error connecting to Redis: %s", safe_error)  # noqa: TRY400
            await self._cleanup_on_connect_failure()
            raise ConnectionError(f"Failed to connect to Redis: {safe_error}") from e

    async def _cleanup_on_connect_failure(self) -> None:
        """Clean up resources after a connection failure."""
        try:
            if self._pool is not None:
                await self._pool.disconnect()
        except Exception as e:
            # Sanitize to prevent credential leakage
            logger.warning(
                "Error during connection cleanup: %s", sanitize_error_message(str(e))
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
        # Close client first, then pool - ensure partial failures don't prevent full cleanup
        try:
            if self._client:
                await self._client.close()
        except Exception as e:
            # Sanitize to prevent credential leakage
            logger.warning(
                "Error closing Redis client: %s", sanitize_error_message(str(e))
            )
        finally:
            self._client = None

        try:
            if self._pool:
                await self._pool.disconnect()
        except Exception as e:
            # Sanitize to prevent credential leakage
            logger.warning(
                "Error disconnecting Redis pool: %s", sanitize_error_message(str(e))
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

        try:
            prefixed_key = self._make_key(key)
            data = await self._client.get(prefixed_key)
            if data is None:
                return None
            result: object = json.loads(data)
            return result
        except json.JSONDecodeError as e:
            logger.warning("Failed to deserialize cache value for key '%s': %s", key, e)
            return None
        except (RedisError, ConnectionError, TimeoutError, OSError) as e:
            logger.warning("Redis get failed for key '%s': %s", key, e)
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

        try:
            prefixed_key = self._make_key(key)
            data = json.dumps(value, default=str)

            if ttl is not None:
                await self._client.setex(prefixed_key, ttl, data)
            else:
                await self._client.set(prefixed_key, data)
        except (TypeError, ValueError) as e:
            logger.warning("Failed to serialize cache value for key '%s': %s", key, e)
        except (RedisError, ConnectionError, TimeoutError, OSError) as e:
            logger.warning("Redis set failed for key '%s': %s", key, e)

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

        try:
            prefixed_key = self._make_key(key)
            await self._client.delete(prefixed_key)
        except (RedisError, ConnectionError, TimeoutError, OSError) as e:
            logger.warning("Redis delete failed for key '%s': %s", key, e)

    async def clear(self) -> None:
        """
        Clear all cache entries with the configured prefix.

        Warning:
            This scans for keys with the prefix and deletes them.
            For large caches, consider FLUSHDB on a dedicated database.
        """
        if not self._validate_connection():
            return
        # Type narrowing: _validate_connection ensures _client is not None
        assert self._client is not None

        try:
            if self._prefix:
                # Scan and delete keys with prefix
                pattern = f"{self._prefix}*"
                cursor = 0
                while True:
                    cursor, keys = await self._client.scan(
                        cursor=cursor, match=pattern, count=100
                    )
                    if keys:
                        await self._client.delete(*keys)
                    if cursor == 0:
                        break
            else:
                # No prefix - flush entire database
                await self._client.flushdb()
        except (RedisError, ConnectionError, TimeoutError, OSError) as e:
            logger.warning("Redis clear failed: %s", e)

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

        try:
            prefixed_key = self._make_key(key)
            result = await self._client.exists(prefixed_key)
            return bool(result > 0)
        except (RedisError, ConnectionError, TimeoutError, OSError) as e:
            logger.warning("Redis exists check failed for key '%s': %s", key, e)
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

        try:
            await self._client.ping()
            return True
        except Exception:
            return False
