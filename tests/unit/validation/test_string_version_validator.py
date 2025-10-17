"""
Comprehensive test suite for StringVersionValidator.

Tests the validation logic that detects ModelSemVer.parse() with string literals
and ensures proper version handling patterns across the codebase.

Coverage:
- Detection of ModelSemVer.parse("1.0.0") patterns
- Allowance of ModelSemVer(1, 0, 0) constructor usage
- Multiple violation detection
- Docstring version string exemption
- Regex pattern exemption
- Line number accuracy reporting
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the validator module directly from its file path
_scripts_path = Path(__file__).parent.parent.parent.parent / "scripts" / "validation"
_validator_path = _scripts_path / "validate-string-versions.py"

# Add scripts/validation to sys.path for timeout_utils import
sys.path.insert(0, str(_scripts_path))

# Load module spec and import it
_spec = importlib.util.spec_from_file_location(
    "validate_string_versions", _validator_path
)
_validator_module = importlib.util.module_from_spec(_spec)
sys.modules["validate_string_versions"] = _validator_module
_spec.loader.exec_module(_validator_module)

# Import the classes we need
PythonASTValidator = _validator_module.PythonASTValidator
StringVersionValidator = _validator_module.StringVersionValidator


class TestStringVersionValidator:
    """Test suite for StringVersionValidator Python file validation."""

    def test_detects_modelsemver_parse_with_string_literal(
        self, tmp_path: Path
    ) -> None:
        """
        Test that ModelSemVer.parse("1.0.0") with string literal is detected.

        This pattern should be flagged as it uses a string literal directly
        instead of the preferred constructor pattern.
        """
        # Create test file with string literal in parse() call
        test_file = tmp_path / "test_version.py"
        test_file.write_text(
            """
from omnibase_core.models.model_semver import ModelSemVer

def get_version():
    return ModelSemVer.parse("1.0.0")
"""
        )

        # Run validator
        validator = StringVersionValidator()
        validator.validate_python_file(test_file)

        # Should detect violation (AST violations don't affect return value)
        assert len(validator.ast_violations) == 1, "Should have exactly one violation"

        violation = validator.ast_violations[0]
        assert violation.violation_type == "semantic_version_string_literal_in_call"
        assert "ModelSemVer.parse" in violation.field_name
        assert "1.0.0" in violation.suggestion
        assert "ModelSemVer(1, 0, 0)" in violation.suggestion

    def test_allows_modelsemver_constructor(self, tmp_path: Path) -> None:
        """
        Test that ModelSemVer(1, 0, 0) constructor pattern is allowed.

        The direct constructor with integer arguments is the preferred
        pattern and should not generate any violations.
        """
        # Create test file with proper constructor usage
        test_file = tmp_path / "test_version.py"
        test_file.write_text(
            """
from omnibase_core.models.model_semver import ModelSemVer

def get_version():
    return ModelSemVer(1, 0, 0)

def get_another_version():
    return ModelSemVer(major=2, minor=1, patch=3)
"""
        )

        # Run validator
        validator = StringVersionValidator()
        result = validator.validate_python_file(test_file)

        # Should pass without violations
        assert result, "Should allow ModelSemVer constructor with integers"
        assert len(validator.ast_violations) == 0, "Should have no violations"
        assert len(validator.errors) == 0, "Should have no errors"

    def test_detects_multiple_violations(self, tmp_path: Path) -> None:
        """
        Test that multiple parse() calls with string literals are all detected.

        Each occurrence should be reported separately with accurate line numbers.
        """
        # Create test file with multiple violations
        test_file = tmp_path / "test_version.py"
        test_file.write_text(
            """
from omnibase_core.models.model_semver import ModelSemVer

def get_version_one():
    return ModelSemVer.parse("1.0.0")

def get_version_two():
    return ModelSemVer.parse("2.1.3")

def get_version_three():
    v1 = ModelSemVer.parse("3.0.0")
    v2 = ModelSemVer.parse("4.2.1")
    return v1, v2
