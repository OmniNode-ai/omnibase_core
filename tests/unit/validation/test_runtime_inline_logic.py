# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime tests of the inline-logic validator: the report writer and the bus come from the container (OMN-21534).

The checker is pure and the validator reads; the runtime resolves the report-writing EFFECT
and the validator-runtime bus from the container with ``get_service`` and never builds
them. A container spy records both resolutions, and the report of the ticket's own fixture
set equals the committed golden report once the run id and the timestamps are normalised.
The overlay pair half of this file runs the same fixture set on the in-memory overlay and
on the Redpanda overlay (bound to a recording bus), on one commit, with the overlay file
the only difference.
"""

from __future__ import annotations

import asyncio
import json
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
from omnibase_core.validation.validator_inline_logic import ValidatorInlineLogic

pytestmark = pytest.mark.unit

_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_REDPANDA = _NODE / "overlays/validator_runtime.redpanda.overlay.yaml"
_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "tests/fixtures/validation/inline_logic"
_TARGETS = sorted(_FIXTURES.glob("violation_*"))
_GOLDEN = _FIXTURES / "golden_inline_logic.json"
_NORMALISED = "<normalised>"
_BROKER_ENV = "KAFKA_BOOTSTRAP_SERVERS"
_BROKER = "broker-fixture:9092"
_REPOSITORY = "example-repository"
_HANDLER = HandlerValidatorRuntimeOverlay()
_PROFILE = _HANDLER.load(_HANDLER.default_overlay_path()).profile
_RUN_TOPIC = _HANDLER.settings().run_topic


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


def _normalised(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    report["report_id"] = _NORMALISED
    report["provenance"]["generated_at"] = _NORMALISED
    return cast(dict[str, object], report)


def _golden() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_GOLDEN.read_text(encoding="utf-8")))


def _run(
    overlay_path: Path, report: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ModelONEXContainer, int]:
    monkeypatch.chdir(_ROOT)
    containers: list[ModelONEXContainer] = []

    def _factory(overlay: ModelValidatorRuntimeOverlay) -> ModelONEXContainer:
        containers.append(build_validator_container(overlay))
        return containers[-1]

    exit_code = main(
        ValidatorInlineLogic,
        [
            *(str(target) for target in _TARGETS),
            "--report-json",
            str(report),
            "--overlay",
            str(overlay_path),
        ],
        _factory,
    )
    return containers[0], exit_code


def test_the_fixture_set_holds_one_violation_per_rule() -> None:
    assert [target.name for target in _TARGETS] == [
        "violation_inline_loop.yml",
        "violation_inline_program.yaml",
        "violation_inline_python.yml",
        "violation_run_block_length.yml",
    ]


def test_runtime_resolves_the_report_writer_and_the_bus_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)
    inner = build_validator_container()
    resolved: list[type] = []
    real_get_service = inner.get_service

    def _recording(protocol_type: type, service_name: str | None = None) -> object:
        resolved.append(protocol_type)
        return real_get_service(protocol_type, service_name)

    monkeypatch.setattr(inner, "get_service", _recording)
    spy = _SpyContainer(inner)
    report_path = tmp_path / "report.json"
    result = run_validator(
        cast(ModelONEXContainer, spy),
        ValidatorInlineLogic(),
        _TARGETS,
        str(report_path),
        _PROFILE,
        _REPOSITORY,
    )
    assert not result.is_valid
    assert spy.resolved == [NodeValidationReportWriteEffect]
    assert resolved == [NodeValidationReportWriteEffect, ModelValidatorRuntimeBus]
    assert _normalised(report_path) == _golden()


def test_the_in_memory_run_equals_the_golden_report_and_one_run_event_is_observed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listened: list[ModelEventMessage] = []

    async def _record(message: ModelEventMessage) -> None:
        listened.append(message)

    bus = EventBusInmemory()
    asyncio.run(bus.subscribe(_RUN_TOPIC, on_message=_record, group_id="listener"))
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)

    report = tmp_path / "report.json"
    _container, exit_code = _run(_INMEMORY, report, monkeypatch)

    assert exit_code == 1
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

    report = tmp_path / "report.json"
    _container, exit_code = _run(_REDPANDA, report, monkeypatch)

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
