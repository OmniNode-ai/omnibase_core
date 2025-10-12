"""
Test suite for validation message models.

This test suite covers ModelValidateMessage, ModelValidateMessageContext, and ModelValidateResult
to maximize coverage of the validation error handling system.
"""

from __future__ import annotations

import datetime
import json
import re
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumLogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus

# Import from actual implementation files for proper coverage tracking
from omnibase_core.models.validation.model_validate_message import ModelValidateMessage
from omnibase_core.models.validation.model_validate_message_context import ModelValidateMessageContext
from omnibase_core.models.validation.model_validate_result import ModelValidateResult

# Compatibility aliases for backward compatibility
ValidateMessageModel = ModelValidateMessage
ValidateMessageModelContext = ModelValidateMessageContext
ValidateResultModel = ModelValidateResult


class TestModelValidateMessageContextInstantiation:
    """Test ModelValidateMessageContext instantiation."""

    def test_default_initialization(self):
        """Test ModelValidateMessageContext initializes with all None values."""
        context = ModelValidateMessageContext()
        assert context.field is None
        assert context.value is None
        assert context.expected is None
        assert context.actual is None
        assert context.reason is None

    def test_full_initialization(self):
        """Test ModelValidateMessageContext with all fields."""
        context = ModelValidateMessageContext(
            field="username",
            value="test_user",
            expected="string with 3-20 characters",
            actual="test_user",
            reason="Valid username",
        )
        assert context.field == "username"
        assert context.value == "test_user"
        assert context.expected == "string with 3-20 characters"
        assert context.actual == "test_user"
        assert context.reason == "Valid username"

    def test_partial_initialization(self):
        """Test ModelValidateMessageContext with partial fields."""
        context = ModelValidateMessageContext(
            field="age",
            expected="integer >= 0",
            actual=-5,
        )
        assert context.field == "age"
        assert context.expected == "integer >= 0"
        assert context.actual == -5
        assert context.value is None
        assert context.reason is None

    def test_with_various_value_types(self):
        """Test context with various value types."""
        # String
        ctx1 = ModelValidateMessageContext(value="string")
        assert isinstance(ctx1.value, str)

        # Integer
        ctx2 = ModelValidateMessageContext(value=42)
        assert isinstance(ctx2.value, int)

        # List
        ctx3 = ModelValidateMessageContext(value=[1, 2, 3])
        assert isinstance(ctx3.value, list)

        # Dict
        ctx4 = ModelValidateMessageContext(value={"key": "value"})
        assert isinstance(ctx4.value, dict)

        # None
        ctx5 = ModelValidateMessageContext(value=None)
        assert ctx5.value is None


class TestModelValidateMessageContextSerialization:
    """Test ModelValidateMessageContext serialization."""

    def test_model_dump(self):
        """Test model_dump returns dict."""
        context = ModelValidateMessageContext(
            field="email",
            expected="valid email format",
            actual="invalid@",
        )
        dumped = context.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["field"] == "email"
        assert dumped["expected"] == "valid email format"

    def test_model_dump_json(self):
        """Test model_dump_json returns JSON string."""
        context = ModelValidateMessageContext(field="test", reason="Test reason")
        json_str = context.model_dump_json()

        assert isinstance(json_str, str)
        assert "test" in json_str

    def test_round_trip_serialization(self):
        """Test serialization and deserialization."""
        original = ModelValidateMessageContext(
            field="status",
            expected="active",
            actual="inactive",
            reason="Status mismatch",
        )

        dumped = original.model_dump()
        restored = ModelValidateMessageContext(**dumped)

        assert restored.field == original.field
        assert restored.expected == original.expected
        assert restored.actual == original.actual
        assert restored.reason == original.reason


