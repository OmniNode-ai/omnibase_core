# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelToolExecution (OMN-1608).

Tests comprehensive tool execution model functionality including:
- Required field validation (tool_name, index, success)
- Optional field handling (error_type, error_message, file_path, timestamp, duration_ms)
- Field constraints (index >= 0, duration_ms >= 0.0)
- Computed directory property
- JSON-compatible tool_parameters with nested structures
- Frozen model immutability
- Extra field rejection

The model is frozen (immutable) and uses extra="forbid".
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.intelligence import ModelToolExecution

pytestmark = pytest.mark.unit


# ============================================================================
# Test: Required Fields
# ============================================================================


class TestModelToolExecutionRequiredFields:
    """Tests for required fields in ModelToolExecution."""

    def test_create_with_required_fields_only(self) -> None:
        """Test creating model with only required fields."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
        )

        assert execution.tool_name == "Read"
        assert execution.index == 0
        assert execution.success is True
        # Optional fields should have defaults
        assert execution.tool_parameters is None
        assert execution.error_type is None
        assert execution.error_message is None
        assert execution.file_path is None
        assert execution.timestamp is None
        assert execution.duration_ms is None

    def test_tool_name_is_required(self) -> None:
        """Test that tool_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecution(
                index=0,
                success=True,
            )  # type: ignore[call-arg]

        assert "tool_name" in str(exc_info.value)

    def test_index_is_required(self) -> None:
        """Test that index is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecution(
                tool_name="Read",
                success=True,
            )  # type: ignore[call-arg]

        assert "index" in str(exc_info.value)

    def test_success_is_required(self) -> None:
        """Test that success is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecution(
                tool_name="Read",
                index=0,
            )  # type: ignore[call-arg]

        assert "success" in str(exc_info.value)


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelToolExecutionFieldValidation:
    """Tests for field validation constraints."""

    def test_index_valid_at_zero(self) -> None:
        """Test index at minimum value (0)."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
        )
        assert execution.index == 0

    def test_index_valid_at_large_value(self) -> None:
        """Test index with large positive value."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=9999,
            success=True,
        )
        assert execution.index == 9999

    def test_index_invalid_below_zero(self) -> None:
        """Test index below minimum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecution(
                tool_name="Read",
                index=-1,
                success=True,
            )

        assert "index" in str(exc_info.value)

    def test_duration_ms_valid_at_zero(self) -> None:
        """Test duration_ms at minimum value (0.0)."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            duration_ms=0.0,
        )
        assert execution.duration_ms == 0.0

    def test_duration_ms_valid_at_positive_value(self) -> None:
        """Test duration_ms with positive value."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            duration_ms=150.5,
        )
        assert execution.duration_ms == 150.5

    def test_duration_ms_invalid_below_zero(self) -> None:
        """Test duration_ms below minimum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecution(
                tool_name="Read",
                index=0,
                success=True,
                duration_ms=-1.0,
            )

        assert "duration_ms" in str(exc_info.value)


# ============================================================================
# Test: Optional Fields
# ============================================================================


class TestModelToolExecutionOptionalFields:
    """Tests for optional field handling."""

    def test_create_with_all_fields(self) -> None:
        """Test creating model with all fields populated."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        execution = ModelToolExecution(
            tool_name="Write",
            index=5,
            success=False,
            tool_parameters={"file_path": "/tmp/test.py", "content": "print('hello')"},
            error_type="FileNotFoundError",
            error_message="No such file or directory: '/tmp/test.py'",
            file_path="/tmp/test.py",
            timestamp=timestamp,
            duration_ms=42.5,
        )

        assert execution.tool_name == "Write"
        assert execution.index == 5
        assert execution.success is False
        assert execution.tool_parameters == {
            "file_path": "/tmp/test.py",
            "content": "print('hello')",
        }
        assert execution.error_type == "FileNotFoundError"
        assert execution.error_message == "No such file or directory: '/tmp/test.py'"
        assert execution.file_path == "/tmp/test.py"
        assert execution.timestamp == timestamp
        assert execution.duration_ms == 42.5

    def test_success_true_execution(self) -> None:
        """Test successful execution without error fields."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/path/to/file.py",
            duration_ms=15.2,
        )

        assert execution.success is True
        assert execution.error_type is None
        assert execution.error_message is None

    def test_success_false_with_error_details(self) -> None:
        """Test failed execution with error details."""
        execution = ModelToolExecution(
            tool_name="Bash",
            index=3,
            success=False,
            error_type="TimeoutError",
            error_message="Command timed out after 30 seconds",
            duration_ms=30000.0,
        )

        assert execution.success is False
        assert execution.error_type == "TimeoutError"
        assert execution.error_message == "Command timed out after 30 seconds"


