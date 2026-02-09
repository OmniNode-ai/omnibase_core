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

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.core.model_envelope_metadata import ModelEnvelopeMetadata
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.security.model_security_context import ModelSecurityContext


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


@pytest.mark.unit
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
        assert isinstance(envelope.metadata, ModelEnvelopeMetadata)
        assert envelope.security_context is None
        assert envelope.priority == 5
        assert envelope.timeout_seconds is None
        assert envelope.retry_count == 0
        assert envelope.request_id is None
        assert envelope.trace_id is None
        assert envelope.span_id is None
        assert envelope.onex_version == ModelSemVer(major=1, minor=0, patch=0)
        assert envelope.envelope_version == ModelSemVer(major=2, minor=1, patch=0)

    def test_instantiation_with_all_fields(self):
        """Test envelope creation with all fields provided."""
        payload = SimplePayload(message="test", value=42)
        correlation_id = uuid4()
        request_id = uuid4()
        trace_id = uuid4()
        span_id = uuid4()
        user_id = uuid4()
        session_id = uuid4()
        security_context = ModelSecurityContext(
            user_id=user_id,
            username="test_user",
            roles=["admin"],
            session_id=session_id,
        )
        metadata = ModelEnvelopeMetadata(tags={"environment": "test", "version": "1.0"})

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
            event_type="core.node.completed",
            payload_type="SimplePayload",
            payload_schema_version=ModelSemVer(major=1, minor=0, patch=0),
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
        assert envelope.event_type == "core.node.completed"
        assert envelope.payload_type == "SimplePayload"
        assert envelope.payload_schema_version == ModelSemVer(major=1, minor=0, patch=0)

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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestModelEventEnvelopeMetadata:
    """Test metadata management functionality."""

    def test_with_metadata_replacement(self):
        """Test replacing metadata with new metadata."""
        payload = SimplePayload(message="test", value=42)
        initial_metadata = ModelEnvelopeMetadata(
            tags={"key1": "value1", "key2": "value2"}
        )
        envelope = ModelEventEnvelope(payload=payload, metadata=initial_metadata)

        new_metadata = ModelEnvelopeMetadata(tags={"key2": "updated", "key3": "value3"})
        new_envelope = envelope.with_metadata(new_metadata)

        # Original unchanged
        assert envelope.metadata == initial_metadata

        # New envelope has new metadata (full replacement, not merge)
        assert new_envelope.metadata == new_metadata
        assert new_envelope.metadata.tags == {"key2": "updated", "key3": "value3"}

    def test_get_metadata_value(self):
        """Test retrieving metadata values."""
        payload = SimplePayload(message="test", value=42)
        metadata = ModelEnvelopeMetadata(
            trace_id="trace-123",
            request_id="req-456",
            tags={"env": "production", "version": "1.0"},
        )
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)

        # Existing tags keys
        assert envelope.get_metadata_value("env") == "production"
        assert envelope.get_metadata_value("version") == "1.0"

        # Existing attributes
        assert envelope.get_metadata_value("trace_id") == "trace-123"
        assert envelope.get_metadata_value("request_id") == "req-456"

        # Non-existing key with default
        assert envelope.get_metadata_value("missing", "default") == "default"
        assert envelope.get_metadata_value("missing") is None


