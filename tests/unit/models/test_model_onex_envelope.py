#!/usr/bin/env python3
"""
TDD Unit tests for ModelOnexEnvelope (OMN-224).

These tests are written BEFORE the implementation following TDD methodology.
Tests define the expected behavior of the new ModelOnexEnvelope model which
replaces ModelOnexEnvelopeV1 with enhanced fields for:
- Causation chain tracking (causation_id)
- Routing support (target_node, handler_type)
- Request/response pattern (is_response, success, error)
- Extended metadata support

Tests verify:
- Instantiation with required and optional fields
- Field renames (envelope_id, source_node, operation)
- New fields functionality
- JSON serialization/deserialization with custom encoders
- Request/response pattern
- Validation errors for invalid inputs
- Round-trip serialization

Related:
- OMN-224 - ModelOnexEnvelope refactoring
- PR #71 - Original source_node_id field
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Fixed Test Data - Deterministic values for reproducible tests
# =============================================================================

DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)
FIXED_ENVELOPE_ID = UUID("12345678-1234-5678-1234-567812345678")
FIXED_CORRELATION_ID = UUID("87654321-4321-8765-4321-876543218765")
FIXED_CAUSATION_ID = UUID("11111111-2222-3333-4444-555555555555")
FIXED_SOURCE_NODE_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
FIXED_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
FIXED_PAYLOAD: dict[str, Any] = {"key": "value", "count": 42}
FIXED_METADATA: dict[str, Any] = {"trace_id": "abc123", "request_id": "req-001"}


# =============================================================================
# Test Class: Instantiation
# =============================================================================


class TestModelOnexEnvelopeInstantiation:
    """Test ModelOnexEnvelope creation with required and optional fields."""

    def test_creation_with_required_fields_only(self) -> None:
        """Test envelope creation with only required fields."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OPERATION",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        # Verify required fields
        assert envelope.envelope_id == FIXED_ENVELOPE_ID
        assert envelope.envelope_version == DEFAULT_VERSION
        assert envelope.correlation_id == FIXED_CORRELATION_ID
        assert envelope.source_node == "test_service"
        assert envelope.operation == "TEST_OPERATION"
        assert envelope.payload == FIXED_PAYLOAD
        assert envelope.timestamp == FIXED_TIMESTAMP

        # Verify optional fields have correct defaults
        assert envelope.causation_id is None
        assert envelope.source_node_id is None
        assert envelope.target_node is None
        assert envelope.handler_type is None
        assert envelope.metadata == {}
        assert envelope.is_response is False
        assert envelope.success is None
        assert envelope.error is None

    def test_creation_with_all_fields(self) -> None:
        """Test envelope creation with all fields specified."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            causation_id=FIXED_CAUSATION_ID,
            source_node="source_service",
            source_node_id=FIXED_SOURCE_NODE_ID,
            target_node="target_service",
            handler_type=EnumHandlerType.HTTP,
            operation="FULL_OPERATION",
            payload=FIXED_PAYLOAD,
            metadata=FIXED_METADATA,
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=True,
            error=None,
        )

        # Verify all fields
        assert envelope.envelope_id == FIXED_ENVELOPE_ID
        assert envelope.envelope_version == DEFAULT_VERSION
        assert envelope.correlation_id == FIXED_CORRELATION_ID
        assert envelope.causation_id == FIXED_CAUSATION_ID
        assert envelope.source_node == "source_service"
        assert envelope.source_node_id == FIXED_SOURCE_NODE_ID
        assert envelope.target_node == "target_service"
        assert envelope.handler_type == EnumHandlerType.HTTP
        assert envelope.operation == "FULL_OPERATION"
        assert envelope.payload == FIXED_PAYLOAD
        assert envelope.metadata == FIXED_METADATA
        assert envelope.timestamp == FIXED_TIMESTAMP
        assert envelope.is_response is True
        assert envelope.success is True
        assert envelope.error is None

    def test_creation_with_uuid_auto_generation(self) -> None:
        """Test that UUIDs are properly handled (no auto-generation for required fields)."""
        # envelope_id is required, so we must provide it
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=DEFAULT_VERSION,
            correlation_id=uuid4(),
            source_node="test_service",
            operation="TEST_OP",
            payload={},
            timestamp=datetime.now(UTC),
        )

        # Verify UUIDs are valid
        assert isinstance(envelope.envelope_id, UUID)
        assert isinstance(envelope.correlation_id, UUID)

    def test_creation_with_empty_payload(self) -> None:
        """Test envelope creation with empty payload."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="EMPTY_PAYLOAD_OP",
            payload={},
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.payload == {}

    def test_creation_with_complex_payload(self) -> None:
        """Test envelope creation with complex nested payload."""
        complex_payload: dict[str, Any] = {
            "level1": {
                "level2": {
                    "array": [1, 2, 3],
                    "nested": {"deep": "value"},
                },
            },
            "numbers": [1.5, 2.5, 3.5],
            "boolean": True,
            "null_value": None,
        }

        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="COMPLEX_PAYLOAD_OP",
            payload=complex_payload,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.payload == complex_payload
        assert envelope.payload["level1"]["level2"]["nested"]["deep"] == "value"


