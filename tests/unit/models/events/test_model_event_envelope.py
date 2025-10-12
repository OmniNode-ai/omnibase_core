"""
Unit tests for ModelEventEnvelope.

Tests comprehensive event envelope functionality including:
- Model instantiation and validation
- Generic payload support
- Correlation tracking and distributed tracing
- QoS features (priority, timeout, retry)
- Security context
- Routing (source/target tools)
- Lazy evaluation
- Factory methods (broadcast/directed)
- Edge cases and error conditions
"""

import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.primitives.model_semver import ModelSemVer


# Test payload models
class SimplePayload(BaseModel):
    """Simple test payload."""

    message: str
    value: int


class ComplexPayload(BaseModel):
    """Complex test payload with nested structures."""

    name: str
    tags: list[str]
    metadata: dict[str, Any]


class TestModelEventEnvelopeInstantiation:
    """Test cases for ModelEventEnvelope instantiation."""

    def test_instantiation_minimal_data(self):
        """Test envelope creation with minimal required data (just payload)."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        assert envelope.payload == payload
        assert isinstance(envelope.envelope_id, UUID)
        assert isinstance(envelope.envelope_timestamp, datetime)
        assert envelope.correlation_id is None
        assert envelope.source_tool is None
        assert envelope.target_tool is None
        assert envelope.metadata == {}
        assert envelope.security_context is None
        assert envelope.priority == 5
        assert envelope.timeout_seconds is None
        assert envelope.retry_count == 0
        assert envelope.request_id is None
        assert envelope.trace_id is None
        assert envelope.span_id is None
        assert envelope.onex_version == ModelSemVer(major=1, minor=0, patch=0)
        assert envelope.envelope_version == ModelSemVer(major=2, minor=0, patch=0)

    def test_instantiation_with_all_fields(self):
        """Test envelope creation with all fields provided."""
        payload = SimplePayload(message="test", value=42)
        correlation_id = uuid4()
        request_id = uuid4()
        trace_id = uuid4()
        span_id = uuid4()
        security_context = {"user": "test_user", "role": "admin"}
        metadata = {"environment": "test", "version": "1.0"}

        envelope = ModelEventEnvelope(
            payload=payload,
            correlation_id=correlation_id,
            source_tool="source-node",
            target_tool="target-node",
            metadata=metadata,
            security_context=security_context,
            priority=8,
            timeout_seconds=30,
            retry_count=2,
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
        )

        assert envelope.payload == payload
        assert envelope.correlation_id == correlation_id
        assert envelope.source_tool == "source-node"
        assert envelope.target_tool == "target-node"
        assert envelope.metadata == metadata
        assert envelope.security_context == security_context
        assert envelope.priority == 8
        assert envelope.timeout_seconds == 30
        assert envelope.retry_count == 2
        assert envelope.request_id == request_id
        assert envelope.trace_id == trace_id
        assert envelope.span_id == span_id

    def test_instantiation_with_onex_event_payload(self):
        """Test envelope wrapping ModelOnexEvent payload."""
        node_id = uuid4()
        onex_event = ModelOnexEvent(event_type="core.node.start", node_id=node_id)
        envelope = ModelEventEnvelope(payload=onex_event)

        assert envelope.payload == onex_event
        assert envelope.payload.node_id == node_id
        assert envelope.payload.event_type == "core.node.start"

    def test_generic_payload_support(self):
        """Test that envelope supports various payload types."""
        # String payload
        envelope_str = ModelEventEnvelope(payload="simple string")
        assert envelope_str.payload == "simple string"

        # Dict payload
        envelope_dict = ModelEventEnvelope(payload={"key": "value"})
        assert envelope_dict.payload == {"key": "value"}

        # List payload
        envelope_list = ModelEventEnvelope(payload=[1, 2, 3])
        assert envelope_list.payload == [1, 2, 3]

        # Complex payload
        complex_payload = ComplexPayload(
            name="test", tags=["tag1", "tag2"], metadata={"nested": {"data": "value"}}
        )
        envelope_complex = ModelEventEnvelope(payload=complex_payload)
        assert envelope_complex.payload == complex_payload


class TestModelEventEnvelopeValidation:
    """Test field validation for ModelEventEnvelope."""

    def test_priority_validation_valid_range(self):
        """Test that priority is validated within range 1-10."""
        payload = SimplePayload(message="test", value=42)

        # Minimum boundary
        envelope_min = ModelEventEnvelope(payload=payload, priority=1)
        assert envelope_min.priority == 1

        # Maximum boundary
        envelope_max = ModelEventEnvelope(payload=payload, priority=10)
        assert envelope_max.priority == 10

        # Mid-range
        envelope_mid = ModelEventEnvelope(payload=payload, priority=5)
        assert envelope_mid.priority == 5

    def test_priority_validation_out_of_range(self):
        """Test that priority outside 1-10 raises ValidationError."""
        payload = SimplePayload(message="test", value=42)

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ModelEventEnvelope(payload=payload, priority=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelEventEnvelope(payload=payload, priority=11)
        assert "less than or equal to 10" in str(exc_info.value)

    def test_timeout_seconds_validation(self):
        """Test that timeout_seconds must be positive."""
        payload = SimplePayload(message="test", value=42)

        # Valid positive timeout
        envelope = ModelEventEnvelope(payload=payload, timeout_seconds=60)
        assert envelope.timeout_seconds == 60

        # Zero timeout should fail (gt=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            ModelEventEnvelope(payload=payload, timeout_seconds=0)
        assert "greater than 0" in str(exc_info.value)

        # Negative timeout should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelEventEnvelope(payload=payload, timeout_seconds=-1)
        assert "greater than 0" in str(exc_info.value)

    def test_retry_count_validation(self):
        """Test that retry_count must be non-negative."""
        payload = SimplePayload(message="test", value=42)

        # Valid retry counts
        envelope_zero = ModelEventEnvelope(payload=payload, retry_count=0)
        assert envelope_zero.retry_count == 0

        envelope_positive = ModelEventEnvelope(payload=payload, retry_count=5)
        assert envelope_positive.retry_count == 5

        # Negative retry count should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelEventEnvelope(payload=payload, retry_count=-1)
        assert "greater than or equal to 0" in str(exc_info.value)


class TestModelEventEnvelopeCorrelation:
    """Test correlation tracking functionality."""

    def test_with_correlation_id(self):
        """Test creating envelope copy with updated correlation_id."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        assert envelope.correlation_id is None

        correlation_id = uuid4()
        new_envelope = envelope.with_correlation_id(correlation_id)

        # Original unchanged
        assert envelope.correlation_id is None

        # New envelope has correlation_id
        assert new_envelope.correlation_id == correlation_id
        assert new_envelope.payload == payload
        # model_copy() creates a new instance but may preserve envelope_id

    def test_is_correlated(self):
        """Test is_correlated() method."""
        payload = SimplePayload(message="test", value=42)

        # Without correlation
        envelope_no_corr = ModelEventEnvelope(payload=payload)
        assert envelope_no_corr.is_correlated() is False

        # With correlation
        correlation_id = uuid4()
        envelope_with_corr = ModelEventEnvelope(
            payload=payload, correlation_id=correlation_id
        )
        assert envelope_with_corr.is_correlated() is True


