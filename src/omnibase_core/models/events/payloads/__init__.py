"""
Typed event payload models for ONEX coordination I/O.

This module provides typed payload models for use with ModelEventPublishIntent
and other event coordination patterns. Using typed payloads instead of
dict[str, Any] enables compile-time type checking and runtime validation.

Contents:
    ModelEventPayloadUnion: Union of all event payload types (18 types)
    ModelRuntimeEventPayloadUnion: Union of runtime event types (9 types)
    ModelDiscoveryEventPayloadUnion: Union of discovery event types (9 types)

    Runtime Events (9 types):
        - ModelNodeRegisteredEvent: Node registered with runtime
        - ModelNodeUnregisteredEvent: Node unregistered from runtime
        - ModelSubscriptionCreatedEvent: Event subscription created
        - ModelSubscriptionFailedEvent: Event subscription failed
        - ModelSubscriptionRemovedEvent: Event subscription removed
        - ModelRuntimeReadyEvent: Runtime fully initialized
        - ModelNodeGraphReadyEvent: Node graph ready for wiring
        - ModelWiringResultEvent: Event bus wiring result
        - ModelWiringErrorEvent: Event bus wiring error

    Discovery Events (9 types):
        - ModelToolInvocationEvent: Tool invocation request
        - ModelToolResponseEvent: Tool execution response
        - ModelNodeHealthEvent: Node health status update
        - ModelNodeShutdownEvent: Node shutdown notification
        - ModelNodeIntrospectionEvent: Node capability announcement
        - ModelIntrospectionResponseEvent: Introspection response
        - ModelRequestIntrospectionEvent: Introspection request
        - ModelToolDiscoveryRequest: Tool discovery request
        - ModelToolDiscoveryResponse: Tool discovery response

Usage:
    from omnibase_core.models.events.payloads import ModelEventPayloadUnion

    # Type-safe event handling
    def handle_event(payload: ModelEventPayloadUnion) -> None:
        if isinstance(payload, ModelNodeRegisteredEvent):
            print(f"Node registered: {payload.node_name}")
        elif isinstance(payload, ModelToolInvocationEvent):
            print(f"Tool invocation: {payload.tool_name}")

See Also:
    - ModelEventPublishIntent: Coordination event that uses these payloads
    - ModelRetryPolicy: Retry configuration for intent execution
"""

from omnibase_core.models.events.payloads.model_event_payload_union import (
    # Union types
    ModelDiscoveryEventPayloadUnion,
    ModelEventPayloadUnion,
    # Discovery Events
    ModelIntrospectionResponseEvent,
    # Runtime Events
    ModelNodeGraphReadyEvent,
    ModelNodeHealthEvent,
    ModelNodeIntrospectionEvent,
    ModelNodeRegisteredEvent,
    ModelNodeShutdownEvent,
    ModelNodeUnregisteredEvent,
    ModelRequestIntrospectionEvent,
    ModelRuntimeEventPayloadUnion,
    ModelRuntimeReadyEvent,
    ModelSubscriptionCreatedEvent,
    ModelSubscriptionFailedEvent,
    ModelSubscriptionRemovedEvent,
    ModelToolDiscoveryRequest,
    ModelToolDiscoveryResponse,
    ModelToolInvocationEvent,
    ModelToolResponseEvent,
    ModelWiringErrorEvent,
    ModelWiringResultEvent,
)
from omnibase_core.utils.util_payload_migration import (
    convert_dict_to_typed_payload,
    get_migration_example,
    get_supported_event_types,
    infer_payload_type_from_dict,
)

__all__ = [
    # Union types
    "ModelEventPayloadUnion",
    "ModelRuntimeEventPayloadUnion",
    "ModelDiscoveryEventPayloadUnion",
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
    # Discovery Events
    "ModelIntrospectionResponseEvent",
    "ModelNodeHealthEvent",
    "ModelNodeIntrospectionEvent",
    "ModelNodeShutdownEvent",
    "ModelRequestIntrospectionEvent",
    "ModelToolDiscoveryRequest",
    "ModelToolDiscoveryResponse",
    "ModelToolInvocationEvent",
    "ModelToolResponseEvent",
    # Migration helpers
    "convert_dict_to_typed_payload",
    "get_migration_example",
    "get_supported_event_types",
    "infer_payload_type_from_dict",
]
