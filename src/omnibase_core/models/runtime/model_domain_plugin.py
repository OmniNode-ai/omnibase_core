# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Domain plugin configuration model used by ProtocolDomainPlugin in omnibase_spi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.runtime.model_domain_plugin_result import (
    ModelDomainPluginResult,
)

__all__: list[str] = ["ModelDomainPluginConfig", "ModelDomainPluginResult"]


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
