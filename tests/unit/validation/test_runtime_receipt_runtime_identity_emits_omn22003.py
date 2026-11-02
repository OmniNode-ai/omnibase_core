# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Every receipt runtime-identity verdict leaves a report and events (OMN-22003)."""

from __future__ import annotations

import json
import logging
import platform
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_receipt_runtime_identity_check_compute.runtime_receipt_runtime_identity_check import (
    VALIDATOR_ID,
    main,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.validation.validator_receipt_runtime_identity import (
    DEFAULT_REQUIRED_PACKAGES,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _logging_level(caplog: pytest.LogCaptureFixture) -> None:
    """Restore the default CLI level after naming CLI tests configure the root logger."""
    caplog.set_level(logging.WARNING)


def _receipt(tmp_path: Path, *, clean: bool) -> Path:
    payload: dict[str, object] = {
        "skill_name": "delegate",
        "node_name": "node_delegate_skill_orchestrator",
        "status": "success",
        "run_id": "0f0f0f0f-0000-4000-8000-000000000000",
        "schema_version": {"major": 1, "minor": 1, "patch": 0},
    }
    if clean:
        payload["runtime_identity"] = {
            "host": platform.node(),
            "packages": {
                name: {"name": name, "source": "absent"}
                for name in DEFAULT_REQUIRED_PACKAGES
            },
        }
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize("clean", [False, True])
def test_verdict_report_and_events(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], clean: bool
) -> None:
    receipt = _receipt(tmp_path, clean=clean)
    report_path = tmp_path / "r.json"
    overlay = HandlerValidatorRuntimeOverlay().default_overlay_path()

    assert main(
        [str(receipt), "--report-json", str(report_path), "--overlay", str(overlay)]
    ) == (0 if clean else 1)

    assert report_path.is_file()
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == ("PASS" if clean else "FAIL")
    assert report.profile == "default"
    assert report.provenance.validators_run == (VALIDATOR_ID,)
    assert Path(f"{report_path}.events.jsonl").is_file()
    output = capsys.readouterr()
    assert output.err == ""
    if clean:
        assert report.findings == ()
        assert output.out == (
            "RUNTIME IDENTITY GATE PASSED: 0 violations across "
            "1 receipt(s) in 1 JSON file(s) under 1 explicit file(s)\n"
        )
    else:
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.validator_id == VALIDATOR_ID
        assert finding.severity == "FAIL"
        assert finding.location == str(receipt)
        assert finding.rule_id == "missing_identity"
        assert output.out == (
            "RUNTIME IDENTITY GATE FAILED: 1 violation(s) in 1 explicit file(s):\n\n"
            f"  [missing_identity] {receipt}\n"
            f"    {finding.message}\n\n"
        )


@pytest.mark.parametrize("missing_directory", [False, True])
def test_runtime_error_report_and_events(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], missing_directory: bool
) -> None:
    report_path = tmp_path / "r.json"
    args = [
        "--report-json",
        str(report_path),
        "--overlay",
        str(HandlerValidatorRuntimeOverlay().default_overlay_path()),
    ]
    if missing_directory:
        args.extend(["--receipts-dir", str(tmp_path / "missing")])
    assert main(args) == (1 if missing_directory else 2)
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert report.findings[0].validator_id == VALIDATOR_ID
    output = capsys.readouterr()
    assert output.out == ""
    assert report.findings[0].message in output.err
    assert "--report-json" not in output.err
    assert "--overlay" not in output.err
    assert Path(f"{report_path}.events.jsonl").is_file()


def test_default_report_and_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    receipt = _receipt(tmp_path, clean=True)
    assert main([str(receipt)]) == 0
    report_path = Path(
        HandlerValidatorRuntimeOverlay()
        .settings()
        .default_report_path.format(validator_id=VALIDATOR_ID)
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "PASS"
    assert Path(f"{report_path}.events.jsonl").is_file()