"""
        )

        # Run validator
        validator = StringVersionValidator()
        validator.validate_python_file(test_file)

        # Should detect all 4 violations
        assert len(validator.ast_violations) == 4, "Should detect all 4 parse() calls"

        # Verify each violation
        expected_versions = ["1.0.0", "2.1.3", "3.0.0", "4.2.1"]
        for i, violation in enumerate(validator.ast_violations):
            assert violation.violation_type == "semantic_version_string_literal_in_call"
            assert expected_versions[i] in violation.suggestion

    def test_ignores_docstrings(self, tmp_path: Path) -> None:
        """
        Test that version strings in docstrings are not flagged.

        Docstrings commonly contain version examples and documentation
        that should not trigger violations.
        """
        # Create test file with version strings in docstrings
        test_file = tmp_path / "test_version.py"
        test_file.write_text(
            '''
from omnibase_core.models.model_semver import ModelSemVer

def parse_version(version_str: str):
    """
    Parse a version string.

    Example:
        >>> parse_version("1.0.0")
        ModelSemVer(1, 0, 0)

    Args:
        version_str: Version string like "2.1.3"

    Returns:
        ModelSemVer object
    """
    # This is the proper way - no string literal
    return ModelSemVer(1, 0, 0)

class VersionManager:
    """
    Manages version information.

    Default version is "1.0.0" which gets parsed at runtime.
    """
    pass
'''
        )

        # Run validator
        validator = StringVersionValidator()
        result = validator.validate_python_file(test_file)

        # Should pass - docstrings are exempt
        assert result, "Should ignore version strings in docstrings"
        assert len(validator.ast_violations) == 0, "Should have no violations"

    def test_ignores_regex_patterns(self, tmp_path: Path) -> None:
        """
        Test that regex pattern strings are not flagged.

        Regex patterns for validation often look like version strings
        but should not trigger violations as they're legitimate patterns.
        """
        # Create test file with regex patterns
        test_file = tmp_path / "test_version.py"
        test_file.write_text(
            r'''
import re
from omnibase_core.models.model_semver import ModelSemVer

# Regex pattern for version validation
VERSION_PATTERN = r"^\d+\.\d+\.\d+$"
version_regex = re.compile(r"^\d+\.\d+\.\d+$")

def validate_version_string(s: str) -> bool:
    """Validate version string matches semantic versioning pattern."""
    pattern = r"^\d+\.\d+\.\d+$"
    return bool(re.match(pattern, s))

# This should still be caught - not a regex pattern
def bad_usage():
    return ModelSemVer.parse("1.0.0")
'''
        )

        # Run validator
        validator = StringVersionValidator()
        validator.validate_python_file(test_file)

        # Should only catch the parse() call, not regex patterns
        assert len(validator.ast_violations) == 1, "Should only catch the parse() call"

        violation = validator.ast_violations[0]
        assert "ModelSemVer.parse" in violation.field_name
        assert "1.0.0" in violation.suggestion

    def test_reports_correct_line_numbers(self, tmp_path: Path) -> None:
        """
        Test that violations report accurate line numbers.

        Line number accuracy is critical for developers to quickly
        locate and fix validation issues.
        """
        # Create test file with violations on specific lines
        test_file = tmp_path / "test_version.py"
        content = """
from omnibase_core.models.model_semver import ModelSemVer

# Line 4 (blank)
def first_function():
    # Line 6: First violation here
    return ModelSemVer.parse("1.0.0")

# Line 9 (blank)
def second_function():
    # Line 11: Second violation here
    v = ModelSemVer.parse("2.1.3")
    return v
"""
        test_file.write_text(content)

        # Run validator
        validator = StringVersionValidator()
        validator.validate_python_file(test_file)

        # Should have 2 violations with correct line numbers
        assert len(validator.ast_violations) == 2, "Should detect 2 violations"

        # First violation should be on line 7 (the actual parse call)
        first_violation = validator.ast_violations[0]
        assert (
            first_violation.line_number == 7
        ), f"Expected line 7, got {first_violation.line_number}"
        assert "1.0.0" in first_violation.suggestion

        # Second violation should be on line 12
        second_violation = validator.ast_violations[1]
        assert (
            second_violation.line_number == 12
        ), f"Expected line 12, got {second_violation.line_number}"
        assert "2.1.3" in second_violation.suggestion

    def test_detects_parse_semver_from_string_function(self, tmp_path: Path) -> None:
        """
        Test that parse_semver_from_string() with string literal is also detected.

        The validator should catch both ModelSemVer.parse() and the utility
        function parse_semver_from_string() when used with string literals.
        """
        # Create test file with parse_semver_from_string usage
        test_file = tmp_path / "test_version.py"
        test_file.write_text(
            """
