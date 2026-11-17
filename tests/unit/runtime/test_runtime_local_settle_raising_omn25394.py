# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""RuntimeLocal writes its state when any step of the bus settle raises (OMN-25394, review finding 1).

``binding_from_overrides`` and ``announce`` sat outside the guarded read, and ``bus.close()`` was
unguarded, so a raise in any of them skipped ``_write_state()`` in the ``finally`` of ``run_async``.
The failing control at head 77e2b996f23a is each raise below: the run raised and no
``workflow_result.json`` was written.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.event_bus.model_bus_settle import ModelBusSettle
from omnibase_core.models.event_bus.model_runtime_bus_reading import (
    ModelRuntimeBusReading,
)
from tests.unit.runtime.test_runtime_local_settle_guard_omn25336 import (
    _count_closes,
    _reading,
    _runtime,
)


class _SettleStepRaised(Exception):
    """An exception outside every class the settle names: the failing control."""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settle_raising_binding_still_closes_and_writes_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(overrides: object) -> object:
        raise _SettleStepRaised("binding unreadable")

    monkeypatch.setattr(ModelBusSettle, "binding_from_overrides", staticmethod(_raise))
    closes = _count_closes(monkeypatch)
    runtime, state_root = _runtime(tmp_path)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    assert closes == [1]
    reading = _reading(state_root)
    assert reading["degraded"] is True
    assert "binding unreadable" in str(reading["reason"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settle_raising_announce_still_closes_and_writes_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(reading: ModelRuntimeBusReading) -> None:
        raise _SettleStepRaised("announce failed")

    monkeypatch.setattr(ModelBusSettle, "announce", staticmethod(_raise))
    closes = _count_closes(monkeypatch)
    runtime, state_root = _runtime(tmp_path)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    assert closes == [1]
    assert "bus_reading" in json.loads(
        (state_root / "workflow_result.json").read_text("utf-8")
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settle_raising_bus_close_still_writes_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _raise(self: EventBusInmemory) -> None:
        raise _SettleStepRaised("close failed")

    monkeypatch.setattr(EventBusInmemory, "close", _raise)
    runtime, state_root = _runtime(tmp_path)

    assert await runtime.run_async() == EnumWorkflowResult.COMPLETED

    reading = _reading(state_root)
    assert reading["degraded"] is True
    assert "close failed" in str(reading["reason"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settle_raising_read_step_is_wrapped_because_the_decorator_wraps_coroutines() -> (
    None
):
    """``standard_error_handling`` wraps coroutine functions: the async read raises ModelOnexError."""
    assert inspect.iscoroutinefunction(ModelBusSettle._read_history)

    class _BusRaising:
        async def get_event_history(self, limit: int) -> list[object]:
            raise _SettleStepRaised("history unreadable")

    binding = ModelBusSettle.binding_from_overrides({"event_bus": "inmemory"})
    with pytest.raises(ModelOnexError, match="history unreadable"):
        await ModelBusSettle._read_history(_BusRaising(), binding)
