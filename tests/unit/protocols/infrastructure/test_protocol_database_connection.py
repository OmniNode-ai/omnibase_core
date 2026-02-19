# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ProtocolDatabaseConnection.

Validates:
1. Protocol definitions are correctly structured
2. runtime_checkable decorator works for isinstance checks
3. Mock implementations conform to protocols
4. Protocol method signatures are correct

Related:
    - PR #302: Add infrastructure protocols
"""

import asyncio
from typing import Any

import pytest

from omnibase_core.protocols.infrastructure import ProtocolDatabaseConnection

# =============================================================================
# Test Fixtures - Mock Implementations
# =============================================================================


class MockDatabaseConnection:
    """Minimal database connection implementation for protocol conformance testing."""

    def __init__(self) -> None:
        self._connected = False
        self._in_transaction = False
        self._data: list[dict[str, Any]] = []

    async def connect(self) -> None:
        """Establish connection to the database."""
        self._connected = True

    async def disconnect(self) -> None:
        """Close the database connection."""
        self._connected = False

    async def is_connected(self) -> bool:
        """Check if the database connection is active."""
        return self._connected

    async def execute(
        self,
        query: str,
        *args: Any,
    ) -> list[dict[str, Any]]:
        """Execute a query and return results."""
        if not self._connected:
            raise RuntimeError("Not connected")
        # Return mock data for SELECT queries
        if query.upper().startswith("SELECT"):
            return self._data
        return []

    async def execute_many(
        self,
        query: str,
        args_list: list[tuple[Any, ...]],
    ) -> int:
        """Execute a query with multiple parameter sets."""
        if not self._connected:
            raise RuntimeError("Not connected")
        return len(args_list)

    async def begin_transaction(self) -> None:
        """Begin a database transaction."""
        if self._in_transaction:
            raise RuntimeError("Transaction already in progress")
        self._in_transaction = True

    async def commit(self) -> None:
        """Commit the current transaction."""
        if not self._in_transaction:
            raise RuntimeError("No transaction in progress")
        self._in_transaction = False

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if not self._in_transaction:
            raise RuntimeError("No transaction in progress")
        self._in_transaction = False

    @property
    def in_transaction(self) -> bool:
        """Check if a transaction is currently in progress."""
        return self._in_transaction


class PartialDatabaseConnection:
    """Partial implementation that should NOT conform to protocol."""

    async def connect(self) -> None:
        """Only implements connect."""

    # Missing all other required methods


class WrongSignatureDatabaseConnection:
    """Implementation with wrong method signatures."""

    def connect(self) -> None:  # Should be async
        """Wrong signature - sync instead of async."""

    async def disconnect(self) -> None:
        pass

    async def is_connected(self) -> bool:
        return True

    async def execute(
        self,
        query: str,
        *args: Any,
    ) -> list[dict[str, Any]]:
        return []

    async def execute_many(
        self,
        query: str,
        args_list: list[tuple[Any, ...]],
    ) -> int:
        return 0

    async def begin_transaction(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    @property
    def in_transaction(self) -> bool:
        return False


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestProtocolDatabaseConnectionDefinition:
    """Test ProtocolDatabaseConnection protocol definition."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify protocol has @runtime_checkable decorator."""
        mock = MockDatabaseConnection()
        assert isinstance(mock, ProtocolDatabaseConnection)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """Verify isinstance returns False for non-conforming classes."""

        class NotADatabaseConnection:
            pass

        obj = NotADatabaseConnection()
        assert not isinstance(obj, ProtocolDatabaseConnection)

    def test_partial_implementation_fails_isinstance(self) -> None:
        """Verify partial implementations don't pass isinstance."""
        obj = PartialDatabaseConnection()
        assert not isinstance(obj, ProtocolDatabaseConnection)

    def test_protocol_methods_exist(self) -> None:
        """Verify protocol defines expected methods."""
        mock = MockDatabaseConnection()

        # Async methods
        assert hasattr(mock, "connect")
        assert hasattr(mock, "disconnect")
        assert hasattr(mock, "is_connected")
        assert hasattr(mock, "execute")
        assert hasattr(mock, "execute_many")
        assert hasattr(mock, "begin_transaction")
        assert hasattr(mock, "commit")
        assert hasattr(mock, "rollback")

        # Properties
        assert hasattr(mock, "in_transaction")

    def test_wrong_signature_passes_runtime_check(self) -> None:
        """
        Verify sync implementation passes runtime isinstance check.

        Note: Python's @runtime_checkable only checks for method/property names,
        NOT for async vs sync signatures. Static type checkers (mypy, pyright)
        will catch the distinction, but isinstance() cannot.

        This is a known limitation of runtime_checkable protocols.
        """
        wrong = WrongSignatureDatabaseConnection()
        # Runtime check passes (only checks names exist)
        assert isinstance(wrong, ProtocolDatabaseConnection)

        # But we can verify the method isn't actually async
        assert not asyncio.iscoroutinefunction(wrong.connect)


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestMockDatabaseConnectionBehavior:
    """Test MockDatabaseConnection behavior for protocol conformance."""

    @pytest.mark.asyncio
    async def test_initial_state(self) -> None:
        """Verify initial state is disconnected."""
        db = MockDatabaseConnection()
        assert not await db.is_connected()
        assert not db.in_transaction

    @pytest.mark.asyncio
    async def test_connect_disconnect_lifecycle(self) -> None:
        """Verify connection lifecycle works correctly."""
        db = MockDatabaseConnection()

        # Initially disconnected
        assert not await db.is_connected()

        # Connect
        await db.connect()
        assert await db.is_connected()

        # Disconnect
        await db.disconnect()
        assert not await db.is_connected()

    @pytest.mark.asyncio
    async def test_execute_requires_connection(self) -> None:
        """Verify execute raises error when not connected."""
        db = MockDatabaseConnection()

        with pytest.raises(RuntimeError, match="Not connected"):
            await db.execute("SELECT * FROM users")

    @pytest.mark.asyncio
    async def test_execute_returns_list(self) -> None:
        """Verify execute returns list of dictionaries."""
        db = MockDatabaseConnection()
        await db.connect()

        result = await db.execute("SELECT * FROM users")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_with_parameters(self) -> None:
        """Verify execute accepts parameters."""
        db = MockDatabaseConnection()
        await db.connect()

        # Should not raise
        result = await db.execute("SELECT * FROM users WHERE id = $1", "user-123")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_many_returns_row_count(self) -> None:
        """Verify execute_many returns affected row count."""
        db = MockDatabaseConnection()
        await db.connect()

        args_list = [("value1",), ("value2",), ("value3",)]
        count = await db.execute_many("INSERT INTO test VALUES ($1)", args_list)
        assert count == 3

    @pytest.mark.asyncio
    async def test_transaction_lifecycle(self) -> None:
        """Verify transaction lifecycle works correctly."""
        db = MockDatabaseConnection()
        await db.connect()

        # Initially no transaction
        assert not db.in_transaction

        # Begin transaction
        await db.begin_transaction()
        assert db.in_transaction

        # Commit
        await db.commit()
        assert not db.in_transaction

    @pytest.mark.asyncio
    async def test_transaction_rollback(self) -> None:
        """Verify transaction rollback works correctly."""
        db = MockDatabaseConnection()
        await db.connect()

        await db.begin_transaction()
        assert db.in_transaction

        await db.rollback()
        assert not db.in_transaction

    @pytest.mark.asyncio
    async def test_nested_transaction_raises_error(self) -> None:
        """Verify beginning transaction while in transaction raises error."""
        db = MockDatabaseConnection()
        await db.connect()

        await db.begin_transaction()

        with pytest.raises(RuntimeError, match="Transaction already in progress"):
            await db.begin_transaction()

    @pytest.mark.asyncio
    async def test_commit_without_transaction_raises_error(self) -> None:
        """Verify commit without transaction raises error."""
        db = MockDatabaseConnection()
        await db.connect()

        with pytest.raises(RuntimeError, match="No transaction in progress"):
            await db.commit()

    @pytest.mark.asyncio
    async def test_rollback_without_transaction_raises_error(self) -> None:
        """Verify rollback without transaction raises error."""
        db = MockDatabaseConnection()
        await db.connect()

        with pytest.raises(RuntimeError, match="No transaction in progress"):
            await db.rollback()


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestProtocolUsagePatterns:
    """Test common usage patterns with ProtocolDatabaseConnection."""

    @pytest.mark.asyncio
    async def test_function_accepting_protocol(self) -> None:
        """Test function that accepts ProtocolDatabaseConnection."""

        async def get_user_count(db: ProtocolDatabaseConnection) -> int:
            """Get the count of users from database."""
            if not await db.is_connected():
                await db.connect()
            result = await db.execute("SELECT COUNT(*) FROM users")
            return len(result)

        db = MockDatabaseConnection()
        count = await get_user_count(db)
        assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_context_manager_pattern(self) -> None:
        """Test protocol usage in context manager pattern."""

        class DatabaseContextManager:
            """Context manager wrapper for database connections."""

            def __init__(self, db: ProtocolDatabaseConnection):
                self._db = db

            async def __aenter__(self) -> ProtocolDatabaseConnection:
                await self._db.connect()
                return self._db

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                await self._db.disconnect()

        db = MockDatabaseConnection()
        async with DatabaseContextManager(db) as conn:
            assert await conn.is_connected()
            result = await conn.execute("SELECT 1")
            assert isinstance(result, list)

        assert not await db.is_connected()

    @pytest.mark.asyncio
    async def test_transaction_context_manager_pattern(self) -> None:
        """Test protocol usage in transaction context manager pattern."""

        class TransactionContextManager:
            """Context manager for database transactions."""

            def __init__(self, db: ProtocolDatabaseConnection):
                self._db = db

            async def __aenter__(self) -> ProtocolDatabaseConnection:
                await self._db.begin_transaction()
                return self._db

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
                if exc_type is not None:
                    await self._db.rollback()
                else:
                    await self._db.commit()
                return False  # Don't suppress exceptions

        db = MockDatabaseConnection()
        await db.connect()

        async with TransactionContextManager(db):
            assert db.in_transaction
            await db.execute("INSERT INTO test VALUES ($1)", "value")

        assert not db.in_transaction

    def test_type_annotation_works(self) -> None:
        """Test that type annotations work with protocol."""

        def get_transaction_status(db: ProtocolDatabaseConnection) -> bool:
            return db.in_transaction

        mock: ProtocolDatabaseConnection = MockDatabaseConnection()
        assert get_transaction_status(mock) is False


@pytest.mark.unit
class TestProtocolImports:
    """Test that protocols are correctly exported."""

    def test_import_from_infrastructure_module(self) -> None:
        """Test imports from omnibase_core.protocols.infrastructure."""
        from omnibase_core.protocols.infrastructure import ProtocolDatabaseConnection

        assert ProtocolDatabaseConnection is not None

    def test_import_from_protocol_file(self) -> None:
        """Test direct imports from protocol file."""
        from omnibase_core.protocols.infrastructure.protocol_database_connection import (
            ProtocolDatabaseConnection,
        )

        assert ProtocolDatabaseConnection is not None
