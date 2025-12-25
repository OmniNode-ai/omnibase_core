"""
Discriminated union type for typed intent payloads.

This module provides ModelIntentPayloadUnion, a discriminated union type that
encompasses all typed intent payloads. The union uses `intent_type` as the
discriminator field for efficient type resolution.

Design Pattern:
    The discriminated union pattern provides:
    - Compile-time type safety via Annotated[Union[...], Field(discriminator="intent_type")]
    - Exhaustive handling enforcement (add new payload -> update all handlers)
    - Efficient runtime dispatch using Pydantic's discriminator optimization
    - Clear separation of concerns (Reducer declares intent, Effect executes)

Usage:
    Use ModelIntentPayloadUnion for:
    - Reducer return types: `list[ModelIntent]` with typed payload
    - Effect dispatch signatures: `def execute(intent: ModelIntent[ModelIntentPayloadUnion])`
    - Pattern matching in Effects using `match payload`

Adding New Payloads:
    1. Create new payload model in appropriate category file
    2. Define `intent_type: Literal["your.intent"] = "your.intent"`
    3. Add import to this file
    4. Add to ModelIntentPayloadUnion
    5. Update all Effect dispatch handlers for exhaustive matching

Performance Note:
    The discriminator field (`intent_type`) is placed FIRST in all payload models
    for optimal union type resolution. Pydantic checks fields in order when
    resolving discriminated unions, so having the discriminator first speeds up
    type matching.

Example - Reducer emitting intents:
    >>> from omnibase_core.models.reducer import ModelIntent
    >>> from omnibase_core.models.reducer.payloads import PayloadLogEvent
    >>>
    >>> def reduce(state, action):
    ...     intent = ModelIntent(
    ...         intent_type="log_event",
    ...         target="logging",
    ...         payload=PayloadLogEvent(
    ...             level="INFO",
    ...             message="Processing completed",
    ...         ).model_dump(),
    ...     )
    ...     return (state, [intent])

Example - Effect pattern matching:
    >>> from omnibase_core.models.reducer.payloads import ModelIntentPayloadUnion
    >>>
    >>> def execute(payload: ModelIntentPayloadUnion) -> None:
    ...     match payload:
    ...         case PayloadLogEvent():
    ...             logger.log(payload.level, payload.message)
    ...         case PayloadMetric():
    ...             metrics.record(payload.name, payload.value)
    ...         case PayloadPersistState():
    ...             storage.save(payload.state_key, payload.state_data)

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.model_intent: Extension intent model
    omnibase_core.nodes.NodeReducer: Reducer node implementation
    omnibase_core.nodes.NodeEffect: Effect node implementation
"""

from typing import Annotated

from pydantic import Field

# Event payloads
from omnibase_core.models.reducer.payloads.model_event_payloads import PayloadEmitEvent

# Extension payloads
from omnibase_core.models.reducer.payloads.model_extension_payloads import (
    PayloadExtension,
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

# ==============================================================================
# Discriminated Union Type
# ==============================================================================

ModelIntentPayloadUnion = Annotated[
    # Logging category
    PayloadLogEvent
    | PayloadMetric
    # Persistence category
    | PayloadPersistState
    | PayloadPersistResult
    # FSM category
    | PayloadFSMStateAction
    | PayloadFSMTransitionAction
    | PayloadFSMCompleted
    # Event category
    | PayloadEmitEvent
    # I/O category
    | PayloadWrite
    | PayloadHTTP
    # Notification category
    | PayloadNotify
    # Extension category (catch-all for plugins)
    | PayloadExtension,
    Field(discriminator="intent_type"),
]
"""Discriminated union of all typed intent payloads.

Use this type for:
- Type hints on payload fields
- Effect dispatch signatures
- Pattern matching in Effects

The union is ordered by category:
1. Logging (log_event, record_metric)
2. Persistence (persist_state, persist_result)
3. FSM (fsm_state_action, fsm_transition_action, fsm_completed)
4. Events (emit_event)
5. I/O (write, http_request)
6. Notifications (notify)
7. Extensions (extension) - catch-all for plugins

Intent Type Reference:
    - log_event: PayloadLogEvent
    - record_metric: PayloadMetric
    - persist_state: PayloadPersistState
    - persist_result: PayloadPersistResult
    - fsm_state_action: PayloadFSMStateAction
    - fsm_transition_action: PayloadFSMTransitionAction
    - fsm_completed: PayloadFSMCompleted
    - emit_event: PayloadEmitEvent
    - write: PayloadWrite
    - http_request: PayloadHTTP
    - notify: PayloadNotify
    - extension: PayloadExtension

Adding a new payload requires:
1. Create new model file: model_payload_<name>.py
2. Add to this union
3. Update all Effect dispatch handlers (exhaustive matching)
"""


# ==============================================================================
# Type Aliases for Common Use Cases
# ==============================================================================

# List type for reducer output
IntentPayloadList = list[ModelIntentPayloadUnion]
"""Type alias for lists of intent payloads in reducer outputs."""


__all__ = [
    # Union type
    "ModelIntentPayloadUnion",
    # Type aliases
    "IntentPayloadList",
    # Re-export all payload types for convenience
    "PayloadLogEvent",
    "PayloadMetric",
    "PayloadPersistState",
    "PayloadPersistResult",
    "PayloadFSMStateAction",
    "PayloadFSMTransitionAction",
    "PayloadFSMCompleted",
    "PayloadEmitEvent",
    "PayloadWrite",
    "PayloadHTTP",
    "PayloadNotify",
    "PayloadExtension",
]
