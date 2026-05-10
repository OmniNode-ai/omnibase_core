# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for substrate_gates._base — BaseGateCheck, GateViolation, has_allow_annotation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from omnibase_core.cli.substrate_gates._base import (
    BaseGateCheck,
    GateViolation,
    has_allow_annotation,
    main_for_gate,
)

# ---------------------------------------------------------------------------
# Minimal concrete gate for testing the base class
# ---------------------------------------------------------------------------


class _AlwaysCleanGate(BaseGateCheck):
    """Gate that never emits violations — used to test empty-input behaviour."""

    def check_tree(
        self,
        tree: ast.Module,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        return []


class _AlwaysViolatingGate(BaseGateCheck):
    """Gate that emits one violation per file — used to test violation plumbing."""

    def check_tree(
        self,
        tree: ast.Module,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        return [GateViolation(path=path, line=1, message="synthetic violation")]


# ---------------------------------------------------------------------------
# GateViolation tests
# ---------------------------------------------------------------------------


class TestGateViolation:
    def test_str_format(self, tmp_path: Path) -> None:
        p = tmp_path / "foo.py"
        v = GateViolation(path=p, line=42, message="something wrong")
        assert str(v) == f"{p}:42: something wrong"

    def test_frozen(self) -> None:
        p = Path("x.py")
        v = GateViolation(path=p, line=1, message="msg")
        with pytest.raises((AttributeError, TypeError)):
            v.line = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# has_allow_annotation tests
# ---------------------------------------------------------------------------


class TestHasAllowAnnotation:
    def test_substrate_allow(self) -> None:
        lines = ["x: int | None = None  # substrate-allow: pending-fix"]
        assert has_allow_annotation(lines, 1) is True

    def test_onex_exclude(self) -> None:
        lines = ["y: Any  # ONEX_EXCLUDE: any_type"]
        assert has_allow_annotation(lines, 1) is True

    def test_ai_slop_ok(self) -> None:
        lines = ["z: dict[str, Any]  # ai-slop-ok"]
        assert has_allow_annotation(lines, 1) is True

    def test_no_annotation(self) -> None:
        lines = ["x: int | None = None"]
        assert has_allow_annotation(lines, 1) is False

    def test_out_of_range_low(self) -> None:
        assert has_allow_annotation([], 0) is False

    def test_out_of_range_high(self) -> None:
        lines = ["x = 1"]
        assert has_allow_annotation(lines, 99) is False

    def test_case_insensitive_onex_exclude(self) -> None:
        lines = ["y: Any  # onex_exclude: something"]
        assert has_allow_annotation(lines, 1) is True


# ---------------------------------------------------------------------------
# BaseGateCheck.run() tests
# ---------------------------------------------------------------------------


class TestBaseGateCheckRun:
    def test_empty_input_returns_empty_list(self) -> None:
        gate = _AlwaysViolatingGate()
        assert gate.run([]) == []

    def test_clean_file_returns_no_violations(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.py"
        f.write_text("x = 1\n")
        gate = _AlwaysCleanGate()
        assert gate.run([f]) == []

    def test_violating_file_returns_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("x = 1\n")
        gate = _AlwaysViolatingGate()
        violations = gate.run([f])
        assert len(violations) == 1
        assert violations[0].path == f
        assert violations[0].line == 1

    def test_syntax_error_reported_as_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "broken.py"
        f.write_text("def foo(\n")  # unclosed paren → SyntaxError
        gate = _AlwaysCleanGate()
        violations = gate.run([f])
        assert len(violations) == 1
        assert "syntax error" in violations[0].message.lower()

    def test_unreadable_file_reported_as_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "ghost.py"
        # File never created — OSError on read
        gate = _AlwaysCleanGate()
        violations = gate.run([f])
        assert len(violations) == 1
        assert "cannot read file" in violations[0].message.lower()

    def test_multiple_files_aggregated(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"f{i}.py"
            f.write_text("x = 1\n")
            files.append(f)
        gate = _AlwaysViolatingGate()
        violations = gate.run(files)
        assert len(violations) == 3


# ---------------------------------------------------------------------------
# main_for_gate tests
# ---------------------------------------------------------------------------


class TestMainForGate:
    def test_clean_exits_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "ok.py"
        f.write_text("x = 1\n")
        gate = _AlwaysCleanGate()
        assert main_for_gate(gate, [str(f)]) == 0

    def test_violation_exits_one(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("x = 1\n")
        gate = _AlwaysViolatingGate()
        assert main_for_gate(gate, [str(f)]) == 1

    def test_no_args_exits_zero(self) -> None:
        gate = _AlwaysViolatingGate()
        assert main_for_gate(gate, []) == 0

    def test_max_violations_below_threshold_exits_zero(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"f{i}.py"
            f.write_text("x = 1\n")
            files.append(f)
        gate = _AlwaysViolatingGate()
        # 3 violations ≤ threshold 5 → exit 0
        assert (
            main_for_gate(gate, ["--max-violations", "5"] + [str(f) for f in files])
            == 0
        )

    def test_max_violations_at_threshold_exits_zero(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"f{i}.py"
            f.write_text("x = 1\n")
            files.append(f)
        gate = _AlwaysViolatingGate()
        # 3 violations == threshold 3 → exit 0
        assert (
            main_for_gate(gate, ["--max-violations", "3"] + [str(f) for f in files])
            == 0
        )

    def test_max_violations_exceeds_threshold_exits_one(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"f{i}.py"
            f.write_text("x = 1\n")
            files.append(f)
        gate = _AlwaysViolatingGate()
        # 3 violations > threshold 2 → exit 1
        assert (
            main_for_gate(gate, ["--max-violations", "2"] + [str(f) for f in files])
            == 1
        )

    def test_max_violations_zero_with_no_violations_exits_zero(
        self, tmp_path: Path
    ) -> None:
        f = tmp_path / "ok.py"
        f.write_text("x = 1\n")
        gate = _AlwaysCleanGate()
        assert main_for_gate(gate, ["--max-violations", "0", str(f)]) == 0
