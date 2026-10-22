# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the validator-triggered event emitter (OMN-21277, AC3).

RULING 2026-10-14T20:01:09Z: validators emit a bus event when they trigger.
A canonical ValidationReport with FAIL or ERROR findings yields exactly one
``onex.evt.platform.validator-triggered.v1`` event per validator that
triggered, published through the event bus abstraction; WARN and PASS
validators publish nothing.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

import pytest

from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.handlers.handler_validator_triggered_emit import (
    HandlerValidatorTriggeredEmit,
)
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_input import (
    ModelValidatorTriggeredEmitInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.models.validation.model_validator_triggered_event import (
    ModelValidatorTriggeredEvent,
)
from omnibase_core.topics import TopicBase

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_CORRELATION = UUID("00000000-0000-4000-8000-000000000001")


def _finding(
    validator_id: str, severity: Literal["WARN", "FAIL", "ERROR"], location: str
) -> ModelValidationFindingEmbed:
    return ModelValidationFindingEmbed(
        validator_id=validator_id,
        severity=severity,
        location=location,
        message=f"{location}: {severity}",
    )


def _report(
    *findings: ModelValidationFindingEmbed, run: tuple[str, ...]
) -> ModelValidationReport:
    return ModelValidationReport.from_findings(
        findings=findings,
        request=ModelValidationRequestRef(profile="default"),
        validators_run=run,
    )


def _input(report: ModelValidationReport) -> ModelValidatorTriggeredEmitInput:
    return ModelValidatorTriggeredEmitInput(
        report=report,
        repository="omnibase_core",
        pull_request=2071,
        head_sha="a" * 40,
        correlation_id=_CORRELATION,
    )


async def _history(bus: EventBusInmemory) -> list[ModelValidatorTriggeredEvent]:
    messages = await bus.get_event_history(topic=TopicBase.VALIDATOR_TRIGGERED)
    return [ModelValidatorTriggeredEvent.model_validate_json(m.value) for m in messages]


async def test_one_event_per_triggered_validator() -> None:
    bus = EventBusInmemory()
    await bus.start()
    report = _report(
        _finding("alpha", "FAIL", "a.py:1"),
        _finding("alpha", "FAIL", "a.py:2"),
        _finding("beta", "ERROR", "b.py"),
        _finding("gamma", "WARN", "c.py"),
        run=("alpha", "beta", "gamma", "delta"),
    )

    output = await HandlerValidatorTriggeredEmit(bus.publish).handle(_input(report))

    events = await _history(bus)
    assert [e.validator_name for e in events] == ["alpha", "beta"]
    assert output.events == tuple(events)
    alpha, beta = events
    assert alpha.severity == "FAIL"
    assert alpha.finding_count == 2
    assert alpha.locations == ("a.py:1", "a.py:2")
    assert beta.severity == "ERROR"
    assert {e.repository for e in events} == {"omnibase_core"}
    assert {e.pull_request for e in events} == {2071}
    assert {e.correlation_id for e in events} == {_CORRELATION}


async def test_error_outranks_fail_for_one_validator() -> None:
    bus = EventBusInmemory()
    await bus.start()
    report = _report(
        _finding("alpha", "FAIL", "a.py:1"),
        _finding("alpha", "ERROR", "a.py"),
        run=("alpha",),
    )

    await HandlerValidatorTriggeredEmit(bus.publish).handle(_input(report))

    events = await _history(bus)
    assert [(e.validator_name, e.severity, e.finding_count) for e in events] == [
        ("alpha", "ERROR", 2)
    ]


async def test_passing_and_warning_report_publishes_nothing() -> None:
    bus = EventBusInmemory()
    await bus.start()
    report = _report(_finding("gamma", "WARN", "c.py"), run=("gamma", "delta"))

    output = await HandlerValidatorTriggeredEmit(bus.publish).handle(_input(report))

    assert output.events == ()
    assert await bus.get_event_history() == []


async def test_event_key_is_the_validator_id() -> None:
    bus = EventBusInmemory()
    await bus.start()
    report = _report(_finding("alpha", "FAIL", "a.py:1"), run=("alpha",))

    await HandlerValidatorTriggeredEmit(bus.publish).handle(_input(report))

    (message,) = await bus.get_event_history(topic=TopicBase.VALIDATOR_TRIGGERED)
    assert message.key == b"alpha"
