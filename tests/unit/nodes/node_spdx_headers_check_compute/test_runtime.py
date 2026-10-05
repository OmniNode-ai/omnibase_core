# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""SPDX runtime reports, warning compatibility and fatal gathering failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.cli.cli_spdx import SPDX_HEADER
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_spdx_headers_check_compute.runtime_spdx_headers_check import (
    main,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("bad", [False, True])
def test_spdx_runtime_report(
    tmp_path: Path, bad: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "a.py"
    path.write_text("" if bad else SPDX_HEADER)
    report_path = tmp_path / "report.json"
    assert main([str(path), "--report-json", str(report_path)]) == int(bad)
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == ("FAIL" if bad else "PASS")
    assert bool(capsys.readouterr().out) == bad
    if bad:
        assert (
            report.findings[0].message
            == f"{path}: File is empty (expected SPDX header)"
        )


@pytest.mark.parametrize("exists", [False, True])
def test_spdx_runtime_zero_scan(tmp_path: Path, exists: bool) -> None:
    root = tmp_path / "empty"
    if exists:
        root.mkdir()
        (root / "ignored.txt").write_text("ignored\n")
    report_path = tmp_path / "report.json"
    assert main(["--root", str(root), "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert "zero files scanned" in report.findings[0].message


def test_spdx_runtime_warnings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing.py"
    ignored = tmp_path / "ignored.txt"
    ignored.write_text("missing header\n")
    report_path = tmp_path / "report.json"
    assert main([str(missing), str(ignored), "--report-json", str(report_path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"Warning: path does not exist: {missing}\n"
        f"Warning: skipping ineligible file: {ignored}\n"
    )
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "PASS"
    )


def test_spdx_runtime_default_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    for relative in (
        ".github/workflows/check.yml",
        "schemas/a.yaml",
        "nested/Dockerfile",
        "Makefile",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SPDX_HEADER)
    excluded = tmp_path / "vendor/ignored.py"
    excluded.parent.mkdir()
    excluded.write_text("pass\n")
    assert main([]) == 0
    (tmp_path / "empty.py").touch()
    assert main(["--root", str(tmp_path)]) == 1


@pytest.mark.parametrize("full_tree", [False, True])
def test_spdx_runtime_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, full_tree: bool
) -> None:
    path = tmp_path / "a.py"
    path.write_text(SPDX_HEADER)
    original = Path.read_text

    def fail_read(
        self: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if self == path:
            raise OSError("permission denied")
        return original(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fail_read)
    report_path = tmp_path / "report.json"
    args = ["--root", str(tmp_path)] if full_tree else [str(path)]
    assert main([*args, "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert "permission denied" in report.findings[0].message


def test_spdx_runtime_invalid_encoding(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_bytes(b"\xff")
    report_path = tmp_path / "report.json"
    assert main([str(path), "--report-json", str(report_path)]) == 1
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "ERROR"
    )
