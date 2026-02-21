# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ProjectionIntent Model.

Represents the intent to project a specific event to a specific projection view.
This is the foundational routing type for the generic projection effect pattern.

Architecture:
    ModelProjectionIntent bridges the gap between event production and projection
    materialization. It carries the event envelope and identifies the target
    projector, allowing a single generic NodeProjectionEffect (in omnibase_spi)
    to dispatch to the correct ProtocolProjector implementation.

    The flow is:
        Event arrives
            → Reducer emits ModelProjectionIntent(s)
            → NodeProjectionEffect receives intent
            → NodeProjectionEffect resolves projector_key → ProtocolProjector
            → ProtocolProjector.project(envelope) → ModelProjectionResult

Intent vs. Event:
    - **ModelEventEnvelope**: The original event from the bus (immutable fact).
    - **ModelProjectionIntent**: The routing decision declaring which projector
      should handle this event. A single event may produce multiple intents if
      multiple projectors subscribe to it.

Design Constraints:
    - ``projector_key`` must be non-empty (identifies the target projector in the
      projector registry).
    - ``event_type`` must be non-empty (documents which event triggered the intent,
      used for logging and observability).
    - ``envelope`` carries the full event so the projector has all context it needs.
      Typed as ``BaseModel`` for flexibility; concrete consumers cast it to the
      appropriate ModelEventEnvelope subtype.
    - ``correlation_id`` is required for distributed tracing (copied from the
      originating envelope).

Thread Safety:
    ModelProjectionIntent is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access. Note: this guarantees that the
    intent's field *references* cannot be reassigned, but does not enforce
    immutability on the envelope itself. If the envelope is a mutable BaseModel
    (frozen=False), callers are responsible for not mutating it after the intent
    is constructed; ModelProjectionIntent cannot enforce envelope immutability.

Example:
    >>> from uuid import uuid4
    >>> from pydantic import BaseModel
    >>> from omnibase_core.models.projectors import ModelProjectionIntent
    >>>
    >>> # Simulate an event envelope (concrete type is ModelEventEnvelope in practice)
    >>> class NodeCreatedEnvelope(BaseModel):
    ...     envelope_id: str
    ...     node_id: str
    ...
    >>> envelope = NodeCreatedEnvelope(envelope_id="env-1", node_id="node-abc")
    >>>
    >>> intent = ModelProjectionIntent(
    ...     projector_key="node_state_projector",
    ...     event_type="node.created.v1",
    ...     envelope=envelope,
    ...     correlation_id=uuid4(),
    ... )
    >>> intent.projector_key
    'node_state_projector'
    >>> intent.event_type
    'node.created.v1'

See Also:
    - NodeProjectionEffect (omnibase_spi) — executes projection effects triggered by this intent
    - ProtocolProjector (omnibase_spi) — projection implementation contract fulfilled by concrete projectors
    - omnibase_core.models.projectors.ModelProjectionResult: Projection outcome
    - omnibase_core.models.projectors.ModelProjectorContract: Declarative projector spec
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH

__all__ = ["ModelProjectionIntent"]


class ModelProjectionIntent(BaseModel):
    """
    Intent to project an event to a specific projection view.

    Carries the routing information and event payload needed by
    NodeProjectionEffect to dispatch to the correct ProtocolProjector.

    A single incoming event may result in multiple ModelProjectionIntents if
    more than one projector is subscribed to that event type. Each intent is
    independent and targets exactly one projector.

    Attributes:
        projector_key: Registry lookup key for the target projector. Must match a
            registered ProtocolProjector in the projector registry. Examples:
            "node_state_projector", "workflow_summary_projector".
        event_type: The event type name that triggered this intent. Used for
            logging, observability, and idempotency key construction. Must
            follow the event naming convention (e.g., "node.created.v1").
        envelope: The full event envelope to project. Typed as BaseModel for
            flexibility; concrete ProtocolProjector implementations cast this
            to the appropriate envelope type for their domain.
        correlation_id: Correlation ID for distributed tracing. Must be copied
            from the originating event envelope, not generated fresh. Links
            this intent to the full causal chain.

    Example:
        >>> from uuid import uuid4
        >>> from pydantic import BaseModel
        >>> from omnibase_core.models.projectors import ModelProjectionIntent
        >>>
        >>> class NodeCreatedEnvelope(BaseModel):
        ...     envelope_id: str
        ...     node_id: str
        ...
        >>> envelope = NodeCreatedEnvelope(envelope_id="env-1", node_id="node-abc")
        >>> intent = ModelProjectionIntent(
        ...     projector_key="node_state_projector",
        ...     event_type="node.created.v1",
        ...     envelope=envelope,
        ...     correlation_id=uuid4(),
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    projector_key: str = Field(
        ...,
        description=(
            "Registry lookup key for the target projector. Must match a registered "
            "ProtocolProjector in the projector registry."
        ),
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    event_type: str = Field(
        ...,
        description=(
            "The event type name that triggered this intent. Used for logging, "
            "observability, and idempotency key construction."
        ),
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    envelope: BaseModel = Field(
        ...,
        description=(
            "The full event envelope to project. Typed as BaseModel for flexibility; "
            "concrete ProtocolProjector implementations cast this to the appropriate "
            "envelope type for their domain. "
            "Note: the envelope must be frozen (frozen=True) for hash-based operations "
            "(set membership, dict keys) to work correctly. "
            "Thread-safety caveat: ModelProjectionIntent.frozen=True prevents field "
            "reassignment but does not freeze the envelope object itself. Mutable "
            "envelopes must not be mutated externally after intent construction."
        ),
    )

    correlation_id: UUID = Field(
        ...,
        description=(
            "Correlation ID for distributed tracing. Must be copied from the "
            "originating event envelope, not generated fresh."
        ),
    )

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (
            f"ModelProjectionIntent("
            f"projector_key={self.projector_key!r}, "
            f"event_type={self.event_type!r}, "
            f"correlation_id={self.correlation_id})"
        )
