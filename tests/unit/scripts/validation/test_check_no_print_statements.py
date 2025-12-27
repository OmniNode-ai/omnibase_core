#!/usr/bin/env python3
"""
Comprehensive tests for the check_no_print_statements.py validation script.

Tests cover:
- PrintStatementDetector AST visitor
- check_docstring_prints() function for docstring print detection
- check_file() function for file-level checking
- Happy paths (no prints)
- Direct print detection
- print-ok comment handling
- Docstring print detection
- Offset calculation for multiline docstrings
- Error handling (file not found, syntax errors)
- Edge cases (empty files, nested print calls, method calls)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the validation script components
# We need to add the scripts directory to path for testing
SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "scripts" / "validation"
)
sys.path.insert(0, str(SCRIPTS_DIR))

# Import after adding to path
# Use importlib to avoid issues with potential filename issues
import importlib.util

spec = importlib.util.spec_from_file_location(
    "check_no_print_statements", SCRIPTS_DIR / "check_no_print_statements.py"
)
if spec is None:
    raise ImportError(
        f"Cannot find module at {SCRIPTS_DIR / 'check_no_print_statements.py'}"
    )
if spec.loader is None:
    raise ImportError("Module spec has no loader")
check_no_print_statements = importlib.util.module_from_spec(spec)
# Add to sys.modules before exec to avoid dataclass issues
sys.modules["check_no_print_statements"] = check_no_print_statements
spec.loader.exec_module(check_no_print_statements)

PrintStatementDetector = check_no_print_statements.PrintStatementDetector
check_docstring_prints = check_no_print_statements.check_docstring_prints
check_file = check_no_print_statements.check_file
main = check_no_print_statements.main

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


@pytest.mark.unit
class TestPrintStatementDetector:
    """Tests for the PrintStatementDetector AST visitor."""

    def test_detects_simple_print(self) -> None:
        """Test detection of simple print() function call."""
        source = """
def foo():
    print("hello")
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        assert len(detector.violations) == 1
        assert detector.violations[0]["type"] == "print_statement"
        assert detector.violations[0]["line"] == 3

    def test_detects_print_with_arguments(self) -> None:
        """Test detection of print() with multiple arguments."""
        source = """
def foo():
    print("hello", "world", sep=", ")
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        assert len(detector.violations) == 1

    def test_detects_multiple_prints(self) -> None:
        """Test detection of multiple print() calls."""
        source = """
def foo():
    print("one")
    print("two")
    print("three")
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        assert len(detector.violations) == 3
        assert detector.violations[0]["line"] == 3
        assert detector.violations[1]["line"] == 4
        assert detector.violations[2]["line"] == 5

    def test_detects_nested_print_in_function(self) -> None:
        """Test detection of print() nested inside another function call."""
        source = """
def foo():
    result = str(print("test"))
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        # Should detect the print call even when nested
        assert len(detector.violations) == 1

    def test_does_not_flag_method_print(self) -> None:
        """Test that obj.print() method calls are NOT flagged."""
        source = """
class Printer:
    def print(self, msg):
        pass

def foo():
    p = Printer()
    p.print("hello")
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        # obj.print() is an Attribute, not a Name, so should not be flagged
        assert len(detector.violations) == 0

    def test_print_ok_same_line(self) -> None:
        """Test that # print-ok: on same line suppresses violation."""
        source = """
def foo():
    print("debug")  # print-ok: debugging output
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        assert len(detector.violations) == 0

    def test_print_ok_line_above(self) -> None:
        """Test that # print-ok: on line above suppresses violation."""
        source = """
def foo():
    # print-ok: debugging output
    print("debug")
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        assert len(detector.violations) == 0

    def test_print_ok_partial_match(self) -> None:
        """Test that # print-ok: comment must contain the full marker."""
        source = """
def foo():
    print("debug")  # print-ok: reason here
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        assert len(detector.violations) == 0

    def test_print_ok_does_not_affect_distant_lines(self) -> None:
        """Test that # print-ok: only affects same line and line below.

        Note: The implementation checks same line AND line above, so a
        # print-ok: comment on line N affects both line N and line N+1.
        """
        source = """
def foo():
    print("first")  # print-ok: this one ok
    x = 1  # buffer line
    print("second")  # no comment - should be flagged
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        # First print is ok, second is flagged (with buffer line between)
        assert len(detector.violations) == 1
        assert detector.violations[0]["line"] == 5

    def test_violation_metadata(self) -> None:
        """Test that violation contains expected metadata."""
        source = """
def foo():
    print("hello")
"""
        source_lines = source.splitlines()
        import ast

        tree = ast.parse(source)
        detector = PrintStatementDetector("test.py", source_lines)
        detector.visit(tree)
        assert len(detector.violations) == 1
        violation = detector.violations[0]
        assert "type" in violation
        assert "line" in violation
        assert "code" in violation
        assert "message" in violation
        assert "severity" in violation
        assert violation["type"] == "print_statement"
        assert violation["severity"] == "error"
        assert "logger" in violation["message"].lower()