# =============================================================================
# Test Class: Field Renames
# =============================================================================


class TestModelOnexEnvelopeFieldRenames:
    """Test renamed fields work correctly (envelope_id, source_node, operation)."""

    def test_envelope_id_renamed_from_event_id(self) -> None:
        """Test envelope_id field (renamed from event_id in V1)."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        # envelope_id should work
        assert envelope.envelope_id == FIXED_ENVELOPE_ID

        # event_id should NOT exist as attribute
        assert not hasattr(envelope, "event_id")

    def test_source_node_renamed_from_source_service(self) -> None:
        """Test source_node field (renamed from source_service in V1)."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="my_source_node",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        # source_node should work
        assert envelope.source_node == "my_source_node"

        # source_service should NOT exist as attribute
        assert not hasattr(envelope, "source_service")

    def test_operation_renamed_from_event_type(self) -> None:
        """Test operation field (renamed from event_type in V1)."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="MY_OPERATION",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        # operation should work
        assert envelope.operation == "MY_OPERATION"

        # event_type should NOT exist as attribute
        assert not hasattr(envelope, "event_type")

    def test_all_renamed_fields_together(self) -> None:
        """Test all renamed fields work correctly together."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="renamed_source",
            operation="RENAMED_OPERATION",
            payload={"renamed": True},
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.envelope_id == FIXED_ENVELOPE_ID
        assert envelope.source_node == "renamed_source"
        assert envelope.operation == "RENAMED_OPERATION"


# =============================================================================
# Test Class: New Fields
# =============================================================================


class TestModelOnexEnvelopeNewFields:
    """Test all new fields (causation_id, target_node, handler_type, metadata, is_response, success, error)."""

    def test_causation_id_field(self) -> None:
        """Test causation_id field for causation chain tracking."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            causation_id=FIXED_CAUSATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.causation_id == FIXED_CAUSATION_ID

    def test_causation_id_optional(self) -> None:
        """Test causation_id is truly optional."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.causation_id is None

    def test_target_node_field(self) -> None:
        """Test target_node field for routing."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="source_service",
            target_node="target_service",
            operation="ROUTED_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.target_node == "target_service"

    def test_target_node_optional(self) -> None:
        """Test target_node is truly optional."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.target_node is None

    def test_handler_type_with_http(self) -> None:
        """Test handler_type field with HTTP type."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            handler_type=EnumHandlerType.HTTP,
            operation="HTTP_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.handler_type == EnumHandlerType.HTTP

    def test_handler_type_with_kafka(self) -> None:
        """Test handler_type field with KAFKA type."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            handler_type=EnumHandlerType.KAFKA,
            operation="KAFKA_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.handler_type == EnumHandlerType.KAFKA

    def test_handler_type_with_database(self) -> None:
        """Test handler_type field with DATABASE type."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            handler_type=EnumHandlerType.DATABASE,
            operation="DB_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.handler_type == EnumHandlerType.DATABASE

    def test_handler_type_optional(self) -> None:
        """Test handler_type is truly optional."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.handler_type is None

    def test_metadata_field_with_data(self) -> None:
        """Test metadata field with data."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            metadata=FIXED_METADATA,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.metadata == FIXED_METADATA
        assert envelope.metadata["trace_id"] == "abc123"

    def test_metadata_defaults_to_empty_dict(self) -> None:
        """Test metadata defaults to empty dict."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.metadata == {}
        assert isinstance(envelope.metadata, dict)

    def test_is_response_field_true(self) -> None:
        """Test is_response field set to True."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="RESPONSE_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
        )

        assert envelope.is_response is True

    def test_is_response_defaults_to_false(self) -> None:
        """Test is_response defaults to False."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.is_response is False

    def test_success_field_true(self) -> None:
        """Test success field set to True."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="SUCCESS_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=True,
        )

        assert envelope.success is True

    def test_success_field_false(self) -> None:
        """Test success field set to False."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="FAILED_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=False,
        )

        assert envelope.success is False

    def test_success_optional(self) -> None:
        """Test success is truly optional (None)."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.success is None

    def test_error_field_with_message(self) -> None:
        """Test error field with error message."""
        error_message = "Something went wrong: validation failed"

        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="ERROR_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=False,
            error=error_message,
        )

        assert envelope.error == error_message

    def test_error_optional(self) -> None:
        """Test error is truly optional (None)."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope.error is None


