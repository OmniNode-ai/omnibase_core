"""
ModelPayloadPersistState - Typed payload for state persistence intents.

This module provides the ModelPayloadPersistState model for FSM state
snapshot persistence from Reducers. The Effect node receives the
intent and stores the state to the configured persistence backend.

Design Pattern:
    Reducers emit this payload when FSM state should be persisted.
    This separation ensures Reducer purity - the Reducer declares the
    desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadPersistState
    >>>
    >>> payload = ModelPayloadPersistState(
    ...     state_key="fsm:order:12345:state",
    ...     state_data={"status": "pending", "items": ["a", "b"]},
    ...     ttl_seconds=86400,  # 24 hours
    ...     version=5,
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
    omnibase_core.utils.util_fsm_executor: FSM executor using these payloads
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadPersistState"]


class ModelPayloadPersistState(ModelIntentPayloadBase):
    """Payload for state persistence intents.

    Emitted by Reducers when FSM state should be persisted. The Effect node
    executes this intent by storing the state to the configured persistence
    backend (e.g., Redis, PostgreSQL, filesystem).

    Supports TTL for automatic expiration and versioning for optimistic locking.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "persist_state".
            Placed first for optimal union type resolution performance.
        state_key: Unique identifier for the state snapshot. Should include
            workflow/entity context for namespacing.
        state_data: The actual state data to persist. Must be JSON-serializable.
        ttl_seconds: Optional time-to-live in seconds for automatic expiration.
        version: Optional version for optimistic locking. If provided, the Effect
            should check version before writing to prevent conflicts.

    Example:
        >>> payload = ModelPayloadPersistState(
        ...     state_key="fsm:order:12345:state",
        ...     state_data={"status": "pending", "items": ["a", "b"]},
        ...     ttl_seconds=86400,  # 24 hours
        ...     version=5,
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["persist_state"] = Field(
        default="persist_state",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    state_key: str = Field(
        ...,
        description=(
            "Unique identifier for the state snapshot. Should include workflow, "
            "entity, and context information. Example: 'fsm:order:12345:state'."
        ),
        min_length=1,
        max_length=512,
    )

    state_data: dict[str, object] = Field(
        ...,
        description=(
            "The actual state data to persist. Must be JSON-serializable. "
            "Contains the FSM state snapshot to be stored."
        ),
    )

    ttl_seconds: int | None = Field(
        default=None,
        description=(
            "Optional time-to-live in seconds for automatic expiration. "
            "If not provided, the state persists indefinitely."
        ),
        ge=0,
    )

    version: int | None = Field(
        default=None,
        description=(
            "Optional version for optimistic locking. The Effect should verify "
            "the current version before writing to prevent concurrent update conflicts."
        ),
        ge=0,
    )

    correlation_id: UUID | None = Field(
        default=None,
        description=(
            "Correlation ID from FSMSubcontract for distributed tracing. "
            "Enables end-to-end tracking of state persistence operations."
        ),
    )