class TestModelValidateMessageInstantiation:
    """Test ModelValidateMessage instantiation."""

    def test_minimal_initialization(self):
        """Test ModelValidateMessage with only required message field."""
        msg = ModelValidateMessage(message="Test error")
        assert msg.message == "Test error"
        assert msg.severity == EnumLogLevel.ERROR
        assert msg.code == "unknown"
        assert msg.file is None
        assert msg.line is None
        assert msg.context is None
        assert msg.uid is not None
        assert msg.timestamp is not None

    def test_full_initialization(self):
        """Test ModelValidateMessage with all fields."""
        context = ModelValidateMessageContext(
            field="username",
            expected="valid string",
            actual="",
        )

        msg = ModelValidateMessage(
            message="Username is required",
            file="/path/to/file.py",
            line=42,
            severity=EnumLogLevel.CRITICAL,
            code="ERR_001",
            context=context,
        )

        assert msg.message == "Username is required"
        assert msg.file == "/path/to/file.py"
        assert msg.line == 42
        assert msg.severity == EnumLogLevel.CRITICAL
        assert msg.code == "ERR_001"
        assert msg.context is not None
        assert msg.context.field == "username"

    def test_default_severity(self):
        """Test default severity is ERROR."""
        msg = ModelValidateMessage(message="Test")
        assert msg.severity == EnumLogLevel.ERROR

    def test_default_code(self):
        """Test default code is 'unknown'."""
        msg = ModelValidateMessage(message="Test")
        assert msg.code == "unknown"

    def test_uid_is_unique(self):
        """Test each message gets a unique UID."""
        msg1 = ModelValidateMessage(message="Test 1")
        msg2 = ModelValidateMessage(message="Test 2")

        assert msg1.uid != msg2.uid

    def test_timestamp_format(self):
        """Test timestamp is in ISO format."""
        msg = ModelValidateMessage(message="Test")
        # Should be a valid ISO 8601 timestamp
        datetime.datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00"))

    def test_various_severity_levels(self):
        """Test message with various severity levels."""
        for level in [
            EnumLogLevel.DEBUG,
            EnumLogLevel.INFO,
            EnumLogLevel.WARNING,
            EnumLogLevel.ERROR,
            EnumLogLevel.CRITICAL,
        ]:
            msg = ModelValidateMessage(message="Test", severity=level)
            assert msg.severity == level


class TestModelValidateMessageComputeHash:
    """Test ModelValidateMessage compute_hash method."""

    def test_compute_hash_returns_string(self):
        """Test compute_hash returns a hex string."""
        msg = ModelValidateMessage(message="Test")
        hash_value = msg.compute_hash()

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 produces 64 hex characters
        # Verify it's a valid hex string
        int(hash_value, 16)

    def test_compute_hash_includes_message(self):
        """Test hash changes with different messages."""
        msg1 = ModelValidateMessage(message="Test 1")
        msg2 = ModelValidateMessage(message="Test 2")

        hash1 = msg1.compute_hash()
        hash2 = msg2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_includes_file(self):
        """Test hash includes file information."""
        msg1 = ModelValidateMessage(message="Test", file="file1.py")
        msg2 = ModelValidateMessage(message="Test", file="file2.py")

        hash1 = msg1.compute_hash()
        hash2 = msg2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_includes_code(self):
        """Test hash includes error code."""
        msg1 = ModelValidateMessage(message="Test", code="ERR_001")
        msg2 = ModelValidateMessage(message="Test", code="ERR_002")

        hash1 = msg1.compute_hash()
        hash2 = msg2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_includes_severity(self):
        """Test hash includes severity."""
        msg1 = ModelValidateMessage(message="Test", severity=EnumLogLevel.ERROR)
        msg2 = ModelValidateMessage(message="Test", severity=EnumLogLevel.WARNING)

        hash1 = msg1.compute_hash()
        hash2 = msg2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_includes_context(self):
        """Test hash includes context information."""
        ctx1 = ModelValidateMessageContext(field="field1")
        ctx2 = ModelValidateMessageContext(field="field2")

        msg1 = ModelValidateMessage(message="Test", context=ctx1)
        msg2 = ModelValidateMessage(message="Test", context=ctx2)

        hash1 = msg1.compute_hash()
        hash2 = msg2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_without_optional_fields(self):
        """Test hash computation with minimal fields."""
        msg = ModelValidateMessage(message="Test")
        hash_value = msg.compute_hash()

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64


