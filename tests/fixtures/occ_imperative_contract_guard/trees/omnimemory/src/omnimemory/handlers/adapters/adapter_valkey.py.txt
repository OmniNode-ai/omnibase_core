# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Valkey/Redis adapter for subscription caching.

used by the subscription handler for fast topic->subscriber lookups.

Valkey is a fork of Redis with full API compatibility. The redis-py library
works with both Redis and Valkey seamlessly.

Redis Async Type Handling
-------------------------

The redis-py library's type stubs declare many async methods as returning
``Awaitable[T] | T`` union types. This is a known limitation where the stubs
must cover both sync and async client behavior. In practice, the async client
always returns awaitables, but type checkers require handling both branches.

This adapter uses the ``_ensure_awaited()`` helper method to handle this
union type cleanly. See that method's docstring for implementation details.

Example::

    from omnimemory.handlers.adapters import (
        AdapterValkey,
        AdapterValkeyConfig,
    )

    config = AdapterValkeyConfig(host=os.environ["VALKEY_HOST"], port=6379)
    adapter = AdapterValkey(config)
    await adapter.initialize()

    # Key-value operations
    await adapter.set_key("key", "value", ttl=3600)
    value = await adapter.get("key")

    # Set operations for topic->subscribers mapping
    await adapter.sadd("topic:memory.item.created", "sub_123", "sub_456")
    subscribers = await adapter.smembers("topic:memory.item.created")

    await adapter.shutdown()

.. versionadded:: 0.1.0
    Initial implementation for OMN-1393.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import warnings
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, TypeAlias, TypeVar, cast, overload

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

_T = TypeVar("_T")
type _ResetPipeline = Callable[[], Awaitable[None]]
type _RedisScalar = bytes | bytearray | memoryview[int] | str | int | float

# redis-py is compatible with both Redis and Valkey
# Type alias for Redis client - provides IDE support while handling incomplete stubs
# Note: redis.asyncio.Redis doesn't support generic type parameters in stubs
if TYPE_CHECKING:
    from redis.asyncio import Redis as AsyncRedis
    from redis.asyncio.client import Pipeline

    RedisClientType: TypeAlias = AsyncRedis  # noqa: UP040 - can't use type keyword in conditional
    PipelineType: TypeAlias = Pipeline  # noqa: UP040 - can't use type keyword in conditional
else:
    RedisClientType: TypeAlias = object  # type: ignore[assignment]  # noqa: UP040  # Why: runtime branch cannot reference AsyncRedis; TYPE_CHECKING branch provides real type
    PipelineType: TypeAlias = object  # type: ignore[assignment]  # noqa: UP040  # Why: runtime branch cannot reference Pipeline; TYPE_CHECKING branch provides real type

# Use mutable variable names (lowercase) to avoid pyright constant redefinition warnings
_redis_available: bool = False
_redis_import_error: str | None = None

try:
    import redis.asyncio as aioredis  # transport-import-ok: designated redis transport boundary (adapter pattern), OMN-13283

    _redis_available = True
except ImportError as e:
    _redis_import_error = str(e)
    aioredis = None  # type: ignore[assignment]  # Why: runtime optional import sentinel; TYPE_CHECKING branch owns the module type


logger = logging.getLogger(__name__)

__all__ = [
    "AdapterValkey",
    "AdapterValkeyConfig",
    "ModelValkeyHealth",
    "ValkeyPipeline",
]