from omnibase_core.utils.version_utils import parse_semver_from_string

def get_version():
    return parse_semver_from_string("1.2.3")
"""
        )

        # Run validator
        validator = StringVersionValidator()
        validator.validate_python_file(test_file)

        # Should detect violation
        assert (
            len(validator.ast_violations) == 1
        ), "Should detect parse_semver_from_string() with string literal"

        violation = validator.ast_violations[0]
        assert violation.violation_type == "semantic_version_string_literal_in_call"
        assert "parse_semver_from_string" in violation.field_name

    def test_mixed_valid_and_invalid_patterns(self, tmp_path: Path) -> None:
        """
        Test file with both valid and invalid patterns.

        Real-world files often mix patterns, so the validator should
        only flag actual violations while allowing valid code.
        """
        # Create test file with mixed patterns
        test_file = tmp_path / "test_version.py"
        test_file.write_text(
            r'''
from omnibase_core.models.model_semver import ModelSemVer
import re

# Valid: Constructor with integers
CURRENT_VERSION = ModelSemVer(1, 0, 0)

# Valid: Regex pattern
VERSION_PATTERN = r"^\d+\.\d+\.\d+$"

def validate_version(s: str) -> bool:
    """Validate version string like "1.0.0"."""
    return bool(re.match(VERSION_PATTERN, s))

# Valid: Constructor from variables
def create_version(major: int, minor: int, patch: int):
    return ModelSemVer(major, minor, patch)

# INVALID: String literal in parse()
def bad_version():
    return ModelSemVer.parse("2.0.0")

# Valid: Parse from parameter
def parse_version(version_str: str):
    return ModelSemVer.parse(version_str)

# INVALID: Another string literal
def another_bad_version():
    v = ModelSemVer.parse("3.1.0")
    return v
'''
        )

        # Run validator
        validator = StringVersionValidator()
        validator.validate_python_file(test_file)

        # Should only catch the 2 invalid patterns
        assert len(validator.ast_violations) == 2, "Should detect exactly 2 violations"

        # Verify the violations are the expected ones
        versions_found = ["2.0.0" in v.suggestion for v in validator.ast_violations] + [
            "3.1.0" in v.suggestion for v in validator.ast_violations
        ]
        assert sum(versions_found) == 2, "Should find both 2.0.0 and 3.1.0 violations"


class TestPythonASTValidator:
    """Test suite for PythonASTValidator AST parsing logic."""

    def test_semantic_version_detection_logic(self) -> None:
        """
        Test the semantic version string detection helper.

        The _is_semantic_version_ast method should correctly identify
        semantic version patterns like X.Y.Z with integer components.
        """
        validator = PythonASTValidator("/fake/path.py")

        # Valid semantic versions
        assert validator._is_semantic_version_ast("1.0.0")
        assert validator._is_semantic_version_ast("2.1.3")
        assert validator._is_semantic_version_ast("10.20.30")
        assert validator._is_semantic_version_ast("0.0.1")

        # Invalid patterns
        assert not validator._is_semantic_version_ast("1.0")  # Only 2 parts
        assert not validator._is_semantic_version_ast("1.0.0.0")  # 4 parts
        assert not validator._is_semantic_version_ast("v1.0.0")  # Has prefix
        assert not validator._is_semantic_version_ast("1.0.0-beta")  # Has suffix
        assert not validator._is_semantic_version_ast("abc.def.ghi")  # Non-numeric
        assert not validator._is_semantic_version_ast("")  # Empty string
        assert not validator._is_semantic_version_ast("version")  # Not a version

    def test_call_function_name_extraction(self) -> None:
        """
        Test extraction of function names from call nodes.

        The validator needs to identify method calls like ModelSemVer.parse()
        to detect violations.
        """
        import ast

        validator = PythonASTValidator("/fake/path.py")

        # Test simple function call
        code = "parse('1.0.0')"
        tree = ast.parse(code)
        call_node = tree.body[0].value
        func_name = validator._get_call_func_name(call_node.func)
        assert func_name == "parse"

        # Test method call
        code = "ModelSemVer.parse('1.0.0')"
        tree = ast.parse(code)
        call_node = tree.body[0].value
        func_name = validator._get_call_func_name(call_node.func)
        assert func_name == "ModelSemVer.parse"

    def test_exception_handling_for_malformed_code(self, tmp_path: Path) -> None:
        """
        Test that validator handles malformed Python files gracefully.

        Syntax errors should be caught and not crash the validator.
        """
        # Create file with syntax error
        test_file = tmp_path / "bad_syntax.py"
        test_file.write_text(
            """
