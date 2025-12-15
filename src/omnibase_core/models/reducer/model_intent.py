"""
Intent model for pure FSM pattern side effect declarations.

This module provides the ModelIntent class that represents side effects
the Reducer wants to occur. Instead of performing side effects directly,
the Reducer emits Intents describing what should happen. The Effect node
consumes and executes these Intents.

Design Pattern:
    The Intent pattern maintains Reducer purity by separating the decision
    of "what side effect should occur" from the execution of that side effect.
    This follows the functional programming principle of keeping the core
    business logic pure and pushing I/O to the edges.

    Reducer function: delta(state, action) -> (new_state, intents[])

Thread Safety:
    ModelIntent is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.
    Note that this provides shallow immutability - while the model's fields cannot
    be reassigned, mutable field values (like dict/list contents) can still be
    modified. For full thread safety with mutable nested data, use
    model_copy(deep=True) to create independent copies.

Key Features:
    - Type-safe intent declaration with payload
    - Priority ordering for intent execution
    - Optional lease integration for single-writer semantics
    - Epoch support for versioned state coordination

Intent Types (Common Examples):
    - "log": Emit log message or metrics
    - "emit_event": Publish event to message bus
    - "write": Persist data to storage
    - "notify": Send notification to external system
    - "http_request": Make outbound HTTP call

Example:
    >>> from omnibase_core.models.reducer import ModelIntent
    >>>
    >>> # Intent to emit an event
    >>> intent = ModelIntent(
    ...     intent_type="emit_event",
    ...     target="user.created",
    ...     payload={"user_id": "123", "email": "user@example.com"},
    ...     priority=5,
    ... )
    >>>
    >>> # Intent with lease for distributed coordination
    >>> lease_intent = ModelIntent(
    ...     intent_type="write",
    ...     target="users/123/profile",
    ...     payload={"name": "Alice"},
    ...     lease_id=current_lease_id,
    ...     epoch=current_epoch,
    ... )

See Also:
    - omnibase_core.models.reducer.model_intent_publish_result: Publication result
    - omnibase_core.nodes.node_reducer: Emits intents during reduction
    - omnibase_core.nodes.node_effect: Executes intents
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Intent payloads require flexible dict[str, Any] to carry arbitrary data "
    "for side effects (event data, log metadata, storage payloads, etc.)."
)
class ModelIntent(BaseModel):
    """
    Intent declaration for side effects from pure Reducer FSM.

    The Reducer is a pure function: δ(state, action) → (new_state, intents[])
    Instead of performing side effects directly, it emits Intents describing
    what side effects should occur. The Effect node consumes these Intents
    and executes them.

    Examples:
        - Intent to log metrics
        - Intent to emit event
        - Intent to write to storage
        - Intent to notify external system
    """

    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this intent",
    )

    intent_type: str = Field(
        ...,
        description="Type of intent (log, emit_event, write, notify)",
        min_length=1,
        max_length=100,
    )

    target: str = Field(
        ...,
        description="Target for the intent execution (service, channel, topic)",
        min_length=1,
        max_length=200,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Intent payload data",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    # Lease fields for single-writer semantics
    lease_id: UUID | None = Field(
        default=None,
        description="Optional lease ID if this intent relates to a leased workflow",
    )

    epoch: int | None = Field(
        default=None,
        description="Optional epoch if this intent relates to versioned state",
        ge=0,
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )
