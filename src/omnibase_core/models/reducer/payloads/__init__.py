# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Typed intent payloads for ONEX Reducer/Effect pattern.

Typed payload models for ModelIntent, replacing the generic
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

from __future__ import annotations

# Base class
# Event payloads
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    from omnibase_core.models.reducer.payloads.model_payload_http import (
        ModelPayloadHTTP,
    )

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

    # Projection payloads
    from omnibase_core.models.reducer.payloads.model_payload_projection_intent import (
        ModelPayloadProjectionIntent,
    )
    from omnibase_core.models.reducer.payloads.model_payload_write import (
        ModelPayloadWrite,
    )

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
    # Projection payloads
    "ModelPayloadProjectionIntent",
    # Extension payloads
    "ModelPayloadExtension",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelPayloadEmitEvent": (
        "omnibase_core.models.reducer.payloads.model_event_payloads",
        "ModelPayloadEmitEvent",
    ),
    "ModelPayloadExtension": (
        "omnibase_core.models.reducer.payloads.model_extension_payloads",
        "ModelPayloadExtension",
    ),
    "ModelIntentPayloadBase": (
        "omnibase_core.models.reducer.payloads.model_intent_payload_base",
        "ModelIntentPayloadBase",
    ),
    "ModelPayloadNotify": (
        "omnibase_core.models.reducer.payloads.model_notification_payloads",
        "ModelPayloadNotify",
    ),
    "ModelPayloadFSMCompleted": (
        "omnibase_core.models.reducer.payloads.model_payload_fsm_completed",
        "ModelPayloadFSMCompleted",
    ),
    "ModelPayloadFSMStateAction": (
        "omnibase_core.models.reducer.payloads.model_payload_fsm_state_action",
        "ModelPayloadFSMStateAction",
    ),
    "ModelPayloadFSMTransitionAction": (
        "omnibase_core.models.reducer.payloads.model_payload_fsm_transition_action",
        "ModelPayloadFSMTransitionAction",
    ),
    "ModelPayloadHTTP": (
        "omnibase_core.models.reducer.payloads.model_payload_http",
        "ModelPayloadHTTP",
    ),
    "ModelPayloadLogEvent": (
        "omnibase_core.models.reducer.payloads.model_payload_log_event",
        "ModelPayloadLogEvent",
    ),
    "ModelPayloadMetric": (
        "omnibase_core.models.reducer.payloads.model_payload_metric",
        "ModelPayloadMetric",
    ),
    "ModelPayloadPersistResult": (
        "omnibase_core.models.reducer.payloads.model_payload_persist_result",
        "ModelPayloadPersistResult",
    ),
    "ModelPayloadPersistState": (
        "omnibase_core.models.reducer.payloads.model_payload_persist_state",
        "ModelPayloadPersistState",
    ),
    "ModelPayloadProjectionIntent": (
        "omnibase_core.models.reducer.payloads.model_payload_projection_intent",
        "ModelPayloadProjectionIntent",
    ),
    "ModelPayloadWrite": (
        "omnibase_core.models.reducer.payloads.model_payload_write",
        "ModelPayloadWrite",
    ),
    "IntentPayloadList": (
        "omnibase_core.models.reducer.payloads.model_protocol_intent_payload",
        "IntentPayloadList",
    ),
    "ProtocolIntentPayload": (
        "omnibase_core.models.reducer.payloads.model_protocol_intent_payload",
        "ProtocolIntentPayload",
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