@pytest.mark.unit
class TestCheckDocstringPrints:
    """Tests for docstring print detection."""

    def test_detects_print_in_function_docstring(self) -> None:
        """Test detection of print() in function docstring."""
        source = '''
def foo():
    """Example function.

    Example:
        print("hello")
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 1
        assert violations[0]["type"] == "docstring_print"
        assert violations[0]["severity"] == "warning"

    def test_detects_print_in_class_docstring(self) -> None:
        """Test detection of print() in class docstring."""
        source = '''
class Foo:
    """Example class.

    Usage:
        print("hello")
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 1
        assert violations[0]["type"] == "docstring_print"

    def test_detects_print_in_module_docstring(self) -> None:
        """Test detection of print() in module docstring."""
        source = '''"""Module docstring.

Example:
    print("module example")
"""

def foo():
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 1

    def test_detects_multiple_prints_in_docstring(self) -> None:
        """Test detection of multiple print() in docstring."""
        source = '''
def foo():
    """Example.

    Examples:
        print("one")
        print("two")
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 2

    def test_print_ok_in_docstring(self) -> None:
        """Test that # print-ok: in docstring suppresses violation."""
        source = '''
def foo():
    """Example.

    Example:
        print("hello")  # print-ok: showing print for demo
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 0

    def test_no_violation_without_print(self) -> None:
        """Test that docstrings without print() have no violations."""
        source = '''
def foo():
    """Example.

    Example:
        logger.info("hello")
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 0

    def test_multiline_docstring_offset_triple_quote_separate_line(self) -> None:
        """Test offset calculation when opening quotes are on separate line."""
        source = '''def foo():
    """
    Example with print:
        print("test")
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        # Should detect the print and calculate correct line number
        assert len(violations) == 1
        # The print is on line 4 (1-indexed)
        assert violations[0]["line"] == 4

    def test_multiline_docstring_opening_quotes_same_line(self) -> None:
        """Test offset calculation when opening quotes are on same line as content."""
        source = '''def foo():
    """Example with print:
        print("test")
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 1
        # Print is on line 3 (1-indexed)
        assert violations[0]["line"] == 3

    def test_handles_syntax_error_gracefully(self) -> None:
        """Test that syntax errors are handled gracefully."""
        source = """def foo(
    # incomplete
"""
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 0

    def test_async_function_docstring(self) -> None:
        """Test detection of print() in async function docstring."""
        source = '''
async def foo():
    """Example async function.

    Example:
        print("hello")
    """
    pass
'''
        source_lines = source.splitlines()
        violations = check_docstring_prints("test.py", source, source_lines)
        assert len(violations) == 1


@pytest.mark.unit
class TestCheckFile:
    """Tests for file-level checking."""

    def test_clean_file_no_violations(self, tmp_path: Path) -> None:
        """Test that clean files return no violations."""
        test_file = tmp_path / "clean.py"
        test_file.write_text(
            '''
def foo():
    """A function that uses logging."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("hello")
'''
        )
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_file_with_print_returns_violation(self, tmp_path: Path) -> None:
        """Test that files with print() return violations."""
        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
def foo():
    print("hello")
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "print_statement"

    def test_file_with_docstring_print(self, tmp_path: Path) -> None:
        """Test that files with print() in docstrings return warnings."""
        test_file = tmp_path / "docstring.py"
        test_file.write_text(
            '''
def foo():
    """Example.

    Example:
        print("hello")
    """
    pass
'''
        )
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "docstring_print"
        assert violations[0]["severity"] == "warning"

    def test_file_combines_violations(self, tmp_path: Path) -> None:
        """Test that file combines AST and docstring violations."""
        test_file = tmp_path / "both.py"
        test_file.write_text(
            '''
def foo():
    """Example.

    Example:
        print("docstring print")
    """
    print("actual print")
'''
        )
        violations = check_file(test_file)
        assert len(violations) == 2
        types = {v["type"] for v in violations}
        assert "print_statement" in types
        assert "docstring_print" in types

    def test_file_not_found_error(self, tmp_path: Path) -> None:
        """Test that missing files return read_error."""
        test_file = tmp_path / "nonexistent.py"
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "read_error"
        assert violations[0]["severity"] == "error"

    def test_syntax_error_handling(self, tmp_path: Path) -> None:
        """Test that syntax errors return syntax_error violation."""
        test_file = tmp_path / "syntax_error.py"
        test_file.write_text(
            """
