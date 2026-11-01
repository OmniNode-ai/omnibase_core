# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The invariant-analysis runtime on both overlays of one commit (OMN-21565, KC-c).

The checker's own planted plan fixtures run twice with the generic validator runtime: once on the
in-memory overlay and once on the Redpanda overlay, with no code change and the overlay file the
only difference. Both reports equal the committed golden report once the run id and the
timestamps are normalised, and each run puts exactly one run event carrying the report's run id on
the bus its overlay binds. The Redpanda overlay is bound to a recording bus here because the broker
client lives in another package.
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
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_overlay import (
    ModelValidatorRuntimeOverlay,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_validation_report_write_effect import (
    handler_validator_runtime_overlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation.validator_invariant_analysis import (
    ValidatorInvariantAnalysis,
)

pytestmark = pytest.mark.unit

_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_REDPANDA = _NODE / "overlays/validator_runtime.redpanda.overlay.yaml"
_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/invariant_analysis"
_GOLDEN = _FIXTURES / "golden_report.json"
_PLAN_RULES = (
    "scope_declaration_missing_or_unknown",
    "invariant_unaddressed",
    "satisfied_by_task_absent",
    "not_applicable_unreasoned",
    "invariant_unknown_or_retired",
)
_NORMALISED = "<normalised>"
_BROKER_ENV = "KAFKA_BOOTSTRAP_SERVERS"
_BROKER = "broker-fixture:9092"
_HANDLER = HandlerValidatorRuntimeOverlay()
_RUN_TOPIC = _HANDLER.settings().run_topic


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


def _workdir(root: Path) -> Path:
    """The planted plan and its repository configuration in a fresh directory."""
    root.mkdir(parents=True, exist_ok=True)
    for name in ("registry.yaml", "lifecycle.yaml", "plan_bad.md"):
        shutil.copy(_FIXTURES / name, root / name)
    shutil.copy(_FIXTURES / "overlay.yaml", root / "invariant_analysis.overlay.yaml")
    return root


def _normalised(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    report["report_id"] = _NORMALISED
    report["provenance"]["generated_at"] = _NORMALISED
    return cast(dict[str, object], report)


def _golden() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_GOLDEN.read_text(encoding="utf-8")))


def _run(
    overlay_path: Path, work: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, int]:
    monkeypatch.chdir(_workdir(work))
    report = work / "report.json"

    def _factory(overlay: ModelValidatorRuntimeOverlay) -> ModelONEXContainer:
        return build_validator_container(overlay)

    exit_code = main(
        ValidatorInvariantAnalysis,
        [str(work), "--report-json", str(report), "--overlay", str(overlay_path)],
        _factory,
    )
    return report, exit_code


def test_the_golden_report_names_every_planted_rule() -> None:
    findings = cast(list[dict[str, str]], _golden()["findings"])
    assert {finding["rule_id"] for finding in findings} == set(_PLAN_RULES)


def test_the_in_memory_run_equals_the_golden_report_and_one_run_event_is_observed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listened: list[ModelEventMessage] = []

    async def _record(message: ModelEventMessage) -> None:
        listened.append(message)

    bus = EventBusInmemory()
    asyncio.run(bus.subscribe(_RUN_TOPIC, on_message=_record, group_id="listener"))
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)

    report, exit_code = _run(_INMEMORY, tmp_path, monkeypatch)

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

    report, exit_code = _run(_REDPANDA, tmp_path, monkeypatch)

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


def test_purity_runtime_resolves_writer_and_bus_from_container(tmp_path, monkeypatch):
    from unittest.mock import patch

    from omnibase_core.handlers.handler_invariant_analysis import (
        HandlerInvariantAnalysis,
    )
    from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
        ModelValidatorRuntimeBus,
    )
    from omnibase_core.nodes.node_validation_report_write_effect.handler import (
        NodeValidationReportWriteEffect,
    )
    from omnibase_core.validation.validator_invariant_analysis import (
        build_analysis_container,
    )

    resolved = []
    original = ModelONEXContainer.get_service

    def spy(self, service_type):
        resolved.append(service_type)
        return original(self, service_type)

    with patch.object(ModelONEXContainer, "get_service", spy):
        _run(_INMEMORY, tmp_path, monkeypatch)
    assert NodeValidationReportWriteEffect in resolved
    assert ModelValidatorRuntimeBus in resolved
    # A preconstructed request proves evaluating a document never resolves services.
    from tests.unit.validation.test_invariant_analysis import request

    req = request()
    handler = HandlerInvariantAnalysis(build_analysis_container())
    with patch.object(
        ModelONEXContainer,
        "get_service",
        side_effect=AssertionError("handler resolved container"),
    ):
        assert handler.handle(req).findings
