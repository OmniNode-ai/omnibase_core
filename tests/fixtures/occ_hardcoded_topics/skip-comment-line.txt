# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kafka Event Bus Adapter Protocol - ONEX SPI Interface.

Protocol definitions for Kafka backend implementations in the
ONEX event bus system. It defines the contract for Kafka-specific event bus adapters
including configuration, connection management, and core messaging operations.

Key Protocols:
    - ProtocolKafkaConfig: Configuration parameters for Kafka clients.
    - ProtocolKafkaAdapter: Kafka-based event bus adapter interface.

The Kafka adapter provides canonical ONEX topic naming (realm-agnostic, no environment
prefix), consumer group coordination, and full support for Kafka's publish/subscribe
messaging patterns with proper partitioning and offset management.

Example:
    ```python
    from omnibase_spi.protocols.event_bus import ProtocolKafkaAdapter

    # Get Kafka adapter from dependency injection
    adapter: ProtocolKafkaAdapter = get_kafka_adapter()

    # Build canonical ONEX topic name (realm-agnostic, no env prefix)
    topic = await adapter.build_topic_name("user-events")
    # Returns: "onex.evt.user-events.v1" (canonical ONEX format)

    # Publish event
    await adapter.publish(
        topic=topic,
        key=b"user:123",
        value=b'{"event": "user_created"}',
        headers={"correlation_id": "abc123"}
    )

    # Subscribe to events
    async def handle_message(msg: ProtocolEventMessage) -> None:
        print(f"Received: {msg}")

    unsubscribe = await adapter.subscribe(
        topic=topic,
        group_id="my-consumer-group",
        on_message=handle_message
    )

    # Cleanup
    await adapter.close()
    ```

See Also:
    - ProtocolRedpandaAdapter: Redpanda-specific adapter with optimized defaults.
    - ProtocolEventBusService: Service layer for event bus operations.
    - ProtocolEventBusProvider: Factory for obtaining event bus instances.
"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.types import JsonType
    from omnibase_spi.protocols.types.protocol_event_bus_types import (
        ProtocolEventMessage,
    )

# Type aliases to avoid namespace violations (PEP 695)
type EventBusHeaders = "JsonType"  # Generic headers type


@runtime_checkable
class ProtocolKafkaConfig(Protocol):
    """
    Protocol for Kafka client configuration parameters.

    Defines security, authentication, and operational settings for
    Kafka connections including SASL/SSL configuration, consumer
    group behavior, and timeout management.

    Attributes:
        security_protocol: Security protocol (PLAINTEXT, SSL, SASL_SSL)
        sasl_mechanism: SASL auth mechanism (PLAIN, SCRAM-SHA-256, etc.)
        sasl_username: SASL authentication username
        sasl_password: SASL authentication password
        ssl_cafile: Path to CA certificate file for SSL
        auto_offset_reset: Consumer offset reset behavior (earliest, latest)
        enable_auto_commit: Whether to auto-commit consumer offsets
        session_timeout_ms: Consumer session timeout in milliseconds
        request_timeout_ms: Request timeout in milliseconds

    Example:
        ```python
        adapter: ProtocolKafkaAdapter = get_kafka_adapter()
        config = adapter.kafka_config

        print(f"Security: {config.security_protocol}")
        print(f"SASL: {config.sasl_mechanism}")
        print(f"Auto-commit: {config.enable_auto_commit}")
        print(f"Session timeout: {config.session_timeout_ms}ms")
        ```

    See Also:
        - ProtocolKafkaAdapter: Kafka adapter using this config
        - ProtocolKafkaClient: Low-level Kafka client
    """

    security_protocol: str
    sasl_mechanism: str
    sasl_username: str | None
    sasl_password: str | None
    ssl_cafile: str | None
    auto_offset_reset: str
    enable_auto_commit: bool
    session_timeout_ms: int
    request_timeout_ms: int


