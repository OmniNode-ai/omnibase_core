# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDispatchLifecycleEvent + per-state required-fields validators (OMN-9885 /
Wave 4 of runtime-lifecycle-hardening plan).

Eliminates self-attested dispatch success: dispatchers cannot mark a run as
SUCCESS; only the consumer that actually emitted the terminal event can. The
orchestrator owns TIMEOUT and CANCELLED; a separate DLQ writer owns DLQ — and
DLQ is reachable only after a TERMINAL_FAILURE with the retry budget exhausted.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from omnibase_core.enums.enum_dispatch_lifecycle_emitter import (
    EnumDispatchLifecycleEmitter,
)
from omnibase_core.enums.enum_dispatch_lifecycle_state import (
    EnumDispatchLifecycleState,
)
from omnibase_core.errors.error_lifecycle_emitter import LifecycleEmitterError

_EMITTER_BY_STATE: dict[EnumDispatchLifecycleState, EnumDispatchLifecycleEmitter] = {
    EnumDispatchLifecycleState.ACCEPTED: EnumDispatchLifecycleEmitter.DISPATCHER,
    EnumDispatchLifecycleState.STARTED: EnumDispatchLifecycleEmitter.CONSUMER,
    EnumDispatchLifecycleState.HEARTBEAT: EnumDispatchLifecycleEmitter.CONSUMER,
    EnumDispatchLifecycleState.TERMINAL_SUCCESS: EnumDispatchLifecycleEmitter.CONSUMER,
    EnumDispatchLifecycleState.TERMINAL_FAILURE: EnumDispatchLifecycleEmitter.CONSUMER,
    EnumDispatchLifecycleState.TIMEOUT: EnumDispatchLifecycleEmitter.ORCHESTRATOR,
    EnumDispatchLifecycleState.CANCELLED: EnumDispatchLifecycleEmitter.ORCHESTRATOR,
    EnumDispatchLifecycleState.DLQ: EnumDispatchLifecycleEmitter.DLQ_WRITER,
}

_REQUIRED_FIELDS_BY_STATE: dict[EnumDispatchLifecycleState, tuple[str, ...]] = {
    EnumDispatchLifecycleState.ACCEPTED: (
        "dispatched_at",
        "command_topic",
        "target_node_id",
    ),
    EnumDispatchLifecycleState.STARTED: (
        "started_at",
        "consumer_group",
        "consumer_host",
    ),
    EnumDispatchLifecycleState.HEARTBEAT: ("heartbeat_at", "consumer_host"),
    EnumDispatchLifecycleState.TERMINAL_SUCCESS: (
        "terminated_at",
        "terminal_event_topic",
        "result_payload_hash",
    ),
    EnumDispatchLifecycleState.TERMINAL_FAILURE: (
        "terminated_at",
        "terminal_event_topic",
        "failure_reason",
    ),
    EnumDispatchLifecycleState.TIMEOUT: (
        "timed_out_at",
        "budget_seconds",
        "last_observed_state",
    ),
    EnumDispatchLifecycleState.CANCELLED: (
        "cancelled_at",
        "cancel_reason",
        "cancelled_by",
    ),
    EnumDispatchLifecycleState.DLQ: (
        "dlq_at",
        "dlq_topic",
        "retry_attempts_used",
        "final_failure_reason",
    ),
}


class ModelDispatchLifecycleEvent(BaseModel):
    """Typed lifecycle event for a single dispatched command.

    Every event carries `correlation_id`, `state`, `emitter`, `emitted_at`
    plus the per-state required fields documented in the Task 10 emitter
    responsibility table.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str = Field(
        min_length=1, description="Identifier shared across every event in a chain."
    )
    state: EnumDispatchLifecycleState = Field(
        description="Lifecycle state this event represents."
    )
    emitter: EnumDispatchLifecycleEmitter = Field(
        description="Actor that emitted this event."
    )
    emitted_at: datetime = Field(description="UTC timestamp the event was emitted.")

    # ACCEPTED-state fields
    dispatched_at: datetime | None = None
    command_topic: str | None = None
    target_node_id: str | None = None

    # STARTED-state fields
    started_at: datetime | None = None
    consumer_group: str | None = None
    consumer_host: str | None = None

    # HEARTBEAT-state fields
    heartbeat_at: datetime | None = None
    progress_percent: float | None = Field(default=None, ge=0.0, le=100.0)

    # TERMINAL_SUCCESS / TERMINAL_FAILURE shared fields
    terminated_at: datetime | None = None
    terminal_event_topic: str | None = None
    result_payload_hash: str | None = None
    failure_reason: str | None = None

    # TIMEOUT-state fields
    timed_out_at: datetime | None = None
    budget_seconds: int | None = Field(default=None, ge=1)
    last_observed_state: EnumDispatchLifecycleState | None = None

    # CANCELLED-state fields
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    cancelled_by: str | None = None

    # DLQ-state fields
    dlq_at: datetime | None = None
    dlq_topic: str | None = None
    retry_attempts_used: int | None = Field(default=None, ge=0)
    final_failure_reason: str | None = None

    def __init__(self, **data: Any) -> None:
        try:
            super().__init__(**data)
        except ValidationError as exc:
            for err in exc.errors():
                ctx = err.get("ctx") or {}
                inner = ctx.get("error")
                if isinstance(inner, LifecycleEmitterError):
                    raise inner
            raise

    @model_validator(mode="after")
    def _validate_emitter_owns_state(self) -> "ModelDispatchLifecycleEvent":
        expected = _EMITTER_BY_STATE[self.state]
        if self.emitter is not expected:
            raise LifecycleEmitterError(
                f"state {self.state.value!r} must be emitted by {expected.value!r}, "
                f"got {self.emitter.value!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_required_fields_for_state(self) -> "ModelDispatchLifecycleEvent":
        missing = [
            field
            for field in _REQUIRED_FIELDS_BY_STATE[self.state]
            if getattr(self, field) in (None, "")
        ]
        if missing:
            # error-ok: pydantic model_validator contract requires ValueError.
            raise ValueError(
                f"state {self.state.value!r} missing required fields: {missing}"
            )
        return self


__all__ = ["ModelDispatchLifecycleEvent"]
