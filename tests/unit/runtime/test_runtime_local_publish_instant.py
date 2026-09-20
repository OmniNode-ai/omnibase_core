# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The published command carries the instant it reached the wire (OMN-18852).

A consumer of a command topic can only report queue wait — the time a record
spent between publish and pickup — if the producer states when it published.
``RuntimeLocal`` is the only wire producer of
``onex.cmd.omnimarket.delegate-skill.v1``, so the stamp has to happen here.

**Why the stamp is taken at the publish seam and nowhere earlier.** Between a
command model's construction and ``bus.publish`` sit the runtime's
``bus.subscribe`` calls, which on a Kafka-backed lane are real consumer-group
joins. A measured control run showed a CLI start at 20:07:58Z against its own
record published at 20:08:15Z — **17 s** of join time, against the ~3 s queue
waits this measurement is about. A stamp taken at construction would inflate
every reported queue wait by that join, and the consuming field's own contract
says an unstamped request reports queue wait as NOT MEASURED rather than zero,
precisely so a wrong measurement is never preferred to an absent one. So
:func:`test_the_stamp_is_taken_after_the_subscriptions_join` is not a detail of
the implementation — it is the property the ticket exists for, and a stamp
moved back to construction must turn it red.

**Why the seam is generic.** ``omnibase_core`` sits below ``omnimarket`` in the
layering (compat -> core -> spi -> infra, omnimarket above), so the runtime
cannot import or type against ``ModelDelegateSkillRequest``. The seam therefore
resolves the field from the published model's own ``model_fields`` — never from
a topic string or a model name. Every positive assertion below is paired with a
counter-assertion pinning what must NOT change: a model that does not declare
the field is published byte-for-byte as before, so "stamp everything" cannot
satisfy this file.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
    ProtocolLocalRuntimeMessage,
)
from omnibase_core.runtime.runtime_local import (
    PUBLISH_INSTANT_FIELD,
    RuntimeLocal,
    _stamp_publish_instant,
)

_MODULE = "tests.unit.runtime.test_runtime_local_publish_instant"

_COMMAND_TOPIC = "onex.cmd.omn18852.publish-instant.v1"
_TERMINAL_TOPIC = "onex.evt.omn18852.publish-instant-completed.v1"


# ---------------------------------------------------------------------------
# Command models. `ModelStampedCommand` is shaped like the real
# `ModelDelegateSkillRequest`: frozen, extra-forbidding, with an OPTIONAL
# timezone-aware `published_at`. `ModelPlainCommand` is the control.
# ---------------------------------------------------------------------------


class ModelStampedCommand(BaseModel):
    """Opts in to the publish instant by declaring the field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    prompt: str = Field(default="")
    published_at: datetime | None = Field(default=None)


class ModelPlainCommand(BaseModel):
    """Declares no publish instant — the control for the byte-identity case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    prompt: str = Field(default="")


