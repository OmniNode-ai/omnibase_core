# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The caller must hear the lane's FAILURE terminal, not time out beside it (OMN-18445).

``RuntimeLocal`` subscribed to exactly one topic: the contract's top-level
``terminal_event``, which names the SUCCESS half of the pair.
``node_delegate_skill_orchestrator`` declares its failure terminal under
``runtime_dispatch.terminal_events.failure`` and nowhere else, so a lane-side
delegation failure published a record to an address nobody was listening on. The
caller could not tell that from silence: it waited out its whole ``--timeout``
and reported a timeout for a run the lane had already answered.

Live framing (``.201`` dev lane, identity ``dev-cli-stickybeatz-studio``,
2026-09-16T16:45Z-16:49Z): five ``onex delegate --bus kafka --lane dev`` runs, all
five returning at ~203s against ``--timeout 200``, and the effects container log
carrying ``Published output event to
onex.evt.omnimarket.delegate-skill-failed.v1`` for each caller's own correlation —
for the concurrent pair, at 16:48:52Z and 16:48:53Z, INSIDE a window opened at
16:45:50Z.

Each positive assertion here is paired with the counter-assertion that pins what
it must not destroy. "Subscribe to everything and fail on anything" would satisfy
a failure test on its own while breaking every successful delegation and
re-opening the cross-run adoption OMN-15660 closed, so the success control and
the foreign-correlation control are part of the proof, not decoration.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_terminal_outcome import EnumTerminalOutcome
from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
    ProtocolLocalRuntimeMessage,
)
from omnibase_core.runtime.contract_terminal_topics import resolve_terminal_topics
from omnibase_core.runtime.runtime_local import RuntimeLocal

_MODULE = "tests.unit.runtime.test_runtime_local_failure_terminal"

_COMMAND_TOPIC = "onex.cmd.omn18445.failure-terminal.v1"
_SUCCESS_TOPIC = "onex.evt.omn18445.failure-terminal-completed.v1"
_FAILURE_TOPIC = "onex.evt.omn18445.failure-terminal-failed.v1"

# The reason string the lane publishes. Asserted verbatim on the caller's side so
# "the run failed" cannot pass for "here is why it failed" (AC4).
_LANE_REASON = "quality gate refused the response: no provider accepted the route"


class ModelFailureProbeCommand(BaseModel):
    """Frozen request model, shaped like ``ModelDelegateSkillRequest``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    prompt: str = Field(default="")


class HandlerFailureProbeSilent:
    """Publishes nothing: the LANE publishes the terminal, as it does in production.

    In client mode (``host_handlers=False``) the runtime binds nothing to the
    command topic at all — the deployed runtime executes it. This handler exists
    only so the contract's ``handler_routing`` resolves; the tests below drive the
    terminal onto the broker themselves, which is what makes them a test of the
    caller's SUBSCRIPTION rather than of an in-process handler's return value.
    """

    async def handle(self, payload: ModelFailureProbeCommand) -> dict[str, str]:
        await asyncio.sleep(0)
        return {"status": "success", "correlation_id": str(payload.correlation_id)}


class _Message:
    """Minimal ``ProtocolLocalRuntimeMessage`` stand-in."""

    def __init__(self, value: bytes, topic: str) -> None:
        self.value = value
        self.key: bytes | None = None
        self.topic = topic
        self.headers: dict[str, str] = {}


class _Broker:
    """A retaining broker: subscribers live here, so a publish reaches every run."""

    def __init__(self) -> None:
        self.log: dict[str, list[bytes]] = {}
        self.committed: dict[tuple[str, str], int] = {}
        self.subscribers: list[
            tuple[str, str, Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]]]
        ] = []

    def append(self, topic: str, value: bytes) -> None:
        self.log.setdefault(topic, []).append(value)

    async def drain(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]],
    ) -> None:
        offset_key = (group_id, topic)
        while self.committed.get(offset_key, 0) < len(self.log.get(topic, [])):
            index = self.committed.get(offset_key, 0)
            self.committed[offset_key] = index + 1
            await on_message(_Message(self.log[topic][index], topic))  # type: ignore[arg-type]

    async def deliver(self, topic: str) -> None:
        for sub_topic, group_id, on_message in list(self.subscribers):
            if sub_topic == topic:
                await self.drain(topic, group_id, on_message)

    async def publish_terminal(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a terminal record the way the deployed lane does."""
        self.append(topic, json.dumps(payload).encode("utf-8"))
        await self.deliver(topic)


