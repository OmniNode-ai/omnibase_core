"""
Base class for all typed intent payloads.

This module provides the ModelIntentPayloadBase class that all typed intent
payloads inherit from. Intent payloads use a discriminated union pattern for
type-safe, exhaustive handling via the `intent_type` discriminator field.

Design Pattern:
    Intent payloads represent the structured data for side effects that Reducers
    emit via ModelIntent. Each payload type has its own schema with an `intent_type`
    discriminator field, enabling structural pattern matching in Effect nodes.

    The discriminated union pattern provides:
    - Compile-time type safety via Annotated[Union[...], Field(discriminator="intent_type")]
    - Exhaustive handling enforcement (add new payload -> update all handlers)
    - Clear separation of concerns (Reducer declares intent, Effect executes)

Architecture:
    Reducer function: delta(state, action) -> (new_state, intents[])

    1. Reducer emits typed intents with typed payloads (does NOT perform side effects)
    2. Effect receives intents and pattern-matches on payload type
    3. Effect executes side effect based on payload data
    4. correlation_id links intent to originating request for tracing

Thread Safety:
    ModelIntentPayloadBase is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access. Note that this provides shallow
    immutability - nested mutable objects should be avoided.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelIntentPayloadBase
    >>> from typing import Literal
    >>>
    >>> class PayloadCustom(ModelIntentPayloadBase):
    ...     intent_type: Literal["custom.action"] = "custom.action"
    ...     data: str

See Also:
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
    omnibase_core.models.reducer.model_intent: Extension intent model
    omnibase_core.nodes.NodeReducer: Reducer node implementation
    omnibase_core.nodes.NodeEffect: Effect node implementation
"""

from pydantic import BaseModel, ConfigDict


class ModelIntentPayloadBase(BaseModel):
    """Base class for all typed intent payloads.

    All intent payloads share this base configuration for immutability
    and strict validation. Subclasses define the specific payload schema
    and an `intent_type` discriminator field for the discriminated union pattern.

    Intent payloads are a CLOSED SET within each category. Each payload has its
    own schema. Dispatch is structural (pattern matching on type), not string-based.

    Subclassing Requirements:
        1. Define `intent_type: Literal["your.intent"] = "your.intent"` as discriminator
        2. Ensure payload implements ProtocolIntentPayload (see model_protocol_intent_payload.py)
        3. Update all Effect dispatch handlers for exhaustive matching

    Configuration:
        - frozen=True: Payloads are immutable after creation
        - extra="forbid": No extra fields allowed (strict schema)
        - validate_assignment=True: Validates on any assignment
        - from_attributes=True: Supports ORM-style attribute access

    Example:
        >>> from typing import Literal
        >>>
        >>> class PayloadMyIntent(ModelIntentPayloadBase):
        ...     intent_type: Literal["my.intent"] = "my.intent"
        ...     data: str
        >>>
        >>> payload = PayloadMyIntent(data="example")
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )
