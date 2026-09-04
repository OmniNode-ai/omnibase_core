# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Client-mode (publish-for-dispatch) tests for ``RuntimeLocal`` (OMN-17304).

Subject: the execution LOCUS of an event-driven workflow.

Before this change ``RuntimeLocal._run_event_driven`` was unconditionally both
roles at once — it subscribed every ``handler_routing.handlers`` entry to its
own ``input_topic`` AND published the initial command to that same topic. On a
shared broker that makes the caller a second, disjoint consumer group of the
command topic it is publishing to, so the deployed runtime and the caller BOTH
execute the entry handler. Live proof on the 2026-08-31 dev lane: the Mac CLI's
group sat at committed offset 53 against a log end of 151 while the lane group
sat at 151/lag 0, and a probe advanced the CLI group by exactly one — it
executed a 98-message-old backlog command, not its own.

``host_handlers=False`` makes the runtime a CLIENT of the bus: publish the
command, await a terminal SCOPED TO THIS RUN'S CORRELATION, host nothing. The
work is then done by whatever runtime is actually subscribed to that command
topic — the deployed lane — which is the only way a lane probe can be
non-vacuous (OMN-17295).

Each positive assertion here is paired with a host-mode counter-assertion.
Without the pair, "never subscribe anything" would satisfy the client-mode
tests while destroying the offline path.
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

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
    ProtocolLocalRuntimeMessage,
)
from omnibase_core.runtime.runtime_local import RuntimeLocal

_MODULE = "tests.unit.runtime.test_runtime_local_client_mode"

_COMMAND_TOPIC = "onex.cmd.omn17304.client-mode.v1"
_TERMINAL_TOPIC = "onex.evt.omn17304.client-mode-completed.v1"


