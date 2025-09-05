"""
PostgreSQL-based Distributed Lock Manager for ONEX.
Replaces Redis-based locking with PostgreSQL advisory locks.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import asyncpg

from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.core.onex_error import OnexError

if TYPE_CHECKING:
    from omnibase.protocols.core.protocol_logger import ProtocolLogger


class PostgreSQLLockManager:
    """
    PostgreSQL advisory lock manager for coordinating operations
    across multiple instances of the automation system.

    Uses PostgreSQL advisory locks which are automatically released
    when the connection ends, providing better reliability than Redis.
    """

    DEFAULT_LOCK_TIMEOUT = 30  # seconds
    DEFAULT_RETRY_DELAY = 0.1  # seconds
    DEFAULT_MAX_RETRIES = 50  # 5 seconds total retry time

    def __init__(
        self,
        container: ModelONEXContainer,
        database_url: str = "postgresql://localhost:5432/onex",
        key_prefix: str = "onex_lock_",
    ):
        """Initialize the PostgreSQL lock manager."""
        self.container = container
        self.logger: ProtocolLogger | None = container.get_tool("LOGGER")
        self.database_url = database_url
        self.key_prefix = key_prefix
        self.connection_pool: asyncpg.Pool | None = None
        self.instance_id = str(uuid.uuid4())  # Unique ID for this instance
        self.held_locks: dict[str, int] = {}  # Track locks held by this instance

    async def connect(self) -> None:
        """Connect to PostgreSQL."""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )
            if self.logger:
                self.logger.info("Connected to PostgreSQL for distributed locking")
        except Exception as e:
            error_msg = f"Failed to connect to PostgreSQL: {e}"
            if self.logger:
                self.logger.exception(error_msg)
            raise OnexError(error_msg) from e

    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL."""
        if self.connection_pool:
            await self.connection_pool.close()
            self.connection_pool = None
            if self.logger:
                self.logger.info("Disconnected from PostgreSQL lock manager")

    def _lock_key_to_id(self, lock_key: str) -> int:
        """Convert lock key to PostgreSQL advisory lock ID."""
        # Use hash to convert string to integer for PostgreSQL advisory locks
        return hash(f"{self.key_prefix}{lock_key}") & 0x7FFFFFFF  # Keep positive

    @asynccontextmanager
    async def acquire_lock(
        self,
        lock_key: str,
        timeout: float | None = None,
        retry_delay: float | None = None,
        max_retries: int | None = None,
    ):
        """
        Async context manager to acquire and automatically release a distributed lock.

        Args:
            lock_key: Unique key for the lock
            timeout: Lock timeout in seconds (default: DEFAULT_LOCK_TIMEOUT)
            retry_delay: Delay between retries in seconds (default: DEFAULT_RETRY_DELAY)
            max_retries: Maximum retries (default: DEFAULT_MAX_RETRIES)
        """
        if not self.connection_pool:
            msg = "PostgreSQL lock manager not connected"
            raise OnexError(msg)

        timeout = timeout or self.DEFAULT_LOCK_TIMEOUT
        retry_delay = retry_delay or self.DEFAULT_RETRY_DELAY
        max_retries = max_retries or self.DEFAULT_MAX_RETRIES

        lock_id = self._lock_key_to_id(lock_key)
        acquired = False

        try:
            # Try to acquire the lock with retries
            for attempt in range(max_retries):
                async with self.connection_pool.acquire() as connection:
                    # Try to acquire advisory lock (non-blocking)
                    result = await connection.fetchval(
                        "SELECT pg_try_advisory_lock($1)",
                        lock_id,
                    )

                    if result:  # Lock acquired
                        acquired = True
                        self.held_locks[lock_key] = lock_id
                        if self.logger:
                            self.logger.debug(
                                f"Acquired lock '{lock_key}' (id: {lock_id})",
                            )
                        break
                    # Lock not available, wait and retry
                    elif attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)

            if not acquired:
                msg = (
                    f"Failed to acquire lock '{lock_key}' after {max_retries} attempts"
                )
                raise OnexError(
                    msg,
                )

            # Yield control to the caller
            yield

        finally:
            # Always try to release the lock
            if acquired and lock_key in self.held_locks:
                try:
                    async with self.connection_pool.acquire() as connection:
                        await connection.execute(
                            "SELECT pg_advisory_unlock($1)",
                            lock_id,
                        )
                    del self.held_locks[lock_key]
                    if self.logger:
                        self.logger.debug(f"Released lock '{lock_key}' (id: {lock_id})")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            f"Failed to explicitly release lock '{lock_key}': {e}",
                        )
                    # Note: PostgreSQL will automatically release the lock when connection closes

    async def is_locked(self, lock_key: str) -> bool:
        """Check if a lock is currently held (by any instance)."""
        if not self.connection_pool:
            return False

        lock_id = self._lock_key_to_id(lock_key)

        try:
            async with self.connection_pool.acquire() as connection:
                # Try to acquire lock non-blocking - if successful, it wasn't locked
                result = await connection.fetchval(
                    "SELECT pg_try_advisory_lock($1)",
                    lock_id,
                )

                if result:
                    # We got the lock, so it wasn't held - release it immediately
                    await connection.execute("SELECT pg_advisory_unlock($1)", lock_id)
                    return False
                # Lock is held by someone else
                return True
        except Exception as e:
            if self.logger:
                self.logger.exception(
                    f"Error checking lock status for '{lock_key}': {e}",
                )
            return False

    async def release_all_locks(self) -> None:
        """Release all locks held by this instance."""
        if not self.connection_pool:
            return

        for lock_key, lock_id in list(self.held_locks.items()):
            try:
                async with self.connection_pool.acquire() as connection:
                    await connection.execute("SELECT pg_advisory_unlock($1)", lock_id)
                del self.held_locks[lock_key]
                if self.logger:
                    self.logger.debug(f"Released lock '{lock_key}' during cleanup")
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Failed to release lock '{lock_key}' during cleanup: {e}",
                    )

    async def health_check(self) -> dict[str, any]:
        """Check the health of the lock manager."""
        if not self.connection_pool:
            return {"status": "disconnected", "connection_pool": None, "held_locks": 0}

        try:
            async with self.connection_pool.acquire() as connection:
                # Test basic functionality
                await connection.fetchval("SELECT 1")

            return {
                "status": "healthy",
                "connection_pool": "active",
                "held_locks": len(self.held_locks),
                "instance_id": self.instance_id,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "held_locks": len(self.held_locks),
            }
