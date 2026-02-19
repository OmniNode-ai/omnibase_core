# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for check_error_raising.py validation hook.

Validates that the error raising detection correctly identifies standard
exception raises and enforces OnexError usage.
"""

import ast
import sys
from pathlib import Path

import pytest

# Add scripts directory to path to import validation hook modules.
# This is needed because check_error_raising.py lives in scripts/validation/
# which is not a Python package (no __init__.py) and is not installed.
# The script is designed to be run standalone, so we add it to sys.path
# to enable testing its functionality from the test suite.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

from check_error_raising import ErrorRaisingDetector, check_file


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
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

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
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

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

    def test_allows_value_error_in_model_validator(self):
        """Test that ValueError in @model_validator is allowed."""
        code = """
from pydantic import model_validator

class MyModel:
    @model_validator(mode="after")
    def validate_something(self):
        if self.value < 0:
            raise ValueError("Value must be positive")
        return self
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        # Should NOT flag ValueError in Pydantic validator
        assert len(detector.violations) == 0

    def test_allows_value_error_in_field_validator(self):
        """Test that ValueError in @field_validator is allowed."""
        code = """
from pydantic import field_validator

class MyModel:
    @field_validator("email")
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_assertion_error_in_pydantic_validator(self):
        """Test that AssertionError in Pydantic validator is allowed."""
        code = """
from pydantic import model_validator

class MyModel:
    @model_validator(mode="after")
    def validate_something(self):
        if not self.valid:
            raise AssertionError("Validation failed")
        return self
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_pydantic_v1_validator_decorator(self):
        """Test that ValueError in @validator (Pydantic v1) is allowed."""
        code = """
from pydantic import validator

class MyModel:
    @validator("age")
    def validate_age(cls, v):
        if v < 0:
            raise ValueError("Age must be positive")
        return v
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_pydantic_v1_root_validator(self):
        """Test that ValueError in @root_validator (Pydantic v1) is allowed."""
        code = """
from pydantic import root_validator

class MyModel:
    @root_validator
    def validate_model(cls, values):
        if values["start"] > values["end"]:
            raise ValueError("Start must be before end")
        return values
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_still_detects_value_error_in_regular_function(self):
        """Test that ValueError in regular functions is still detected."""
        code = """
def regular_function(value):
    if value < 0:
        raise ValueError("Value must be positive")
    return value
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        # Should STILL flag ValueError in regular function
        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "ValueError"

    def test_detects_other_exceptions_in_pydantic_validators(self):
        """Test that non-allowed exceptions in Pydantic validators are still flagged."""
        code = """
from pydantic import model_validator

class MyModel:
    @model_validator(mode="after")
    def validate_something(self):
        if self.value < 0:
            raise RuntimeError("Value must be positive")
        return self
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        # RuntimeError should STILL be flagged even in validator
        assert len(detector.violations) == 1
        assert detector.violations[0]["exception"] == "RuntimeError"

    def test_pydantic_validator_with_nested_functions(self):
        """Test that ValueError in nested functions inside validators is handled."""
        code = """
from pydantic import model_validator

class MyModel:
    @model_validator(mode="after")
    def validate_something(self):
        def nested_check():
            # This should still be allowed as it's inside validator context
            raise ValueError("Nested validation error")

        nested_check()
        return self
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ErrorRaisingDetector("test.py", source_lines)
        detector.visit(tree)

        # Note: This will NOT be allowed because nested_check() doesn't have
        # the decorator. This is intentional - only the decorated function
        # gets the exception, not nested helpers.
        assert len(detector.violations) == 1


class TestCheckFile:
    """Test suite for check_file function."""

    def test_check_file_with_violations(self, tmp_path: Path):
        """Test checking a file with violations."""
        temp_file = tmp_path / "test_violations.py"
        temp_file.write_text(
            """
def process():
    raise ValueError("Test error")
""",
            encoding="utf-8",
        )

        violations = check_file(temp_file)
        assert len(violations) == 1
        assert violations[0]["exception"] == "ValueError"

    def test_check_file_without_violations(self, tmp_path: Path):
        """Test checking a file without violations."""
        temp_file = tmp_path / "test_no_violations.py"
        temp_file.write_text(
            """
from omnibase_core.errors.error_codes import OnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

def process():
    raise OnexError(error_code=EnumCoreErrorCode.VALIDATION_ERROR, message="Test")
""",
            encoding="utf-8",
        )

        violations = check_file(temp_file)
        assert len(violations) == 0

    def test_skips_test_files(self, tmp_path: Path):
        """Test that test files in tests/ directory are skipped."""
        # Create a directory structure that includes "tests/" in the path
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_sample.py"
        test_file.write_text(
            """
def test_something():
    raise ValueError("Test error")  # OK in test files
""",
            encoding="utf-8",
        )

        violations = check_file(test_file)
        # Test files in tests/ directory should be skipped, so no violations
        assert len(violations) == 0

    def test_handles_syntax_error(self, tmp_path: Path):
        """Test handling of syntax errors in files."""
        temp_file = tmp_path / "test_syntax_error.py"
        temp_file.write_text(
            """
def process():
    raise ValueError("Test"
# Missing closing parenthesis
""",
            encoding="utf-8",
        )

        violations = check_file(temp_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "syntax_error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
