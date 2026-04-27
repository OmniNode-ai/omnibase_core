# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""LifecycleChain — ordered sequence of dispatch lifecycle events for a single
correlation_id, with FSM transition rules (OMN-9885 / Wave 4 of
runtime-lifecycle-hardening plan)."""

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from omnibase_core.enums.enum_dispatch_lifecycle_state import (
    EnumDispatchLifecycleState,
)
from omnibase_core.errors.error_lifecycle_transition import (
    LifecycleTransitionError,
)
from omnibase_core.models.dispatch.model_dispatch_lifecycle_event import (
    ModelDispatchLifecycleEvent,
)

HEARTBEAT_REQUIRED_ENV_VAR = "LIFECYCLE_HEARTBEAT_REQUIRED_SECONDS"
DEFAULT_HEARTBEAT_REQUIRED_SECONDS = 60


def _heartbeat_required_seconds() -> int:
    raw = os.environ.get(HEARTBEAT_REQUIRED_ENV_VAR)
    if raw is None:
        return DEFAULT_HEARTBEAT_REQUIRED_SECONDS
    try:
        value = int(raw)
    except ValueError as exc:
        # error-ok: env-var parse boundary; ValueError is the contract for callers.
        raise ValueError(
            f"{HEARTBEAT_REQUIRED_ENV_VAR}={raw!r} is not an integer"
        ) from exc
    if value < 1:
        # error-ok: env-var validation boundary.
        raise ValueError(f"{HEARTBEAT_REQUIRED_ENV_VAR} must be >= 1, got {value}")
    return value


class LifecycleChain(BaseModel):
    """Ordered sequence of lifecycle events for a single correlation_id.

    Mutable on purpose: callers append events via `transition_to` so the FSM
    rules (terminal_failure-before-dlq, retry budget gate, terminal-state
    closure) can be enforced as the chain grows.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    events: list[ModelDispatchLifecycleEvent] = Field(default_factory=list)
    duration_seconds_override: int | None = Field(
        default=None,
        description="Test/inspection hook: when set, overrides the wall-clock "
        "duration computed from emitted_at deltas.",
    )

    def __init__(self, **data: Any) -> None:
        try:
            super().__init__(**data)
        except ValidationError as exc:
            for err in exc.errors():
                ctx = err.get("ctx") or {}
                inner = ctx.get("error")
                if isinstance(inner, LifecycleTransitionError):
                    raise inner
            raise

    @model_validator(mode="after")
    def _validate_initial_chain(self) -> "LifecycleChain":
        if not self.events:
            return self
        if self.events[0].state is not EnumDispatchLifecycleState.ACCEPTED:
            raise LifecycleTransitionError(
                "lifecycle chain must start with state 'accepted', "
                f"got {self.events[0].state.value!r}"
            )
        first_corr = self.events[0].correlation_id
        for event in self.events[1:]:
            if event.correlation_id != first_corr:
                raise LifecycleTransitionError(
                    f"correlation_id mismatch in chain: expected {first_corr!r}, "
                    f"got {event.correlation_id!r}"
                )
        return self

    @property
    def terminal(self) -> EnumDispatchLifecycleState | None:
        if not self.events:
            return None
        last = self.events[-1].state
        return last if last.is_terminal() else None

    @property
    def observed_duration_seconds(self) -> float:
        if self.duration_seconds_override is not None:
            return float(self.duration_seconds_override)
        if len(self.events) < 2:
            return 0.0
        delta = self.events[-1].emitted_at - self.events[0].emitted_at
        return delta.total_seconds()

    @property
    def heartbeat_required(self) -> bool:
        return self.observed_duration_seconds > _heartbeat_required_seconds()

    def transition_to(
        self,
        event: ModelDispatchLifecycleEvent,
        retry_budget_remaining: int,
    ) -> None:
        if self.terminal is not None:
            raise LifecycleTransitionError(
                f"chain already terminal in state {self.terminal.value!r}; "
                "no further transitions allowed"
            )
        if self.events and event.correlation_id != self.events[0].correlation_id:
            raise LifecycleTransitionError(
                f"correlation_id mismatch: chain={self.events[0].correlation_id!r}, "
                f"event={event.correlation_id!r}"
            )
        if event.state is EnumDispatchLifecycleState.DLQ:
            prior_states = [e.state for e in self.events]
            if EnumDispatchLifecycleState.TERMINAL_FAILURE not in prior_states:
                raise LifecycleTransitionError(
                    "dlq requires a prior terminal_failure event"
                )
            if retry_budget_remaining > 0:
                raise LifecycleTransitionError(
                    f"dlq requires exhausted retry budget; "
                    f"remaining={retry_budget_remaining}"
                )
        self.events.append(event)


__all__ = [
    "DEFAULT_HEARTBEAT_REQUIRED_SECONDS",
    "HEARTBEAT_REQUIRED_ENV_VAR",
    "LifecycleChain",
]
