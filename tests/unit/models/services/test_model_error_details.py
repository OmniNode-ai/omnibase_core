"""
Unit tests for ModelErrorDetails.

Tests all aspects of the error details model including:
- Model instantiation and validation
- Required and optional field handling
- Default value behavior
- Factory method from_dict() with legacy format conversion
- is_retryable() method logic
- Nested inner_errors validation
- Datetime serialization
- Edge cases and error conditions
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.services.model_error_details import ModelErrorDetails


@pytest.mark.unit
class TestModelErrorDetailsInstantiation:
    """Test cases for ModelErrorDetails instantiation and basic validation."""

    def test_model_instantiation_minimal_required_fields(self):
        """Test that model can be instantiated with only required fields."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Validation failed",
        )

        assert error.error_code == "ERR001"
        assert error.error_type == "validation"
        assert error.error_message == "Validation failed"

    def test_model_instantiation_all_fields(self):
        """Test model instantiation with all fields populated."""
        request_id = uuid4()
        user_id = uuid4()
        session_id = uuid4()

        error = ModelErrorDetails(
            error_code="ERR002",
            error_type="runtime",
            error_message="Runtime error occurred",
            component="auth_service",
            operation="validate_token",
            stack_trace=["File main.py, line 10", "File auth.py, line 25"],
            inner_errors=None,
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            context_data={
                "key1": ModelSchemaValue.from_value("value1"),
            },
            retry_after_seconds=30,
            recovery_suggestions=["Try again later", "Check credentials"],
            documentation_url="https://docs.example.com/errors/ERR002",
        )

        assert error.error_code == "ERR002"
        assert error.error_type == "runtime"
        assert error.error_message == "Runtime error occurred"
        assert error.component == "auth_service"
        assert error.operation == "validate_token"
        assert len(error.stack_trace) == 2
        assert error.request_id == request_id
        assert error.user_id == user_id
        assert error.session_id == session_id
        assert len(error.context_data) == 1
        assert error.retry_after_seconds == 30
        assert len(error.recovery_suggestions) == 2
        assert error.documentation_url == "https://docs.example.com/errors/ERR002"

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing error_code
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorDetails(
                error_type="validation",
                error_message="Test message",
            )
        assert "error_code" in str(exc_info.value)

        # Missing error_type
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorDetails(
                error_code="ERR001",
                error_message="Test message",
            )
        assert "error_type" in str(exc_info.value)

        # Missing error_message
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorDetails(
                error_code="ERR001",
                error_type="validation",
            )
        assert "error_message" in str(exc_info.value)