class ModelWrongTypeCommand(BaseModel):
    """Declares the NAME but not the type — must not be stamped.

    ``model_copy(update=...)`` bypasses validation by design, so a name-only
    match would write a ``datetime`` into a field this model would itself have
    refused, producing a record it cannot round-trip.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    published_at: str | None = Field(default=None)


class HandlerPublishInstantEcho:
    """Host-mode handler: completes the run so the terminal wait returns."""

    async def handle(self, payload: BaseModel) -> dict[str, str]:
        correlation_id = getattr(payload, "correlation_id", uuid.uuid4())
        return {"status": "success", "correlation_id": str(correlation_id)}


# ---------------------------------------------------------------------------
# A bus double that records BOTH what was published and WHEN each subscription
# joined. The join timestamps are what make "stamped at publish, not at
# construction" observable at all: without them a construction-time stamp and a
# publish-time stamp are indistinguishable in a test that runs in microseconds.
# ---------------------------------------------------------------------------


class _RecordingMessage:
    def __init__(self, value: bytes, topic: str) -> None:
        self.value = value
        self.key: bytes | None = None
        self.topic = topic
        self.headers: dict[str, str] = {}


class _RecordingBus:
    def __init__(self, *, subscribe_delay: float = 0.0) -> None:
        self.published: list[tuple[str, bytes]] = []
        self.subscribe_completed_at: list[datetime] = []
        self._subscribe_delay = subscribe_delay
        self._subscribers: list[
            tuple[str, Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]]]
        ] = []

    @property
    def command_records(self) -> list[bytes]:
        return [value for topic, value in self.published if topic == _COMMAND_TOPIC]

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def publish(self, topic: str, key: object, value: bytes) -> object:
        self.published.append((topic, value))
        for sub_topic, on_message in list(self._subscribers):
            if sub_topic == topic:
                await on_message(_RecordingMessage(value, topic))  # type: ignore[arg-type]
        return None

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]],
        group_id: str,
    ) -> Callable[[], Awaitable[None]]:
        # Stand-in for a real consumer-group join, which is where the measured
        # 17 s between construction and publish actually goes.
        if self._subscribe_delay:
            await asyncio.sleep(self._subscribe_delay)
        registration = (topic, on_message)
        self._subscribers.append(registration)
        self.subscribe_completed_at.append(datetime.now(UTC))

        async def _unsub() -> None:
            if registration in self._subscribers:
                self._subscribers.remove(registration)

        return _unsub


def _write_contract(target: Path, *, model_name: str) -> None:
    contract: dict[str, Any] = {
        "workflow_id": "omn-18852-publish-instant",
        "name": "publish_instant_probe",
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
                        "name": "HandlerPublishInstantEcho",
                    },
                    "event_model": {"module": _MODULE, "name": model_name},
                    "output_topic": _TERMINAL_TOPIC,
                }
            ],
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")


async def _run(
    run_dir: Path,
    *,
    model_name: str,
    payload: dict[str, Any],
    bus: _RecordingBus,
) -> EnumWorkflowResult:
    run_dir.mkdir(parents=True, exist_ok=True)
    contract_path = run_dir / "contract.yaml"
    input_path = run_dir / "input.json"
    _write_contract(contract_path, model_name=model_name)
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=run_dir / "state",
        input_path=input_path,
        timeout=5,
        host_handlers=True,
    )
    runtime._create_event_bus = lambda: bus  # type: ignore[assignment,method-assign]
    return await runtime.run_async()


def _decode_command(bus: _RecordingBus) -> dict[str, Any]:
    assert len(bus.command_records) == 1, (
        f"expected exactly one command record, got {len(bus.command_records)}"
    )
    decoded: dict[str, Any] = json.loads(bus.command_records[0])
    return decoded


# ---------------------------------------------------------------------------
# The stamp itself.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_model_declaring_the_field_is_published_with_a_tz_aware_stamp(
    tmp_path: Path,
) -> None:
    """A declaring model reaches the wire carrying a timezone-aware UTC instant."""
    correlation_id = uuid.uuid4()
    bus = _RecordingBus()

    before = datetime.now(UTC)
    result = await _run(
        tmp_path / "stamped",
        model_name="ModelStampedCommand",
        payload={"correlation_id": str(correlation_id), "prompt": "probe"},
        bus=bus,
    )
    after = datetime.now(UTC)

    assert result == EnumWorkflowResult.COMPLETED
    record = _decode_command(bus)
    raw_stamp = record.get(PUBLISH_INSTANT_FIELD)
    # `is not None`, not merely `in record`: before this change the field
    # serialised as an explicit null on every request, so key presence alone
    # would be satisfied by the unstamped behaviour this test must refuse.
    assert isinstance(raw_stamp, str), (
        f"the declaring model reached the wire with no publish instant: {raw_stamp!r}"
    )
    stamped = datetime.fromisoformat(raw_stamp)
    # The consuming validator refuses a naive datetime outright, so a naive
    # stamp would be a dead-lettered record rather than a wrong number.
    assert stamped.tzinfo is not None, "publish instant must be timezone-aware"
    assert stamped.utcoffset() == timedelta(0), "publish instant must be UTC"
    assert before <= stamped <= after, (
        f"stamp {stamped} is outside the run window {before}..{after}"
    )
    # Nothing else about the record moved.
    assert record["correlation_id"] == str(correlation_id)
    assert record["prompt"] == "probe"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_the_stamp_is_taken_after_the_subscriptions_join(
    tmp_path: Path,
) -> None:
    """The instant is the WIRE instant, not the construction instant.

    This is the whole point of the ticket. The runtime joins its consumer
    groups between building the command model and publishing it; on a live
    Kafka lane that took 17 s. A stamp taken at construction is therefore wrong
    by the join time on every single request, and this test is the falsifier:
    move the stamp back to ``_build_initial_payload`` and it goes red, because
    the stamp would precede the last subscription rather than follow it.
    """
    bus = _RecordingBus(subscribe_delay=0.05)

    result = await _run(
        tmp_path / "ordering",
        model_name="ModelStampedCommand",
        payload={"correlation_id": str(uuid.uuid4()), "prompt": "probe"},
        bus=bus,
    )

    assert result == EnumWorkflowResult.COMPLETED
    assert bus.subscribe_completed_at, (
        "the runtime joined no consumer group — this test would pass vacuously"
    )
    last_join = max(bus.subscribe_completed_at)
    raw_stamp = _decode_command(bus).get(PUBLISH_INSTANT_FIELD)
    assert isinstance(raw_stamp, str), (
        f"no publish instant to order against the joins: {raw_stamp!r}"
    )
    stamped = datetime.fromisoformat(raw_stamp)
    assert stamped >= last_join, (
        f"publish instant {stamped} precedes the last subscription join "
        f"{last_join}: the stamp was taken before the joins, which is the "
        "measurement error OMN-18852 exists to prevent"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_caller_supplied_instant_is_preserved_verbatim(
    tmp_path: Path,
) -> None:
    """A caller that stated its own publish instant wins; the seam does not overwrite."""
    supplied = datetime(2026, 9, 19, 12, 34, 56, tzinfo=UTC)
    bus = _RecordingBus()

    result = await _run(
        tmp_path / "supplied",
        model_name="ModelStampedCommand",
        payload={
            "correlation_id": str(uuid.uuid4()),
            "prompt": "probe",
            PUBLISH_INSTANT_FIELD: supplied.isoformat(),
        },
        bus=bus,
    )

    assert result == EnumWorkflowResult.COMPLETED
    raw_stamp = _decode_command(bus).get(PUBLISH_INSTANT_FIELD)
    assert isinstance(raw_stamp, str), f"caller value lost: {raw_stamp!r}"
    stamped = datetime.fromisoformat(raw_stamp)
    assert stamped == supplied, (
        f"caller-supplied instant {supplied} was overwritten with {stamped}"
    )


# ---------------------------------------------------------------------------
# Counter-assertions: what must NOT change.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_model_without_the_field_is_published_byte_identically(
    tmp_path: Path,
) -> None:
    """Every model that does not declare the field serialises exactly as before.

    Compared against the model's own ``model_dump_json()`` rather than a
    hand-written expectation, so the assertion is byte equality with what this
    runtime published before the change, not a restatement of it.
    """
    correlation_id = uuid.uuid4()
    bus = _RecordingBus()

    result = await _run(
        tmp_path / "plain",
        model_name="ModelPlainCommand",
        payload={"correlation_id": str(correlation_id), "prompt": "probe"},
        bus=bus,
    )

    assert result == EnumWorkflowResult.COMPLETED
    expected = (
        ModelPlainCommand(correlation_id=correlation_id, prompt="probe")
        .model_dump_json()
        .encode("utf-8")
    )
    assert bus.command_records[0] == expected, (
        "a model that declares no publish instant changed on the wire"
    )
    assert PUBLISH_INSTANT_FIELD not in json.loads(bus.command_records[0])


@pytest.mark.unit
def test_a_field_of_the_right_name_but_the_wrong_type_is_not_stamped() -> None:
    """The seam matches on the annotation, not merely on the field name."""
    original = ModelWrongTypeCommand(correlation_id=uuid.uuid4())
    returned = _stamp_publish_instant(original)
    assert returned is original, (
        "a non-datetime field sharing the name was stamped; model_copy bypasses "
        "validation, so this would put an un-round-trippable value on the wire"
    )


@pytest.mark.unit
def test_a_non_pydantic_payload_is_returned_untouched() -> None:
    """There is nothing to resolve a field from on a non-model payload."""
    payload = object()
    assert _stamp_publish_instant(payload) is payload


@pytest.mark.unit
def test_the_seam_does_not_mutate_the_model_it_was_handed() -> None:
    """The stamp is a copy; the caller's own instance is unchanged.

    The command models on this path are frozen, and the runtime reads the
    pre-stamp instance for its correlation id before publishing.
    """
    original = ModelStampedCommand(correlation_id=uuid.uuid4())
    stamped = _stamp_publish_instant(original)
    assert stamped is not original
    assert original.published_at is None
    assert isinstance(stamped, ModelStampedCommand)
    assert stamped.published_at is not None
    assert stamped.published_at.tzinfo is not None
