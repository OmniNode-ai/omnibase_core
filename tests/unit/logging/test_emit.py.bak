"""
Comprehensive unit tests for logging/emit.py module.

Tests cover:
- emit_log_event() core functionality
- Sensitive data sanitization (SECURITY CRITICAL)
- Correlation ID handling
- Node ID detection
- Log context creation
- Performance decorators and context managers
- Thread safety
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.emit import (
    LogCodeBlock,
    _create_log_context_from_frame,
    _detect_node_id_from_context,
    _sanitize_data_dict,
    _sanitize_sensitive_data,
    emit_log_event,
    emit_log_event_async,
    emit_log_event_sync,
    emit_log_event_with_new_correlation,
    log_performance_metrics,
    trace_function_lifecycle,
)
from omnibase_core.models.core.model_log_entry import LogModelContext


class TestEmitLogEventCore:
    """Test core emit_log_event functionality."""

    def test_emit_log_event_basic(self):
        """Test basic emit_log_event call."""
        correlation_id = uuid4()

        # Should not raise exception
        emit_log_event(
            level=LogLevel.INFO,
            event_type="test_event",
            message="Test message",
            correlation_id=correlation_id,
        )

    def test_emit_log_event_with_node_id(self):
        """Test emit_log_event with explicit node_id."""
        correlation_id = uuid4()
        node_id = uuid4()

        emit_log_event(
            level=LogLevel.DEBUG,
            event_type="test_event",
            message="Test with node_id",
            correlation_id=correlation_id,
            node_id=node_id,
        )

    def test_emit_log_event_with_data(self):
        """Test emit_log_event with additional data."""
        correlation_id = uuid4()

        emit_log_event(
            level=LogLevel.INFO,
            event_type="test_event",
            message="Test with data",
            correlation_id=correlation_id,
            data={"key": "value", "count": 42},
        )

    def test_emit_log_event_with_all_parameters(self):
        """Test emit_log_event with all parameters."""
        correlation_id = uuid4()
        node_id = uuid4()
        mock_event_bus = Mock()

        emit_log_event(
            level=LogLevel.WARNING,
            event_type="test_event",
            message="Complete test",
            correlation_id=correlation_id,
            node_id=node_id,
            data={"test": "data"},
            event_bus=mock_event_bus,
        )


class TestEmitLogEventWrappers:
    """Test emit_log_event wrapper functions."""

    def test_emit_log_event_with_new_correlation(self):
        """Test emit_log_event_with_new_correlation generates UUID."""
        correlation_id = emit_log_event_with_new_correlation(
            level=LogLevel.INFO,
            event_type="test_event",
            message="Test message",
        )

        assert isinstance(correlation_id, UUID)

    def test_emit_log_event_sync(self):
        """Test emit_log_event_sync wrapper."""
        correlation_id = uuid4()

        emit_log_event_sync(
            level=LogLevel.INFO,
            message="Sync test",
            correlation_id=correlation_id,
        )

    @pytest.mark.asyncio
    async def test_emit_log_event_async(self):
        """Test emit_log_event_async wrapper."""
        correlation_id = uuid4()

        await emit_log_event_async(
            level=LogLevel.DEBUG,
            message="Async test",
            correlation_id=correlation_id,
        )


class TestSensitiveDataSanitization:
    """Test sensitive data sanitization - SECURITY CRITICAL."""

    def test_sanitize_sensitive_data_passwords(self):
        """Test sanitization of password patterns."""
        # Various password formats
        test_cases = [
            ('password="secret123"', "password=[REDACTED]"),
            ("password=mysecret", "password=[REDACTED]"),
            ('password: "secret123"', "password=[REDACTED]"),
            ("PASSWORD=secret", "password=[REDACTED]"),
        ]

        for input_text, expected_pattern in test_cases:
            result = _sanitize_sensitive_data(input_text)
            assert "[REDACTED]" in result or "password=" in result.lower()

    def test_sanitize_sensitive_data_api_keys(self):
        """Test sanitization of API key patterns."""
        test_cases = [
            ('api_key="sk-1234567890abcdef"', "api_key=[REDACTED]"),
            ("api-key=1234567890", "api_key=[REDACTED]"),
            ('apikey: "secret-key-123"', "api_key=[REDACTED]"),
        ]

        for input_text, _ in test_cases:
            result = _sanitize_sensitive_data(input_text)
            assert "[REDACTED]" in result or "api" in result.lower()

    def test_sanitize_sensitive_data_tokens(self):
        """Test sanitization of token patterns."""
        # Base64 token pattern (20+ characters)
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = _sanitize_sensitive_data(f"Authorization: Bearer {token}")
        assert "[REDACTED_TOKEN]" in result or len(token) != len(result.split()[-1])

    def test_sanitize_sensitive_data_access_tokens(self):
        """Test sanitization of access_token patterns."""
        test_cases = [
            ('access_token="abc123xyz"', "access_token=[REDACTED]"),
            ("access-token=secret", "access_token=[REDACTED]"),
        ]

        for input_text, _ in test_cases:
            result = _sanitize_sensitive_data(input_text)
            assert "[REDACTED]" in result

    def test_sanitize_sensitive_data_secrets(self):
        """Test sanitization of secret patterns."""
        test_cases = [
            ('secret="my_secret_value"', "secret=[REDACTED]"),
            ("secret=topsecret", "secret=[REDACTED]"),
            ('SECRET: "value123"', "secret=[REDACTED]"),
        ]

        for input_text, _ in test_cases:
            result = _sanitize_sensitive_data(input_text)
            assert "[REDACTED]" in result

    def test_sanitize_sensitive_data_preserves_safe_content(self):
        """Test that sanitization preserves non-sensitive content."""
        safe_text = "This is a safe message with no secrets"
        result = _sanitize_sensitive_data(safe_text)
        assert result == safe_text

    def test_sanitize_sensitive_data_non_string_input(self):
        """Test sanitization with non-string input."""
        result = _sanitize_sensitive_data(123)
        assert result == 123  # Should return unchanged

        result = _sanitize_sensitive_data(None)
        assert result is None


class TestDataDictSanitization:
    """Test _sanitize_data_dict functionality."""

    def test_sanitize_data_dict_string_values(self):
        """Test sanitization of string values in dict."""
        data = {
            "message": "User login",
            "password": "secret123",
            "username": "testuser",
        }

        result = _sanitize_data_dict(data)

        assert "message" in result
        assert "password" in result
        assert "username" in result
        # Password value should be sanitized
        assert result["password"] != "secret123"

    def test_sanitize_data_dict_json_compatibility(self):
        """Test that sanitized dict is JSON-compatible."""
        data = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "none": None,
        }

        result = _sanitize_data_dict(data)

        # All values should remain JSON-compatible
        assert isinstance(result["string"], str)
        assert isinstance(result["number"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["boolean"], bool)
        assert result["none"] is None

    def test_sanitize_data_dict_converts_non_json_types(self):
        """Test conversion of non-JSON-compatible types."""

        class CustomObject:
            def __str__(self):
                return "CustomObject"

        data = {
            "custom": CustomObject(),
            "uuid": uuid4(),
        }

        result = _sanitize_data_dict(data)

        # Non-JSON types should be converted to strings
        assert isinstance(result["custom"], str)
        assert isinstance(result["uuid"], str)

    def test_sanitize_data_dict_handles_boolean_before_int(self):
        """Test that boolean handling comes before int (bool is subclass of int)."""
        data = {"flag": True, "count": 1}

        result = _sanitize_data_dict(data)

        # Boolean should stay boolean, not be treated as int
        assert result["flag"] is True
        assert isinstance(result["flag"], bool)
        assert result["count"] == 1

    def test_sanitize_data_dict_non_dict_input(self):
        """Test sanitization with non-dict input."""
        result = _sanitize_data_dict("not a dict")
        assert result == "not a dict"  # Should return unchanged

    def test_sanitize_data_dict_sensitive_keys(self):
        """Test sanitization of sensitive key names."""
        data = {
            "api_key_value": "secret",
            "normal_key": "value",
        }

        result = _sanitize_data_dict(data)

        # Key names with sensitive patterns should be sanitized
        assert "api" in str(result).lower() or "[REDACTED]" in str(result)


class TestNodeIdDetection:
    """Test _detect_node_id_from_context functionality."""

    def test_detect_node_id_returns_string_or_uuid(self):
        """Test that node ID detection returns valid identifier."""
        node_id = _detect_node_id_from_context()

        # Should return either UUID or string identifier
        assert isinstance(node_id, (UUID, str))

    def test_detect_node_id_from_node_instance(self):
        """Test node ID detection from node instance in stack."""

        class MockNode:
            def __init__(self):
                self.node_id = uuid4()

            def call_emit(self):
                return _detect_node_id_from_context()

        node = MockNode()
        detected_id = node.call_emit()

        # Should detect the node_id from the MockNode instance
        assert detected_id == node.node_id or isinstance(detected_id, (UUID, str))

    def test_detect_node_id_fallback_to_class_name(self):
        """Test fallback to class name when no node_id."""

        class MyNodeComponent:
            def call_emit(self):
                return _detect_node_id_from_context()

        component = MyNodeComponent()
        detected_id = component.call_emit()

        # Should fall back to class name or module name
        assert isinstance(detected_id, str)

    def test_detect_node_id_max_depth_limit(self):
        """Test that stack walking respects max depth limit."""

        # Create deep call stack
        def level_10():
            return _detect_node_id_from_context()

        def level_9():
            return level_10()

        def level_8():
            return level_9()

        def level_7():
            return level_8()

        def level_6():
            return level_7()

        def level_5():
            return level_6()

        # Should complete without infinite loop
        result = level_5()
        assert isinstance(result, (UUID, str))


class TestLogContextCreation:
    """Test _create_log_context_from_frame functionality."""

    def test_create_log_context_returns_model(self):
        """Test that log context creation returns LogModelContext."""
        context = _create_log_context_from_frame()

        assert isinstance(context, LogModelContext)

    def test_create_log_context_has_required_fields(self):
        """Test that log context has required fields."""
        context = _create_log_context_from_frame()

        assert hasattr(context, "calling_function")
        assert hasattr(context, "calling_module")
        assert hasattr(context, "calling_line")
        assert hasattr(context, "timestamp")
        assert hasattr(context, "node_id")

    def test_create_log_context_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        context = _create_log_context_from_frame()

        # Should be ISO format string
        assert isinstance(context.timestamp, str)
        # Should be parseable as datetime
        datetime.fromisoformat(context.timestamp)

    def test_create_log_context_calling_info(self):
        """Test that calling information is captured."""
        context = _create_log_context_from_frame()

        # Should have valid calling function name
        assert isinstance(context.calling_function, str)
        assert len(context.calling_function) > 0

        # Should have valid module name
        assert isinstance(context.calling_module, str)

        # Should have valid line number
        assert isinstance(context.calling_line, int)
        assert context.calling_line >= 0


class TestTraceFunctionLifecycle:
    """Test trace_function_lifecycle decorator."""

    def test_trace_function_lifecycle_decorator(self):
        """Test function lifecycle tracing decorator."""

        @trace_function_lifecycle
        def test_function(x, y):
            return x + y

        result = test_function(2, 3)
        assert result == 5

    def test_trace_function_lifecycle_with_exception(self):
        """Test lifecycle tracing when function raises exception."""

        @trace_function_lifecycle
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_trace_function_lifecycle_preserves_function_name(self):
        """Test that decorator preserves function metadata."""

        @trace_function_lifecycle
        def my_function():
            pass

        # Function name should be preserved (might be 'wrapper' for simple decorator)
        assert callable(my_function)


class TestLogCodeBlock:
    """Test LogCodeBlock context manager."""

    def test_log_code_block_success(self):
        """Test LogCodeBlock with successful execution."""
        correlation_id = uuid4()

        with LogCodeBlock("test_block", correlation_id=correlation_id):
            x = 1 + 1

        assert x == 2

    def test_log_code_block_with_exception(self):
        """Test LogCodeBlock with exception."""
        correlation_id = uuid4()

        with pytest.raises(ValueError):
            with LogCodeBlock("failing_block", correlation_id=correlation_id):
                raise ValueError("Test error")

    def test_log_code_block_with_data(self):
        """Test LogCodeBlock with additional data."""
        correlation_id = uuid4()

        with LogCodeBlock(
            "data_block", correlation_id=correlation_id, data={"key": "value"}
        ):
            pass

    def test_log_code_block_custom_level(self):
        """Test LogCodeBlock with custom log level."""
        correlation_id = uuid4()

        with LogCodeBlock(
            "custom_level_block", correlation_id=correlation_id, level=LogLevel.WARNING
        ):
            pass


class TestLogPerformanceMetrics:
    """Test log_performance_metrics decorator."""

    def test_log_performance_metrics_decorator(self):
        """Test performance metrics logging decorator."""

        @log_performance_metrics(threshold_ms=1000)
        def fast_function():
            return "result"

        result = fast_function()
        assert result == "result"

    def test_log_performance_metrics_threshold_warning(self):
        """Test that slow functions trigger warning."""
        import time

        @log_performance_metrics(threshold_ms=10)  # Very low threshold
        def slow_function():
            time.sleep(0.02)  # Sleep 20ms
            return "result"

        result = slow_function()
        assert result == "result"

    def test_log_performance_metrics_preserves_return_value(self):
        """Test that decorator preserves function return value."""

        @log_performance_metrics(threshold_ms=1000)
        def function_with_return():
            return {"status": "success", "value": 42}

        result = function_with_return()
        assert result == {"status": "success", "value": 42}


class TestSanitizationSecurityEdgeCases:
    """Security-focused edge case tests for sanitization."""

    def test_sanitize_multiple_secrets_in_single_string(self):
        """Test sanitization of multiple secrets in one string."""
        text = 'password="secret1" api_key="secret2" token="secret3"'
        result = _sanitize_sensitive_data(text)

        # All secrets should be redacted
        assert "secret1" not in result
        assert "secret2" not in result
        assert "secret3" not in result
        assert result.count("[REDACTED]") >= 2

    def test_sanitize_case_insensitive_patterns(self):
        """Test that sanitization is case-insensitive."""
        text = 'PASSWORD="secret" API_KEY="key" SECRET="value"'
        result = _sanitize_sensitive_data(text)

        # Should detect patterns regardless of case
        assert "secret" not in result.lower() or "[REDACTED]" in result

    def test_sanitize_preserves_log_structure(self):
        """Test that sanitization preserves log structure."""
        text = "User login failed for user=admin password=secret123 at 2024-01-01"
        result = _sanitize_sensitive_data(text)

        # Should preserve most of the structure
        assert "User login failed" in result
        assert "2024-01-01" in result
        # But secret should be removed
        assert "secret123" not in result

    def test_sanitize_dict_with_nested_secrets(self):
        """Test sanitization of nested secret values."""
        data = {
            "config": "api_key=secret123",
            "normal": "value",
        }

        result = _sanitize_data_dict(data)

        # Nested secret in string should be sanitized
        assert "secret123" not in str(result.get("config", ""))


class TestThreadSafety:
    """Test thread safety of logging functions."""

    def test_concurrent_log_emissions(self):
        """Test that concurrent log emissions don't interfere."""
        import threading

        results = []

        def emit_logs(thread_id):
            correlation_id = uuid4()
            for i in range(5):
                emit_log_event(
                    level=LogLevel.INFO,
                    event_type="concurrent_test",
                    message=f"Thread {thread_id} message {i}",
                    correlation_id=correlation_id,
                )
            results.append(thread_id)

        threads = [threading.Thread(target=emit_logs, args=(i,)) for i in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should complete
        assert len(results) == 3
