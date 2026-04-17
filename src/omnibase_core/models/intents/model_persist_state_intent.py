# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent to persist node state via the effect pipeline.

Design Pattern:
    Reducers emit ModelPersistStateIntent when accumulated state should be
    durably persisted. The downstream effect node (node_state_persist_effect)
    receives this intent, calls ProtocolStateStore.put(envelope), and emits
    ModelStatePersistedEvent confirming successful persistence.

    This separation ensures Reducer purity — the Reducer declares the desired
    outcome (persist this state envelope) without performing any I/O.

Reducer → Effect Flow:
    1. Reducer emits ModelPersistStateIntent with a fully-populated envelope.
    2. The intent travels through the internal intent topic
       ``onex.int.state-persist.v1``.
    3. node_state_persist_effect receives it, writes to the state store, and
       emits ``ModelStatePersistedEvent`` on ``onex.evt.state.persisted.v1``.

Fields:
    intent_id: Unique ID for this specific persist request. Distinct from
        correlation_id so that multiple intents sharing the same correlation
        chain can be individually identified.
    envelope: The state snapshot to persist. Contains node_id, scope_id,
        data payload, written_at timestamp, and contract fingerprint.
    emitted_at: Explicit injection timestamp (timezone-aware). Never
        use ``datetime.utcnow()`` — always pass ``datetime.now(timezone.utc)``.
    correlation_id: Inherited from ModelCoreIntent. Links this intent to the
        originating request across service boundaries.

Example:
    >>> from datetime import datetime, timezone
    >>> from uuid import uuid4
    >>> from omnibase_core.models.intents import ModelPersistStateIntent
    >>> from omnibase_core.models.state import ModelStateEnvelope
    >>>
    >>> envelope = ModelStateEnvelope(
    ...     node_id="node-handler-ledger",
    ...     scope_id="default",
    ...     data={"last_sweep": "2026-04-16T00:00:00Z"},
    ...     written_at=datetime.now(timezone.utc),
    ... )
    >>> intent = ModelPersistStateIntent(
    ...     intent_id=uuid4(),
    ...     envelope=envelope,
    ...     emitted_at=datetime.now(timezone.utc),
    ...     correlation_id=uuid4(),
    ... )

See Also:
    omnibase_core.models.intents.ModelCoreIntent: Base class
    omnibase_core.models.state.ModelStateEnvelope: State payload wrapper
    omnibase_core.protocols.storage.ProtocolStateStore: Persistence protocol
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from omnibase_core.models.intents.model_core_intent_base import ModelCoreIntent
from omnibase_core.models.state.model_state_envelope import ModelStateEnvelope


class ModelPersistStateIntent(ModelCoreIntent):
    """Intent to persist a node state envelope via the effect pipeline.

    Emitted by Reducers when a state snapshot should be durably written to
    the state store. The Effect node executes the actual I/O; the Reducer
    remains pure.

    Attributes:
        intent_id: Unique identifier for this persist request. Allows
            individual intents to be correlated even when multiple intents
            share the same ``correlation_id`` chain.
        envelope: The fully-populated state snapshot to persist.
            All fields (node_id, scope_id, data, written_at) must be set
            before emitting this intent — the Effect node writes the envelope
            as-is, without modification.
        emitted_at: Timezone-aware timestamp at which the Reducer emitted
            this intent. Must be explicitly injected — no default value is
            provided to prevent silent clock drift across execution contexts.
        correlation_id: Inherited from ModelCoreIntent. UUID linking this
            intent to the originating request for distributed tracing.

    Example:
        >>> from datetime import datetime, timezone
        >>> from uuid import uuid4
        >>> from omnibase_core.models.intents import ModelPersistStateIntent
        >>> from omnibase_core.models.state import ModelStateEnvelope
        >>>
        >>> intent = ModelPersistStateIntent(
        ...     intent_id=uuid4(),
        ...     envelope=ModelStateEnvelope(
        ...         node_id="my-node",
        ...         data={"k": "v"},
        ...         written_at=datetime.now(timezone.utc),
        ...     ),
        ...     emitted_at=datetime.now(timezone.utc),
        ...     correlation_id=uuid4(),
        ... )
    """

    intent_id: UUID = Field(
        ...,
        description=(
            "Unique identifier for this persist request. Distinct from "
            "correlation_id — allows individual intents within the same "
            "correlation chain to be independently identified and traced."
        ),
    )
    envelope: ModelStateEnvelope = Field(
        ...,
        description=(
            "The state snapshot to persist. The Effect node writes this "
            "envelope directly to ProtocolStateStore without modification."
        ),
    )
    emitted_at: datetime = Field(
        ...,
        description=(
            "Timezone-aware timestamp at which the Reducer emitted this intent. "
            "Explicitly injected — no default. Use datetime.now(timezone.utc)."
        ),
    )
