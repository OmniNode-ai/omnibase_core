"""
Tests for ModelToolExecutionResult.

Comprehensive test suite for tool execution result model.
Adapted from archived test_model_execution_result.py.

Comprehensive type safety testing required.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.tools.model_tool_execution_result import (
    ModelToolExecutionResult,
)


class TestBasicCreation:
    """Test basic creation and initialization."""

    def test_successful_creation_with_required_fields(self) -> None:
        """Test creating successful execution result with required fields."""
        result = ModelToolExecutionResult(
            tool_name="test_tool",
            success=True,
            output={"result": "success", "value": 42},
        )

        assert result.success is True
        assert result.tool_name == "test_tool"
        assert result.output == {"result": "success", "value": 42}
        assert result.error is None
        assert isinstance(result.execution_id, UUID)
        assert result.execution_time_ms == 0
        assert result.status_code == 0

    def test_error_creation_with_required_fields(self) -> None:
        """Test creating error execution result with required fields."""
        result = ModelToolExecutionResult(
            tool_name="test_tool",
            success=False,
            error="Test error occurred",
        )

        assert result.success is False
        assert result.tool_name == "test_tool"
        assert result.error == "Test error occurred"
        assert result.output == {}
        assert isinstance(result.execution_id, UUID)
        assert result.execution_time_ms == 0
        assert result.status_code == 0

    def test_custom_execution_id(self) -> None:
        """Test creating result with custom execution ID."""
        custom_id = UUID("12345678-1234-5678-9abc-123456789abc")
        result = ModelToolExecutionResult(
            execution_id=custom_id,
            tool_name="test_tool",
            success=True,
        )

        assert result.execution_id == custom_id

    def test_default_execution_id_generation(self) -> None:
        """Test that execution_id is auto-generated if not provided."""
        result1 = ModelToolExecutionResult(tool_name="test_tool", success=True)
        result2 = ModelToolExecutionResult(tool_name="test_tool", success=True)

        assert isinstance(result1.execution_id, UUID)
        assert isinstance(result2.execution_id, UUID)
        assert result1.execution_id != result2.execution_id

    def test_all_fields_provided(self) -> None:
        """Test creating result with all fields explicitly provided."""
        custom_id = uuid4()
        result = ModelToolExecutionResult(
            execution_id=custom_id,
            tool_name="comprehensive_tool",
            success=True,
            output={"status": "complete", "items": 10},
            error=None,
            execution_time_ms=1250,
            status_code=200,
        )

        assert result.execution_id == custom_id
        assert result.tool_name == "comprehensive_tool"
        assert result.success is True
        assert result.output == {"status": "complete", "items": 10}
        assert result.error is None
        assert result.execution_time_ms == 1250
        assert result.status_code == 200


class TestSuccessScenarios:
    """Test various success scenarios."""

    def test_success_with_simple_output(self) -> None:
        """Test successful execution with simple output data."""
        result = ModelToolExecutionResult(
            tool_name="simple_tool",
            success=True,
            output={"message": "Task completed"},
        )

        assert result.success is True
        assert result.output["message"] == "Task completed"
        assert result.error is None

    def test_success_with_complex_output(self) -> None:
        """Test successful execution with complex structured output."""
        complex_output = {
            "count": 42,
            "status": "completed",
            "rate": 98.5,
            "flag": True,
        }
        result = ModelToolExecutionResult(
            tool_name="complex_tool",
            success=True,
            output=complex_output,
        )

        assert result.success is True
        assert result.output["count"] == 42
        assert result.output["status"] == "completed"
        assert result.output["rate"] == 98.5
        assert result.output["flag"] is True

    def test_success_with_empty_output(self) -> None:
        """Test successful execution with empty output (default)."""
        result = ModelToolExecutionResult(
            tool_name="empty_tool",
            success=True,
        )

        assert result.success is True
        assert result.output == {}
        assert result.error is None

    def test_success_with_execution_time(self) -> None:
        """Test successful execution with execution time tracking."""
        result = ModelToolExecutionResult(
            tool_name="timed_tool",
            success=True,
            output={"result": "done"},
            execution_time_ms=5000,
        )

        assert result.success is True
        assert result.execution_time_ms == 5000

    def test_success_with_custom_status_code(self) -> None:
        """Test successful execution with custom status code."""
        result = ModelToolExecutionResult(
            tool_name="status_tool",
            success=True,
            output={"result": "ok"},
            status_code=201,
        )

        assert result.success is True
        assert result.status_code == 201


class TestFailureScenarios:
    """Test various failure scenarios."""

    def test_failure_with_error_message(self) -> None:
        """Test failed execution with error message."""
        result = ModelToolExecutionResult(
            tool_name="failing_tool",
            success=False,
            error="Connection timeout",
        )

        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.output == {}

    def test_failure_with_status_code(self) -> None:
        """Test failed execution with non-zero status code."""
        result = ModelToolExecutionResult(
            tool_name="error_tool",
            success=False,
            error="Command failed",
            status_code=1,
        )

        assert result.success is False
        assert result.status_code == 1
        assert result.error == "Command failed"

    def test_failure_with_http_status_code(self) -> None:
        """Test failed execution with HTTP-style status code."""
        result = ModelToolExecutionResult(
            tool_name="api_tool",
            success=False,
            error="Not Found",
            status_code=404,
        )

        assert result.success is False
        assert result.status_code == 404
        assert result.error == "Not Found"

    def test_failure_with_execution_time(self) -> None:
        """Test failed execution with execution time tracking."""
        result = ModelToolExecutionResult(
            tool_name="timeout_tool",
            success=False,
            error="Execution timeout",
            execution_time_ms=30000,
        )

        assert result.success is False
        assert result.execution_time_ms == 30000

    def test_failure_can_have_partial_output(self) -> None:
        """Test that failed execution can include partial output."""
        result = ModelToolExecutionResult(
            tool_name="partial_tool",
            success=False,
            error="Failed after partial completion",
            output={"processed": 50, "total": 100},
        )

        assert result.success is False
        assert result.error == "Failed after partial completion"
        assert result.output["processed"] == 50
        assert result.output["total"] == 100


class TestToolSpecificFields:
    """Test tool-specific fields."""

    def test_tool_name_required(self) -> None:
        """Test that tool_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionResult(success=True)

        assert "tool_name" in str(exc_info.value)

    def test_tool_name_variations(self) -> None:
        """Test various tool name formats."""
        names = [
            "simple_tool",
            "complex-tool-name",
            "tool.with.dots",
            "tool_123",
            "ToolCamelCase",
        ]

        for name in names:
            result = ModelToolExecutionResult(tool_name=name, success=True)
            assert result.tool_name == name

    def test_status_code_variations(self) -> None:
        """Test various status code values."""
        codes = [0, 1, 127, 200, 404, 500]

        for code in codes:
            result = ModelToolExecutionResult(
                tool_name="test_tool",
                success=(code == 0),
                status_code=code,
            )
            assert result.status_code == code

    def test_status_code_default_zero(self) -> None:
        """Test that status_code defaults to 0."""
        result = ModelToolExecutionResult(tool_name="test_tool", success=True)
        assert result.status_code == 0