class TestModelValidateMessageWithHash:
    """Test ModelValidateMessage with_hash method."""

    def test_with_hash_sets_hash_field(self):
        """Test with_hash sets the hash field."""
        msg = ModelValidateMessage(message="Test")
        assert msg.hash is None

        msg.with_hash()
        assert msg.hash is not None
        assert len(msg.hash) == 64

    def test_with_hash_returns_self(self):
        """Test with_hash returns self for chaining."""
        msg = ModelValidateMessage(message="Test")
        result = msg.with_hash()

        assert result is msg

    def test_with_hash_chaining(self):
        """Test with_hash can be chained during initialization."""
        msg = ModelValidateMessage(message="Test").with_hash()

        assert msg.hash is not None
        assert msg.message == "Test"


class TestModelValidateMessageToJson:
    """Test ModelValidateMessage to_json method."""

    def test_to_json_returns_string(self):
        """Test to_json returns a JSON string."""
        msg = ModelValidateMessage(message="Test")
        json_str = msg.to_json()

        assert isinstance(json_str, str)

    def test_to_json_is_valid_json(self):
        """Test to_json returns valid JSON."""
        msg = ModelValidateMessage(message="Test", code="ERR_001")
        json_str = msg.to_json()

        # Should be parseable as JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["message"] == "Test"
        assert parsed["code"] == "ERR_001"

    def test_to_json_includes_all_fields(self):
        """Test to_json includes all fields."""
        ctx = ModelValidateMessageContext(field="test_field")
        msg = ModelValidateMessage(
            message="Test message",
            file="test.py",
            line=10,
            severity=EnumLogLevel.WARNING,
            code="WARN_001",
            context=ctx,
        ).with_hash()

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["message"] == "Test message"
        assert parsed["file"] == "test.py"
        assert parsed["line"] == 10
        assert parsed["code"] == "WARN_001"
        assert "context" in parsed
        assert parsed["hash"] is not None


class TestModelValidateMessageToText:
    """Test ModelValidateMessage to_text method."""

    def test_to_text_returns_string(self):
        """Test to_text returns a string."""
        msg = ModelValidateMessage(message="Test")
        text = msg.to_text()

        assert isinstance(text, str)

    def test_to_text_includes_severity(self):
        """Test to_text includes severity."""
        msg = ModelValidateMessage(message="Test error", severity=EnumLogLevel.ERROR)
        text = msg.to_text()

        assert "ERROR" in text
        assert "Test error" in text

    def test_to_text_includes_file(self):
        """Test to_text includes file information."""
        msg = ModelValidateMessage(message="Test", file="test.py")
        text = msg.to_text()

        assert "File: test.py" in text

    def test_to_text_includes_line(self):
        """Test to_text includes line number."""
        msg = ModelValidateMessage(message="Test", line=42)
        text = msg.to_text()

        assert "Line: 42" in text

    def test_to_text_includes_code(self):
        """Test to_text includes error code."""
        msg = ModelValidateMessage(message="Test", code="ERR_001")
        text = msg.to_text()

        assert "Code: ERR_001" in text

    def test_to_text_includes_uid(self):
        """Test to_text includes UID."""
        msg = ModelValidateMessage(message="Test")
        text = msg.to_text()

        assert "UID:" in text
        assert msg.uid in text

    def test_to_text_includes_hash(self):
        """Test to_text includes hash."""
        msg = ModelValidateMessage(message="Test").with_hash()
        text = msg.to_text()

        assert "Hash:" in text
        assert msg.hash in text

    def test_to_text_computes_hash_if_not_set(self):
        """Test to_text computes hash if not already set."""
        msg = ModelValidateMessage(message="Test")
        text = msg.to_text()

        # Hash should be computed and included
        assert "Hash:" in text

    def test_to_text_includes_context(self):
        """Test to_text includes context information."""
        ctx = ModelValidateMessageContext(field="username")
        msg = ModelValidateMessage(message="Test", context=ctx)
        text = msg.to_text()

        assert "Context:" in text


