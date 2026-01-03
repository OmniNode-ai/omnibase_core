"""
ModelPayloadPersistResult - Typed payload for computation result persistence intents.

This module provides the ModelPayloadPersistResult model for computation
result persistence from Reducers. The Effect node receives the intent
and stores the result to the configured persistence backend.

Design Pattern:
    Reducers emit this payload when a computation result should be persisted.
    This separation ensures Reducer purity - the Reducer declares the
    desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadPersistResult
    >>>
    >>> payload = ModelPayloadPersistResult(
    ...     result_key="compute:transform:batch-001",
    ...     result_data={"records": 1000, "status": "success"},
    ...     ttl_seconds=7200,  # 2 hours cache
    ...     metadata={"compute_ms": 1250, "node_id": "compute-a1b2"},
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
    omnibase_core.utils.util_fsm_executor: FSM executor using these payloads
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadPersistResult"]


class ModelPayloadPersistResult(ModelIntentPayloadBase):
    """Payload for computation result persistence intents.

    Emitted by Reducers when a computation result should be persisted. The Effect
    node executes this intent by storing the result to the configured persistence
    backend for caching, auditing, or downstream consumption.

    Supports TTL for cache expiration and metadata for result classification.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "persist_result".
            Placed first for optimal union type resolution performance.
        result_key: Unique identifier for the result. Should include
            computation context for namespacing.
        result_data: The actual result data to persist. Must be JSON-serializable.
        ttl_seconds: Optional time-to-live in seconds for cache expiration.
        metadata: Optional metadata about the result (e.g., computation time, version).

    Example:
        >>> payload = ModelPayloadPersistResult(
        ...     result_key="compute:transform:batch-001",
        ...     result_data={"records": 1000, "status": "success"},
        ...     ttl_seconds=7200,  # 2 hours cache
        ...     metadata={"compute_ms": 1250, "node_id": "compute-a1b2"},
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["persist_result"] = Field(
        default="persist_result",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    result_key: str = Field(
        ...,
        description=(
            "Unique identifier for the result. Should include computation type, "
            "entity, and context. Example: 'compute:transform:batch-001'."
        ),
        min_length=1,
        max_length=512,
    )

    result_data: dict[str, object] = Field(
        ...,
        description=(
            "The actual result data to persist. Must be JSON-serializable. "
            "Contains the computation output to be stored."
        ),
    )

    ttl_seconds: int | None = Field(
        default=None,
        description=(
            "Optional time-to-live in seconds for cache expiration. "
            "If not provided, the result persists indefinitely."
        ),
        ge=0,
    )

    metadata: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Optional metadata about the result. Common keys: 'compute_ms' for "
            "computation time, 'node_id' for origin, 'version' for result version."
        ),
    )