# =============================================================================
# Test Class: Serialization
# =============================================================================


class TestModelOnexEnvelopeSerialization:
    """Test JSON serialization with custom encoders for UUID/datetime."""

    def test_model_dump_basic(self) -> None:
        """Test basic model_dump serialization."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        data = envelope.model_dump()

        assert data["envelope_id"] == FIXED_ENVELOPE_ID
        assert data["correlation_id"] == FIXED_CORRELATION_ID
        assert data["source_node"] == "test_service"
        assert data["operation"] == "TEST_OP"
        assert data["payload"] == FIXED_PAYLOAD

    def test_model_dump_with_all_fields(self) -> None:
        """Test model_dump with all fields populated."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            causation_id=FIXED_CAUSATION_ID,
            source_node="source_service",
            source_node_id=FIXED_SOURCE_NODE_ID,
            target_node="target_service",
            handler_type=EnumHandlerType.HTTP,
            operation="FULL_OP",
            payload=FIXED_PAYLOAD,
            metadata=FIXED_METADATA,
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=True,
            error=None,
        )

        data = envelope.model_dump()

        assert data["causation_id"] == FIXED_CAUSATION_ID
        assert data["target_node"] == "target_service"
        assert data["handler_type"] == EnumHandlerType.HTTP
        assert data["metadata"] == FIXED_METADATA
        assert data["is_response"] is True
        assert data["success"] is True
        assert data["error"] is None

    def test_model_dump_json_basic(self) -> None:
        """Test model_dump_json produces valid JSON string."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        json_str = envelope.model_dump_json()

        # Should be a valid JSON string
        assert isinstance(json_str, str)
        assert "envelope_id" in json_str
        assert "correlation_id" in json_str
        assert str(FIXED_ENVELOPE_ID) in json_str

    def test_model_dump_json_uuid_serialization(self) -> None:
        """Test UUID fields are properly serialized in JSON."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            causation_id=FIXED_CAUSATION_ID,
            source_node="test_service",
            source_node_id=FIXED_SOURCE_NODE_ID,
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        json_str = envelope.model_dump_json()

        # All UUIDs should be serialized as strings
        assert str(FIXED_ENVELOPE_ID) in json_str
        assert str(FIXED_CORRELATION_ID) in json_str
        assert str(FIXED_CAUSATION_ID) in json_str
        assert str(FIXED_SOURCE_NODE_ID) in json_str

    def test_model_dump_json_datetime_serialization(self) -> None:
        """Test datetime fields are properly serialized in JSON."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        json_str = envelope.model_dump_json()

        # Datetime should be serialized in ISO format
        assert "2024-01-01" in json_str
        assert "12:00:00" in json_str

    def test_model_dump_json_handler_type_serialization(self) -> None:
        """Test EnumHandlerType is properly serialized in JSON."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            handler_type=EnumHandlerType.KAFKA,
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        json_str = envelope.model_dump_json()

        # Handler type should be serialized
        assert "kafka" in json_str.lower() or "KAFKA" in json_str

    def test_serialization_excludes_none_optional_fields(self) -> None:
        """Test serialization behavior with None optional fields."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        data = envelope.model_dump()

        # Optional fields should either be absent or have None value
        # This behavior depends on model configuration
        if "causation_id" in data:
            assert data["causation_id"] is None
        if "target_node" in data:
            assert data["target_node"] is None
        if "handler_type" in data:
            assert data["handler_type"] is None


# =============================================================================
# Test Class: Deserialization
# =============================================================================


class TestModelOnexEnvelopeDeserialization:
    """Test JSON to model roundtrip deserialization."""

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        data: dict[str, Any] = {
            "envelope_id": str(FIXED_ENVELOPE_ID),
            "envelope_version": {"major": 1, "minor": 0, "patch": 0},
            "correlation_id": str(FIXED_CORRELATION_ID),
            "source_node": "test_service",
            "operation": "TEST_OP",
            "payload": FIXED_PAYLOAD,
            "timestamp": FIXED_TIMESTAMP.isoformat(),
        }

        envelope = ModelOnexEnvelope.model_validate(data)

        assert envelope.envelope_id == FIXED_ENVELOPE_ID
        assert envelope.correlation_id == FIXED_CORRELATION_ID
        assert envelope.source_node == "test_service"
        assert envelope.operation == "TEST_OP"

    def test_model_validate_json(self) -> None:
        """Test model_validate_json from JSON string."""
        original = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        json_str = original.model_dump_json()
        deserialized = ModelOnexEnvelope.model_validate_json(json_str)

        assert deserialized.envelope_id == FIXED_ENVELOPE_ID
        assert deserialized.correlation_id == FIXED_CORRELATION_ID

    def test_round_trip_basic(self) -> None:
        """Test complete round-trip serialization/deserialization."""
        original = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="round_trip_service",
            operation="ROUND_TRIP_OP",
            payload={"round": "trip"},
            timestamp=FIXED_TIMESTAMP,
        )

        json_str = original.model_dump_json()
        restored = ModelOnexEnvelope.model_validate_json(json_str)

        assert restored.envelope_id == original.envelope_id
        assert restored.correlation_id == original.correlation_id
        assert restored.source_node == original.source_node
        assert restored.operation == original.operation
        assert restored.payload == original.payload

    def test_round_trip_with_all_fields(self) -> None:
        """Test round-trip with all fields populated."""
        original = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            causation_id=FIXED_CAUSATION_ID,
            source_node="full_service",
            source_node_id=FIXED_SOURCE_NODE_ID,
            target_node="target_service",
            handler_type=EnumHandlerType.DATABASE,
            operation="FULL_OP",
            payload=FIXED_PAYLOAD,
            metadata=FIXED_METADATA,
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=False,
            error="Test error message",
        )

        json_str = original.model_dump_json()
        restored = ModelOnexEnvelope.model_validate_json(json_str)

        assert restored.envelope_id == original.envelope_id
        assert restored.correlation_id == original.correlation_id
        assert restored.causation_id == original.causation_id
        assert restored.source_node == original.source_node
        assert restored.source_node_id == original.source_node_id
        assert restored.target_node == original.target_node
        assert restored.handler_type == original.handler_type
        assert restored.operation == original.operation
        assert restored.payload == original.payload
        assert restored.metadata == original.metadata
        assert restored.is_response == original.is_response
        assert restored.success == original.success
        assert restored.error == original.error

    def test_round_trip_with_none_optional_fields(self) -> None:
        """Test round-trip preserves None for optional fields."""
        original = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
            # All optional fields left as default/None
        )

        json_str = original.model_dump_json()
        restored = ModelOnexEnvelope.model_validate_json(json_str)

        assert restored.causation_id is None
        assert restored.source_node_id is None
        assert restored.target_node is None
        assert restored.handler_type is None
        assert restored.success is None
        assert restored.error is None


# =============================================================================
# Test Class: Request/Response Pattern
# =============================================================================


class TestModelOnexEnvelopeRequestResponse:
    """Test request/response pattern (is_response, success, error)."""

    def test_request_envelope(self) -> None:
        """Test creating a request envelope."""
        request = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="client_service",
            target_node="server_service",
            operation="GET_DATA",
            payload={"query": "test"},
            timestamp=FIXED_TIMESTAMP,
            is_response=False,
        )

        assert request.is_response is False
        assert request.success is None
        assert request.error is None
        assert request.target_node == "server_service"

    def test_successful_response_envelope(self) -> None:
        """Test creating a successful response envelope."""
        response = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,  # Same as request
            causation_id=FIXED_ENVELOPE_ID,  # Points to request envelope_id
            source_node="server_service",
            target_node="client_service",
            operation="GET_DATA_RESPONSE",
            payload={"data": "result"},
            timestamp=datetime.now(UTC),
            is_response=True,
            success=True,
        )

        assert response.is_response is True
        assert response.success is True
        assert response.error is None
        assert response.causation_id == FIXED_ENVELOPE_ID

    def test_failed_response_envelope(self) -> None:
        """Test creating a failed response envelope with error."""
        response = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            causation_id=FIXED_ENVELOPE_ID,
            source_node="server_service",
            target_node="client_service",
            operation="GET_DATA_RESPONSE",
            payload={},
            timestamp=datetime.now(UTC),
            is_response=True,
            success=False,
            error="Resource not found: ID 12345",
        )

        assert response.is_response is True
        assert response.success is False
        assert response.error == "Resource not found: ID 12345"

    def test_request_response_correlation(self) -> None:
        """Test correlation between request and response."""
        # Create request
        request = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="client",
            target_node="server",
            operation="REQUEST_OP",
            payload={"request": True},
            timestamp=FIXED_TIMESTAMP,
            is_response=False,
        )

        # Create response with matching correlation
        response = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=DEFAULT_VERSION,
            correlation_id=request.correlation_id,  # Same correlation
            causation_id=request.envelope_id,  # Causation points to request
            source_node="server",
            target_node="client",
            operation="RESPONSE_OP",
            payload={"response": True},
            timestamp=datetime.now(UTC),
            is_response=True,
            success=True,
        )

        # Verify correlation chain
        assert response.correlation_id == request.correlation_id
        assert response.causation_id == request.envelope_id

    def test_error_without_success_false(self) -> None:
        """Test error field can be set independently of success."""
        # Edge case: error set but success not explicitly False
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload={},
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            error="Warning message",  # Error without success=False
        )

        assert envelope.error == "Warning message"
        assert envelope.success is None  # Not explicitly set


# =============================================================================
# Test Class: Validation
# =============================================================================


class TestModelOnexEnvelopeValidation:
    """Test validation errors for invalid inputs."""

    def test_missing_required_envelope_id(self) -> None:
        """Test validation error when envelope_id is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexEnvelope(
                # envelope_id missing
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("envelope_id",) for e in errors)

    def test_missing_required_envelope_version(self) -> None:
        """Test validation error when envelope_version is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                # envelope_version missing
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("envelope_version",) for e in errors)

    def test_missing_required_correlation_id(self) -> None:
        """Test validation error when correlation_id is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                # correlation_id missing
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("correlation_id",) for e in errors)

    def test_missing_required_source_node(self) -> None:
        """Test validation error when source_node is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                # source_node missing
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_node",) for e in errors)

    def test_missing_required_operation(self) -> None:
        """Test validation error when operation is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                # operation missing
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("operation",) for e in errors)

    def test_missing_required_payload(self) -> None:
        """Test validation error when payload is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                # payload missing
                timestamp=FIXED_TIMESTAMP,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("payload",) for e in errors)

    def test_missing_required_timestamp(self) -> None:
        """Test validation error when timestamp is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                # timestamp missing
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("timestamp",) for e in errors)

    def test_invalid_uuid_envelope_id(self) -> None:
        """Test validation error for invalid UUID envelope_id."""
        with pytest.raises(ValidationError):
            ModelOnexEnvelope(
                envelope_id="not-a-valid-uuid",  # type: ignore[arg-type]
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

    def test_invalid_uuid_correlation_id(self) -> None:
        """Test validation error for invalid UUID correlation_id."""
        with pytest.raises(ValidationError):
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id="invalid-uuid",  # type: ignore[arg-type]
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

    def test_invalid_handler_type(self) -> None:
        """Test validation error for invalid handler_type."""
        with pytest.raises(ValidationError):
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                handler_type="invalid_type",  # type: ignore[arg-type]
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
            )

    def test_invalid_timestamp_type(self) -> None:
        """Test validation error for invalid timestamp type."""
        with pytest.raises(ValidationError):
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp="not-a-datetime",  # type: ignore[arg-type]
            )

    def test_invalid_payload_type(self) -> None:
        """Test validation error for invalid payload type (not dict)."""
        with pytest.raises(ValidationError):
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload="not-a-dict",  # type: ignore[arg-type]
                timestamp=FIXED_TIMESTAMP,
            )

    def test_invalid_is_response_type(self) -> None:
        """Test validation error for invalid is_response type."""
        with pytest.raises(ValidationError):
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload=FIXED_PAYLOAD,
                timestamp=FIXED_TIMESTAMP,
                is_response="not-a-bool",  # type: ignore[arg-type]
            )


