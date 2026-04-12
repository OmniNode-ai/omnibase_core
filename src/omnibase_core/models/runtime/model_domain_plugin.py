# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Domain plugin lifecycle models used by ProtocolDomainPlugin in omnibase_spi."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from omnibase_core.models.container.model_onex_container import ModelONEXContainer


@dataclass
class ModelDomainPluginConfig:
    """Configuration passed to domain plugins during lifecycle hooks.

    The kernel creates this config and passes it to each plugin during bootstrap,
    providing all context needed for initialization and handler wiring.

    Attributes:
        container: The ONEX container for dependency injection.
        event_bus: The event bus instance (InMemoryEventBus or KafkaEventBus).
        correlation_id: Correlation ID for distributed tracing.
        input_topic: The input topic for event consumers.
        output_topic: The output topic for event publishers.
        consumer_group: The consumer group for Kafka consumers.
        dispatch_engine: The MessageDispatchEngine for dispatcher wiring
            (set after engine creation, may be None).
        node_identity: Typed node identity for structured consumer group naming.
        kafka_bootstrap_servers: Kafka bootstrap servers string.
        output_topic_map: Per-event-type topic routing from contract published_events.

    Note:
        event_bus, dispatch_engine, and node_identity are typed as ``Any`` here
        so SPI has zero runtime dependency on omnibase_infra. Callers in infra
        pass the concrete types; the protocol contract is satisfied structurally.
    """

    container: ModelONEXContainer
    event_bus: Any
    correlation_id: UUID
    input_topic: str
    output_topic: str
    consumer_group: str

    dispatch_engine: Any | None = None
    node_identity: Any | None = None
    kafka_bootstrap_servers: str | None = None
    output_topic_map: dict[str, str] | None = None


@dataclass
class ModelDomainPluginResult:
    """Result returned by domain plugin lifecycle hooks.

    Attributes:
        plugin_id: Identifier of the plugin that produced this result.
        success: Whether the operation succeeded.
        message: Human-readable message describing the outcome.
        resources_created: List of resource identifiers created during this operation.
        services_registered: List of service class names registered in container.
        duration_seconds: Time taken for the operation.
        error_message: Error message if operation failed.
        unsubscribe_callbacks: Callbacks to invoke during shutdown for cleanup.
    """

    plugin_id: str
    success: bool
    message: str = ""
    resources_created: list[str] = field(default_factory=list)
    services_registered: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: str | None = None

    unsubscribe_callbacks: list[Callable[[], Awaitable[None]]] = field(
        default_factory=list
    )

    def get_error_message_or_default(self, default: str = "unknown") -> str:
        """Return error_message if set, otherwise the default value."""
        return self.error_message if self.error_message else default

    def __bool__(self) -> bool:
        """Return True if the operation succeeded.

        Warning:
            **Non-standard __bool__ behavior**: Returns ``True`` only when
            ``success`` is True. Differs from typical dataclass behavior.
        """
        return self.success

    @classmethod
    def succeeded(
        cls,
        plugin_id: str,
        message: str = "",
        duration_seconds: float = 0.0,
    ) -> ModelDomainPluginResult:
        """Create a simple success result."""
        return cls(
            plugin_id=plugin_id,
            success=True,
            message=message,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def failed(
        cls,
        plugin_id: str,
        error_message: str,
        message: str = "",
        duration_seconds: float = 0.0,
    ) -> ModelDomainPluginResult:
        """Create a failure result."""
        return cls(
            plugin_id=plugin_id,
            success=False,
            message=message or f"Plugin {plugin_id} failed",
            error_message=error_message,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def skipped(
        cls,
        plugin_id: str,
        reason: str,
    ) -> ModelDomainPluginResult:
        """Create a skipped result (plugin did not activate)."""
        return cls(
            plugin_id=plugin_id,
            success=True,
            message=f"Plugin {plugin_id} skipped: {reason}",
        )


__all__: list[str] = [
    "ModelDomainPluginConfig",
    "ModelDomainPluginResult",
]
