# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The report writer publishes through a container-resolved bus (OMN-21529).

A run with three failing validators puts one run event and three
validator-triggered events on the bus the container supplies; a run with none puts the
run event alone. A container spy records that the writer resolved the bus from the
container rather than building one, an in-memory listener counts what arrived, and
``events.jsonl`` stays the offline copy. A writer that builds its own bus, or that
publishes nothing, fails these tests.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import cast

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_output import (
    ModelValidationReportWriteOutput,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_settings import (
    ModelValidatorRuntimeSettings,
)
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_input import (
    ModelValidatorTriggeredEmitInput,
)
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_output import (
    ModelValidatorTriggeredEmitOutput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.models.validation.model_validator_run_events import (
    ModelValidatorRunEvents,
)
from omnibase_core.models.validation.model_validator_triggered_event import (
    ModelValidatorTriggeredEvent,
)
from omnibase_core.nodes.node_validation_report_write_effect._report_writer_interface import (
    ValidationReportWriterInterface,
)
from omnibase_core.nodes.node_validation_report_write_effect._run_events_interface import (
    ValidatorRunEventsInterface,
)
from omnibase_core.nodes.node_validation_report_write_effect._triggered_emitter_interface import (
    ValidatorTriggeredEmitterInterface,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validation_report_publish import (
    NodeValidationReportPublishEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_run_events import (
    HandlerValidatorRunEvents,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_triggered_emit import (
    HandlerValidatorTriggeredEmit,
)
from omnibase_core.topics import TopicBase

pytestmark = pytest.mark.unit

_FAILING = ("arch-alpha", "arch-beta", "arch-gamma")
_REPOSITORY = "example-repository"
_RUN_TOPIC = HandlerValidatorRuntimeOverlay().settings().run_topic


class _SpyContainer:
    """Records every type resolved through ``get_service`` and delegates to a container."""

    def __init__(self, inner: ModelONEXContainer) -> None:
        self._inner = inner
        self.resolved: list[type] = []

    def get_service(
        self, protocol_type: type, service_name: str | None = None
    ) -> object:
        self.resolved.append(protocol_type)
        return self._inner.get_service(protocol_type, service_name)


class _Listener:
    """An in-memory listener counting the events of every topic the writer publishes."""

    def __init__(self) -> None:
        self.messages: dict[str, list[ModelEventMessage]] = {}

    async def subscribe_to(self, bus: EventBusInmemory) -> None:
        for topic in (_RUN_TOPIC, TopicBase.VALIDATOR_TRIGGERED):
            await bus.subscribe(topic, on_message=self._record, group_id="listener")

    async def _record(self, message: ModelEventMessage) -> None:
        self.messages.setdefault(message.topic, []).append(message)

    def count(self, topic: str) -> int:
        return len(self.messages.get(topic, []))


def _container_with_bus(
    listener: _Listener | None = None,
) -> tuple[ModelONEXContainer, EventBusInmemory, _Listener]:
    bus = EventBusInmemory()
    listener = listener or _Listener()
    container = ModelONEXContainer(enable_service_registry=True)

    async def _compose() -> None:
        await container.service_registry.register_instance(
            ModelValidatorRuntimeBus,
            ModelValidatorRuntimeBus(
                start=bus.start, publish=bus.publish, close=bus.close
            ),
        )
        await container.service_registry.register_instance(
            ModelValidatorRuntimeSettings, HandlerValidatorRuntimeOverlay().settings()
        )
        await container.service_registry.register_instance(
            cast(
                "type[ValidationReportWriterInterface[ModelValidationReportWriteInput, ModelValidationReportWriteOutput]]",
                ValidationReportWriterInterface,
            ),
            NodeValidationReportWriteEffect(),
        )
        await container.service_registry.register_instance(
            cast(
                "type[ValidatorRunEventsInterface[ModelValidationReport, ModelValidatorRunEvents]]",
                ValidatorRunEventsInterface,
            ),
            HandlerValidatorRunEvents(),
        )
        await container.service_registry.register_instance(
            cast(
                "type[ValidatorTriggeredEmitterInterface[ModelValidatorTriggeredEmitInput, ModelValidatorTriggeredEmitOutput]]",
                ValidatorTriggeredEmitterInterface,
            ),
            HandlerValidatorTriggeredEmit(bus.publish),
        )
        await listener.subscribe_to(bus)

    asyncio.run(_compose())
    return container, bus, listener


def _report(failing: tuple[str, ...]) -> ModelValidationReport:
    findings = tuple(
        ModelValidationFindingEmbed(
            validator_id=validator,
            severity="FAIL",
            location=f"{validator}.py:1",
            message=f"{validator}: planted violation",
        )
        for validator in failing
    )
    return ModelValidationReport.from_findings(
        findings=findings,
        request=ModelValidationRequestRef(profile="default"),
        validators_run=failing or ("arch-alpha",),
    )


def _write(
    container: object, report: ModelValidationReport, target: Path
) -> NodeValidationReportPublishEffect:
    writer = NodeValidationReportPublishEffect(cast(ModelONEXContainer, container))
    writer.handle(
        ModelValidationReportWriteInput(
            report_path=str(target), report=report, repository=_REPOSITORY
        )
    )
    return writer


def test_three_failing_validators_put_three_triggered_and_one_run_event_on_the_bus(
    tmp_path: Path,
) -> None:
    container, _bus, listener = _container_with_bus()
    spy = _SpyContainer(container)
    report = _report(_FAILING)

    _write(spy, report, tmp_path / "report.json")

    assert spy.resolved == [
        ValidationReportWriterInterface,
        ValidatorRunEventsInterface,
        ValidatorTriggeredEmitterInterface,
        ModelValidatorRuntimeSettings,
        ModelValidatorRuntimeBus,
    ]
    assert listener.count(TopicBase.VALIDATOR_TRIGGERED) == 3
    assert listener.count(_RUN_TOPIC) == 1
    run = ModelValidatorRunEvent.model_validate_json(
        listener.messages[_RUN_TOPIC][0].value
    )
    assert (run.kind, run.report_ref, run.verdict) == ("run", report.report_id, "FAIL")
    triggered = {
        ModelValidatorTriggeredEvent.model_validate_json(message.value).validator_name
        for message in listener.messages[TopicBase.VALIDATOR_TRIGGERED]
    }
    assert triggered == set(_FAILING)


def test_a_run_with_no_failing_validator_puts_the_run_event_alone_on_the_bus(
    tmp_path: Path,
) -> None:
    container, _bus, listener = _container_with_bus()
    spy = _SpyContainer(container)

    _write(spy, _report(()), tmp_path / "report.json")

    assert spy.resolved == [
        ValidationReportWriterInterface,
        ValidatorRunEventsInterface,
        ValidatorTriggeredEmitterInterface,
        ModelValidatorRuntimeSettings,
        ModelValidatorRuntimeBus,
    ]
    assert listener.count(TopicBase.VALIDATOR_TRIGGERED) == 0
    assert listener.count(_RUN_TOPIC) == 1


def test_events_jsonl_stays_the_offline_copy_beside_the_published_events(
    tmp_path: Path,
) -> None:
    container, _bus, _listener = _container_with_bus()
    target = tmp_path / "report.json"

    _write(container, _report(_FAILING), target)

    lines = [
        json.loads(line)
        for line in (tmp_path / "report.json.events.jsonl").read_text().splitlines()
    ]
    assert [line["kind"] for line in lines] == ["run", "fire", "fire", "fire"]


def test_the_two_runs_are_told_apart_by_run_id(tmp_path: Path) -> None:
    first_container, _bus, listener = _container_with_bus()
    second_container, _bus, _same = _container_with_bus(listener)
    first, second = _report(_FAILING), _report(())

    _write(first_container, first, tmp_path / "first.json")
    _write(second_container, second, tmp_path / "second.json")

    refs = [
        ModelValidatorRunEvent.model_validate_json(message.value).report_ref
        for message in listener.messages[_RUN_TOPIC]
    ]
    assert refs == [first.report_id, second.report_id]


def test_a_writer_with_no_container_writes_the_offline_copy_and_publishes_nothing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "report.json"

    output = NodeValidationReportWriteEffect().handle(
        ModelValidationReportWriteInput(
            report_path=str(target), report=_report(_FAILING)
        )
    )

    assert output.events_written == 4
    assert output.events_published == 0


def test_failing_validators_without_a_repository_refuse_to_publish(
    tmp_path: Path,
) -> None:
    container, _bus, listener = _container_with_bus()

    with pytest.raises(ModelOnexError, match="repository"):
        NodeValidationReportPublishEffect(container).handle(
            ModelValidationReportWriteInput(
                report_path=str(tmp_path / "report.json"), report=_report(_FAILING)
            )
        )

    assert listener.count(TopicBase.VALIDATOR_TRIGGERED) == 0