@runtime_checkable
class ProtocolKafkaAdapter(Protocol):
    """
    Protocol for Kafka-based event bus adapter implementations.

    Provides Kafka-specific configuration, connection management, and
    core event bus operations for publishing events and subscribing
    to topics with environment and group isolation.

    Example:
        ```python
        adapter: ProtocolKafkaAdapter = get_kafka_adapter()

        # Access configuration
        print(f"Servers: {adapter.bootstrap_servers}")
        print(f"Environment: {adapter.environment}")
        print(f"Group: {adapter.group}")

        # Build canonical ONEX topic name (no env prefix)
        topic = await adapter.build_topic_name("user-events")

        # Publish event
        await adapter.publish(
            topic=topic,
            key=b"user:123",
            value=b'{"event": "user_created"}',
            headers={"correlation_id": "abc123"}
        )

        # Subscribe to events
        async def handle_message(msg: ProtocolEventMessage):
            print(f"Received: {msg}")

        unsubscribe = await adapter.subscribe(
            topic=topic,
            group_id="my-consumer-group",
            on_message=handle_message
        )

        # Cleanup
        await adapter.close()
        ```

    See Also:
        - ProtocolKafkaConfig: Configuration parameters
        - ProtocolEventBusProvider: ONEX event bus interface
        - ProtocolKafkaClient: Low-level Kafka operations
    """

    @property
    def bootstrap_servers(self) -> str:
        """Kafka bootstrap servers connection string.

        Returns:
            Comma-separated list of broker addresses (e.g., "kafka1:9092,kafka2:9092").
        """
        ...

    @property
    def environment(self) -> str:
        """Environment name for metadata and consumer-group coordination.

        Used for consumer-group naming and event metadata/headers, NOT for
        topic name prefixing. Topics are realm-agnostic in ONEX convention.

        Returns:
            Environment identifier (e.g., "dev", "staging", "prod").
        """
        ...

    @property
    def group(self) -> str:
        """Consumer group identifier.

        Returns:
            Group ID for consumer group coordination.
        """
        ...

    @property
    def config(self) -> ProtocolKafkaConfig | None:
        """Optional Kafka configuration overrides.

        Returns:
            Kafka configuration object or None for defaults.
        """
        ...

    @property
    def kafka_config(self) -> ProtocolKafkaConfig:
        """Complete Kafka configuration with all settings.

        Returns:
            Full Kafka configuration object including security and timeout settings.
        """
        ...

    async def build_topic_name(self, topic: str) -> str:
        """
        Build canonical ONEX topic name (realm-agnostic, no environment prefix).

        Topics follow the ONEX naming convention and are never prefixed with
        environment identifiers like ``dev-``, ``staging-``, or ``prod-``.

        Args:
            topic: Base topic name.

        Returns:
            Canonical ONEX topic name without environment prefix.
        """
        ...

    # Core event bus adapter interface methods
    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: "EventBusHeaders",
    ) -> None:
        """
        Publish event message to Kafka topic.

        Args:
            topic: Target topic name.
            key: Optional message key for partitioning.
            value: Message payload as bytes.
            headers: Event headers/metadata.

        Returns:
            None. The method completes when the message is successfully published.

        Raises:
            PublishError: If message publication fails.
        """
        ...

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[["ProtocolEventMessage"], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """
        Subscribe to Kafka topic with consumer group.

        Args:
            topic: Topic to subscribe to.
            group_id: Consumer group identifier.
            on_message: Async callback for message handling.

        Returns:
            Async callable to unsubscribe from the topic.

        Raises:
            SubscriptionError: If subscription fails.
        """
        ...

    async def close(self, timeout_seconds: float = 30.0) -> None:
        """Close Kafka adapter and release resources.

        Cleanly shuts down producer and consumer connections, flushes
        pending messages, and releases network resources.

        Args:
            timeout_seconds: Maximum time to wait for cleanup to complete.
                Defaults to 30.0 seconds.

        Returns:
            None. The method completes when all resources are released.

        Raises:
            TimeoutError: If cleanup does not complete within the specified timeout.

        Example:
            ```python
            # Close with default timeout
            await adapter.close()

            # Close with custom timeout
            await adapter.close(timeout_seconds=60.0)
            ```
        """
        ...
