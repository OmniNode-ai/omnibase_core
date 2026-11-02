# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The duplicate IDs hook persists every verdict with its original CLI behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_duplicate_config_ids_check_compute.runtime_duplicate_config_ids_check import (
    VALIDATOR_ID,
    main,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)

pytestmark = pytest.mark.unit


def _read_report(path: Path) -> ModelValidationReport:
    assert path.is_file()
    report = ModelValidationReport.model_validate_json(path.read_text(encoding="utf-8"))
    events_path = path.with_name(f"{path.name}.events.jsonl")
    assert events_path.is_file()
    events = [
        ModelValidatorRunEvent.model_validate_json(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
    ]
    assert events[0].kind == "run"
    assert events[0].verdict == report.overall_status
    assert events[0].report_ref == report.report_id
    assert len(events) == 1 + len(report.findings)
    assert report.provenance.validators_run == (VALIDATOR_ID,)
    return report


@pytest.mark.parametrize("violating", [True, False])
def test_verdict_and_events(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], violating: bool
) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "registries:\n  - path: reg.yaml\n    list_path: entries\n    id_field: id\n",
        encoding="utf-8",
    )
    registry = tmp_path / "reg.yaml"
    registry.write_text(
        "entries:\n  - id: a\n  - id: a\n"
        if violating
        else "entries:\n  - id: a\n  - id: b\n",
        encoding="utf-8",
    )
    report_path = tmp_path / "r.json"
    handler = HandlerValidatorRuntimeOverlay()

    assert main(
        [
            "--manifest",
            str(manifest),
            "--repo-root",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--overlay",
            str(handler.default_overlay_path()),
        ]
    ) == (1 if violating else 0)

    output = capsys.readouterr()
    report = _read_report(report_path)
    assert report.overall_status == ("FAIL" if violating else "PASS")
    if violating:
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.validator_id == VALIDATOR_ID
        assert finding.severity == "FAIL"
        assert finding.location == "reg.yaml"
        assert finding.rule_id is None
        assert "duplicate id='a'" in finding.message
        assert output.out == (
            f"reg.yaml: {finding.message}\n\n1 duplicate-id registry violation(s).\n"
        )
    else:
        assert report.findings == ()
        assert output.out == "No duplicate-id registry violations found.\n"
    assert output.err == ""


def test_malformed_manifest_emits_runtime_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("wrong_key: []\n", encoding="utf-8")
    report_path = tmp_path / "r.json"
    assert main(["--manifest", str(manifest), "--report-json", str(report_path)]) == 1
    report = _read_report(report_path)
    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    output = capsys.readouterr()
    assert output.out == f"FAIL: {report.findings[0].message}\n"
    assert output.err == ""


def test_no_manifest_emits_to_settings_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    path = Path(
        HandlerValidatorRuntimeOverlay()
        .settings()
        .default_report_path.format(validator_id=VALIDATOR_ID)
    )
    report = _read_report(path)
    assert report.overall_status == "PASS"
    assert report.findings == ()
    output = capsys.readouterr()
    assert output.out == (
        "No manifest at .duplicate-id-registries.yaml — "
        "no registries opted in, nothing to check.\n"
    )
    assert output.err == ""
