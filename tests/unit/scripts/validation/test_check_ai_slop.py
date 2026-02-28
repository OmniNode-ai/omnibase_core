# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive tests for the check_ai_slop.py validation script.

Tests cover:
- Boilerplate docstring detection (TestBoilerplateDocstring)
- reST-style docstring detection (TestRestDocstring)
- Sycophantic opener detection (TestSycophancy)
- Step narration comment detection (TestStepNarration)
- Markdown separator detection (TestMarkdownSeparator)
- Suppression marker behavior
- Multi-line docstring openers (AST required — line-based would miss these)
- Exit code behavior (strict vs non-strict)

Linear ticket: OMN-2971
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Import the checker module via importlib (same pattern as other script tests)
# ---------------------------------------------------------------------------

SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "scripts" / "validation"
)

spec = importlib.util.spec_from_file_location(
    "check_ai_slop", SCRIPTS_DIR / "check_ai_slop.py"
)
if spec is None:
    raise ImportError(f"Cannot find check_ai_slop.py at {SCRIPTS_DIR}")
if spec.loader is None:
    raise ImportError("Module spec has no loader")

check_ai_slop = importlib.util.module_from_spec(spec)
sys.modules["check_ai_slop"] = check_ai_slop
spec.loader.exec_module(check_ai_slop)

SlopViolation: Any = check_ai_slop.SlopViolation
check_file: Any = check_ai_slop.check_file
main: Any = check_ai_slop.main
CHECK_SYCOPHANCY: str = check_ai_slop.CHECK_SYCOPHANCY
CHECK_REST_DOCSTRING: str = check_ai_slop.CHECK_REST_DOCSTRING
CHECK_BOILERPLATE_DOCSTRING: str = check_ai_slop.CHECK_BOILERPLATE_DOCSTRING
CHECK_STEP_NARRATION: str = check_ai_slop.CHECK_STEP_NARRATION
CHECK_MD_SEPARATOR: str = check_ai_slop.CHECK_MD_SEPARATOR
SEVERITY_ERROR: str = check_ai_slop.SEVERITY_ERROR
SEVERITY_WARNING: str = check_ai_slop.SEVERITY_WARNING

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_py(tmp_path: Path, source: str) -> Path:
    """Write Python source to a temp file and return its path."""
    source = textwrap.dedent(source)
    p = tmp_path / "test_subject.py"
    p.write_text(source, encoding="utf-8")
    return p


def _violations_of(tmp_path: Path, source: str) -> list[Any]:
    return check_file(_write_py(tmp_path, source))


def _checks(violations: list[Any]) -> list[str]:
    return [v.check for v in violations]


# ---------------------------------------------------------------------------
# TestBoilerplateDocstring
# ---------------------------------------------------------------------------


