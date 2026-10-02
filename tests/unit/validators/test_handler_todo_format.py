# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Falsifiers for the OCC ticket-format hook port (OMN-20068)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.handlers.handler_todo_format import check_file, main
from omnibase_core.models.validation.model_todo_format_finding import (
    ModelTodoFormatFinding,
)

pytestmark = pytest.mark.unit

FIRST_MARKER = "TO" + "DO"
SECOND_MARKER = "FIX" + "ME"
THIRD_MARKER = "HA" + "CK"


def _write(tmp_path: Path, text: str, name: str = "sample.py") -> str:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_bare_todo_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, f"# {FIRST_MARKER}: x\n")
    assert main([path]) == 1
    assert len(check_file(path)) == 1


@pytest.mark.parametrize("comment", [f"# {SECOND_MARKER} x", f"# {THIRD_MARKER}"])
def test_bare_fixme_and_hack_are_refused(tmp_path: Path, comment: str) -> None:
    assert main([_write(tmp_path, comment)]) == 1


def test_valid_marker_does_not_hide_bare_marker(tmp_path: Path) -> None:
    assert (
        main([_write(tmp_path, f"# {FIRST_MARKER}(OMN-123): x; {SECOND_MARKER} x\n")])
        == 1
    )


@pytest.mark.parametrize(
    "comment",
    [
        f"# {FIRST_MARKER} (OMN-123): x",
        f"# {FIRST_MARKER}(OMN-123) x",
        f"# {FIRST_MARKER}(OMN-XXXX): x",
        f"# {FIRST_MARKER}(ABC-123): x",
        f"# {FIRST_MARKER}: x  # {FIRST_MARKER}_FORMAT_EXEMPT:   ",
    ],
)
def test_malformed_ticket_or_empty_exemption_is_refused(
    tmp_path: Path, comment: str
) -> None:
    assert main([_write(tmp_path, comment)]) == 1


def test_exemption_inside_string_does_not_hide_bare_marker(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f'value = "# {FIRST_MARKER}_FORMAT_EXEMPT: legacy"  # {FIRST_MARKER}: x\n',
    )
    assert main([path]) == 1


def test_printed_findings_and_summary_match_source_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = _write(tmp_path, f"value = 1\n# {FIRST_MARKER}: x\n# {SECOND_MARKER} x\n")
    second = _write(tmp_path, f"# {THIRD_MARKER}\n", "second.py")
    assert main([first, second]) == 1
    message = (
        f"bare {FIRST_MARKER}/{SECOND_MARKER}/{THIRD_MARKER} without ticket reference"
        f" -- use format: # {FIRST_MARKER}(OMN-XXXX): description"
    )
    assert [finding.model_dump() for finding in check_file(first)] == [
        {"path": first, "line": 2, "message": message},
        {"path": first, "line": 3, "message": message},
    ]
    captured = capsys.readouterr()
    assert captured.out == (
        f"{first}:2: {message}\n{first}:3: {message}\n{second}:1: {message}\n"
        f"\n3 violation(s). Use format: # {FIRST_MARKER}(OMN-XXXX): description\n"
    )
    assert captured.err == ""


@pytest.mark.parametrize("marker", [FIRST_MARKER, SECOND_MARKER, THIRD_MARKER])
def test_ticketed_marker_is_accepted(tmp_path: Path, marker: str) -> None:
    path = _write(tmp_path, f"# {marker}(OMN-123): x\n")
    assert check_file(path) == []
    assert main([path]) == 0


def test_comment_exemption_with_reason_is_accepted(tmp_path: Path) -> None:
    path = _write(
        tmp_path, f"# {FIRST_MARKER}: x  # {FIRST_MARKER}_FORMAT_EXEMPT: legacy\n"
    )
    assert check_file(path) == []
    assert main([path]) == 0


@pytest.mark.parametrize(
    "segment", ["tests", "docs", "examples", "fixtures", "vendored"]
)
def test_excluded_path_segment_is_skipped(tmp_path: Path, segment: str) -> None:
    path = _write(tmp_path, f"# {FIRST_MARKER}: x\n", f"src/{segment}/nested/sample.py")
    assert check_file(path) == []
    assert main([path]) == 0