# ============================================================================
# Test: tool_parameters with JsonType
# ============================================================================


class TestModelToolExecutionToolParameters:
    """Tests for tool_parameters field with various JSON structures."""

    def test_tool_parameters_none(self) -> None:
        """Test tool_parameters as None."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            tool_parameters=None,
        )
        assert execution.tool_parameters is None

    def test_tool_parameters_primitive_string(self) -> None:
        """Test tool_parameters as string primitive."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            tool_parameters="simple_value",
        )
        assert execution.tool_parameters == "simple_value"

    def test_tool_parameters_primitive_int(self) -> None:
        """Test tool_parameters as integer primitive."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            tool_parameters=42,
        )
        assert execution.tool_parameters == 42

    def test_tool_parameters_primitive_bool(self) -> None:
        """Test tool_parameters as boolean primitive."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            tool_parameters=True,
        )
        assert execution.tool_parameters is True

    def test_tool_parameters_flat_dict(self) -> None:
        """Test tool_parameters as flat dictionary."""
        params = {"key": "value", "count": 10}
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            tool_parameters=params,
        )
        assert execution.tool_parameters == params

    def test_tool_parameters_nested_dict(self) -> None:
        """Test tool_parameters with nested dictionary structure."""
        params = {
            "config": {
                "timeout": 30,
                "retries": 3,
                "options": {"verbose": True, "dry_run": False},
            },
            "metadata": {"version": "1.0"},
        }
        execution = ModelToolExecution(
            tool_name="Bash",
            index=0,
            success=True,
            tool_parameters=params,
        )

        # Access nested structure with type narrowing
        assert isinstance(execution.tool_parameters, dict)
        config = execution.tool_parameters["config"]
        assert isinstance(config, dict)
        assert config["timeout"] == 30
        options = config["options"]
        assert isinstance(options, dict)
        assert options["verbose"] is True

    def test_tool_parameters_list(self) -> None:
        """Test tool_parameters as list."""
        params = ["arg1", "arg2", "arg3"]
        execution = ModelToolExecution(
            tool_name="Bash",
            index=0,
            success=True,
            tool_parameters=params,
        )
        assert execution.tool_parameters == params

    def test_tool_parameters_mixed_list(self) -> None:
        """Test tool_parameters as list with mixed types."""
        params = ["string", 42, True, None, {"nested": "dict"}]
        execution = ModelToolExecution(
            tool_name="Bash",
            index=0,
            success=True,
            tool_parameters=params,
        )
        assert execution.tool_parameters == params

    def test_tool_parameters_complex_structure(self) -> None:
        """Test tool_parameters with complex nested structure."""
        params = {
            "command": "git commit",
            "args": ["-m", "fix: something"],
            "env": {"PATH": "/usr/bin", "HOME": "/home/user"},
            "metadata": None,
            "nested": {
                "level1": {
                    "level2": [1, 2, {"level3": "deep"}],
                },
            },
        }
        execution = ModelToolExecution(
            tool_name="Bash",
            index=0,
            success=True,
            tool_parameters=params,
        )
        assert execution.tool_parameters == params


# ============================================================================
# Test: directory Property
# ============================================================================


class TestModelToolExecutionDirectoryProperty:
    """Tests for computed directory property."""

    def test_directory_none_when_file_path_none(self) -> None:
        """Test directory returns None when file_path is None."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path=None,
        )
        assert execution.directory is None

    def test_directory_from_absolute_path(self) -> None:
        """Test directory extracts parent from absolute path."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/home/user/project/src/main.py",
        )
        assert execution.directory == "/home/user/project/src"

    def test_directory_from_relative_path(self) -> None:
        """Test directory extracts parent from relative path."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="src/main.py",
        )
        assert execution.directory == "src"

    def test_directory_from_file_in_root(self) -> None:
        """Test directory for file in root directory."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/file.txt",
        )
        assert execution.directory == "/"

    def test_directory_from_simple_filename(self) -> None:
        """Test directory for simple filename without path."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="file.txt",
        )
        assert execution.directory == "."

    def test_directory_from_nested_path(self) -> None:
        """Test directory from deeply nested path."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/a/b/c/d/e/file.py",
        )
        assert execution.directory == "/a/b/c/d/e"


# ============================================================================
# Test: Frozen Immutability
# ============================================================================