class TestExecutionTiming:
    """Test execution timing fields."""

    def test_execution_time_default_zero(self) -> None:
        """Test that execution_time_ms defaults to 0."""
        result = ModelToolExecutionResult(tool_name="test_tool", success=True)
        assert result.execution_time_ms == 0

    def test_execution_time_positive_values(self) -> None:
        """Test various positive execution time values."""
        times = [1, 100, 1000, 5000, 60000, 300000]

        for time_ms in times:
            result = ModelToolExecutionResult(
                tool_name="test_tool",
                success=True,
                execution_time_ms=time_ms,
            )
            assert result.execution_time_ms == time_ms

    def test_execution_time_zero_valid(self) -> None:
        """Test that zero execution time is valid (instant execution)."""
        result = ModelToolExecutionResult(
            tool_name="instant_tool",
            success=True,
            execution_time_ms=0,
        )
        assert result.execution_time_ms == 0

    def test_execution_time_negative_rejected(self) -> None:
        """Test that negative execution time is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionResult(
                tool_name="test_tool",
                success=True,
                execution_time_ms=-100,
            )

        assert "execution_time_ms" in str(exc_info.value)


class TestStructuredDataHandling:
    """Test structured data output handling."""

    def test_output_with_string_values(self) -> None:
        """Test output with string values."""
        result = ModelToolExecutionResult(
            tool_name="string_tool",
            success=True,
            output={"message": "success", "status": "ok"},
        )

        assert result.output["message"] == "success"
        assert result.output["status"] == "ok"

    def test_output_with_numeric_values(self) -> None:
        """Test output with various numeric values."""
        result = ModelToolExecutionResult(
            tool_name="numeric_tool",
            success=True,
            output={"count": 42, "rate": 98.5, "percentage": 0.85},
        )

        assert result.output["count"] == 42
        assert result.output["rate"] == 98.5
        assert result.output["percentage"] == 0.85

    def test_output_with_boolean_values(self) -> None:
        """Test output with boolean values."""
        result = ModelToolExecutionResult(
            tool_name="bool_tool",
            success=True,
            output={"enabled": True, "verified": False},
        )

        assert result.output["enabled"] is True
        assert result.output["verified"] is False

    def test_output_with_none_values(self) -> None:
        """Test output with None values."""
        result = ModelToolExecutionResult(
            tool_name="none_tool",
            success=True,
            output={"optional": None, "value": 42},
        )

        assert result.output["optional"] is None
        assert result.output["value"] == 42

    def test_output_with_mixed_types(self) -> None:
        """Test output with mixed primitive types."""
        mixed_output = {
            "string_value": "text",
            "int_value": 123,
            "float_value": 45.67,
            "bool_value": True,
            "none_value": None,
        }
        result = ModelToolExecutionResult(
            tool_name="mixed_tool",
            success=True,
            output=mixed_output,
        )

        assert result.output["string_value"] == "text"
        assert result.output["int_value"] == 123
        assert result.output["float_value"] == 45.67
        assert result.output["bool_value"] is True
        assert result.output["none_value"] is None

    def test_empty_output_dictionary(self) -> None:
        """Test that empty output dictionary is valid."""
        result = ModelToolExecutionResult(
            tool_name="empty_tool",
            success=True,
            output={},
        )

        assert result.output == {}
        assert len(result.output) == 0


class TestFieldValidation:
    """Test Pydantic field validation."""

    def test_success_field_required(self) -> None:
        """Test that success field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionResult(tool_name="test_tool")

        assert "success" in str(exc_info.value)

    def test_success_field_boolean_only(self) -> None:
        """Test that success field must be boolean."""
        result_true = ModelToolExecutionResult(tool_name="test_tool", success=True)
        result_false = ModelToolExecutionResult(tool_name="test_tool", success=False)

        assert result_true.success is True
        assert result_false.success is False

    def test_tool_name_empty_string_valid(self) -> None:
        """Test that empty tool name is technically valid (though not recommended)."""
        result = ModelToolExecutionResult(tool_name="", success=True)
        assert result.tool_name == ""

    def test_error_field_optional(self) -> None:
        """Test that error field is optional."""
        result = ModelToolExecutionResult(tool_name="test_tool", success=True)
        assert result.error is None

    def test_error_field_string_or_none(self) -> None:
        """Test that error field accepts string or None."""
        result_with_error = ModelToolExecutionResult(
            tool_name="test_tool",
            success=False,
            error="Error message",
        )
        result_without_error = ModelToolExecutionResult(
            tool_name="test_tool",
            success=True,
            error=None,
        )

        assert result_with_error.error == "Error message"
        assert result_without_error.error is None

    def test_validate_assignment(self) -> None:
        """Test that field assignments are validated (validate_assignment=True)."""
        result = ModelToolExecutionResult(
            tool_name="test_tool",
            success=True,
            execution_time_ms=100,
        )

        # Valid assignment
        result.execution_time_ms = 200
        assert result.execution_time_ms == 200

        # Invalid assignment should raise ValidationError
        with pytest.raises(ValidationError):
            result.execution_time_ms = -50


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_tool_name(self) -> None:
        """Test with very long tool name."""
        long_name = "a" * 1000
        result = ModelToolExecutionResult(tool_name=long_name, success=True)
        assert result.tool_name == long_name
        assert len(result.tool_name) == 1000

    def test_very_long_error_message(self) -> None:
        """Test with very long error message."""
        long_error = "Error: " + ("x" * 10000)
        result = ModelToolExecutionResult(
            tool_name="test_tool",
            success=False,
            error=long_error,
        )
        assert len(result.error) > 10000

    def test_large_execution_time(self) -> None:
        """Test with large execution time (hours/days in milliseconds)."""
        one_day_ms = 24 * 60 * 60 * 1000
        result = ModelToolExecutionResult(
            tool_name="long_tool",
            success=True,
            execution_time_ms=one_day_ms,
        )
        assert result.execution_time_ms == one_day_ms

    def test_large_output_dictionary(self) -> None:
        """Test with large output dictionary."""
        large_output = {f"key_{i}": i for i in range(1000)}
        result = ModelToolExecutionResult(
            tool_name="large_tool",
            success=True,
            output=large_output,
        )
        assert len(result.output) == 1000
        assert result.output["key_999"] == 999

    def test_special_characters_in_strings(self) -> None:
        """Test with special characters in string fields."""
        result = ModelToolExecutionResult(
            tool_name="special!@#$%^&*()_+-={}[]|\\:;\"'<>?,./",
            success=False,
            error="Error with unicode: 你好世界 🚀 Ñoño",
        )
        assert "special!@#$%^&*()" in result.tool_name
        assert "你好世界" in result.error
        assert "🚀" in result.error

    def test_model_serialization(self) -> None:
        """Test that model can be serialized to dict."""
        result = ModelToolExecutionResult(
            tool_name="serialize_tool",
            success=True,
            output={"value": 42},
            execution_time_ms=1000,
        )

        serialized = result.model_dump()

        assert isinstance(serialized, dict)
        assert serialized["tool_name"] == "serialize_tool"
        assert serialized["success"] is True
        assert serialized["output"]["value"] == 42
        assert serialized["execution_time_ms"] == 1000

    def test_model_json_serialization(self) -> None:
        """Test that model can be serialized to JSON."""
        result = ModelToolExecutionResult(
            tool_name="json_tool",
            success=True,
            output={"status": "ok"},
        )

        json_str = result.model_dump_json()

        assert isinstance(json_str, str)
        assert "json_tool" in json_str
        assert "status" in json_str

    def test_model_deserialization(self) -> None:
        """Test that model can be deserialized from dict."""
        data = {
            "execution_id": "12345678-1234-5678-9abc-123456789abc",
            "tool_name": "deserialize_tool",
            "success": True,
            "output": {"result": "data"},
            "error": None,
            "execution_time_ms": 500,
            "status_code": 0,
        }

        result = ModelToolExecutionResult(**data)

        assert result.tool_name == "deserialize_tool"
        assert result.success is True
        assert result.output["result"] == "data"
        assert result.execution_time_ms == 500


