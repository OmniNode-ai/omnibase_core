# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A degraded settle carries the count of events it read (OMN-25394, review finding 12)."""

from __future__ import annotations

import pytest

from omnibase_core.models.event_bus.model_bus_settle import ModelBusSettle
from omnibase_core.models.event_bus.model_runtime_bus_event import ModelRuntimeBusEvent


class _Bus:
    async def get_event_history(self, limit: int) -> list[object]:
        return [object(), object()]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bus_settle_carries_events_recorded_when_the_read_step_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failing control: history was read (2 events) and the read raised; events_recorded was 0."""
    monkeypatch.setattr(
        ModelRuntimeBusEvent,
        "from_message",
        classmethod(
            lambda cls, message: ModelRuntimeBusEvent(
                topic="onex.evt.omn25394.recorded.v1", value_b64="e30="
            )
        ),
    )

    def _raise(binding: object, events: object) -> object:
        raise RuntimeError("receipt step raised")

    monkeypatch.setattr(ModelBusSettle, "read", staticmethod(_raise))

    reading = await ModelBusSettle.settle(_Bus(), {"event_bus": "inmemory"})

    assert reading.degraded is True
    assert reading.events_recorded == 2
    assert reading.events_failed == 2