class TestBoilerplateDocstring:
    """Tests for boilerplate_docstring WARNING violations."""

    def test_module_docstring_boilerplate(self, tmp_path: Path) -> None:
        source = '''\
            """This module provides utility functions."""
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING in _checks(violations)

    def test_class_docstring_boilerplate(self, tmp_path: Path) -> None:
        source = '''\
            class Foo:
                """This class implements the Foo protocol."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING in _checks(violations)

    def test_function_docstring_boilerplate(self, tmp_path: Path) -> None:
        source = '''\
            def do_thing():
                """This function handles the request processing."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING in _checks(violations)

    def test_boilerplate_is_warning_not_error(self, tmp_path: Path) -> None:
        source = '''\
            """This module provides things."""
        '''
        violations = _violations_of(tmp_path, source)
        bp = [v for v in violations if v.check == CHECK_BOILERPLATE_DOCSTRING]
        assert bp, "Expected boilerplate violation"
        assert all(v.severity == SEVERITY_WARNING for v in bp)

    def test_non_boilerplate_docstring_clean(self, tmp_path: Path) -> None:
        source = '''\
            def do_thing():
                """Compute the hash of the input string."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING not in _checks(violations)

    def test_multi_line_opener(self, tmp_path: Path) -> None:
        """
        Key regression: opener is on the line AFTER the triple-quote.
        Line-based regex would miss this; AST is required.
        """
        source = '''\
            def do_thing():
                """
                This function provides the main entry point.
                """
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING in _checks(violations), (
            "Multi-line boilerplate opener must be caught via AST"
        )

    def test_boilerplate_contains(self, tmp_path: Path) -> None:
        source = '''\
            """This service contains all the configuration."""
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING in _checks(violations)

    def test_boilerplate_responsible_for(self, tmp_path: Path) -> None:
        source = '''\
            class Bar:
                """This handler is responsible for routing."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING in _checks(violations)

    def test_suppression_on_def_line(self, tmp_path: Path) -> None:
        source = '''\
            def do_thing():  # ai-slop-ok: legacy docstring
                """This function provides things."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING not in _checks(violations)

    def test_suppression_on_docstring_line(self, tmp_path: Path) -> None:
        source = '''\
            def do_thing():
                """This function provides things."""  # ai-slop-ok: approved
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING not in _checks(violations)

    def test_suppression_on_preceding_line(self, tmp_path: Path) -> None:
        source = '''\
            # ai-slop-ok: approved boilerplate for compatibility
            def do_thing():
                """This function provides things."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING not in _checks(violations)


# ---------------------------------------------------------------------------
# TestRestDocstring
# ---------------------------------------------------------------------------


class TestRestDocstring:
    """Tests for rest_docstring ERROR violations."""

    def test_param_rest(self, tmp_path: Path) -> None:
        source = '''\
            def fn(x: int) -> int:
                """Add one.

                :param x: the input value
                :returns: x + 1
                """
                return x + 1
        '''
        violations = _violations_of(tmp_path, source)
        rest = [v for v in violations if v.check == CHECK_REST_DOCSTRING]
        assert len(rest) >= 1

    def test_rest_is_error(self, tmp_path: Path) -> None:
        source = '''\
            def fn(x: int) -> int:
                """:param x: value"""
                return x
        '''
        violations = _violations_of(tmp_path, source)
        rest = [v for v in violations if v.check == CHECK_REST_DOCSTRING]
        assert rest
        assert all(v.severity == SEVERITY_ERROR for v in rest)

    def test_type_rest(self, tmp_path: Path) -> None:
        source = '''\
            def fn(x: int) -> int:
                """
                :type x: int
                """
                return x
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING in _checks(violations)

    def test_raises_rest(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """
                :raises ValueError: if bad
                """
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING in _checks(violations)

    def test_google_style_clean(self, tmp_path: Path) -> None:
        source = '''\
            def fn(x: int) -> int:
                """Add one.

                Args:
                    x: The input value.

                Returns:
                    x + 1
                """
                return x + 1
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING not in _checks(violations)

    def test_suppression_on_class_line(self, tmp_path: Path) -> None:
        source = '''\
            class Foo:  # ai-slop-ok: third-party compat
                """
                :param x: the input
                """
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING not in _checks(violations)

    def test_suppression_on_docstring_line(self, tmp_path: Path) -> None:
        source = '''\
            def fn(x: int) -> int:
                """:param x: value"""  # ai-slop-ok: external API
                return x
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING not in _checks(violations)

    def test_suppression_on_preceding_line(self, tmp_path: Path) -> None:
        source = '''\
            # ai-slop-ok: compatible with sphinx
            def fn(x: int) -> int:
                """:param x: value"""
                return x
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING not in _checks(violations)


# ---------------------------------------------------------------------------
# TestSycophancy
# ---------------------------------------------------------------------------


class TestSycophancy:
    """Tests for sycophancy ERROR violations."""

    def test_excellent_opener(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """Excellent! This is a great function."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY in _checks(violations)

    def test_great_opener(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """Great, now let me explain."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY in _checks(violations)

    def test_sure_opener(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """Sure! Here is the implementation."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY in _checks(violations)

    def test_certainly_opener(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """Certainly! Let me help you."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY in _checks(violations)

    def test_sycophancy_is_error(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """Absolutely! Great work."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        syco = [v for v in violations if v.check == CHECK_SYCOPHANCY]
        assert syco
        assert all(v.severity == SEVERITY_ERROR for v in syco)

    def test_multi_line_sycophancy(self, tmp_path: Path) -> None:
        """Opener on line after triple-quote — AST required."""
        source = '''\
            def fn() -> None:
                """
                Excellent! This is well-designed.
                """
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY in _checks(violations)

    def test_non_sycophantic_opener_clean(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """Compute the hash of the input."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY not in _checks(violations)

    def test_suppression_on_def_line(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:  # ai-slop-ok: intentional tone
                """Excellent! This is well-designed."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY not in _checks(violations)


# ---------------------------------------------------------------------------
# TestStepNarration
# ---------------------------------------------------------------------------


class TestStepNarration:
    """Tests for step_narration WARNING violations (line-based, outside docstrings)."""

    def test_step_narration_colon(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                # Step 1: Initialize the system
                x = 1
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_STEP_NARRATION in _checks(violations)

    def test_step_narration_dash(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                # Step 2 - Connect to database
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_STEP_NARRATION in _checks(violations)

    def test_step_narration_is_warning(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                # Step 3: Do the thing
                pass
        '''
        violations = _violations_of(tmp_path, source)
        sn = [v for v in violations if v.check == CHECK_STEP_NARRATION]
        assert sn
        assert all(v.severity == SEVERITY_WARNING for v in sn)

    def test_non_step_comment_clean(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                # Initialize the system
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_STEP_NARRATION not in _checks(violations)

    def test_step_narration_suppressed(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                # Step 1: Initialize  # ai-slop-ok: tutorial code
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_STEP_NARRATION not in _checks(violations)


# ---------------------------------------------------------------------------
# TestMarkdownSeparator
# ---------------------------------------------------------------------------


class TestMarkdownSeparator:
    """Tests for md_separator WARNING violations (==== in docstrings)."""

    def test_md_separator_in_docstring(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """
                Title
                =====
                Some content.
                """
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_MD_SEPARATOR in _checks(violations)

    def test_md_separator_is_warning(self, tmp_path: Path) -> None:
        source = '''\
            def fn() -> None:
                """
                Title
                ====
                Body.
                """
                pass
        '''
        violations = _violations_of(tmp_path, source)
        sep = [v for v in violations if v.check == CHECK_MD_SEPARATOR]
        assert sep
        assert all(v.severity == SEVERITY_WARNING for v in sep)

    def test_three_equals_clean(self, tmp_path: Path) -> None:
        """Three = signs should not trigger — only 4+ are flagged."""
        source = '''\
            def fn() -> None:
                """
                x === y is a thing.
                """
                pass
        '''
        # Three === is below threshold of 4
        violations = _violations_of(tmp_path, source)
        sep = [v for v in violations if v.check == CHECK_MD_SEPARATOR]
        assert not sep


# ---------------------------------------------------------------------------
# Exit code tests
# ---------------------------------------------------------------------------


class TestExitCodes:
    """Tests for main() exit code behavior."""

    def test_clean_file_exits_zero(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path,
            '''\
                def fn() -> None:
                    """Compute the result."""
                    pass
            ''',
        )
        result = main([str(p)])
        assert result == 0

    def test_error_violation_exits_one(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path,
            '''\
                def fn(x: int) -> int:
                    """:param x: value"""
                    return x
            ''',
        )
        result = main([str(p)])
        assert result == 1

    def test_warning_non_strict_exits_zero(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path,
            '''\
                """This module provides utilities."""
            ''',
        )
        result = main([str(p)])
        assert result == 0

    def test_warning_strict_exits_two(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path,
            '''\
                """This module provides utilities."""
            ''',
        )
        result = main(["--strict", str(p)])
        assert result == 2

    def test_empty_file_exits_zero(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.py"
        p.write_text("", encoding="utf-8")
        result = main([str(p)])
        assert result == 0
