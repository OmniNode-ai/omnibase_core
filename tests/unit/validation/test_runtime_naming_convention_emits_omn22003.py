# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Every naming convention verdict leaves a report and events (OMN-22003)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_naming_convention_check_compute.runtime_naming_convention_check import (
    VALIDATOR_ID,
    main,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _restore_root_logging() -> Iterator[None]:
    """The runtime calls logging.basicConfig(force=True), which binds a root handler to the
    captured stderr of the test; undo it so later tests in the process see their own."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


@pytest.mark.parametrize(
    ("clean", "warning_mode", "exit_code"),
    [(False, False, 1), (True, False, 0), (False, True, 0)],
)
def test_verdict_report_and_events(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    clean: bool,
    warning_mode: bool,
    exit_code: int,
) -> None:
    directory = tmp_path / "omnibase_core" / "models"
    directory.mkdir(parents=True)
    source = directory / ("model_user.py" if clean else "user.py")
    source.touch()
    report_path = tmp_path / "r.json"
    args = [
        str(directory),
        "--report-json",
        str(report_path),
        "--overlay",
        str(HandlerValidatorRuntimeOverlay().default_overlay_path()),
    ]
    if warning_mode:
        args.append("--warning-mode")

    assert main(args) == exit_code

    assert report_path.is_file()
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == ("PASS" if clean else "FAIL")
    assert report.profile == "default"
    assert report.provenance.validators_run == (VALIDATOR_ID,)
    assert Path(f"{report_path}.events.jsonl").is_file()
    output = capsys.readouterr()
    assert output.out == ""
    expected = f"Checking naming conventions in: {directory}\n{'-' * 60}\n"
    if clean:
        assert report.findings == ()
        expected += "All files conform to naming conventions!\n"
    else:
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.validator_id == VALIDATOR_ID
        assert finding.severity == "FAIL"
        assert finding.location == str(source)
        assert finding.rule_id is None
        assert finding.message == (
            "File 'user.py' in 'models/' directory must start with 'model_'"
        )
        expected += (
            f"Found 1 naming convention violation(s):\n  {source}: {finding.message}\n"
        )
        if warning_mode:
            expected += "Warning mode enabled; not failing on violations.\n"
    assert output.err == expected


def test_runtime_error_report_and_events(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "missing"
    report_path = tmp_path / "r.json"
    assert (
        main(
            [
                str(directory),
                "--report-json",
                str(report_path),
                "--overlay",
                str(HandlerValidatorRuntimeOverlay().default_overlay_path()),
            ]
        )
        == 1
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert report.findings[0].validator_id == VALIDATOR_ID
    assert report.findings[0].message == f"Directory not found: {directory}"
    assert Path(f"{report_path}.events.jsonl").is_file()
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == f"Directory not found: {directory}\n"


def test_default_report_and_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main([str(tmp_path)]) == 0
    report_path = Path(
        HandlerValidatorRuntimeOverlay()
        .settings()
        .default_report_path.format(validator_id=VALIDATOR_ID)
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "PASS"
    assert Path(f"{report_path}.events.jsonl").is_file()
