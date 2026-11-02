# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ticket-format verdicts always leave canonical reports and run events (OMN-22003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_todo_format_check_effect.handler_todo_format import (
    TICKET_FORMAT,
    check_file,
)
from omnibase_core.nodes.node_todo_format_check_effect.runtime_todo_format import (
    VALIDATOR_ID,
    main,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("violating", [True, False])
def test_verdict_report_and_events_preserve_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], violating: bool
) -> None:
    source = tmp_path / "sample.py"
    marker = "TO" + "DO"
    source.write_text(
        f"# {marker}: first\n# {marker}: second\n"
        if violating
        else f"# {marker}(OMN-22003): tracked\n",
        encoding="utf-8",
    )
    findings = check_file(str(source))
    report_path = tmp_path / "r.json"
    handler = HandlerValidatorRuntimeOverlay()

    assert main(
        [
            str(source),
            "--report-json",
            str(report_path),
            "--overlay",
            str(handler.default_overlay_path()),
        ]
    ) == (1 if violating else 0)

    captured = capsys.readouterr()
    expected = "".join(f"{finding.format()}\n" for finding in findings)
    if findings:
        expected += f"\n{len(findings)} violation(s). Use format: {TICKET_FORMAT}\n"
    assert captured.out == expected
    assert captured.err == ""
    assert report_path.is_file()
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == ("FAIL" if violating else "PASS")
    assert report.profile == handler.load(handler.default_overlay_path()).profile
    assert report.provenance.validators_run == (VALIDATOR_ID,)
    assert len(report.findings) == len(findings)
    for embedded, finding in zip(report.findings, findings, strict=True):
        assert embedded.validator_id == VALIDATOR_ID
        assert embedded.severity == "FAIL"
        assert embedded.location == f"{finding.path}:{finding.line}"
        assert embedded.message == finding.message
        assert embedded.rule_id is None

    events_path = report_path.with_name(f"{report_path.name}.events.jsonl")
    assert events_path.is_file()
    events = [
        ModelValidatorRunEvent.model_validate_json(line)
        for line in events_path.read_text().splitlines()
    ]
    assert len(events) == 1 + len(findings)
    assert events[0].kind == "run"
    assert events[0].verdict == report.overall_status
    assert all(event.report_ref == report.report_id for event in events)


def test_empty_run_writes_settings_default_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    report_path = Path(
        HandlerValidatorRuntimeOverlay()
        .settings()
        .default_report_path.format(validator_id=VALIDATOR_ID)
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report_path.with_name(f"{report_path.name}.events.jsonl").is_file()
