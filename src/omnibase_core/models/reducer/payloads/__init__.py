"""
Typed intent payloads for ONEX Reducer/Effect pattern.

This module provides typed payload models for ModelIntent, replacing the generic
`dict[str, Any]` payload field with Protocol-based types for type safety.

Intent Payload Architecture:
    The ONEX intent system uses typed payloads for compile-time type safety:

    1. Protocol-Based Payloads (ProtocolIntentPayload):
       - Open extensibility: Plugins can define their own payloads
       - Duck typing: Any conforming class works as a payload
       - Structural typing for pattern matching in Effects

    2. Extension Payloads (ModelPayloadExtension):
       - Flexible structure for plugins and experiments
       - Uses `extension_type` for sub-classification
       - Runtime validation

Payload Categories:
    - Logging: ModelPayloadLogEvent, ModelPayloadMetric
    - Persistence: ModelPayloadPersistState, ModelPayloadPersistResult
    - FSM: ModelPayloadFSMStateAction, ModelPayloadFSMTransitionAction, ModelPayloadFSMCompleted
    - Events: ModelPayloadEmitEvent
    - I/O: ModelPayloadWrite, ModelPayloadHTTP
    - Notifications: ModelPayloadNotify
    - Extensions: ModelPayloadExtension

Usage:
    >>> from omnibase_core.models.reducer.payloads import (
    ...     ModelPayloadLogEvent,
    ...     ModelPayloadMetric,
    ...     ProtocolIntentPayload,
    ... )
    >>>
    >>> # Create a typed payload
    >>> payload = ModelPayloadLogEvent(
    ...     level="INFO",
    ...     message="Operation completed",
    ...     context={"duration_ms": 125},
    ... )
    >>>
    >>> # Use in pattern matching
    >>> def handle_payload(payload: ProtocolIntentPayload) -> None:
    ...     match payload:
    ...         case ModelPayloadLogEvent():
    ...             print(f"Log: {payload.message}")
    ...         case ModelPayloadMetric():
    ...             print(f"Metric: {payload.name}={payload.value}")

See Also:
    omnibase_core.models.reducer.model_intent: ModelIntent with payload field
    omnibase_core.models.intents: Core infrastructure intents
    omnibase_core.nodes.NodeReducer: Reducer node implementation
    omnibase_core.nodes.NodeEffect: Effect node implementation
"""

# Base class
# Event payloads
from omnibase_core.models.reducer.payloads.model_event_payloads import (
    ModelPayloadEmitEvent,
)

# Extension payloads
from omnibase_core.models.reducer.payloads.model_extension_payloads import (
    ModelPayloadExtension,
)
from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Notification payloads
from omnibase_core.models.reducer.payloads.model_notification_payloads import (
    ModelPayloadNotify,
)

# FSM payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_fsm_completed import (
    ModelPayloadFSMCompleted,
)
from omnibase_core.models.reducer.payloads.model_payload_fsm_state_action import (
    ModelPayloadFSMStateAction,
)
from omnibase_core.models.reducer.payloads.model_payload_fsm_transition_action import (
    ModelPayloadFSMTransitionAction,
)

# I/O payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_http import ModelPayloadHTTP

# Logging payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_log_event import (
    ModelPayloadLogEvent,
)
from omnibase_core.models.reducer.payloads.model_payload_metric import (
    ModelPayloadMetric,
)

# Persistence payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_persist_result import (
    ModelPayloadPersistResult,
)
from omnibase_core.models.reducer.payloads.model_payload_persist_state import (
    ModelPayloadPersistState,
)
from omnibase_core.models.reducer.payloads.model_payload_write import ModelPayloadWrite

# Protocol for structural typing
from omnibase_core.models.reducer.payloads.model_protocol_intent_payload import (
    IntentPayloadList,
    ProtocolIntentPayload,
)

# Public API - listed immediately after imports per Python convention
__all__ = [
    # Protocol for structural typing
    "ProtocolIntentPayload",
    "IntentPayloadList",
    # Base class
    "ModelIntentPayloadBase",
    # Logging payloads
    "ModelPayloadLogEvent",
    "ModelPayloadMetric",
    # Persistence payloads
    "ModelPayloadPersistState",
    "ModelPayloadPersistResult",
    # FSM payloads
    "ModelPayloadFSMStateAction",
    "ModelPayloadFSMTransitionAction",
    "ModelPayloadFSMCompleted",
    # Event payloads
    "ModelPayloadEmitEvent",
    # I/O payloads
    "ModelPayloadWrite",
    "ModelPayloadHTTP",
    # Notification payloads
    "ModelPayloadNotify",
    # Extension payloads
    "ModelPayloadExtension",
]
