# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime parity and effect-boundary error coverage."""

from pathlib import Path

import pytest

from omnibase_core.models.nodes.source_file_gather.model_skipped_source_file import (
    ModelSkippedSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelSourceFileGatherOutput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

from .parity_helpers import CORPUS, runtime_parity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("name", "strict", "exit_code", "status"),
    [
        ("clean.py", False, 0, "PASS"),
        ("warning.py", False, 0, "WARN"),
        ("warning.py", True, 2, "FAIL"),
        ("rest_param.py", False, 1, "FAIL"),
        ("syntax.py", False, 1, "ERROR"),
        ("info.py", True, 0, "PASS"),
    ],
)
def test_parity_runtime_filenames(
    name: str, strict: bool, exit_code: int, status: str, tmp_path: Path
) -> None:
    source = tmp_path / name
    source.write_text(CORPUS[name])
    code, result = runtime_parity([source], strict, True, tmp_path / "report.json")
    assert code == exit_code
    assert result.overall_status == status


def test_parity_runtime_empty_tree(tmp_path: Path) -> None:
    code, result = runtime_parity(
        [], False, False, tmp_path / "report.json", ["--root", str(tmp_path)]
    )
    assert code == 1
    assert result.overall_status == "ERROR"
    assert "zero files scanned" in result.findings[0].message


def test_parity_runtime_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.py"
    path.write_text("x = 1\n")

    def unreadable(
        self: NodeSourceFileGatherEffect, request: ModelSourceFileGatherInput
    ) -> ModelSourceFileGatherOutput:
        return ModelSourceFileGatherOutput(
            root=request.root,
            skipped=[
                ModelSkippedSourceFile(
                    path=str(path), reason="read error: Permission denied"
                )
            ],
        )

    monkeypatch.setattr(NodeSourceFileGatherEffect, "handle", unreadable)
    code, result = runtime_parity([path], False, False, tmp_path / "report.json")
    assert code == 1
    assert result.overall_status == "ERROR"
    assert "Permission denied" in result.findings[0].message


def test_parity_runtime_missing_and_unsupported_paths(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text(CORPUS["notes.md"])
    code, result = runtime_parity(
        [source, tmp_path / "missing.py"], True, True, tmp_path / "report.json"
    )
    assert code == 0
    assert not result.findings


def test_parity_runtime_json_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    from omnibase_core.nodes.node_ai_slop_check_compute.runtime_ai_slop_check import (
        main,
    )

    source = tmp_path / "source.py"
    source.write_text(CORPUS["warning.py"])
    assert main(["--json", str(source)]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["severity"] == "WARNING"


def test_parity_runtime_full_tree_report_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("x = 1\n")
    code, report = runtime_parity(
        [], True, False, tmp_path / "report.json", ["--root", str(tmp_path)]
    )
    assert code == 0
    assert (
        ModelValidationReport.model_validate_json(
            (tmp_path / "report.json").read_text()
        ).overall_status
        == report.overall_status
        == "PASS"
    )


def test_parity_runtime_hidden_suffix_file(tmp_path: Path) -> None:
    from .parity_helpers import handler_parity, rows_parity

    path = tmp_path / ".py"
    path.write_text(CORPUS["rest_param.py"])
    # The replaced script scanned a file named ".py" (suffix ""), found nothing and exited 0.
    code, report = runtime_parity([path], True, True, tmp_path / "report.json")
    assert code == 0
    assert rows_parity(report) == []
    assert rows_parity(handler_parity([path], True, True)) == []


def test_parity_runtime_read_error_keeps_other_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from .parity_helpers import handler_parity, rows_parity

    unreadable = tmp_path / "unreadable.py"
    unreadable.write_text("x = 1\n")
    bad = tmp_path / "bad.py"
    bad.write_text(CORPUS["rest_param.py"])
    oracle = rows_parity(handler_parity([bad], True, True))
    assert oracle, "positive control: the unreadable file's neighbour has findings"
    original_read = Path.read_text

    def read(self: Path, *args: object, **kwargs: object) -> str:
        if self == unreadable:
            raise PermissionError("Permission denied")
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    code, report = runtime_parity(
        [bad, unreadable, bad], True, True, tmp_path / "report.json"
    )
    expected_error = {
        "filename": str(unreadable),
        "line": 0,
        "check": "file_read",
        "severity": "ERROR",
        "message": "Cannot read file: Permission denied",
    }
    assert code == 1
    assert report.overall_status == "ERROR"
    assert rows_parity(report) == [
        *oracle,
        expected_error,
        *oracle,
    ]
