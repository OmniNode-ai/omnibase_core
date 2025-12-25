"""
Typed event payload models for ONEX coordination I/O.

This module provides typed payload models for use with ModelEventPublishIntent
and other event coordination patterns. Using typed payloads instead of
dict[str, Any] enables compile-time type checking and runtime validation.

Contents:
    ModelEventPayloadUnion: Union of all event payload types
    ModelRuntimeEventPayloadUnion: Union of runtime event types (9 types)

    Runtime Events (9 types) - Currently included:
        - ModelNodeRegisteredEvent: Node registered with runtime
        - ModelNodeUnregisteredEvent: Node unregistered from runtime
        - ModelSubscriptionCreatedEvent: Event subscription created
        - ModelSubscriptionFailedEvent: Event subscription failed
        - ModelSubscriptionRemovedEvent: Event subscription removed
        - ModelRuntimeReadyEvent: Runtime fully initialized
        - ModelNodeGraphReadyEvent: Node graph ready for wiring
        - ModelWiringResultEvent: Event bus wiring result
        - ModelWiringErrorEvent: Event bus wiring error

    Discovery Events (9 types) - TODO: Add when circular import resolved:
        - ModelToolInvocationEvent: Tool invocation request
        - ModelToolResponseEvent: Tool execution response
        - ModelNodeHealthEvent: Node health status update
        - ModelNodeShutdownEvent: Node shutdown notification
        - ModelNodeIntrospectionEvent: Node capability announcement
        - ModelIntrospectionResponseEvent: Introspection response
        - ModelRequestIntrospectionEvent: Introspection request
        - ModelToolDiscoveryRequest: Tool discovery request
        - ModelToolDiscoveryResponse: Tool discovery response

Note:
    Discovery events are excluded due to a pre-existing circular import
    issue in omnibase_core.models.discovery. See model_event_payload_union.py
    for details.

Usage:
    from omnibase_core.models.events.payloads import ModelEventPayloadUnion

    # Type-safe event handling
    def handle_event(payload: ModelEventPayloadUnion) -> None:
        if isinstance(payload, ModelNodeRegisteredEvent):
            print(f"Node registered: {payload.node_name}")
        elif isinstance(payload, ModelWiringResultEvent):
            print(f"Wiring complete: {payload.success}")

See Also:
    - ModelEventPublishIntent: Coordination event that uses these payloads
    - ModelRetryPolicy: Retry configuration for intent execution
"""

from omnibase_core.models.events.payloads.model_event_payload_union import (
    ModelEventPayloadUnion,
    ModelNodeGraphReadyEvent,
    # Runtime Events
    ModelNodeRegisteredEvent,
    ModelNodeUnregisteredEvent,
    ModelRuntimeEventPayloadUnion,
    ModelRuntimeReadyEvent,
    ModelSubscriptionCreatedEvent,
    ModelSubscriptionFailedEvent,
    ModelSubscriptionRemovedEvent,
    ModelWiringErrorEvent,
    ModelWiringResultEvent,
)

__all__ = [
    # Union types
    "ModelEventPayloadUnion",
    "ModelRuntimeEventPayloadUnion",
    # Runtime Events
    "ModelNodeRegisteredEvent",
    "ModelNodeUnregisteredEvent",
    "ModelSubscriptionCreatedEvent",
    "ModelSubscriptionFailedEvent",
    "ModelSubscriptionRemovedEvent",
    "ModelRuntimeReadyEvent",
    "ModelNodeGraphReadyEvent",
    "ModelWiringResultEvent",
    "ModelWiringErrorEvent",
]