class TestModelValidateMessageToCi:
    """Test ModelValidateMessage to_ci method."""

    def test_to_ci_returns_string(self):
        """Test to_ci returns a string."""
        msg = ModelValidateMessage(message="Test")
        ci_str = msg.to_ci()

        assert isinstance(ci_str, str)

    def test_to_ci_includes_severity(self):
        """Test to_ci includes severity level."""
        msg = ModelValidateMessage(message="Test error", severity=EnumLogLevel.ERROR)
        ci_str = msg.to_ci()

        assert "error" in ci_str

    def test_to_ci_includes_message(self):
        """Test to_ci includes the error message."""
        msg = ModelValidateMessage(message="Test error message")
        ci_str = msg.to_ci()

        assert "Test error message" in ci_str

    def test_to_ci_includes_file_and_line(self):
        """Test to_ci includes file and line when present."""
        msg = ModelValidateMessage(message="Test", file="test.py", line=42)
        ci_str = msg.to_ci()

        assert "file=test.py" in ci_str
        assert "line=42" in ci_str

    def test_to_ci_without_file_and_line(self):
        """Test to_ci format when file and line are not provided."""
        msg = ModelValidateMessage(message="Test")
        ci_str = msg.to_ci()

        # Should not include file and line info
        assert "file=" not in ci_str
        assert "line=" not in ci_str

    def test_to_ci_github_actions_format(self):
        """Test to_ci produces GitHub Actions annotation format."""
        msg = ModelValidateMessage(
            message="Validation failed",
            file="src/main.py",
            line=10,
            severity=EnumLogLevel.ERROR,
        )
        ci_str = msg.to_ci()

        # GitHub Actions format: ::error file=...,line=...::message
        assert "::" in ci_str
        assert ci_str.startswith("::")


class TestModelValidateMessageCompatibilityAliases:
    """Test compatibility aliases for ModelValidateMessage."""

    def test_validate_message_model_alias(self):
        """Test ValidateMessageModel is an alias."""
        assert ValidateMessageModel is ModelValidateMessage

    def test_validate_message_model_context_alias(self):
        """Test ValidateMessageModelContext is an alias."""
        assert ValidateMessageModelContext is ModelValidateMessageContext


class TestModelValidateResultInstantiation:
    """Test ModelValidateResult instantiation."""

    def test_minimal_initialization(self):
        """Test ModelValidateResult with empty messages list."""
        result = ModelValidateResult(messages=[])
        assert len(result.messages) == 0
        assert result.status == EnumOnexStatus.ERROR
        assert result.summary is None
        assert result.uid is not None
        assert result.timestamp is not None

    def test_with_messages(self):
        """Test ModelValidateResult with messages."""
        msg1 = ModelValidateMessage(message="Error 1")
        msg2 = ModelValidateMessage(message="Error 2")

        result = ModelValidateResult(
            messages=[msg1, msg2],
            status=EnumOnexStatus.ERROR,
        )

        assert len(result.messages) == 2
        assert result.messages[0].message == "Error 1"
        assert result.messages[1].message == "Error 2"

    def test_with_summary(self):
        """Test ModelValidateResult with summary."""
        result = ModelValidateResult(
            messages=[],
            status=EnumOnexStatus.SUCCESS,
            summary="Validation passed successfully",
        )

        assert result.summary == "Validation passed successfully"
        assert result.status == EnumOnexStatus.SUCCESS

    def test_default_status(self):
        """Test default status is ERROR."""
        result = ModelValidateResult(messages=[])
        assert result.status == EnumOnexStatus.ERROR

    def test_uid_is_unique(self):
        """Test each result gets a unique UID."""
        result1 = ModelValidateResult(messages=[])
        result2 = ModelValidateResult(messages=[])

        assert result1.uid != result2.uid

    def test_various_statuses(self):
        """Test result with various status values."""
        for status in [
            EnumOnexStatus.SUCCESS,
            EnumOnexStatus.ERROR,
            EnumOnexStatus.WARNING,
            EnumOnexStatus.SKIPPED,
        ]:
            result = ModelValidateResult(messages=[], status=status)
            assert result.status == status


