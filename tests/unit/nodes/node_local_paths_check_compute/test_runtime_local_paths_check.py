# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime parity, EFFECT boundaries and canonical reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_local_paths_check_compute.runtime_local_paths_check import (
    _gather_paths,
    main,
)

pytestmark = pytest.mark.unit

BAD_SOURCE = 'A = "/' + 'Users/alice/x"\n'
SKIP_DIRS = (
    ".git",
    "__pycache__",
    "node_modules",
    ".tox",
    ".venv",
    "venv",
    ".next",
    "dist",
    "build",
    "graphify-out",
    "dod_receipts",
    "evidence",
    ".evidence",
    ".onex_state",
)
EXTENSIONS = (
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".sh",
    ".toml",
    ".txt",
    ".rst",
    ".cfg",
    ".ini",
)


@pytest.mark.parametrize(
    ("source", "code", "status"), [("A = 1\n", 0, "PASS"), (BAD_SOURCE, 1, "FAIL")]
)
@pytest.mark.parametrize("extension", EXTENSIONS)
def test_parity_runtime_filenames_report(
    source: str, code: int, status: str, extension: str, tmp_path: Path
) -> None:
    path = tmp_path / ("source" + extension)
    path.write_text(source)
    destination = tmp_path / "report.json"
    assert main([str(path), "--report-json", str(destination)]) == code
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == status


@pytest.mark.parametrize("directory", SKIP_DIRS)
def test_parity_runtime_skip_directories(directory: str, tmp_path: Path) -> None:
    path = tmp_path / directory / "bad.txt"
    path.parent.mkdir()
    path.write_text(BAD_SOURCE)
    assert main([str(path)]) == 0
    assert _gather_paths([tmp_path])[0] == []


def test_parity_runtime_gather_scope(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    names = [
        "schema/foo_schema.yaml",
        ".github/workflow.yml",
        ".pytest_cache/a.txt",
        "src/a.py",
        "a.py",
        "a/nested.py",
    ]
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BAD_SOURCE)
    (tmp_path / "ignored.lock").write_text(BAD_SOURCE)
    (tmp_path / "upper.PY").write_text(BAD_SOURCE)
    (tmp_path / ".onexignore").write_text("all:\n  patterns:\n    - src/\n")
    files, errors = _gather_paths([tmp_path])
    assert not errors
    assert {Path(f.path).relative_to(tmp_path).as_posix() for f in files} == set(names)
    assert main(["--root", str(tmp_path)]) == 1
    assert capsys.readouterr().out.count("[macOS user home]") == len(names)


def test_parity_runtime_zero_tree_error_report(tmp_path: Path) -> None:
    destination = tmp_path / "report.json"
    # Exit-code parity takes precedence over the default fail-closed exit policy.
    assert main(["--root", str(tmp_path), "--report-json", str(destination)]) == 0
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "ERROR"


def test_parity_runtime_unreadable_error_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "unreadable.txt"
    source.write_text(BAD_SOURCE)
    original = Path.read_text

    def unreadable(path: Path, *args: object, **kwargs: object) -> str:
        if path == source:
            raise PermissionError("fixture unreadable")
        return original(path)

    monkeypatch.setattr(Path, "read_text", unreadable)
    destination = tmp_path / "report.json"
    assert main([str(source), "--report-json", str(destination)]) == 0
    assert (
        ModelValidationReport.model_validate_json(
            destination.read_text()
        ).overall_status
        == "ERROR"
    )


def test_parity_runtime_missing_and_nontext(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"
    binary = tmp_path / "binary.so"
    binary.write_bytes(b"\xff")
    assert main([str(missing), str(binary)]) == 0


@pytest.mark.parametrize("mode", ["file", "tree", "restored"])
def test_parity_runtime_replacement_decoding_report(mode: str, tmp_path: Path) -> None:
    source = tmp_path / (
        "schema/invalid_schema.txt" if mode == "restored" else "invalid.txt"
    )
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(BAD_SOURCE.encode("utf-8") + b"\xff")
    destination = tmp_path.parent / (tmp_path.name + "-report.json")
    args = [str(source)] if mode == "file" else ["--root", str(tmp_path)]
    assert main([*args, "--report-json", str(destination)]) == 1
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].location == f"{source}:1"
