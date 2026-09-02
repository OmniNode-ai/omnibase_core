# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Terminal-event isolation for ``RuntimeLocal`` (OMN-15660, OMN-17567).

Two defects, both proven live on 2026-09-02 against a Kafka-backed single-tenant
lane, and both invisible to the OMN-17304 suite because that suite only exercises
``host_handlers=False`` — a mode with **zero production callers**.

**OMN-15660 — cross-run terminal adoption.** ``RuntimeLocal.__init__`` defaults
``host_handlers=True``; ``onex delegate`` therefore always runs host mode. In host
mode the OMN-17304 remedies were both gated off: the correlation predicate was
never armed and the terminal consumer group was never run-scoped. On a durable
broker every invocation joined one fixed group, inherited the previous run's
committed offset, and adopted whatever terminal was still retained — a *sequential*
manifestation (runs minutes apart), not the concurrent one the original ticket
described. The state is self-perpetuating: a run that adopts a stale terminal
returns before publishing its own, leaving that one retained-and-uncommitted for
the next run.

**OMN-17567 — optimistic status read.** ``_on_terminal_event`` read
``payload.get("status", "success")`` at the *envelope* top level. A
``ModelEventEnvelope``-shaped terminal carries no top-level ``status`` — it lives
under ``payload.status`` — so a FAILED terminal was classified COMPLETED. Two
terminal shapes coexist on the delegate topic (the single-output adapter path
publishes a bare domain payload; the fan-out path publishes an envelope), which is
what made the ambiguity reachable.

Every positive assertion here is paired with a counter-assertion that pins the
behaviour it must NOT destroy: the offline in-process path with a status-less
domain terminal must stay COMPLETED, or "refuse everything" would satisfy these
tests while deleting the offline runtime.
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

_MODULE = "tests.unit.runtime.test_runtime_local_terminal_isolation"

_COMMAND_TOPIC = "onex.cmd.omn15660.terminal-isolation.v1"
_TERMINAL_TOPIC = "onex.evt.omn15660.terminal-isolation-completed.v1"


