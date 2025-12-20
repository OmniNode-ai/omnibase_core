"""
Comprehensive tests for ModelOnexMessage.

Tests cover:
- Basic instantiation with required fields
- Optional field handling
- EnumLogLevel integration
- File location fields (file, line, column)
- Context field with ModelOnexMessageContext
- Timestamp handling
- Field validation and type safety
- Localization support
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.results.model_onex_message import ModelOnexMessage
from omnibase_core.models.results.model_onex_message_context import (
    ModelOnexMessageContext,
)


@pytest.mark.unit
class TestModelOnexMessageBasicInstantiation:
    """Test basic instantiation with required fields."""

    def test_minimal_instantiation_with_summary_only(self):
        """Test creating message with only required summary field."""
        message = ModelOnexMessage(summary="Test message")

        assert message.summary == "Test message"
        assert message.level == EnumLogLevel.INFO  # Default level
        assert message.suggestions is None
        assert message.remediation is None

    def test_instantiation_with_summary_and_level(self):
        """Test creating message with summary and level."""
        message = ModelOnexMessage(summary="Error occurred", level=EnumLogLevel.ERROR)

        assert message.summary == "Error occurred"
        assert message.level == EnumLogLevel.ERROR


@pytest.mark.unit
class TestModelOnexMessageLevelField:
    """Test level field with EnumLogLevel."""

    def test_all_log_levels(self):
        """Test instantiation with all EnumLogLevel values."""
        levels = [
            EnumLogLevel.DEBUG,
            EnumLogLevel.INFO,
            EnumLogLevel.WARNING,
            EnumLogLevel.ERROR,
            EnumLogLevel.CRITICAL,
        ]

        for level in levels:
            message = ModelOnexMessage(summary="Test", level=level)
            assert message.level == level

    def test_level_defaults_to_info(self):
        """Test that level defaults to INFO."""
        message = ModelOnexMessage(summary="Test")
        assert message.level == EnumLogLevel.INFO

    def test_level_must_be_valid_enum(self):
        """Test that level must be valid EnumLogLevel value."""
        with pytest.raises(ValidationError):
            ModelOnexMessage(summary="Test", level="invalid_level")


@pytest.mark.unit
class TestModelOnexMessageFieldValidation:
    """Test field validation and type safety."""

    def test_summary_field_required(self):
        """Test that summary field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexMessage()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("summary",) for error in errors)

    def test_summary_must_be_string(self):
        """Test that summary must be a string."""
        message = ModelOnexMessage(summary="Valid string")
        assert isinstance(message.summary, str)

        with pytest.raises(ValidationError):
            ModelOnexMessage(summary=123)  # Not a string


@pytest.mark.unit
class TestModelOnexMessageFileLocationFields:
    """Test file location fields (file, line, column)."""

    def test_file_field(self):
        """Test file field with file path."""
        message = ModelOnexMessage(summary="Error in file", file="src/main.py")

        assert message.file == "src/main.py"

    def test_line_field(self):
        """Test line field with line number."""
        message = ModelOnexMessage(summary="Error on line", file="src/main.py", line=42)

        assert message.file == "src/main.py"
        assert message.line == 42

    def test_column_field(self):
        """Test column field with column number."""
        message = ModelOnexMessage(
            summary="Error at position",
            file="src/main.py",
            line=42,
            column=15,
        )

        assert message.file == "src/main.py"
        assert message.line == 42
        assert message.column == 15

    def test_line_must_be_integer(self):
        """Test that line field must be integer."""
        message = ModelOnexMessage(summary="Test", line=10)
        assert isinstance(message.line, int)

        with pytest.raises(ValidationError):
            ModelOnexMessage(summary="Test", line="not an integer")


@pytest.mark.unit
class TestModelOnexMessageDetailFields:
    """Test detail and suggestion fields."""

    def test_details_field(self):
        """Test details field with extended information."""
        message = ModelOnexMessage(
            summary="Short summary",
            details="This is a much longer detailed explanation of the issue.",
        )

        assert message.summary == "Short summary"
        assert "longer detailed explanation" in message.details

    def test_suggestions_field(self):
        """Test suggestions list field."""
        suggestions = ["Fix line 10", "Update documentation", "Add error handling"]
        message = ModelOnexMessage(summary="Warning", suggestions=suggestions)

        assert len(message.suggestions) == 3
        assert "Fix line 10" in message.suggestions

    def test_remediation_field(self):
        """Test remediation field with fix instructions."""
        message = ModelOnexMessage(
            summary="Error found",
            remediation="To fix this error, update the configuration file.",
        )

        assert "update the configuration file" in message.remediation


