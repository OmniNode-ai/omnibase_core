# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDispatchLifecycleEvent state machine (OMN-9885)."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_dispatch_lifecycle_emitter import (
    EnumDispatchLifecycleEmitter,
)
from omnibase_core.enums.enum_dispatch_lifecycle_state import (
    EnumDispatchLifecycleState,
)
from omnibase_core.errors.error_lifecycle_emitter import LifecycleEmitterError
from omnibase_core.errors.error_lifecycle_transition import (
    LifecycleTransitionError,
)
from omnibase_core.models.dispatch.model_dispatch_lifecycle_event import (
    ModelDispatchLifecycleEvent,
)
from omnibase_core.models.dispatch.model_lifecycle_chain import (
    DEFAULT_HEARTBEAT_REQUIRED_SECONDS,
    HEARTBEAT_REQUIRED_ENV_VAR,
    LifecycleChain,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _accepted(correlation_id: str = "corr-1") -> ModelDispatchLifecycleEvent:
    return ModelDispatchLifecycleEvent(
        correlation_id=correlation_id,
        state=EnumDispatchLifecycleState.ACCEPTED,
        emitter=EnumDispatchLifecycleEmitter.DISPATCHER,
        emitted_at=_now(),
        dispatched_at=_now(),
        command_topic="onex.cmd.omnimarket.build-loop-orchestrator-start.v1",
        target_node_id="node_build_loop_orchestrator",
    )


def _started(correlation_id: str = "corr-1") -> ModelDispatchLifecycleEvent:
    return ModelDispatchLifecycleEvent(
        correlation_id=correlation_id,
        state=EnumDispatchLifecycleState.STARTED,
        emitter=EnumDispatchLifecycleEmitter.CONSUMER,
        emitted_at=_now(),
        started_at=_now(),
        consumer_group="onex-build-loop-projection-compute",
        consumer_host="omninode-runtime-effects-1",
    )


def _terminal_failure(correlation_id: str = "corr-1") -> ModelDispatchLifecycleEvent:
    return ModelDispatchLifecycleEvent(
        correlation_id=correlation_id,
        state=EnumDispatchLifecycleState.TERMINAL_FAILURE,
        emitter=EnumDispatchLifecycleEmitter.CONSUMER,
        emitted_at=_now(),
        terminated_at=_now(),
        terminal_event_topic="onex.evt.omnimarket.build-loop-orchestrator-completed.v1",
        failure_reason="handler raised RuntimeError",
    )


def _dlq(correlation_id: str = "corr-1") -> ModelDispatchLifecycleEvent:
    return ModelDispatchLifecycleEvent(
        correlation_id=correlation_id,
        state=EnumDispatchLifecycleState.DLQ,
        emitter=EnumDispatchLifecycleEmitter.DLQ_WRITER,
        emitted_at=_now(),
        dlq_at=_now(),
        dlq_topic="onex.dlq.omnimarket.build-loop.v1",
        retry_attempts_used=3,
        final_failure_reason="exceeded retry budget after handler errors",
    )


# ---------------------------------------------------------------------------
# Plan-mandated test cases (Task 10 acceptance contract)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lifecycle_event_state_enum_exact() -> None:
    """Plan acceptance: enum membership must be exactly the eight states."""
    assert {state.value for state in EnumDispatchLifecycleState} == {
        "accepted",
        "started",
        "heartbeat",
        "terminal_success",
        "terminal_failure",
        "timeout",
        "cancelled",
        "dlq",
    }


@pytest.mark.unit
def test_dlq_only_after_terminal_failure_and_budget_exhausted() -> None:
    """Plan acceptance: dlq requires terminal_failure first AND retry budget == 0."""
    chain = LifecycleChain(events=[_accepted(), _started(), _terminal_failure()])

    with pytest.raises(LifecycleTransitionError, match="retry budget"):
        chain.transition_to(_dlq(), retry_budget_remaining=2)

    chain.transition_to(_dlq(), retry_budget_remaining=0)
    assert chain.terminal == EnumDispatchLifecycleState.DLQ


@pytest.mark.unit
def test_dlq_without_prior_terminal_failure_rejected() -> None:
    chain = LifecycleChain(events=[_accepted(), _started()])
    with pytest.raises(LifecycleTransitionError, match="terminal_failure"):
        chain.transition_to(_dlq(), retry_budget_remaining=0)


@pytest.mark.unit
def test_heartbeat_required_only_above_60s(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan acceptance: heartbeat required iff wall-clock duration > 60s (default)."""
    monkeypatch.delenv(HEARTBEAT_REQUIRED_ENV_VAR, raising=False)

    long_chain = LifecycleChain(
        events=[
            _accepted(),
            _started(),
        ]
    )
    long_chain.duration_seconds_override = 90
    assert long_chain.heartbeat_required is True

    short_chain = LifecycleChain(events=[_accepted(), _started()])
    short_chain.duration_seconds_override = 10
    assert short_chain.heartbeat_required is False


@pytest.mark.unit
def test_heartbeat_threshold_configurable_via_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default threshold of 60s can be overridden by env var."""
    monkeypatch.setenv(HEARTBEAT_REQUIRED_ENV_VAR, "5")

    chain = LifecycleChain(events=[_accepted(), _started()])
    chain.duration_seconds_override = 10
    assert chain.heartbeat_required is True


@pytest.mark.unit
def test_emitter_responsibility_enforced() -> None:
    """Plan acceptance: terminal_success emitted by dispatcher must raise."""
    with pytest.raises(LifecycleEmitterError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.TERMINAL_SUCCESS,
            emitter=EnumDispatchLifecycleEmitter.DISPATCHER,
            emitted_at=_now(),
            terminated_at=_now(),
            terminal_event_topic="onex.evt.foo.v1",
            result_payload_hash="abc123",
        )


# ---------------------------------------------------------------------------
# Per-state required-fields validation (responsibility table from Task 10)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_accepted_requires_dispatched_at_and_command_topic() -> None:
    with pytest.raises(ValidationError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.ACCEPTED,
            emitter=EnumDispatchLifecycleEmitter.DISPATCHER,
            emitted_at=_now(),
            command_topic="onex.cmd.foo.v1",
            target_node_id="node_foo",
        )


@pytest.mark.unit
def test_started_requires_consumer_group_and_host() -> None:
    with pytest.raises(ValidationError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.STARTED,
            emitter=EnumDispatchLifecycleEmitter.CONSUMER,
            emitted_at=_now(),
            started_at=_now(),
        )


@pytest.mark.unit
def test_terminal_success_requires_result_payload_hash() -> None:
    with pytest.raises(ValidationError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.TERMINAL_SUCCESS,
            emitter=EnumDispatchLifecycleEmitter.CONSUMER,
            emitted_at=_now(),
            terminated_at=_now(),
            terminal_event_topic="onex.evt.foo.v1",
        )


@pytest.mark.unit
def test_terminal_failure_requires_failure_reason() -> None:
    with pytest.raises(ValidationError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.TERMINAL_FAILURE,
            emitter=EnumDispatchLifecycleEmitter.CONSUMER,
            emitted_at=_now(),
            terminated_at=_now(),
            terminal_event_topic="onex.evt.foo.v1",
        )


@pytest.mark.unit
def test_timeout_requires_budget_and_last_state() -> None:
    with pytest.raises(ValidationError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.TIMEOUT,
            emitter=EnumDispatchLifecycleEmitter.ORCHESTRATOR,
            emitted_at=_now(),
            timed_out_at=_now(),
        )


@pytest.mark.unit
def test_cancelled_requires_reason_and_actor() -> None:
    with pytest.raises(ValidationError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.CANCELLED,
            emitter=EnumDispatchLifecycleEmitter.ORCHESTRATOR,
            emitted_at=_now(),
            cancelled_at=_now(),
        )


@pytest.mark.unit
def test_dlq_requires_retry_attempts_and_topic() -> None:
    with pytest.raises(ValidationError):
        ModelDispatchLifecycleEvent(
            correlation_id="corr-1",
            state=EnumDispatchLifecycleState.DLQ,
            emitter=EnumDispatchLifecycleEmitter.DLQ_WRITER,
            emitted_at=_now(),
            dlq_at=_now(),
            dlq_topic="onex.dlq.foo.v1",
            final_failure_reason="x",
        )


@pytest.mark.unit
def test_emitter_consumer_for_started_passes() -> None:
    event = _started()
    assert event.state is EnumDispatchLifecycleState.STARTED
    assert event.emitter is EnumDispatchLifecycleEmitter.CONSUMER


# ---------------------------------------------------------------------------
# Chain transition rules
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chain_must_start_with_accepted() -> None:
    with pytest.raises(LifecycleTransitionError, match="must start with"):
        LifecycleChain(events=[_started()])


@pytest.mark.unit
def test_chain_correlation_id_mismatch_rejected() -> None:
    with pytest.raises(LifecycleTransitionError, match="correlation_id"):
        LifecycleChain(events=[_accepted("a"), _started("b")])


@pytest.mark.unit
def test_chain_terminal_state_blocks_further_transitions() -> None:
    chain = LifecycleChain(
        events=[
            _accepted(),
            _started(),
            ModelDispatchLifecycleEvent(
                correlation_id="corr-1",
                state=EnumDispatchLifecycleState.TERMINAL_SUCCESS,
                emitter=EnumDispatchLifecycleEmitter.CONSUMER,
                emitted_at=_now(),
                terminated_at=_now(),
                terminal_event_topic="onex.evt.foo.v1",
                result_payload_hash="hash",
            ),
        ]
    )
    assert chain.terminal == EnumDispatchLifecycleState.TERMINAL_SUCCESS

    with pytest.raises(LifecycleTransitionError, match="already terminal"):
        chain.transition_to(_started(), retry_budget_remaining=0)


@pytest.mark.unit
def test_default_heartbeat_seconds_constant_is_60() -> None:
    """Plan acceptance: default heartbeat threshold is 60 seconds."""
    assert DEFAULT_HEARTBEAT_REQUIRED_SECONDS == 60


@pytest.mark.unit
def test_chain_observed_duration_uses_emitted_at_when_no_override() -> None:
    accepted_at = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    started_at = accepted_at + timedelta(seconds=120)

    accepted = ModelDispatchLifecycleEvent(
        correlation_id="corr-1",
        state=EnumDispatchLifecycleState.ACCEPTED,
        emitter=EnumDispatchLifecycleEmitter.DISPATCHER,
        emitted_at=accepted_at,
        dispatched_at=accepted_at,
        command_topic="onex.cmd.foo.v1",
        target_node_id="node_foo",
    )
    started = ModelDispatchLifecycleEvent(
        correlation_id="corr-1",
        state=EnumDispatchLifecycleState.STARTED,
        emitter=EnumDispatchLifecycleEmitter.CONSUMER,
        emitted_at=started_at,
        started_at=started_at,
        consumer_group="g",
        consumer_host="h",
    )
    chain = LifecycleChain(events=[accepted, started])
    assert chain.observed_duration_seconds == 120
