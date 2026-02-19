# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelErrorContext."""

import pytest

from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


@pytest.mark.unit
class TestModelErrorContextInstantiation:
    """Tests for ModelErrorContext instantiation."""

    def test_create_empty(self):
        """Test creating empty error context."""
        context = ModelErrorContext()
        assert context.file_path is None
        assert context.line_number is None
        assert context.column_number is None
        assert context.function_name is None
        assert context.module_name is None
        assert context.stack_trace is None
        assert context.additional_context == {}

    def test_create_with_file_info(self):
        """Test creating context with file information."""
        context = ModelErrorContext(
            file_path="/path/to/file.py", line_number=42, column_number=10
        )
        assert context.file_path == "/path/to/file.py"
        assert context.line_number == 42
        assert context.column_number == 10

    def test_create_with_function_info(self):
        """Test creating context with function information."""
        context = ModelErrorContext(
            function_name="test_function", module_name="test_module"
        )
        assert context.function_name == "test_function"
        assert context.module_name == "test_module"

    def test_create_with_stack_trace(self):
        """Test creating context with stack trace."""
        stack = "Traceback (most recent call last):\n  File..."
        context = ModelErrorContext(stack_trace=stack)
        assert context.stack_trace == stack

    def test_create_with_additional_context(self):
        """Test creating context with additional context."""
        additional = {
            "error_type": ModelSchemaValue.from_value("validation"),
            "severity": ModelSchemaValue.from_value("high"),
        }
        context = ModelErrorContext(additional_context=additional)
        assert len(context.additional_context) == 2
        assert "error_type" in context.additional_context
        assert "severity" in context.additional_context


@pytest.mark.unit
class TestModelErrorContextFactoryMethods:
    """Tests for ModelErrorContext factory methods."""

    def test_with_context_empty(self):
        """Test with_context factory with empty dict."""
        context = ModelErrorContext.with_context({})
        assert context.file_path is None
        assert context.line_number is None
        assert context.additional_context == {}

    def test_with_context_single_value(self):
        """Test with_context factory with single value."""
        additional = {"error_type": ModelSchemaValue.from_value("typeerror")}
        context = ModelErrorContext.with_context(additional)
        assert len(context.additional_context) == 1
        assert "error_type" in context.additional_context
        assert context.additional_context["error_type"].to_value() == "typeerror"

    def test_with_context_multiple_values(self):
        """Test with_context factory with multiple values."""
        additional = {
            "error_type": ModelSchemaValue.from_value("validation"),
            "field_name": ModelSchemaValue.from_value("email"),
            "expected_type": ModelSchemaValue.from_value("string"),
        }
        context = ModelErrorContext.with_context(additional)
        assert len(context.additional_context) == 3
        assert all(k in context.additional_context for k in additional)


@pytest.mark.unit
class TestModelErrorContextSerialization:
    """Tests for ModelErrorContext serialization."""

    def test_serialize_empty(self):
        """Test serializing empty context."""
        context = ModelErrorContext()
        data = context.serialize()
        assert isinstance(data, dict)
        assert "file_path" in data
        assert "additional_context" in data

    def test_serialize_with_data(self):
        """Test serializing context with data."""
        context = ModelErrorContext(
            file_path="/test/file.py", line_number=10, function_name="test_func"
        )
        data = context.serialize()
        assert data["file_path"] == "/test/file.py"
        assert data["line_number"] == 10
        assert data["function_name"] == "test_func"

    def test_model_dump(self):
        """Test model_dump method."""
        context = ModelErrorContext(module_name="test_module")
        data = context.model_dump()
        assert isinstance(data, dict)
        assert "module_name" in data


@pytest.mark.unit
class TestModelErrorContextProtocols:
    """Tests for ModelErrorContext protocol implementations."""

    def test_validate_instance(self):
        """Test validate_instance method."""
        context = ModelErrorContext()
        assert context.validate_instance() is True

    def test_validate_instance_with_data(self):
        """Test validate_instance with populated context."""
        context = ModelErrorContext(
            file_path="/test/file.py",
            line_number=42,
            additional_context={
                "error_type": ModelSchemaValue.from_value("validation")
            },
        )
        assert context.validate_instance() is True


@pytest.mark.unit
class TestModelErrorContextEdgeCases:
    """Tests for ModelErrorContext edge cases."""

    def test_all_fields_populated(self):
        """Test context with all fields populated."""
        additional = {
            "key1": ModelSchemaValue.from_value("value1"),
            "key2": ModelSchemaValue.from_value(42),
        }
        context = ModelErrorContext(
            file_path="/path/to/file.py",
            line_number=100,
            column_number=20,
            function_name="my_function",
            module_name="my_module",
            stack_trace="Full stack trace here",
            additional_context=additional,
        )
        assert context.file_path == "/path/to/file.py"
        assert context.line_number == 100
        assert context.column_number == 20
        assert context.function_name == "my_function"
        assert context.module_name == "my_module"
        assert context.stack_trace == "Full stack trace here"
        assert len(context.additional_context) == 2

    def test_zero_line_number(self):
        """Test context with zero line number."""
        context = ModelErrorContext(line_number=0)
        assert context.line_number == 0

    def test_negative_line_number(self):
        """Test context with negative line number."""
        context = ModelErrorContext(line_number=-1)
        assert context.line_number == -1

    def test_empty_string_fields(self):
        """Test context with empty string fields."""
        context = ModelErrorContext(
            file_path="", function_name="", module_name="", stack_trace=""
        )
        assert context.file_path == ""
        assert context.function_name == ""
        assert context.module_name == ""
        assert context.stack_trace == ""

    def test_additional_context_with_various_types(self):
        """Test additional context with various ModelSchemaValue types."""
        additional = {
            "string_val": ModelSchemaValue.from_value("test"),
            "int_val": ModelSchemaValue.from_value(42),
            "float_val": ModelSchemaValue.from_value(3.14),
            "bool_val": ModelSchemaValue.from_value(True),
        }
        context = ModelErrorContext.with_context(additional)
        assert len(context.additional_context) == 4
        assert context.additional_context["string_val"].to_value() == "test"
        assert context.additional_context["int_val"].to_value() == 42
        assert context.additional_context["float_val"].to_value() == 3.14
        assert context.additional_context["bool_val"].to_value() is True

    def test_large_stack_trace(self):
        """Test context with large stack trace."""
        large_trace = "Line\n" * 1000
        context = ModelErrorContext(stack_trace=large_trace)
        # Stack trace may be truncated to 5000 characters
        assert len(context.stack_trace) >= 5000

    def test_special_characters_in_fields(self):
        """Test context with special characters."""
        context = ModelErrorContext(
            file_path="/path/with spaces/file.py",
            function_name="test_function_with_underscores",
            module_name="module.submodule.name",
        )
        assert context.file_path == "/path/with spaces/file.py"
        assert context.function_name == "test_function_with_underscores"
        assert context.module_name == "module.submodule.name"
