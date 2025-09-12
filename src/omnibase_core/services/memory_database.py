#!/usr/bin/env python3
"""
In-memory Database implementation.

Provides a fallback implementation of ProtocolDatabaseConnection
using in-memory storage when external databases are unavailable.
"""

import asyncio
import time
from typing import Any
from uuid import uuid4

from omnibase_core.models.service.model_service_health import ModelServiceHealth
from omnibase_core.protocol.protocol_database_connection import (
    ProtocolDatabaseConnection,
)


class InMemoryDatabase(ProtocolDatabaseConnection):
    """
    In-memory database fallback implementation.

    Stores all data in memory. Not suitable for persistent storage
    but provides a working fallback when external databases
    are unavailable.
    """

    def __init__(self):
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self._locks: dict[str, dict[str, Any]] = {}  # lock_token -> lock_info
        self._lock = asyncio.Lock()
        self._connected = False

    async def connect(self) -> bool:
        """Establish in-memory connection (always succeeds)."""
        async with self._lock:
            self._connected = True
        return True

    async def disconnect(self) -> None:
        """Close in-memory connection and clean up."""
        async with self._lock:
            self._tables.clear()
            self._locks.clear()
            self._connected = False

    async def execute_query(
        self,
        query: str,
        parameters: tuple | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute SELECT query in memory.

        This is a simplified implementation that supports basic SELECT operations.
        Real implementations would use SQL parsing.
        """
        if not self._connected:
            raise RuntimeError("Database not connected")

        async with self._lock:
            # Simple query parsing for common cases
            query_lower = query.lower().strip()

            # Handle simple health check queries
            if "select 1" in query_lower or "select version()" in query_lower:
                return [{"result": 1}]

            # Handle table queries (simplified)
            if query_lower.startswith("select"):
                # Extract table name (very basic parsing)
                if " from " in query_lower:
                    parts = query_lower.split(" from ")
                    if len(parts) > 1:
                        table_name = parts[1].split()[0].strip()
                        return self._tables.get(table_name, [])

                # Default empty result
                return []

            return []

    async def execute_command(
        self,
        command: str,
        parameters: tuple | None = None,
    ) -> int:
        """
        Execute INSERT/UPDATE/DELETE command in memory.

        This is a simplified implementation for basic operations.
        """
        if not self._connected:
            raise RuntimeError("Database not connected")

        async with self._lock:
            command_lower = command.lower().strip()

            # Handle CREATE TABLE
            if command_lower.startswith("create table"):
                table_name = self._extract_table_name(command_lower, "create table")
                if table_name and table_name not in self._tables:
                    self._tables[table_name] = []
                return 1

            # Handle INSERT
            if command_lower.startswith("insert into"):
                table_name = self._extract_table_name(command_lower, "insert into")
                if table_name:
                    # Simplified insert - create a dummy record
                    if table_name not in self._tables:
                        self._tables[table_name] = []

                    record = {"id": str(uuid4()), "created_at": time.time()}
                    if parameters:
                        # Add parameters as fields (simplified)
                        for i, param in enumerate(parameters):
                            record[f"field_{i}"] = param

                    self._tables[table_name].append(record)
                    return 1

            # Handle UPDATE
            elif command_lower.startswith("update"):
                table_name = self._extract_table_name(command_lower, "update")
                if table_name and table_name in self._tables:
                    # Simplified update - update all records
                    affected_rows = len(self._tables[table_name])
                    for record in self._tables[table_name]:
                        record["updated_at"] = time.time()
                    return affected_rows

            # Handle DELETE
            elif command_lower.startswith("delete from"):
                table_name = self._extract_table_name(command_lower, "delete from")
                if table_name and table_name in self._tables:
                    affected_rows = len(self._tables[table_name])
                    self._tables[table_name].clear()
                    return affected_rows

            return 0

    def _extract_table_name(self, command: str, prefix: str) -> str | None:
        """Extract table name from SQL command (simplified)."""
        try:
            # Remove prefix and get table name
            after_prefix = command[len(prefix) :].strip()
            table_name = after_prefix.split()[0].strip()
            # Remove common SQL elements
            table_name = table_name.replace("(", "").replace(",", "")
            return table_name if table_name else None
        except (IndexError, AttributeError):
            return None

    async def execute_transaction(
        self,
        commands: list[tuple[str, tuple | None]],
    ) -> bool:
        """Execute commands in transaction (atomic operation)."""
        if not self._connected:
            raise RuntimeError("Database not connected")

        async with self._lock:
            # Create a backup of current state
            backup_tables = {
                table: records.copy() for table, records in self._tables.items()
            }

            try:
                # Execute all commands
                for command, parameters in commands:
                    await self.execute_command(command, parameters)
                return True

            except Exception:
                # Restore backup on failure
                self._tables = backup_tables
                return False

    async def acquire_lock(
        self,
        lock_name: str,
        timeout_seconds: int = 30,
    ) -> str | None:
        """Acquire a named advisory lock."""
        if not self._connected:
            return None

        end_time = time.time() + timeout_seconds

        while time.time() < end_time:
            async with self._lock:
                # Check if lock is already held
                active_locks = {
                    token: info
                    for token, info in self._locks.items()
                    if info["lock_name"] == lock_name
                    and info["expires_at"] > time.time()
                }

                if not active_locks:
                    # Lock is available
                    lock_token = str(uuid4())
                    self._locks[lock_token] = {
                        "lock_name": lock_name,
                        "acquired_at": time.time(),
                        "expires_at": time.time() + 300,  # 5 minute default expiry
                    }
                    return lock_token

            # Wait a bit before retrying
            await asyncio.sleep(0.1)

        return None  # Timeout

    async def release_lock(self, lock_token: str) -> bool:
        """Release an advisory lock."""
        if not self._connected:
            return False

        async with self._lock:
            if lock_token in self._locks:
                del self._locks[lock_token]
                return True
            return False

    async def health_check(self) -> ModelServiceHealth:
        """Check in-memory database health (always healthy if connected)."""
        if not self._connected:
            return ModelServiceHealth(
                service_id="memory_database",
                status="critical",
                error_message="Database not connected",
                last_check=time.time(),
            )

        return ModelServiceHealth(
            service_id="memory_database",
            status="healthy",
            last_check=time.time(),
            error_message=None,
        )

    async def get_connection_info(self) -> dict[str, Any]:
        """Get in-memory database connection information."""
        async with self._lock:
            return {
                "database_type": "memory",
                "connected": self._connected,
                "tables": list(self._tables.keys()),
                "total_records": sum(len(records) for records in self._tables.values()),
                "active_locks": len(
                    [
                        lock
                        for lock in self._locks.values()
                        if lock["expires_at"] > time.time()
                    ],
                ),
                "memory_usage": "not_tracked",
            }

    # Additional methods for testing and management

    async def clear_all_data(self) -> None:
        """Clear all data (for testing)."""
        async with self._lock:
            self._tables.clear()
            self._locks.clear()

    async def get_table_data(self, table_name: str) -> list[dict[str, Any]]:
        """Get all data from a specific table (for debugging)."""
        async with self._lock:
            return self._tables.get(table_name, []).copy()

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        async with self._lock:
            total_records = sum(len(records) for records in self._tables.values())
            active_locks = len(
                [
                    lock
                    for lock in self._locks.values()
                    if lock["expires_at"] > time.time()
                ],
            )

            return {
                "total_tables": len(self._tables),
                "total_records": total_records,
                "active_locks": active_locks,
                "expired_locks": len(self._locks) - active_locks,
                "largest_table": max(
                    (len(records) for records in self._tables.values()),
                    default=0,
                ),
            }
