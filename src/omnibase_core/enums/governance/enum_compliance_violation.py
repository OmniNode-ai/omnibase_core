# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance Violation Enum.

Specific violation types for handler contract compliance checks.
"""

from enum import Enum, unique


@unique
class EnumComplianceViolation(str, Enum):
    """Specific contract compliance violation types.

    Each value represents a distinct way a handler can bypass
    the contract-declared dispatch system.
    """

    HARDCODED_TOPIC = "hardcoded_topic"
    """Topic string literal in handler instead of contract declaration."""

    UNDECLARED_TRANSPORT = "undeclared_transport"
    """Handler uses a transport (DB, HTTP, Kafka) not declared in contract."""

    LOGIC_IN_NODE = "logic_in_node"
    """Business logic found in node.py instead of handler."""

    MISSING_HANDLER_ROUTING = "missing_handler_routing"
    """Handler exists in handlers/ but is not in contract.yaml handler_routing."""

    UNDECLARED_PUBLISH = "undeclared_publish"
    """Handler publishes to topic not in contract event_bus.publish_topics."""

    UNDECLARED_SUBSCRIBE = "undeclared_subscribe"
    """Handler subscribes to topic not in contract event_bus.subscribe_topics."""

    DIRECT_DB_ACCESS = "direct_db_access"
    """Handler constructs DB connections directly instead of using injected services."""

    UNREGISTERED_HANDLER = "unregistered_handler"
    """Handler file in handlers/ directory but not importable or registered."""

    WIRE_SCHEMA_MISMATCH = "wire_schema_mismatch"
    """Producer/consumer field name does not match wire schema contract."""

    MODEL_DUMP_DRIFT = "model_dump_drift"
    """Pydantic model schema has drifted from wire schema contract declaration."""

    HARDCODED_CONFIG = "hardcoded_config"
    """Configuration hardcoded as an in-source literal.

    Freestanding code passes runtime configuration as literals
    (e.g. ``max_tokens=2048``, ``temperature=0.7``, a private-range IP address)
    instead of resolving it from a contract or model registry.
    """

    RAW_HTTP_INFERENCE = "raw_http_inference"
    """Freestanding code performs raw HTTP I/O instead of a contract transport.

    Direct ``httpx`` / ``requests`` / ``aiohttp`` / ``urllib`` calls bypass the
    contract-declared transport + handler dispatch path.
    """

    RAW_KAFKA = "raw_kafka"
    """Freestanding code constructs a Kafka producer/consumer directly.

    Direct ``confluent_kafka`` / ``aiokafka`` / ``kafka`` client construction
    bypasses the injected event-bus transport.
    """

    DIRECT_DB = "direct_db"
    """Freestanding code opens a database/cache connection directly.

    Direct ``asyncpg`` / ``psycopg`` / ``sqlite3`` / ``redis`` connection
    construction bypasses injected persistence services.
    """

    SUBPROCESS_NETWORK = "subprocess_network"
    """Freestanding code shells out to a network/git operation via subprocess.

    ``subprocess`` invocations of ``ssh`` / ``scp`` / ``curl`` / ``git`` / ``rsync``
    bypass contract-declared transports and deployment handlers.
    """

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