class AdapterValkeyConfig(  # omnimemory-model-exempt: adapter config
    BaseModel
):
    """Configuration for the Valkey adapter.

    Attributes:
        host: Valkey server hostname.
        port: Valkey server port.
        db: Database index to use.
        password: Optional password for authentication.
        username: Optional username for ACL authentication.
        socket_timeout: Socket timeout in seconds.
        socket_connect_timeout: Connection timeout in seconds.
        decode_responses: Whether to decode responses to strings.
        max_connections: Maximum number of connections in the pool.
        key_prefix: Optional prefix for all keys (namespacing).
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
    )

    host: str = Field(
        ...,
        description="Valkey server hostname",
    )
    port: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Valkey server port",
    )
    db: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Database index (0-15)",
    )
    password: SecretStr | None = Field(
        default=None,
        description="Optional password for authentication",
    )
    username: str | None = Field(
        default=None,
        description="Optional username for ACL authentication",
    )
    socket_timeout: float = Field(
        default=5.0,
        gt=0.0,
        le=60.0,
        description="Socket timeout in seconds",
    )
    socket_connect_timeout: float = Field(
        default=5.0,
        gt=0.0,
        le=30.0,
        description="Connection timeout in seconds",
    )
    decode_responses: bool = Field(
        default=True,
        description="Decode responses to strings (True for text, False for bytes)",
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum connections in the pool",
    )
    key_prefix: str = Field(
        default="omnimemory:",
        description="Prefix for all keys (namespacing)",
    )

    @field_validator("decode_responses")
    @classmethod
    def validate_decode_responses(cls, v: bool) -> bool:
        """Warn if decode_responses is False since adapter assumes string responses.

        The AdapterValkey implementation assumes all responses are decoded to
        strings. Setting decode_responses=False will cause bytes to be returned,
        which may lead to type errors in methods like get(), smembers(), etc.

        Args:
            v: The decode_responses value.

        Returns:
            The validated value (unchanged).

        Warns:
            UserWarning: If decode_responses is False.
        """
        if not v:
            warnings.warn(
                "AdapterValkey assumes decode_responses=True for string handling. "
                "Setting to False may cause type errors in methods that expect "
                "string responses (get, smembers, hgetall, etc.).",
                UserWarning,
                stacklevel=2,
            )
        return v


class ModelValkeyHealth(BaseModel):  # omnimemory-model-exempt: adapter health
    """Health status for the Valkey adapter.

    Attributes:
        is_healthy: Overall health status.
        initialized: Whether the adapter has been initialized.
        ping_success: Whether PING command succeeded.
        error_message: Error details if unhealthy.
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
    )

    is_healthy: bool = Field(
        ...,
        description="Overall health status",
    )
    initialized: bool = Field(
        ...,
        description="Whether the adapter has been initialized",
    )
    ping_success: bool | None = Field(
        default=None,
        description="Whether PING command succeeded (None if not checked)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if unhealthy",
    )


