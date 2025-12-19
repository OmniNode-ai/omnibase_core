"""
Runtime directive model (INTERNAL-ONLY).

This model represents internal runtime control signals that are:
- NEVER published to event bus
- NEVER returned from handlers
- NOT part of ModelHandlerOutput

Produced by runtime after interpreting intents or events.
Used for execution mechanics (scheduling, retries, delays).
"""

from datetime import UTC, datetime
from enum import StrEnum, unique
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


@unique
class EnumDirectiveType(StrEnum):
    """Runtime directive types (internal-only)."""

    SCHEDULE_EFFECT = "schedule_effect"
    ENQUEUE_HANDLER = "enqueue_handler"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    DELAY_UNTIL = "delay_until"
    CANCEL_EXECUTION = "cancel_execution"


class ModelRuntimeDirective(BaseModel):
    """
    Internal-only runtime directive.

    NEVER published to event bus.
    NEVER returned from handlers.
    Produced by runtime after interpreting intents or events.

    Thread Safety:
        This model is frozen (immutable) after creation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    directive_id: UUID = Field(
        default_factory=uuid4, description="Unique directive identifier"
    )
    directive_type: EnumDirectiveType = Field(
        ..., description="Type of runtime directive"
    )
    target_handler_id: str | None = Field(
        default=None, description="Target handler for execution"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Directive-specific payload"
    )
    delay_ms: int | None = Field(
        default=None, ge=0, description="Delay before execution in ms"
    )
    max_retries: int | None = Field(
        default=None, ge=0, description="Maximum retry attempts"
    )
    correlation_id: UUID = Field(
        ..., description="Trace back to originating intent/event"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this directive was created (UTC)",
    )