# =============================================================================
# Test Class: String Representation
# =============================================================================


class TestModelOnexEnvelopeStringRepresentation:
    """Test __str__ and __repr__ methods."""

    def test_str_representation(self) -> None:
        """Test __str__ produces readable output."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OPERATION",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        str_repr = str(envelope)

        # Should contain key identifying information
        assert "ModelOnexEnvelope" in str_repr or "TEST_OPERATION" in str_repr
        assert "test_service" in str_repr or str(FIXED_CORRELATION_ID)[:8] in str_repr

    def test_str_representation_with_response(self) -> None:
        """Test __str__ for response envelope."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="RESPONSE_OP",
            payload={},
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=True,
        )

        str_repr = str(envelope)

        # String representation should exist
        assert isinstance(str_repr, str)
        assert len(str_repr) > 0


# =============================================================================
# Test Class: Equality and Hashing
# =============================================================================


class TestModelOnexEnvelopeEquality:
    """Test equality comparison behavior."""

    def test_same_envelope_equal(self) -> None:
        """Test two envelopes with same data are equal."""
        envelope1 = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        envelope2 = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope1.envelope_id == envelope2.envelope_id
        assert envelope1.correlation_id == envelope2.correlation_id
        assert envelope1.source_node == envelope2.source_node
        assert envelope1.operation == envelope2.operation
        assert envelope1.payload == envelope2.payload

    def test_different_envelope_ids_not_equal(self) -> None:
        """Test envelopes with different envelope_ids are not equal."""
        envelope1 = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        different_id = UUID("99999999-9999-9999-9999-999999999999")
        envelope2 = ModelOnexEnvelope(
            envelope_id=different_id,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload=FIXED_PAYLOAD,
            timestamp=FIXED_TIMESTAMP,
        )

        assert envelope1.envelope_id != envelope2.envelope_id