class TestModelValidateResultComputeHash:
    """Test ModelValidateResult compute_hash method."""

    def test_compute_hash_returns_string(self):
        """Test compute_hash returns a hex string."""
        result = ModelValidateResult(messages=[])
        hash_value = result.compute_hash()

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 produces 64 hex characters

    def test_compute_hash_includes_messages(self):
        """Test hash changes with different messages."""
        msg1 = ModelValidateMessage(message="Error 1").with_hash()
        msg2 = ModelValidateMessage(message="Error 2").with_hash()

        result1 = ModelValidateResult(messages=[msg1])
        result2 = ModelValidateResult(messages=[msg2])

        hash1 = result1.compute_hash()
        hash2 = result2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_includes_status(self):
        """Test hash includes status."""
        result1 = ModelValidateResult(messages=[], status=EnumOnexStatus.SUCCESS)
        result2 = ModelValidateResult(messages=[], status=EnumOnexStatus.ERROR)

        hash1 = result1.compute_hash()
        hash2 = result2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_includes_summary(self):
        """Test hash includes summary."""
        result1 = ModelValidateResult(messages=[], summary="Summary 1")
        result2 = ModelValidateResult(messages=[], summary="Summary 2")

        hash1 = result1.compute_hash()
        hash2 = result2.compute_hash()

        assert hash1 != hash2

    def test_compute_hash_with_message_without_hash(self):
        """Test hash computation when message doesn't have hash set."""
        msg = ModelValidateMessage(message="Test")
        result = ModelValidateResult(messages=[msg])

        hash_value = result.compute_hash()
        assert isinstance(hash_value, str)


class TestModelValidateResultWithHash:
    """Test ModelValidateResult with_hash method."""

    def test_with_hash_sets_hash_field(self):
        """Test with_hash sets the hash field."""
        result = ModelValidateResult(messages=[])
        assert result.hash is None

        result.with_hash()
        assert result.hash is not None

    def test_with_hash_returns_self(self):
        """Test with_hash returns self for chaining."""
        result = ModelValidateResult(messages=[])
        returned = result.with_hash()

        assert returned is result

    def test_with_hash_chaining(self):
        """Test with_hash can be chained during initialization."""
        result = ModelValidateResult(messages=[]).with_hash()

        assert result.hash is not None


class TestModelValidateResultToJson:
    """Test ModelValidateResult to_json method."""

    def test_to_json_returns_string(self):
        """Test to_json returns a JSON string."""
        result = ModelValidateResult(messages=[])
        json_str = result.to_json()

        assert isinstance(json_str, str)

    def test_to_json_is_valid_json(self):
        """Test to_json returns valid JSON."""
        result = ModelValidateResult(
            messages=[],
            status=EnumOnexStatus.SUCCESS,
            summary="Test summary",
        )
        json_str = result.to_json()

        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["summary"] == "Test summary"

    def test_to_json_includes_messages(self):
        """Test to_json includes all messages."""
        msg1 = ModelValidateMessage(message="Error 1")
        msg2 = ModelValidateMessage(message="Error 2")

        result = ModelValidateResult(messages=[msg1, msg2])
        json_str = result.to_json()

        parsed = json.loads(json_str)
        assert len(parsed["messages"]) == 2


class TestModelValidateResultToText:
    """Test ModelValidateResult to_text method."""

    def test_to_text_returns_string(self):
        """Test to_text returns a string."""
        result = ModelValidateResult(messages=[])
        text = result.to_text()

        assert isinstance(text, str)

    def test_to_text_includes_status(self):
        """Test to_text includes status."""
        result = ModelValidateResult(messages=[], status=EnumOnexStatus.SUCCESS)
        text = result.to_text()

        assert "Status: success" in text

    def test_to_text_includes_summary(self):
        """Test to_text includes summary when present."""
        result = ModelValidateResult(
            messages=[],
            summary="Validation completed",
        )
        text = result.to_text()

        assert "Summary: Validation completed" in text

    def test_to_text_includes_uid(self):
        """Test to_text includes UID."""
        result = ModelValidateResult(messages=[])
        text = result.to_text()

        assert "UID:" in text
        assert result.uid in text

    def test_to_text_includes_hash(self):
        """Test to_text includes hash."""
        result = ModelValidateResult(messages=[]).with_hash()
        text = result.to_text()

        assert "Hash:" in text
        assert result.hash in text

    def test_to_text_computes_hash_if_not_set(self):
        """Test to_text computes hash if not already set."""
        result = ModelValidateResult(messages=[])
        text = result.to_text()

        assert "Hash:" in text

    def test_to_text_includes_messages(self):
        """Test to_text includes all messages."""
        msg1 = ModelValidateMessage(message="Error 1")
        msg2 = ModelValidateMessage(message="Error 2")

        result = ModelValidateResult(messages=[msg1, msg2])
        text = result.to_text()

        # Each message should call to_text()
        assert "ERROR" in text  # From message severity


