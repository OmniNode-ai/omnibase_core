"""
Typed intent payloads for ONEX Reducer/Effect pattern.

This module provides typed payload models for ModelIntent, replacing the generic
`dict[str, Any]` payload field with discriminated union types for type safety.

Intent Payload Architecture:
    The ONEX intent system uses typed payloads for compile-time type safety:

    1. Core Typed Payloads (this module):
       - Discriminated union pattern via `intent_type` field
       - Closed set of known payload types
       - Exhaustive pattern matching in Effects
       - Compile-time type safety

    2. Extension Payloads (PayloadExtension):
       - Flexible structure for plugins and experiments
       - Uses `extension_type` for sub-classification
       - Runtime validation

Payload Categories:
    - Logging: PayloadLogEvent, PayloadMetric
    - Persistence: PayloadPersistState, PayloadPersistResult
    - FSM: PayloadFSMStateAction, PayloadFSMTransitionAction, PayloadFSMCompleted
    - Events: PayloadEmitEvent
    - I/O: PayloadWrite, PayloadHTTP
    - Notifications: PayloadNotify
    - Extensions: PayloadExtension

Usage:
    >>> from omnibase_core.models.reducer.payloads import (
    ...     PayloadLogEvent,
    ...     PayloadMetric,
    ...     ModelIntentPayloadUnion,
    ... )
    >>>
    >>> # Create a typed payload
    >>> payload = PayloadLogEvent(
    ...     level="INFO",
    ...     message="Operation completed",
    ...     context={"duration_ms": 125},
    ... )
    >>>
    >>> # Use in pattern matching
    >>> def handle_payload(payload: ModelIntentPayloadUnion) -> None:
    ...     match payload:
    ...         case PayloadLogEvent():
    ...             print(f"Log: {payload.message}")
    ...         case PayloadMetric():
    ...             print(f"Metric: {payload.name}={payload.value}")

See Also:
    omnibase_core.models.reducer.model_intent: ModelIntent with payload field
    omnibase_core.models.intents: Core infrastructure intents
    omnibase_core.nodes.NodeReducer: Reducer node implementation
    omnibase_core.nodes.NodeEffect: Effect node implementation
"""

# Base class
# Event payloads
from omnibase_core.models.reducer.payloads.model_event_payloads import PayloadEmitEvent

# Extension payloads
from omnibase_core.models.reducer.payloads.model_extension_payloads import (
    PayloadExtension,
)
from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Discriminated union
from omnibase_core.models.reducer.payloads.model_intent_payload_union import (
    IntentPayloadList,
    ModelIntentPayloadUnion,
)

# Notification payloads
from omnibase_core.models.reducer.payloads.model_notification_payloads import (
    PayloadNotify,
)

# FSM payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_fsm_completed import (
    PayloadFSMCompleted,
)
from omnibase_core.models.reducer.payloads.model_payload_fsm_state_action import (
    PayloadFSMStateAction,
)
from omnibase_core.models.reducer.payloads.model_payload_fsm_transition_action import (
    PayloadFSMTransitionAction,
)

# I/O payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_http import PayloadHTTP

# Logging payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_log_event import (
    PayloadLogEvent,
)
from omnibase_core.models.reducer.payloads.model_payload_metric import PayloadMetric

# Persistence payloads (split files)
from omnibase_core.models.reducer.payloads.model_payload_persist_result import (
    PayloadPersistResult,
)
from omnibase_core.models.reducer.payloads.model_payload_persist_state import (
    PayloadPersistState,
)
from omnibase_core.models.reducer.payloads.model_payload_write import PayloadWrite

__all__ = [
    # Base class
    "ModelIntentPayloadBase",
    # Logging payloads
    "PayloadLogEvent",
    "PayloadMetric",
    # Persistence payloads
    "PayloadPersistState",
    "PayloadPersistResult",
    # FSM payloads
    "PayloadFSMStateAction",
    "PayloadFSMTransitionAction",
    "PayloadFSMCompleted",
    # Event payloads
    "PayloadEmitEvent",
    # I/O payloads
    "PayloadWrite",
    "PayloadHTTP",
    # Notification payloads
    "PayloadNotify",
    # Extension payloads
    "PayloadExtension",
    # Discriminated union
    "ModelIntentPayloadUnion",
    "IntentPayloadList",
]
