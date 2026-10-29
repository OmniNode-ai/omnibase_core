# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime tests of the handler-shape validator: the writer and the bus come from the container (OMN-21536).

The checker is pure and the validator reads; the runtime resolves the report-writing
EFFECT and the validator-runtime bus from the container with ``get_service`` and never
builds them. A container spy records both resolutions. The ticket's own fixture set
then runs on the in-memory overlay and on the Redpanda overlay (bound to a recording
bus, because a unit test never reaches a broker), both reports equal the committed
golden report once the run id and the timestamps are normalised, and each run puts
exactly one run event carrying the report's run id on the bus its overlay binds. The
live-broker run of the same overlay is ``tests/integration/validation/lab``.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import types
from pathlib import Path
from typing import cast

import pytest

from omnibase_core.event_bus import event_bus_inmemory
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_overlay import (
    ModelValidatorRuntimeOverlay,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_validation_report_write_effect import (
    handler_validator_runtime_overlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
    run_validator,
)
from omnibase_core.validation.validator_handler_shape import ValidatorHandlerShape

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "tests/fixtures/validation/handler_shape"
_GOLDEN = _FIXTURES / "golden_report.json"
_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_REDPANDA = _NODE / "overlays/validator_runtime.redpanda.overlay.yaml"
_NORMALISED = "<normalised>"
_BROKER_ENV = "KAFKA_BOOTSTRAP_SERVERS"
_BROKER = "broker-fixture:9092"
_HANDLER = HandlerValidatorRuntimeOverlay()
_RUN_TOPIC = _HANDLER.settings().run_topic
_REPOSITORY = "example-repository"
_PROFILE = _HANDLER.load(_HANDLER.default_overlay_path()).profile


class _RecordingBus:
    """Stands in for the broker bus the Redpanda overlay names; records what is published."""

    published: list[tuple[str, bytes | None, bytes]] = []
    bootstrap: list[str] = []

    @classmethod
    def from_bootstrap(cls, bootstrap: str) -> _RecordingBus:
        cls.bootstrap.append(bootstrap)
        return cls()

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def publish(self, topic: str, key: bytes | None, value: bytes) -> None:
        self.published.append((topic, key, value))


def _stage(work: Path) -> list[Path]:
    """The ticket's fixture set: every planted violation, under a handler module name."""
    for fixture in sorted(_FIXTURES.glob("violation_*.py")):
        shutil.copy(
            fixture, work / f"handler_{fixture.name.removeprefix('violation_')}"
        )
    return sorted(work.glob("handler_*.py"))


def _normalised(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    report["report_id"] = _NORMALISED
    report["provenance"]["generated_at"] = _NORMALISED
    return cast(dict[str, object], report)


def _golden() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_GOLDEN.read_text(encoding="utf-8")))


def _run(
    overlay_path: Path, work: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ModelONEXContainer, int, Path]:
    targets = _stage(work)
    monkeypatch.chdir(work)
    containers: list[ModelONEXContainer] = []
    report = work / "report.json"

    def _factory(overlay: ModelValidatorRuntimeOverlay) -> ModelONEXContainer:
        containers.append(build_validator_container(overlay))
        return containers[-1]

    exit_code = main(
        ValidatorHandlerShape,
        [
            *(str(t) for t in targets),
            "--report-json",
            str(report),
            "--overlay",
            str(overlay_path),
        ],
        _factory,
    )
    return containers[0], exit_code, report


def test_runtime_resolves_the_writer_and_the_bus_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: a container spy records the resolution of the writer and of the bus."""
    container = build_validator_container()
    resolved: list[type] = []
    real_get_service = container.get_service

    def _spy(protocol_type: type, service_name: str | None = None) -> object:
        resolved.append(protocol_type)
        return real_get_service(protocol_type, service_name)

    monkeypatch.setattr(container, "get_service", _spy)
    targets = _stage(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = run_validator(
        container,
        ValidatorHandlerShape(),
        targets,
        str(tmp_path / "report.json"),
        _PROFILE,
        _REPOSITORY,
    )

    assert not result.is_valid
    assert resolved == [NodeValidationReportWriteEffect, ModelValidatorRuntimeBus]


def test_the_in_memory_run_equals_the_golden_report_and_one_run_event_is_observed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listened: list[ModelEventMessage] = []

    async def _record(message: ModelEventMessage) -> None:
        listened.append(message)

    bus = EventBusInmemory()
    asyncio.run(bus.subscribe(_RUN_TOPIC, on_message=_record, group_id="listener"))
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)

    container, exit_code, report = _run(_INMEMORY, tmp_path, monkeypatch)

    assert exit_code == 1
    assert container.get_service(ModelValidatorRuntimeBus).publish == bus.publish
    assert _normalised(report) == _golden()
    runs = [ModelValidatorRunEvent.model_validate_json(m.value) for m in listened]
    written = json.loads(report.read_text(encoding="utf-8"))
    assert [run.report_ref for run in runs] == [written["report_id"]]


def test_the_redpanda_run_equals_the_golden_report_and_one_run_event_is_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    redpanda = _HANDLER.load(_REDPANDA)
    module_name, _, class_name = redpanda.bus.implementation.partition(":")
    fake_module = types.SimpleNamespace(**{class_name: _RecordingBus})
    real_import = handler_validator_runtime_overlay.importlib.import_module
    monkeypatch.setattr(
        handler_validator_runtime_overlay.importlib,
        "import_module",
        lambda name: fake_module if name == module_name else real_import(name),
    )
    monkeypatch.setenv(_BROKER_ENV, _BROKER)
    _RecordingBus.published, _RecordingBus.bootstrap = [], []

    _container, exit_code, report = _run(_REDPANDA, tmp_path, monkeypatch)

    assert exit_code == 1
    assert _RecordingBus.bootstrap == [_BROKER]
    assert _normalised(report) == _golden()
    written = json.loads(report.read_text(encoding="utf-8"))
    run_events = [
        ModelValidatorRunEvent.model_validate_json(value)
        for topic, _key, value in _RecordingBus.published
        if topic == _RUN_TOPIC
    ]
    assert [run.report_ref for run in run_events] == [written["report_id"]]
