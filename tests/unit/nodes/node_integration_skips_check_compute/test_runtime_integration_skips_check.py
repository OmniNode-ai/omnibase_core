# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Artifact runtime boundary and legacy exit-code parity."""

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_integration_skips_check_compute.runtime_integration_skips_check import (
    main,
)

pytestmark = pytest.mark.unit
CORPUS = (
    Path(__file__).resolve().parents[4]
    / "tests/fixtures/validator_parity/integration_skips"
)


@pytest.mark.parametrize(
    ("name", "code", "status"),
    [
        ("pass.xml", 0, "PASS"),
        ("absence_strings.xml", 1, "FAIL"),
        ("malformed.xml", 2, "ERROR"),
        ("missing.xml", 2, "ERROR"),
    ],
)
def test_parity_filenames_reports(
    name: str, code: int, status: str, tmp_path: Path
) -> None:
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                str(CORPUS / name),
                "--config",
                str(CORPUS / "config.yaml"),
                "--report-json",
                str(report_path),
            ]
        )
        == code
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == status


def test_parity_full_tree_aggregates_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "pass.xml").write_text((CORPUS / "pass.xml").read_text())
    (tmp_path / "nested/fail.xml").write_text(
        (CORPUS / "absence_strings.xml").read_text()
    )
    assert main(["--root", str(tmp_path), "--config", str(CORPUS / "config.yaml")]) == 1
    assert "cases=12 executed=4 skipped=8" in capsys.readouterr().out


def test_parity_zero_file_tree_is_error(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "--config",
                str(CORPUS / "config.yaml"),
                "--report-json",
                str(report_path),
            ]
        )
        == 2
    )
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "ERROR"
    )


def test_parity_unreadable_artifact_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "unreadable.xml"
    artifact.write_text("<testsuite/>")
    original_read = Path.read_text

    def read(path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        if path == artifact:
            raise OSError("permission denied")
        return original_read(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", read)
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                str(artifact),
                "--config",
                str(CORPUS / "config.yaml"),
                "--report-json",
                str(report_path),
            ]
        )
        == 1
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert "permission denied" in report.findings[0].message


def test_parity_non_xml_explicit_artifact_is_consumed(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text((CORPUS / "pass.xml").read_text())
    assert (
        main(["--junit", str(artifact), "--config", str(CORPUS / "config.yaml")]) == 0
    )


def test_parity_argparse_usage_exits_two() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--junit"])
    assert exc.value.code == 2
