"""
Protocol for database connection operations.

This module provides the ProtocolDatabaseConnection protocol which defines
the contract for database connection implementations. It supports:
- Async connection lifecycle management
- Query execution with parameterized queries
- Transaction management with commit/rollback
- Connection pooling support

IMPORTANT - Architecture Boundary:
    This protocol is defined in omnibase_core. Concrete implementations
    (e.g., PostgresConnection, SQLiteConnection) belong in omnibase_infra,
    NOT in omnibase_core. This maintains clean architecture separation:

    - omnibase_core: Protocols (interfaces) only - no external dependencies
    - omnibase_infra: Concrete implementations with external library dependencies

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what ONEX Core actually needs
- Provide complete type hints for mypy strict mode compliance
- Support async operations for production deployments

Usage:
    from omnibase_core.protocols.infrastructure import ProtocolDatabaseConnection

    async def check_health(db: ProtocolDatabaseConnection) -> bool:
        return await db.is_connected()

Migration Guide:
    Step 1: Create an adapter implementing ProtocolDatabaseConnection (in omnibase_infra)

        NOTE: This adapter implementation belongs in omnibase_infra, not omnibase_core.
        Example location: omnibase_infra/adapters/database/postgres_connection_adapter.py

        The adapter should:
        - Import asyncpg (or your preferred async database library)
        - Implement all methods defined in ProtocolDatabaseConnection
        - Wrap a connection pool for efficient resource management

        See omnibase_infra for concrete implementation examples.

    Step 2: Register via DI container

        # In your application bootstrap code:
        adapter = PostgresConnectionAdapter(pool)  # Created in omnibase_infra
        container.register_service("ProtocolDatabaseConnection", adapter)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolDatabaseConnection(Protocol):
    """
    Protocol for database connection operations.

    Defines the minimal interface for database connections needed by ONEX Core.
    Implementations can wrap asyncpg, aiosqlite, databases, or other async
    database libraries.

    This protocol enables dependency inversion - components depend on
    this protocol rather than concrete database libraries, allowing:
    - Easier unit testing with mock implementations
    - Swapping database backends without code changes
    - Consistent interface across different database types

    Lifecycle Management:
        Implementations MAY use connection pooling for performance.
        Callers MUST NOT assume ownership of the connection.
        The creating code (often the DI container) is responsible for cleanup.

    Example:
        async def get_user(db: ProtocolDatabaseConnection, user_id: str) -> dict:
            result = await db.execute(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            return result[0] if result else {}
    """

    async def connect(self) -> None:
        """
        Establish connection to the database.

        For pooled connections, this may acquire a connection from the pool.

        Raises:
            ConnectionError: If connection cannot be established
        """
        ...

    async def disconnect(self) -> None:
        """
        Close the database connection.

        For pooled connections, this may return the connection to the pool.
        """
        ...

    async def is_connected(self) -> bool:
        """
        Check if the database connection is active.

        Returns:
            True if connected and healthy, False otherwise
        """
        ...

    async def execute(
        self,
        query: str,
        *args: object,
    ) -> list[dict[str, Any]]:
        """
        Execute a query and return results.

        Args:
            query: SQL query string with parameter placeholders
            *args: Query parameters (positional)

        Returns:
            List of result rows as dictionaries

        Raises:
            May raise implementation-specific database errors
        """
        ...

    async def execute_many(
        self,
        query: str,
        args_list: list[tuple[object, ...]],
    ) -> int:
        """
        Execute a query with multiple parameter sets.

        Args:
            query: SQL query string with parameter placeholders
            args_list: List of parameter tuples for batch execution

        Returns:
            Number of rows affected

        Raises:
            May raise implementation-specific database errors
        """
        ...

    async def begin_transaction(self) -> None:
        """
        Begin a database transaction.

        Raises:
            RuntimeError: If a transaction is already in progress
        """
        ...

    async def commit(self) -> None:
        """
        Commit the current transaction.

        Raises:
            RuntimeError: If no transaction is in progress
        """
        ...

    async def rollback(self) -> None:
        """
        Rollback the current transaction.

        Raises:
            RuntimeError: If no transaction is in progress
        """
        ...

    @property
    def in_transaction(self) -> bool:
        """
        Check if a transaction is currently in progress.

        Returns:
            True if in a transaction, False otherwise
        """
        ...


__all__ = ["ProtocolDatabaseConnection"]