# =============================================================================
# Test Class: Bulk Operations
# =============================================================================


class TestModelOnexEnvelopeBulkOperations:
    """Test bulk envelope creation and processing."""

    def test_bulk_creation(self) -> None:
        """Test bulk envelope creation works correctly."""
        count = 100

        envelopes = [
            ModelOnexEnvelope(
                envelope_id=UUID(f"00000000-0000-0000-0000-{i:012d}"),
                envelope_version=DEFAULT_VERSION,
                correlation_id=UUID(f"11111111-1111-1111-1111-{i:012d}"),
                source_node=f"service_{i}",
                operation=f"OP_{i}",
                payload={"index": i},
                timestamp=FIXED_TIMESTAMP,
            )
            for i in range(count)
        ]

        assert len(envelopes) == count

        for i, envelope in enumerate(envelopes):
            expected_envelope_id = UUID(f"00000000-0000-0000-0000-{i:012d}")
            assert envelope.envelope_id == expected_envelope_id
            assert envelope.payload["index"] == i

    def test_bulk_serialization(self) -> None:
        """Test bulk serialization preserves all data."""
        count = 50

        envelopes = [
            ModelOnexEnvelope(
                envelope_id=UUID(f"00000000-0000-0000-0000-{i:012d}"),
                envelope_version=DEFAULT_VERSION,
                correlation_id=UUID(f"11111111-1111-1111-1111-{i:012d}"),
                source_node=f"service_{i}",
                operation=f"OP_{i}",
                payload={"index": i},
                timestamp=FIXED_TIMESTAMP,
            )
            for i in range(count)
        ]

        # Serialize all
        serialized = [env.model_dump_json() for env in envelopes]

        assert len(serialized) == count

        # Verify each serialized version contains expected data
        for i, json_str in enumerate(serialized):
            expected_id = f"00000000-0000-0000-0000-{i:012d}"
            assert expected_id in json_str

    def test_bulk_round_trip(self) -> None:
        """Test bulk round-trip serialization/deserialization."""
        count = 25

        original_envelopes = [
            ModelOnexEnvelope(
                envelope_id=UUID(f"00000000-0000-0000-0000-{i:012d}"),
                envelope_version=DEFAULT_VERSION,
                correlation_id=UUID(f"11111111-1111-1111-1111-{i:012d}"),
                source_node=f"service_{i}",
                operation=f"OP_{i}",
                payload={"index": i, "data": f"value_{i}"},
                timestamp=FIXED_TIMESTAMP,
            )
            for i in range(count)
        ]

        # Round trip
        restored_envelopes = [
            ModelOnexEnvelope.model_validate_json(env.model_dump_json())
            for env in original_envelopes
        ]

        assert len(restored_envelopes) == count

        for i, (original, restored) in enumerate(
            zip(original_envelopes, restored_envelopes)
        ):
            assert restored.envelope_id == original.envelope_id
            assert restored.correlation_id == original.correlation_id
            assert restored.payload == original.payload
