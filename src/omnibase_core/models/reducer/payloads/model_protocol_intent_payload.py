"""
Protocol for intent payloads.

This module defines the ProtocolIntentPayload which all intent payloads must
implement. Using a Protocol (structural typing) instead of a discriminated union
provides open extensibility - any class implementing the protocol can be used
as a payload without modifying a central union type.

Design Pattern:
    Protocol-based payloads enable:
    - Open extensibility: Plugins can define their own payloads
    - Duck typing: Any conforming class works as a payload
    - Decoupling: No central union to modify when adding payloads
    - Structural pattern matching still works via isinstance checks

Architecture:
    Reducer function: delta(state, action) -> (new_state, intents[])

    1. Reducer emits typed intents with Protocol-conforming payloads
    2. Effect receives intents and validates payload via Protocol
    3. Effect executes side effect based on payload data
    4. intent_type enables routing to appropriate handlers

Thread Safety:
    All conforming payloads should be immutable (frozen=True) after creation.

Example:
    >>> from omnibase_core.models.reducer.payloads import ProtocolIntentPayload
    >>> from pydantic import BaseModel, ConfigDict
    >>> from typing import Literal
    >>>
    >>> class ModelPayloadCustom(BaseModel):
    ...     model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    ...     intent_type: Literal["custom.action"] = "custom.action"
    ...     data: str
    ...
    ...     def get_intent_type(self) -> str:
    ...         return self.intent_type
    >>>
    >>> # MyPayload conforms to ProtocolIntentPayload via structural typing
    >>> payload: ProtocolIntentPayload = ModelPayloadCustom(data="test")

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class for core payloads
    omnibase_core.models.reducer.model_intent: Intent model using this protocol
"""

from typing import Protocol, runtime_checkable

# Public API - listed immediately after imports per Python convention
__all__ = [
    "ProtocolIntentPayload",
    "IntentPayloadList",
]


@runtime_checkable
class ProtocolIntentPayload(Protocol):
    """Protocol for intent payloads.

    All intent payloads must implement this protocol to be usable with ModelIntent.
    The protocol uses structural typing - any class with matching attributes and
    methods satisfies the protocol without explicit inheritance.

    Required Attributes:
        intent_type: String identifier for routing to the appropriate Effect handler.
            Should be a Literal type for type safety (e.g., Literal["log_event"]).

    Conformance Requirements:
        - Must have an `intent_type` attribute (read-only string)
        - Should be immutable (frozen=True) for thread safety
        - Should use extra="forbid" for strict schema validation
        - Should use from_attributes=True for pytest-xdist compatibility

    Example:
        >>> from pydantic import BaseModel, ConfigDict
        >>> from typing import Literal
        >>>
        >>> class ModelPayloadMyIntent(BaseModel):
        ...     model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
        ...     intent_type: Literal["my.intent"] = "my.intent"
        ...     data: str
        >>>
        >>> # Automatically satisfies ProtocolIntentPayload
        >>> payload: ProtocolIntentPayload = ModelPayloadMyIntent(data="test")

    Note:
        The @runtime_checkable decorator enables isinstance() checks:
        >>> isinstance(payload, ProtocolIntentPayload)  # True
    """

    @property
    def intent_type(self) -> str:
        """Intent type identifier for routing.

        Used by Effect nodes to dispatch to the appropriate handler.
        Should return a dot-separated namespace (e.g., "log_event", "persist_state").

        Returns:
            str: The intent type identifier.
        """
        ...


# Type alias for list of payloads
IntentPayloadList = list[ProtocolIntentPayload]
"""Type alias for lists of intent payloads in reducer outputs."""
