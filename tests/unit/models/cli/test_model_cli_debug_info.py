"""
Test suite for ModelCliDebugInfo.

Tests the clean, strongly-typed replacement for dict[str, Any] in CLI debug info.
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.omnibase_core.models.cli.model_cli_debug_info import ModelCliDebugInfo


class TestModelCliDebugInfo:
    """Test cases for ModelCliDebugInfo."""

    def test_initialization_empty(self):
        """Test empty initialization with defaults."""
        debug_info = ModelCliDebugInfo()

        assert debug_info.debug_level == "info"
        assert isinstance(debug_info.timestamp, datetime)
        assert debug_info.debug_messages == []
        assert debug_info.timing_info == {}
        assert debug_info.memory_info == {}
        assert debug_info.system_info == {}
        assert debug_info.error_details == {}
        assert debug_info.stack_traces == []
        assert debug_info.verbose_mode is False
        assert debug_info.trace_mode is False
        assert debug_info.custom_debug_fields == {}

    def test_initialization_with_values(self):
        """Test initialization with specific values."""
        timestamp = datetime.now(UTC)
        debug_info = ModelCliDebugInfo(
            debug_level="debug",
            timestamp=timestamp,
            debug_messages=["Initial message"],
            timing_info={"operation1": 123.45},
            memory_info={"heap": 1024},
            verbose_mode=True,
            trace_mode=True,
        )

        assert debug_info.debug_level == "debug"
        assert debug_info.timestamp == timestamp
        assert debug_info.debug_messages == ["Initial message"]
        assert debug_info.timing_info == {"operation1": 123.45}
        assert debug_info.memory_info == {"heap": 1024}
        assert debug_info.verbose_mode is True
        assert debug_info.trace_mode is True

    def test_timestamp_default_utc(self):
        """Test that default timestamp is in UTC."""
        debug_info = ModelCliDebugInfo()

        # Should be recent and in UTC
        now = datetime.now(UTC)
        time_diff = abs((now - debug_info.timestamp).total_seconds())
        assert time_diff < 1.0  # Should be within 1 second
        assert debug_info.timestamp.tzinfo == UTC

    def test_add_debug_message(self):
        """Test adding debug messages."""
        debug_info = ModelCliDebugInfo()

        # Start with empty messages
        assert debug_info.debug_messages == []

        # Add messages
        debug_info.add_debug_message("First message")
        debug_info.add_debug_message("Second message")

        assert len(debug_info.debug_messages) == 2
        assert debug_info.debug_messages[0] == "First message"
        assert debug_info.debug_messages[1] == "Second message"

    def test_add_timing_info(self):
        """Test adding timing information."""
        debug_info = ModelCliDebugInfo()

        # Start with empty timing info
        assert debug_info.timing_info == {}

        # Add timing data
        debug_info.add_timing_info("database_query", 125.7)
        debug_info.add_timing_info("api_call", 89.3)

        assert debug_info.timing_info["database_query"] == 125.7
        assert debug_info.timing_info["api_call"] == 89.3
        assert len(debug_info.timing_info) == 2

    def test_add_memory_info(self):
        """Test adding memory information."""
        debug_info = ModelCliDebugInfo()

        # Start with empty memory info
        assert debug_info.memory_info == {}

        # Add memory data
        debug_info.add_memory_info("heap_usage", 2048000)
        debug_info.add_memory_info("stack_usage", 512000)

        assert debug_info.memory_info["heap_usage"] == 2048000
        assert debug_info.memory_info["stack_usage"] == 512000
        assert len(debug_info.memory_info) == 2

    def test_add_system_info(self):
        """Test adding system information."""
        debug_info = ModelCliDebugInfo()

        # Start with empty system info
        assert debug_info.system_info == {}

        # Add system data
        debug_info.add_system_info("os", "Linux")
        debug_info.add_system_info("python_version", "3.11.0")
        debug_info.add_system_info("cpu_cores", "8")

        assert debug_info.system_info["os"] == "Linux"
        assert debug_info.system_info["python_version"] == "3.11.0"
        assert debug_info.system_info["cpu_cores"] == "8"
        assert len(debug_info.system_info) == 3

    def test_add_error_detail(self):
        """Test adding error details."""
        debug_info = ModelCliDebugInfo()

        # Start with empty error details
        assert debug_info.error_details == {}

        # Add error data
        debug_info.add_error_detail("validation", "Required field missing")
        debug_info.add_error_detail("network", "Connection timeout")

        assert debug_info.error_details["validation"] == "Required field missing"
        assert debug_info.error_details["network"] == "Connection timeout"
        assert len(debug_info.error_details) == 2

    def test_add_stack_trace(self):
        """Test adding stack traces."""
        debug_info = ModelCliDebugInfo()

        # Start with empty stack traces
        assert debug_info.stack_traces == []

        # Add stack traces
        trace1 = "File '/app/main.py', line 42, in main\\n    raise Exception('Test')"
        trace2 = "File '/app/utils.py', line 15, in helper\\n    return process_data()"

        debug_info.add_stack_trace(trace1)
        debug_info.add_stack_trace(trace2)

        assert len(debug_info.stack_traces) == 2
        assert debug_info.stack_traces[0] == trace1
        assert debug_info.stack_traces[1] == trace2

    def test_custom_field_operations(self):
        """Test custom debug field operations."""
        debug_info = ModelCliDebugInfo()

        # Start with empty custom fields
        assert debug_info.custom_debug_fields == {}

        # Set various types of custom fields
        debug_info.set_custom_field("string_field", "test_value")
        debug_info.set_custom_field("int_field", 42)
        debug_info.set_custom_field("float_field", 3.14)
        debug_info.set_custom_field("bool_field", True)

        # Verify values
        assert debug_info.custom_debug_fields["string_field"] == "test_value"
        assert debug_info.custom_debug_fields["int_field"] == 42
        assert debug_info.custom_debug_fields["float_field"] == 3.14
        assert debug_info.custom_debug_fields["bool_field"] is True

        # Test get_custom_field
        assert debug_info.get_custom_field("string_field") == "test_value"
        assert debug_info.get_custom_field("int_field") == 42
        assert debug_info.get_custom_field("nonexistent") is None
        assert debug_info.get_custom_field("nonexistent", "default") == "default"

    def test_complex_debug_scenario(self):
        """Test complex debugging scenario with all features."""
        debug_info = ModelCliDebugInfo(
            debug_level="debug", verbose_mode=True, trace_mode=True
        )

        # Add debug messages
        debug_info.add_debug_message("Starting complex operation")
        debug_info.add_debug_message("Validating input parameters")
        debug_info.add_debug_message("Processing data batch")

        # Add timing information for different operations
        debug_info.add_timing_info("input_validation", 5.2)
        debug_info.add_timing_info("data_processing", 156.8)
        debug_info.add_timing_info("output_generation", 23.4)

        # Add memory information
        debug_info.add_memory_info("initial_memory", 512000)
        debug_info.add_memory_info("peak_memory", 2048000)
        debug_info.add_memory_info("final_memory", 768000)

        # Add system information
        debug_info.add_system_info("hostname", "worker-node-01")
        debug_info.add_system_info("process_id", "12345")

        # Add error details
        debug_info.add_error_detail("warning", "Deprecated API used")

        # Add stack trace
        debug_info.add_stack_trace("Traceback info for warning")

        # Add custom fields
        debug_info.set_custom_field("batch_size", 1000)
        debug_info.set_custom_field("worker_id", "worker-01")

        # Verify all data is present
        assert len(debug_info.debug_messages) == 3
        assert len(debug_info.timing_info) == 3
        assert len(debug_info.memory_info) == 3
        assert len(debug_info.system_info) == 2
        assert len(debug_info.error_details) == 1
        assert len(debug_info.stack_traces) == 1
        assert len(debug_info.custom_debug_fields) == 2

    def test_debug_modes(self):
        """Test different debug modes."""
        # Test info level (default)
        info_debug = ModelCliDebugInfo()
        assert info_debug.debug_level == "info"
        assert info_debug.verbose_mode is False
        assert info_debug.trace_mode is False

        # Test debug level with verbose
        debug_verbose = ModelCliDebugInfo(debug_level="debug", verbose_mode=True)
        assert debug_verbose.debug_level == "debug"
        assert debug_verbose.verbose_mode is True

        # Test trace mode
        trace_debug = ModelCliDebugInfo(
            debug_level="debug", verbose_mode=True, trace_mode=True
        )
        assert trace_debug.trace_mode is True

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""
        timestamp = datetime.now(UTC)
        debug_info = ModelCliDebugInfo(
            debug_level="debug",
            timestamp=timestamp,
            debug_messages=["Test message"],
            timing_info={"test_op": 100.0},
            memory_info={"heap": 1024},
            verbose_mode=True,
        )

        # Test model_dump
        data = debug_info.model_dump()

        assert data["debug_level"] == "debug"
        assert data["debug_messages"] == ["Test message"]
        assert data["timing_info"] == {"test_op": 100.0}
        assert data["memory_info"] == {"heap": 1024}
        assert data["verbose_mode"] is True

    def test_pydantic_deserialization(self):
        """Test Pydantic model deserialization."""
        timestamp = datetime.now(UTC)
        data = {
            "debug_level": "error",
            "timestamp": timestamp.isoformat(),
            "debug_messages": ["Error occurred"],
            "timing_info": {"error_handling": 50.0},
            "memory_info": {"error_memory": 256},
            "system_info": {"error_context": "test"},
            "error_details": {"main_error": "Test error"},
            "stack_traces": ["Test stack trace"],
            "verbose_mode": True,
            "trace_mode": False,
            "custom_debug_fields": {"error_code": 500},
        }

        debug_info = ModelCliDebugInfo.model_validate(data)

        assert debug_info.debug_level == "error"
        assert debug_info.debug_messages == ["Error occurred"]
        assert debug_info.timing_info == {"error_handling": 50.0}
        assert debug_info.memory_info == {"error_memory": 256}
        assert debug_info.system_info == {"error_context": "test"}
        assert debug_info.error_details == {"main_error": "Test error"}
        assert debug_info.stack_traces == ["Test stack trace"]
        assert debug_info.verbose_mode is True
        assert debug_info.trace_mode is False
        assert debug_info.custom_debug_fields == {"error_code": 500}

    def test_model_round_trip(self):
        """Test serialization -> deserialization round trip."""
        original = ModelCliDebugInfo(
            debug_level="warn",
            debug_messages=["Warning message"],
            timing_info={"warn_operation": 75.5},
            memory_info={"warn_memory": 512},
            verbose_mode=True,
            trace_mode=False,
        )

        # Add some data via methods
        original.add_system_info("warning_source", "validation")
        original.set_custom_field("warning_level", 2)

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back to model
        restored = ModelCliDebugInfo.model_validate(data)

        # Should be equal
        assert restored.debug_level == original.debug_level
        assert restored.debug_messages == original.debug_messages
        assert restored.timing_info == original.timing_info
        assert restored.memory_info == original.memory_info
        assert restored.system_info == original.system_info
        assert restored.verbose_mode == original.verbose_mode
        assert restored.trace_mode == original.trace_mode
        assert restored.custom_debug_fields == original.custom_debug_fields

    def test_edge_cases_empty_collections(self):
        """Test edge cases with empty collections."""
        debug_info = ModelCliDebugInfo(
            debug_messages=[],
            timing_info={},
            memory_info={},
            system_info={},
            error_details={},
            stack_traces=[],
            custom_debug_fields={},
        )

        # All collections should be empty
        assert debug_info.debug_messages == []
        assert debug_info.timing_info == {}
        assert debug_info.memory_info == {}
        assert debug_info.system_info == {}
        assert debug_info.error_details == {}
        assert debug_info.stack_traces == []
        assert debug_info.custom_debug_fields == {}

    def test_method_side_effects(self):
        """Test that methods properly modify the model state."""
        debug_info = ModelCliDebugInfo()

        # Verify initial state
        assert len(debug_info.debug_messages) == 0
        assert len(debug_info.timing_info) == 0

        # Add data via methods
        debug_info.add_debug_message("Side effect test")
        debug_info.add_timing_info("side_effect_op", 42.0)

        # Verify state changed
        assert len(debug_info.debug_messages) == 1
        assert len(debug_info.timing_info) == 1
        assert debug_info.debug_messages[0] == "Side effect test"
        assert debug_info.timing_info["side_effect_op"] == 42.0

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        debug_info = ModelCliDebugInfo(
            debug_level="info",
            debug_messages=["JSON test"],
            timing_info={"json_op": 15.5},
            verbose_mode=False,
        )

        # Test JSON serialization
        json_str = debug_info.model_dump_json()
        assert isinstance(json_str, str)
        assert '"debug_level":"info"' in json_str
        assert '"debug_messages":["JSON test"]' in json_str

        # Test JSON deserialization
        restored = ModelCliDebugInfo.model_validate_json(json_str)
        assert restored.debug_level == "info"
        assert restored.debug_messages == ["JSON test"]
        assert restored.timing_info == {"json_op": 15.5}

    def test_custom_field_type_validation(self):
        """Test that custom fields accept the correct types."""
        debug_info = ModelCliDebugInfo()

        # Test all supported types
        debug_info.set_custom_field("str_val", "string")
        debug_info.set_custom_field("int_val", 42)
        debug_info.set_custom_field("bool_val", True)
        debug_info.set_custom_field("float_val", 3.14159)

        assert debug_info.custom_debug_fields["str_val"] == "string"
        assert debug_info.custom_debug_fields["int_val"] == 42
        assert debug_info.custom_debug_fields["bool_val"] is True
        assert debug_info.custom_debug_fields["float_val"] == 3.14159

    def test_timestamp_handling(self):
        """Test timestamp handling and timezone awareness."""
        # Test with explicit UTC timestamp
        utc_time = datetime.now(UTC)
        debug_info = ModelCliDebugInfo(timestamp=utc_time)
        assert debug_info.timestamp == utc_time
        assert debug_info.timestamp.tzinfo == UTC

        # Test default timestamp is recent
        debug_info_default = ModelCliDebugInfo()
        time_diff = abs(
            (datetime.now(UTC) - debug_info_default.timestamp).total_seconds()
        )
        assert time_diff < 2.0  # Should be within 2 seconds
