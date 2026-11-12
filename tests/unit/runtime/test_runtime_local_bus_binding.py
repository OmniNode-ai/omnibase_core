# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""RuntimeLocal publishes where its declared bus binding says, and says so when it cannot.

The default runner is the in-memory bus; its events die with the process. A run now
carries a declared binding: a runtime-local in-memory bus whose recorded events a
forwarder (registered under ``onex.runtime_bus_forwarders``) carries to the hosted
bus, the hosted bus itself, an in-memory bus a test declared on purpose, or no binding
at all. Every run writes ``bus_reading`` into ``workflow_result.json``; an in-memory
run with no forwarder and no test declaration raises the degraded alarm (error log and
stderr line). The failing control is the missing binding: on the runtime before this
change the ``bus_reading`` key does not exist.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_runtime_bus_binding_kind import EnumRuntimeBusBindingKind
from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.models.event_bus.model_bus_settle import ModelBusSettle
from omnibase_core.models.event_bus.model_runtime_bus_binding import (
    RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP,
    ModelRuntimeBusBinding,
)
from omnibase_core.models.event_bus.model_runtime_bus_event import ModelRuntimeBusEvent
from omnibase_core.models.event_bus.model_runtime_bus_forward_receipt import (
    ModelRuntimeBusForwardReceipt,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.runtime.runtime_local import RuntimeLocal

_THIS_MODULE = "tests.unit.runtime.test_runtime_local_bus_binding"
_TERMINAL_TOPIC = "onex.evt.omn19998.bus-binding-completed.v1"
_BINDING_MODULE = "omnibase_core.models.event_bus.model_runtime_bus_binding"


class _HandlerReturnsSuccess:
    """A single handler that takes the bus, as the runtime's handlers do, and succeeds."""

    def __init__(self, event_bus: ProtocolLocalRuntimeBus) -> None:
        self._event_bus = event_bus

    async def handle(self, payload: object) -> object:
        return {"status": "success"}


class _FakeEntryPoint:
    def __init__(self, name: str, target: object) -> None:
        self.name = name
        self.value = f"fake:{name}"
        self._target = target

    def load(self) -> object:
        return self._target


class _RecordingForwarder:
    """A forwarder that records what it was handed and answers a clean receipt."""

    received: list[ModelRuntimeBusEvent] = []

    def forward(
        self, events: Sequence[ModelRuntimeBusEvent]
    ) -> ModelRuntimeBusForwardReceipt:
        type(self).received = list(events)
        return ModelRuntimeBusForwardReceipt(forwarded=len(events), failed=0)


class _RaisingForwarder:
    def forward(self, events: Sequence[ModelRuntimeBusEvent]) -> object:
        raise OSError("broker unreachable")


class _FailingReceiptForwarder:
    def forward(self, events: Sequence[ModelRuntimeBusEvent]) -> object:
        return {"forwarded": 0, "failed": 1, "detail": "refused"}


def _install_forwarders(
    monkeypatch: pytest.MonkeyPatch, *providers: _FakeEntryPoint
) -> None:
    def fake_entry_points(*, group: str) -> list[_FakeEntryPoint]:
        assert group == RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP
        return list(providers)

    monkeypatch.setattr(f"{_BINDING_MODULE}.entry_points", fake_entry_points)


_INMEMORY = {"event_bus": "inmemory"}


def _runtime(tmp_path: Path, overrides: dict[str, str]) -> tuple[RuntimeLocal, Path]:
    contract = tmp_path / "contract.yaml"
    contract.write_text(
        yaml.safe_dump(
            {
                "workflow_id": "omn-19998-bus-binding",
                "terminal_event": _TERMINAL_TOPIC,
                "event_bus": {"publish_topics": [_TERMINAL_TOPIC]},
                "handler": {
                    "module": _THIS_MODULE,
                    "class": "_HandlerReturnsSuccess",
                },
            }
        ),
        encoding="utf-8",
    )
    state_root = tmp_path / "state"
    runtime = RuntimeLocal(
        workflow_path=contract,
        state_root=state_root,
        timeout=5,
        backend_overrides=overrides,
    )
    return runtime, state_root


def _reading(state_root: Path) -> dict[str, object]:
    written = json.loads((state_root / "workflow_result.json").read_text("utf-8"))
    reading = written["bus_reading"]
    assert isinstance(reading, dict)
    return reading


@pytest.mark.unit
@pytest.mark.asyncio
async def test_forwarded_binding_hands_recorded_events_to_the_forwarder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Golden: the recorded terminal event reaches the registered forwarder, nothing alarms."""
    _RecordingForwarder.received = []
    _install_forwarders(monkeypatch, _FakeEntryPoint("fake", _RecordingForwarder))
    runtime, state_root = _runtime(tmp_path, _INMEMORY)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    assert _TERMINAL_TOPIC in {e.topic for e in _RecordingForwarder.received}
    reading = _reading(state_root)
    assert reading["kind"] == "inmemory_forwarded"
    assert reading["forwarder"] == "fake"
    assert reading["degraded"] is False
    assert reading["events_recorded"] == len(_RecordingForwarder.received) >= 1
    assert reading["events_forwarded"] == reading["events_recorded"]
    assert "DEGRADED BUS" not in capsys.readouterr().err


@pytest.mark.unit
@pytest.mark.asyncio
async def test_forwarder_that_raises_degrades_the_reading_not_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Error chain: the broker is unreachable; the run still completes and says what was lost."""
    _install_forwarders(monkeypatch, _FakeEntryPoint("fake", _RaisingForwarder))
    runtime, state_root = _runtime(tmp_path, _INMEMORY)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    reading = _reading(state_root)
    assert reading["degraded"] is True
    assert reading["events_failed"] == reading["events_recorded"] >= 1
    assert "broker unreachable" in str(reading["reason"])
    assert "DEGRADED BUS (inmemory_forwarded)" in capsys.readouterr().err


@pytest.mark.unit
@pytest.mark.asyncio
async def test_forwarder_receipt_with_failed_events_degrades_the_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Error chain: the forwarder answers a receipt (a plain mapping) that counts a failure."""
    _install_forwarders(monkeypatch, _FakeEntryPoint("fake", _FailingReceiptForwarder))
    runtime, state_root = _runtime(tmp_path, _INMEMORY)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    reading = _reading(state_root)
    assert reading["degraded"] is True
    assert reading["events_failed"] == 1
    assert reading["reason"] == "refused"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_binding_reads_unknown_and_alarms(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failing control: no binding declared reads UNKNOWN, loudly. Absent before this change."""
    runtime, state_root = _runtime(tmp_path, {})

    with caplog.at_level(logging.ERROR, logger="omnibase_core.runtime.runtime_local"):
        assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    reading = _reading(state_root)
    assert reading["kind"] == "unknown"
    assert reading["degraded"] is True
    assert reading["events_recorded"] >= 1
    assert reading["events_failed"] == reading["events_recorded"]
    assert "DEGRADED BUS (unknown)" in capsys.readouterr().err
    assert any("DEGRADED BUS" in r.getMessage() for r in caplog.records)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_declared_test_bus_is_not_degraded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A test may declare an in-memory bus with no forwarder; that is not an alarm."""
    runtime, state_root = _runtime(tmp_path, {**_INMEMORY, "forwarder": "none"})

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    reading = _reading(state_root)
    assert reading["kind"] == "inmemory_test"
    assert reading["degraded"] is False
    assert "DEGRADED BUS" not in capsys.readouterr().err


@pytest.mark.unit
@pytest.mark.asyncio
async def test_declared_inmemory_with_no_forwarder_installed_is_degraded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An in-memory runtime whose forwarder is not installed says so in the reading."""
    _install_forwarders(monkeypatch)
    runtime, state_root = _runtime(tmp_path, _INMEMORY)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    reading = _reading(state_root)
    assert reading["kind"] == "inmemory_unforwarded"
    assert reading["degraded"] is True
    assert "onex.runtime_bus_forwarders" in str(reading["reason"])


@pytest.mark.unit
def test_binding_from_overrides() -> None:
    kind = EnumRuntimeBusBindingKind
    assert ModelBusSettle.binding_from_overrides({}).kind is kind.UNKNOWN
    assert (
        ModelBusSettle.binding_from_overrides({"event_bus": "kafka"}).kind
        is kind.HOSTED
    )
    assert (
        ModelBusSettle.binding_from_overrides(
            {"event_bus": "inmemory", "forwarder": "none"}
        ).kind
        is kind.INMEMORY_TEST
    )


@pytest.mark.unit
def test_binding_shape_is_refused_when_forwarder_and_kind_disagree() -> None:
    with pytest.raises(ValidationError):
        ModelRuntimeBusBinding(kind=EnumRuntimeBusBindingKind.INMEMORY_FORWARDED)
    with pytest.raises(ValidationError):
        ModelRuntimeBusBinding(kind=EnumRuntimeBusBindingKind.HOSTED, forwarder="x")


@pytest.mark.unit
def test_two_registered_forwarders_are_never_chosen_by_install_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_forwarders(
        monkeypatch,
        _FakeEntryPoint("first", _RecordingForwarder),
        _FakeEntryPoint("second", _RecordingForwarder),
    )
    binding = ModelRuntimeBusBinding.declared_inmemory()
    assert binding.kind is EnumRuntimeBusBindingKind.INMEMORY_UNFORWARDED
    assert "first" in str(binding.reason)
    assert "second" in str(binding.reason)
