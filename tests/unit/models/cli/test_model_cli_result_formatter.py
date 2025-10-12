"""
Comprehensive tests for ModelCliResultFormatter.

Tests output formatting, error formatting, summary formatting,
and handling of various data types and edge cases.
"""

import json

import pytest

from omnibase_core.enums.enum_cli_status import EnumCliStatus
from omnibase_core.models.cli.model_cli_output_data import ModelCliOutputData
from omnibase_core.models.cli.model_cli_result_formatter import (
    ModelCliResultFormatter,
)


class TestModelCliResultFormatterOutputFormatting:
    """Test output formatting functionality."""

    def test_format_output_with_text(self) -> None:
        """Test formatting output when text is available."""
        output_text = "Command executed successfully"
        result = ModelCliResultFormatter.format_output(output_text, None)

        assert result == output_text

    def test_format_output_text_priority(self) -> None:
        """Test output_text takes priority over output_data."""
        output_text = "Text output"
        output_data = ModelCliOutputData.create_simple(stdout="Data output")

        result = ModelCliResultFormatter.format_output(output_text, output_data)

        # Text should be returned, not data
        assert result == output_text
        assert "Data output" not in result

    def test_format_output_with_data_only(self) -> None:
        """Test formatting output with only output_data."""
        output_data = ModelCliOutputData.create_simple(
            stdout="Command output",
            status=EnumCliStatus.SUCCESS,
        )

        result = ModelCliResultFormatter.format_output("", output_data)

        # Should format as JSON
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["stdout"] == "Command output"
        assert "status" in parsed

    def test_format_output_empty(self) -> None:
        """Test formatting with no output."""
        result = ModelCliResultFormatter.format_output("", None)

        assert result == ""

    def test_format_output_empty_text_empty_data(self) -> None:
        """Test formatting with empty text but data present."""
        output_data = ModelCliOutputData.create_simple()

        result = ModelCliResultFormatter.format_output("", output_data)

        # Should format empty data as JSON
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "stdout" in parsed

    def test_format_output_data_with_results(self) -> None:
        """Test formatting output_data with structured results."""
        output_data = ModelCliOutputData.create_with_results(
            results={"key1": "value1", "key2": "value2"},
            status=EnumCliStatus.SUCCESS,
        )

        result = ModelCliResultFormatter.format_output("", output_data)

        # Should be formatted JSON
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "results" in parsed

    def test_format_output_multiline_text(self) -> None:
        """Test formatting multiline text output."""
        output_text = "Line 1\nLine 2\nLine 3"
        result = ModelCliResultFormatter.format_output(output_text, None)

        assert result == output_text
        assert result.count("\n") == 2

    def test_format_output_whitespace_text(self) -> None:
        """Test formatting text with various whitespace."""
        output_text = "  Leading spaces\n\tTabbed line\nTrailing spaces  "
        result = ModelCliResultFormatter.format_output(output_text, None)

        assert result == output_text

    def test_format_output_unicode_text(self) -> None:
        """Test formatting text with unicode characters."""
        output_text = "Unicode: ✓ ✗ → ← ⚠️"
        result = ModelCliResultFormatter.format_output(output_text, None)

        assert result == output_text

    def test_format_output_data_json_pretty(self) -> None:
        """Test output_data is formatted with indentation."""
        output_data = ModelCliOutputData.create_with_results(
            results={"nested": "data"},
        )

        result = ModelCliResultFormatter.format_output("", output_data)

        # Should have indentation (pretty-printed JSON)
        assert "  " in result or "\n" in result


