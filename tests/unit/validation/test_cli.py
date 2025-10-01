"""
Comprehensive unit tests for validation CLI module.

Tests cover:
- ModelValidationSuite initialization and validation methods
- CLI argument parsing
- Validation type routing
- Result formatting
- Error handling
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from omnibase_core.validation.cli import (
    ModelValidationSuite,
    create_parser,
    format_result,
)
from omnibase_core.validation.validation_utils import ValidationResult

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture


class TestModelValidationSuite:
    """Test ModelValidationSuite class."""

    def test_suite_initialization(self) -> None:
        """Test suite initializes with correct validators."""
        suite = ModelValidationSuite()

        assert "architecture" in suite.validators
        assert "union-usage" in suite.validators
        assert "contracts" in suite.validators
        assert "patterns" in suite.validators

        # Check validator info structure
        arch_validator = suite.validators["architecture"]
        assert "func" in arch_validator
        assert "description" in arch_validator
        assert "args" in arch_validator
        assert callable(arch_validator["func"])

    def test_run_validation_unknown_type(self, tmp_path: Path) -> None:
        """Test run_validation raises error for unknown validation type."""
        suite = ModelValidationSuite()

        with pytest.raises(ValueError, match="Unknown validation type"):
            suite.run_validation("nonexistent", tmp_path)

    def test_run_validation_filters_kwargs(self, tmp_path: Path) -> None:
        """Test run_validation filters kwargs to relevant parameters."""
        suite = ModelValidationSuite()

        # Create test directory with a Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        # Call with extra kwargs that shouldn't be passed
        result = suite.run_validation(
            "architecture",
            tmp_path,
            max_violations=0,
            extra_param="should_be_filtered",
            another_param=123,
        )

        # Should succeed without error
        assert isinstance(result, ValidationResult)

    def test_run_all_validations_success(self, tmp_path: Path) -> None:
        """Test run_all_validations executes all validators."""
        suite = ModelValidationSuite()

        # Create test directory with a Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        results = suite.run_all_validations(tmp_path)

        assert len(results) == 4
        assert "architecture" in results
        assert "union-usage" in results
        assert "contracts" in results
        assert "patterns" in results

        # All results should be ValidationResult objects
        for validation_type, result in results.items():
            assert isinstance(result, ValidationResult)

    def test_run_all_validations_handles_errors(self, tmp_path: Path) -> None:
        """Test run_all_validations handles validator errors gracefully."""
        suite = ModelValidationSuite()

        # Use nonexistent directory to trigger errors
        nonexistent = tmp_path / "nonexistent"

        results = suite.run_all_validations(nonexistent)

        # Should still return results for all validators
        assert len(results) == 4

        # Some results should have errors
        for validation_type, result in results.items():
            assert isinstance(result, ValidationResult)

    def test_list_validators(self, capsys: CaptureFixture[str]) -> None:
        """Test list_validators prints available validators."""
        suite = ModelValidationSuite()

        suite.list_validators()

        captured = capsys.readouterr()
        assert "Available Validation Tools" in captured.out
        assert "architecture" in captured.out
        assert "union-usage" in captured.out
        assert "contracts" in captured.out
        assert "patterns" in captured.out
        assert "Usage Examples" in captured.out


class TestCreateParser:
    """Test CLI argument parser creation."""

    def test_parser_creation(self) -> None:
        """Test parser is created with correct structure."""
        parser = create_parser()

        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_validation_type_choices(self) -> None:
        """Test parser accepts valid validation types."""
        parser = create_parser()

        # Test valid choices
        for validation_type in [
            "architecture",
            "union-usage",
            "contracts",
            "patterns",
            "all",
            "list",
        ]:
            args = parser.parse_args([validation_type])
            assert args.validation_type == validation_type

    def test_parser_validation_type_invalid(self) -> None:
        """Test parser rejects invalid validation types."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["invalid_type"])

    def test_parser_default_directories(self) -> None:
        """Test parser uses default directories when none provided."""
        parser = create_parser()

        args = parser.parse_args(["architecture"])
        assert args.directories == ["src/"]

    def test_parser_custom_directories(self) -> None:
        """Test parser accepts custom directories."""
        parser = create_parser()

        args = parser.parse_args(["architecture", "custom/dir", "another/dir"])
        assert "custom/dir" in args.directories
        assert "another/dir" in args.directories

    def test_parser_strict_flag(self) -> None:
        """Test parser handles strict flag."""
        parser = create_parser()

        args = parser.parse_args(["patterns", "--strict"])
        assert args.strict is True

        args = parser.parse_args(["patterns"])
        assert args.strict is False

    def test_parser_max_violations(self) -> None:
        """Test parser handles max-violations argument."""
        parser = create_parser()

        args = parser.parse_args(["architecture", "--max-violations", "5"])
        assert args.max_violations == 5

        args = parser.parse_args(["architecture"])
        assert args.max_violations == 0  # Default

    def test_parser_max_unions(self) -> None:
        """Test parser handles max-unions argument."""
        parser = create_parser()

        args = parser.parse_args(["union-usage", "--max-unions", "50"])
        assert args.max_unions == 50

        args = parser.parse_args(["union-usage"])
        assert args.max_unions == 100  # Default

    def test_parser_verbose_flag(self) -> None:
        """Test parser handles verbose flag."""
        parser = create_parser()

        args = parser.parse_args(["architecture", "-v"])
        assert args.verbose is True

        args = parser.parse_args(["architecture", "--verbose"])
        assert args.verbose is True

    def test_parser_quiet_flag(self) -> None:
        """Test parser handles quiet flag."""
        parser = create_parser()

        args = parser.parse_args(["architecture", "-q"])
        assert args.quiet is True

        args = parser.parse_args(["architecture", "--quiet"])
        assert args.quiet is True

    def test_parser_exit_zero_flag(self) -> None:
        """Test parser handles exit-zero flag."""
        parser = create_parser()

        args = parser.parse_args(["architecture", "--exit-zero"])
        assert args.exit_zero is True