class ModelIsolationCommand(BaseModel):
    """Frozen request model, shaped like ``ModelDelegateSkillRequest``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    prompt: str = Field(default="")


class HandlerIsolationEcho:
    """Host-mode handler: echoes this run's correlation onto the terminal topic.

    The ``sleep`` is load-bearing for the concurrent test: without a real yield
    inside the publish chain, two ``run_async`` coroutines gathered together run to
    completion one after the other and the "concurrent" case degenerates into a
    sequential one that passes vacuously.
    """

    async def handle(self, payload: ModelIsolationCommand) -> dict[str, str]:
        # The prompt carries this run's think-time so a concurrent test can put
        # the slow run in the terminal wait at the exact moment the fast run's
        # terminal lands. Without a real yield inside the publish chain, two
        # gathered ``run_async`` coroutines run one after the other and every
        # "concurrent" assertion passes vacuously.
        await asyncio.sleep(0.30 if payload.prompt == "slow" else 0.01)
        return {
            "status": "success",
            "correlation_id": str(payload.correlation_id),
            "prompt": payload.prompt,
        }


# ---------------------------------------------------------------------------
# A retaining broker double: Kafka semantics (retained log + per-group committed
# offsets) with no Kafka. The in-memory bus dies with the process and is immune
# to this defect by construction, so it cannot express the bug.
# ---------------------------------------------------------------------------


class _DurableMessage:
    """Minimal ``ProtocolLocalRuntimeMessage`` stand-in."""

    def __init__(self, value: bytes, topic: str) -> None:
        self.value = value
        self.key: bytes | None = None
        self.topic = topic
        self.headers: dict[str, str] = {}


class _DurableBroker:
    """Records survive the process that published them; groups carry offsets.

    Subscribers live on the BROKER, not on a bus instance: a topic is shared by
    every process attached to it, so a publish from one run must reach another
    run's subscription. A bus instance that only fans out to its own subscribers
    cannot express cross-run delivery at all, and every cross-talk test against it
    would pass vacuously.
    """

    def __init__(self) -> None:
        self.log: dict[str, list[bytes]] = {}
        self.committed: dict[tuple[str, str], int] = {}
        self.subscribers: list[
            tuple[str, str, Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]]]
        ] = []

    def append(self, topic: str, value: bytes) -> None:
        self.log.setdefault(topic, []).append(value)

    def seed(self, topic: str, payload: dict[str, Any]) -> None:
        """Retain a record no consumer group has committed past (the live LAG-1)."""
        self.append(topic, json.dumps(payload).encode("utf-8"))

    async def drain(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]],
    ) -> None:
        """Deliver every record this group has not committed past, in order."""
        offset_key = (group_id, topic)
        while self.committed.get(offset_key, 0) < len(self.log.get(topic, [])):
            index = self.committed.get(offset_key, 0)
            self.committed[offset_key] = index + 1
            await on_message(_DurableMessage(self.log[topic][index], topic))  # type: ignore[arg-type]

    async def deliver(self, topic: str) -> None:
        for sub_topic, group_id, on_message in list(self.subscribers):
            if sub_topic == topic:
                await self.drain(topic, group_id, on_message)


class _DurableBus:
    """One process's view of :class:`_DurableBroker`.

    A fresh instance per run — like a fresh ``onex delegate`` process — while the
    broker (log, committed offsets, live subscribers) outlives every one of them.
    """

    def __init__(self, broker: _DurableBroker) -> None:
        self.broker = broker
        self.subscriptions: list[tuple[str, str]] = []
        self.closed = False

    @property
    def subscribed_topics(self) -> list[str]:
        return [topic for topic, _group in self.subscriptions]

    def terminal_groups(self) -> list[str]:
        return [
            group for topic, group in self.subscriptions if topic == _TERMINAL_TOPIC
        ]

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


def _write_contract(target: Path) -> None:
    contract: dict[str, Any] = {
        "workflow_id": "omn-15660-terminal-isolation",
        "name": "terminal_isolation_probe",
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
                    "handler": {"module": _MODULE, "name": "HandlerIsolationEcho"},
                    "event_model": {"module": _MODULE, "name": "ModelIsolationCommand"},
                    "output_topic": _TERMINAL_TOPIC,
                }
            ],
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")


def _build_runtime(
    run_dir: Path,
    *,
    correlation_id: uuid.UUID,
    host_handlers: bool = True,
    timeout: int = 2,
    prompt: str = "probe",
) -> RuntimeLocal:
    """One runtime, with its own state_root — a distinct `onex delegate` process."""
    run_dir.mkdir(parents=True, exist_ok=True)
    contract_path = run_dir / "contract.yaml"
    input_path = run_dir / "input.json"
    _write_contract(contract_path)
    input_path.write_text(
        json.dumps({"correlation_id": str(correlation_id), "prompt": prompt}),
        encoding="utf-8",
    )
    return RuntimeLocal(
        workflow_path=contract_path,
        state_root=run_dir / "state",
        input_path=input_path,
        timeout=timeout,
        host_handlers=host_handlers,
    )


def _bind(runtime: RuntimeLocal, bus: _DurableBus) -> None:
    runtime._create_event_bus = lambda: bus  # type: ignore[assignment,method-assign]


def _written(run_dir: Path) -> dict[str, Any]:
    raw = (run_dir / "state" / "workflow_result.json").read_text(encoding="utf-8")
    decoded: dict[str, Any] = json.loads(raw)
    return decoded


def _envelope(correlation_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    """A ``ModelEventEnvelope`` wire dict — the fan-out publish shape.

    ``envelope_id`` + a dict ``payload`` is the discriminator the adapter already
    uses (``_unwrap_envelope_dict``); note there is deliberately no top-level
    ``status`` key, which is the whole of OMN-17567.
    """
    return {
        "envelope_id": str(uuid.uuid4()),
        "envelope_timestamp": "2026-09-02T11:59:00.005090Z",
        "correlation_id": str(correlation_id),
        "event_type": "omnimarket.delegate-skill-completed",
        "payload": payload,
    }


# ---------------------------------------------------------------------------
# OMN-15660: sequential cross-run adoption on a durable bus.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_host_mode_never_adopts_a_retained_terminal_from_an_earlier_run(
    tmp_path: Path,
) -> None:
    """The live defect: run B adopts run A's retained terminal and exits.

    Sequential, not concurrent — run A is already gone. The broker still holds A's
    terminal because A never joined it (it had adopted an even older one), which is
    the LAG-1 state observed on the lane. Run B must ignore A's record entirely and
    complete only on the terminal its own handler publishes.
    """
    broker = _DurableBroker()
    run_a_correlation = uuid.uuid4()
    broker.seed(
        _TERMINAL_TOPIC,
        {"status": "success", "correlation_id": str(run_a_correlation)},
    )

    run_b_correlation = uuid.uuid4()
    run_b_dir = tmp_path / "run_b"
    runtime = _build_runtime(run_b_dir, correlation_id=run_b_correlation)
    bus = _DurableBus(broker)
    _bind(runtime, bus)

    result = await runtime.run_async()

    assert result is EnumWorkflowResult.COMPLETED
    written = _written(run_b_dir)
    assert written["terminal_payload"]["correlation_id"] == str(run_b_correlation), (
        "host mode adopted an earlier run's retained terminal — this run reported "
        f"correlation {written['terminal_payload'].get('correlation_id')} as its own "
        f"result, but it published {run_b_correlation}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_host_mode_refuses_a_retained_failed_terminal_from_an_earlier_run(
    tmp_path: Path,
) -> None:
    """The compounded live case: the adopted terminal was a FAILURE.

    Offset 1 on the lane was an envelope whose ``payload.status`` was ``failed``;
    the runtime reported the run ``completed``. Both defects have to be fixed for
    this to hold — correlation isolation (OMN-15660) and the status read
    (OMN-17567).
    """
    broker = _DurableBroker()
    run_a_correlation = uuid.uuid4()
    broker.seed(
        _TERMINAL_TOPIC,
        _envelope(
            run_a_correlation,
            {
                "status": "failed",
                "correlation_id": str(run_a_correlation),
                "quality_gates_failed": ["coverage"],
            },
        ),
    )

    run_b_correlation = uuid.uuid4()
    run_b_dir = tmp_path / "run_b"
    runtime = _build_runtime(run_b_dir, correlation_id=run_b_correlation)
    bus = _DurableBus(broker)
    _bind(runtime, bus)

    result = await runtime.run_async()

    written = _written(run_b_dir)
    assert written["terminal_payload"]["correlation_id"] == str(run_b_correlation), (
        "this run reported another run's FAILED terminal as its own result"
    )
    assert result is EnumWorkflowResult.COMPLETED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_host_mode_terminal_group_is_run_scoped(tmp_path: Path) -> None:
    """A host must not inherit another run's committed terminal offset either.

    OMN-17304 AC5 run-scoped this group for clients only. ``onex delegate`` is a
    host, so on the lane every invocation joined one fixed group and resumed the
    previous run's offset. Run-scoping alone does not fix adoption (a fresh group
    reads the retained backlog from the beginning) — it must land together with the
    armed correlation predicate, which the tests above cover.
    """
    broker = _DurableBroker()
    correlation_id = uuid.uuid4()
    run_dir = tmp_path / "run"
    runtime = _build_runtime(run_dir, correlation_id=correlation_id)
    bus = _DurableBus(broker)
    _bind(runtime, bus)

    await runtime.run_async()

    groups = bus.terminal_groups()
    assert len(groups) == 1
    assert runtime.run_id.hex[:12] in groups[0], (
        "host-mode terminal subscription reused the shared runtime-local group id "
        f"{groups[0]!r}; a fresh run resumes another run's committed offset"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_two_sequential_host_runs_do_not_share_a_terminal_group(
    tmp_path: Path,
) -> None:
    """End-to-end sequential proof: run A, let it finish, then run B.

    Each run must join its own terminal group and return its own correlation. This
    is the shape ``onex delegate`` actually takes on a Kafka-backed lane.
    """
    broker = _DurableBroker()

    run_a_correlation = uuid.uuid4()
    run_a_dir = tmp_path / "run_a"
    runtime_a = _build_runtime(run_a_dir, correlation_id=run_a_correlation)
    bus_a = _DurableBus(broker)
    _bind(runtime_a, bus_a)
    result_a = await runtime_a.run_async()

    run_b_correlation = uuid.uuid4()
    run_b_dir = tmp_path / "run_b"
    runtime_b = _build_runtime(run_b_dir, correlation_id=run_b_correlation)
    bus_b = _DurableBus(broker)
    _bind(runtime_b, bus_b)
    result_b = await runtime_b.run_async()

    assert result_a is EnumWorkflowResult.COMPLETED
    assert result_b is EnumWorkflowResult.COMPLETED
    assert _written(run_a_dir)["terminal_payload"]["correlation_id"] == str(
        run_a_correlation
    )
    assert _written(run_b_dir)["terminal_payload"]["correlation_id"] == str(
        run_b_correlation
    ), "the second run returned the first run's result"
    assert bus_a.terminal_groups() != bus_b.terminal_groups(), (
        "both runs joined the same terminal consumer group"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_slow_host_run_does_not_adopt_a_concurrent_runs_terminal(
    tmp_path: Path,
) -> None:
    """OMN-15660's original concurrent framing, on the host path this time.

    The slow run is parked in its terminal wait when the fast run's terminal is
    published. Sharing one terminal consumer group, the slow run's callback is
    served that record first and — with no correlation predicate armed — accepts
    it, so the slow run returns the fast run's answer and the fast run gets
    nothing. Ordering here is deterministic: the slow handler sleeps 30x longer.
    """
    broker = _DurableBroker()

    slow_correlation = uuid.uuid4()
    fast_correlation = uuid.uuid4()
    slow_dir = tmp_path / "concurrent_slow"
    fast_dir = tmp_path / "concurrent_fast"
    slow = _build_runtime(
        slow_dir, correlation_id=slow_correlation, timeout=5, prompt="slow"
    )
    fast = _build_runtime(
        fast_dir, correlation_id=fast_correlation, timeout=5, prompt="fast"
    )
    _bind(slow, _DurableBus(broker))
    _bind(fast, _DurableBus(broker))

    slow_result, fast_result = await asyncio.gather(slow.run_async(), fast.run_async())

    assert _written(slow_dir)["terminal_payload"]["correlation_id"] == str(
        slow_correlation
    ), "the slow run adopted the concurrent fast run's terminal"
    assert _written(fast_dir)["terminal_payload"]["correlation_id"] == str(
        fast_correlation
    ), "the fast run's own terminal was consumed by the concurrent slow run"
    assert slow_result is EnumWorkflowResult.COMPLETED
    assert fast_result is EnumWorkflowResult.COMPLETED


# ---------------------------------------------------------------------------
# OMN-17567: the terminal status read.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_envelope_shaped_failed_terminal_is_classified_failed(tmp_path: Path) -> None:
    """``payload.status == "failed"`` on an envelope must not read as success.

    ``_on_terminal_event`` looked for ``status`` at the envelope top level only and
    defaulted the miss to ``"success"``, so an envelope-shaped terminal could never
    surface a failure through this path.
    """
    correlation_id = uuid.uuid4()
    runtime = RuntimeLocal(
        workflow_path=tmp_path / "contract.yaml",
        state_root=tmp_path / "state",
    )

    runtime._on_terminal_event(
        _envelope(
            correlation_id,
            {"status": "failed", "correlation_id": str(correlation_id)},
        )
    )

    assert runtime._result is EnumWorkflowResult.FAILED


@pytest.mark.unit
@pytest.mark.parametrize("status", ["failure", "failed", "error", "ERROR"])
def test_envelope_shaped_failure_statuses_all_classify_failed(
    tmp_path: Path, status: str
) -> None:
    """The envelope path recognises the same failure vocabulary as the bare path."""
    correlation_id = uuid.uuid4()
    runtime = RuntimeLocal(
        workflow_path=tmp_path / "contract.yaml",
        state_root=tmp_path / "state",
    )

    runtime._on_terminal_event(
        _envelope(
            correlation_id,
            {"status": status, "correlation_id": str(correlation_id)},
        )
    )

    assert runtime._result is EnumWorkflowResult.FAILED


@pytest.mark.unit
def test_envelope_shaped_terminal_with_no_status_anywhere_is_refused(
    tmp_path: Path,
) -> None:
    """An envelope that declares no status is UNKNOWN — and UNKNOWN is not success.

    Symmetric with ``_terminal_correlation_matches``, which already refuses an
    envelope that names no correlation: an unattributable terminal accepted as ours
    is the same defect as a foreign one, and an unclassifiable one accepted as green
    is the same defect as a failed one.
    """
    correlation_id = uuid.uuid4()
    runtime = RuntimeLocal(
        workflow_path=tmp_path / "contract.yaml",
        state_root=tmp_path / "state",
    )

    runtime._on_terminal_event(
        _envelope(correlation_id, {"correlation_id": str(correlation_id)})
    )

    assert runtime._result is not EnumWorkflowResult.COMPLETED
    assert runtime._result is EnumWorkflowResult.FAILED
    assert "status" in (runtime.last_error or "").lower(), (
        f"refusal did not name the missing status: {runtime.last_error!r}"
    )


@pytest.mark.unit
def test_envelope_shaped_success_terminal_is_completed(tmp_path: Path) -> None:
    """Counter-assertion: a genuine envelope success still completes."""
    correlation_id = uuid.uuid4()
    runtime = RuntimeLocal(
        workflow_path=tmp_path / "contract.yaml",
        state_root=tmp_path / "state",
    )

    runtime._on_terminal_event(
        _envelope(
            correlation_id,
            {"status": "success", "correlation_id": str(correlation_id)},
        )
    )

    assert runtime._result is EnumWorkflowResult.COMPLETED


@pytest.mark.unit
def test_bare_domain_terminal_without_status_keeps_the_offline_classification(
    tmp_path: Path,
) -> None:
    """Counter-assertion: the offline path publishes bare payloads with no status.

    The single-output adapter path dumps the handler's return value directly, so a
    terminal like ``{"kind": "completed"}`` is normal and has always been COMPLETED
    via the ``_classify_result`` heuristics. Refusing it would delete the offline
    runtime, so the OMN-17567 refusal is scoped to envelope-shaped messages, which
    are structurally required to carry a domain status.
    """
    runtime = RuntimeLocal(
        workflow_path=tmp_path / "contract.yaml",
        state_root=tmp_path / "state",
    )

    runtime._on_terminal_event({"kind": "completed"})

    assert runtime._result is EnumWorkflowResult.COMPLETED


@pytest.mark.unit
def test_envelope_payload_failure_beats_an_envelope_level_success(
    tmp_path: Path,
) -> None:
    """Disagreement fails closed: a failure declared anywhere is a failure."""
    correlation_id = uuid.uuid4()
    runtime = RuntimeLocal(
        workflow_path=tmp_path / "contract.yaml",
        state_root=tmp_path / "state",
    )

    payload = _envelope(
        correlation_id,
        {"status": "failed", "correlation_id": str(correlation_id)},
    )
    payload["status"] = "success"

    runtime._on_terminal_event(payload)

    assert runtime._result is EnumWorkflowResult.FAILED