def foo(
    # incomplete function
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "syntax_error"
        assert violations[0]["severity"] == "error"

    def test_unicode_decode_error(self, tmp_path: Path) -> None:
        """Test that files with encoding issues return read_error."""
        test_file = tmp_path / "binary.py"
        # Write binary data that cannot be decoded as UTF-8
        test_file.write_bytes(b"\xff\xfe")
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "read_error"


@pytest.mark.unit
class TestEdgeCases:
    """Edge case tests."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test that empty files return no violations."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_file_with_only_docstring(self, tmp_path: Path) -> None:
        """Test file containing only module docstring."""
        test_file = tmp_path / "doconly.py"
        test_file.write_text(
            '''"""Module docstring without print."""
'''
        )
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_file_with_comments_only(self, tmp_path: Path) -> None:
        """Test file containing only comments."""
        test_file = tmp_path / "comments.py"
        test_file.write_text(
            """# This is a comment
# print("not real code")
# Another comment
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_print_in_string_literal_not_flagged(self, tmp_path: Path) -> None:
        """Test that print() in string literals is not flagged as AST violation."""
        test_file = tmp_path / "string.py"
        test_file.write_text(
            """
def foo():
    message = "print() is a function"
    return message
"""
        )
        violations = check_file(test_file)
        # Should not flag the string literal
        assert len(violations) == 0

    def test_print_as_variable_name(self, tmp_path: Path) -> None:
        """Test that print as variable name does not cause issues."""
        # Note: using 'print' as a variable shadows the builtin, but is valid Python
        test_file = tmp_path / "shadow.py"
        test_file.write_text(
            """
def foo():
    print = lambda x: x  # shadows builtin
    return print("test")  # this is calling the lambda
"""
        )
        # The AST still sees print() as a call to Name('print')
        # Our detector flags it because it looks for print by name
        violations = check_file(test_file)
        # This will still be flagged since we detect Name with id='print'
        assert len(violations) == 1

    def test_nested_function_print(self, tmp_path: Path) -> None:
        """Test print() in nested function."""
        test_file = tmp_path / "nested.py"
        test_file.write_text(
            """
def outer():
    def inner():
        print("nested")
    return inner
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 1

    def test_print_in_lambda(self, tmp_path: Path) -> None:
        """Test print() in lambda (unusual but valid)."""
        test_file = tmp_path / "lambda_print.py"
        test_file.write_text(
            """
# Note: print in lambda is unusual but syntactically valid
f = lambda x: print(x) or x
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 1

    def test_print_in_list_comprehension(self, tmp_path: Path) -> None:
        """Test print() in list comprehension (unusual but valid)."""
        test_file = tmp_path / "listcomp.py"
        test_file.write_text(
            """
# Note: print in list comp is unusual but valid
result = [print(x) for x in range(3)]
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 1

    def test_print_with_file_argument(self, tmp_path: Path) -> None:
        """Test print() with file argument still flagged."""
        test_file = tmp_path / "print_file.py"
        test_file.write_text(
            """
import sys

def foo():
    print("error", file=sys.stderr)
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 1

    def test_multiline_print_call(self, tmp_path: Path) -> None:
        """Test multiline print() call detection."""
        test_file = tmp_path / "multiline.py"
        test_file.write_text(
            """
def foo():
    print(
        "hello",
        "world"
    )
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 1
        # Line number should be where print starts
        assert violations[0]["line"] == 3


@pytest.mark.unit
class TestMainFunction:
    """Tests for the main() entry point."""

    def test_main_no_args_shows_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that main with no args shows usage."""
        with patch.object(sys, "argv", ["check_no_print_statements.py"]):
            result = main()
            assert result == 1
            captured = capsys.readouterr()
            assert "Usage:" in captured.out

    def test_main_clean_file_returns_zero(self, tmp_path: Path) -> None:
        """Test that main returns 0 for clean files."""
        test_file = tmp_path / "clean.py"
        test_file.write_text(
            """
def foo():
    pass
"""
        )
        with patch.object(
            sys, "argv", ["check_no_print_statements.py", str(test_file)]
        ):
            result = main()
            assert result == 0

    def test_main_file_with_error_returns_one(self, tmp_path: Path) -> None:
        """Test that main returns 1 for files with errors."""
        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
def foo():
    print("hello")
"""
        )
        with patch.object(
            sys, "argv", ["check_no_print_statements.py", str(test_file)]
        ):
            result = main()
            assert result == 1

    def test_main_file_with_warning_only_returns_zero(self, tmp_path: Path) -> None:
        """Test that main returns 0 for files with only warnings (docstring prints)."""
        test_file = tmp_path / "warning.py"
        test_file.write_text(
            '''
def foo():
    """Example.

    Example:
        print("docstring only")
    """
    pass
'''
        )
        with patch.object(
            sys, "argv", ["check_no_print_statements.py", str(test_file)]
        ):
            result = main()
            # Warnings don't block commit, so returns 0
            assert result == 0

    def test_main_nonexistent_file_skipped(self, tmp_path: Path) -> None:
        """Test that nonexistent files are skipped."""
        test_file = tmp_path / "nonexistent.py"
        with patch.object(
            sys, "argv", ["check_no_print_statements.py", str(test_file)]
        ):
            result = main()
            # File doesn't exist, so no violations
            assert result == 0

    def test_main_non_python_file_skipped(self, tmp_path: Path) -> None:
        """Test that non-Python files are skipped."""
        test_file = tmp_path / "readme.txt"
        test_file.write_text("print('not python')")
        with patch.object(
            sys, "argv", ["check_no_print_statements.py", str(test_file)]
        ):
            result = main()
            # Not a .py file, so skipped
            assert result == 0

    def test_main_multiple_files(self, tmp_path: Path) -> None:
        """Test main with multiple files."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("def foo(): pass")

        bad_file = tmp_path / "bad.py"
        bad_file.write_text('print("hello")')

        with patch.object(
            sys,
            "argv",
            ["check_no_print_statements.py", str(clean_file), str(bad_file)],
        ):
            result = main()
            assert result == 1

    def test_main_output_format(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that main outputs expected format."""
        test_file = tmp_path / "bad.py"
        test_file.write_text('print("hello")')

        with patch.object(
            sys, "argv", ["check_no_print_statements.py", str(test_file)]
        ):
            main()
            captured = capsys.readouterr()
            assert "ONEX Print Statement Validation Failed" in captured.out
            assert "ERRORS" in captured.out
            assert "print-ok:" in captured.out


@pytest.mark.unit
class TestPrintOkCommentVariations:
    """Tests for various # print-ok: comment formats."""

    def test_print_ok_with_reason(self, tmp_path: Path) -> None:
        """Test # print-ok: with reason text."""
        test_file = tmp_path / "ok.py"
        test_file.write_text(
            """
def foo():
    print("CLI output")  # print-ok: CLI tool output
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_print_ok_minimal(self, tmp_path: Path) -> None:
        """Test minimal # print-ok: comment."""
        test_file = tmp_path / "ok.py"
        test_file.write_text(
            """
def foo():
    print("output")  # print-ok:
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_print_ok_with_extra_whitespace_before_hash(self, tmp_path: Path) -> None:
        """Test # print-ok: with extra whitespace before the hash.

        Note: Extra whitespace AFTER the # (like '#   print-ok:') does NOT
        match because the implementation checks for exact '# print-ok:' substring.
        """
        test_file = tmp_path / "ok.py"
        test_file.write_text(
            """
def foo():
    print("output")    # print-ok: reason with space before hash
"""
        )
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_print_ok_whitespace_after_hash_not_recognized(
        self, tmp_path: Path
    ) -> None:
        """Test that extra whitespace after # is NOT recognized.

        The implementation checks for exact '# print-ok:' substring,
        so '#   print-ok:' won't match.
        """
        test_file = tmp_path / "not_ok.py"
        test_file.write_text(
            """
def foo():
    print("output")  #   print-ok:   reason
"""
        )
        violations = check_file(test_file)
        # This will be flagged because '#   print-ok:' != '# print-ok:'
        assert len(violations) == 1

    def test_print_ok_case_sensitive(self, tmp_path: Path) -> None:
        """Test that # print-ok: is case-sensitive."""
        test_file = tmp_path / "case.py"
        test_file.write_text(
            """
def foo():
    print("output")  # PRINT-OK: this won't work
"""
        )
        violations = check_file(test_file)
        # Case-sensitive, so PRINT-OK: doesn't match
        assert len(violations) == 1

    def test_similar_but_different_comment(self, tmp_path: Path) -> None:
        """Test that similar but different comments don't bypass."""
        test_file = tmp_path / "similar.py"
        test_file.write_text(
            """
def foo():
    print("output")  # print-okay: close but not exact
"""
        )
        violations = check_file(test_file)
        # "print-okay:" is not "print-ok:", so should be flagged
        assert len(violations) == 1