@pytest.mark.unit
class TestModelErrorDetailsDefaults:
    """Test default values for optional fields."""

    def test_timestamp_default(self):
        """Test that timestamp defaults to current UTC time."""
        before = datetime.now(UTC)
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
        )
        after = datetime.now(UTC)

        assert error.timestamp is not None
        assert before <= error.timestamp <= after

    def test_context_data_default(self):
        """Test that context_data defaults to empty dict."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
        )

        assert error.context_data == {}
        assert isinstance(error.context_data, dict)

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
        )

        assert error.component is None
        assert error.operation is None
        assert error.stack_trace is None
        assert error.inner_errors is None
        assert error.request_id is None
        assert error.user_id is None
        assert error.session_id is None
        assert error.retry_after_seconds is None
        assert error.recovery_suggestions is None
        assert error.documentation_url is None


@pytest.mark.unit
class TestModelErrorDetailsFromDict:
    """Test the from_dict() factory method."""

    def test_from_dict_with_none(self):
        """Test from_dict() returns None when passed None."""
        result = ModelErrorDetails.from_dict(None)
        assert result is None

    def test_from_dict_with_standard_format(self):
        """Test from_dict() with standard field names."""
        data = {
            "error_code": "ERR001",
            "error_type": "validation",
            "error_message": "Standard format error",
        }

        error = ModelErrorDetails.from_dict(data)

        assert error is not None
        assert error.error_code == "ERR001"
        assert error.error_type == "validation"
        assert error.error_message == "Standard format error"

    def test_from_dict_with_legacy_code_field(self):
        """Test from_dict() converts legacy 'code' to 'error_code'."""
        data = {
            "code": "LEGACY001",
            "error_type": "system",
            "error_message": "Legacy format error",
        }

        error = ModelErrorDetails.from_dict(data)

        assert error is not None
        assert error.error_code == "LEGACY001"
        assert error.error_type == "system"

    def test_from_dict_with_legacy_message_field(self):
        """Test from_dict() converts legacy 'message' to 'error_message'."""
        data = {
            "error_code": "ERR001",
            "error_type": "runtime",
            "message": "Legacy message format",
        }

        error = ModelErrorDetails.from_dict(data)

        assert error is not None
        assert error.error_message == "Legacy message format"

    def test_from_dict_with_missing_error_type(self):
        """Test from_dict() defaults error_type to 'runtime' when missing."""
        data = {
            "error_code": "ERR001",
            "error_message": "No type specified",
        }

        error = ModelErrorDetails.from_dict(data)

        assert error is not None
        assert error.error_type == "runtime"

    def test_from_dict_with_all_legacy_fields(self):
        """Test from_dict() handles all legacy field conversions together."""
        data = {
            "code": "LEGACY002",
            "message": "Full legacy format",
        }

        error = ModelErrorDetails.from_dict(data)

        assert error is not None
        assert error.error_code == "LEGACY002"
        assert error.error_message == "Full legacy format"
        assert error.error_type == "runtime"  # Default

    def test_from_dict_with_all_fields(self):
        """Test from_dict() with all fields populated."""
        request_id = uuid4()
        data = {
            "error_code": "ERR003",
            "error_type": "validation",
            "error_message": "Full error details",
            "component": "api_gateway",
            "operation": "process_request",
            "request_id": request_id,
            "retry_after_seconds": 60,
            "recovery_suggestions": ["Retry", "Contact support"],
        }

        error = ModelErrorDetails.from_dict(data)

        assert error is not None
        assert error.error_code == "ERR003"
        assert error.component == "api_gateway"
        assert error.operation == "process_request"
        assert error.request_id == request_id
        assert error.retry_after_seconds == 60
        assert len(error.recovery_suggestions) == 2

    def test_from_dict_preserves_standard_fields_over_legacy(self):
        """Test that standard field names take precedence over legacy."""
        data = {
            "error_code": "STANDARD",
            "code": "LEGACY",
            "error_type": "validation",
            "error_message": "Standard message",
            "message": "Legacy message",
        }

        error = ModelErrorDetails.from_dict(data)

        assert error is not None
        # Standard fields should be used, legacy fields should not overwrite
        assert error.error_code == "STANDARD"
        assert error.error_message == "Standard message"


@pytest.mark.unit
class TestModelErrorDetailsIsRetryable:
    """Test the is_retryable() method."""

    def test_is_retryable_with_retry_after_seconds(self):
        """Test is_retryable() returns True when retry_after_seconds is set."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Retryable error",
            retry_after_seconds=30,
        )

        assert error.is_retryable() is True

    def test_is_retryable_with_timeout_error_type(self):
        """Test is_retryable() returns True for timeout error type."""
        error = ModelErrorDetails(
            error_code="TIMEOUT001",
            error_type="timeout",
            error_message="Request timed out",
        )

        assert error.is_retryable() is True

    def test_is_retryable_with_rate_limit_error_type(self):
        """Test is_retryable() returns True for rate_limit error type."""
        error = ModelErrorDetails(
            error_code="RATELIMIT001",
            error_type="rate_limit",
            error_message="Rate limit exceeded",
        )

        assert error.is_retryable() is True

    def test_is_retryable_with_validation_error_type(self):
        """Test is_retryable() returns False for validation error type."""
        error = ModelErrorDetails(
            error_code="VAL001",
            error_type="validation",
            error_message="Validation error",
        )

        assert error.is_retryable() is False

    def test_is_retryable_with_runtime_error_type(self):
        """Test is_retryable() returns False for runtime error type."""
        error = ModelErrorDetails(
            error_code="RUN001",
            error_type="runtime",
            error_message="Runtime error",
        )

        assert error.is_retryable() is False

    def test_is_retryable_with_system_error_type(self):
        """Test is_retryable() returns False for system error type."""
        error = ModelErrorDetails(
            error_code="SYS001",
            error_type="system",
            error_message="System error",
        )

        assert error.is_retryable() is False

    def test_is_retryable_with_retry_seconds_and_non_retryable_type(self):
        """Test is_retryable() returns True when retry_after_seconds is set regardless of type."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",  # Normally not retryable
            error_message="Error with retry",
            retry_after_seconds=10,
        )

        # Should be True because retry_after_seconds is set
        assert error.is_retryable() is True

    def test_is_retryable_with_zero_retry_seconds(self):
        """Test is_retryable() with zero retry_after_seconds."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Zero retry seconds",
            retry_after_seconds=0,
        )

        # 0 is still "not None", so should be True
        assert error.is_retryable() is True


