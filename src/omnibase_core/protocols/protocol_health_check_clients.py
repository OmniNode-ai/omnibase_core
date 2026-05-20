# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocols for external service clients used in health checks."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolConnectionPool(Protocol):
    """Protocol for database connection pools (asyncpg, SQLAlchemy).

    Note: The execute method returns a sequence of row mappings. While specific
    implementations may return library-specific types (e.g., asyncpg.Record),
    the protocol uses a generic type that covers the common case of row-based
    query results.
    """

    async def execute(self, query: str) -> list[dict[str, object]]:
        """Execute a query on the connection pool.

        Args:
            query: SQL query string to execute.

        Returns:
            List of row dictionaries, where keys are column names and values
            are the column values. For non-SELECT queries, returns an empty list.
        """
        raise NotImplementedError  # stub-ok: protocol method body


@runtime_checkable
class ProtocolConnectionPoolWithConnection(Protocol):
    """Protocol for connection pools that provide connection context managers."""

    def connection(self) -> object:
        """Get a connection from the pool."""
        raise NotImplementedError  # stub-ok: protocol method body


@runtime_checkable
class ProtocolKafkaProducerAio(Protocol):
    """Protocol for aiokafka-style Kafka producers."""

    async def bootstrap_connected(self) -> bool:
        """Check if connected to bootstrap servers."""
        raise NotImplementedError  # stub-ok: protocol method body


@runtime_checkable
class ProtocolKafkaProducerConfluent(Protocol):
    """Protocol for confluent-kafka-style Kafka producers.

    Note: The list_topics method returns cluster metadata. While the actual
    confluent-kafka library returns a ClusterMetadata object, the protocol
    uses a generic dict type representing topic names to their metadata.
    """

    def list_topics(self, timeout: float) -> dict[str, object]:
        """List available Kafka topics.

        Args:
            timeout: Timeout in seconds for the operation.

        Returns:
            Dictionary mapping topic names to their metadata. The exact
            structure depends on the implementation, but typically includes
            partition information and broker details.
        """
        raise NotImplementedError  # stub-ok: protocol method body


@runtime_checkable
class ProtocolRedisClient(Protocol):
    """Protocol for async Redis clients (aioredis, redis-py)."""

    async def ping(self) -> bool:
        """Ping the Redis server."""
        raise NotImplementedError  # stub-ok: protocol method body


__all__ = [
    "ProtocolConnectionPool",
    "ProtocolConnectionPoolWithConnection",
    "ProtocolKafkaProducerAio",
    "ProtocolKafkaProducerConfluent",
    "ProtocolRedisClient",
]
