# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime effects and exact legacy exit-code semantics."""

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.runtime_hardcoded_topic_check import (
    main,
)
from tests.unit.nodes.node_hardcoded_topic_check_compute.parity_helpers import (
    materialize_parity_corpus,
    normalize_parity_stdout,
    read_parity_golden,
)

pytestmark = pytest.mark.unit


def test_parity_runtime_invalid_utf8(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "invalid.py"
    topic = ".".join(("onex", "a", "b", "c"))
    path.write_bytes(f'T = "{topic}"'.encode() + bytes([255]))
    assert main([str(path), "--quiet"]) == 1
    assert capsys.readouterr().out == f'{path}:1: [{topic}] T = "{topic}"\ufffd\n'


@pytest.mark.parametrize(
    ("name", "expected_code", "expected_status"),
    [("contract.py", 0, "PASS"), ("generation.py", 1, "FAIL")],
)
def test_parity_runtime_filenames_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    name: str,
    expected_code: int,
    expected_status: str,
) -> None:
    materialize_parity_corpus(tmp_path)
    report_path = tmp_path / "output.report"
    assert (
        main([str(tmp_path / name), "--report-json", str(report_path)]) == expected_code
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == expected_status
    assert bool(capsys.readouterr().out)


def test_parity_runtime_report_only_retains_fail(tmp_path: Path) -> None:
    materialize_parity_corpus(tmp_path)
    report_path = tmp_path / "output.report"
    assert (
        main(
            [
                str(tmp_path / "generation.py"),
                "--report-only",
                "--report-json",
                str(report_path),
            ]
        )
        == 0
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "FAIL"


def test_parity_runtime_full_tree_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    materialize_parity_corpus(tmp_path)
    golden = read_parity_golden()
    assert main(["--root", str(tmp_path)]) == golden["exit_code"]
    assert (
        normalize_parity_stdout(capsys.readouterr().out, tmp_path) == golden["findings"]
    )


def test_parity_runtime_default_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    materialize_parity_corpus(tmp_path)
    monkeypatch.chdir(tmp_path)
    golden = read_parity_golden()
    assert main([]) == golden["exit_code"]
    assert (
        normalize_parity_stdout(capsys.readouterr().out, Path()) == golden["findings"]
    )


def test_parity_runtime_zero_files_new_root_errors(tmp_path: Path) -> None:
    report_path = tmp_path / "output.report"
    assert main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert "zero files scanned" in report.findings[0].message


def test_parity_runtime_zero_files_legacy_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "output.report"
    assert main([str(tmp_path), "--report-json", str(report_path)]) == 0
    assert capsys.readouterr().out == (
        "No hardcoded onex.* topic-literal violations found.\n"
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"


@pytest.mark.parametrize("root_mode", [False, True])
def test_parity_runtime_unreadable_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    root_mode: bool,
) -> None:
    source_path = tmp_path / "blocked.py"
    source_path.write_text("x = 1\n")
    original_read = Path.read_text

    def blocked_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == source_path:
            raise PermissionError("fixture cannot be read")
        return original_read(path, encoding="utf-8")

    monkeypatch.setattr(Path, "read_text", blocked_read)
    report_path = tmp_path / "output.report"
    if root_mode:
        args = ["--root", str(tmp_path)]
        expected_exit = 1
    else:
        args = [str(source_path)]
        expected_exit = 0
    assert main([*args, "--report-json", str(report_path)]) == expected_exit
    if not root_mode:
        assert capsys.readouterr().out == (
            "No hardcoded onex.* topic-literal violations found.\n"
        )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert report.metrics.error_count == 1
    assert "read error:" in report.findings[0].message
