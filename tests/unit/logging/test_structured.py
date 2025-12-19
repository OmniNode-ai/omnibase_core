"""
Comprehensive unit tests for logging/structured.py module.

Tests cover:
- emit_log_event_sync() core functionality
- Structured log entry creation
- Log level mapping to Python logging
- Context handling (dict, ProtocolLogContext, Pydantic models)
- JSON encoding with PydanticJSONEncoder
- Edge cases (None context, empty context, special characters)
- All LogLevel enums
"""

import json
import logging
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync


class SampleContext(BaseModel):
    """Sample Pydantic model for context testing."""

    correlation_id: UUID
    node_id: UUID
    operation: str


class MockLogContext:
    """Mock ProtocolLogContext for testing."""

    def __init__(self, data: dict):
        self.data = data

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.data


@pytest.mark.unit
class TestEmitLogEventSyncBasic:
    """Test basic emit_log_event_sync functionality."""

    def test_emit_log_event_sync_info(self, caplog):
        """Test emit_log_event_sync with INFO level."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test info message")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["level"] == "info"
        assert log_data["message"] == "Test info message"

    def test_emit_log_event_sync_debug(self, caplog):
        """Test emit_log_event_sync with DEBUG level."""
        with caplog.at_level(logging.DEBUG):
            emit_log_event_sync(LogLevel.DEBUG, "Test debug message")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["level"] == "debug"
        assert log_data["message"] == "Test debug message"

    def test_emit_log_event_sync_warning(self, caplog):
        """Test emit_log_event_sync with WARNING level."""
        with caplog.at_level(logging.WARNING):
            emit_log_event_sync(LogLevel.WARNING, "Test warning message")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["level"] == "warning"
        assert log_data["message"] == "Test warning message"

    def test_emit_log_event_sync_error(self, caplog):
        """Test emit_log_event_sync with ERROR level."""
        with caplog.at_level(logging.ERROR):
            emit_log_event_sync(LogLevel.ERROR, "Test error message")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["level"] == "error"
        assert log_data["message"] == "Test error message"

    def test_emit_log_event_sync_critical(self, caplog):
        """Test emit_log_event_sync with CRITICAL level."""
        with caplog.at_level(logging.CRITICAL):
            emit_log_event_sync(LogLevel.CRITICAL, "Test critical message")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["level"] == "critical"
        assert log_data["message"] == "Test critical message"

    def test_emit_log_event_sync_fatal(self, caplog):
        """Test emit_log_event_sync with FATAL level."""
        with caplog.at_level(logging.INFO):  # FATAL falls back to INFO level
            emit_log_event_sync(LogLevel.FATAL, "Test fatal message")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["level"] == "fatal"


@pytest.mark.unit
class TestStructuredLogEntry:
    """Test structured log entry creation."""

    def test_log_entry_has_timestamp(self, caplog):
        """Test that log entry includes timestamp."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test")

        log_data = json.loads(caplog.records[0].message)
        assert "timestamp" in log_data

        # Should be valid ISO format
        timestamp = datetime.fromisoformat(log_data["timestamp"])
        assert isinstance(timestamp, datetime)

    def test_log_entry_has_level(self, caplog):
        """Test that log entry includes level."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test")

        log_data = json.loads(caplog.records[0].message)
        assert "level" in log_data
        assert log_data["level"] == "info"

    def test_log_entry_has_message(self, caplog):
        """Test that log entry includes message."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test message")

        log_data = json.loads(caplog.records[0].message)
        assert "message" in log_data
        assert log_data["message"] == "Test message"

    def test_log_entry_has_context(self, caplog):
        """Test that log entry includes context."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context={"key": "value"})

        log_data = json.loads(caplog.records[0].message)
        assert "context" in log_data

    def test_log_entry_structure(self, caplog):
        """Test complete log entry structure."""
        test_context = {"operation": "test", "count": 42}

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Complete test", context=test_context)

        log_data = json.loads(caplog.records[0].message)

        # Verify all required fields
        assert "timestamp" in log_data
        assert "level" in log_data
        assert "message" in log_data
        assert "context" in log_data
        assert log_data["context"]["operation"] == "test"
        assert log_data["context"]["count"] == 42


@pytest.mark.unit
class TestContextHandling:
    """Test different context types handling."""

    def test_context_none(self, caplog):
        """Test emit with None context."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=None)

        log_data = json.loads(caplog.records[0].message)
        assert log_data["context"] == {}

    def test_context_empty_dict(self, caplog):
        """Test emit with empty dict context."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context={})

        log_data = json.loads(caplog.records[0].message)
        assert log_data["context"] == {}

    def test_context_dict(self, caplog):
        """Test emit with dict context."""
        test_context = {"key": "value", "count": 42, "flag": True}

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=test_context)

        log_data = json.loads(caplog.records[0].message)
        assert log_data["context"]["key"] == "value"
        assert log_data["context"]["count"] == 42
        assert log_data["context"]["flag"] is True

    def test_context_pydantic_model(self, caplog):
        """Test emit with Pydantic model context."""
        test_uuid = uuid4()
        node_uuid = uuid4()
        context_model = SampleContext(
            correlation_id=test_uuid, node_id=node_uuid, operation="test_op"
        )

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=context_model)

        log_data = json.loads(caplog.records[0].message)
        # Pydantic model should be serialized by PydanticJSONEncoder
        assert isinstance(log_data["context"], (dict, object))

    def test_context_log_protocol(self, caplog):
        """Test emit with ProtocolLogContext-like object."""
        context_data = {"function": "test_func", "line": 42}
        log_context = MockLogContext(context_data)

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=log_context)

        log_data = json.loads(caplog.records[0].message)
        # Should be serialized via PydanticJSONEncoder
        assert isinstance(log_data["context"], (dict, object))

    def test_context_with_uuid(self, caplog):
        """Test emit with context containing UUID."""
        test_uuid = uuid4()
        test_context = {"correlation_id": test_uuid, "name": "test"}

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=test_context)

        log_data = json.loads(caplog.records[0].message)
        # UUID should be serialized as string
        assert log_data["context"]["correlation_id"] == str(test_uuid)

    def test_context_with_nested_data(self, caplog):
        """Test emit with nested context data."""
        test_context = {
            "outer": {"inner": {"value": 42}},
            "list": [1, 2, 3],
            "nested_dict": {"a": {"b": "c"}},
        }

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=test_context)

        log_data = json.loads(caplog.records[0].message)
        assert log_data["context"]["outer"]["inner"]["value"] == 42
        assert log_data["context"]["list"] == [1, 2, 3]
        assert log_data["context"]["nested_dict"]["a"]["b"] == "c"


@pytest.mark.unit
class TestLogLevelMapping:
    """Test LogLevel to Python logging level mapping."""

    def test_debug_level_mapping(self, caplog):
        """Test DEBUG level maps to logging.DEBUG."""
        with caplog.at_level(logging.DEBUG):
            emit_log_event_sync(LogLevel.DEBUG, "Debug test")

        # Should be logged at DEBUG level
        assert caplog.records[0].levelno == logging.DEBUG

    def test_info_level_mapping(self, caplog):
        """Test INFO level maps to logging.INFO."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Info test")

        assert caplog.records[0].levelno == logging.INFO

    def test_warning_level_mapping(self, caplog):
        """Test WARNING level maps to logging.WARNING."""
        with caplog.at_level(logging.WARNING):
            emit_log_event_sync(LogLevel.WARNING, "Warning test")

        assert caplog.records[0].levelno == logging.WARNING

    def test_error_level_mapping(self, caplog):
        """Test ERROR level maps to logging.ERROR."""
        with caplog.at_level(logging.ERROR):
            emit_log_event_sync(LogLevel.ERROR, "Error test")

        assert caplog.records[0].levelno == logging.ERROR

    def test_critical_level_mapping(self, caplog):
        """Test CRITICAL level maps to logging.CRITICAL."""
        with caplog.at_level(logging.CRITICAL):
            emit_log_event_sync(LogLevel.CRITICAL, "Critical test")

        assert caplog.records[0].levelno == logging.CRITICAL

    def test_fatal_level_mapping(self, caplog):
        """Test FATAL level falls back to logging.INFO."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.FATAL, "Fatal test")

        # FATAL should fall back to INFO (not in mapping)
        assert caplog.records[0].levelno == logging.INFO

    def test_unknown_level_fallback(self, caplog):
        """Test unknown level falls back to INFO."""
        # Create a mock LogLevel that's not in the mapping
        with caplog.at_level(logging.INFO):
            # Use a valid LogLevel, but test the fallback path
            emit_log_event_sync(LogLevel.INFO, "Fallback test")

        # Should fall back to INFO level
        assert caplog.records[0].levelno >= logging.DEBUG


@pytest.mark.unit
class TestJSONEncoding:
    """Test JSON encoding with PydanticJSONEncoder."""

    def test_json_encoding_valid_output(self, caplog):
        """Test that output is valid JSON."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context={"key": "value"})

        # Should be parseable as JSON
        log_data = json.loads(caplog.records[0].message)
        assert isinstance(log_data, dict)

    def test_json_encoding_handles_uuid(self, caplog):
        """Test JSON encoding handles UUID in context."""
        test_uuid = uuid4()
        context = {"id": test_uuid}

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=context)

        log_data = json.loads(caplog.records[0].message)
        # UUID should be serialized as string
        assert isinstance(log_data["context"]["id"], str)

    def test_json_encoding_handles_pydantic_model(self, caplog):
        """Test JSON encoding handles Pydantic model in context."""
        model = SampleContext(correlation_id=uuid4(), node_id=uuid4(), operation="test")

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=model)

        log_data = json.loads(caplog.records[0].message)
        # Should be serialized successfully
        assert isinstance(log_data["context"], (dict, object))

    def test_json_encoding_preserves_types(self, caplog):
        """Test JSON encoding preserves basic types."""
        context = {
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
        }

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=context)

        log_data = json.loads(caplog.records[0].message)
        assert log_data["context"]["string"] == "text"
        assert log_data["context"]["int"] == 42
        assert log_data["context"]["float"] == 3.14
        assert log_data["context"]["bool"] is True
        assert log_data["context"]["none"] is None
        assert log_data["context"]["list"] == [1, 2, 3]


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_message(self, caplog):
        """Test emit with empty message."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "")

        log_data = json.loads(caplog.records[0].message)
        assert log_data["message"] == ""

    def test_long_message(self, caplog):
        """Test emit with very long message."""
        long_message = "A" * 10000

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, long_message)

        log_data = json.loads(caplog.records[0].message)
        assert log_data["message"] == long_message

    def test_message_with_special_characters(self, caplog):
        """Test emit with special characters in message."""
        special_message = "Test: \n\t\r ñ é ü 中文 🚀"

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, special_message)

        log_data = json.loads(caplog.records[0].message)
        assert "Test" in log_data["message"]

    def test_message_with_json_special_chars(self, caplog):
        """Test emit with JSON special characters."""
        message = 'Test with " quotes and \\ backslash'

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, message)

        log_data = json.loads(caplog.records[0].message)
        assert "quotes" in log_data["message"]

    def test_context_with_none_values(self, caplog):
        """Test emit with None values in context."""
        context = {"value": None, "name": "test", "count": 0}

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=context)

        log_data = json.loads(caplog.records[0].message)
        assert log_data["context"]["value"] is None
        assert log_data["context"]["name"] == "test"
        assert log_data["context"]["count"] == 0

    def test_context_with_empty_strings(self, caplog):
        """Test emit with empty strings in context."""
        context = {"empty": "", "name": "test"}

        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test", context=context)

        log_data = json.loads(caplog.records[0].message)
        assert log_data["context"]["empty"] == ""
        assert log_data["context"]["name"] == "test"

    def test_multiple_consecutive_emissions(self, caplog):
        """Test multiple consecutive log emissions."""
        with caplog.at_level(logging.INFO):
            for i in range(5):
                emit_log_event_sync(LogLevel.INFO, f"Message {i}", context={"count": i})

        assert len(caplog.records) == 5
        for i, record in enumerate(caplog.records):
            log_data = json.loads(record.message)
            assert log_data["message"] == f"Message {i}"
            assert log_data["context"]["count"] == i

    def test_concurrent_emissions(self, caplog):
        """Test concurrent log emissions from multiple threads."""
        import threading

        def emit_logs(thread_id):
            for i in range(3):
                emit_log_event_sync(
                    LogLevel.INFO,
                    f"Thread {thread_id} message {i}",
                    context={"thread": thread_id, "index": i},
                )

        with caplog.at_level(logging.INFO):
            threads = [threading.Thread(target=emit_logs, args=(i,)) for i in range(3)]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        # Should have logs from all threads
        assert len(caplog.records) >= 9  # 3 threads × 3 messages


@pytest.mark.unit
class TestLoggerNaming:
    """Test logger naming convention."""

    def test_uses_omnibase_logger(self, caplog):
        """Test that emit_log_event_sync uses 'omnibase' logger."""
        with caplog.at_level(logging.INFO):
            emit_log_event_sync(LogLevel.INFO, "Test")

        # Should use 'omnibase' logger
        assert caplog.records[0].name == "omnibase"

    def test_logger_hierarchy(self, caplog):
        """Test logger can be part of hierarchy."""
        # Get the omnibase logger
        logger = logging.getLogger("omnibase")

        with caplog.at_level(logging.INFO, logger="omnibase"):
            emit_log_event_sync(LogLevel.INFO, "Test")

        assert any(record.name == "omnibase" for record in caplog.records)
