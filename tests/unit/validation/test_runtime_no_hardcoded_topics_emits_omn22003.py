# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The topics hook persists every verdict without changing its CLI output."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_no_hardcoded_topics_check_compute.runtime_no_hardcoded_topics_check import (
    VALIDATOR_ID,
    main,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.validation.validator_no_hardcoded_topics import (
    ValidatorNoHardcodedTopics,
    load_rules,
)

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "occ_hardcoded_topics"


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
    target = tmp_path / "service.py"
    fixture = "positive-control-py.txt" if violating else "pass-clean-py.txt"
    target.write_text(
        (_FIXTURES / fixture).read_text(encoding="utf-8"), encoding="utf-8"
    )
    report_path = tmp_path / "r.json"
    handler = HandlerValidatorRuntimeOverlay()

    assert main(
        [
            str(target),
            "--report-json",
            str(report_path),
            "--overlay",
            str(handler.default_overlay_path()),
        ]
    ) == (1 if violating else 0)

    output = capsys.readouterr()
    report = _read_report(report_path)
    assert report.overall_status == ("FAIL" if violating else "PASS")
    assert len(report.findings) == (2 if violating else 0)
    rules = load_rules(ValidatorNoHardcodedTopics().contract)
    if violating:
        assert all(f.validator_id == VALIDATOR_ID for f in report.findings)
        assert all(f.severity == "FAIL" for f in report.findings)
        assert all(f.rule_id == rules.validator_name for f in report.findings)
        assert [f.location for f in report.findings] == [
            f"{target}:45",
            f"{target}:46",
        ]
        assert output.out == "".join(f"{f.message}\n" for f in report.findings) + (
            f"\n2 violation(s). {rules.remediation}\n"
        )
    else:
        assert output.out == ""
    assert output.err == ""


def test_unreadable_file_emits_runtime_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "r.json"
    assert main([str(tmp_path / "missing.py"), "--report-json", str(report_path)]) == 1
    report = _read_report(report_path)
    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    output = capsys.readouterr()
    assert output.out == f"ERROR: {report.findings[0].message}\n"
    assert output.err == ""


def test_no_files_emits_to_settings_default(
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
    assert output.out == output.err == ""
