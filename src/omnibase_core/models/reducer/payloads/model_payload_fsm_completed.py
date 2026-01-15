"""
ModelPayloadFSMCompleted - Typed payload for FSM completion notification intents.

This module provides the ModelPayloadFSMCompleted model for FSM completion
notification from Reducers. The Effect node receives the intent and
performs cleanup operations and notifies downstream systems.

Design Pattern:
    Reducers emit this payload when an FSM has reached a terminal state.
    This separation ensures Reducer purity - the Reducer declares the
    desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from uuid import UUID
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadFSMCompleted
    >>>
    >>> payload = ModelPayloadFSMCompleted(
    ...     fsm_id=UUID("12345678-1234-5678-1234-567812345678"),
    ...     final_state="completed",
    ...     completion_status="success",
    ...     result_data={"order_total": 99.99, "items_count": 3},
    ...     metadata={"duration_ms": 1500, "transitions": 5},
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
__all__ = ["ModelPayloadFSMCompleted"]


class ModelPayloadFSMCompleted(ModelIntentPayloadBase):
    """Payload for FSM completion notification intents.

    Emitted by Reducers when an FSM has reached a terminal state and should
    be marked as completed. The Effect node executes this intent by performing
    cleanup operations and notifying downstream systems.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "fsm_completed".
            Placed first for optimal union type resolution performance.
        fsm_id: FSM instance identifier that has completed.
        final_state: The terminal state the FSM ended in.
        completion_status: Outcome of the FSM execution (success, failure, cancelled).
        result_data: Optional result data from the FSM execution.
        metadata: Optional metadata about the completion (timing, metrics, etc.).

    Example:
        >>> payload = ModelPayloadFSMCompleted(
        ...     fsm_id=UUID("12345678-1234-5678-1234-567812345678"),
        ...     final_state="completed",
        ...     completion_status="success",
        ...     result_data={"order_total": 99.99, "items_count": 3},
        ...     metadata={"duration_ms": 1500, "transitions": 5},
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["fsm_completed"] = Field(
        default="fsm_completed",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    fsm_id: UUID = Field(
        ...,
        description="FSM instance identifier that has completed.",
    )

    final_state: str = Field(
        ...,
        description=(
            "The terminal state the FSM ended in. Should be a valid terminal "
            "state defined in the FSM schema."
        ),
        min_length=1,
        max_length=128,
    )

    completion_status: Literal["success", "failure", "cancelled", "timeout"] = Field(
        ...,
        description=(
            "Outcome of the FSM execution. success for normal completion, "
            "failure for errors, cancelled for manual cancellation, timeout for "
            "deadline exceeded."
        ),
    )

    result_data: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Optional result data from the FSM execution. Contains any output "
            "or computed values from the workflow."
        ),
    )

    metadata: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Optional metadata about the completion. Common keys: 'duration_ms', "
            "'transitions', 'start_time', 'end_time'."
        ),
    )
