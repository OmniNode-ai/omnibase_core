# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime parity and fatal scan-error reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_no_untyped_metadata_check_compute.runtime_no_untyped_metadata_check import (
    main,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("bad", [False, True])
def test_parity_runtime_filenames_and_reports(
    tmp_path: Path, bad: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "field.py"
    path.write_text(
        "metadata" + (": dict[str, Any]\n" if bad else ": OutputMetadataDict\n")
    )
    report_path = tmp_path / "report.json"
    assert main([str(path), "--report-json", str(report_path)]) == int(bad)
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == ("FAIL" if bad else "PASS")
    assert bool(capsys.readouterr().out) == bad


def test_parity_runtime_default_full_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "src"
    root.mkdir()
    (root / "clean.py").write_text("metadata: OutputMetadataDict\n")
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    (root / "bad.py").write_text("metadata" + ": dict[str, object]\n")
    assert main(["--root", str(root)]) == 1


@pytest.mark.parametrize("exists", [False, True])
def test_parity_runtime_zero_scan_error(tmp_path: Path, exists: bool) -> None:
    root = tmp_path / "empty"
    if exists:
        root.mkdir()
    report_path = tmp_path / "error.json"
    assert main(["--root", str(root), "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert "zero files scanned" in report.findings[0].message


@pytest.mark.parametrize("full_tree", [False, True])
def test_parity_runtime_unreadable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, full_tree: bool
) -> None:
    path = tmp_path / "unreadable.py"
    path.write_text("pass\n")
    original = Path.read_text

    def fail_read(
        self: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if self == path:
            raise OSError("permission denied")
        return original(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fail_read)
    report_path = tmp_path / "error.json"
    args = ["--root", str(tmp_path)] if full_tree else [str(path)]
    assert main([*args, "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert "permission denied" in report.findings[0].message


def test_parity_runtime_invalid_encoding_error(tmp_path: Path) -> None:
    path = tmp_path / "undecodable.py"
    path.write_bytes(b"\xff")
    report_path = tmp_path / "error.json"
    assert main([str(path), "--report-json", str(report_path)]) == 1
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "ERROR"
    )


def test_parity_runtime_missing_python_error(tmp_path: Path) -> None:
    report_path = tmp_path / "error.json"
    assert main([str(tmp_path / "missing.py"), "--report-json", str(report_path)]) == 1
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "ERROR"
    )
