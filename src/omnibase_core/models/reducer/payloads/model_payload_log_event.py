"""
ModelPayloadLogEvent - Typed payload for log event emission intents.

This module provides the ModelPayloadLogEvent model for structured log event
emission from Reducers. The Effect node receives the intent and sends
the log to the configured logging backend.

Design Pattern:
    Reducers emit this payload when a log event should be recorded.
    This separation ensures Reducer purity - the Reducer declares the
    desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent
    >>>
    >>> payload = ModelPayloadLogEvent(
    ...     level="INFO",
    ...     message="User authentication successful",
    ...     context={"user_id": "abc123", "auth_method": "oauth2"},
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadLogEvent"]


class ModelPayloadLogEvent(ModelIntentPayloadBase):
    """Payload for log event emission intents.

    Emitted by Reducers when a log event should be recorded. The Effect node
    executes this intent by sending the log to the configured logging backend.

    Supports structured logging with severity levels, messages, and arbitrary
    context data for rich debugging and observability.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "log_event".
            Placed first for optimal union type resolution performance.
        level: Log severity level. Standard levels: DEBUG, INFO, WARNING, ERROR.
        message: Human-readable log message describing the event.
        context: Additional structured context data for the log entry.
            Uses dict[str, object] for type-safe flexible metadata.

    Example:
        >>> payload = ModelPayloadLogEvent(
        ...     level="INFO",
        ...     message="User authentication successful",
        ...     context={"user_id": "abc123", "auth_method": "oauth2"},
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["log_event"] = Field(
        default="log_event",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        ...,
        description=(
            "Log severity level. DEBUG for detailed diagnostics, INFO for normal "
            "operations, WARNING for potential issues, ERROR for failures."
        ),
    )

    message: str = Field(
        ...,
        description="Human-readable log message describing the event.",
        min_length=1,
        max_length=4096,
    )

    context: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Additional structured context data for the log entry. Keys should be "
            "descriptive identifiers, values can be any JSON-serializable type."
        ),
    )
