# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The event-chain runtime on the in-memory default and on the Redpanda overlay (OMN-21558, KC-c).

The ticket's own fixture set runs twice on one commit: once on the in-memory default and once
with the Redpanda overlay, bound here to a recording bus because a unit test never reaches a
broker. Both reports equal the committed golden report once the run id and the timestamp are
normalised, and each run puts exactly one run event carrying the report's run id on the bus the
overlay binds. The overlay file is the only difference between the two runs. The live-broker
run of the same fixture set is the lab run (``tests/integration/validation/lab``).
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
from omnibase_core.validation.validator_event_chain_walker import (
    ValidatorEventChainWalker,
)

pytestmark = pytest.mark.unit

_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_REDPANDA = _NODE / "overlays/validator_runtime.redpanda.overlay.yaml"
_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "tests/fixtures/validation/event_chain_walker"
_GOLDEN = _FIXTURES / "golden_event_chain_walker.json"
_PLANTED = (
    "event_without_consumer",
    "consumer_without_producer",
    "state_without_exit",
    "transition_on_undeclared_event",
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


def _normalised(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    report["report_id"] = _NORMALISED
    report["provenance"]["generated_at"] = _NORMALISED
    return cast(dict[str, object], report)


def _golden() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_GOLDEN.read_text(encoding="utf-8")))


def _stage(root: Path) -> list[str]:
    """Copy the planted fixtures to ``root/src/pkg`` as node contracts; return their paths."""
    target = root / "src/pkg"
    target.mkdir(parents=True)
    paths = []
    for rule_id in _PLANTED:
        source = _FIXTURES / f"violation_{rule_id}.contract.yaml"
        copy = target / f"violation_{rule_id}.contract.yaml"
        shutil.copy(source, copy)
        paths.append(str(copy.relative_to(root)))
    return sorted(paths)


def _run(
    overlay_path: Path,
    report: Path,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ModelONEXContainer, int]:
    monkeypatch.chdir(root)
    containers: list[ModelONEXContainer] = []

    def _factory(overlay: ModelValidatorRuntimeOverlay) -> ModelONEXContainer:
        containers.append(build_validator_container(overlay))
        return containers[-1]

    exit_code = main(
        ValidatorEventChainWalker,
        [*_stage(root), "--report-json", str(report), "--overlay", str(overlay_path)],
        _factory,
    )
    return containers[0], exit_code


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
    _container, exit_code = _run(_INMEMORY, report, tmp_path, monkeypatch)

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
    _container, exit_code = _run(_REDPANDA, report, tmp_path, monkeypatch)

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
