# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Emits judgment and its report through the report writer (OMN-22003, AC2 and AC5).

A fixture repository config holds one bare-script hook beside one core-format hook;
the consumer reports the bare one and only the bare one, and the gap is visible in
the report written through ``NodeValidationReportWriteEffect`` with the run event and
one triggered event observed on the in-memory bus.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_validator_requirement_gap_kind import (
    EnumValidatorRequirementGapKind,
)
from omnibase_core.event_bus import event_bus_inmemory
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.nodes.requirements_consumer_check.model_requirements_consumer_check_input import (
    ModelRequirementsConsumerCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.models.validation.model_validator_triggered_event import (
    ModelValidatorTriggeredEvent,
)
from omnibase_core.nodes.node_requirements_consumer_check_compute.handler import (
    VALIDATOR_ID,
    NodeRequirementsConsumerCheckCompute,
)
from omnibase_core.nodes.node_requirements_consumer_check_compute.runtime_requirements_consumer_check import (
    main,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.topics import TopicBase

pytestmark = pytest.mark.unit

_WRITER = "NodeValidationReportWriteEffect"
_BARE = "my-validator-bare"
_CORE = "my-validator-core"


def _spec(tmp_path: Path) -> Path:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        yaml.safe_dump(
            {
                "schema_version": {"major": 1, "minor": 5, "patch": 0},
                "known_repos": [],
                "emits_check": {
                    "module_pattern": r"-m\s+([A-Za-z_][A-Za-z0-9_.]*)",
                    "core_package": "omnibase_core",
                    "writer_marker": _WRITER,
                },
                "required_validators": {
                    "my-validator": {
                        "description": "x",
                        "central_source": "x",
                        "pre_commit": "required",
                        "ci_workflow": "optional",
                        "required_check_on_main": None,
                        "silent_skip_allowed": False,
                        "applies_to_repos": "all",
                        "emits": "required",
                        "pre_commit_hook_ids": [_BARE, _CORE],
                    }
                },
            }
        )
    )
    return spec


def _repo(tmp_path: Path) -> Path:
    """One bare-script hook beside one core-format hook whose module names the writer."""
    root = tmp_path / "repo"
    package = root / "src" / "omnibase_core" / "fixture_checks"
    package.mkdir(parents=True)
    (package / "runtime_core.py").write_text(f"from x import {_WRITER}\n")
    hooks = [
        {
            "id": _BARE,
            "name": _BARE,
            "entry": "uv run python scripts/check_my_validator.py",
            "language": "system",
        },
        {
            "id": _CORE,
            "name": _CORE,
            "entry": "uv run python -m omnibase_core.fixture_checks.runtime_core",
            "language": "system",
        },
    ]
    (root / ".pre-commit-config.yaml").write_text(
        yaml.safe_dump({"repos": [{"repo": "local", "hooks": hooks}]})
    )
    return root


def _request(tmp_path: Path, *, emits: bool) -> ModelRequirementsConsumerCheckInput:
    return ModelRequirementsConsumerCheckInput(
        repo="r",
        repo_root=str(_repo(tmp_path)),
        spec_path=str(_spec(tmp_path)),
        check_emits=emits,
    )


def test_emits_reports_the_bare_script_hook_and_not_the_core_format_hook(
    tmp_path: Path,
) -> None:
    result = NodeRequirementsConsumerCheckCompute().handle(
        _request(tmp_path, emits=True)
    )
    assert [(g.kind, g.hook_id) for g in result.gaps] == [
        (EnumValidatorRequirementGapKind.NON_EMITTING_ENTRY, _BARE)
    ]


def test_emits_is_silent_when_the_check_is_not_requested(tmp_path: Path) -> None:
    result = NodeRequirementsConsumerCheckCompute().handle(
        _request(tmp_path, emits=False)
    )
    assert result.gaps == ()


def test_emits_reports_nothing_for_a_core_format_hook_alone(tmp_path: Path) -> None:
    request = _request(tmp_path, emits=True)
    config = Path(request.repo_root) / ".pre-commit-config.yaml"
    document = yaml.safe_load(config.read_text())
    document["repos"][0]["hooks"] = [
        hook for hook in document["repos"][0]["hooks"] if hook["id"] == _CORE
    ]
    config.write_text(yaml.safe_dump(document))
    assert NodeRequirementsConsumerCheckCompute().handle(request).gaps == ()


def test_emits_reports_a_core_module_whose_source_does_not_name_the_writer(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path, emits=True)
    module = (
        Path(request.repo_root) / "src/omnibase_core/fixture_checks/runtime_core.py"
    )
    module.write_text("print('no writer here')\n")
    result = NodeRequirementsConsumerCheckCompute().handle(request)
    assert {g.hook_id for g in result.gaps} == {_BARE, _CORE}


def test_emits_main_exits_two_and_names_the_gap_kind(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, spec = _repo(tmp_path), _spec(tmp_path)
    rc = main(["--repo", "r", "--repo-root", str(root), "--spec", str(spec), "--emits"])
    assert rc == 2
    assert "[NON_EMITTING_ENTRY] r :: my-validator" in capsys.readouterr().err


def test_bus_and_emits_gap_is_in_the_written_report_with_run_and_triggered_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = HandlerValidatorRuntimeOverlay()
    run_topic = handler.settings().run_topic
    listened: list[ModelEventMessage] = []

    async def _record(message: ModelEventMessage) -> None:
        listened.append(message)

    bus = EventBusInmemory()

    async def _subscribe() -> None:
        for topic in (run_topic, TopicBase.VALIDATOR_TRIGGERED):
            await bus.subscribe(topic, on_message=_record, group_id="listener")

    asyncio.run(_subscribe())
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)

    report_path = tmp_path / "out" / "report.json"
    rc = main(
        [
            "--repo",
            "r",
            "--repo-root",
            str(_repo(tmp_path)),
            "--spec",
            str(_spec(tmp_path)),
            "--emits",
            "--report-json",
            str(report_path),
            "--overlay",
            str(handler.default_overlay_path()),
        ]
    )

    assert rc == 2
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "FAIL"
    assert [(f.validator_id, f.rule_id, f.location) for f in report.findings] == [
        (
            VALIDATOR_ID,
            EnumValidatorRequirementGapKind.NON_EMITTING_ENTRY.value,
            _BARE,
        )
    ]
    runs = [
        ModelValidatorRunEvent.model_validate_json(m.value)
        for m in listened
        if m.topic == run_topic
    ]
    triggered = [
        ModelValidatorTriggeredEvent.model_validate_json(m.value)
        for m in listened
        if m.topic == TopicBase.VALIDATOR_TRIGGERED
    ]
    assert [run.report_ref for run in runs] == [report.report_id]
    assert [(t.validator_name, t.finding_count) for t in triggered] == [
        (VALIDATOR_ID, 1)
    ]
    offline = report_path.with_name(f"{report_path.name}.events.jsonl")
    assert json.loads(offline.read_text().splitlines()[0])


def test_bus_and_emits_a_clean_run_writes_a_passing_report_and_no_triggered_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = HandlerValidatorRuntimeOverlay()
    listened: list[ModelEventMessage] = []

    async def _record(message: ModelEventMessage) -> None:
        listened.append(message)

    bus = EventBusInmemory()

    async def _subscribe() -> None:
        for topic in (handler.settings().run_topic, TopicBase.VALIDATOR_TRIGGERED):
            await bus.subscribe(topic, on_message=_record, group_id="listener")

    asyncio.run(_subscribe())
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)

    root = _repo(tmp_path)
    config = root / ".pre-commit-config.yaml"
    document = yaml.safe_load(config.read_text())
    document["repos"][0]["hooks"] = [
        hook for hook in document["repos"][0]["hooks"] if hook["id"] == _CORE
    ]
    config.write_text(yaml.safe_dump(document))
    report_path = tmp_path / "report.json"
    rc = main(
        [
            "--repo",
            "r",
            "--repo-root",
            str(root),
            "--spec",
            str(_spec(tmp_path)),
            "--emits",
            "--report-json",
            str(report_path),
        ]
    )
    assert rc == 0
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "PASS"
    )
    assert [m.topic for m in listened] == [handler.settings().run_topic]
