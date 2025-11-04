"""
Tests for check_error_raising.py validation hook.

Validates that the error raising detection correctly identifies standard
exception raises and enforces OnexError usage.
"""

import ast
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

from check_error_raising import ErrorRaisingDetector, check_file

from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestErrorRaisingDetector:
    """Test suite for ErrorRaisingDetector."""

    def test_detects_value_error_raise(self):
        """Test detection of ValueError raises."""
        code = """
def validate_input(value):
    if value < 0:
        raise ValueError("Value must be positive")
    return value
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "ValueError"
        assert detector.violations[0]["type"] == "standard_exception_raise"

    def test_detects_type_error_raise(self):
        """Test detection of TypeError raises."""
        code = """
def process_data(data):
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    return data
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "TypeError"

    def test_detects_runtime_error_raise(self):
        """Test detection of RuntimeError raises."""
        code = """
def execute():
    raise RuntimeError("Execution failed")
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "RuntimeError"

    def test_detects_key_error_raise(self):
        """Test detection of KeyError raises."""
        code = """
def get_value(data, key):
    if key not in data:
        raise KeyError(f"Key {key} not found")
    return data[key]
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "KeyError"

    def test_allows_onex_error_raise(self):
        """Test that OnexError raises are allowed."""
        code = """
from omnibase_core.errors.error_codes import OnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode

def validate_input(value):
    if value < 0:
        raise OnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Value must be positive"
        )
    return value
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_error_ok_comment(self):
        """Test that # error-ok: comment allows standard exceptions."""
        code = """
def process_data(data):
    raise ValueError("Test value")  # error-ok: testing purposes only
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_exception_catching(self):
        """Test that catching exceptions (not raising) is allowed."""
        code = """
def process_data(data):
    try:
        return int(data)
    except ValueError as e:
        return None
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_reraise_as_onex_error(self):
        """Test that re-raising as OnexError is allowed."""
        code = """
from omnibase_core.errors.error_codes import OnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode

def process_data(data):
    try:
        return int(data)
    except ValueError as e:
        raise OnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Invalid data format"
        ) from e
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_detects_generic_exception_raise(self):
        """Test detection of generic Exception raises."""
        code = """
def process():
    raise Exception("Something went wrong")
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "Exception"

    def test_allows_bare_reraise(self):
        """Test that bare re-raise (raise without expression) is allowed."""
        code = """
def process():
    try:
        do_something()
    except ValueError:
        log_error()
        raise
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_detects_not_implemented_error_without_stub_ok(self):
        """Test detection of NotImplementedError without stub-ok comment."""
        code = """
def abstract_method():
    raise NotImplementedError("Must be implemented by subclass")
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "NotImplementedError"

    def test_allows_not_implemented_error_with_stub_ok(self):
        """Test that NotImplementedError with stub-ok comment is allowed."""
        code = """
def abstract_method():
    raise NotImplementedError("Must be implemented")  # stub-ok: abstract method
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_detects_multiple_violations(self):
        """Test detection of multiple violations in one file."""
        code = """
def validate(value):
    if value < 0:
        raise ValueError("Negative value")
    if value > 100:
        raise TypeError("Value too large")
    return value
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 2
        exceptions = {v["exception"] for v in detector.violations}
        assert exceptions == {"ValueError", "TypeError"}


class TestCheckFile:
    """Test suite for check_file function."""

    def test_check_file_with_violations(self):
        """Test checking a file with violations."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def process():
    raise ValueError("Test error")
"""
            )
            f.flush()
            temp_path = Path(f.name)

        try:
            violations = check_file(temp_path)
            assert len(violations) == 1
            assert violations[0]["exception"] == "ValueError"
        finally:
            temp_path.unlink()

    def test_check_file_without_violations(self):
        """Test checking a file without violations."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from omnibase_core.errors.error_codes import OnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode

def process():
    raise OnexError(error_code=EnumCoreErrorCode.VALIDATION_ERROR, message="Test")
"""
            )
            f.flush()
            temp_path = Path(f.name)

        try:
            violations = check_file(temp_path)
            assert len(violations) == 0
        finally:
            temp_path.unlink()

    def test_skips_test_files(self):
        """Test that test files in tests/ directory are skipped."""
        # Create a temp directory that includes "tests/" in the path
        import os

        temp_dir = tempfile.mkdtemp()
        tests_dir = Path(temp_dir) / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_sample.py"
        test_file.write_text(
            """
def test_something():
    raise ValueError("Test error")  # OK in test files
"""
        )

        try:
            violations = check_file(test_file)
            # Test files in tests/ directory should be skipped, so no violations
            assert len(violations) == 0
        finally:
            test_file.unlink()
            tests_dir.rmdir()
            Path(temp_dir).rmdir()

    def test_handles_syntax_error(self):
        """Test handling of syntax errors in files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def process():
    raise ValueError("Test"
# Missing closing parenthesis
"""
            )
            f.flush()
            temp_path = Path(f.name)

        try:
            violations = check_file(temp_path)
            assert len(violations) == 1
            assert violations[0]["type"] == "syntax_error"
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
