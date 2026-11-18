# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""RuntimeLocal always closes its bus and writes its state when settling the bus fails (OMN-25336).

``ModelBusSettle.settle`` runs in the ``finally`` of ``run_async``. A forwarder or an event read
that raises something outside the forward failures it expected (a bare ``Exception``) used to
leave the ``finally`` unfinished: ``bus.close()`` and ``_write_state()`` were skipped and the
exception replaced the run's result. The failing control is the bare exception: on the runtime
before this change the run raises and no ``workflow_result.json`` is written.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.event_bus.model_runtime_bus_binding import (
    RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP,
)
from omnibase_core.models.event_bus.model_runtime_bus_event import ModelRuntimeBusEvent
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.runtime.runtime_local import RuntimeLocal

_THIS_MODULE = "tests.unit.runtime.test_runtime_local_settle_guard_omn25336"
_TERMINAL_TOPIC = "onex.evt.omn25336.settle-guard-completed.v1"
_BINDING_MODULE = "omnibase_core.models.event_bus.model_runtime_bus_binding"
_INMEMORY = {"event_bus": "inmemory"}


class _HandlerReturnsSuccess:
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


class _OutsideForwardFailures(Exception):
    """An exception outside every class ``_FORWARD_FAILURES`` names: the settle's failing control."""


class _BareExceptionForwarder:
    def forward(self, events: Sequence[ModelRuntimeBusEvent]) -> object:
        raise _OutsideForwardFailures("forwarder blew up")


def _runtime(tmp_path: Path) -> tuple[RuntimeLocal, Path]:
    contract = tmp_path / "contract.yaml"
    contract.write_text(
        yaml.safe_dump(
            {
                "workflow_id": "omn-25336-settle-guard",
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
        backend_overrides=_INMEMORY,
    )
    return runtime, state_root


def _count_closes(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    closes: list[int] = []
    original = EventBusInmemory.close

    async def _counting_close(self: EventBusInmemory) -> None:
        closes.append(1)
        await original(self)

    monkeypatch.setattr(EventBusInmemory, "close", _counting_close)
    return closes


def _reading(state_root: Path) -> dict[str, object]:
    written = json.loads((state_root / "workflow_result.json").read_text("utf-8"))
    reading = written["bus_reading"]
    assert isinstance(reading, dict)
    return reading


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settle_bare_exception_from_forwarder_reads_degraded_and_still_closes_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Error chain: a bare Exception in the forwarder is a degraded reading, never a lost run."""
    monkeypatch.setattr(
        f"{_BINDING_MODULE}.entry_points",
        lambda *, group: (
            [_FakeEntryPoint("fake", _BareExceptionForwarder)]
            if group == RUNTIME_BUS_FORWARDER_ENTRY_POINT_GROUP
            else []
        ),
    )
    closes = _count_closes(monkeypatch)
    runtime, state_root = _runtime(tmp_path)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    assert closes == [1]
    reading = _reading(state_root)
    assert reading["degraded"] is True
    assert "forwarder blew up" in str(reading["reason"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settle_bare_exception_from_event_history_reads_degraded_and_still_closes_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Error chain: the event-history read raises outside the forward failures."""

    async def _broken_history(
        self: EventBusInmemory, *args: object, **kw: object
    ) -> list[object]:
        raise _OutsideForwardFailures("history unreadable")

    monkeypatch.setattr(EventBusInmemory, "get_event_history", _broken_history)
    closes = _count_closes(monkeypatch)
    runtime, state_root = _runtime(tmp_path)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    assert closes == [1]
    reading = _reading(state_root)
    assert reading["degraded"] is True
    assert "history unreadable" in str(reading["reason"])
