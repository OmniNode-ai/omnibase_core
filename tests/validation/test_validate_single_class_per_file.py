# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for the single-class-per-file validator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "validation"
    / "validate-single-class-per-file.py"
)


def _load_validator_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "validate_single_class_per_file", VALIDATOR_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_delegation_terminal_v2_exception_is_scoped_to_its_canonical_path(
    tmp_path: Path,
) -> None:
    """An identically named file elsewhere must remain subject to the rule."""
    validator = _load_validator_module()
    canonical_path = Path(
        "src/omnibase_core/models/delegation/wire/model_delegation_terminal_v2.py"
    )
    canonical_absolute_path = (
        VALIDATOR_PATH.parents[2]
        / "src"
        / "omnibase_core"
        / "models"
        / "delegation"
        / "wire"
        / "model_delegation_terminal_v2.py"
    )
    shadow_path = (
        tmp_path.parent
        / "single_class_scope_shadow"
        / "model_delegation_terminal_v2.py"
    )
    shadow_path.parent.mkdir()
    shadow_path.write_text("class First:\n    pass\n\nclass Second:\n    pass\n")

    assert validator.should_exclude_file(canonical_path)
    assert validator.should_exclude_file(canonical_absolute_path)
    assert not validator.should_exclude_file(shadow_path)
    assert not validator.check_file(shadow_path)["valid"]


def test_main_preserves_empty_scan_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """An empty scan must retain its established success diagnostic."""
    validator = _load_validator_module()
    monkeypatch.setattr(sys, "argv", ["validator", str(tmp_path)])

    assert validator.main() == 0
    captured = capsys.readouterr()

    assert captured.out == "No Python files found to check\n"
    assert captured.err == ""


def test_main_preserves_violation_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """A violation must retain its complete, line-oriented CLI report."""
    validator = _load_validator_module()
    source_file = tmp_path.parent / "single_class_violation" / "multiple_classes.py"
    source_file.parent.mkdir()
    source_file.write_text("class First:\n    pass\n\nclass Second:\n    pass\n")
    monkeypatch.setattr(sys, "argv", ["validator", str(source_file)])

    assert validator.main() == 1
    captured = capsys.readouterr()

    assert captured.out == (
        f"\n{source_file}:\n"
        "  Found 2 non-enum class(es) and 0 enum(s) in same file\n"
        "  Non-enum classes:\n"
        "    Line 1: First\n"
        "    Line 4: Second\n"
        "\n❌ Found 1 file(s) violating single-class-per-file rule\n"
        "\nGuidance:\n"
        "  - Split files with multiple non-enum classes into separate files\n"
        "  - Each class should have its own file with matching name\n"
        "  - Multiple enums in one file are acceptable (enum collections)\n"
        "\nExamples:\n"
        "  ❌ node_orchestrator.py with 11 classes\n"
        "  ✓ node_orchestrator.py (main class only)\n"
        "  ✓ model_orchestrator_input.py (separate file)\n"
        "  ✓ enum_workflow_states.py (multiple enums OK)\n"
    )
    assert captured.err == ""


def test_check_file_preserves_read_error_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Expected read failures remain non-fatal and retain their stderr diagnostic."""
    validator = _load_validator_module()
    source_file = tmp_path / "unreadable.py"

    def raise_read_error(*args: object, **kwargs: object) -> object:
        raise OSError("read failure")

    monkeypatch.setattr("builtins.open", raise_read_error)

    assert validator.check_file(source_file) == {
        "valid": True,
        "skipped": True,
        "reason": "error: read failure",
    }
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == f"Error processing {source_file}: read failure\n"
