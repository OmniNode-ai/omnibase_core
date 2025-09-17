#!/usr/bin/env python3
"""
PostgreSQL Database implementation with fallback.

Implements ProtocolDatabaseConnection using asyncpg with graceful fallback
to in-memory implementation when PostgreSQL is unavailable.
"""

import asyncio
import logging
import time
from typing import Any

from omnibase_core.models.service.model_service_health import ModelServiceHealth
from omnibase_core.protocol.protocol_database_connection import (
    ProtocolDatabaseConnection,
)


class PostgreSQLDatabase(ProtocolDatabaseConnection):
    """
    PostgreSQL-based database connection with automatic fallback.

    Falls back to InMemoryDatabase when PostgreSQL is unavailable.
    """

    def __init__(
        self,
        database_url: str = "postgresql://localhost:5432/onex",
        pool_min_size: int = 5,
        pool_max_size: int = 20,
        enable_fallback: bool = True,
    ):
        # Store original URL but create sanitized version for logging
        self.database_url = database_url
        self.sanitized_url = self._sanitize_connection_string(database_url)
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self.enable_fallback = enable_fallback
        self.logger = logging.getLogger(self.__class__.__name__)

        self._pool = None
        self._fallback_database = None
        self._is_using_fallback = False
        self._held_locks: dict[str, int] = {}  # lock_token -> lock_id mapping

    def _sanitize_connection_string(self, connection_string: str) -> str:
        """Sanitize database connection string to hide credentials for logging."""
        try:
            import re

            # Pattern to match password in connection strings
            # Matches both URL format and key=value format
            url_pattern = r"(://[^:]*:)[^@]*(@)"
            key_value_pattern = r"(password=)[^\s;]*([\s]|$|;)"

            # Sanitize URL format: postgresql://user:password@host/db -> postgresql://user:***@host/db
            sanitized = re.sub(url_pattern, r"\1***\2", connection_string)
            # Sanitize key=value format: password=secret -> password=***
            sanitized = re.sub(key_value_pattern, r"\1***\2", sanitized)

            return sanitized
        except Exception:
            # If sanitization fails, return generic string to avoid exposure
            return "postgresql://***:***@***/***"

    async def connect(self) -> bool:
        """Establish connection to PostgreSQL with fallback."""
        try:
            # Try to import and connect to PostgreSQL
            import asyncpg

            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.pool_min_size,
                max_size=self.pool_max_size,
            )

            # Test connection
            await self._test_connection()
            self.logger.info(
                f"Successfully connected to PostgreSQL: {self.sanitized_url}",
            )
            return True

        except ImportError:
            self.logger.warning("asyncpg library not available, using fallback")
            await self._initialize_fallback()
            return True
        except Exception as e:
            # Use sanitized URL in error messages - never expose credentials
            self.logger.warning(
                f"Failed to connect to PostgreSQL ({self.sanitized_url}): {e}",
            )
            if self.enable_fallback:
                await self._initialize_fallback()
                return True
            return False

    async def _test_connection(self):
        """Test PostgreSQL connection."""
        if self._pool:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

    async def _initialize_fallback(self):
        """Initialize in-memory fallback database."""
        if self._fallback_database is None:
            from omnibase_core.services.memory_database import InMemoryDatabase

            self._fallback_database = InMemoryDatabase()
            await self._fallback_database.connect()
            self._is_using_fallback = True
            self.logger.warning("Using in-memory database fallback")

    async def disconnect(self) -> None:
        """Close database connections."""
        if self._fallback_database:
            await self._fallback_database.disconnect()

        if self._pool:
            await self._pool.close()
            self._pool = None

    async def execute_query(
        self,
        query: str,
        parameters: tuple | None = None,
    ) -> list[dict[str, Any]]:
        """Execute SELECT query with PostgreSQL or fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_database.execute_query(query, parameters)

            async with self._pool.acquire() as conn:
                if parameters:
                    rows = await conn.fetch(query, *parameters)
                else:
                    rows = await conn.fetch(query)

                return [dict(row) for row in rows]

        except Exception as e:
            # Never expose connection details in error messages
            self.logger.error(f"Query execution failed on {self.sanitized_url}: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.execute_query(query, parameters)
            raise

    async def execute_command(
        self,
        command: str,
        parameters: tuple | None = None,
    ) -> int:
        """Execute INSERT/UPDATE/DELETE command with PostgreSQL or fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_database.execute_command(
                    command,
                    parameters,
                )

            async with self._pool.acquire() as conn:
                if parameters:
                    result = await conn.execute(command, *parameters)
                else:
                    result = await conn.execute(command)

                # Extract affected row count from result string like "UPDATE 3"
                return int(result.split()[-1]) if result else 0

        except Exception as e:
            # Never expose connection details in error messages
            self.logger.error(f"Command execution failed on {self.sanitized_url}: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.execute_command(command, parameters)
            raise

    async def execute_transaction(
        self,
        commands: list[tuple[str, tuple | None]],
    ) -> bool:
        """Execute commands in transaction with PostgreSQL or fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_database.execute_transaction(commands)

            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    for command, parameters in commands:
                        if parameters:
                            await conn.execute(command, *parameters)
                        else:
                            await conn.execute(command)
                return True

        except Exception as e:
            # Never expose connection details in error messages
            self.logger.error(
                f"Transaction execution failed on {self.sanitized_url}: {e}",
            )
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.execute_transaction(commands)
            return False

    async def acquire_lock(
        self,
        lock_name: str,
        timeout_seconds: int = 30,
    ) -> str | None:
        """Acquire PostgreSQL advisory lock with fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_database.acquire_lock(
                    lock_name,
                    timeout_seconds,
                )

            # Generate lock ID from lock name (simple hash)
            lock_id = hash(lock_name) % (2**31)  # Keep within int32 range

            async with self._pool.acquire() as conn:
                # Try to acquire lock with timeout
                end_time = time.time() + timeout_seconds

                while time.time() < end_time:
                    # Try to acquire lock (non-blocking)
                    result = await conn.fetchval(
                        "SELECT pg_try_advisory_lock($1)",
                        lock_id,
                    )

                    if result:
                        # Lock acquired - generate token
                        import uuid

                        lock_token = str(uuid.uuid4())
                        self._held_locks[lock_token] = lock_id
                        return lock_token

                    # Wait a bit before retrying
                    await asyncio.sleep(0.1)

                return None  # Timeout

        except Exception as e:
            # Never expose connection details in error messages
            self.logger.error(f"Lock acquisition failed on {self.sanitized_url}: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.acquire_lock(lock_name, timeout_seconds)
            return None

    async def release_lock(self, lock_token: str) -> bool:
        """Release PostgreSQL advisory lock with fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_database.release_lock(lock_token)

            if lock_token not in self._held_locks:
                return False

            lock_id = self._held_locks[lock_token]

            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT pg_advisory_unlock($1)", lock_id)

                if result:
                    del self._held_locks[lock_token]

                return bool(result)

        except Exception as e:
            # Never expose connection details in error messages
            self.logger.error(f"Lock release failed on {self.sanitized_url}: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.release_lock(lock_token)
            return False

    async def health_check(self) -> ModelServiceHealth:
        """Check PostgreSQL health with fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_database.health_check()

            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

                return ModelServiceHealth(
                    service_id="postgresql",
                    status="healthy",
                    last_check=time.time(),
                    error_message=None,
                )

        except Exception as e:
            # Never expose connection details in error messages
            self.logger.error(f"Health check failed on {self.sanitized_url}: {e}")
            return ModelServiceHealth(
                service_id="postgresql",
                status="critical",
                error_message=f"Health check error: {e}",
                last_check=time.time(),
            )

    async def get_connection_info(self) -> dict[str, Any]:
        """Get PostgreSQL connection information with fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_database.get_connection_info()

            return {
                "database_type": "postgresql",
                "connection_url": self.sanitized_url,  # Use sanitized URL
                "pool_size": self._pool.get_size() if self._pool else 0,
                "pool_min_size": self.pool_min_size,
                "pool_max_size": self.pool_max_size,
                "active_locks": len(self._held_locks),
                "using_fallback": self._is_using_fallback,
            }

        except Exception as e:
            self.logger.error(f"Connection info failed: {e}")
            return {
                "database_type": "postgresql",
                "error": str(e),
                "using_fallback": self._is_using_fallback,
            }