@pytest.mark.unit
class TestModelErrorDetailsInnerErrors:
    """Test nested inner_errors validation."""

    def test_single_inner_error(self):
        """Test model with a single inner error."""
        inner_error = ModelErrorDetails(
            error_code="INNER001",
            error_type="validation",
            error_message="Inner error message",
        )

        outer_error = ModelErrorDetails(
            error_code="OUTER001",
            error_type="runtime",
            error_message="Outer error message",
            inner_errors=[inner_error],
        )

        assert outer_error.inner_errors is not None
        assert len(outer_error.inner_errors) == 1
        assert outer_error.inner_errors[0].error_code == "INNER001"

    def test_multiple_inner_errors(self):
        """Test model with multiple inner errors."""
        inner_errors = [
            ModelErrorDetails(
                error_code="INNER001",
                error_type="validation",
                error_message="First inner error",
            ),
            ModelErrorDetails(
                error_code="INNER002",
                error_type="validation",
                error_message="Second inner error",
            ),
            ModelErrorDetails(
                error_code="INNER003",
                error_type="validation",
                error_message="Third inner error",
            ),
        ]

        outer_error = ModelErrorDetails(
            error_code="OUTER001",
            error_type="runtime",
            error_message="Outer error with multiple inner errors",
            inner_errors=inner_errors,
        )

        assert len(outer_error.inner_errors) == 3
        assert outer_error.inner_errors[0].error_code == "INNER001"
        assert outer_error.inner_errors[1].error_code == "INNER002"
        assert outer_error.inner_errors[2].error_code == "INNER003"

    def test_deeply_nested_inner_errors(self):
        """Test model with deeply nested inner errors."""
        level3_error = ModelErrorDetails(
            error_code="LEVEL3",
            error_type="validation",
            error_message="Level 3 error",
        )

        level2_error = ModelErrorDetails(
            error_code="LEVEL2",
            error_type="runtime",
            error_message="Level 2 error",
            inner_errors=[level3_error],
        )

        level1_error = ModelErrorDetails(
            error_code="LEVEL1",
            error_type="system",
            error_message="Level 1 error",
            inner_errors=[level2_error],
        )

        assert level1_error.inner_errors[0].error_code == "LEVEL2"
        assert level1_error.inner_errors[0].inner_errors[0].error_code == "LEVEL3"

    def test_empty_inner_errors_list(self):
        """Test model with empty inner_errors list."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Error with empty inner list",
            inner_errors=[],
        )

        assert error.inner_errors == []
        assert len(error.inner_errors) == 0


@pytest.mark.unit
class TestModelErrorDetailsDatetimeSerialization:
    """Test datetime field serialization."""

    def test_serialize_datetime_to_iso(self):
        """Test that timestamp is serialized to ISO format."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
            timestamp=timestamp,
        )

        # Use model_dump to get serialized data
        data = error.model_dump()
        assert data["timestamp"] == "2024-01-15T10:30:00+00:00"

    def test_serialize_datetime_with_microseconds(self):
        """Test that timestamp with microseconds is serialized correctly."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=UTC)
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
            timestamp=timestamp,
        )

        data = error.model_dump()
        assert "2024-01-15T10:30:00.123456" in data["timestamp"]

    def test_json_serialization_with_datetime(self):
        """Test JSON serialization includes properly formatted timestamp."""
        timestamp = datetime(2024, 6, 20, 15, 45, 30, tzinfo=UTC)
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test message",
            timestamp=timestamp,
        )

        json_str = error.model_dump_json()
        assert "2024-06-20T15:45:30" in json_str


@pytest.mark.unit
class TestModelErrorDetailsContextData:
    """Test context_data field handling."""

    def test_context_data_with_string_values(self):
        """Test context_data with string ModelSchemaValue."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
            context_data={
                "field_name": ModelSchemaValue.from_value("email"),
                "expected_format": ModelSchemaValue.from_value("user@domain.com"),
            },
        )

        assert len(error.context_data) == 2
        assert error.context_data["field_name"].to_value() == "email"

    def test_context_data_with_numeric_values(self):
        """Test context_data with numeric ModelSchemaValue."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
            context_data={
                "expected_min": ModelSchemaValue.from_value(0),
                "expected_max": ModelSchemaValue.from_value(100),
                "actual_value": ModelSchemaValue.from_value(150),
            },
        )

        assert len(error.context_data) == 3
        assert error.context_data["actual_value"].to_value() == 150

    def test_context_data_with_boolean_values(self):
        """Test context_data with boolean ModelSchemaValue."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test message",
            context_data={
                "required": ModelSchemaValue.from_value(True),
                "provided": ModelSchemaValue.from_value(False),
            },
        )

        assert error.context_data["required"].to_value() is True
        assert error.context_data["provided"].to_value() is False

    def test_context_data_with_mixed_types(self):
        """Test context_data with mixed ModelSchemaValue types."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test message",
            context_data={
                "string_val": ModelSchemaValue.from_value("test"),
                "int_val": ModelSchemaValue.from_value(42),
                "float_val": ModelSchemaValue.from_value(3.14),
                "bool_val": ModelSchemaValue.from_value(True),
            },
        )

        assert len(error.context_data) == 4
        assert error.context_data["string_val"].to_value() == "test"
        assert error.context_data["int_val"].to_value() == 42
        assert error.context_data["float_val"].to_value() == 3.14
        assert error.context_data["bool_val"].to_value() is True


@pytest.mark.unit
class TestModelErrorDetailsUUIDs:
    """Test UUID field handling."""

    def test_request_id_uuid(self):
        """Test request_id with valid UUID."""
        request_id = uuid4()
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test message",
            request_id=request_id,
        )

        assert error.request_id == request_id
        assert isinstance(error.request_id, UUID)

    def test_user_id_uuid(self):
        """Test user_id with valid UUID."""
        user_id = uuid4()
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test message",
            user_id=user_id,
        )

        assert error.user_id == user_id
        assert isinstance(error.user_id, UUID)

    def test_session_id_uuid(self):
        """Test session_id with valid UUID."""
        session_id = uuid4()
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test message",
            session_id=session_id,
        )

        assert error.session_id == session_id
        assert isinstance(error.session_id, UUID)

    def test_all_uuid_fields(self):
        """Test all UUID fields populated."""
        request_id = uuid4()
        user_id = uuid4()
        session_id = uuid4()

        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test message",
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )

        assert error.request_id == request_id
        assert error.user_id == user_id
        assert error.session_id == session_id


@pytest.mark.unit
class TestModelErrorDetailsEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_string_fields(self):
        """Test model with empty string fields."""
        error = ModelErrorDetails(
            error_code="",
            error_type="",
            error_message="",
        )

        assert error.error_code == ""
        assert error.error_type == ""
        assert error.error_message == ""

    def test_whitespace_string_fields(self):
        """Test model with whitespace-only string fields."""
        error = ModelErrorDetails(
            error_code="   ",
            error_type="   ",
            error_message="   ",
        )

        assert error.error_code == "   "
        assert error.error_type == "   "
        assert error.error_message == "   "

    def test_special_characters_in_strings(self):
        """Test model with special characters in string fields."""
        error = ModelErrorDetails(
            error_code="ERR-001/TEST",
            error_type="validation/syntax",
            error_message="Error: Invalid value '<script>' in field \"name\"",
            component="auth-service.v2",
            operation="validate_input[0]",
        )

        assert error.error_code == "ERR-001/TEST"
        assert error.error_type == "validation/syntax"
        assert "<script>" in error.error_message
        assert '"name"' in error.error_message

    def test_unicode_in_strings(self):
        """Test model with Unicode characters."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Invalid character: cafe (cafe)",
            component="internationalization",
        )

        assert "cafe" in error.error_message

    def test_long_strings(self):
        """Test model with very long strings."""
        long_message = "A" * 10000
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message=long_message,
        )

        assert len(error.error_message) == 10000

    def test_long_stack_trace(self):
        """Test model with large stack trace."""
        stack_lines = [f"File file_{i}.py, line {i}" for i in range(100)]
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Error with large stack trace",
            stack_trace=stack_lines,
        )

        assert len(error.stack_trace) == 100

    def test_many_recovery_suggestions(self):
        """Test model with many recovery suggestions."""
        suggestions = [f"Suggestion {i}" for i in range(50)]
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Error with many suggestions",
            recovery_suggestions=suggestions,
        )

        assert len(error.recovery_suggestions) == 50

    def test_serialization_deserialization(self):
        """Test model serialization and deserialization."""
        original = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test error",
            component="test_component",
            retry_after_seconds=30,
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["error_code"] == "ERR001"
        assert data["retry_after_seconds"] == 30

        # Deserialize from dict
        restored = ModelErrorDetails.model_validate(data)
        assert restored.error_code == original.error_code
        assert restored.error_type == original.error_type
        assert restored.error_message == original.error_message
        assert restored.component == original.component
        assert restored.retry_after_seconds == original.retry_after_seconds

    def test_json_serialization_deserialization(self):
        """Test JSON serialization and deserialization."""
        original = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="JSON test error",
            component="json_component",
        )

        # Serialize to JSON
        json_str = original.model_dump_json()
        assert isinstance(json_str, str)
        assert "ERR001" in json_str

        # Deserialize from JSON
        restored = ModelErrorDetails.model_validate_json(json_str)
        assert restored.error_code == original.error_code
        assert restored.error_message == original.error_message

    def test_model_equality(self):
        """Test model equality comparison."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        error1 = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test error",
            timestamp=timestamp,
        )

        error2 = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test error",
            timestamp=timestamp,
        )

        error3 = ModelErrorDetails(
            error_code="ERR002",
            error_type="runtime",
            error_message="Different error",
            timestamp=timestamp,
        )

        assert error1 == error2
        assert error1 != error3

    def test_negative_retry_after_seconds(self):
        """Test model with negative retry_after_seconds (no validation prevents it)."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="timeout",
            error_message="Test error",
            retry_after_seconds=-1,
        )

        # Negative value is allowed by the model (no validation constraint)
        assert error.retry_after_seconds == -1
        # But is_retryable should still return True (it checks "is not None")
        assert error.is_retryable() is True


