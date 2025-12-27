"""
Event emission intent payloads for event bus publishing.

This module provides typed payloads for event-related intents:
- ModelPayloadEmitEvent: Domain event emission to event bus

Design Pattern:
    Reducers emit these payloads when event publishing side effects are needed.
    The Effect node receives the intent, pattern-matches on the `intent_type`
    discriminator, and publishes the event to the configured event bus.

    This separation ensures Reducer purity - the Reducer declares the desired
    outcome without performing the actual side effect.

Event Integration:
    - ModelPayloadEmitEvent supports structured event emission with type, data, and metadata
    - Supports multiple event bus targets (Kafka, Redis, in-memory)
    - Includes correlation ID for distributed tracing

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadEmitEvent
    >>>
    >>> # Domain event payload
    >>> event_payload = ModelPayloadEmitEvent(
    ...     event_type="order.created",
    ...     event_data={"order_id": "12345", "total": 99.99},
    ...     topic="orders",
    ...     correlation_id="req-abc-123",
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
    omnibase_core.events: Event system implementation
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadEmitEvent"]


class ModelPayloadEmitEvent(ModelIntentPayloadBase):
    """Payload for event emission intents.

    Emitted by Reducers when a domain event should be published to the event bus.
    The Effect node executes this intent by publishing the event to the configured
    message broker (Kafka, Redis Streams, etc.).

    Supports structured events with type classification, data payload, topic routing,
    and correlation tracking for distributed tracing.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "emit_event".
            Placed first for optimal union type resolution performance.
        event_type: Domain event type following naming conventions.
            Examples: "order.created", "user.registered", "payment.processed".
        event_data: The actual event data payload. Must be JSON-serializable.
        topic: Target topic/channel for event routing. Determines which consumers
            receive the event.
        correlation_id: Optional correlation ID for distributed tracing. Links
            this event to the originating request across service boundaries.
        partition_key: Optional partition key for ordered delivery. Events with
            the same partition key are delivered in order.
        headers: Optional headers for event metadata (e.g., content-type, version).

    Example:
        >>> payload = ModelPayloadEmitEvent(
        ...     event_type="inventory.updated",
        ...     event_data={"sku": "PROD-123", "quantity": 50, "warehouse": "US-WEST"},
        ...     topic="inventory-events",
        ...     correlation_id="req-xyz-789",
        ...     partition_key="PROD-123",
        ...     headers={"event-version": "1.0", "source": "inventory-service"},
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["emit_event"] = Field(
        default="emit_event",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    event_type: str = Field(
        ...,
        description=(
            "Domain event type following naming conventions. Use dot notation "
            "for namespacing. Examples: 'order.created', 'user.registered'."
        ),
        min_length=1,
        max_length=256,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$",
    )

    event_data: dict[str, object] = Field(
        ...,
        description=(
            "The actual event data payload. Must be JSON-serializable. Contains "
            "the domain event information to be published."
        ),
    )

    topic: str = Field(
        ...,
        description=(
            "Target topic or channel for event routing. Determines which "
            "consumers receive the event. Examples: 'orders', 'user-events'."
        ),
        min_length=1,
        max_length=256,
    )

    correlation_id: str | None = Field(
        default=None,
        description=(
            "Optional correlation ID for distributed tracing. Links this event "
            "to the originating request across service boundaries."
        ),
        max_length=128,
    )

    partition_key: str | None = Field(
        default=None,
        description=(
            "Optional partition key for ordered delivery. Events with the same "
            "partition key are guaranteed to be delivered in order."
        ),
        max_length=256,
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Optional headers for event metadata. Common headers: 'event-version', "
            "'source', 'content-type', 'schema-id'."
        ),
    )
