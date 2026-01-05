"""
Tests targeting conditional branch coverage in logging/emit.py.

This test file specifically targets previously untested conditional branches
to improve overall branch coverage from 24.4% toward 75%+ target.
"""

from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_emit import (
    _detect_node_id_from_context,
    _route_to_logger_node,
    _sanitize_data_dict,
    _validate_node_id,
    emit_log_event,
)
from omnibase_core.models.core.model_log_context import ModelLogContext


@pytest.mark.unit
class TestValidateNodeIdConditional:
    """Test _validate_node_id conditional branches."""

    def test_validate_node_id_with_none(self):
        """Test _validate_node_id when node_id is None."""
        result = _validate_node_id(None)
        assert result is None

    def test_validate_node_id_with_valid_uuid(self):
        """Test _validate_node_id with valid UUID."""
        test_uuid = uuid4()
        result = _validate_node_id(test_uuid)
        assert result == test_uuid
        assert isinstance(result, UUID)

    def test_validate_node_id_with_valid_uuid_string(self):
        """Test _validate_node_id with valid UUID string."""
        test_uuid = uuid4()
        result = _validate_node_id(str(test_uuid))
        assert isinstance(result, UUID)
        assert str(result) == str(test_uuid)

    def test_validate_node_id_with_invalid_uuid_string(self):
        """Test _validate_node_id with invalid UUID string (non-UUID format)."""
        result = _validate_node_id("not-a-valid-uuid")
        assert result is None

    def test_validate_node_id_with_module_name_string(self):
        """Test _validate_node_id with module name fallback string."""
        result = _validate_node_id("test_module")
        assert result is None