class ModelClientModeCommand(BaseModel):
    """Frozen request model, shaped like ``ModelDelegateSkillRequest``.

    Frozen matters: the real delegate request model is
    ``model_config = {"frozen": True, "extra": "forbid"}``, which is exactly why
    the pre-OMN-17304 correlation overwrite raised ``ValidationError`` and was
    swallowed into a bare ``pass`` — leaving the runtime logging a uuid4 that
    never reached the wire.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    prompt: str = Field(default="")


class HandlerClientModeEcho:
    """Host-mode handler: echoes the command back on the terminal topic."""

    async def handle(self, payload: ModelClientModeCommand) -> dict[str, str]:
        return {
            "status": "success",
            "correlation_id": str(payload.correlation_id),
            "prompt": payload.prompt,
        }


class _RecordedMessage:
    """Minimal ``ProtocolLocalRuntimeMessage`` stand-in."""

    def __init__(self, value: bytes) -> None:
        self.value = value
        self.key: bytes | None = None
        self.topic: str = ""
        self.headers: dict[str, str] = {}


class _RecordingBus:
    """Bus double that records every subscribe/publish and can inject terminals.

    Deliberately does NOT route published commands to subscribers: the subject
    under test is which topics the runtime binds to, not handler execution.
    """

    def __init__(self) -> None:
        self.subscriptions: list[tuple[str, str]] = []
        self.published: list[tuple[str, bytes]] = []
        self._terminal_callbacks: list[
            Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]]
        ] = []
        self.closed = False

    @property
    def subscribed_topics(self) -> list[str]:
        return [topic for topic, _group in self.subscriptions]

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        self.closed = True

    async def publish(self, topic: str, key: object, value: bytes) -> object:
        self.published.append((topic, value))
        return None

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]],
        group_id: str,
    ) -> Callable[[], Awaitable[None]]:
        self.subscriptions.append((topic, group_id))
        if topic == _TERMINAL_TOPIC:
            self._terminal_callbacks.append(on_message)

        async def _unsub() -> None:
            return None

        return _unsub

    async def deliver_terminal(self, payload: dict[str, Any]) -> None:
        message = _RecordedMessage(json.dumps(payload).encode("utf-8"))
        for callback in self._terminal_callbacks:
            await callback(message)  # type: ignore[arg-type]


def _write_contract(target: Path) -> None:
    contract: dict[str, Any] = {
        "workflow_id": "omn-17304-client-mode",
        "name": "client_mode_probe",
        "terminal_event": _TERMINAL_TOPIC,
        "event_bus": {
            "subscribe_topics": [_COMMAND_TOPIC],
            "publish_topics": [_TERMINAL_TOPIC],
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "operation": "start",
                    "handler": {
                        "module": _MODULE,
                        "name": "HandlerClientModeEcho",
                    },
                    "event_model": {
                        "module": _MODULE,
                        "name": "ModelClientModeCommand",
                    },
                }
            ],
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")


def _write_input(target: Path, correlation_id: uuid.UUID) -> None:
    target.write_text(
        json.dumps({"correlation_id": str(correlation_id), "prompt": "probe"}),
        encoding="utf-8",
    )


def _build_runtime(
    tmp_path: Path,
    *,
    host_handlers: bool,
    correlation_id: uuid.UUID,
    timeout: int = 5,
) -> RuntimeLocal:
    contract_path = tmp_path / "contract.yaml"
    input_path = tmp_path / "input.json"
    _write_contract(contract_path)
    _write_input(input_path, correlation_id)
    return RuntimeLocal(
        workflow_path=contract_path,
        state_root=tmp_path / "state",
        input_path=input_path,
        timeout=timeout,
        host_handlers=host_handlers,
    )


def _bind(runtime: RuntimeLocal, bus: _RecordingBus) -> None:
    """Make ``run_async`` use the recording bus instead of a real backend."""
    runtime._create_event_bus = lambda: bus  # type: ignore[assignment,method-assign]


# ---------------------------------------------------------------------------
# Locus: which topics does the runtime bind to?
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_mode_does_not_subscribe_the_command_topic(
    tmp_path: Path,
) -> None:
    """AC4 (OMN-17304): a client publishes; it does not host the entry handler."""
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=False, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(correlation_id)}
    )
    result = await task

    assert result is EnumWorkflowResult.COMPLETED
    assert _COMMAND_TOPIC not in bus.subscribed_topics, (
        "client mode subscribed the command topic it publishes to — the caller "
        "is still a second consumer group of the deployed runtime's own "
        f"command topic. subscriptions={bus.subscriptions}"
    )
    assert _TERMINAL_TOPIC in bus.subscribed_topics
    assert [topic for topic, _ in bus.published] == [_COMMAND_TOPIC]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_host_mode_still_subscribes_the_command_topic(tmp_path: Path) -> None:
    """Counter-assertion: the offline/standalone path is unchanged.

    Passes before AND after the change. Without it, "subscribe nothing" would
    satisfy the client-mode assertion above while deleting in-process
    execution entirely.
    """
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=True, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(correlation_id)}
    )
    result = await task

    assert result is EnumWorkflowResult.COMPLETED
    assert _COMMAND_TOPIC in bus.subscribed_topics
    assert _TERMINAL_TOPIC in bus.subscribed_topics


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_mode_terminal_group_is_run_scoped(tmp_path: Path) -> None:
    """A client must not inherit another run's committed terminal offset."""
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=False, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(correlation_id)}
    )
    result = await task

    assert result is EnumWorkflowResult.COMPLETED
    terminal_groups = [g for t, g in bus.subscriptions if t == _TERMINAL_TOPIC]
    assert len(terminal_groups) == 1
    assert runtime.run_id.hex[:12] in terminal_groups[0], (
        "client-mode terminal subscription reused the shared runtime-local "
        f"group id {terminal_groups[0]!r}; a fresh run would resume another "
        "run's committed offset"
    )


# ---------------------------------------------------------------------------
# Correlation: whose terminal does the client accept?
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_mode_ignores_a_foreign_terminal(tmp_path: Path) -> None:
    """A terminal for a different correlation must not complete this run."""
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=False, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(uuid.uuid4())}
    )
    result = await task

    assert result is EnumWorkflowResult.TIMEOUT, (
        "a foreign terminal completed this run — the client returned another "
        "delegation's result as its own"
    )
    written = json.loads(
        (tmp_path / "state" / "workflow_result.json").read_text(encoding="utf-8")
    )
    assert "terminal_payload" not in written


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_mode_accepts_its_own_terminal_after_a_foreign_one(
    tmp_path: Path,
) -> None:
    """The filter discards, it does not latch — the right terminal still lands."""
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=False, correlation_id=correlation_id, timeout=2
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(uuid.uuid4())}
    )
    await bus.deliver_terminal(
        {
            "status": "success",
            "correlation_id": str(correlation_id),
            "payload": {"correlation_id": str(correlation_id), "answer": "alive"},
        }
    )
    result = await task

    assert result is EnumWorkflowResult.COMPLETED
    written = json.loads(
        (tmp_path / "state" / "workflow_result.json").read_text(encoding="utf-8")
    )
    assert written["terminal_payload"]["correlation_id"] == str(correlation_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_host_mode_terminal_is_correlation_filtered_too(tmp_path: Path) -> None:
    """SUPERSEDED BY OMN-15660: host mode is filtered on the same terms.

    This test previously asserted the opposite — that first-terminal-wins was
    deliberately preserved in host mode because "in-process hosting on the
    in-memory bus has exactly one producer of the terminal topic". That premise
    is true only of the in-memory bus, which dies with the process. Host mode is
    the DEFAULT (``host_handlers=True``) and the only mode any production caller
    uses, so on a Kafka-backed lane the unfiltered path meant `onex delegate`
    adopted whatever terminal the topic still retained from an earlier run —
    observed live 2026-09-02, a run returning a 12-minute-old FAILED terminal as
    its own success. The predicate is now armed wherever a correlation id
    reached the wire, in either mode.
    """
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=True, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(uuid.uuid4())}
    )
    result = await task

    assert result is EnumWorkflowResult.TIMEOUT, (
        "host mode accepted a foreign terminal — the default (and only "
        "production) mode still returns another run's result as its own"
    )
    written = json.loads(
        (tmp_path / "state" / "workflow_result.json").read_text(encoding="utf-8")
    )
    assert "terminal_payload" not in written


