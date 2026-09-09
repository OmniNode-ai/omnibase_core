# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The handler-path correlation refusal on ``LocalRuntimeBusAdapter`` (OMN-15660).

OMN-15660 names two legs. The TERMINAL leg landed in ``omnibase_core#1645``:
``RuntimeLocal._terminal_correlation_matches`` refuses a terminal that names
another run. The HANDLER leg had no equivalent — ``on_message`` read
``correlation_id`` and used it for logging only, with no conditional between
deserialize and invoke, so a message belonging to a concurrent invocation was
executed as this invocation's own input.

Group-id uniqueness cannot substitute for the refusal and the ticket says so:
Kafka fans every record to every consumer group, so a run-scoped group still
observes every other run's records. The group id bounds which records this run
is *served*; the refusal is what decides which it *acts on*.

Every refusal assertion here is paired with a counter-assertion pinning what the
refusal must NOT destroy — an unarmed adapter, and a message that declares no
correlation at all. Refusing those two would satisfy a naive "isolate
everything" reading while making the offline path and every def-B chain
unrunnable, which is the OMN-17980 regression already paid for once on the
terminal leg.
"""

from __future__ import annotations

import json
from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
    ProtocolLocalRuntimeCallableTarget,
)
from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter

_OUTPUT_TOPIC = "onex.evt.omn15660.handler-refusal.v1"


class ModelRefusalCommand(BaseModel):
    """Input model that carries a correlation, like every wire command."""

    model_config = ConfigDict(extra="forbid")

    correlation_id: UUID | None = None
    prompt: str = ""


class _RecordingHandler:
    """Records every input it was actually invoked on."""

    def __init__(self) -> None:
        self.invocations: list[object] = []

    def handle(self, request: object) -> None:
        self.invocations.append(request)


class _FakeBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []

    async def start(self) -> None:  # pragma: no cover - unused
        return None

    async def close(self) -> None:  # pragma: no cover - unused
        return None

    async def publish(self, topic: str, key: object, value: bytes) -> object:
        self.published.append((topic, value))
        return None

    async def subscribe(
        self, topic: str, *, on_message: object, group_id: str
    ) -> object:  # pragma: no cover - unused
        return None


class _FakeMsg:
    def __init__(self, value: bytes) -> None:
        self.value = value


def _adapter(
    handler: _RecordingHandler,
    *,
    expected_correlation_id: UUID | None,
    input_model_cls: type[BaseModel] | None = ModelRefusalCommand,
) -> LocalRuntimeBusAdapter:
    return LocalRuntimeBusAdapter(
        handler=cast("ProtocolLocalRuntimeCallableTarget", handler),
        handler_name="omn15660-refusal-probe",
        input_model_cls=input_model_cls,
        output_topic=_OUTPUT_TOPIC,
        bus=cast("ProtocolLocalRuntimeBus", _FakeBus()),
        expected_correlation_id=expected_correlation_id,
    )


def _msg(payload: dict[str, object]) -> _FakeMsg:
    return _FakeMsg(json.dumps(payload).encode("utf-8"))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_foreign_correlation_is_not_invoked_on() -> None:
    """The defect, stated directly: another run's input must not be executed.

    RED before the fix: ``on_message`` had no conditional between deserialize and
    invoke, so this handler recorded the sibling's command.
    """
    handler = _RecordingHandler()
    mine, theirs = uuid4(), uuid4()
    adapter = _adapter(handler, expected_correlation_id=mine)

    await adapter.on_message(cast("object", _msg({"correlation_id": str(theirs)})))  # type: ignore[arg-type]

    assert handler.invocations == [], (
        "the handler executed a command belonging to correlation "
        f"{theirs} while this invocation awaits {mine}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_this_runs_own_correlation_is_invoked_on() -> None:
    """Counter-assertion: the refusal must still let this run's own input through."""
    handler = _RecordingHandler()
    mine = uuid4()
    adapter = _adapter(handler, expected_correlation_id=mine)

    await adapter.on_message(cast("object", _msg({"correlation_id": str(mine)})))  # type: ignore[arg-type]

    assert len(handler.invocations) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_an_unarmed_adapter_invokes_on_anything() -> None:
    """Counter-assertion: no predicate armed means no operand to filter on.

    The offline / in-memory path publishes commands that never carried a
    correlation onto a wire. Refusing there would break it for no isolation gain
    — an in-memory bus dies with its process and has no second run to collide
    with.
    """
    handler = _RecordingHandler()
    adapter = _adapter(handler, expected_correlation_id=None)

    await adapter.on_message(cast("object", _msg({"correlation_id": str(uuid4())})))  # type: ignore[arg-type]

    assert len(handler.invocations) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_message_declaring_no_correlation_is_invoked_on() -> None:
    """Counter-assertion, and the OMN-17980 lesson applied to the handler leg.

    The canonical def-B message is the handler's bare domain model, which has no
    field in which to carry a correlation id. Refusing an undeclared correlation
    would make every def-B chain stall after its first hop — the exact regression
    the terminal leg shipped and had to fix.
    """
    handler = _RecordingHandler()
    adapter = _adapter(handler, expected_correlation_id=uuid4())

    await adapter.on_message(cast("object", _msg({"prompt": "no correlation here"})))  # type: ignore[arg-type]

    assert len(handler.invocations) == 1, (
        "a bare def-B domain payload was refused; that breaks every def-B chain "
        "rather than isolating anything"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_foreign_correlation_inside_an_envelope_is_refused() -> None:
    """The envelope shape carries the correlation at the top, not in the payload.

    ``_unwrap_envelope_dict`` is what the adapter already uses to find it, so the
    refusal must read the unwrapped value or the fan-out wire shape would slip
    past unchecked.
    """
    handler = _RecordingHandler()
    mine, theirs = uuid4(), uuid4()
    adapter = _adapter(handler, expected_correlation_id=mine)

    envelope: dict[str, object] = {
        "envelope_id": str(uuid4()),
        "correlation_id": str(theirs),
        "event_type": "omn15660.refusal-probe",
        "payload": {"prompt": "someone else's work"},
    }
    await adapter.on_message(cast("object", _msg(envelope)))  # type: ignore[arg-type]

    assert handler.invocations == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_refusal_is_not_reported_as_a_handler_failure() -> None:
    """A sibling's record is not this run's failure.

    Routing the refusal through ``on_error`` would mark the workflow FAILED the
    moment any concurrent invocation published, turning an isolation fix into a
    concurrency outage.
    """
    handler = _RecordingHandler()
    errors: list[int] = []
    adapter = LocalRuntimeBusAdapter(
        handler=cast("ProtocolLocalRuntimeCallableTarget", handler),
        handler_name="omn15660-refusal-probe",
        input_model_cls=ModelRefusalCommand,
        output_topic=_OUTPUT_TOPIC,
        bus=cast("ProtocolLocalRuntimeBus", _FakeBus()),
        on_error=lambda: errors.append(1),
        expected_correlation_id=uuid4(),
    )

    await adapter.on_message(cast("object", _msg({"correlation_id": str(uuid4())})))  # type: ignore[arg-type]

    assert handler.invocations == []
    assert errors == [], "a foreign record marked this run's workflow FAILED"
