"""
Unit tests for ModelTraceData.

Tests trace data model with protocol implementations and validation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.cli.model_trace_data import ModelTraceData


class TestModelTraceDataBasics:
    """Test basic initialization and validation."""

    def test_minimal_initialization(self):
        """Test model with all required fields."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        assert trace.trace_id == trace_id
        assert trace.span_id == span_id
        assert trace.start_time == start_time
        assert trace.end_time == end_time
        assert trace.duration_ms == 100.0
        assert trace.parent_span_id is None
        assert trace.tags == {}
        assert trace.logs == []

    def test_full_initialization(self):
        """Test model with all fields specified."""
        trace_id = uuid4()
        span_id = uuid4()
        parent_span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=250)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=250.0,
            tags={"env": "test", "version": "1.0"},
            logs=["Started", "Processing", "Completed"],
        )

        assert trace.trace_id == trace_id
        assert trace.span_id == span_id
        assert trace.parent_span_id == parent_span_id
        assert trace.duration_ms == 250.0
        assert len(trace.tags) == 2
        assert len(trace.logs) == 3

    def test_missing_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTraceData()  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "trace_id" in error_str or "span_id" in error_str

    def test_uuid_types(self):
        """Test UUID field type validation."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        assert isinstance(trace.trace_id, UUID)
        assert isinstance(trace.span_id, UUID)


class TestModelTraceDataTimestamps:
    """Test timestamp handling."""

    def test_datetime_fields(self):
        """Test datetime field types."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        assert isinstance(trace.start_time, datetime)
        assert isinstance(trace.end_time, datetime)
        assert trace.end_time > trace.start_time

    def test_duration_calculation(self):
        """Test duration with various time ranges."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 1)  # 1 second later

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=1000.0,
        )

        assert trace.duration_ms == 1000.0

    def test_zero_duration(self):
        """Test with zero duration."""
        trace_id = uuid4()
        span_id = uuid4()
        now = datetime.now()

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=now,
            end_time=now,
            duration_ms=0.0,
        )

        assert trace.duration_ms == 0.0


class TestModelTraceDataTagsAndLogs:
    """Test tags and logs handling."""

    def test_empty_tags_and_logs(self):
        """Test with empty tags and logs."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
            tags={},
            logs=[],
        )

        assert trace.tags == {}
        assert trace.logs == []

    def test_multiple_tags(self):
        """Test with multiple tags."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        tags = {
            "environment": "production",
            "service": "api",
            "version": "2.0",
            "region": "us-east-1",
        }

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
            tags=tags,
        )

        assert len(trace.tags) == 4
        assert trace.tags["environment"] == "production"
        assert trace.tags["service"] == "api"

    def test_multiple_logs(self):
        """Test with multiple log entries."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        logs = [
            "Trace started",
            "Processing request",
            "Database query executed",
            "Response sent",
            "Trace completed",
        ]

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
            logs=logs,
        )

        assert len(trace.logs) == 5
        assert trace.logs[0] == "Trace started"
        assert trace.logs[-1] == "Trace completed"


class TestModelTraceDataProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serialization to dictionary."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
            tags={"env": "test"},
        )

        data = trace.serialize()

        assert isinstance(data, dict)
        assert "trace_id" in data
        assert "span_id" in data
        assert "tags" in data

    def test_get_name_default(self):
        """Test default name generation."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        name = trace.get_name()

        assert "ModelTraceData" in name
        assert "Unnamed" in name

    def test_set_name_no_field(self):
        """Test set_name when no name field exists."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        # Should not raise
        trace.set_name("test_trace")

        # Name still returns default
        assert "Unnamed" in trace.get_name()

    def test_validate_instance(self):
        """Test instance validation."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        result = trace.validate_instance()

        assert result is True


class TestModelTraceDataEdgeCases:
    """Test edge cases and boundary values."""

    def test_parent_span_with_parent(self):
        """Test trace with parent span."""
        trace_id = uuid4()
        span_id = uuid4()
        parent_span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        assert trace.parent_span_id == parent_span_id
        assert isinstance(trace.parent_span_id, UUID)

    def test_parent_span_none(self):
        """Test trace without parent span (root trace)."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        assert trace.parent_span_id is None

    def test_large_duration(self):
        """Test with very large duration."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=24)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=86400000.0,  # 24 hours in ms
        )

        assert trace.duration_ms == 86400000.0

    def test_fractional_duration(self):
        """Test with fractional millisecond duration."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(microseconds=500)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=0.5,
        )

        assert trace.duration_ms == 0.5

    def test_model_config_extra_ignore(self):
        """Test that extra fields are ignored."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
            unknown_field="value",  # type: ignore[call-arg]
        )

        assert trace.trace_id == trace_id
        assert not hasattr(trace, "unknown_field")

    def test_validate_assignment(self):
        """Test validate_assignment config."""
        trace_id = uuid4()
        span_id = uuid4()
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=100)

        trace = ModelTraceData(
            trace_id=trace_id,
            span_id=span_id,
            start_time=start_time,
            end_time=end_time,
            duration_ms=100.0,
        )

        # Should allow valid assignment
        trace.duration_ms = 200.0
        assert trace.duration_ms == 200.0

        new_end_time = start_time + timedelta(milliseconds=200)
        trace.end_time = new_end_time
        assert trace.end_time == new_end_time
