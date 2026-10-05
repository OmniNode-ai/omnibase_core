# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime parity, report persistence, and fatal input diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_test_root_collection_check_compute.runtime_test_root_collection_check import (
    main,
)
from tests.unit.nodes.node_test_root_collection_check_compute.parity_support import (
    materialize_parity_case,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("case", "code", "status"), [("clean", 0, "PASS"), ("stray", 1, "FAIL")]
)
def test_parity_runtime_filenames(
    case: str, code: int, status: str, tmp_path: Path
) -> None:
    materialize_parity_case(tmp_path, case)
    report_file = tmp_path / "report.json"
    assert (
        main(
            [
                str(tmp_path / "pyproject.toml"),
                "--root",
                str(tmp_path),
                "--report-json",
                str(report_file),
            ]
        )
        == code
    )
    report = ModelValidationReport.model_validate_json(report_file.read_text())
    assert report.overall_status == status
    assert report.provenance.validators_run == ("arch-test-root-collection",)


def test_parity_runtime_zero_files(tmp_path: Path) -> None:
    report_file = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_file)]) == 1
    report = ModelValidationReport.model_validate_json(report_file.read_text())
    assert report.overall_status == "ERROR"
    assert "zero files scanned" in report.findings[0].message


def test_parity_runtime_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    materialize_parity_case(tmp_path, "clean")
    target = tmp_path / "pyproject.toml"
    original = Path.read_text

    def read_text(
        path: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if path == target:
            raise OSError("permission denied")
        return original(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", read_text)
    report_file = tmp_path / "report.json"
    assert (
        main([str(target), "--root", str(tmp_path), "--report-json", str(report_file)])
        == 1
    )
    report = ModelValidationReport.model_validate_json(report_file.read_text())
    assert report.overall_status == "ERROR"
    assert "permission denied" in report.findings[0].message


@pytest.mark.parametrize(
    "content",
    [
        '{"standalone_projects": {}, "known_uncollected_debt": []}',
        '{"unexpected": true}',
        "not json",
    ],
)
def test_parity_runtime_typed_config(content: str, tmp_path: Path) -> None:
    materialize_parity_case(tmp_path, "clean")
    config_file = tmp_path / "config.json"
    config_file.write_text(content)
    report_file = tmp_path / "report.json"
    code = main(
        [
            "--root",
            str(tmp_path),
            "--config",
            str(config_file),
            "--report-json",
            str(report_file),
        ]
    )
    report = ModelValidationReport.model_validate_json(report_file.read_text())
    valid = "standalone_projects" in content
    assert code == (0 if valid else 1)
    assert report.overall_status == ("PASS" if valid else "ERROR")


def test_parity_runtime_missing_config(tmp_path: Path) -> None:
    materialize_parity_case(tmp_path, "clean")
    report_file = tmp_path / "report.json"
    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "--config",
                str(tmp_path / "missing.json"),
                "--report-json",
                str(report_file),
            ]
        )
        == 1
    )
    assert (
        ModelValidationReport.model_validate_json(
            report_file.read_text()
        ).overall_status
        == "ERROR"
    )


def test_parity_runtime_invalid_encoding(tmp_path: Path) -> None:
    materialize_parity_case(tmp_path, "clean")
    (tmp_path / "pyproject.toml").write_bytes(b"\xff")
    report_file = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_file)]) == 1
    report = ModelValidationReport.model_validate_json(report_file.read_text())
    assert report.overall_status == "ERROR"
    assert "decode" in report.findings[0].message


@pytest.mark.parametrize("case", ["clean", "standalone_scalar_pr"])
def test_parity_runtime_project_existence_does_not_require_reading(
    case: str, tmp_path: Path
) -> None:
    materialize_parity_case(tmp_path, case)
    project = tmp_path / "scripts/deploy-agent/pyproject.toml"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_bytes(b"\xff")
    report_file = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_file)]) == 0
    report = ModelValidationReport.model_validate_json(report_file.read_text())
    assert report.overall_status == "PASS"
