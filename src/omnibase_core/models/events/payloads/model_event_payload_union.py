"""
Typed event payload union for ModelEventPublishIntent.

This module defines a union type that encompasses all event payload types
that can be published through the ModelEventPublishIntent coordination pattern.
Using typed payloads instead of dict[str, Any] provides:
- Compile-time type checking
- Runtime validation via Pydantic
- Better IDE support and autocomplete
- Explicit documentation of supported event types

Event Categories:
    Runtime Events (ModelRuntimeEventBase subclasses):
        - Node lifecycle: registration, unregistration
        - Subscription lifecycle: created, failed, removed
        - Runtime status: ready, graph ready
        - Wiring: result, error

    Discovery Events (ModelOnexEvent subclasses):
        - Tool lifecycle: invocation, response
        - Node discovery: introspection, health, shutdown
        - Tool discovery: request, response

Note:
    Import Order: Imports are sorted alphabetically by module path (isort convention).
    Discovery events from `omnibase_core.models.discovery.*` come before runtime
    events from `omnibase_core.models.events.*` due to alphabetical ordering.

    For true discriminated union support with optimal performance,
    event models would need Literal types for event_type (e.g.,
    `event_type: Literal["onex.runtime.node.registered"]`).
    Currently, Pydantic will try each type in order until validation
    succeeds. This is correct but less efficient than discriminated unions.
"""

# Discovery Events (ModelOnexEvent subclasses)
# These are service discovery events for tool and node introspection.
from omnibase_core.models.discovery.model_introspection_response_event import (
    ModelIntrospectionResponseEvent,
)
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeIntrospectionEvent,
)
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.discovery.model_nodehealthevent import ModelNodeHealthEvent
from omnibase_core.models.discovery.model_request_introspection_event import (
    ModelRequestIntrospectionEvent,
)
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.discovery.model_tooldiscoveryrequest import (
    ModelToolDiscoveryRequest,
)
from omnibase_core.models.discovery.model_tooldiscoveryresponse import (
    ModelToolDiscoveryResponse,
)

# Runtime Events (ModelRuntimeEventBase subclasses)
# These are runtime lifecycle events for node registration, subscriptions, and wiring.
from omnibase_core.models.events.model_node_graph_ready_event import (
    ModelNodeGraphReadyEvent,
)
from omnibase_core.models.events.model_node_registered_event import (
    ModelNodeRegisteredEvent,
)
from omnibase_core.models.events.model_node_unregistered_event import (
    ModelNodeUnregisteredEvent,
)
from omnibase_core.models.events.model_runtime_ready_event import (
    ModelRuntimeReadyEvent,
)
from omnibase_core.models.events.model_subscription_created_event import (
    ModelSubscriptionCreatedEvent,
)
from omnibase_core.models.events.model_subscription_failed_event import (
    ModelSubscriptionFailedEvent,
)
from omnibase_core.models.events.model_subscription_removed_event import (
    ModelSubscriptionRemovedEvent,
)
from omnibase_core.models.events.model_wiring_error_event import (
    ModelWiringErrorEvent,
)
from omnibase_core.models.events.model_wiring_result_event import (
    ModelWiringResultEvent,
)

__all__ = [
    # Union types
    "ModelEventPayloadUnion",
    "ModelDiscoveryEventPayloadUnion",
    "ModelRuntimeEventPayloadUnion",
    # Re-export individual discovery event types for convenience
    # (discovery imports come before runtime - alphabetical by module path)
    "ModelIntrospectionResponseEvent",
    "ModelNodeHealthEvent",
    "ModelNodeIntrospectionEvent",
    "ModelNodeShutdownEvent",
    "ModelRequestIntrospectionEvent",
    "ModelToolDiscoveryRequest",
    "ModelToolDiscoveryResponse",
    "ModelToolInvocationEvent",
    "ModelToolResponseEvent",
    # Re-export individual runtime event types for convenience
    "ModelNodeGraphReadyEvent",
    "ModelNodeRegisteredEvent",
    "ModelNodeUnregisteredEvent",
    "ModelRuntimeReadyEvent",
    "ModelSubscriptionCreatedEvent",
    "ModelSubscriptionFailedEvent",
    "ModelSubscriptionRemovedEvent",
    "ModelWiringErrorEvent",
    "ModelWiringResultEvent",
]


# Type alias for discovery event payloads (9 types)
# These are ModelOnexEvent subclasses for service discovery events
# Defined first for alphabetical consistency (discovery < runtime)
ModelDiscoveryEventPayloadUnion = (
    ModelIntrospectionResponseEvent
    | ModelNodeHealthEvent
    | ModelNodeIntrospectionEvent
    | ModelNodeShutdownEvent
    | ModelRequestIntrospectionEvent
    | ModelToolDiscoveryRequest
    | ModelToolDiscoveryResponse
    | ModelToolInvocationEvent
    | ModelToolResponseEvent
)


# Type alias for runtime event payloads (9 types)
# These are ModelRuntimeEventBase subclasses for runtime lifecycle events
ModelRuntimeEventPayloadUnion = (
    ModelNodeRegisteredEvent
    | ModelNodeUnregisteredEvent
    | ModelSubscriptionCreatedEvent
    | ModelSubscriptionFailedEvent
    | ModelSubscriptionRemovedEvent
    | ModelRuntimeReadyEvent
    | ModelNodeGraphReadyEvent
    | ModelWiringResultEvent
    | ModelWiringErrorEvent
)


# Main type alias for all event payloads (18 types total)
# Includes both discovery events and runtime events (alphabetical order).
#
# Usage:
#     from omnibase_core.models.events.payloads import ModelEventPayloadUnion
#
#     def process_event(payload: ModelEventPayloadUnion) -> None:
#         if isinstance(payload, ModelNodeRegisteredEvent):
#             handle_registration(payload)
#         elif isinstance(payload, ModelToolInvocationEvent):
#             handle_tool_invocation(payload)
#         # ... etc
#
ModelEventPayloadUnion = ModelDiscoveryEventPayloadUnion | ModelRuntimeEventPayloadUnion