class TestModelToolExecutionFrozenImmutability:
    """Tests for frozen model immutability."""

    def test_frozen_immutability_tool_name(self) -> None:
        """Test that tool_name cannot be modified."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
        )

        with pytest.raises(ValidationError):
            execution.tool_name = "Write"

    def test_frozen_immutability_index(self) -> None:
        """Test that index cannot be modified."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
        )

        with pytest.raises(ValidationError):
            execution.index = 5

    def test_frozen_immutability_success(self) -> None:
        """Test that success cannot be modified."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
        )

        with pytest.raises(ValidationError):
            execution.success = False

    def test_frozen_immutability_file_path(self) -> None:
        """Test that file_path cannot be modified."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/original/path.py",
        )

        with pytest.raises(ValidationError):
            execution.file_path = "/new/path.py"

    def test_frozen_immutability_tool_parameters(self) -> None:
        """Test that tool_parameters cannot be reassigned."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            tool_parameters={"key": "value"},
        )

        with pytest.raises(ValidationError):
            execution.tool_parameters = {"new": "data"}


# ============================================================================
# Test: Extra Fields Forbidden
# ============================================================================


class TestModelToolExecutionExtraFieldsForbidden:
    """Tests for extra field rejection."""

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecution(
                tool_name="Read",
                index=0,
                success=True,
                unknown_field="bad",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)

    def test_multiple_extra_fields_forbidden(self) -> None:
        """Test that multiple extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecution(
                tool_name="Read",
                index=0,
                success=True,
                extra1="bad",  # type: ignore[call-arg]
                extra2=123,  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value)
        assert "extra1" in error_str or "extra2" in error_str


# ============================================================================
# Test: Serialization Round-Trip
# ============================================================================


class TestModelToolExecutionSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump_round_trip(self) -> None:
        """Test model_dump and model_validate round-trip."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        original = ModelToolExecution(
            tool_name="Write",
            index=3,
            success=False,
            tool_parameters={"content": "test"},
            error_type="PermissionError",
            error_message="Access denied",
            file_path="/protected/file.txt",
            timestamp=timestamp,
            duration_ms=25.5,
        )

        data = original.model_dump()
        restored = ModelToolExecution.model_validate(data)

        assert original.tool_name == restored.tool_name
        assert original.index == restored.index
        assert original.success == restored.success
        assert original.tool_parameters == restored.tool_parameters
        assert original.error_type == restored.error_type
        assert original.error_message == restored.error_message
        assert original.file_path == restored.file_path
        assert original.timestamp == restored.timestamp
        assert original.duration_ms == restored.duration_ms

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelToolExecution(
            tool_name="Bash",
            index=0,
            success=True,
            tool_parameters={"command": "ls -la"},
            duration_ms=100.0,
        )

        json_str = original.model_dump_json()
        restored = ModelToolExecution.model_validate_json(json_str)

        assert original.tool_name == restored.tool_name
        assert original.index == restored.index
        assert original.success == restored.success
        assert original.tool_parameters == restored.tool_parameters
        assert original.duration_ms == restored.duration_ms

    def test_directory_not_in_serialization(self) -> None:
        """Test that directory property is not included in serialization."""
        execution = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/path/to/file.py",
        )

        data = execution.model_dump()

        # directory is a computed property, not a stored field
        assert "directory" not in data
        # But can still access it
        assert execution.directory == "/path/to"


# ============================================================================
# Test: Model Equality
# ============================================================================


class TestModelToolExecutionEquality:
    """Tests for model equality comparisons."""

    def test_equality_same_values(self) -> None:
        """Test equality for models with same values."""
        e1 = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/path/file.py",
        )
        e2 = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
            file_path="/path/file.py",
        )

        assert e1 == e2

    def test_inequality_different_values(self) -> None:
        """Test inequality for models with different values."""
        e1 = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
        )
        e2 = ModelToolExecution(
            tool_name="Write",
            index=0,
            success=True,
        )

        assert e1 != e2

    def test_inequality_different_index(self) -> None:
        """Test inequality for models with different index."""
        e1 = ModelToolExecution(
            tool_name="Read",
            index=0,
            success=True,
        )
        e2 = ModelToolExecution(
            tool_name="Read",
            index=1,
            success=True,
        )

        assert e1 != e2


# ============================================================================
# Test: Import from Package
# ============================================================================


class TestModelToolExecutionImport:
    """Tests for model import from intelligence package."""

    def test_import_from_intelligence_module(self) -> None:
        """Test that ModelToolExecution can be imported from intelligence module."""
        from omnibase_core.models.intelligence import ModelToolExecution as Imported

        assert Imported is ModelToolExecution

    def test_model_in_all(self) -> None:
        """Test that ModelToolExecution is in __all__."""
        from omnibase_core.models import intelligence

        assert "ModelToolExecution" in intelligence.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
