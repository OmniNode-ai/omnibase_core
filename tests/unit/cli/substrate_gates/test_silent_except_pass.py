# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for substrate_gates.silent_except_pass — Gate 4."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from omnibase_core.cli.substrate_gates.silent_except_pass import SilentExceptPassGate

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.unit
class TestSilentExceptPassGate:
    def test_violation_fixture_has_violations(self, tmp_path: Path) -> None:
        violation_fixture = tmp_path / "except_violation.py"
        violation_fixture.write_text(
            dedent(
                """
                def may_raise() -> None:
                    raise ValueError("fixture")


                def bare_except() -> None:
                    try:
                        may_raise()
                    except:
                        pass


                def except_exception() -> None:
                    try:
                        may_raise()
                    except Exception:
                        pass


                def except_base_exception() -> None:
                    try:
                        may_raise()
                    except BaseException:
                        pass


                def except_tuple() -> None:
                    try:
                        may_raise()
                    except (Exception, ValueError):
                        pass
                """
            ),
            encoding="utf-8",
        )
        gate = SilentExceptPassGate()
        violations = gate.run([violation_fixture])
        assert len(violations) >= 4, (
            f"expected >=4 violations, got {len(violations)}: {violations}"
        )

    def test_clean_fixture_has_no_violations(self) -> None:
        gate = SilentExceptPassGate()
        violations = gate.run([FIXTURES_DIR / "except_clean.py"])
        assert violations == [], f"unexpected violations: {violations}"

    def test_bare_except_pass_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "bare.py"
        f.write_text("try:\n    pass\nexcept:\n    pass\n")
        violations = SilentExceptPassGate().run([f])
        assert len(violations) == 1
        assert "silent except-pass" in violations[0].message

    def test_except_exception_pass_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "exc.py"
        f.write_text("try:\n    pass\nexcept Exception:\n    pass\n")
        violations = SilentExceptPassGate().run([f])
        assert len(violations) == 1

    def test_except_tuple_pass_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "tup.py"
        f.write_text("try:\n    pass\nexcept (Exception, ValueError):\n    pass\n")
        violations = SilentExceptPassGate().run([f])
        assert len(violations) == 1

    def test_except_with_body_allowed(self, tmp_path: Path) -> None:
        f = tmp_path / "body.py"
        f.write_text("try:\n    pass\nexcept Exception:\n    print('ok')\n")
        violations = SilentExceptPassGate().run([f])
        assert violations == []

    def test_narrow_except_pass_with_allow_suppressed(self, tmp_path: Path) -> None:
        f = tmp_path / "allowed.py"
        f.write_text(
            "try:\n    pass\nexcept ValueError:  # substrate-allow: intentional\n    pass\n"
        )
        violations = SilentExceptPassGate().run([f])
        assert violations == []

    def test_bare_except_pass_with_allow_suppressed(self, tmp_path: Path) -> None:
        f = tmp_path / "bare_allowed.py"
        f.write_text(
            "try:\n    pass\nexcept:  # substrate-allow: bootstrap\n    pass\n"
        )
        violations = SilentExceptPassGate().run([f])
        assert violations == []

    def test_multiple_violations_in_one_file(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        f.write_text(
            "try:\n    pass\nexcept:\n    pass\n"
            "try:\n    pass\nexcept Exception:\n    pass\n"
        )
        violations = SilentExceptPassGate().run([f])
        assert len(violations) == 2

    def test_empty_paths_returns_empty(self) -> None:
        assert SilentExceptPassGate().run([]) == []

    def test_reraise_not_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "reraise.py"
        f.write_text(
            "try:\n    pass\nexcept Exception as exc:\n    raise RuntimeError from exc\n"
        )
        violations = SilentExceptPassGate().run([f])
        assert violations == []

    def test_violation_line_number_correct(self, tmp_path: Path) -> None:
        f = tmp_path / "lineno.py"
        f.write_text("x = 1\ntry:\n    pass\nexcept:\n    pass\n")
        violations = SilentExceptPassGate().run([f])
        assert len(violations) == 1
        assert violations[0].line == 4
