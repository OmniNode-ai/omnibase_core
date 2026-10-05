# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Port the original AI-slop assertions onto the canonical node."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from omnibase_core.models.nodes.ai_slop_check.model_ai_slop_check_input import (
    ModelAiSlopCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
)
from omnibase_core.nodes.node_ai_slop_check_compute.handler import (
    NodeAiSlopCheckCompute,
)
from omnibase_core.nodes.node_ai_slop_check_compute.rules_ai_slop import (
    resolve_script_rules,
)
from omnibase_core.nodes.node_ai_slop_check_compute.runtime_ai_slop_check import main

pytestmark = pytest.mark.unit

CHECK_SYCOPHANCY = "sycophancy"
CHECK_REST_DOCSTRING = "rest_docstring"
CHECK_BOILERPLATE_DOCSTRING = "boilerplate_docstring"
CHECK_STEP_NARRATION = "step_narration"
CHECK_MD_SEPARATOR = "md_separator"
# Original script ERROR and WARNING map to canonical FAIL and WARN findings.
SEVERITY_ERROR = "FAIL"
SEVERITY_WARNING = "WARN"
SUPPRESSION_MARKER = "ai-slop" + "-ok"


def _write_py(tmp_path: Path, source: str) -> Path:
    """Write the original source, reconstructing literal suppression markers."""
    p = tmp_path / "test_subject.py"
    p.write_text(
        textwrap.dedent(source).replace("{suppression}", SUPPRESSION_MARKER),
        encoding="utf-8",
    )
    return p


def _write_md(tmp_path: Path, source: str) -> Path:
    p = tmp_path / "test_subject.md"
    p.write_text(textwrap.dedent(source), encoding="utf-8")
    return p


def _check_source(path: Path) -> list[ModelValidationFindingEmbed]:
    report = NodeAiSlopCheckCompute().handle(
        ModelAiSlopCheckInput(
            files=[
                ModelSourceFile(path=str(path), source=path.read_text(encoding="utf-8"))
            ],
            rules=resolve_script_rules(Path.cwd(), docstrings=True)
            + resolve_script_rules(Path.cwd(), docstrings=False),
            fallback_docstring_rules=resolve_script_rules(Path.cwd(), docstrings=True),
        )
    )
    return list(report.findings)


def _violations_of(tmp_path: Path, source: str) -> list[ModelValidationFindingEmbed]:
    return _check_source(_write_py(tmp_path, source))


def _violations_of_md(tmp_path: Path, source: str) -> list[ModelValidationFindingEmbed]:
    return _check_source(_write_md(tmp_path, source))


def _checks(violations: list[ModelValidationFindingEmbed]) -> list[str | None]:
    return [v.rule_id for v in violations]


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
        bp = [v for v in violations if v.rule_id == CHECK_BOILERPLATE_DOCSTRING]
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
            def do_thing():  # {suppression}: legacy docstring
                """This function provides things."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING not in _checks(violations)

    def test_suppression_on_docstring_line(self, tmp_path: Path) -> None:
        source = '''\
            def do_thing():
                """This function provides things."""  # {suppression}: approved
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING not in _checks(violations)

    def test_suppression_on_preceding_line(self, tmp_path: Path) -> None:
        source = '''\
            # {suppression}: approved boilerplate for compatibility
            def do_thing():
                """This function provides things."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_BOILERPLATE_DOCSTRING not in _checks(violations)


# TestRestDocstring


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
        rest = [v for v in violations if v.rule_id == CHECK_REST_DOCSTRING]
        assert len(rest) >= 1

    def test_rest_is_error(self, tmp_path: Path) -> None:
        source = '''\
            def fn(x: int) -> int:
                """:param x: value"""
                return x
        '''
        violations = _violations_of(tmp_path, source)
        rest = [v for v in violations if v.rule_id == CHECK_REST_DOCSTRING]
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
            class Foo:  # {suppression}: third-party compat
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
                """:param x: value"""  # {suppression}: external API
                return x
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING not in _checks(violations)

    def test_suppression_on_preceding_line(self, tmp_path: Path) -> None:
        source = '''\
            # {suppression}: compatible with sphinx
            def fn(x: int) -> int:
                """:param x: value"""
                return x
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_REST_DOCSTRING not in _checks(violations)


# TestSycophancy


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
        syco = [v for v in violations if v.rule_id == CHECK_SYCOPHANCY]
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
            def fn() -> None:  # {suppression}: intentional tone
                """Excellent! This is well-designed."""
                pass
        '''
        violations = _violations_of(tmp_path, source)
        assert CHECK_SYCOPHANCY not in _checks(violations)


# TestStepNarration


class TestStepNarration:
    """Tests for step_narration WARNING violations (line-based, outside docstrings)."""

    def test_step_narration_colon(self, tmp_path: Path) -> None:
        source = """\
            ## Step 1: Initialize the system

            Some prose here.
        """
        violations = _violations_of_md(tmp_path, source)
        assert CHECK_STEP_NARRATION in _checks(violations)

    def test_step_narration_dash(self, tmp_path: Path) -> None:
        source = """\
            ## Step 2 - Connect to database

            Some prose here.
        """
        violations = _violations_of_md(tmp_path, source)
        assert CHECK_STEP_NARRATION in _checks(violations)

    def test_step_narration_is_warning(self, tmp_path: Path) -> None:
        source = """\
            ## Step 3: Do the thing

            Some prose here.
        """
        violations = _violations_of_md(tmp_path, source)
        sn = [v for v in violations if v.rule_id == CHECK_STEP_NARRATION]
        assert sn
        assert all(v.severity == SEVERITY_WARNING for v in sn)

    def test_non_step_comment_clean(self, tmp_path: Path) -> None:
        source = """\
            def fn() -> None:
                # Initialize the system
                pass
        """
        violations = _violations_of(tmp_path, source)
        assert CHECK_STEP_NARRATION not in _checks(violations)

    def test_step_narration_suppressed(self, tmp_path: Path) -> None:
        source = """\
            def fn() -> None:
                # Step 1: Initialize  # {suppression}: tutorial code
                pass
        """
        violations = _violations_of(tmp_path, source)
        assert CHECK_STEP_NARRATION not in _checks(violations)


# TestMarkdownSeparator


class TestMarkdownSeparator:
    """Tests for md_separator WARNING violations (four-or-more = signs in docstrings)."""

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
        sep = [v for v in violations if v.rule_id == CHECK_MD_SEPARATOR]
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
        sep = [v for v in violations if v.rule_id == CHECK_MD_SEPARATOR]
        assert not sep


# Exit code tests


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

    def test_markdown_file_clean_exits_zero(self, tmp_path: Path) -> None:
        """Markdown files are processed for line-based checks (step_narration)."""
        p = tmp_path / "notes.md"
        p.write_text("# My Notes\n\nSome content here.\n", encoding="utf-8")
        result = main([str(p)])
        assert result == 0

    def test_no_files_exits_zero(self, tmp_path: Path) -> None:
        """Empty file list exits cleanly."""
        result = main([])
        assert result == 0