def test_similar_path_segment_does_not_skip_source(tmp_path: Path) -> None:
    path = _write(tmp_path, f"# {FIRST_MARKER}: x\n", "tests_extra/sample.py")
    assert main([path]) == 1


@pytest.mark.parametrize("name", ["sample.txt", "sample.PY", "sample.py.txt"])
def test_non_python_file_is_skipped(tmp_path: Path, name: str) -> None:
    path = _write(tmp_path, f"# {FIRST_MARKER}: x\n", name)
    assert check_file(path) == []
    assert main([path]) == 0


@pytest.mark.parametrize("name", ["handler_todo_format.py", "check_todo_format.py"])
def test_hook_basename_is_skipped(tmp_path: Path, name: str) -> None:
    assert check_file(_write(tmp_path, f"# {FIRST_MARKER}: x\n", name)) == []


@pytest.mark.parametrize("delimiter", ['"""', "'''"])
def test_marker_inside_triple_quoted_docstring_is_ignored(
    tmp_path: Path, delimiter: str
) -> None:
    path = _write(
        tmp_path,
        f"{delimiter}\n# {FIRST_MARKER}: x\n# {SECOND_MARKER} x\n"
        f"{delimiter}\n# {FIRST_MARKER}(OMN-123): x\n",
    )
    assert main([path]) == 0


@pytest.mark.parametrize(
    "text",
    [
        f'value = "# {FIRST_MARKER}: x"\n',
        f"value = '# {SECOND_MARKER} x'\n",
        f'value = "escaped \\" # {THIRD_MARKER}"\n',
        f'value = "{FIRST_MARKER}: x"  # ordinary comment\n',
    ],
)
def test_marker_inside_string_literal_is_ignored(tmp_path: Path, text: str) -> None:
    assert main([_write(tmp_path, text)]) == 0


def test_bare_marker_after_string_literal_is_refused(tmp_path: Path) -> None:
    assert main([_write(tmp_path, f'value = "ordinary"  # {FIRST_MARKER}: x\n')]) == 1


def test_block_comment_lines_are_ignored_and_scanning_resumes(tmp_path: Path) -> None:
    path = _write(
        tmp_path, f"/*\n# {FIRST_MARKER}: x\n*/ # {SECOND_MARKER} x\n# {THIRD_MARKER}\n"
    )
    assert [finding.line for finding in check_file(path)] == [4]


def test_unreadable_file_is_skipped(tmp_path: Path) -> None:
    assert check_file(str(tmp_path / "missing.py")) == []
    directory = tmp_path / "directory.py"
    directory.mkdir()
    assert check_file(str(directory)) == []


def test_clean_and_empty_arguments_return_zero_without_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([_write(tmp_path, "value = 1\n")]) == 0
    assert main([]) == 0
    assert capsys.readouterr().out == ""


def test_default_main_arguments_scan_sys_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, f"# {FIRST_MARKER}: x\n")
    monkeypatch.setattr(sys, "argv", ["handler_todo_format", path])
    assert main() == 1


def test_finding_refuses_mutation_and_unknown_fields() -> None:
    finding = ModelTodoFormatFinding(path="sample.py", line=1, message="bare marker")
    with pytest.raises(ValidationError, match="frozen_instance"):
        finding.line = 2
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelTodoFormatFinding.model_validate(
            {"path": "sample.py", "line": 1, "message": "bare marker", "extra": True}
        )


def test_exported_hook_preserves_consumer_id_and_handler_entry() -> None:
    root = Path(__file__).resolve().parents[3]
    hooks = yaml.safe_load(
        (root / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    )
    (hook,) = [hook for hook in hooks if hook["id"] == "no-untracked-todos"]
    assert (
        hook["name"]
        == f"No untracked {FIRST_MARKER}/{SECOND_MARKER}/{THIRD_MARKER} comments"
    )
    assert hook["description"] == (
        f"Require all {FIRST_MARKER}/{SECOND_MARKER}/{THIRD_MARKER} comments to reference a Linear ticket (OMN-XXXX). "
        "Ported from onex_change_control (OMN-20068, S8).\n"
    )
    assert hook["entry"] == "python -m omnibase_core.handlers.handler_todo_format"
    assert hook["language"] == "python"
    assert hook["types"] == ["python"]
    assert hook["stages"] == ["pre-commit"]
    assert hook["pass_filenames"] is True
    assert hook["require_serial"] is True