@pytest.mark.unit
class TestModelOnexMessageCodeField:
    """Test code field for error/warning codes."""

    def test_code_field(self):
        """Test code field with error code."""
        message = ModelOnexMessage(summary="Validation error", code="E001")

        assert message.code == "E001"

    def test_code_field_with_standard_codes(self):
        """Test code field with standard error code formats."""
        codes = ["E001", "W123", "ERR-404", "WARN-100"]

        for code in codes:
            message = ModelOnexMessage(summary="Test", code=code)
            assert message.code == code


@pytest.mark.unit
class TestModelOnexMessageContextField:
    """Test context field with ModelOnexMessageContext."""

    def test_context_field_with_message_context(self):
        """Test context field with ModelOnexMessageContext instance."""
        context = ModelOnexMessageContext(
            key="variable_name", value=ModelSchemaValue.from_value("test_value")
        )
        message = ModelOnexMessage(summary="Context message", context=context)

        assert message.context.key == "variable_name"
        assert message.context.value.string_value == "test_value"

    def test_context_field_optional(self):
        """Test that context field is optional."""
        message = ModelOnexMessage(summary="No context")
        assert message.context is None


@pytest.mark.unit
class TestModelOnexMessageTimestampField:
    """Test timestamp field handling."""

    def test_timestamp_field(self):
        """Test timestamp field with datetime."""
        now = datetime(2025, 1, 1, 12, 0, 0)
        message = ModelOnexMessage(summary="Timestamped message", timestamp=now)

        assert message.timestamp == now
        assert isinstance(message.timestamp, datetime)

    def test_timestamp_field_optional(self):
        """Test that timestamp field is optional."""
        message = ModelOnexMessage(summary="No timestamp")
        assert message.timestamp is None


@pytest.mark.unit
class TestModelOnexMessageFixableField:
    """Test fixable boolean field."""

    def test_fixable_field_true(self):
        """Test fixable field when issue can be auto-fixed."""
        message = ModelOnexMessage(
            summary="Formatting issue",
            fixable=True,
            remediation="Run formatter",
        )

        assert message.fixable is True
        assert message.remediation is not None

    def test_fixable_field_false(self):
        """Test fixable field when issue cannot be auto-fixed."""
        message = ModelOnexMessage(summary="Logic error", fixable=False)

        assert message.fixable is False

    def test_fixable_field_optional(self):
        """Test that fixable field is optional."""
        message = ModelOnexMessage(summary="Unknown fixability")
        assert message.fixable is None


@pytest.mark.unit
class TestModelOnexMessageOriginField:
    """Test origin field for message source."""

    def test_origin_field(self):
        """Test origin field identifying message source."""
        message = ModelOnexMessage(summary="Lint error", origin="pylint")

        assert message.origin == "pylint"

    def test_origin_field_with_various_tools(self):
        """Test origin field with different tool names."""
        tools = ["pylint", "mypy", "black", "pytest", "custom_validator"]

        for tool in tools:
            message = ModelOnexMessage(summary="Message from tool", origin=tool)
            assert message.origin == tool


@pytest.mark.unit
class TestModelOnexMessageRenderingFields:
    """Test rendering and documentation fields."""

    def test_rendered_markdown_field(self):
        """Test rendered_markdown field for rich content."""
        markdown = "## Error Details\n\n- Point 1\n- Point 2"
        message = ModelOnexMessage(summary="Rich message", rendered_markdown=markdown)

        assert message.rendered_markdown == markdown
        assert "## Error Details" in message.rendered_markdown

    def test_doc_link_field(self):
        """Test doc_link field with documentation URL."""
        doc_url = "https://docs.example.com/errors/E001"
        message = ModelOnexMessage(summary="See docs", doc_link=doc_url)

        assert message.doc_link == doc_url

    def test_example_field(self):
        """Test example field with code example."""
        example = "def foo():\n    pass"
        message = ModelOnexMessage(summary="Example code", example=example)

        assert message.example == example


@pytest.mark.unit
class TestModelOnexMessageLocalizationField:
    """Test localization support via localized_text field."""

    def test_localized_text_field(self):
        """Test localized_text field with multiple languages."""
        localized = {
            "en": "Error occurred",
            "es": "Ocurrió un error",
            "fr": "Une erreur s'est produite",
        }
        message = ModelOnexMessage(summary="Error", localized_text=localized)

        assert len(message.localized_text) == 3
        assert message.localized_text["en"] == "Error occurred"
        assert message.localized_text["es"] == "Ocurrió un error"

    def test_localized_text_field_optional(self):
        """Test that localized_text field is optional."""
        message = ModelOnexMessage(summary="English only")
        assert message.localized_text is None