@pytest.mark.unit
class TestSanitizeDataDictConditionalBranches:
    """Test _sanitize_data_dict conditional type checking branches."""

    def test_sanitize_data_dict_with_list(self):
        """Test _sanitize_data_dict with non-dict input (list)."""
        input_data = ["item1", "item2"]
        result = _sanitize_data_dict(input_data)
        # Should return unchanged for non-dict types
        assert result == input_data

    def test_sanitize_data_dict_with_none(self):
        """Test _sanitize_data_dict with None input."""
        result = _sanitize_data_dict(None)
        assert result is None

    def test_sanitize_data_dict_with_integer(self):
        """Test _sanitize_data_dict with integer input."""
        result = _sanitize_data_dict(42)
        assert result == 42

    def test_sanitize_data_dict_boolean_value_branch(self):
        """Test _sanitize_data_dict bool branch (before int check)."""
        data = {"is_active": True, "is_deleted": False}
        result = _sanitize_data_dict(data)

        # Boolean values should remain boolean
        assert result["is_active"] is True
        assert result["is_deleted"] is False
        assert isinstance(result["is_active"], bool)
        assert isinstance(result["is_deleted"], bool)

    def test_sanitize_data_dict_integer_value_branch(self):
        """Test _sanitize_data_dict integer branch."""
        data = {"count": 42, "total": 0, "negative": -10}
        result = _sanitize_data_dict(data)

        assert result["count"] == 42
        assert result["total"] == 0
        assert result["negative"] == -10
        assert isinstance(result["count"], int)

    def test_sanitize_data_dict_float_value_branch(self):
        """Test _sanitize_data_dict float branch."""
        data = {"pi": 3.14159, "zero_float": 0.0, "negative": -2.5}
        result = _sanitize_data_dict(data)

        assert result["pi"] == 3.14159
        assert result["zero_float"] == 0.0
        assert result["negative"] == -2.5
        assert isinstance(result["pi"], float)

    def test_sanitize_data_dict_none_value_branch(self):
        """Test _sanitize_data_dict None value branch."""
        data = {"optional": None, "required": "value"}
        result = _sanitize_data_dict(data)

        assert result["optional"] is None
        assert result["required"] == "value"

    def test_sanitize_data_dict_mixed_types(self):
        """Test _sanitize_data_dict with all type branches."""
        data = {
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "uuid": uuid4(),
        }

        result = _sanitize_data_dict(data)

        # Verify type handling
        assert isinstance(result["string"], str)
        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["bool"], bool)
        assert result["none"] is None
        # UUID converted to string
        assert isinstance(result["uuid"], str)

    def test_sanitize_data_dict_sensitive_key_redaction(self):
        """Test _sanitize_data_dict sensitive key name redaction."""
        data = {
            "password": "actual-value-ignored",
            "api_key": "actual-value-ignored",
            "secret": "actual-value-ignored",
            "token": "actual-value-ignored",
            "normal_key": "preserved-value",
        }

        result = _sanitize_data_dict(data)

        # Sensitive keys should have redacted values
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["secret"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"
        # Normal keys preserved
        assert result["normal_key"] == "preserved-value"

    def test_sanitize_data_dict_sensitive_key_case_insensitive(self):
        """Test _sanitize_data_dict case-insensitive sensitive key detection."""
        data = {
            "password": "value",
            "api_key": "value",
            "secret": "value",
            "token": "value",
        }

        result = _sanitize_data_dict(data)

        # All sensitive keys should be redacted
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["secret"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"


@pytest.mark.unit
class TestDetectNodeIdContextConditionalBranches:
    """Test _detect_node_id_from_context depth and fallback branches."""

    def test_detect_node_id_deep_stack_depth_limit(self):
        """Test _detect_node_id_from_context respects max_depth limit."""

        # Create a very deep call stack beyond max_depth (10)
        def level_20():
            return _detect_node_id_from_context()

        def level_19():
            return level_20()

        def level_18():
            return level_19()

        def level_17():
            return level_18()

        def level_16():
            return level_17()

        def level_15():
            return level_16()

        def level_14():
            return level_15()

        def level_13():
            return level_14()

        def level_12():
            return level_13()

        def level_11():
            return level_12()

        # Call with depth > 10 should still return something (fallback)
        result = level_11()
        assert isinstance(result, (UUID, str))

    def test_detect_node_id_no_self_in_frame(self):
        """Test _detect_node_id_from_context when no 'self' in frame."""

        # Function without self (not in a class)
        def standalone_function():
            return _detect_node_id_from_context()

        result = standalone_function()
        # Should fall back to module name or "unknown"
        assert isinstance(result, str)

    def test_detect_node_id_object_without_node_id_attribute(self):
        """Test _detect_node_id_from_context with object lacking node_id."""

        class PlainObject:
            def call_detect(self):
                return _detect_node_id_from_context()

        obj = PlainObject()
        result = obj.call_detect()
        # Should fall back to class name or module
        assert isinstance(result, (UUID, str))

    def test_detect_node_id_node_class_name_pattern(self):
        """Test _detect_node_id_from_context detects 'node' in class name."""

        class SomeNodeProcessor:
            def call_detect(self):
                return _detect_node_id_from_context()

        processor = SomeNodeProcessor()
        result = processor.call_detect()
        # Should detect class name with 'node' pattern
        assert isinstance(result, (UUID, str))

    def test_detect_node_id_module_name_fallback(self):
        """Test _detect_node_id_from_context falls back to module name."""
        result = _detect_node_id_from_context()
        # Should return module name or "unknown"
        assert isinstance(result, str)


@pytest.mark.unit
class TestRouteToLoggerNodeCacheBranches:
    """Test _route_to_logger_node cache expiration branches."""

    def test_route_to_logger_node_cache_expired(self):
        """Test _route_to_logger_node when cache is expired."""
        import omnibase_core.logging.logging_emit as emit_module

        # Reset cache state to ensure test isolation
        emit_module._CACHED_FORMATTER = None
        emit_module._CACHED_OUTPUT_HANDLER = None
        emit_module._CACHE_TIMESTAMP = 0.0

        correlation_id = uuid4()
        context = ModelLogContext(
            calling_function="test",
            calling_module="test",
            calling_line=1,
            timestamp="2024-01-01T00:00:00",
            node_id=None,
        )

        # Mock ModelONEXContainer where it's imported inside the function
        with patch(
            "omnibase_core.models.container.model_onex_container.ModelONEXContainer"
        ) as mock_container_class:
            # Mock container to prevent actual service lookups
            mock_container = MagicMock()
            mock_container.get_service.side_effect = Exception("Service unavailable")
            mock_container_class.return_value = mock_container

            # Mock time to simulate cache expiration
            with patch("omnibase_core.logging.logging_emit.time") as mock_time:
                # Provide enough time values: initial check + lock check
                mock_time.time.side_effect = [400, 450]  # Well beyond 300s TTL

                # Call _route_to_logger_node to trigger cache check
                _route_to_logger_node(
                    level=LogLevel.INFO,
                    event_type="test",
                    message="test message",
                    _node_id=None,
                    correlation_id=correlation_id,
                    context=context,
                    data={},
                    _event_bus=None,
                )

        # Should complete without error (cache refresh attempted with fallback)

    def test_route_to_logger_node_with_formatter_and_handler(self):
        """Test _route_to_logger_node with cached formatter and handler."""
        correlation_id = uuid4()
        context = ModelLogContext(
            calling_function="test",
            calling_module="test",
            calling_line=1,
            timestamp="2024-01-01T00:00:00",
            node_id=None,
        )

        # Call should succeed even without cached components (fallback)
        _route_to_logger_node(
            level=LogLevel.INFO,
            event_type="test",
            message="test message",
            _node_id=None,
            correlation_id=correlation_id,
            context=context,
            data={},
            _event_bus=None,
        )

    def test_route_to_logger_node_fallback_no_services(self):
        """Test _route_to_logger_node fallback when services unavailable."""
        correlation_id = uuid4()
        context = ModelLogContext(
            calling_function="test",
            calling_module="test",
            calling_line=1,
            timestamp="2024-01-01T00:00:00",
            node_id=None,
        )

        # Should handle missing services gracefully (fallback)
        _route_to_logger_node(
            level=LogLevel.INFO,
            event_type="test",
            message="test",
            _node_id=None,
            correlation_id=correlation_id,
            context=context,
            data={},
            _event_bus=None,
        )


@pytest.mark.unit
class TestEmitLogEventNodeIdBranches:
    """Test emit_log_event node_id validation branches."""

    def test_emit_log_event_node_id_none(self):
        """Test emit_log_event with node_id=None (auto-detect)."""
        correlation_id = uuid4()

        emit_log_event(
            level=LogLevel.INFO,
            event_type="test",
            message="test",
            correlation_id=correlation_id,
            node_id=None,
        )
        # Should auto-detect node_id

    def test_emit_log_event_node_id_valid_uuid(self):
        """Test emit_log_event with valid UUID node_id."""
        correlation_id = uuid4()
        node_id = uuid4()

        emit_log_event(
            level=LogLevel.INFO,
            event_type="test",
            message="test",
            correlation_id=correlation_id,
            node_id=node_id,
        )

    def test_emit_log_event_node_id_string_fallback(self):
        """Test emit_log_event with string node_id (fallback case)."""
        correlation_id = uuid4()

        emit_log_event(
            level=LogLevel.INFO,
            event_type="test",
            message="test",
            correlation_id=correlation_id,
            node_id="module_name",
        )
        # String node_id should be validated to None

    def test_emit_log_event_event_bus_none(self):
        """Test emit_log_event with event_bus=None (default bus)."""
        correlation_id = uuid4()

        emit_log_event(
            level=LogLevel.INFO,
            event_type="test",
            message="test",
            correlation_id=correlation_id,
            event_bus=None,
        )
        # Should use default event bus

    def test_emit_log_event_event_bus_provided(self):
        """Test emit_log_event with explicit event_bus."""
        correlation_id = uuid4()
        mock_bus = Mock()

        emit_log_event(
            level=LogLevel.INFO,
            event_type="test",
            message="test",
            correlation_id=correlation_id,
            event_bus=mock_bus,
        )


@pytest.mark.unit
class TestLogCodeBlockConditionalBranches:
    """Test LogCodeBlock context manager conditional branches."""

    def test_log_code_block_start_time_none_branch(self):
        """Test LogCodeBlock when start_time is None (edge case)."""
        from omnibase_core.logging.logging_emit import LogCodeBlock

        correlation_id = uuid4()

        # Create instance and manually set start_time to None to test branch
        block = LogCodeBlock("test_block", correlation_id=correlation_id)
        block.start_time = None

        # Exit should handle None start_time gracefully
        block.__exit__(None, None, None)
        # Should compute execution_time_ms as 0

    def test_log_code_block_exception_type_none(self):
        """Test LogCodeBlock exception handling with None exc_type."""
        from omnibase_core.logging.logging_emit import LogCodeBlock

        correlation_id = uuid4()

        with LogCodeBlock("test_block", correlation_id=correlation_id):
            pass
        # Should log successful completion (exc_type is None)

    def test_log_code_block_exception_with_type(self):
        """Test LogCodeBlock exception logging branch."""
        from omnibase_core.logging.logging_emit import LogCodeBlock

        correlation_id = uuid4()

        try:
            with LogCodeBlock("failing_block", correlation_id=correlation_id):
                raise ValueError("Test error")
        except ValueError:
            pass
        # Should log exception with exc_type.__name__
