"""
Distributed Lock Manager for Phase 4 Production Readiness.
Provides Redis-based distributed locking for multi-instance deployments.
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional

import redis.asyncio as redis

from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.protocol.protocol_logger import ProtocolLogger
from omnibase_core.utils import metrics_registry as metrics


class DistributedLockManager:
    """
    Redis-based distributed lock manager for coordinating operations
    across multiple instances of the automation system.

    Uses Redis SET with NX (only set if not exists) and EX (expiration)
    for atomic lock acquisition with automatic expiration.
    """

    DEFAULT_LOCK_TIMEOUT = 30  # seconds
    DEFAULT_RETRY_DELAY = 0.1  # seconds
    DEFAULT_MAX_RETRIES = 50  # 5 seconds total retry time

    def __init__(
        self,
        container: ONEXContainer,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "onex:lock:",
    ):
        """Initialize the distributed lock manager."""
        self.container = container
        self.logger: Optional[ProtocolLogger] = container.get_tool("LOGGER")
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis_client: Optional[redis.Redis] = None
        self.instance_id = str(uuid.uuid4())  # Unique ID for this instance
        self.held_locks: Dict[str, str] = {}  # Track locks held by this instance

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis_client.ping()
            if self.logger:
                self.logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            if self.logger:
                self.logger.info("Disconnected from Redis")

    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = DEFAULT_LOCK_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> Optional[str]:
        """
        Acquire a distributed lock.

        Args:
            lock_name: Name of the lock to acquire
            timeout: Lock expiration time in seconds
            max_retries: Maximum number of acquisition attempts
            retry_delay: Delay between retry attempts

        Returns:
            Lock token if acquired, None otherwise
        """
        if not self.redis_client:
            await self.connect()

        lock_key = f"{self.key_prefix}{lock_name}"
        lock_token = f"{self.instance_id}:{uuid.uuid4()}"

        for attempt in range(max_retries):
            try:
                # Try to acquire lock with atomic SET NX EX
                acquired = await self.redis_client.set(
                    lock_key,
                    lock_token,
                    nx=True,  # Only set if not exists
                    ex=timeout,  # Expiration time
                )

                if acquired:
                    self.held_locks[lock_name] = lock_token

                    # Update Prometheus metrics
                    metrics.distributed_locks_acquired.labels(
                        lock_name=lock_name, component="lock_manager"
                    ).inc()

                    metrics.distributed_locks_active.labels(
                        lock_name=lock_name, holder=self.instance_id
                    ).set(1)

                    if self.logger:
                        self.logger.debug(
                            f"Acquired lock '{lock_name}' with token {lock_token}"
                        )
                    return lock_token

                # Lock not acquired, wait before retry
                await asyncio.sleep(retry_delay)

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error acquiring lock '{lock_name}': {str(e)}")

                metrics.distributed_locks_failed.labels(
                    lock_name=lock_name, component="lock_manager", reason="exception"
                ).inc()

        # Failed to acquire after all retries
        metrics.distributed_locks_failed.labels(
            lock_name=lock_name, component="lock_manager", reason="timeout"
        ).inc()

        if self.logger:
            self.logger.warning(
                f"Failed to acquire lock '{lock_name}' after {max_retries} attempts"
            )
        return None

    async def release_lock(self, lock_name: str, lock_token: str) -> bool:
        """
        Release a distributed lock.

        Args:
            lock_name: Name of the lock to release
            lock_token: Token received when lock was acquired

        Returns:
            True if lock was released, False otherwise
        """
        if not self.redis_client:
            if self.logger:
                self.logger.error("Redis client not connected")
            return False

        lock_key = f"{self.key_prefix}{lock_name}"

        # Lua script for atomic check-and-delete
        # Only delete if the token matches (prevents releasing someone else's lock)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await self.redis_client.eval(lua_script, 1, lock_key, lock_token)

            if result:
                # Remove from held locks
                self.held_locks.pop(lock_name, None)

                # Update Prometheus metrics
                metrics.distributed_locks_active.labels(
                    lock_name=lock_name, holder=self.instance_id
                ).set(0)

                if self.logger:
                    self.logger.debug(f"Released lock '{lock_name}'")
                return True
            else:
                if self.logger:
                    self.logger.warning(
                        f"Failed to release lock '{lock_name}' - token mismatch or lock expired"
                    )
                return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error releasing lock '{lock_name}': {str(e)}")
            return False

    async def extend_lock(
        self, lock_name: str, lock_token: str, additional_time: int
    ) -> bool:
        """
        Extend the expiration time of a held lock.

        Args:
            lock_name: Name of the lock to extend
            lock_token: Token received when lock was acquired
            additional_time: Additional seconds to extend the lock

        Returns:
            True if lock was extended, False otherwise
        """
        if not self.redis_client:
            return False

        lock_key = f"{self.key_prefix}{lock_name}"

        # Lua script for atomic check-and-extend
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        try:
            result = await self.redis_client.eval(
                lua_script, 1, lock_key, lock_token, additional_time
            )

            if result:
                if self.logger:
                    self.logger.debug(
                        f"Extended lock '{lock_name}' by {additional_time} seconds"
                    )
                return True
            else:
                if self.logger:
                    self.logger.warning(f"Failed to extend lock '{lock_name}'")
                return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error extending lock '{lock_name}': {str(e)}")
            return False

    @asynccontextmanager
    async def lock(
        self,
        lock_name: str,
        timeout: int = DEFAULT_LOCK_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ):
        """
        Context manager for distributed locking.

        Usage:
            async with lock_manager.lock("my_operation"):
                # Critical section code here
                pass
        """
        lock_token = None
        start_time = time.time()

        try:
            # Acquire the lock
            lock_token = await self.acquire_lock(
                lock_name, timeout, max_retries, retry_delay
            )

            if not lock_token:
                raise RuntimeError(f"Failed to acquire lock '{lock_name}'")

            yield lock_token

        finally:
            # Always try to release the lock
            if lock_token:
                duration = time.time() - start_time

                # Record lock hold duration
                metrics.distributed_lock_hold_duration.labels(
                    lock_name=lock_name
                ).observe(duration)

                await self.release_lock(lock_name, lock_token)

    async def release_all_locks(self) -> None:
        """Release all locks held by this instance."""
        for lock_name, lock_token in list(self.held_locks.items()):
            await self.release_lock(lock_name, lock_token)

    async def is_locked(self, lock_name: str) -> bool:
        """Check if a lock is currently held by any instance."""
        if not self.redis_client:
            await self.connect()

        lock_key = f"{self.key_prefix}{lock_name}"

        try:
            result = await self.redis_client.exists(lock_key)
            return bool(result)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking lock status: {str(e)}")
            return False

    async def get_lock_info(self, lock_name: str) -> Optional[Dict[str, str]]:
        """Get information about a lock (holder and TTL)."""
        if not self.redis_client:
            await self.connect()

        lock_key = f"{self.key_prefix}{lock_name}"

        try:
            holder = await self.redis_client.get(lock_key)
            if holder:
                ttl = await self.redis_client.ttl(lock_key)
                return {
                    "holder": holder,
                    "ttl": ttl,
                    "is_mine": holder in self.held_locks.values(),
                }
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting lock info: {str(e)}")
            return None
