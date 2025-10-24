"""
ModelIntent - Side effect declaration for pure FSM pattern.

Intents represent side effects that the Reducer wants to occur,
emitted to the Effect node for execution. This maintains the
Reducer's purity while allowing side effects to be described.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