@pytest.mark.unit
class TestModelErrorDetailsRecoverySuggestions:
    """Test recovery_suggestions field handling."""

    def test_single_suggestion(self):
        """Test with single recovery suggestion."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test error",
            recovery_suggestions=["Try again later"],
        )

        assert len(error.recovery_suggestions) == 1
        assert error.recovery_suggestions[0] == "Try again later"

    def test_multiple_suggestions(self):
        """Test with multiple recovery suggestions."""
        suggestions = [
            "Check your network connection",
            "Verify your credentials",
            "Contact support if issue persists",
        ]
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test error",
            recovery_suggestions=suggestions,
        )

        assert len(error.recovery_suggestions) == 3
        assert "Check your network connection" in error.recovery_suggestions

    def test_empty_suggestions_list(self):
        """Test with empty recovery suggestions list."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test error",
            recovery_suggestions=[],
        )

        assert error.recovery_suggestions == []


@pytest.mark.unit
class TestModelErrorDetailsDocumentationUrl:
    """Test documentation_url field handling."""

    def test_valid_documentation_url(self):
        """Test with valid documentation URL."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test error",
            documentation_url="https://docs.example.com/errors/ERR001",
        )

        assert error.documentation_url == "https://docs.example.com/errors/ERR001"

    def test_documentation_url_with_query_params(self):
        """Test documentation URL with query parameters."""
        url = "https://docs.example.com/errors?code=ERR001&lang=en"
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test error",
            documentation_url=url,
        )

        assert error.documentation_url == url

    def test_documentation_url_with_fragment(self):
        """Test documentation URL with fragment."""
        url = "https://docs.example.com/errors#err001"
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="validation",
            error_message="Test error",
            documentation_url=url,
        )

        assert error.documentation_url == url


@pytest.mark.unit
class TestModelErrorDetailsStackTrace:
    """Test stack_trace field handling."""

    def test_single_line_stack_trace(self):
        """Test with single line stack trace."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test error",
            stack_trace=["File main.py, line 10, in <module>"],
        )

        assert len(error.stack_trace) == 1

    def test_typical_stack_trace(self):
        """Test with typical multi-line stack trace."""
        stack = [
            "Traceback (most recent call last):",
            "  File main.py, line 10, in <module>",
            "    result = process_data(data)",
            "  File process.py, line 25, in process_data",
            "    return validate(data)",
            "  File validate.py, line 15, in validate",
            "    raise ValidationError('Invalid data')",
            "ValidationError: Invalid data",
        ]

        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test error",
            stack_trace=stack,
        )

        assert len(error.stack_trace) == 8
        assert "Traceback" in error.stack_trace[0]
        assert "ValidationError" in error.stack_trace[-1]

    def test_empty_stack_trace(self):
        """Test with empty stack trace list."""
        error = ModelErrorDetails(
            error_code="ERR001",
            error_type="runtime",
            error_message="Test error",
            stack_trace=[],
        )

        assert error.stack_trace == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