class ValkeyPipeline:
    """Wrapper around Redis pipeline that handles key prefixing.

    This class wraps a Redis pipeline and provides the same interface as
    AdapterValkey methods, automatically applying the key prefix to all keys.
    Pipeline commands are queued and executed atomically when the context
    manager exits.

    Example::

        async with adapter.pipeline() as pipe:
            pipe.sadd("topic:memory.item.created", "sub_123")
            pipe.set_key("subscription:sub_123", data, ttl=3600)
            # Commands are executed atomically on context exit

    Note:
        Pipeline methods are synchronous (they queue commands). The actual
        execution happens asynchronously when the context manager exits.
        Calling execute() manually is supported but the context manager will
        skip re-execution if already executed.
    """

    def __init__(self, pipe: PipelineType, key_prefix: str) -> None:
        """Initialize the pipeline wrapper.

        Args:
            pipe: The underlying Redis pipeline.
            key_prefix: The key prefix to apply to all keys.
        """
        self._pipe = pipe
        self._key_prefix = key_prefix
        self._executed = False
        self._results: list[object] = []

    def _prefixed_key(self, key: str) -> str:
        """Add namespace prefix to key.

        Args:
            key: The raw key.

        Returns:
            The prefixed key.
        """
        return f"{self._key_prefix}{key}"

    def sadd(self, key: str, *members: str) -> ValkeyPipeline:
        """Queue SADD command to add members to a set.

        Args:
            key: The set key.
            *members: Members to add to the set.

        Returns:
            Self for method chaining.
        """
        if members:
            self._pipe.sadd(self._prefixed_key(key), *members)
        return self

    def srem(self, key: str, *members: str) -> ValkeyPipeline:
        """Queue SREM command to remove members from a set.

        Args:
            key: The set key.
            *members: Members to remove from the set.

        Returns:
            Self for method chaining.
        """
        if members:
            self._pipe.srem(self._prefixed_key(key), *members)
        return self

    def set_key(self, key: str, value: str, ttl: int | None = None) -> ValkeyPipeline:
        """Queue SET/SETEX command to set a key value.

        Note:
            Named ``set_key`` instead of ``set`` to avoid shadowing the
            Python builtin ``set`` type.

        Args:
            key: The key to set.
            value: The value to store.
            ttl: Optional time-to-live in seconds.

        Returns:
            Self for method chaining.
        """
        if ttl is not None:
            self._pipe.setex(self._prefixed_key(key), ttl, value)
        else:
            self._pipe.set(self._prefixed_key(key), value)
        return self

    def delete(self, key: str) -> ValkeyPipeline:
        """Queue DELETE command to delete a key.

        Args:
            key: The key to delete.

        Returns:
            Self for method chaining.
        """
        self._pipe.delete(self._prefixed_key(key))
        return self

    def expire(self, key: str, ttl: int) -> ValkeyPipeline:
        """Queue EXPIRE command to set expiration on a key.

        Args:
            key: The key to set expiration for.
            ttl: Time-to-live in seconds.

        Returns:
            Self for method chaining.
        """
        self._pipe.expire(self._prefixed_key(key), ttl)
        return self

    async def execute(self) -> list[object]:
        """Execute all queued commands atomically.

        This method is safe to call multiple times - subsequent calls return
        the cached results from the first execution. The context manager will
        also skip re-execution if this method was called manually.

        Returns:
            List of results from each command.

        Note:
            When using the pipeline as a context manager, execution happens
            automatically on context exit. Calling this method manually is
            optional and only needed if you want access to the results before
            the context exits.
        """
        if self._executed:
            return self._results
        self._results = await self._pipe.execute()
        self._executed = True
        return self._results

    @property
    def executed(self) -> bool:
        """Check if the pipeline has been executed.

        Returns:
            True if execute() has been called, False otherwise.
        """
        return self._executed