class _Bus:
    """One process's view of :class:`_Broker`."""

    def __init__(self, broker: _Broker) -> None:
        self.broker = broker
        self.subscriptions: list[tuple[str, str]] = []
        self.closed = False

    @property
    def subscribed_topics(self) -> list[str]:
        return [topic for topic, _group in self.subscriptions]

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        self.closed = True

    async def publish(self, topic: str, key: object, value: bytes) -> object:
        self.broker.append(topic, value)
        await self.broker.deliver(topic)
        return None

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]],
        group_id: str,
    ) -> Callable[[], Awaitable[None]]:
        self.subscriptions.append((topic, group_id))
        registration = (topic, group_id, on_message)
        self.broker.subscribers.append(registration)
        await self.broker.drain(topic, group_id, on_message)

        async def _unsub() -> None:
            if registration in self.broker.subscribers:
                self.broker.subscribers.remove(registration)

        return _unsub


def _contract_body(*, declare_failure_terminal: bool) -> dict[str, Any]:
    """The delegate orchestrator's shape: failure declared under ``runtime_dispatch``.

    ``declare_failure_terminal=False`` is the pre-OMN-18445 contract shape and is
    what makes AC2 falsifiable — removing the declaration must change which
    topics are subscribed, which it cannot do if a topic string is hardcoded in
    the runtime.
    """
    contract: dict[str, Any] = {
        "workflow_id": "omn-18445-failure-terminal",
        "name": "failure_terminal_probe",
        "terminal_event": _SUCCESS_TOPIC,
        "event_bus": {
            "subscribe_topics": [_COMMAND_TOPIC],
            "publish_topics": [_SUCCESS_TOPIC, _FAILURE_TOPIC],
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "operation": "start",
                    "handler": {
                        "module": _MODULE,
                        "name": "HandlerFailureProbeSilent",
                    },
                    "event_model": {
                        "module": _MODULE,
                        "name": "ModelFailureProbeCommand",
                    },
                    "output_topic": _SUCCESS_TOPIC,
                }
            ],
        },
    }
    if declare_failure_terminal:
        contract["runtime_dispatch"] = {
            "command_topic": _COMMAND_TOPIC,
            "terminal_events": {
                "success": _SUCCESS_TOPIC,
                "failure": _FAILURE_TOPIC,
            },
        }
    return contract


def _build_runtime(
    run_dir: Path,
    *,
    correlation_id: uuid.UUID,
    timeout: int = 2,
    declare_failure_terminal: bool = True,
) -> RuntimeLocal:
    """One runtime with its own state_root — a distinct `onex delegate` process."""
    run_dir.mkdir(parents=True, exist_ok=True)
    contract_path = run_dir / "contract.yaml"
    input_path = run_dir / "input.json"
    contract_path.write_text(
        yaml.safe_dump(
            _contract_body(declare_failure_terminal=declare_failure_terminal)
        ),
        encoding="utf-8",
    )
    input_path.write_text(
        json.dumps({"correlation_id": str(correlation_id), "prompt": "probe"}),
        encoding="utf-8",
    )
    return RuntimeLocal(
        workflow_path=contract_path,
        state_root=run_dir / "state",
        input_path=input_path,
        timeout=timeout,
        host_handlers=False,
    )


def _bind(runtime: RuntimeLocal, bus: _Bus) -> None:
    runtime._create_event_bus = lambda: bus  # type: ignore[assignment,method-assign]


def _written(run_dir: Path) -> dict[str, Any]:
    raw = (run_dir / "state" / "workflow_result.json").read_text(encoding="utf-8")
    decoded: dict[str, Any] = json.loads(raw)
    return decoded