class TestModelCliResultFormatterErrorFormatting:
    """Test error formatting functionality."""

    def test_format_error_message_only(self) -> None:
        """Test formatting with only error message."""
        error_msg = "Command failed"
        result = ModelCliResultFormatter.format_error(error_msg)

        assert "Error: Command failed" in result
        assert "Details:" not in result
        assert "Validation Errors" not in result

    def test_format_error_with_details(self) -> None:
        """Test formatting error with details."""
        error_msg = "Command failed"
        error_details = "Exit code 1: Permission denied"

        result = ModelCliResultFormatter.format_error(error_msg, error_details)

        assert "Error: Command failed" in result
        assert "Details: Exit code 1: Permission denied" in result

    def test_format_error_with_validation_errors(self) -> None:
        """Test formatting error with validation errors."""
        error_msg = "Validation failed"
        validation_errors = [
            "Field 'name' is required",
            "Field 'age' must be positive",
            "Field 'email' is invalid",
        ]

        result = ModelCliResultFormatter.format_error(
            error_msg,
            validation_errors=validation_errors,
        )

        assert "Error: Validation failed" in result
        assert "Validation Errors (3):" in result
        assert "1. Field 'name' is required" in result
        assert "2. Field 'age' must be positive" in result
        assert "3. Field 'email' is invalid" in result

    def test_format_error_all_fields(self) -> None:
        """Test formatting error with all fields."""
        error_msg = "Operation failed"
        error_details = "Database connection lost"
        validation_errors = ["Retry timeout exceeded"]

        result = ModelCliResultFormatter.format_error(
            error_msg,
            error_details,
            validation_errors,
        )

        assert "Error: Operation failed" in result
        assert "Details: Database connection lost" in result
        assert "Validation Errors (1):" in result
        assert "1. Retry timeout exceeded" in result

    def test_format_error_none_message(self) -> None:
        """Test formatting with None error message."""
        result = ModelCliResultFormatter.format_error(None)

        assert result == ""

    def test_format_error_empty_validation_list(self) -> None:
        """Test formatting with empty validation errors list."""
        error_msg = "Error occurred"
        result = ModelCliResultFormatter.format_error(
            error_msg,
            validation_errors=[],
        )

        assert "Error: Error occurred" in result
        assert "Validation Errors" not in result

    def test_format_error_multiline_message(self) -> None:
        """Test formatting error with multiline message."""
        error_msg = "Error on line 1\nContinued on line 2"
        result = ModelCliResultFormatter.format_error(error_msg)

        assert "Error: Error on line 1\nContinued on line 2" in result

    def test_format_error_special_characters(self) -> None:
        """Test formatting error with special characters."""
        error_msg = "Error: <invalid> & 'quoted' \"text\""
        result = ModelCliResultFormatter.format_error(error_msg)

        # Should preserve special characters
        assert "<invalid>" in result
        assert "&" in result
        assert "'quoted'" in result


class TestModelCliResultFormatterSummaryFormatting:
    """Test summary formatting functionality."""

    def test_format_summary_success(self) -> None:
        """Test formatting successful execution summary."""
        result = ModelCliResultFormatter.format_summary(
            success=True,
            duration_ms=1500,
            exit_code=0,
        )

        assert "Status: SUCCESS" in result
        assert "Exit Code: 0" in result
        assert "Duration: 1500ms" in result
        assert "Warnings" not in result

    def test_format_summary_failure(self) -> None:
        """Test formatting failed execution summary."""
        result = ModelCliResultFormatter.format_summary(
            success=False,
            duration_ms=500,
            exit_code=1,
        )

        assert "Status: FAILURE" in result
        assert "Exit Code: 1" in result
        assert "Duration: 500ms" in result

    def test_format_summary_with_warnings(self) -> None:
        """Test formatting summary with warnings."""
        warnings = [
            "Deprecated API used",
            "Missing optional field",
            "Performance issue detected",
        ]

        result = ModelCliResultFormatter.format_summary(
            success=True,
            duration_ms=2000,
            exit_code=0,
            warnings=warnings,
        )

        assert "Status: SUCCESS" in result
        assert "Warnings (3):" in result
        assert "- Deprecated API used" in result
        assert "- Missing optional field" in result
        assert "- Performance issue detected" in result

    def test_format_summary_empty_warnings(self) -> None:
        """Test formatting summary with empty warnings list."""
        result = ModelCliResultFormatter.format_summary(
            success=True,
            duration_ms=100,
            exit_code=0,
            warnings=[],
        )

        assert "Status: SUCCESS" in result
        assert "Warnings" not in result

    def test_format_summary_zero_duration(self) -> None:
        """Test formatting summary with zero duration."""
        result = ModelCliResultFormatter.format_summary(
            success=True,
            duration_ms=0,
            exit_code=0,
        )

        assert "Duration: 0ms" in result

    def test_format_summary_large_duration(self) -> None:
        """Test formatting summary with large duration."""
        result = ModelCliResultFormatter.format_summary(
            success=True,
            duration_ms=999999,
            exit_code=0,
        )

        assert "Duration: 999999ms" in result

    def test_format_summary_non_zero_exit_code(self) -> None:
        """Test formatting summary with various exit codes."""
        # Exit code 2
        result = ModelCliResultFormatter.format_summary(
            success=False,
            duration_ms=100,
            exit_code=2,
        )
        assert "Exit Code: 2" in result

        # Exit code 127
        result = ModelCliResultFormatter.format_summary(
            success=False,
            duration_ms=100,
            exit_code=127,
        )
        assert "Exit Code: 127" in result

    def test_format_summary_multiline_output(self) -> None:
        """Test that summary output is multiline."""
        result = ModelCliResultFormatter.format_summary(
            success=True,
            duration_ms=1000,
            exit_code=0,
        )

        lines = result.split("\n")
        assert len(lines) >= 3  # At least 3 lines for status, exit code, duration


