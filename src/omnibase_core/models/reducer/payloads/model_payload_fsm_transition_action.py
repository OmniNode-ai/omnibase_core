"""
ModelPayloadFSMTransitionAction - Typed payload for FSM transition action execution intents.

This module provides the ModelPayloadFSMTransitionAction model for FSM
transition action execution from Reducers. The Effect node receives
the intent and invokes the registered transition action handler.

Design Pattern:
    Reducers emit this payload when a transition action should be executed.
    This separation ensures Reducer purity - the Reducer declares the
    desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadFSMTransitionAction
    >>>
    >>> payload = ModelPayloadFSMTransitionAction(
    ...     from_state="cart",
    ...     to_state="checkout",
    ...     trigger="proceed_to_checkout",
    ...     action_name="calculate_totals",
    ...     parameters={"apply_discount": True},
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
__all__ = ["ModelPayloadFSMTransitionAction"]


class ModelPayloadFSMTransitionAction(ModelIntentPayloadBase):
    """Payload for FSM transition action execution intents.

    Emitted by Reducers when a transition action should be executed.
    The Effect node executes this intent by invoking the registered action
    handler for the specified transition.

    Transitions can have guard conditions and side effects that are executed
    by the Effect layer.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "fsm_transition_action".
            Placed first for optimal union type resolution performance.
        from_state: Source state of the transition.
        to_state: Target state of the transition.
        trigger: Event/trigger that caused the transition.
        action_name: Name of the action to execute (maps to handler function).
        parameters: Optional parameters to pass to the action handler.
        fsm_id: Optional FSM instance identifier for multi-instance scenarios.
        correlation_id: Optional correlation ID for distributed tracing across Effect nodes.

    Example:
        >>> payload = ModelPayloadFSMTransitionAction(
        ...     from_state="cart",
        ...     to_state="checkout",
        ...     trigger="proceed_to_checkout",
        ...     action_name="calculate_totals",
        ...     parameters={"apply_discount": True},
        ...     fsm_id=uuid4(),
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["fsm_transition_action"] = Field(
        default="fsm_transition_action",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    from_state: str = Field(
        ...,
        description=(
            "Source state of the transition. Must match a valid state in the "
            "FSM definition."
        ),
        min_length=1,
        max_length=128,
    )

    to_state: str = Field(
        ...,
        description=(
            "Target state of the transition. Must match a valid state in the "
            "FSM definition."
        ),
        min_length=1,
        max_length=128,
    )

    trigger: str = Field(
        ...,
        description=(
            "Event or trigger that caused the transition. Maps to an event type "
            "defined in the FSM schema."
        ),
        min_length=1,
        max_length=128,
    )

    action_name: str = Field(
        ...,
        description=(
            "Name of the action to execute. Maps to a registered transition action "
            "handler function in the Effect node."
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
