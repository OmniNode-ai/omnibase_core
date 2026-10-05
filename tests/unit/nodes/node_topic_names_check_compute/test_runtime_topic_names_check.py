# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI effect boundaries and report serialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_topic_names_check_compute.runtime_topic_names_check import (
    main,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("bad", [False, True])
def test_parity_filenames_and_json(bad: bool, tmp_path: Path) -> None:
    source = tmp_path / "topics.py"
    value = "agent-actions" if bad else "onex." + "evt.platform.event.v1"
    source.write_text(f"TOPIC_CASE = {value!r}\n", encoding="utf-8")
    output = tmp_path / "report.json"
    assert main([str(source), "--report-json", str(output)]) == int(bad)
    report = ModelValidationReport.model_validate_json(output.read_text())
    assert report.overall_status == ("FAIL" if bad else "PASS")


def test_parity_full_tree_mode(tmp_path: Path) -> None:
    source = tmp_path / "topics.ts"
    source.write_text('export const TOPIC_CASE = "agent-actions"\n')
    output = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(output)]) == 1
    report = ModelValidationReport.model_validate_json(output.read_text())
    assert report.overall_status == "FAIL"
    assert report.findings[0].location == "topics.ts:1"


def test_parity_zero_file_full_tree_error(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(output)]) == 1
    report = ModelValidationReport.model_validate_json(output.read_text())
    assert report.overall_status == "ERROR"
    assert "zero files scanned" in report.findings[0].message


def test_parity_unreadable_file_error(tmp_path: Path) -> None:
    source = tmp_path / "topics.py"
    source.write_text('TOPIC_CASE = "agent-actions"\n')
    source.chmod(0)
    output = tmp_path / "report.json"
    try:
        assert main([str(source), "--report-json", str(output)]) == 1
        report = ModelValidationReport.model_validate_json(output.read_text())
        assert report.overall_status == "ERROR"
    finally:
        source.chmod(0o600)


def test_parity_invalid_encoding_error(tmp_path: Path) -> None:
    source = tmp_path / "topics.py"
    source.write_bytes(b"\xff")
    output = tmp_path / "report.json"
    assert main([str(source), "--report-json", str(output)]) == 1
    assert (
        ModelValidationReport.model_validate_json(output.read_text()).overall_status
        == "ERROR"
    )


def test_parity_missing_filename_error(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    assert main([str(tmp_path / "topics.py"), "--report-json", str(output)]) == 1
    assert (
        ModelValidationReport.model_validate_json(output.read_text()).overall_status
        == "ERROR"
    )


def test_parity_legacy_no_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert (
        capsys.readouterr().err
        == "Usage: onex-validate-topics <repo-root> [--verbose]\n"
    )


@pytest.mark.parametrize("flag", ["--verbose", "--help", "-h", "--unknown"])
def test_parity_legacy_flag_root_error(
    flag: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main([flag]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Error: {tmp_path / flag} is not a directory\n"