# ---------------------------------------------------------------------------
# AC6: the correlation the runtime reports is the one on the wire
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wire_correlation_is_the_payload_correlation_not_a_fresh_uuid(
    tmp_path: Path,
) -> None:
    """AC6 (OMN-17304): stop reporting a uuid4 that never reached the broker.

    ``ModelDelegateSkillRequest`` is frozen, so the old
    ``payload.correlation_id = uuid4()`` raised ``ValidationError`` into a bare
    ``except (AttributeError, ValueError): pass``. The published bytes kept the
    caller's id; every "published initial command (correlation_id=...)" log
    line named the discarded one.
    """
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=False, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(correlation_id)}
    )
    result = await task

    assert result is EnumWorkflowResult.COMPLETED
    assert runtime.wire_correlation_id == correlation_id
    published_topic, published_bytes = bus.published[0]
    assert published_topic == _COMMAND_TOPIC
    on_the_wire = json.loads(published_bytes.decode("utf-8"))
    assert on_the_wire["correlation_id"] == str(runtime.wire_correlation_id), (
        "the reported correlation and the published correlation disagree"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_mode_refuses_an_unattributable_command(tmp_path: Path) -> None:
    """No correlation on the wire ⇒ no correlated await ⇒ refuse, don't guess."""

    class ModelNoCorrelation(BaseModel):
        model_config = ConfigDict(frozen=True, extra="forbid")

        prompt: str = Field(default="")

    contract_path = tmp_path / "contract.yaml"
    contract: dict[str, Any] = {
        "workflow_id": "omn-17304-no-correlation",
        "name": "no_correlation_probe",
        "terminal_event": _TERMINAL_TOPIC,
        "event_bus": {
            "subscribe_topics": [_COMMAND_TOPIC],
            "publish_topics": [_TERMINAL_TOPIC],
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "operation": "start",
                    "handler": {"module": _MODULE, "name": "HandlerClientModeEcho"},
                    "event_model": {"module": _MODULE, "name": "ModelNoCorrelation"},
                }
            ],
        },
    }
    contract_path.write_text(yaml.safe_dump(contract), encoding="utf-8")

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=tmp_path / "state",
        timeout=1,
        host_handlers=False,
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    result = await runtime.run_async()

    assert result is EnumWorkflowResult.FAILED
    assert bus.published == [], "refused run still published a command"
    assert "correlation" in (runtime.last_error or ""), (
        f"refusal did not name the missing correlation: {runtime.last_error!r}"
    )


# ---------------------------------------------------------------------------
# Locus is recorded in the durable result
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execution_locus_is_written_to_workflow_result(tmp_path: Path) -> None:
    """The receipt layer must be able to answer "did this run on the lane?"."""
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=False, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(correlation_id)}
    )
    result = await task

    assert result is EnumWorkflowResult.COMPLETED
    written = json.loads(
        (tmp_path / "state" / "workflow_result.json").read_text(encoding="utf-8")
    )
    assert written["handler_locus"] == "dispatched"
    assert written["wire_correlation_id"] == str(correlation_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execution_locus_in_process_for_host_mode(tmp_path: Path) -> None:
    """Counter-assertion: host mode records itself honestly too."""
    correlation_id = uuid.uuid4()
    runtime = _build_runtime(
        tmp_path, host_handlers=True, correlation_id=correlation_id, timeout=1
    )
    bus = _RecordingBus()

    _bind(runtime, bus)
    task = asyncio.ensure_future(runtime.run_async())
    await asyncio.sleep(0.05)
    await bus.deliver_terminal(
        {"status": "success", "correlation_id": str(correlation_id)}
    )
    result = await task

    assert result is EnumWorkflowResult.COMPLETED
    written = json.loads(
        (tmp_path / "state" / "workflow_result.json").read_text(encoding="utf-8")
    )
    assert written["handler_locus"] == "in_process"
