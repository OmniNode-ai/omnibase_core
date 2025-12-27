# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Runtime directive model (INTERNAL-ONLY).

This model represents internal runtime control signals that are:
- NEVER published to event bus
- NEVER returned from handlers
- NOT part of ModelHandlerOutput

Produced by runtime after interpreting intents or events.
Used for execution mechanics (scheduling, retries, delays).

Payload Types:
    The payload field accepts three types (in order of preference):
    1. ModelRuntimeDirectivePayload: Typed payload with structured fields for
       all directive types (SCHEDULE_EFFECT, ENQUEUE_HANDLER, RETRY_WITH_BACKOFF,
       DELAY_UNTIL, CANCEL_EXECUTION).
    2. TContext (Generic): Custom typed payloads via Generic[TContext] for
       specialized use cases not covered by ModelRuntimeDirectivePayload.
    3. dict[str, Any]: Backwards compatible untyped payloads.

Generic Parameters:
    TContext: Optional custom payload type. When not parameterized, only
        ModelRuntimeDirectivePayload and dict[str, Any] are available.
"""

from datetime import UTC, datetime
from typing import Any, Generic
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_directive_type import EnumDirectiveType
from omnibase_core.models.context import ModelRuntimeDirectivePayload
from omnibase_core.models.services.model_error_details import TContext
from omnibase_core.utils.util_decorators import allow_dict_str_any

__all__ = ["ModelRuntimeDirective"]


@allow_dict_str_any(
    "Directive payload supports ModelRuntimeDirectivePayload (preferred typed option), "
    "custom TContext types via Generic[TContext], and dict[str, Any] for backwards "
    "compatibility. ModelRuntimeDirectivePayload covers all standard directive types; "
    "TContext provides flexibility for specialized use cases."
)
class ModelRuntimeDirective(BaseModel, Generic[TContext]):
    """
    Internal-only runtime directive.

    NEVER published to event bus.
    NEVER returned from handlers.
    Produced by runtime after interpreting intents or events.

    Payload Types:
        The payload field accepts three types (in order of preference):

        1. ModelRuntimeDirectivePayload (preferred): Typed payload with structured
           fields for all standard directive types.
        2. TContext (via Generic): Custom typed payloads for specialized use cases.
        3. dict[str, Any]: Backwards compatible untyped payloads.

    Generic Parameters:
        TContext: Optional custom payload type for specialized use cases not
            covered by ModelRuntimeDirectivePayload.

    Thread Safety:
        This model is frozen (immutable) after creation.

    Example:
        Using ModelRuntimeDirectivePayload (preferred)::

            from omnibase_core.models.context import ModelRuntimeDirectivePayload

            directive = ModelRuntimeDirective(
                directive_type=EnumDirectiveType.RETRY_WITH_BACKOFF,
                correlation_id=uuid4(),
                payload=ModelRuntimeDirectivePayload(
                    backoff_base_ms=1000,
                    backoff_multiplier=2.0,
                    jitter_ms=100,
                ),
            )

        Using dict (backwards compatible)::

            directive = ModelRuntimeDirective(
                directive_type=EnumDirectiveType.SCHEDULE_EFFECT,
                correlation_id=uuid4(),
                payload={"handler_args": {"key": "value"}},
            )

        With custom typed payload (specialized)::

            from pydantic import BaseModel, ConfigDict

            class CustomPayload(BaseModel):
                model_config = ConfigDict(frozen=True)
                custom_field: str

            directive = ModelRuntimeDirective[CustomPayload](
                directive_type=EnumDirectiveType.SCHEDULE_EFFECT,
                correlation_id=uuid4(),
                payload=CustomPayload(custom_field="value"),
            )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    directive_id: UUID = Field(
        default_factory=uuid4, description="Unique directive identifier"
    )
    directive_type: EnumDirectiveType = Field(
        ..., description="Type of runtime directive"
    )
    target_handler_id: str | None = Field(
        default=None, description="Target handler for execution"
    )
    payload: ModelRuntimeDirectivePayload | TContext | dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Directive-specific payload. Accepts ModelRuntimeDirectivePayload (preferred "
            "typed option with structured fields for all directive types), custom TContext "
            "types via Generic[TContext], or dict[str, Any] for flexible payloads."
        ),
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