def broken_function(
    # Missing closing parenthesis
"""
        )

        # Run validator
        validator = StringVersionValidator()
        result = validator.validate_python_file(test_file)

        # Should handle gracefully without crashing
        # Syntax errors are skipped as they'll be caught by other tools
        assert result, "Should handle syntax errors gracefully"


class TestStringVersionValidatorYAMLValidation:
    """Test suite for YAML file validation."""

    def test_detects_string_versions_in_yaml(self, tmp_path: Path) -> None:
        """
        Test that string versions in YAML contract files are detected.

        YAML files should use ModelSemVer format instead of string versions.
        """
        # Create YAML file with string version
        yaml_file = tmp_path / "contract.yaml"
        yaml_file.write_text(
            """
version: "1.0.0"
contract_version: "2.1.3"
name: "test_contract"
"""
        )

        # Run validator
        validator = StringVersionValidator()
        result = validator.validate_yaml_file(yaml_file)

        # Should detect violations
        assert not result, "Should detect string versions in YAML"
        assert len(validator.errors) > 0, "Should have error messages"

        # Check error messages contain version fields
        error_text = " ".join(validator.errors)
        assert "version" in error_text.lower()

    def test_allows_modelsemver_format_in_yaml(self, tmp_path: Path) -> None:
        """
        Test that ModelSemVer format in YAML is allowed.

        YAML files using {major: X, minor: Y, patch: Z} format should pass.
        """
        # Create YAML file with proper ModelSemVer format
        yaml_file = tmp_path / "contract.yaml"
        yaml_file.write_text(
            """
version:
  major: 1
  minor: 0
  patch: 0
contract_version:
  major: 2
  minor: 1
  patch: 3
name: "test_contract"
"""
        )

        # Run validator
        validator = StringVersionValidator()
        result = validator.validate_yaml_file(yaml_file)

        # Should pass
        assert result, "Should allow ModelSemVer format in YAML"
        assert len(validator.errors) == 0, "Should have no errors"


class TestStringVersionValidatorEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that validator handles non-existent files gracefully."""
        nonexistent_file = tmp_path / "does_not_exist.py"

        validator = StringVersionValidator()
        result = validator.validate_python_file(nonexistent_file)

        assert not result, "Should fail for non-existent file"
        assert len(validator.errors) > 0, "Should report error"
        assert "does not exist" in validator.errors[0].lower()

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Test that validator handles empty files gracefully."""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        validator = StringVersionValidator()
        result = validator.validate_python_file(empty_file)

        # Empty files should pass
        assert result, "Should handle empty files gracefully"
        assert len(validator.errors) == 0

    def test_handles_large_file_within_limits(self, tmp_path: Path) -> None:
        """Test that validator processes files within size limits."""
        # Create a reasonably large file (under 10MB limit)
        large_file = tmp_path / "large.py"
        content = "# Comment line\n" * 10000  # About 150KB
        large_file.write_text(content)

        validator = StringVersionValidator()
        result = validator.validate_python_file(large_file)

        # Should process successfully
        assert result, "Should handle large files within limits"

    def test_validates_all_files_batch(self, tmp_path: Path) -> None:
        """Test batch validation of multiple files."""
        # Create multiple test files
        file1 = tmp_path / "file1.py"
        file1.write_text(
            """
from omnibase_core.models.model_semver import ModelSemVer
v = ModelSemVer(1, 0, 0)  # Valid
"""
        )

        file2 = tmp_path / "file2.py"
        file2.write_text(
            """
from omnibase_core.models.model_semver import ModelSemVer
v = ModelSemVer.parse("1.0.0")  # Invalid
"""
        )

        file3 = tmp_path / "file3.yaml"
        file3.write_text(
            """
version:
  major: 1
  minor: 0
  patch: 0
"""
        )

        # Validate all files
        validator = StringVersionValidator()
        validator.validate_all_files([file1, file2, file3])

        # Should detect violation in file2
        assert len(validator.ast_violations) == 1, "Should detect violation in file2"
        assert "file2.py" in validator.ast_violations[0].file_path
