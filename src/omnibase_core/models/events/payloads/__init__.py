# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Typed event payload models for ONEX coordination I/O.

Typed payload models for use with ModelEventPublishIntent
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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelDiscoveryEventPayloadUnion": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelDiscoveryEventPayloadUnion",
    ),
    "ModelEventPayloadUnion": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelEventPayloadUnion",
    ),
    "ModelIntrospectionResponseEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelIntrospectionResponseEvent",
    ),
    "ModelNodeGraphReadyEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelNodeGraphReadyEvent",
    ),
    "ModelNodeHealthEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelNodeHealthEvent",
    ),
    "ModelNodeIntrospectionEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelNodeIntrospectionEvent",
    ),
    "ModelNodeRegisteredEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelNodeRegisteredEvent",
    ),
    "ModelNodeShutdownEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelNodeShutdownEvent",
    ),
    "ModelNodeUnregisteredEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelNodeUnregisteredEvent",
    ),
    "ModelRequestIntrospectionEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelRequestIntrospectionEvent",
    ),
    "ModelRuntimeEventPayloadUnion": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelRuntimeEventPayloadUnion",
    ),
    "ModelRuntimeReadyEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelRuntimeReadyEvent",
    ),
    "ModelSubscriptionCreatedEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelSubscriptionCreatedEvent",
    ),
    "ModelSubscriptionFailedEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelSubscriptionFailedEvent",
    ),
    "ModelSubscriptionRemovedEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelSubscriptionRemovedEvent",
    ),
    "ModelToolDiscoveryRequest": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelToolDiscoveryRequest",
    ),
    "ModelToolDiscoveryResponse": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelToolDiscoveryResponse",
    ),
    "ModelToolInvocationEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelToolInvocationEvent",
    ),
    "ModelToolResponseEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelToolResponseEvent",
    ),
    "ModelWiringErrorEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelWiringErrorEvent",
    ),
    "ModelWiringResultEvent": (
        "omnibase_core.models.events.payloads.model_event_payload_union",
        "ModelWiringResultEvent",
    ),
    "convert_dict_to_typed_payload": (
        "omnibase_core.utils.util_payload_migration",
        "convert_dict_to_typed_payload",
    ),
    "get_migration_example": (
        "omnibase_core.utils.util_payload_migration",
        "get_migration_example",
    ),
    "get_supported_event_types": (
        "omnibase_core.utils.util_payload_migration",
        "get_supported_event_types",
    ),
    "infer_payload_type_from_dict": (
        "omnibase_core.utils.util_payload_migration",
        "infer_payload_type_from_dict",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