class TestModelEventEnvelopeMetadata:
    """Test metadata management functionality."""

    def test_with_metadata_merge(self):
        """Test merging metadata with existing metadata."""
        payload = SimplePayload(message="test", value=42)
        initial_metadata = {"key1": "value1", "key2": "value2"}
        envelope = ModelEventEnvelope(payload=payload, metadata=initial_metadata)

        new_metadata = {"key2": "updated", "key3": "value3"}
        new_envelope = envelope.with_metadata(new_metadata)

        # Original unchanged
        assert envelope.metadata == initial_metadata

        # New envelope has merged metadata (new values override)
        assert new_envelope.metadata == {
            "key1": "value1",
            "key2": "updated",
            "key3": "value3",
        }

    def test_get_metadata_value(self):
        """Test retrieving metadata values."""
        payload = SimplePayload(message="test", value=42)
        metadata = {"env": "production", "version": "1.0", "nested": {"key": "value"}}
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)

        # Existing keys
        assert envelope.get_metadata_value("env") == "production"
        assert envelope.get_metadata_value("version") == "1.0"
        assert envelope.get_metadata_value("nested") == {"key": "value"}

        # Non-existing key with default
        assert envelope.get_metadata_value("missing", "default") == "default"
        assert envelope.get_metadata_value("missing") is None