@pytest.mark.unit
class TestModelEventEnvelopeSecurity:
    """Test security context functionality."""

    def test_with_security_context(self):
        """Test creating envelope copy with updated security context."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        assert envelope.security_context is None

        security_context = ModelSecurityContext(
            username="admin",
            roles=["superuser"],
            permissions=["read", "write"],
        )
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
        security_context = ModelSecurityContext(username="test")
        envelope_with_sec = ModelEventEnvelope(
            payload=payload, security_context=security_context
        )
        assert envelope_with_sec.has_security_context() is True


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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
            payload=payload,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
        )

        assert envelope.priority == 5  # Default priority


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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

    def test_default_metadata(self):
        """Test envelope with default metadata (no args)."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        assert isinstance(envelope.metadata, ModelEnvelopeMetadata)
        assert envelope.metadata.trace_id is None
        assert envelope.metadata.request_id is None
        assert envelope.metadata.tags == {}
        assert envelope.get_metadata_value("missing") is None

    def test_empty_security_context(self):
        """Test envelope with default security context (None)."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload, security_context=None)

        assert envelope.security_context is None
        assert envelope.has_security_context() is False

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
        """Test envelope with large metadata tags."""
        payload = SimplePayload(message="test", value=42)
        large_tags = {f"key_{i}": f"value_{i}" for i in range(1000)}
        metadata = ModelEnvelopeMetadata(tags=large_tags)
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)

        assert len(envelope.metadata.tags) == 1000
        assert envelope.get_metadata_value("key_500") == "value_500"

    def test_unicode_in_fields(self):
        """Test envelope with unicode characters in string fields."""
        payload = SimplePayload(message="测试 тест 🚀", value=42)
        metadata = ModelEnvelopeMetadata(tags={"emoji": "🎉", "unicode": "你好"})
        envelope = ModelEventEnvelope(
            payload=payload,
            source_tool="源工具",
            target_tool="目标工具",
            metadata=metadata,
        )

        assert envelope.source_tool == "源工具"
        assert envelope.target_tool == "目标工具"
        assert envelope.metadata.tags["emoji"] == "🎉"

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


@pytest.mark.unit
class TestModelEventEnvelopeInferCategory:
    """Tests for message category inference."""

    def test_infer_category_default_is_event(self):
        """Default category should be EVENT for generic payloads."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)
        assert envelope.message_category == EnumMessageCategory.EVENT

    def test_infer_category_dict_payload_is_event(self):
        """Dict payload should default to EVENT category."""
        envelope = ModelEventEnvelope(payload={"key": "value"})
        assert envelope.infer_category() == EnumMessageCategory.EVENT

    def test_infer_category_string_payload_is_event(self):
        """String payload should default to EVENT category."""
        envelope = ModelEventEnvelope(payload="simple string")
        assert envelope.message_category == EnumMessageCategory.EVENT

    def test_infer_category_from_payload_type_command(self):
        """Payload with Command in name should infer COMMAND."""

        class ProcessOrderCommand(BaseModel):
            """Command payload model."""

            order_id: UUID

        payload = ProcessOrderCommand(order_id=uuid4())
        envelope = ModelEventEnvelope(payload=payload)
        assert envelope.infer_category() == EnumMessageCategory.COMMAND

    def test_infer_category_from_payload_type_command_suffix(self):
        """Payload ending with Command should infer COMMAND."""

        class UserCreateCommand(BaseModel):
            """Command model with suffix."""

            username: str

        payload = UserCreateCommand(username="test")
        envelope = ModelEventEnvelope(payload=payload)
        assert envelope.message_category == EnumMessageCategory.COMMAND

    def test_infer_category_from_payload_type_command_in_middle(self):
        """Payload with Command anywhere in name should infer COMMAND."""

        class CommandProcessor(BaseModel):
            """Model with Command in middle."""

            data: str

        payload = CommandProcessor(data="test")
        envelope = ModelEventEnvelope(payload=payload)
        assert envelope.infer_category() == EnumMessageCategory.COMMAND

    def test_infer_category_from_payload_type_intent(self):
        """Payload with Intent in name should infer INTENT."""

        class CreateUserIntent(BaseModel):
            """Intent payload model."""

            username: str
            email: str

        payload = CreateUserIntent(username="test", email="test@example.com")
        envelope = ModelEventEnvelope(payload=payload)
        assert envelope.infer_category() == EnumMessageCategory.INTENT

    def test_infer_category_from_payload_type_intent_suffix(self):
        """Payload ending with Intent should infer INTENT."""

        class ProcessOrderIntent(BaseModel):
            """Intent model with suffix."""

            order_id: UUID

        payload = ProcessOrderIntent(order_id=uuid4())
        envelope = ModelEventEnvelope(payload=payload)
        assert envelope.message_category == EnumMessageCategory.INTENT

    def test_infer_category_from_payload_type_intent_in_middle(self):
        """Payload with Intent anywhere in name should infer INTENT."""

        class IntentHandler(BaseModel):
            """Model with Intent in middle."""

            action: str

        payload = IntentHandler(action="process")
        envelope = ModelEventEnvelope(payload=payload)
        assert envelope.infer_category() == EnumMessageCategory.INTENT

    def test_infer_category_from_metadata_tag_event(self):
        """Explicit EVENT category in metadata should take precedence."""

        # Even though payload has Command in name, metadata overrides
        class TestCommand(BaseModel):
            """Command-like payload."""

            data: str

        metadata = ModelEnvelopeMetadata(tags={"message_category": "event"})
        payload = TestCommand(data="test")
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)
        assert envelope.infer_category() == EnumMessageCategory.EVENT

    def test_infer_category_from_metadata_tag_command(self):
        """Explicit COMMAND category in metadata should take precedence."""
        payload = SimplePayload(message="test", value=42)
        metadata = ModelEnvelopeMetadata(tags={"message_category": "command"})
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)
        assert envelope.message_category == EnumMessageCategory.COMMAND

    def test_infer_category_from_metadata_tag_intent(self):
        """Explicit INTENT category in metadata should take precedence."""
        payload = SimplePayload(message="test", value=42)
        metadata = ModelEnvelopeMetadata(tags={"message_category": "intent"})
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)
        assert envelope.infer_category() == EnumMessageCategory.INTENT

    def test_infer_category_metadata_tag_case_insensitive(self):
        """Metadata category tag should be case-insensitive."""
        payload = SimplePayload(message="test", value=42)

        # Uppercase
        metadata_upper = ModelEnvelopeMetadata(tags={"message_category": "COMMAND"})
        envelope_upper = ModelEventEnvelope(payload=payload, metadata=metadata_upper)
        assert envelope_upper.infer_category() == EnumMessageCategory.COMMAND

        # Mixed case
        metadata_mixed = ModelEnvelopeMetadata(tags={"message_category": "Intent"})
        envelope_mixed = ModelEventEnvelope(payload=payload, metadata=metadata_mixed)
        assert envelope_mixed.message_category == EnumMessageCategory.INTENT

    def test_infer_category_metadata_takes_precedence_over_payload_type(self):
        """Metadata category should override payload type inference."""

        class SomeCommand(BaseModel):
            """Command-like payload."""

            value: int

        # Payload suggests COMMAND, but metadata says INTENT
        metadata = ModelEnvelopeMetadata(tags={"message_category": "intent"})
        payload = SomeCommand(value=42)
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)

        # Metadata should win
        assert envelope.infer_category() == EnumMessageCategory.INTENT

    def test_infer_category_invalid_metadata_tag_falls_back(self):
        """Invalid metadata category should fall back to payload inference."""

        class TestIntent(BaseModel):
            """Intent-like payload."""

            data: str

        # Invalid category value in metadata
        metadata = ModelEnvelopeMetadata(tags={"message_category": "invalid"})
        payload = TestIntent(data="test")
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)

        # Should fall back to payload type inference (INTENT from class name)
        assert envelope.infer_category() == EnumMessageCategory.INTENT

    def test_infer_category_empty_metadata_tags(self):
        """Empty metadata tags should use payload type inference."""
        payload = SimplePayload(message="test", value=42)
        metadata = ModelEnvelopeMetadata(tags={})
        envelope = ModelEventEnvelope(payload=payload, metadata=metadata)
        assert envelope.message_category == EnumMessageCategory.EVENT

    def test_message_category_property_returns_same_as_infer_category(self):
        """message_category property should return same as infer_category()."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        assert envelope.message_category == envelope.infer_category()

    def test_infer_category_with_onex_event_payload(self):
        """Test category inference with ModelOnexEvent payload."""
        node_id = uuid4()
        onex_event = ModelOnexEvent(event_type="core.node.start", node_id=node_id)
        envelope = ModelEventEnvelope(payload=onex_event)

        # ModelOnexEvent doesn't have Command/Intent in name, should be EVENT
        assert envelope.infer_category() == EnumMessageCategory.EVENT


@pytest.mark.unit
class TestModelEventEnvelopeEventTyping:
    """Tests for event_type, payload_type, and payload_schema_version fields."""

    def test_new_fields_default_to_none(self):
        """New fields should default to None for backwards compatibility."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        assert envelope.event_type is None
        assert envelope.payload_type is None
        assert envelope.payload_schema_version is None

    def test_event_type_set_explicitly(self):
        """event_type can be set as a dot-path routing key."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(
            payload=payload,
            event_type="intelligence.claude-hook-event",
        )

        assert envelope.event_type == "intelligence.claude-hook-event"

    def test_payload_type_set_explicitly(self):
        """payload_type can be set to a Pydantic model class name."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(
            payload=payload,
            payload_type="SimplePayload",
        )

        assert envelope.payload_type == "SimplePayload"

    def test_payload_schema_version_set_explicitly(self):
        """payload_schema_version can be set to a ModelSemVer instance."""
        payload = SimplePayload(message="test", value=42)
        schema_version = ModelSemVer(major=2, minor=1, patch=0)
        envelope = ModelEventEnvelope(
            payload=payload,
            payload_schema_version=schema_version,
        )

        assert envelope.payload_schema_version == schema_version
        assert envelope.payload_schema_version.major == 2
        assert envelope.payload_schema_version.minor == 1
        assert envelope.payload_schema_version.patch == 0

    def test_all_new_fields_together(self):
        """All three new fields can be set together."""
        payload = SimplePayload(message="test", value=42)
        schema_version = ModelSemVer(major=1, minor=3, patch=0)
        envelope = ModelEventEnvelope(
            payload=payload,
            event_type="core.node.start",
            payload_type="SimplePayload",
            payload_schema_version=schema_version,
        )

        assert envelope.event_type == "core.node.start"
        assert envelope.payload_type == "SimplePayload"
        assert envelope.payload_schema_version == schema_version

    def test_new_fields_serialize_correctly(self):
        """New fields should serialize and deserialize via model_dump/model_validate."""
        payload = SimplePayload(message="test", value=42)
        schema_version = ModelSemVer(major=1, minor=2, patch=3)
        envelope = ModelEventEnvelope(
            payload=payload,
            event_type="intelligence.analysis",
            payload_type="SimplePayload",
            payload_schema_version=schema_version,
        )

        data = envelope.model_dump()
        assert data["event_type"] == "intelligence.analysis"
        assert data["payload_type"] == "SimplePayload"
        assert data["payload_schema_version"]["major"] == 1
        assert data["payload_schema_version"]["minor"] == 2
        assert data["payload_schema_version"]["patch"] == 3

    def test_new_fields_json_round_trip(self):
        """New fields should survive JSON serialization round-trip."""
        payload = SimplePayload(message="test", value=42)
        schema_version = ModelSemVer(major=1, minor=0, patch=0)
        envelope = ModelEventEnvelope(
            payload=payload,
            event_type="test.event",
            payload_type="SimplePayload",
            payload_schema_version=schema_version,
        )

        json_str = envelope.model_dump_json()
        deserialized = ModelEventEnvelope[SimplePayload].model_validate_json(json_str)

        assert deserialized.event_type == "test.event"
        assert deserialized.payload_type == "SimplePayload"
        assert deserialized.payload_schema_version == schema_version

    def test_new_fields_none_json_round_trip(self):
        """None-valued new fields should survive JSON round-trip."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        json_str = envelope.model_dump_json()
        deserialized = ModelEventEnvelope[SimplePayload].model_validate_json(json_str)

        assert deserialized.event_type is None
        assert deserialized.payload_type is None
        assert deserialized.payload_schema_version is None

    def test_new_fields_in_to_dict_lazy(self):
        """New fields should appear in to_dict_lazy() output."""
        payload = SimplePayload(message="test", value=42)
        schema_version = ModelSemVer(major=2, minor=0, patch=1)
        envelope = ModelEventEnvelope(
            payload=payload,
            event_type="test.lazy",
            payload_type="SimplePayload",
            payload_schema_version=schema_version,
        )

        lazy_dict = envelope.to_dict_lazy()

        assert lazy_dict["event_type"] == "test.lazy"
        assert lazy_dict["payload_type"] == "SimplePayload"
        assert lazy_dict["payload_schema_version"] == str(schema_version)

    def test_new_fields_none_in_to_dict_lazy(self):
        """None-valued new fields should appear as None in to_dict_lazy()."""
        payload = SimplePayload(message="test", value=42)
        envelope = ModelEventEnvelope(payload=payload)

        lazy_dict = envelope.to_dict_lazy()

        assert lazy_dict["event_type"] is None
        assert lazy_dict["payload_type"] is None
        assert lazy_dict["payload_schema_version"] is None

    def test_new_fields_preserved_by_model_copy(self):
        """New fields should be preserved through model_copy operations."""
        payload = SimplePayload(message="test", value=42)
        schema_version = ModelSemVer(major=1, minor=0, patch=0)
        envelope = ModelEventEnvelope(
            payload=payload,
            event_type="test.copy",
            payload_type="SimplePayload",
            payload_schema_version=schema_version,
        )

        copied = envelope.with_priority(9)

        assert copied.event_type == "test.copy"
        assert copied.payload_type == "SimplePayload"
        assert copied.payload_schema_version == schema_version
        assert copied.priority == 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
