# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelPayloadProjectionIntent - Typed payload for projection intent emission from reducers.

This module provides the ModelPayloadProjectionIntent model, which wraps a
ModelProjectionIntent and allows the reducer to declare "this event should be
projected via this projector" as a first-class effect in its output.

Architecture:
    Reducers maintain purity by emitting intents rather than calling projectors
    directly. ModelPayloadProjectionIntent is the intent payload that carries a
    ModelProjectionIntent to the NodeProjectionEffect (in omnibase_spi), which
    executes the projection as a blocking effect.

    The flow is:
        Reducer processes trigger
            → emits ModelIntent(payload=ModelPayloadProjectionIntent(intent=...))
            → NodeProjectionEffect consumes the intent
            → NodeProjectionEffect calls ProtocolProjector.project(envelope)
            → Projection is persisted before pipeline advances

Design Pattern:
    This payload follows the same pattern as other typed payloads
    (ModelPayloadPersistState, ModelPayloadLogEvent, etc.):
    - intent_type: Literal discriminator for routing
    - Carries domain-specific data needed by the Effect node
    - Immutable (frozen=True)

Blocking Semantics:
    Unlike fire-and-forget side effects, the runtime contract requires that
    projection effects are resolved before the reducer pipeline advances.
    This ordering guarantee is enforced by the Effect executor, not the payload.
    The payload simply declares what should happen.

Thread Safety:
    ModelPayloadProjectionIntent is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from uuid import uuid4
    >>> from pydantic import BaseModel
    >>> from omnibase_core.models.projectors import ModelProjectionIntent
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadProjectionIntent
    >>>
    >>> class NodeCreatedEnvelope(BaseModel):
    ...     envelope_id: str
    ...     node_id: str
    ...
    >>> envelope = NodeCreatedEnvelope(envelope_id="env-1", node_id="node-abc")
    >>> projection_intent = ModelProjectionIntent(
    ...     projector_key="node_state_projector",
    ...     event_type="node.created.v1",
    ...     envelope=envelope,
    ...     correlation_id=uuid4(),
    ... )
    >>> payload = ModelPayloadProjectionIntent(intent=projection_intent)
    >>> payload.intent_type
    'projection_intent'

See Also:
    omnibase_core.models.projectors.ModelProjectionIntent: The wrapped projection routing model
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class for payloads
    omnibase_core.nodes.node_reducer: Emits this payload during reduction
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.projectors.model_projection_intent import (
    ModelProjectionIntent,
)
from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadProjectionIntent"]


class ModelPayloadProjectionIntent(ModelIntentPayloadBase):
    """Payload for projection intent emission from reducers.

    Wraps a ModelProjectionIntent and enables the reducer to declare
    a projection as a first-class effect in its intents list. The
    Effect node (NodeProjectionEffect in omnibase_spi) consumes this
    payload and executes the projection synchronously before the
    reducer pipeline advances.

    This payload enables the reducer to remain a pure function: instead
    of calling a projector directly (a side effect), it emits a
    ModelPayloadProjectionIntent that declares what projection should occur.
    The Effect layer is responsible for executing the projection.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always
            "projection_intent". Placed first for optimal union type
            resolution performance.
        intent: The ModelProjectionIntent carrying projector routing
            information (projector_key, event_type, envelope, correlation_id).

    Blocking Contract:
        The runtime contract (enforced by the Effect executor, not this payload)
        requires that projection effects complete before the reducer pipeline
        advances. This ensures projection ordering guarantees and eliminates
        the read-your-writes race condition.

    Example:
        >>> from uuid import uuid4
        >>> from pydantic import BaseModel
        >>> from omnibase_core.models.projectors import ModelProjectionIntent
        >>> from omnibase_core.models.reducer.payloads import ModelPayloadProjectionIntent
        >>>
        >>> class NodeCreatedEnvelope(BaseModel):
        ...     envelope_id: str
        ...     node_id: str
        ...
        >>> envelope = NodeCreatedEnvelope(envelope_id="env-1", node_id="node-abc")
        >>> projection_intent = ModelProjectionIntent(
        ...     projector_key="node_state_projector",
        ...     event_type="node.created.v1",
        ...     envelope=envelope,
        ...     correlation_id=uuid4(),
        ... )
        >>> payload = ModelPayloadProjectionIntent(intent=projection_intent)
        >>> assert payload.intent_type == "projection_intent"
        >>> assert payload.intent.projector_key == "node_state_projector"
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["projection_intent"] = Field(
        default="projection_intent",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler. "
            "Always 'projection_intent' for this payload type."
        ),
    )

    intent: ModelProjectionIntent = Field(
        ...,
        description=(
            "The projection intent carrying routing information: projector_key "
            "(identifies target projector in registry), event_type (event that "
            "triggered the projection), envelope (full event payload), and "
            "correlation_id (for distributed tracing)."
        ),
    )
