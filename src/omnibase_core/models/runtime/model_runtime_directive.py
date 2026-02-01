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
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_directive_type import EnumDirectiveType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.payloads import ModelDirectivePayload

__all__ = ["ModelRuntimeDirective"]


class ModelRuntimeDirective(BaseModel):
    """
    Internal-only runtime directive.

    NEVER published to event bus.
    NEVER returned from handlers.
    Produced by runtime after interpreting intents or events.

    The payload field is a typed discriminated union that ensures type safety.
    The directive_type must match the payload.kind field (validated automatically).

    Thread Safety:
        This model is frozen (immutable) after creation.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_directive_type import EnumDirectiveType
        >>> from omnibase_core.models.runtime.payloads import ModelScheduleEffectPayload
        >>>
        >>> directive = ModelRuntimeDirective(
        ...     directive_type=EnumDirectiveType.SCHEDULE_EFFECT,
        ...     correlation_id=uuid4(),
        ...     payload=ModelScheduleEffectPayload(effect_node_type="http_request"),
        ... )
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
    payload: ModelDirectivePayload = Field(
        ..., description="Typed directive-specific payload (discriminated by 'kind')"
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

    @model_validator(mode="after")
    def _validate_payload_matches_type(self) -> Self:
        """
        Validate that payload.kind matches directive_type.

        This ensures type consistency between the directive type enum
        and the actual payload provided, preventing mismatched directives.

        Raises:
            ModelOnexError: If payload.kind doesn't match directive_type.value
        """
        expected_kind = self.directive_type.value
        if self.payload.kind != expected_kind:
            raise ModelOnexError(
                message=(
                    f"Payload kind '{self.payload.kind}' doesn't match "
                    f"directive_type '{expected_kind}'"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                payload_kind=self.payload.kind,
                expected_kind=expected_kind,
            )
        return self
