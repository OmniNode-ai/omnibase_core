# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI modes, report persistence, and fail-closed source read behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.runtime_precommit_interpreter_check import (
    main,
)

pytestmark = pytest.mark.unit


def _parity_config(root: Path, entry: str = "uv run python x.py") -> Path:
    hooks = [{"id": "hook", "entry": entry}] + [
        {"id": f"pad-{index}", "entry": "uv run python x.py"} for index in range(9)
    ]
    config = root / ".pre-commit-config.yaml"
    config.write_text(yaml.safe_dump({"repos": [{"repo": "local", "hooks": hooks}]}))
    return config


@pytest.mark.parametrize(
    ("entry", "exit_code", "status"),
    [
        ("uv run python x.py", 0, "PASS"),
        ("python x.py", 1, "FAIL"),
        ("python 'x.py", 1, "ERROR"),
    ],
)
def test_parity_runtime_filenames_and_json(
    tmp_path: Path, entry: str, exit_code: int, status: str
) -> None:
    config = _parity_config(tmp_path, entry)
    report_path = tmp_path / "report.json"
    assert (
        main([str(config), "--root", str(tmp_path), "--report-json", str(report_path)])
        == exit_code
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == status


def test_parity_runtime_full_tree_referenced_script(tmp_path: Path) -> None:
    _parity_config(tmp_path, "bash hook.sh")
    (tmp_path / "hook.sh").write_text("python x.py\n")
    report_path = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "FAIL"
    assert report.findings[0].location == "hook.sh:1"


def test_parity_runtime_zero_file_tree(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert ".pre-commit-config.yaml" in report.findings[0].message
    assert "not found" in report.findings[0].message


@pytest.mark.parametrize("target", ["config", "script"])
def test_parity_runtime_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    config = _parity_config(tmp_path, "bash hook.sh")
    script = tmp_path / "hook.sh"
    script.write_text("python x.py\n")
    unreadable = config if target == "config" else script
    original = Path.read_text

    def read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path == unreadable:
            raise PermissionError("fixture denied")
        return original(path)

    monkeypatch.setattr(Path, "read_text", read_text)
    report_path = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert "fixture denied" in report.findings[0].message


def test_parity_runtime_default_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _parity_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0


@pytest.mark.parametrize("target", ["config", "script"])
def test_parity_runtime_invalid_utf8(tmp_path: Path, target: str) -> None:
    config = _parity_config(tmp_path, "bash hook.sh")
    script = tmp_path / "hook.sh"
    script.write_text("python x.py\n")
    unreadable = config if target == "config" else script
    unreadable.write_bytes(b"\xff")
    report_path = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 1
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert report.findings[0].message == (
        f"{unreadable}: read error: 'utf-8' codec can't decode byte 0xff "
        "in position 0: invalid start byte"
    )