class AdapterValkey:
    """Valkey/Redis adapter for subscription caching.

    Provides key-value and set operations for fast subscription lookups.
    Uses connection pooling for efficient resource management.

    Attributes:
        config: The adapter configuration.

    Example::

        config = AdapterValkeyConfig(host=os.environ["VALKEY_HOST"], port=6379)
        adapter = AdapterValkey(config)
        await adapter.initialize()

        # Store subscription mapping
        await adapter.sadd("topic:memory.item.created", "sub_123")

        # Get all subscribers for a topic
        subscribers = await adapter.smembers("topic:memory.item.created")

        await adapter.shutdown()
    """

    def __init__(self, config: AdapterValkeyConfig) -> None:
        """Initialize the adapter with configuration.

        Args:
            config: The adapter configuration.

        Raises:
            ImportError: If redis-py is not installed.
        """
        if not _redis_available:
            raise ImportError(
                f"redis-py is required for AdapterValkey. "
                f"Install it with: poetry add redis. "
                f"Original error: {_redis_import_error}"
            )

        self._config = config
        self._client: RedisClientType | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    @property
    def config(self) -> AdapterValkeyConfig:
        """Get the adapter configuration."""
        return self._config

    @property
    def is_initialized(self) -> bool:
        """Check if the adapter has been initialized."""
        return self._initialized

    def _prefixed_key(self, key: str) -> str:
        """Add namespace prefix to key.

        Args:
            key: The raw key.

        Returns:
            The prefixed key.
        """
        return f"{self._config.key_prefix}{key}"

    @overload
    async def _ensure_awaited(self, result: Awaitable[_T]) -> _T: ...

    @overload
    async def _ensure_awaited(self, result: _T) -> _T: ...

    async def _ensure_awaited(  # stub-ok: redis-py-awaitable-helper-deferred
        self, result: _T | Awaitable[_T]
    ) -> _T:
        """Ensure a Redis result is awaited if it's an awaitable.

        **Why This Helper Exists**

        The redis-py library has a type annotation quirk where many async
        methods are typed as returning ``Awaitable[T] | T`` (a union type),
        even though in practice the async client always returns awaitables.
        This happens because:

        1. redis-py supports both sync and async clients with shared method
           signatures in its type stubs
        2. The type stubs use union types to cover both execution modes
        3. Type checkers see the union and require handling both branches

        Without this helper, every Redis call would need explicit type
        narrowing or explicit casts. This helper provides a
        single, type-safe way to handle the union by checking at runtime
        whether the result needs to be awaited.

        **Example**

        Instead of::

            result = await client.sadd(key, *members)

        We use::

            result = await self._ensure_awaited(client.sadd(key, *members))

        **Technical Details**

        - Uses ``inspect.isawaitable()`` for robust awaitable detection
        - Handles coroutines, Tasks, and any other awaitable types
        - Zero overhead for already-resolved values (just a type check)
        - Maintains full type safety with ``TypeVar`` preservation

        Args:
            result: The result from a Redis operation, which may be either
                an awaitable (coroutine/Task) or an already-resolved value.

        Returns:
            The resolved value of type ``T``.

        See Also:
            - https://github.com/redis/redis-py/issues/2596 (typing discussion)
            - Module docstring for broader context on Redis async handling
        """
        if inspect.isawaitable(result):
            return await result
        return result

    async def initialize(self) -> None:
        """Initialize the Valkey connection.

        Creates a connection pool and tests connectivity.

        Raises:
            RuntimeError: If connection fails.
        """
        async with self._init_lock:
            if self._initialized:
                return

            try:
                password = None
                if self._config.password:
                    password = self._config.password.get_secret_value()

                # aioredis is guaranteed to be available here because
                # __init__ raises ImportError if _redis_available is False
                assert aioredis is not None, "aioredis module not available"

                self._client = aioredis.Redis(
                    host=self._config.host,
                    port=self._config.port,
                    db=self._config.db,
                    password=password,
                    username=self._config.username,
                    socket_timeout=self._config.socket_timeout,
                    socket_connect_timeout=self._config.socket_connect_timeout,
                    decode_responses=self._config.decode_responses,  # pyright: ignore[reportArgumentType]
                    max_connections=self._config.max_connections,
                )
                # Assert for type narrowing: pyright doesn't narrow instance
                # attributes after assignment due to potential concurrent modification
                assert self._client is not None

                # Test connection with PING
                await self._client.ping()

                self._initialized = True
                logger.info(
                    "AdapterValkey initialized: %s:%d db=%d",
                    self._config.host,
                    self._config.port,
                    self._config.db,
                )

            except Exception as e:
                logger.error("Failed to initialize AdapterValkey: %s", e)
                if self._client:
                    await self._client.aclose()
                    self._client = None
                raise RuntimeError(f"Valkey connection failed: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the adapter and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("AdapterValkey shutdown complete")

    def _ensure_initialized(self) -> RedisClientType:
        """Ensure adapter is initialized and return client.

        Returns:
            The initialized Redis client.

        Raises:
            RuntimeError: If adapter is not initialized.
        """
        if not self._initialized or self._client is None:
            raise RuntimeError(
                "AdapterValkey not initialized. Call initialize() first."
            )
        return self._client

    # =========================================================================
    # Key-Value Operations
    # =========================================================================

    async def get(self, key: str) -> str | None:
        """Get value for a key.

        Args:
            key: The key to retrieve.

        Returns:
            The value if found, None otherwise.
        """
        client = self._ensure_initialized()
        result = await client.get(self._prefixed_key(key))
        if result is None:
            return None
        return str(result) if not isinstance(result, str) else result

    async def mget(self, *keys: str) -> list[str | None]:
        """Get values for multiple keys in a single round-trip.

        This is more efficient than calling get() in a loop when retrieving
        multiple keys, as it reduces network round-trips.

        Args:
            *keys: The keys to retrieve.

        Returns:
            List of values in the same order as keys (None for missing keys).
        """
        if not keys:
            return []
        client = self._ensure_initialized()
        prefixed_keys = [self._prefixed_key(k) for k in keys]
        results = await client.mget(prefixed_keys)
        return [str(v) if v is not None else None for v in results]

    async def set_key(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> None:
        """Set value for a key.

        Note:
            Named ``set_key`` instead of ``set`` to avoid shadowing the
            Python builtin ``set`` type.

        Args:
            key: The key to set.
            value: The value to store.
            ttl: Optional time-to-live in seconds.
        """
        client = self._ensure_initialized()
        if ttl is not None:
            await client.setex(self._prefixed_key(key), ttl, value)
        else:
            await client.set(self._prefixed_key(key), value)

    async def delete(self, key: str) -> int:
        """Delete a key.

        Args:
            key: The key to delete.

        Returns:
            Number of keys deleted (0 or 1).
        """
        client = self._ensure_initialized()
        result = await client.delete(self._prefixed_key(key))
        return int(result)

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: The key to check.

        Returns:
            True if key exists, False otherwise.
        """
        client = self._ensure_initialized()
        result = await client.exists(self._prefixed_key(key))
        return int(result) > 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key.

        Args:
            key: The key to set expiration for.
            ttl: Time-to-live in seconds.

        Returns:
            True if timeout was set, False if key does not exist.
        """
        client = self._ensure_initialized()
        result = await client.expire(self._prefixed_key(key), ttl)
        return bool(result)

    # =========================================================================
    # Set Operations (for topic->subscribers mapping)
    # =========================================================================

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to a set.

        Args:
            key: The set key.
            *members: Members to add to the set.

        Returns:
            Number of members actually added (excludes already existing).
        """
        if not members:
            return 0
        client = self._ensure_initialized()
        result = await self._ensure_awaited(
            client.sadd(self._prefixed_key(key), *members)
        )
        return int(result)

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from a set.

        Args:
            key: The set key.
            *members: Members to remove from the set.

        Returns:
            Number of members actually removed.
        """
        if not members:
            return 0
        client = self._ensure_initialized()
        result = await self._ensure_awaited(
            client.srem(self._prefixed_key(key), *members)
        )
        return int(result)

    async def smembers(self, key: str) -> set[str]:
        """Get all members of a set.

        Args:
            key: The set key.

        Returns:
            Set of members (empty set if key does not exist).
        """
        client = self._ensure_initialized()
        result = await self._ensure_awaited(client.smembers(self._prefixed_key(key)))
        return {str(m) for m in result}

    async def sismember(self, key: str, member: str) -> bool:
        """Check if a member exists in a set.

        Args:
            key: The set key.
            member: The member to check.

        Returns:
            True if member is in the set, False otherwise.
        """
        client = self._ensure_initialized()
        result = await self._ensure_awaited(
            client.sismember(self._prefixed_key(key), member)
        )
        return bool(result)

    async def scard(self, key: str) -> int:
        """Get the number of members in a set.

        Args:
            key: The set key.

        Returns:
            Number of members (0 if key does not exist).
        """
        client = self._ensure_initialized()
        result = await self._ensure_awaited(client.scard(self._prefixed_key(key)))
        return int(result)

    # =========================================================================
    # Hash Operations (for storing subscription data)
    # =========================================================================

    async def hset(
        self,
        key: str,
        mapping: Mapping[str, str],
    ) -> int:
        """Set multiple hash fields.

        Args:
            key: The hash key.
            mapping: Field->value mapping to set.

        Returns:
            Number of fields added (excludes updated existing fields).
        """
        if not mapping:
            return 0
        client = self._ensure_initialized()
        redis_mapping = cast("Mapping[_RedisScalar, _RedisScalar]", mapping)
        result = await self._ensure_awaited(
            client.hset(self._prefixed_key(key), mapping=redis_mapping)
        )
        return int(result)

    async def hget(self, key: str, field: str) -> str | None:
        """Get a hash field value.

        Args:
            key: The hash key.
            field: The field to retrieve.

        Returns:
            The field value if found, None otherwise.
        """
        client = self._ensure_initialized()
        result = await self._ensure_awaited(client.hget(self._prefixed_key(key), field))
        if result is None:
            return None
        # Always convert to str - handles both str and bytes from redis
        return str(result)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all fields and values of a hash.

        Args:
            key: The hash key.

        Returns:
            Dictionary of field->value pairs (empty dict if key does not exist).
        """
        client = self._ensure_initialized()
        result = await self._ensure_awaited(client.hgetall(self._prefixed_key(key)))
        return {str(k): str(v) for k, v in result.items()}

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields.

        Args:
            key: The hash key.
            *fields: Fields to delete.

        Returns:
            Number of fields deleted.
        """
        if not fields:
            return 0
        client = self._ensure_initialized()
        result = await self._ensure_awaited(
            client.hdel(self._prefixed_key(key), *fields)
        )
        return int(result)

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> ModelValkeyHealth:
        """Check if the Valkey connection is healthy.

        Returns:
            ModelValkeyHealth with detailed status.
        """
        if not self._initialized or self._client is None:
            return ModelValkeyHealth(
                is_healthy=False,
                initialized=False,
                ping_success=None,
                error_message="Adapter not initialized",
            )

        try:
            await self._client.ping()
            return ModelValkeyHealth(
                is_healthy=True,
                initialized=True,
                ping_success=True,
            )
        except Exception as e:
            logger.warning("Valkey health check failed: %s", e)
            return ModelValkeyHealth(
                is_healthy=False,
                initialized=True,
                ping_success=False,
                error_message=f"PING failed: {e}",
            )

    # =========================================================================
    # Pipeline Operations
    # =========================================================================

    @asynccontextmanager
    async def pipeline(self) -> AsyncGenerator[ValkeyPipeline, None]:
        """Create a Redis pipeline for batching commands atomically.

        Pipelines allow multiple commands to be sent in a single round-trip,
        improving performance and providing atomicity. Commands are queued
        and executed when the context manager exits.

        The pipeline wrapper automatically handles key prefixing, matching
        the behavior of individual adapter methods.

        Usage::

            async with adapter.pipeline() as pipe:
                pipe.sadd("topic:memory.item.created", "sub_123")
                pipe.sadd("agent:agent_456:subscriptions", "sub_123")
                pipe.set_key("subscription:sub_123", data_json, ttl=3600)
                # All commands are executed atomically on context exit

        Yields:
            ValkeyPipeline wrapper with prefixed key operations.

        Raises:
            RuntimeError: If adapter is not initialized.

        Note:
            - Pipeline commands are synchronous (they queue commands)
            - Execution happens asynchronously on context exit
            - If any command fails, subsequent commands may still execute
              (Redis pipelines are not transactions)
            - For true transactions, use MULTI/EXEC via the raw client
        """
        client = self._ensure_initialized()
        pipe = client.pipeline()
        wrapper = ValkeyPipeline(pipe, self._config.key_prefix)
        try:
            yield wrapper
            # Only execute if not already executed (prevents double-execution
            # if user called execute() manually inside the context)
            if not wrapper.executed:
                await wrapper.execute()
        finally:
            # Reset releases pipeline resources
            reset_pipeline = cast("_ResetPipeline", pipe.reset)
            await reset_pipeline()

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def keys(self, pattern: str) -> list[str]:
        """Find keys matching a pattern.

        WARNING: This operation can be slow on large databases.
        Use SCAN in production for iterating over large key spaces.

        Args:
            pattern: Glob-style pattern (e.g., "topic:*").

        Returns:
            List of matching keys (without prefix).
        """
        client = self._ensure_initialized()
        full_pattern = self._prefixed_key(pattern)
        result = await client.keys(full_pattern)
        prefix_len = len(self._config.key_prefix)
        return [str(k)[prefix_len:] for k in result]

    async def flush_namespace(self) -> int:
        """Delete all keys in this adapter's namespace.

        WARNING: This is a destructive operation. Use with caution.

        Returns:
            Number of keys deleted.
        """
        keys = await self.keys("*")
        if not keys:
            return 0

        client = self._ensure_initialized()
        prefixed_keys = [self._prefixed_key(k) for k in keys]
        result = await client.delete(*prefixed_keys)
        logger.info(
            "Flushed %d keys from namespace %s", result, self._config.key_prefix
        )
        return int(result)
