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
    Runtime Events (ModelRuntimeEventBase subclasses) - Currently included:
        - Node lifecycle: registration, unregistration
        - Subscription lifecycle: created, failed, removed
        - Runtime status: ready, graph ready
        - Wiring: result, error

    Discovery Events (ModelOnexEvent subclasses) - TODO: Add when circular import resolved:
        - Tool lifecycle: invocation, response
        - Node discovery: introspection, health, shutdown
        - Tool discovery: request, response

Note:
    Discovery events (ModelOnexEvent subclasses) are currently excluded due to a
    pre-existing circular import issue in the codebase. When importing
    omnibase_core.models.discovery, a circular import chain occurs:
        discovery -> core -> common -> validation -> contracts -> mixins -> discovery

    Once this circular import is resolved, the following types should be added:
        - ModelToolInvocationEvent
        - ModelToolResponseEvent
        - ModelNodeHealthEvent
        - ModelNodeShutdownEvent
        - ModelNodeIntrospectionEvent
        - ModelIntrospectionResponseEvent
        - ModelRequestIntrospectionEvent
        - ModelToolDiscoveryRequest
        - ModelToolDiscoveryResponse

    For true discriminated union support with optimal performance,
    event models would need Literal types for event_type (e.g.,
    `event_type: Literal["onex.runtime.node.registered"]`).
    Currently, Pydantic will try each type in order until validation
    succeeds. This is correct but less efficient than discriminated unions.
"""

# Runtime Events (ModelRuntimeEventBase subclasses)
# These events do NOT trigger the circular import and are safe to use
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

# NOTE: Discovery Events are excluded due to pre-existing circular import.
# See module docstring for details on which events to add once resolved.
# Imports would be:
#   from omnibase_core.models.discovery.model_introspection_response_event import ...
#   from omnibase_core.models.discovery.model_nodehealthevent import ...
#   from omnibase_core.models.discovery.model_nodeintrospectionevent import ...
#   from omnibase_core.models.discovery.model_node_shutdown_event import ...
#   from omnibase_core.models.discovery.model_request_introspection_event import ...
#   from omnibase_core.models.discovery.model_tool_invocation_event import ...
#   from omnibase_core.models.discovery.model_tool_response_event import ...
#   from omnibase_core.models.discovery.model_tooldiscoveryrequest import ...
#   from omnibase_core.models.discovery.model_tooldiscoveryresponse import ...

__all__ = [
    "ModelEventPayloadUnion",
    "ModelRuntimeEventPayloadUnion",
    # Re-export individual runtime event types for convenience
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


# Type alias for runtime event payloads (9 types)
# These are the events that can be published via ModelEventPublishIntent
# without triggering circular imports
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


# Main type alias for all event payloads
# Currently only includes runtime events due to circular import issue.
# Once the circular import in omnibase_core.models.discovery is resolved,
# this union should be expanded to include:
#   ModelToolInvocationEvent,
#   ModelToolResponseEvent,
#   ModelNodeHealthEvent,
#   ModelNodeShutdownEvent,
#   ModelNodeIntrospectionEvent,
#   ModelIntrospectionResponseEvent,
#   ModelRequestIntrospectionEvent,
#   ModelToolDiscoveryRequest,
#   ModelToolDiscoveryResponse,
#
# Usage:
#     from omnibase_core.models.events.payloads import ModelEventPayloadUnion
#
#     def process_event(payload: ModelEventPayloadUnion) -> None:
#         if isinstance(payload, ModelNodeRegisteredEvent):
#             handle_registration(payload)
#         elif isinstance(payload, ModelWiringResultEvent):
#             handle_wiring(payload)
#         # ... etc
#
ModelEventPayloadUnion = ModelRuntimeEventPayloadUnion
