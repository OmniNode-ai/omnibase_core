# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime parity at input and report persistence boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_skip_count_ratchet_check_compute.runtime_skip_count_ratchet_check import (
    main,
)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[4]
CORPUS = ROOT / "tests/fixtures/validator_parity/skip_count_ratchet"
BASELINE = CORPUS / "recorded.yaml"


@pytest.mark.parametrize(
    ("name", "code", "status"),
    [("nodeids-at-0.xml", 0, "PASS"), ("nodeids-grown-0.xml", 1, "FAIL")],
)
def test_parity_runtime_filenames(
    name: str, code: int, status: str, tmp_path: Path
) -> None:
    destination = tmp_path / "report.json"
    assert (
        main(
            [
                "--baseline",
                str(BASELINE),
                "--suite",
                "fixture/nodeids",
                str(CORPUS / name),
                "--report-json",
                str(destination),
            ]
        )
        == code
    )
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == status
    if status == "FAIL":
        assert report.metrics.fail_count == 2
        assert all(f.location == f"{BASELINE}:1" for f in report.findings)


def test_parity_runtime_full_tree(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "report.xml").write_text((CORPUS / "nodeids-at-0.xml").read_text())
    destination = tmp_path / "report.json"
    assert (
        main(
            [
                "--baseline",
                str(BASELINE),
                "--suite",
                "fixture/nodeids",
                "--root",
                str(artifacts),
                "--report-json",
                str(destination),
            ]
        )
        == 0
    )
    assert (
        ModelValidationReport.model_validate_json(
            destination.read_text()
        ).overall_status
        == "PASS"
    )


def test_parity_runtime_zero_files(tmp_path: Path) -> None:
    artifacts = tmp_path / "empty"
    artifacts.mkdir()
    destination = tmp_path / "report.json"
    assert (
        main(
            [
                "--suite",
                "fixture/count",
                "--root",
                str(artifacts),
                "--report-json",
                str(destination),
            ]
        )
        == 1
    )
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "ERROR"
    assert "zero files scanned" in report.findings[0].message


@pytest.mark.parametrize("collected", [0, 100])
def test_parity_runtime_zero_records_required_error(
    collected: int, tmp_path: Path
) -> None:
    artifact = tmp_path / "empty.xml"
    artifact.write_text(f'<testsuites><testsuite tests="{collected}"/></testsuites>')
    destination = tmp_path / "report.json"
    assert (
        main(
            [
                "--baseline",
                str(BASELINE),
                "--suite",
                "fixture/count",
                "--junit",
                str(artifact),
                "--report-json",
                str(destination),
            ]
        )
        == 1
    )
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "ERROR"
    assert report.findings[0].message == (
        "::error::skip-count-ratchet input error (fail-closed): "
        "zero test records observed: a run that scans nothing is ERROR, never PASS"
    )


def test_parity_runtime_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "unreadable.xml"
    artifact.write_text('<testsuite tests="1"><testcase name="p"/></testsuite>')
    original = Path.read_text

    def read(path: Path, *args: object, **kwargs: object) -> str:
        if path == artifact:
            raise PermissionError("synthetic unreadable JUnit file")
        return original(path)

    monkeypatch.setattr(Path, "read_text", read)
    destination = tmp_path / "report.json"
    assert (
        main(
            [
                "--baseline",
                str(BASELINE),
                "--suite",
                "fixture/count",
                "--junit",
                str(artifact),
                "--report-json",
                str(destination),
            ]
        )
        == 1
    )
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "ERROR"
    assert "read error:" in report.findings[0].message


def test_parity_runtime_no_disk_writes_except_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(path: Path, *args: object, **kwargs: object) -> int:
        pytest.fail(f"unexpected direct write: {path}")

    monkeypatch.setattr(Path, "write_text", forbidden)
    assert main(["--selftest"]) == 0