def _lane_failure_envelope(correlation_id: uuid.UUID) -> dict[str, Any]:
    """The failure terminal as the deployed applier publishes it.

    A ``ModelEventEnvelope`` wire dict: ``envelope_id`` plus a mapping
    ``payload``, with no top-level ``status`` — the shape OMN-17567 recorded.
    """
    return {
        "envelope_id": str(uuid.uuid4()),
        "envelope_timestamp": "2026-09-16T16:48:52.104000Z",
        "correlation_id": str(correlation_id),
        "event_type": "omnimarket.delegate-skill-failed",
        "payload": {
            "correlation_id": str(correlation_id),
            "status": "failed",
            "error_message": _LANE_REASON,
        },
    }


async def _publish_after(
    broker: _Broker, topic: str, payload: dict[str, Any], *, delay: float
) -> None:
    """Publish a terminal once the caller is inside its wait window."""
    await asyncio.sleep(delay)
    await broker.publish_terminal(topic, payload)


# ---------------------------------------------------------------------------
# AC1 / AC4 — the failure terminal ends the wait, with the lane's reason.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failure_terminal_inside_the_window_ends_the_wait_as_failed(
    tmp_path: Path,
) -> None:
    """The live defect: the lane answers on the failure topic and the caller waits.

    Pre-image: the caller subscribes only to ``terminal_event`` (the success
    topic), the failure record lands on a topic nothing is bound to, and this
    returns TIMEOUT at the full ``timeout`` with ``terminal_payload`` absent.
    """
    broker = _Broker()
    correlation_id = uuid.uuid4()
    run_dir = tmp_path / "run"
    runtime = _build_runtime(run_dir, correlation_id=correlation_id, timeout=5)
    _bind(runtime, _Bus(broker))

    loop = asyncio.get_running_loop()
    started = loop.time()
    publisher = asyncio.create_task(
        _publish_after(
            broker,
            _FAILURE_TOPIC,
            _lane_failure_envelope(correlation_id),
            delay=0.05,
        )
    )
    result = await runtime.run_async()
    await publisher
    elapsed = loop.time() - started

    assert result is EnumWorkflowResult.FAILED
    # Non-zero exit, and specifically not the timeout's exit for the wrong reason.
    assert runtime.exit_code != 0
    assert elapsed < 4.0, "the caller waited out its timeout beside a live answer"

    written = _written(run_dir)
    assert written["result"] == EnumWorkflowResult.FAILED.value
    assert written["wire_correlation_id"] == str(correlation_id)
    # AC4: the reason the LANE published, not merely that something failed.
    assert written["terminal_payload"]["payload"]["error_message"] == _LANE_REASON


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failure_terminal_without_a_status_field_is_still_failed(
    tmp_path: Path,
) -> None:
    """The contract's declaration outranks a payload that declares nothing.

    The un-enveloped failure shape recorded under OMN-15468 carries no
    ``status`` at either level. Classifying it by payload alone reads a missing
    failure marker as success, which would turn this defect into a worse one:
    an explicit lane failure reported as a completed delegation.
    """
    broker = _Broker()
    correlation_id = uuid.uuid4()
    run_dir = tmp_path / "run"
    runtime = _build_runtime(run_dir, correlation_id=correlation_id, timeout=5)
    _bind(runtime, _Bus(broker))

    raw_failure = {
        "correlation_id": str(correlation_id),
        "task_description": "probe",
        "attempts": [{"provider": "glm", "error": _LANE_REASON}],
    }
    publisher = asyncio.create_task(
        _publish_after(broker, _FAILURE_TOPIC, raw_failure, delay=0.05)
    )
    result = await runtime.run_async()
    await publisher

    assert result is EnumWorkflowResult.FAILED
    assert _written(run_dir)["result"] == EnumWorkflowResult.FAILED.value