class TestModelValidateResultToCi:
    """Test ModelValidateResult to_ci method."""

    def test_to_ci_returns_string(self):
        """Test to_ci returns a string."""
        result = ModelValidateResult(messages=[])
        ci_str = result.to_ci()

        assert isinstance(ci_str, str)

    def test_to_ci_includes_all_messages(self):
        """Test to_ci includes all messages in CI format."""
        msg1 = ModelValidateMessage(message="Error 1", file="test1.py", line=10)
        msg2 = ModelValidateMessage(message="Error 2", file="test2.py", line=20)

        result = ModelValidateResult(messages=[msg1, msg2])
        ci_str = result.to_ci()

        assert "Error 1" in ci_str
        assert "Error 2" in ci_str

    def test_to_ci_with_empty_messages(self):
        """Test to_ci with no messages."""
        result = ModelValidateResult(messages=[])
        ci_str = result.to_ci()

        # Should return empty string or minimal output
        assert isinstance(ci_str, str)


class TestModelValidateResultCompatibilityAliases:
    """Test compatibility aliases for ModelValidateResult."""

    def test_validate_result_model_alias(self):
        """Test ValidateResultModel is an alias."""
        assert ValidateResultModel is ModelValidateResult


class TestValidationModelsIntegration:
    """Test integration scenarios with all validation models."""

    def test_complete_validation_workflow(self):
        """Test complete validation workflow with context, messages, and result."""
        # Create context
        ctx1 = ModelValidateMessageContext(
            field="email",
            expected="valid email",
            actual="invalid@",
            reason="Invalid email format",
        )

        ctx2 = ModelValidateMessageContext(
            field="age",
            expected="positive integer",
            actual=-5,
            reason="Age cannot be negative",
        )

        # Create messages
        msg1 = ModelValidateMessage(
            message="Email validation failed",
            file="user.py",
            line=42,
            severity=EnumLogLevel.ERROR,
            code="VALIDATION_EMAIL",
            context=ctx1,
        ).with_hash()

        msg2 = ModelValidateMessage(
            message="Age validation failed",
            file="user.py",
            line=45,
            severity=EnumLogLevel.ERROR,
            code="VALIDATION_AGE",
            context=ctx2,
        ).with_hash()

        # Create result
        result = ModelValidateResult(
            messages=[msg1, msg2],
            status=EnumOnexStatus.ERROR,
            summary="2 validation errors found",
        ).with_hash()

        # Verify complete structure
        assert len(result.messages) == 2
        assert result.status == EnumOnexStatus.ERROR
        assert result.summary == "2 validation errors found"
        assert result.hash is not None
        assert all(msg.hash is not None for msg in result.messages)

    def test_success_validation_result(self):
        """Test validation result with success status."""
        result = ModelValidateResult(
            messages=[],
            status=EnumOnexStatus.SUCCESS,
            summary="All validations passed",
        )

        assert result.status == EnumOnexStatus.SUCCESS
        assert len(result.messages) == 0

    def test_warning_validation_result(self):
        """Test validation result with warnings."""
        msg = ModelValidateMessage(
            message="Deprecated field usage",
            severity=EnumLogLevel.WARNING,
            code="DEPRECATED",
        )

        result = ModelValidateResult(
            messages=[msg],
            status=EnumOnexStatus.WARNING,
            summary="1 warning found",
        )

        assert result.status == EnumOnexStatus.WARNING
        assert len(result.messages) == 1
        assert result.messages[0].severity == EnumLogLevel.WARNING

    def test_serialization_round_trip_complete(self):
        """Test complete serialization round trip."""
        ctx = ModelValidateMessageContext(field="test", reason="test reason")
        msg = ModelValidateMessage(
            message="Test message",
            file="test.py",
            line=10,
            context=ctx,
        ).with_hash()

        result = ModelValidateResult(
            messages=[msg],
            status=EnumOnexStatus.ERROR,
            summary="Test summary",
        ).with_hash()

        # Serialize
        dumped = result.model_dump()

        # Deserialize
        restored = ModelValidateResult(**dumped)

        # Verify restoration
        assert restored.status == result.status
        assert restored.summary == result.summary
        assert len(restored.messages) == len(result.messages)
        assert restored.messages[0].message == result.messages[0].message
