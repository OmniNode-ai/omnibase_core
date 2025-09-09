#!/usr/bin/env python3
"""
Protocol for Database Connection abstraction.

Provides a clean interface for database operations with proper fallback
strategies and connection management.
"""

from typing import Protocol, runtime_checkable

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.model.service.model_service_health import ModelServiceHealth


@runtime_checkable
class ProtocolDatabaseConnection(Protocol):
    """
    Protocol for database connection management.

    Abstracts database operations from specific implementations
    like asyncpg, aiomysql, or in-memory fallbacks.
    """

    async def connect(self) -> bool:
        """
        Establish connection to the database.

        Returns:
            True if connection successful, False otherwise
        """
        ...

    async def disconnect(self) -> None:
        """
        Close database connection and clean up resources.
        """
        ...

    async def execute_query(
        self,
        query: str,
        parameters: tuple | None = None,
    ) -> list[dict[str, str | int | float | bool | None]]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query string
            parameters: Optional query parameters

        Returns:
            List of row dictionaries
        """
        ...

    async def execute_command(
        self,
        command: str,
        parameters: tuple | None = None,
    ) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE command.

        Args:
            command: SQL command string
            parameters: Optional command parameters

        Returns:
            Number of affected rows
        """
        ...

    async def execute_transaction(
        self,
        commands: list[tuple[str, tuple | None]],
    ) -> bool:
        """
        Execute multiple commands in a transaction.

        Args:
            commands: List of (command, parameters) tuples

        Returns:
            True if all commands succeeded, False otherwise
        """
        ...

    async def acquire_lock(
        self,
        lock_name: str,
        timeout_seconds: int = 30,
    ) -> str | None:
        """
        Acquire a named advisory lock.

        Args:
            lock_name: Name of the lock to acquire
            timeout_seconds: Maximum time to wait for lock

        Returns:
            Lock token if successful, None if failed
        """
        ...

    async def release_lock(self, lock_token: str) -> bool:
        """
        Release an advisory lock.

        Args:
            lock_token: Token returned by acquire_lock

        Returns:
            True if released successfully, False otherwise
        """
        ...

    async def health_check(self) -> ModelServiceHealth:
        """
        Check database health and connection status.

        Returns:
            Database health information
        """
        ...

    async def get_connection_info(self) -> dict[str, ModelScalarValue]:
        """
        Get connection information and statistics.

        Returns:
            Dictionary with connection details
        """
        ...