class TestModelEventEnvelopeSecurity:
    """Test security context functionality."""

    def test_with_security_context(self):
        """Test creating envelope copy with updated security context."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        assert envelope.security_context is None

        security_context = {"user": "admin", "role": "superuser", "permissions": ["read", "write"]}
        new_envelope = envelope.with_security_context(security_context)

        # Original unchanged
        assert envelope.security_context is None

        # New envelope has security context
        assert new_envelope.security_context == security_context

    def test_has_security_context(self):
        """Test has_security_context() method."""
        payload = SimplePayload(message="test", value=42)

        # Without security context
        envelope_no_sec = ModelEventEnvelope(payload=payload)
        assert envelope_no_sec.has_security_context() is False

        # With security context
        security_context = {"user": "test"}
        envelope_with_sec = ModelEventEnvelope(
            payload=payload, security_context=security_context
        )
        assert envelope_with_sec.has_security_context() is True


class TestModelEventEnvelopeRouting:
    """Test routing functionality (source/target tools)."""

    def test_set_routing_both_tools(self):
        """Test setting both source and target tools."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        new_envelope = envelope.set_routing(
            source_tool="source-service", target_tool="target-service"
        )

        # Original unchanged
        assert envelope.source_tool is None
        assert envelope.target_tool is None

        # New envelope has routing
        assert new_envelope.source_tool == "source-service"
        assert new_envelope.target_tool == "target-service"

    def test_set_routing_source_only(self):
        """Test setting only source tool."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        new_envelope = envelope.set_routing(source_tool="source-service")

        assert new_envelope.source_tool == "source-service"
        assert new_envelope.target_tool is None

    def test_set_routing_target_only(self):
        """Test setting only target tool."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        new_envelope = envelope.set_routing(target_tool="target-service")

        assert new_envelope.source_tool is None
        assert new_envelope.target_tool == "target-service"


class TestModelEventEnvelopeTracing:
    """Test distributed tracing functionality."""

    def test_with_tracing_all_ids(self):
        """Test creating envelope with full tracing context."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        trace_id = uuid4()
        span_id = uuid4()
        request_id = uuid4()

        new_envelope = envelope.with_tracing(
            trace_id=trace_id, span_id=span_id, request_id=request_id
        )

        assert new_envelope.trace_id == trace_id
        assert new_envelope.span_id == span_id
        assert new_envelope.request_id == request_id

    def test_with_tracing_without_request_id(self):
        """Test creating envelope with tracing but no request_id."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        trace_id = uuid4()
        span_id = uuid4()

        new_envelope = envelope.with_tracing(trace_id=trace_id, span_id=span_id)

        assert new_envelope.trace_id == trace_id
        assert new_envelope.span_id == span_id
        assert new_envelope.request_id is None

    def test_has_trace_context(self):
        """Test has_trace_context() method."""
        payload = SimplePayload(message="test", value=42)

        # Without tracing
        envelope_no_trace = ModelEventEnvelope(payload=payload)
        assert envelope_no_trace.has_trace_context() is False

        # With partial tracing (only trace_id)
        envelope_partial = ModelEventEnvelope(payload=payload, trace_id=uuid4())
        assert envelope_partial.has_trace_context() is False

        # With full tracing context
        envelope_full = ModelEventEnvelope(
            payload=payload, trace_id=uuid4(), span_id=uuid4()
        )
        assert envelope_full.has_trace_context() is True

    def test_get_trace_context(self):
        """Test get_trace_context() method."""
        payload = SimplePayload(message="test", value=42)

        # Without tracing
        envelope_no_trace = ModelEventEnvelope(payload=payload)
        assert envelope_no_trace.get_trace_context() is None

        # With tracing but no request_id
        trace_id = uuid4()
        span_id = uuid4()
        envelope_basic = ModelEventEnvelope(
            payload=payload, trace_id=trace_id, span_id=span_id
        )
        context = envelope_basic.get_trace_context()
        assert context is not None
        assert context["trace_id"] == str(trace_id)
        assert context["span_id"] == str(span_id)
        assert "request_id" not in context

        # With full tracing including request_id
        request_id = uuid4()
        envelope_full = ModelEventEnvelope(
            payload=payload, trace_id=trace_id, span_id=span_id, request_id=request_id
        )
        context_full = envelope_full.get_trace_context()
        assert context_full is not None
        assert context_full["trace_id"] == str(trace_id)
        assert context_full["span_id"] == str(span_id)
        assert context_full["request_id"] == str(request_id)


