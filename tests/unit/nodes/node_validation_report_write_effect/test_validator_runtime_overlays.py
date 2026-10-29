# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The validator-runtime overlay pair and the hook-run default report path (OMN-21529).

The in-memory overlay and the Redpanda overlay differ only in the bus binding. The same
fixture run on both, on one commit, yields reports equal to the committed golden report
once the run id and the timestamps are normalised, and each run puts exactly one run
event carrying the report's run id on the bus the overlay binds. The Redpanda overlay
is bound here to a recording bus, because the broker client lives in another package
and a unit test never reaches a broker; the lab run drives the same overlay against a
live broker (``tests/integration/validation/lab``).
"""

from __future__ import annotations

import asyncio
import json
import shutil
import types
from pathlib import Path
from typing import cast

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
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
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
    main_for_reference,
)
from omnibase_core.topics import TopicBase
from omnibase_core.validation.validator_hook_writes import ValidatorHookWrites

pytestmark = pytest.mark.unit

_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_REDPANDA = _NODE / "overlays/validator_runtime.redpanda.overlay.yaml"
_ROOT = Path(__file__).resolve().parents[4]
_FIXTURES = _ROOT / "tests/fixtures/validation/hook_writes"
_PLANTED = _FIXTURES / "violation_hook_writes_fix_flag.yaml"
_GOLDEN = _FIXTURES / "golden_hook_writes_fix_flag.json"
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


def _run(
    overlay_path: Path, report: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ModelONEXContainer, int]:
    monkeypatch.chdir(_ROOT)
    containers: list[ModelONEXContainer] = []

    def _factory(overlay: ModelValidatorRuntimeOverlay) -> ModelONEXContainer:
        containers.append(build_validator_container(overlay))
        return containers[-1]

    exit_code = main(
        ValidatorHookWrites,
        [
            str(_PLANTED),
            "--report-json",
            str(report),
            "--overlay",
            str(overlay_path),
        ],
        _factory,
    )
    return containers[0], exit_code


def test_the_overlay_pair_differs_only_in_the_bus_binding() -> None:
    inmemory = yaml.safe_load(_INMEMORY.read_text(encoding="utf-8"))
    redpanda = yaml.safe_load(_REDPANDA.read_text(encoding="utf-8"))

    assert {key for key in inmemory if inmemory[key] != redpanda.get(key)} == {"bus"}
    assert set(inmemory) == set(redpanda)
    assert inmemory["bus"] != redpanda["bus"]


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
    container, exit_code = _run(_INMEMORY, report, monkeypatch)

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
    assert [t for t, _k, _v in _RecordingBus.published].count(
        TopicBase.VALIDATOR_TRIGGERED
    ) == 1


def test_an_unset_broker_fails_the_redpanda_bind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_BROKER_ENV, raising=False)
    monkeypatch.setattr(
        handler_validator_runtime_overlay.importlib,
        "import_module",
        lambda _name: types.SimpleNamespace(EventBusKafka=_RecordingBus),
    )

    with pytest.raises(ModelOnexError, match="expands to nothing"):
        _HANDLER.bind_bus(_HANDLER.load(_REDPANDA))


def _overlay_text(**changes: object) -> str:
    overlay = yaml.safe_load(_REDPANDA.read_text(encoding="utf-8"))
    for dotted, value in changes.items():
        node = overlay
        *parents, leaf = dotted.split("__")
        for parent in parents:
            node = node[parent]
        if value is None:
            node.pop(leaf)
        else:
            node[leaf] = value
    return yaml.safe_dump(overlay)


@pytest.mark.parametrize(
    "changes",
    [
        {"name": None},
        {"profile": None},
        {"bus": None},
        {"bus__implementation": None},
        {"bus__implementation": "not a module class"},
        {"stray": "key"},
        {"bus__stray": "key"},
    ],
)
def test_an_invalid_overlay_fails_to_load(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    path = tmp_path / "overlay.yaml"
    path.write_text(_overlay_text(**changes), encoding="utf-8")

    with pytest.raises(ModelOnexError, match="invalid"):
        _HANDLER.load(path)


def test_every_overlay_key_changes_what_the_runtime_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        handler_validator_runtime_overlay.importlib,
        "import_module",
        lambda _name: types.SimpleNamespace(
            Alpha=_RecordingBus, EventBusKafka=_RecordingBus
        ),
    )
    monkeypatch.setenv(_BROKER_ENV, _BROKER)
    base = _HANDLER.load(_REDPANDA)
    profile = tmp_path / "profile.yaml"
    profile.write_text(_overlay_text(profile="strict"), encoding="utf-8")
    implementation = tmp_path / "implementation.yaml"
    implementation.write_text(
        _overlay_text(bus__implementation="package.module:Alpha"), encoding="utf-8"
    )

    assert _HANDLER.load(profile).profile != base.profile
    assert _HANDLER.load(implementation).bus.implementation != base.bus.implementation
    _RecordingBus.bootstrap = []
    _HANDLER.bind_bus(_HANDLER.load(implementation))
    assert _RecordingBus.bootstrap == [_BROKER]
    constructor = tmp_path / "constructor.yaml"
    constructor.write_text(_overlay_text(bus__constructor="absent"), encoding="utf-8")
    with pytest.raises(ModelOnexError, match="cannot be bound"):
        _HANDLER.bind_bus(_HANDLER.load(constructor))
    _RecordingBus.bootstrap = []
    _HANDLER.bind_bus(base)
    assert _RecordingBus.bootstrap == [_BROKER]
    monkeypatch.setenv(_BROKER_ENV, "other-broker:9092")
    _HANDLER.bind_bus(base)
    assert _RecordingBus.bootstrap == [_BROKER, "other-broker:9092"]


def test_an_invalid_settings_file_fails_to_load(tmp_path: Path) -> None:
    settings = tmp_path / "settings.yaml"
    settings.write_text("default_overlay: x.yaml\n", encoding="utf-8")

    with pytest.raises(ModelOnexError):
        _HANDLER.settings(settings)


def test_the_settings_name_the_default_overlay_and_the_contract_the_topics() -> None:
    contract = yaml.safe_load((_NODE / "contract.yaml").read_text(encoding="utf-8"))

    assert _HANDLER.default_overlay_path() == _INMEMORY
    assert set(contract["event_bus"]["publish_topics"]) == {
        _RUN_TOPIC,
        TopicBase.VALIDATOR_TRIGGERED,
    }


def test_a_hook_run_that_omits_report_json_still_finds_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / _PLANTED.name
    shutil.copy(_PLANTED, target)
    monkeypatch.chdir(tmp_path)
    reference = "omnibase_core.validation.validator_hook_writes:ValidatorHookWrites"

    exit_code = main_for_reference([reference, str(target)])

    expected = tmp_path / _HANDLER.settings().default_report_path.format(
        validator_id=ValidatorHookWrites.validator_id
    )
    assert exit_code == 1
    assert expected.is_file()
    assert json.loads(expected.read_text(encoding="utf-8"))["overall_status"] == "FAIL"