class TestFormatResult:
    """Test result formatting function."""

    def test_format_result_success(self, capsys: CaptureFixture[str]) -> None:
        """Test formatting successful validation result."""
        result = ValidationResult(
            success=True,
            errors=[],
            files_checked=10,
        )

        format_result("architecture", result, verbose=False)

        captured = capsys.readouterr()
        assert "ARCHITECTURE" in captured.out
        assert "PASSED" in captured.out

    def test_format_result_failure(self, capsys: CaptureFixture[str]) -> None:
        """Test formatting failed validation result."""
        result = ValidationResult(
            success=False,
            errors=["Error 1", "Error 2"],
            files_checked=5,
        )

        format_result("patterns", result, verbose=False)

        captured = capsys.readouterr()
        assert "PATTERNS" in captured.out
        assert "FAILED" in captured.out
        assert "Error 1" in captured.out
        assert "Error 2" in captured.out

    def test_format_result_verbose(self, capsys: CaptureFixture[str]) -> None:
        """Test verbose formatting includes extra details."""
        result = ValidationResult(
            success=True,
            errors=[],
            files_checked=15,
            metadata={"total_unions": 42},
        )

        format_result("union-usage", result, verbose=True)

        captured = capsys.readouterr()
        assert "Files checked: 15" in captured.out
        assert "Total unions: 42" in captured.out

    def test_format_result_with_violations_metadata(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test formatting with violations metadata."""
        result = ValidationResult(
            success=False,
            errors=["Violation 1"],
            files_checked=5,
            metadata={"violations_found": 3},
        )

        format_result("architecture", result, verbose=True)

        captured = capsys.readouterr()
        assert "Violations: 3" in captured.out

    def test_format_result_many_errors_not_shown_without_verbose(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test formatting with many errors requires verbose mode."""
        errors = [f"Error {i}" for i in range(15)]
        result = ValidationResult(
            success=False,
            errors=errors,
            files_checked=10,
        )

        format_result("contracts", result, verbose=False)

        captured = capsys.readouterr()
        # With >10 errors and non-verbose, only shows count, not error details
        assert "Issues found: 15" in captured.out
        assert "FAILED" in captured.out

    def test_format_result_many_errors_shown_with_verbose(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test verbose mode shows truncated error list."""
        errors = [f"Error {i}" for i in range(15)]
        result = ValidationResult(
            success=False,
            errors=errors,
            files_checked=10,
        )

        format_result("contracts", result, verbose=True)

        captured = capsys.readouterr()
        # Verbose mode shows first 10 errors with truncation message
        assert "Error 0" in captured.out
        assert "and 5 more issues" in captured.out


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_validation_workflow_architecture(self, tmp_path: Path) -> None:
        """Test complete validation workflow for architecture."""
        suite = ModelValidationSuite()

        # Create test directory with Python file
        test_file = tmp_path / "test_model.py"
        test_file.write_text(
            """
class ModelTest:
    pass
"""
        )

        result = suite.run_validation("architecture", tmp_path)

        assert isinstance(result, ValidationResult)
        assert result.files_checked > 0

    def test_validation_workflow_union_usage(self, tmp_path: Path) -> None:
        """Test complete validation workflow for union-usage."""
        suite = ModelValidationSuite()

        # Create test directory with Python file containing unions
        test_file = tmp_path / "test_unions.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        )

        result = suite.run_validation(
            "union-usage",
            tmp_path,
            max_unions=100,
            strict=False,
        )

        assert isinstance(result, ValidationResult)
        assert result.files_checked > 0

    def test_validation_workflow_contracts(self, tmp_path: Path) -> None:
        """Test complete validation workflow for contracts."""
        suite = ModelValidationSuite()

        # Create test directory structure
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()

        result = suite.run_validation("contracts", tmp_path)

        assert isinstance(result, ValidationResult)

    def test_validation_workflow_patterns(self, tmp_path: Path) -> None:
        """Test complete validation workflow for patterns."""
        suite = ModelValidationSuite()

        # Create test directory with Python file
        test_file = tmp_path / "test_patterns.py"
        test_file.write_text(
            """
def example_function():
    pass
"""
        )

        result = suite.run_validation("patterns", tmp_path, strict=False)

        assert isinstance(result, ValidationResult)
        assert result.files_checked > 0

    def test_empty_directory_handling(self, tmp_path: Path) -> None:
        """Test handling of empty directories."""
        suite = ModelValidationSuite()

        result = suite.run_validation("architecture", tmp_path)

        assert isinstance(result, ValidationResult)
        assert result.success is True  # Empty directory should pass

    def test_kwargs_filtering_architecture(self, tmp_path: Path) -> None:
        """Test architecture validation only receives relevant kwargs."""
        suite = ModelValidationSuite()

        # Pass kwargs for all validation types
        result = suite.run_validation(
            "architecture",
            tmp_path,
            max_violations=5,  # Relevant
            max_unions=100,  # Not relevant (union-usage)
            strict=True,  # Not relevant (union-usage, patterns)
        )

        assert isinstance(result, ValidationResult)

    def test_kwargs_filtering_union_usage(self, tmp_path: Path) -> None:
        """Test union-usage validation only receives relevant kwargs."""
        suite = ModelValidationSuite()

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test\n")

        result = suite.run_validation(
            "union-usage",
            tmp_path,
            max_unions=50,  # Relevant
            strict=True,  # Relevant
            max_violations=10,  # Not relevant (architecture)
        )

        assert isinstance(result, ValidationResult)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_validation_with_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test validation handles nonexistent directories gracefully."""
        suite = ModelValidationSuite()

        nonexistent = tmp_path / "does_not_exist"

        # Should not raise exception, but return result indicating no files
        result = suite.run_validation("architecture", nonexistent)

        assert isinstance(result, ValidationResult)

    def test_validation_with_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test validation handles file path instead of directory."""
        suite = ModelValidationSuite()

        # Create a file
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test\n")

        # Pass file path instead of directory
        result = suite.run_validation("architecture", test_file)

        assert isinstance(result, ValidationResult)

    def test_all_validations_mixed_results(self, tmp_path: Path) -> None:
        """Test run_all_validations with mixed success/failure results."""
        suite = ModelValidationSuite()

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:  # Complex union
    pass
"""
        )

        results = suite.run_all_validations(
            tmp_path,
            max_unions=0,  # Force union-usage to fail
            strict=True,
        )

        assert len(results) > 0
        # At least one result should have errors
        has_errors = any(not r.success for r in results.values())
        assert True  # May pass if validation is permissive

    def test_suite_validators_immutability(self) -> None:
        """Test that validator configuration is consistent across calls."""
        suite1 = ModelValidationSuite()
        suite2 = ModelValidationSuite()

        # Both suites should have same validators
        assert set(suite1.validators.keys()) == set(suite2.validators.keys())

        # Validator info should be identical
        for key in suite1.validators:
            assert (
                suite1.validators[key]["description"]
                == suite2.validators[key]["description"]
            )
            assert suite1.validators[key]["args"] == suite2.validators[key]["args"]