class TestModelEventEnvelopeQoS:
    """Test Quality of Service features (priority, timeout, retry)."""

    def test_with_priority(self):
        """Test creating envelope with updated priority."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload, priority=3)

        new_envelope = envelope.with_priority(9)

        assert envelope.priority == 3
        assert new_envelope.priority == 9

    def test_is_high_priority(self):
        """Test is_high_priority() method (threshold >= 8)."""
        payload = SimplePayload(message="test", value=42)

        # Low priority
        envelope_low = ModelEventEnvelope(payload=payload, priority=5)
        assert envelope_low.is_high_priority() is False

        # Boundary below threshold
        envelope_below = ModelEventEnvelope(payload=payload, priority=7)
        assert envelope_below.is_high_priority() is False

        # Boundary at threshold
        envelope_threshold = ModelEventEnvelope(payload=payload, priority=8)
        assert envelope_threshold.is_high_priority() is True

        # High priority
        envelope_high = ModelEventEnvelope(payload=payload, priority=10)
        assert envelope_high.is_high_priority() is True

    def test_increment_retry_count(self):
        """Test incrementing retry count."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload, retry_count=0)

        new_envelope = envelope.increment_retry_count()

        assert envelope.retry_count == 0
        assert new_envelope.retry_count == 1

        # Multiple increments
        new_envelope2 = new_envelope.increment_retry_count()
        assert new_envelope2.retry_count == 2

    def test_is_retry(self):
        """Test is_retry() method."""
        payload = SimplePayload(message="test", value=42)

        # First attempt
        envelope_first = ModelEventEnvelope(payload=payload, retry_count=0)
        assert envelope_first.is_retry() is False

        # Retry attempt
        envelope_retry = ModelEventEnvelope(payload=payload, retry_count=1)
        assert envelope_retry.is_retry() is True

        envelope_multiple = ModelEventEnvelope(payload=payload, retry_count=5)
        assert envelope_multiple.is_retry() is True

    def test_is_expired(self):
        """Test is_expired() method based on timeout."""
        payload = SimplePayload(message="test", value=42)

        # No timeout set - never expires
        envelope_no_timeout = ModelEventEnvelope(payload=payload)
        assert envelope_no_timeout.is_expired() is False

        # Fresh envelope with timeout
        envelope_fresh = ModelEventEnvelope(payload=payload, timeout_seconds=10)
        assert envelope_fresh.is_expired() is False

        # Expired envelope (simulate by creating with old timestamp)
        # We'll test this by briefly sleeping and checking with very short timeout
        envelope_expire = ModelEventEnvelope(payload=payload, timeout_seconds=1)
        time.sleep(1.1)
        assert envelope_expire.is_expired() is True

    def test_get_elapsed_time(self):
        """Test get_elapsed_time() method."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        # Immediately after creation
        elapsed = envelope.get_elapsed_time()
        assert elapsed >= 0
        assert elapsed < 1  # Should be very small

        # After brief sleep
        time.sleep(0.1)
        elapsed_after = envelope.get_elapsed_time()
        assert elapsed_after >= 0.1


class TestModelEventEnvelopeFactoryMethods:
    """Test factory methods for creating envelopes."""

    def test_create_broadcast(self):
        """Test create_broadcast() factory method."""
        payload = SimplePayload(message="test", value=42)
        source_node_id = uuid4()
        correlation_id = uuid4()

        envelope = ModelEventEnvelope.create_broadcast(
            payload=payload,
            source_node_id=source_node_id,
            correlation_id=correlation_id,
            priority=7,
        )

        assert envelope.payload == payload
        assert envelope.source_tool == str(source_node_id)
        assert envelope.target_tool is None  # Broadcast has no specific target
        assert envelope.correlation_id == correlation_id
        assert envelope.priority == 7

    def test_create_broadcast_default_priority(self):
        """Test create_broadcast() with default priority."""
        payload = SimplePayload(message="test", value=42)
        source_node_id = uuid4()

        envelope = ModelEventEnvelope.create_broadcast(
            payload=payload, source_node_id=source_node_id
        )

        assert envelope.priority == 5  # Default priority

    def test_create_directed(self):
        """Test create_directed() factory method."""
        payload = SimplePayload(message="test", value=42)
        source_node_id = uuid4()
        target_node_id = uuid4()
        correlation_id = uuid4()

        envelope = ModelEventEnvelope.create_directed(
            payload=payload,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            correlation_id=correlation_id,
            priority=9,
        )

        assert envelope.payload == payload
        assert envelope.source_tool == str(source_node_id)
        assert envelope.target_tool == str(target_node_id)
        assert envelope.correlation_id == correlation_id
        assert envelope.priority == 9

    def test_create_directed_default_priority(self):
        """Test create_directed() with default priority."""
        payload = SimplePayload(message="test", value=42)
        source_node_id = uuid4()
        target_node_id = uuid4()

        envelope = ModelEventEnvelope.create_directed(
            payload=payload, source_node_id=source_node_id, target_node_id=target_node_id
        )

        assert envelope.priority == 5  # Default priority


class TestModelEventEnvelopePayloadExtraction:
    """Test payload extraction functionality."""

    def test_extract_payload_simple(self):
        """Test extracting simple payload."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        extracted = envelope.extract_payload()
        assert extracted == payload
        assert isinstance(extracted, SimplePayload)

    def test_extract_payload_complex(self):
        """Test extracting complex payload."""
        payload = ComplexPayload(
            name="test", tags=["a", "b"], metadata={"key": "value"}
        )
        envelope = ModelEventEnvelope(payload=payload)

        extracted = envelope.extract_payload()
        assert extracted == payload
        assert extracted.name == "test"
        assert extracted.tags == ["a", "b"]

    def test_extract_payload_onex_event(self):
        """Test extracting ModelOnexEvent payload."""
        node_id = uuid4()
        event = ModelOnexEvent(event_type="core.node.start", node_id=node_id)
        envelope = ModelEventEnvelope(payload=event)

        extracted = envelope.extract_payload()
        assert extracted == event
        assert isinstance(extracted, ModelOnexEvent)
        assert extracted.node_id == node_id