@pytest.mark.unit
class TestModelOnexMessageSeverityField:
    """Test severity field (in addition to level)."""

    def test_severity_field_with_log_level(self):
        """Test severity field using EnumLogLevel."""
        message = ModelOnexMessage(
            summary="Critical issue",
            level=EnumLogLevel.ERROR,
            severity=EnumLogLevel.CRITICAL,
        )

        assert message.level == EnumLogLevel.ERROR
        assert message.severity == EnumLogLevel.CRITICAL

    def test_severity_field_optional(self):
        """Test that severity field is optional."""
        message = ModelOnexMessage(summary="Info message", level=EnumLogLevel.INFO)
        assert message.severity is None


@pytest.mark.unit
class TestModelOnexMessageTypeField:
    """Test type field for message categorization."""

    def test_type_field(self):
        """Test type field with message type."""
        message = ModelOnexMessage(summary="Type example", type="error")

        assert message.type == "error"

    def test_type_field_with_various_types(self):
        """Test type field with different message types."""
        types = ["error", "warning", "note", "hint", "suggestion"]

        for msg_type in types:
            message = ModelOnexMessage(summary="Typed message", type=msg_type)
            assert message.type == msg_type


@pytest.mark.unit
class TestModelOnexMessageOptionalFields:
    """Test that all optional fields can be None."""

    def test_all_optional_fields_can_be_none(self):
        """Test that all optional fields default to None."""
        message = ModelOnexMessage(summary="Minimal message")

        assert message.suggestions is None
        assert message.remediation is None
        assert message.rendered_markdown is None
        assert message.doc_link is None
        assert message.file is None
        assert message.line is None
        assert message.column is None
        assert message.details is None
        assert message.severity is None
        assert message.code is None
        assert message.context is None
        assert message.timestamp is None
        assert message.fixable is None
        assert message.origin is None
        assert message.example is None
        assert message.localized_text is None
        assert message.type is None


@pytest.mark.unit
class TestModelOnexMessageSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary."""
        message = ModelOnexMessage(
            summary="Test message",
            level=EnumLogLevel.WARNING,
            file="test.py",
            line=10,
        )

        dumped = message.model_dump()

        assert dumped["summary"] == "Test message"
        assert dumped["level"] == EnumLogLevel.WARNING
        assert dumped["file"] == "test.py"
        assert dumped["line"] == 10

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        message = ModelOnexMessage(summary="Test", level=EnumLogLevel.INFO)

        dumped = message.model_dump(exclude_none=True)

        assert "summary" in dumped
        assert "level" in dumped
        assert "file" not in dumped
        assert "line" not in dumped

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ModelOnexMessage(
            summary="Test message",
            level=EnumLogLevel.ERROR,
            file="src/main.py",
            line=42,
            code="E001",
        )

        json_str = original.model_dump_json()
        restored = ModelOnexMessage.model_validate_json(json_str)

        assert restored.summary == original.summary
        assert restored.level == original.level
        assert restored.file == original.file
        assert restored.line == original.line
        assert restored.code == original.code


@pytest.mark.unit
class TestModelOnexMessageComplexScenarios:
    """Test complex usage scenarios."""

    def test_full_error_message(self):
        """Test fully populated error message."""
        context = ModelOnexMessageContext(
            key="line_content", value=ModelSchemaValue.from_value("def foo():")
        )
        message = ModelOnexMessage(
            summary="Syntax error detected",
            level=EnumLogLevel.ERROR,
            severity=EnumLogLevel.CRITICAL,
            file="src/main.py",
            line=42,
            column=15,
            details="Missing colon at end of function definition",
            code="E999",
            suggestions=["Add colon", "Check syntax"],
            remediation="Add ':' at the end of the line",
            fixable=True,
            origin="pylint",
            context=context,
            timestamp=datetime.now(),
            type="error",
        )

        assert message.summary == "Syntax error detected"
        assert message.level == EnumLogLevel.ERROR
        assert message.file == "src/main.py"
        assert message.line == 42
        assert message.fixable is True
        assert len(message.suggestions) == 2

    def test_warning_message_with_doc_link(self):
        """Test warning message with documentation."""
        message = ModelOnexMessage(
            summary="Deprecated API usage",
            level=EnumLogLevel.WARNING,
            file="src/api.py",
            line=100,
            details="This API will be removed in version 2.0",
            doc_link="https://docs.example.com/deprecation/api-v1",
            suggestions=["Use new API v2"],
        )

        assert message.level == EnumLogLevel.WARNING
        assert message.doc_link is not None
        assert "docs.example.com" in message.doc_link


@pytest.mark.unit
class TestModelOnexMessageTypeSafety:
    """Test type safety - comprehensive testing required."""

    def test_no_any_types_in_annotations(self):
        """Test that model fields don't use Any type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOnexMessage)

        # Check that no field uses Any type directly (except in unions with None)
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert "typing.Any" not in type_str or "None" in type_str, (
                f"Field {field_name} uses Any type: {type_str}"
            )