class TestModelConfiguration:
    """Test Pydantic model configuration."""

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored (extra='ignore')."""
        # Pydantic with extra='ignore' allows unexpected fields without errors
        result = ModelToolExecutionResult(
            tool_name="test_tool",
            success=True,
            unexpected_field="should be ignored",
        )

        assert result.tool_name == "test_tool"
        assert not hasattr(result, "unexpected_field")

    def test_model_immutability_via_validation(self) -> None:
        """Test that field validation applies on assignment."""
        result = ModelToolExecutionResult(
            tool_name="test_tool",
            success=True,
            execution_time_ms=100,
        )

        # Should allow valid updates
        result.execution_time_ms = 200
        assert result.execution_time_ms == 200

        # Should reject invalid updates
        with pytest.raises(ValidationError):
            result.execution_time_ms = -100

    def test_model_copy(self) -> None:
        """Test that model can be copied with updates."""
        original = ModelToolExecutionResult(
            tool_name="original_tool",
            success=True,
            output={"value": 1},
            execution_time_ms=100,
        )

        # Create copy with updates
        copied = original.model_copy(
            update={"tool_name": "copied_tool", "execution_time_ms": 200},
        )

        assert copied.tool_name == "copied_tool"
        assert copied.execution_time_ms == 200
        assert copied.output == {"value": 1}
        assert original.tool_name == "original_tool"
        assert original.execution_time_ms == 100


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_cli_command_success_scenario(self) -> None:
        """Test typical CLI command success scenario."""
        result = ModelToolExecutionResult(
            tool_name="git_status",
            success=True,
            output={
                "branch": "main",
                "clean": True,
                "ahead": 0,
                "behind": 0,
            },
            execution_time_ms=150,
            status_code=0,
        )

        assert result.success is True
        assert result.tool_name == "git_status"
        assert result.output["branch"] == "main"
        assert result.status_code == 0

    def test_cli_command_failure_scenario(self) -> None:
        """Test typical CLI command failure scenario."""
        result = ModelToolExecutionResult(
            tool_name="git_push",
            success=False,
            error="fatal: unable to access remote repository",
            execution_time_ms=3000,
            status_code=128,
        )

        assert result.success is False
        assert result.tool_name == "git_push"
        assert "unable to access" in result.error
        assert result.status_code == 128

    def test_api_call_success_scenario(self) -> None:
        """Test typical API call success scenario."""
        result = ModelToolExecutionResult(
            tool_name="fetch_user_data",
            success=True,
            output={
                "user_id": 12345,
                "username": "testuser",
                "verified": True,
            },
            execution_time_ms=450,
            status_code=200,
        )

        assert result.success is True
        assert result.status_code == 200
        assert result.output["user_id"] == 12345

    def test_api_call_failure_scenario(self) -> None:
        """Test typical API call failure scenario."""
        result = ModelToolExecutionResult(
            tool_name="fetch_user_data",
            success=False,
            error="User not found",
            execution_time_ms=250,
            status_code=404,
        )

        assert result.success is False
        assert result.status_code == 404
        assert result.error == "User not found"

    def test_long_running_task_scenario(self) -> None:
        """Test long-running task scenario."""
        result = ModelToolExecutionResult(
            tool_name="batch_processor",
            success=True,
            output={
                "total_items": 10000,
                "processed": 10000,
                "failed": 0,
                "success_rate": 100.0,
            },
            execution_time_ms=300000,  # 5 minutes
            status_code=0,
        )

        assert result.success is True
        assert result.execution_time_ms == 300000
        assert result.output["processed"] == 10000

    def test_partial_failure_scenario(self) -> None:
        """Test partial failure scenario with diagnostic output."""
        result = ModelToolExecutionResult(
            tool_name="bulk_import",
            success=False,
            error="Import partially failed",
            output={
                "total": 100,
                "successful": 75,
                "failed": 25,
            },
            execution_time_ms=5000,
            status_code=1,
        )

        assert result.success is False
        assert result.output["successful"] == 75
        assert result.output["failed"] == 25
        assert result.status_code == 1
