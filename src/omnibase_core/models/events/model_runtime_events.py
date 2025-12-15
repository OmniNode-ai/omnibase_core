"""
Runtime event models for coordination I/O (re-exports).

This module provides a unified import location for runtime event models.
The actual implementations are in separate files per ONEX single-class rule.

These models are referenced in contracts/runtime/event_bus_wiring_effect.yaml
and support the runtime self-hosting architecture.

See:
    - model_runtime_event_base.py: ModelRuntimeEventBase
    - model_node_registered_event.py: ModelNodeRegisteredEvent
    - model_node_unregistered_event.py: ModelNodeUnregisteredEvent
    - model_subscription_created_event.py: ModelSubscriptionCreatedEvent
    - model_subscription_removed_event.py: ModelSubscriptionRemovedEvent
    - model_subscription_failed_event.py: ModelSubscriptionFailedEvent
    - model_runtime_ready_event.py: ModelRuntimeReadyEvent
    - model_wiring_error_event.py: ModelWiringErrorEvent
    - model_node_graph_ready_event.py: ModelNodeGraphReadyEvent
    - model_wiring_result_event.py: ModelWiringResultEvent
    - model_node_graph_info.py: ModelNodeGraphInfo
    - model_wiring_error_info.py: ModelWiringErrorInfo
"""

from omnibase_core.models.events.model_node_graph_info import (
    ModelNodeGraphInfo,
)
from omnibase_core.models.events.model_node_graph_ready_event import (
    NODE_GRAPH_READY_EVENT,
    ModelNodeGraphReadyEvent,
)
from omnibase_core.models.events.model_node_registered_event import (
    NODE_REGISTERED_EVENT,
    ModelNodeRegisteredEvent,
)
from omnibase_core.models.events.model_node_unregistered_event import (
    NODE_UNREGISTERED_EVENT,
    ModelNodeUnregisteredEvent,
)
from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)
from omnibase_core.models.events.model_runtime_ready_event import (
    RUNTIME_READY_EVENT,
    ModelRuntimeReadyEvent,
)
from omnibase_core.models.events.model_subscription_created_event import (
    SUBSCRIPTION_CREATED_EVENT,
    ModelSubscriptionCreatedEvent,
)
from omnibase_core.models.events.model_subscription_failed_event import (
    SUBSCRIPTION_FAILED_EVENT,
    ModelSubscriptionFailedEvent,
)
from omnibase_core.models.events.model_subscription_removed_event import (
    SUBSCRIPTION_REMOVED_EVENT,
    ModelSubscriptionRemovedEvent,
)
from omnibase_core.models.events.model_wiring_error_event import (
    WIRING_ERROR_EVENT,
    ModelWiringErrorEvent,
)
from omnibase_core.models.events.model_wiring_error_info import (
    ModelWiringErrorInfo,
)
from omnibase_core.models.events.model_wiring_result_event import (
    WIRING_RESULT_EVENT,
    ModelWiringResultEvent,
)

__all__ = [
    # Event type constants
    "NODE_GRAPH_READY_EVENT",
    "NODE_REGISTERED_EVENT",
    "NODE_UNREGISTERED_EVENT",
    "RUNTIME_READY_EVENT",
    "SUBSCRIPTION_CREATED_EVENT",
    "SUBSCRIPTION_FAILED_EVENT",
    "SUBSCRIPTION_REMOVED_EVENT",
    "WIRING_ERROR_EVENT",
    "WIRING_RESULT_EVENT",
    # Event models
    "ModelNodeGraphReadyEvent",
    "ModelNodeRegisteredEvent",
    "ModelNodeUnregisteredEvent",
    "ModelRuntimeEventBase",
    "ModelRuntimeReadyEvent",
    "ModelSubscriptionCreatedEvent",
    "ModelSubscriptionFailedEvent",
    "ModelSubscriptionRemovedEvent",
    "ModelWiringErrorEvent",
    "ModelWiringResultEvent",
    # Supporting models
    "ModelNodeGraphInfo",
    "ModelWiringErrorInfo",
]