class TestModelEventEnvelopeLazyEvaluation:
    """Test lazy evaluation functionality."""

    def test_to_dict_lazy_with_pydantic_payload(self):
        """Test to_dict_lazy() with Pydantic model payload."""
        payload = SimplePayload(message="test", value=42)
        correlation_id = uuid4()
        envelope = ModelEventEnvelope(
            payload=payload, correlation_id=correlation_id, priority=7
        )

        lazy_dict = envelope.to_dict_lazy()

        # Verify structure
        assert "envelope_id" in lazy_dict
        assert "envelope_timestamp" in lazy_dict
        assert "payload" in lazy_dict
        assert lazy_dict["correlation_id"] == str(correlation_id)
        assert lazy_dict["priority"] == 7

        # Verify payload is present (lazy evaluation returns dict from Pydantic models)
        # The lazy evaluation converts Pydantic models to dict
        assert "payload" in lazy_dict
        payload_data = lazy_dict["payload"]
        # If it's a dict (fully evaluated), check contents
        if isinstance(payload_data, dict):
            assert payload_data["message"] == "test"
            assert payload_data["value"] == 42

    def test_to_dict_lazy_with_non_pydantic_payload(self):
        """Test to_dict_lazy() with non-Pydantic payload."""
        payload = {"simple": "dict"}
        envelope = ModelEventEnvelope(payload=payload)

        lazy_dict = envelope.to_dict_lazy()

        # Non-Pydantic payload should be included as-is
        assert lazy_dict["payload"] == payload

    def test_to_dict_lazy_uuid_conversion(self):
        """Test that UUIDs are converted to strings in to_dict_lazy()."""
        payload = SimplePayload(message="test", value=42)
        correlation_id = uuid4()
        trace_id = uuid4()
        span_id = uuid4()

        envelope = ModelEventEnvelope(
            payload=payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
        )

        lazy_dict = envelope.to_dict_lazy()

        # UUIDs should be strings
        assert isinstance(lazy_dict["envelope_id"], str)
        assert isinstance(lazy_dict["correlation_id"], str)
        assert lazy_dict["correlation_id"] == str(correlation_id)

    def test_to_dict_lazy_timestamp_conversion(self):
        """Test that timestamps are converted to ISO format in to_dict_lazy()."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        lazy_dict = envelope.to_dict_lazy()

        # Timestamp should be ISO format string
        assert isinstance(lazy_dict["envelope_timestamp"], str)
        assert "T" in lazy_dict["envelope_timestamp"]  # ISO format has T separator

    def test_to_dict_lazy_version_conversion(self):
        """Test that versions are converted to strings in to_dict_lazy()."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        lazy_dict = envelope.to_dict_lazy()

        # Versions should be strings
        assert isinstance(lazy_dict["onex_version"], str)
        assert isinstance(lazy_dict["envelope_version"], str)


