"""
ModelPayloadFSMStateAction - Typed payload for FSM state action execution intents.

This module provides the ModelPayloadFSMStateAction model for FSM state
entry/exit action execution from Reducers. The Effect node receives
the intent and invokes the registered action handler.

Design Pattern:
    Reducers emit this payload when a state entry or exit action should
    be executed. This separation ensures Reducer purity - the Reducer
    declares the desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadFSMStateAction
    >>>
    >>> payload = ModelPayloadFSMStateAction(
    ...     state_name="authenticated",
    ...     action_type="on_enter",
    ...     action_name="log_user_session",
    ...     parameters={"user_id": "user-123", "ip": "192.168.1.1"},
    ...     fsm_id=uuid4(),
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
__all__ = ["ModelPayloadFSMStateAction"]


class ModelPayloadFSMStateAction(ModelIntentPayloadBase):
    """Payload for FSM state action execution intents.

    Emitted by Reducers when a state entry or exit action should be executed.
    The Effect node executes this intent by invoking the registered action
    handler for the specified state.

    Supports on_enter and on_exit action types with arbitrary parameters.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "fsm_state_action".
            Placed first for optimal union type resolution performance.
        state_name: Name of the FSM state triggering the action.
        action_type: Type of state action (on_enter or on_exit).
        action_name: Name of the action to execute (maps to handler function).
        parameters: Optional parameters to pass to the action handler.
        fsm_id: Optional FSM instance identifier for multi-instance scenarios.
        correlation_id: Optional correlation ID for distributed tracing.

    Example:
        >>> payload = ModelPayloadFSMStateAction(
        ...     state_name="authenticated",
        ...     action_type="on_enter",
        ...     action_name="log_user_session",
        ...     parameters={"user_id": "user-123", "ip": "192.168.1.1"},
        ...     fsm_id=uuid4(),
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["fsm_state_action"] = Field(
        default="fsm_state_action",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    state_name: str = Field(
        ...,
        description=(
            "Name of the FSM state triggering the action. Must match a valid "
            "state in the FSM definition."
        ),
        min_length=1,
        max_length=128,
    )

    action_type: Literal["on_enter", "on_exit"] = Field(
        ...,
        description=(
            "Type of state action. on_enter is triggered when entering the state, "
            "on_exit is triggered when leaving the state."
        ),
    )

    action_name: str = Field(
        ...,
        description=(
            "Name of the action to execute. Maps to a registered action handler "
            "function in the Effect node."
        ),
        min_length=1,
        max_length=128,
    )

    parameters: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Optional parameters to pass to the action handler. Keys are parameter "
            "names, values are the arguments."
        ),
    )

    fsm_id: UUID | None = Field(
        default=None,
        description=(
            "Optional FSM instance identifier. Required for multi-instance FSM "
            "scenarios to route the action to the correct instance."
        ),
    )

    correlation_id: UUID | None = Field(
        default=None,
        description=(
            "Correlation ID from FSMSubcontract for distributed tracing. "
            "Enables end-to-end tracking of FSM operations across Effect nodes."
        ),
    )
