# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A forwarder receipt that does not account for every recorded event reads degraded (OMN-25336).

``ModelBusSettle.read`` used to read ``degraded`` as ``receipt.failed > 0``, so a receipt of
``forwarded=0, failed=0`` for N recorded events read healthy while nothing was carried. The failing
control is that receipt: it reads degraded only once forwarded must equal the recorded count.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from omnibase_core.enums.enum_runtime_bus_binding_kind import EnumRuntimeBusBindingKind
from omnibase_core.models.event_bus.model_bus_settle import ModelBusSettle
from omnibase_core.models.event_bus.model_runtime_bus_binding import (
    ModelRuntimeBusBinding,
)
from omnibase_core.models.event_bus.model_runtime_bus_event import ModelRuntimeBusEvent
from omnibase_core.models.event_bus.model_runtime_bus_forward_receipt import (
    ModelRuntimeBusForwardReceipt,
)
from omnibase_core.models.event_bus.model_runtime_bus_reading import (
    ModelRuntimeBusReading,
)


def _events(count: int) -> tuple[ModelRuntimeBusEvent, ...]:
    return tuple(
        ModelRuntimeBusEvent(topic=f"onex.evt.omn25336.{i}.v1", value_b64="e30=")
        for i in range(count)
    )


def _read(
    monkeypatch: pytest.MonkeyPatch, forwarded: int, failed: int, recorded: int
) -> ModelRuntimeBusReading:
    receipt = ModelRuntimeBusForwardReceipt(forwarded=forwarded, failed=failed)

    def _load_forward(
        self: ModelRuntimeBusBinding,
    ) -> Callable[[Sequence[ModelRuntimeBusEvent]], object]:
        return lambda events: receipt

    monkeypatch.setattr(ModelRuntimeBusBinding, "load_forward", _load_forward)
    binding = ModelRuntimeBusBinding(
        kind=EnumRuntimeBusBindingKind.INMEMORY_FORWARDED, forwarder="fake"
    )
    return ModelBusSettle.read(binding, _events(recorded))


@pytest.mark.unit
def test_bus_settle_degraded_when_receipt_forwarded_nothing_and_failed_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failing control: forwarded=0 failed=0 for 3 events must not read healthy."""
    reading = _read(monkeypatch, forwarded=0, failed=0, recorded=3)
    assert reading.degraded is True
    assert reading.events_recorded == 3
    assert reading.events_forwarded == 0
    assert reading.events_failed == 3
    assert reading.reason is not None
    assert "0 of 3" in reading.reason


@pytest.mark.unit
@pytest.mark.parametrize(
    ("forwarded", "failed", "recorded"),
    [(2, 0, 3), (4, 0, 3), (3, 1, 3), (2, 1, 3)],
)
def test_bus_settle_degraded_when_receipt_does_not_equal_the_recorded_count(
    monkeypatch: pytest.MonkeyPatch, forwarded: int, failed: int, recorded: int
) -> None:
    assert _read(monkeypatch, forwarded, failed, recorded).degraded is True


@pytest.mark.unit
def test_bus_settle_degraded_is_false_only_when_forwarded_equals_the_recorded_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive control: a receipt that carries all 3 events reads healthy."""
    reading = _read(monkeypatch, forwarded=3, failed=0, recorded=3)
    assert reading.degraded is False
    assert reading.events_forwarded == 3
    assert reading.events_failed == 0
