# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime parity and effect-boundary failure coverage."""

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_markdown_links_check_compute.runtime_markdown_links_check import (
    main,
)

from .parity_support import make_parity_corpus

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("case", "code", "status"), [("pass", 0, "PASS"), ("fail", 1, "FAIL")]
)
def test_parity_runtime_filenames(
    case: str, code: int, status: str, tmp_path: Path
) -> None:
    root = tmp_path / case
    make_parity_corpus(root, case)
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                str(root / "README.md"),
                "--root",
                str(root),
                "--report-json",
                str(report_path),
            ]
        )
        == code
    )
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == status
    )


def test_parity_runtime_zero_files(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 0
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "ERROR"
    )


def test_parity_runtime_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "pass"
    make_parity_corpus(root, "pass")
    original = Path.read_text

    def unreadable(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "README.md":
            raise PermissionError("test unreadable file")
        return original(path)

    monkeypatch.setattr(Path, "read_text", unreadable)
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                str(root / "README.md"),
                "--root",
                str(root),
                "--report-json",
                str(report_path),
            ]
        )
        == 0
    )
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "ERROR"
    )