# ---------------------------------------------------------------------------
# Counter-assertions: what the fix must not destroy.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_success_terminal_still_completes(tmp_path: Path) -> None:
    """Positive control. Watching a second topic must not break the first one."""
    broker = _Broker()
    correlation_id = uuid.uuid4()
    run_dir = tmp_path / "run"
    runtime = _build_runtime(run_dir, correlation_id=correlation_id, timeout=5)
    _bind(runtime, _Bus(broker))

    success = {
        "envelope_id": str(uuid.uuid4()),
        "correlation_id": str(correlation_id),
        "event_type": "omnimarket.delegate-skill-completed",
        "payload": {"correlation_id": str(correlation_id), "status": "success"},
    }
    publisher = asyncio.create_task(
        _publish_after(broker, _SUCCESS_TOPIC, success, delay=0.05)
    )
    result = await runtime.run_async()
    await publisher

    assert result is EnumWorkflowResult.COMPLETED
    assert runtime.exit_code == 0
    assert _written(run_dir)["result"] == EnumWorkflowResult.COMPLETED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_another_runs_failure_terminal_is_discarded(tmp_path: Path) -> None:
    """AC3 — two runs in flight: a foreign failure is refused on the new topic too.

    The correlation predicate is the isolation boundary OMN-15660 armed on the
    success topic. Subscribing to a second topic without extending that boundary
    would hand every concurrent delegation its neighbour's failure.
    """
    broker = _Broker()
    correlation_id = uuid.uuid4()
    stranger = uuid.uuid4()
    run_dir = tmp_path / "run"
    runtime = _build_runtime(run_dir, correlation_id=correlation_id, timeout=2)
    _bind(runtime, _Bus(broker))

    publisher = asyncio.create_task(
        _publish_after(
            broker, _FAILURE_TOPIC, _lane_failure_envelope(stranger), delay=0.05
        )
    )
    result = await runtime.run_async()
    await publisher

    assert result is EnumWorkflowResult.TIMEOUT
    written = _written(run_dir)
    assert "terminal_payload" not in written
    # It was seen and refused, not simply never delivered — a never-delivered
    # record would make this assertion pass with no isolation at all.
    assert runtime._events_received.get("(terminal:foreign)") == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_own_failure_terminal_survives_a_stranger_on_the_same_topic(
    tmp_path: Path,
) -> None:
    """A foreign failure ahead of ours must not consume the run's own answer."""
    broker = _Broker()
    correlation_id = uuid.uuid4()
    stranger = uuid.uuid4()
    run_dir = tmp_path / "run"
    runtime = _build_runtime(run_dir, correlation_id=correlation_id, timeout=5)
    _bind(runtime, _Bus(broker))

    async def _publish_both() -> None:
        await asyncio.sleep(0.05)
        await broker.publish_terminal(_FAILURE_TOPIC, _lane_failure_envelope(stranger))
        await broker.publish_terminal(
            _FAILURE_TOPIC, _lane_failure_envelope(correlation_id)
        )

    publisher = asyncio.create_task(_publish_both())
    result = await runtime.run_async()
    await publisher

    assert result is EnumWorkflowResult.FAILED
    written = _written(run_dir)
    assert written["terminal_payload"]["correlation_id"] == str(correlation_id)


# ---------------------------------------------------------------------------
# AC2 — the subscription set is contract-declared, not a literal.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscription_set_follows_the_contract_declaration(
    tmp_path: Path,
) -> None:
    """Removing the declaration removes the subscription.

    A runtime that hardcoded the failure topic would subscribe to it in both
    halves of this test and the second assertion would fail.
    """
    declared_dir = tmp_path / "declared"
    declared_bus = _Bus(_Broker())
    declared = _build_runtime(
        declared_dir,
        correlation_id=uuid.uuid4(),
        timeout=1,
        declare_failure_terminal=True,
    )
    _bind(declared, declared_bus)
    await declared.run_async()
    assert _FAILURE_TOPIC in declared_bus.subscribed_topics
    assert _SUCCESS_TOPIC in declared_bus.subscribed_topics

    undeclared_dir = tmp_path / "undeclared"
    undeclared_bus = _Bus(_Broker())
    undeclared = _build_runtime(
        undeclared_dir,
        correlation_id=uuid.uuid4(),
        timeout=1,
        declare_failure_terminal=False,
    )
    _bind(undeclared, undeclared_bus)
    await undeclared.run_async()
    assert _FAILURE_TOPIC not in undeclared_bus.subscribed_topics
    assert _SUCCESS_TOPIC in undeclared_bus.subscribed_topics


@pytest.mark.unit
def test_resolver_reads_all_three_declaration_sites_success_first() -> None:
    """The three sites, in success-first order, de-duplicated on first mention."""
    resolved = resolve_terminal_topics(
        {
            "terminal_event": _SUCCESS_TOPIC,
            "runtime_dispatch": {
                "terminal_events": {
                    "failure": _FAILURE_TOPIC,
                    "success": _SUCCESS_TOPIC,
                }
            },
        }
    )
    assert [declared.topic for declared in resolved] == [
        _SUCCESS_TOPIC,
        _FAILURE_TOPIC,
    ]
    assert resolved[0].outcome is EnumTerminalOutcome.SUCCESS
    assert resolved[1].outcome is EnumTerminalOutcome.FAILURE