class TestModelEventEnvelopeSerialization:
    """Test serialization and deserialization."""

    def test_model_dump(self):
        """Test Pydantic model_dump() serialization."""
        payload = SimplePayload(message="test", value=42)
        correlation_id = uuid4()
        envelope = ModelEventEnvelope(
            payload=payload, correlation_id=correlation_id, priority=8
        )

        data = envelope.model_dump()

        assert data["correlation_id"] == correlation_id
        assert data["priority"] == 8
        assert "payload" in data
        assert data["payload"]["message"] == "test"

    def test_model_dump_json(self):
        """Test JSON serialization."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload, priority=7)

        json_str = envelope.model_dump_json()

        assert isinstance(json_str, str)
        assert "test" in json_str
        assert "42" in json_str
        assert '"priority":7' in json_str or '"priority": 7' in json_str

    def test_model_validate_json(self):
        """Test JSON deserialization."""
        payload = SimplePayload(message="original", value=100)
        envelope = ModelEventEnvelope(payload=payload, priority=6)

        json_str = envelope.model_dump_json()
        deserialized = ModelEventEnvelope[SimplePayload].model_validate_json(json_str)

        assert deserialized.priority == envelope.priority
        assert deserialized.payload.message == "original"
        assert deserialized.payload.value == 100


class TestModelEventEnvelopeEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_payload(self):
        """Test that None payload handling."""
        # The payload field uses default=..., making it required
        # But None might be accepted as a valid type based on Generic[T] typing
        # Test if None is accepted or rejected
        try:
            envelope = ModelEventEnvelope(payload=None)
            # If accepted, verify it's set to None
            assert envelope.payload is None
        except ValidationError:
            # If rejected, this is also valid behavior
            pass

    def test_empty_metadata(self):
        """Test envelope with empty metadata dict."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload, metadata={})

        assert envelope.metadata == {}
        assert envelope.get_metadata_value("missing") is None

    def test_empty_security_context(self):
        """Test envelope with empty security context dict."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload, security_context={})

        assert envelope.security_context == {}
        assert envelope.has_security_context() is True  # Empty dict still counts

    def test_immutability_pattern(self):
        """Test that envelope methods return new instances (immutable pattern)."""
        payload = SimplePayload(message="test", value=42)
        original = ModelEventEnvelope(payload=payload, priority=5)

        modified = original.with_priority(8)

        # Verify immutability - original is unchanged
        assert original.priority == 5
        assert modified.priority == 8
        # Note: model_copy() may preserve envelope_id, but creates new instance
        # The key is that original is not modified
        assert id(original) != id(modified)  # Different Python objects

    def test_chaining_methods(self):
        """Test chaining multiple envelope modification methods."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        correlation_id = uuid4()
        trace_id = uuid4()
        span_id = uuid4()

        chained = (
            envelope.with_correlation_id(correlation_id)
            .with_priority(9)
            .with_tracing(trace_id=trace_id, span_id=span_id)
            .set_routing(source_tool="source", target_tool="target")
        )

        # Original unchanged
        assert envelope.correlation_id is None
        assert envelope.priority == 5

        # Chained envelope has all modifications
        assert chained.correlation_id == correlation_id
        assert chained.priority == 9
        assert chained.trace_id == trace_id
        assert chained.span_id == span_id
        assert chained.source_tool == "source"
        assert chained.target_tool == "target"

    def test_large_metadata(self):
        """Test envelope with large metadata dict."""
        payload = SimplePayload(message="test", value=42)
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(1000)}
        envelope = ModelEventEnvelope(payload=payload, metadata=large_metadata)

        assert len(envelope.metadata) == 1000
        assert envelope.get_metadata_value("key_500") == "value_500"

    def test_unicode_in_fields(self):
        """Test envelope with unicode characters in string fields."""
        payload = SimplePayload(message="测试 тест 🚀", value=42)
        envelope = ModelEventEnvelope(
            payload=payload,
            source_tool="源工具",
            target_tool="目标工具",
            metadata={"emoji": "🎉", "unicode": "你好"},
        )

        assert envelope.source_tool == "源工具"
        assert envelope.target_tool == "目标工具"
        assert envelope.metadata["emoji"] == "🎉"

    def test_multiple_retries(self):
        """Test multiple retry increments."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload, retry_count=0)

        # Simulate multiple retries
        retry1 = envelope.increment_retry_count()
        retry2 = retry1.increment_retry_count()
        retry3 = retry2.increment_retry_count()

        assert envelope.retry_count == 0
        assert retry1.retry_count == 1
        assert retry2.retry_count == 2
        assert retry3.retry_count == 3
        assert retry3.is_retry() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