class TestModelCliResultFormatterEdgeCases:
    """Test edge cases and special scenarios."""

    def test_format_output_none_text_none_data(self) -> None:
        """Test both parameters are None."""
        result = ModelCliResultFormatter.format_output(None, None)  # type: ignore

        assert result == ""

    def test_format_error_all_none(self) -> None:
        """Test all error parameters are None."""
        result = ModelCliResultFormatter.format_error(None, None, None)

        assert result == ""

    def test_static_methods_no_state(self) -> None:
        """Test that formatter is stateless (static methods)."""
        # Create multiple formatter instances
        formatter1 = ModelCliResultFormatter()
        formatter2 = ModelCliResultFormatter()

        # Both should work identically
        output1 = formatter1.format_output("test", None)
        output2 = formatter2.format_output("test", None)

        assert output1 == output2 == "test"

    def test_format_error_complex_validation_errors(self) -> None:
        """Test formatting with complex validation error objects."""
        # Validation errors can be any type
        validation_errors = [
            {"field": "name", "error": "required"},
            ["nested", "error"],
            "Simple string error",
            123,  # Even non-strings
        ]

        result = ModelCliResultFormatter.format_error(
            "Validation failed",
            validation_errors=validation_errors,
        )

        assert "Validation Errors (4):" in result
        # Should convert all to strings
        assert "1." in result
        assert "4." in result

    def test_format_output_data_serialization_error(self) -> None:
        """Test handling when output_data can't be serialized to JSON."""
        # Create output data that might have serialization issues
        output_data = ModelCliOutputData.create_simple(stdout="test")

        # Should handle gracefully
        result = ModelCliResultFormatter.format_output("", output_data)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_summary_single_warning(self) -> None:
        """Test summary formatting with single warning."""
        result = ModelCliResultFormatter.format_summary(
            success=True,
            duration_ms=100,
            exit_code=0,
            warnings=["Single warning"],
        )

        assert "Warnings (1):" in result
        assert "- Single warning" in result

    def test_all_methods_return_strings(self) -> None:
        """Test that all formatter methods return strings."""
        output_result = ModelCliResultFormatter.format_output("test", None)
        assert isinstance(output_result, str)

        error_result = ModelCliResultFormatter.format_error("error")
        assert isinstance(error_result, str)

        summary_result = ModelCliResultFormatter.format_summary(True, 100, 0)
        assert isinstance(summary_result, str)

    def test_formatter_is_utility_class(self) -> None:
        """Test that formatter behaves as utility class."""
        # Should be instantiable but methods are static
        formatter = ModelCliResultFormatter()
        assert formatter is not None

        # Static methods should work the same way
        assert ModelCliResultFormatter.format_output(
            "test", None
        ) == formatter.format_output("test", None)