@pytest.mark.unit
def test_resolver_returns_nothing_for_a_contract_with_no_terminal() -> None:
    """Empty is the caller's decision to make, exactly as ``.get()`` was."""
    assert resolve_terminal_topics({"name": "no_terminal"}) == ()


# ---------------------------------------------------------------------------
# A terminal the broker will not let this client read.
# ---------------------------------------------------------------------------


class _RefusingBus(_Bus):
    """A broker that authorizes one terminal topic and refuses the other.

    The live state of the ``.201`` dev lane when this landed: identity
    ``dev-cli-stickybeatz-studio`` held a read grant on the completed terminal
    and none on the failed one, so the first run that tried to watch both got
    ``TopicAuthorizationFailedError`` from the second subscribe.
    """

    def __init__(self, broker: _Broker, *, refuse: str) -> None:
        super().__init__(broker)
        self.refuse = refuse
        self.refused: list[str] = []

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]],
        group_id: str,
    ) -> Callable[[], Awaitable[None]]:
        if topic == self.refuse:
            self.refused.append(topic)
            raise PermissionError(f"topic {topic} is not authorized for this client")
        return await super().subscribe(topic, on_message=on_message, group_id=group_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_an_unwatchable_extra_terminal_does_not_break_the_delegation(
    tmp_path: Path,
) -> None:
    """New coverage that cannot be obtained must not take a working run down.

    Watching a second topic is an improvement on a lane that permits it. On a
    lane that does not, the run must still do everything it did before —
    otherwise this change converts a class of silent timeouts into a class of
    delegations that cannot run at all.
    """
    broker = _Broker()
    correlation_id = uuid.uuid4()
    run_dir = tmp_path / "run"
    bus = _RefusingBus(broker, refuse=_FAILURE_TOPIC)
    runtime = _build_runtime(run_dir, correlation_id=correlation_id, timeout=5)
    _bind(runtime, bus)

    success = {
        "envelope_id": str(uuid.uuid4()),
        "correlation_id": str(correlation_id),
        "payload": {"correlation_id": str(correlation_id), "status": "success"},
    }
    publisher = asyncio.create_task(
        _publish_after(broker, _SUCCESS_TOPIC, success, delay=0.05)
    )
    result = await runtime.run_async()
    await publisher

    assert result is EnumWorkflowResult.COMPLETED
    assert bus.refused == [_FAILURE_TOPIC]
    # Recorded, not swallowed: a later timeout must be able to say which
    # terminal it was unable to listen on.
    assert runtime._events_received.get(f"(terminal:unwatchable:{_FAILURE_TOPIC})") == 1
    assert runtime._last_error is not None
    assert _FAILURE_TOPIC in runtime._last_error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_an_unwatchable_first_terminal_is_still_fatal(tmp_path: Path) -> None:
    """Counter-assertion: the terminal this runtime always watched stays fatal.

    Degrading on the FIRST declared terminal would mean a run that watches
    nothing at all and then sits out its whole timeout, which is a worse
    failure than the one being fixed. It propagates instead, and ``run_async``
    records it as FAILED the way it always has — immediately, not at the
    timeout, and with no unwatchable-terminal diagnostic, because nothing was
    degraded here.
    """
    broker = _Broker()
    run_dir = tmp_path / "run"
    bus = _RefusingBus(broker, refuse=_SUCCESS_TOPIC)
    runtime = _build_runtime(run_dir, correlation_id=uuid.uuid4(), timeout=30)
    _bind(runtime, bus)

    loop = asyncio.get_running_loop()
    started = loop.time()
    result = await runtime.run_async()
    elapsed = loop.time() - started

    assert result is EnumWorkflowResult.FAILED
    assert elapsed < 5.0, "a fatal subscribe must not be paid for at the timeout"
    assert bus.refused == [_SUCCESS_TOPIC]
    assert not any(
        key.startswith("(terminal:unwatchable") for key in runtime._events_received
    )
