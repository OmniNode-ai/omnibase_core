"""
TDD Unit tests for ModelOnexEnvelope ().

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
-  - ModelOnexEnvelope refactoring
- PR #71 - Original source_node_id field
"""

import warnings
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_envelope_metadata import ModelEnvelopeMetadata
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
FIXED_METADATA = ModelEnvelopeMetadata(trace_id="abc123", request_id="req-001")


# =============================================================================
# Test Class: Instantiation
# =============================================================================


@pytest.mark.unit
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
        assert envelope.metadata == ModelEnvelopeMetadata()
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


@pytest.mark.unit
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


@pytest.mark.unit
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
        assert envelope.metadata.trace_id == "abc123"

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

        assert envelope.metadata == ModelEnvelopeMetadata()
        assert isinstance(envelope.metadata, ModelEnvelopeMetadata)

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


@pytest.mark.unit
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
        assert data["metadata"] == FIXED_METADATA.model_dump()
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestModelOnexEnvelopeStringRepresentation:
    """Test __str__ and __repr__ methods."""

    def test_str_representation(self) -> None:
        """Test __str__ produces readable output with is_response status."""
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
        assert "ModelOnexEnvelope" in str_repr
        assert "TEST_OPERATION" in str_repr
        assert "test_service" in str_repr
        assert str(FIXED_CORRELATION_ID)[:8] in str_repr
        # Should include is_response status (defaults to False)
        assert "resp=False" in str_repr

        # Verify exact format
        expected = (
            f"ModelOnexEnvelope["
            f"op=TEST_OPERATION, "
            f"corr={str(FIXED_CORRELATION_ID)[:8]}, "
            f"src=test_service, "
            f"resp=False]"
        )
        assert str_repr == expected

    def test_str_representation_with_response(self) -> None:
        """Test __str__ for response envelope shows resp=True."""
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
        # Should show is_response=True
        assert "resp=True" in str_repr

        # Verify exact format
        expected = (
            f"ModelOnexEnvelope["
            f"op=RESPONSE_OP, "
            f"corr={str(FIXED_CORRELATION_ID)[:8]}, "
            f"src=test_service, "
            f"resp=True]"
        )
        assert str_repr == expected

    def test_str_representation_request_vs_response_distinguishable(self) -> None:
        """Test that request and response envelopes are distinguishable by __str__."""
        request = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="client",
            operation="GET_DATA",
            payload={"query": "test"},
            timestamp=FIXED_TIMESTAMP,
            is_response=False,
        )

        response = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="server",
            operation="GET_DATA",
            payload={"result": "data"},
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=True,
        )

        request_str = str(request)
        response_str = str(response)

        # Both should have the same operation but different resp values
        assert "op=GET_DATA" in request_str
        assert "op=GET_DATA" in response_str
        assert "resp=False" in request_str
        assert "resp=True" in response_str


# =============================================================================
# Test Class: Equality and Hashing
# =============================================================================


@pytest.mark.unit
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


@pytest.mark.unit
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

        for original, restored in zip(
            original_envelopes, restored_envelopes, strict=True
        ):
            assert restored.envelope_id == original.envelope_id
            assert restored.correlation_id == original.correlation_id
            assert restored.payload == original.payload


# =============================================================================
# Test Class: Success/Error Field Correlation Validation
# =============================================================================


@pytest.mark.unit
class TestModelOnexEnvelopeSuccessErrorValidation:
    """
    Test validation behavior around success and error field correlation.

    These tests document the expected behavior of the ModelOnexEnvelope model
    regarding the relationship between success and error fields. The model
    allows flexible combinations to support various use cases:

    - Warnings (error message with success=True or None)
    - Failures without details (success=False without error)
    - Standard success (success=True without error)
    - Standard failure (success=False with error)

    Note: The model does NOT enforce strict correlation between success and
    error fields. This is intentional to support diverse messaging patterns.
    """

    def test_error_with_success_true_is_allowed(self) -> None:
        """
        Test that setting error with success=True is allowed (documents current behavior).

        This combination may represent a "successful with warnings" scenario
        where the operation completed but encountered non-fatal issues.

        Note: This creates a semantically inconsistent state that emits a
        warning but is still allowed for backward compatibility.
        """
        # warnings already imported at top level

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # Suppress expected warning
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="WARNING_OP",
                payload={"status": "completed_with_warnings"},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=True,
                error="Non-fatal warning: deprecated API used",
            )

        # Model allows this combination - documents current permissive behavior
        assert envelope.success is True
        assert envelope.error == "Non-fatal warning: deprecated API used"

    def test_success_false_without_error_is_valid(self) -> None:
        """
        Test that success=False without an error message is valid.

        This represents a failure case where the error details are either:
        - Not available
        - Conveyed through other means (e.g., in payload)
        - Intentionally omitted for security reasons

        Note: This emits a warning but is still allowed for backward compatibility.
        """
        # warnings already imported at top level

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # Suppress expected warning
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="SILENT_FAILURE_OP",
                payload={"error_code": "ERR_001"},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=False,
                error=None,  # No error message provided
            )

        assert envelope.success is False
        assert envelope.error is None

    def test_success_true_with_no_error_is_valid(self) -> None:
        """
        Test that success=True without an error is the standard success case.

        This is the canonical success response pattern where the operation
        completed successfully without any issues or warnings.
        """
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="SUCCESS_OP",
            payload={"result": "data"},
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=True,
            error=None,
        )

        assert envelope.success is True
        assert envelope.error is None

    def test_error_with_success_false_is_consistent(self) -> None:
        """
        Test that error with success=False is the standard failure pattern.

        This is the canonical failure response pattern where the operation
        failed and an error message explains why.
        """
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="FAILURE_OP",
            payload={},
            timestamp=FIXED_TIMESTAMP,
            is_response=True,
            success=False,
            error="Operation failed: resource not found",
        )

        assert envelope.success is False
        assert envelope.error == "Operation failed: resource not found"

    def test_success_none_is_valid(self) -> None:
        """
        Test that success=None (default) is valid.

        This represents cases where success status is:
        - Not yet determined
        - Not applicable (e.g., for request envelopes)
        - Intentionally left unset
        """
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="PENDING_OP",
            payload={"status": "processing"},
            timestamp=FIXED_TIMESTAMP,
            is_response=False,  # Request, not response
            # success defaults to None
        )

        assert envelope.success is None
        assert envelope.error is None

    def test_success_none_with_error_is_valid(self) -> None:
        """
        Test that success=None with an error message is valid.

        This represents cases like:
        - Warning messages on non-response envelopes
        - Error context without definitive success/failure status
        """
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="WARN_OP",
            payload={},
            timestamp=FIXED_TIMESTAMP,
            is_response=False,
            success=None,
            error="Warning: rate limit approaching",
        )

        assert envelope.success is None
        assert envelope.error == "Warning: rate limit approaching"

    def test_all_success_error_combinations_serialize_correctly(self) -> None:
        """
        Test that all combinations of success/error serialize and deserialize correctly.

        This ensures that regardless of the combination used, the model
        maintains data integrity through serialization round-trips.
        """
        # warnings already imported at top level

        combinations: list[tuple[bool | None, str | None]] = [
            (True, None),  # Standard success
            (False, "Error message"),  # Standard failure
            (True, "Warning message"),  # Success with warning
            (False, None),  # Silent failure
            (None, None),  # Undetermined
            (None, "Info message"),  # Info with no status
        ]

        for success_val, error_val in combinations:
            # Some combinations emit warnings, which is expected
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                original = ModelOnexEnvelope(
                    envelope_id=FIXED_ENVELOPE_ID,
                    envelope_version=DEFAULT_VERSION,
                    correlation_id=FIXED_CORRELATION_ID,
                    source_node="test_service",
                    operation="TEST_OP",
                    payload={},
                    timestamp=FIXED_TIMESTAMP,
                    is_response=True,
                    success=success_val,
                    error=error_val,
                )

                # Serialize and deserialize
                json_str = original.model_dump_json()
                restored = ModelOnexEnvelope.model_validate_json(json_str)

            # Verify round-trip preserves values
            assert restored.success == success_val, (
                f"success mismatch for ({success_val}, {error_val})"
            )
            assert restored.error == error_val, (
                f"error mismatch for ({success_val}, {error_val})"
            )


# =============================================================================
# Test Class: Success/Error Validation Warnings
# =============================================================================


@pytest.mark.unit
class TestModelOnexEnvelopeValidationWarnings:
    """
    Test that validation warnings are emitted for inconsistent success/error states.

    These tests verify the soft validation behavior added to ModelOnexEnvelope
    that warns about potentially inconsistent success/error field combinations
    while maintaining backward compatibility by not raising errors.
    """

    def test_error_with_success_true_emits_warning(self) -> None:
        """Test that setting error with success=True emits a UserWarning."""
        with pytest.warns(UserWarning, match=r"error=.*success=True"):
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="WARNING_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=True,
                error="Something went wrong",
            )

        # Envelope should still be created (soft validation)
        assert envelope.success is True
        assert envelope.error == "Something went wrong"

    def test_response_success_false_without_error_emits_warning(self) -> None:
        """Test that is_response=True with success=False but no error emits warning."""
        with pytest.warns(UserWarning, match=r"success=False.*no error"):
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="SILENT_FAIL_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=False,
                error=None,  # No error message
            )

        # Envelope should still be created (soft validation)
        assert envelope.success is False
        assert envelope.error is None

    def test_response_success_false_with_empty_error_emits_warning(self) -> None:
        """Test that success=False with empty string error emits warning."""
        # Empty string is treated as no error, so we expect the same warning pattern
        with pytest.warns(UserWarning, match=r"success=False.*no error"):
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="EMPTY_ERR_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=False,
                error="",  # Empty string
            )

        # Envelope should still be created
        assert envelope.success is False
        assert envelope.error == ""

    def test_response_success_false_with_whitespace_error_emits_warning(self) -> None:
        """Test that success=False with whitespace-only error emits warning."""
        # Whitespace-only is treated as no error, so we expect the same warning pattern
        with pytest.warns(UserWarning, match=r"success=False.*no error"):
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="WHITESPACE_ERR_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=False,
                error="   ",  # Whitespace only
            )

        # Envelope should still be created
        assert envelope.success is False

    def test_success_true_without_error_no_warning(self) -> None:
        """Test that success=True without error does NOT emit warning (canonical success)."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="SUCCESS_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=True,
                error=None,
            )

            assert envelope.success is True
            assert envelope.error is None

            # Should NOT have emitted any warnings
            assert len(caught) == 0

    def test_success_false_with_error_no_warning(self) -> None:
        """Test that success=False with error does NOT emit warning (canonical failure)."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="FAILURE_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=False,
                error="Operation failed",
            )

            assert envelope.success is False
            assert envelope.error == "Operation failed"

            # Should NOT have emitted any warnings
            assert len(caught) == 0

    def test_non_response_success_false_without_error_no_warning(self) -> None:
        """Test that non-response with success=False and no error does NOT warn."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="REQUEST_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=False,  # Not a response
                success=False,
                error=None,
            )

            assert envelope.success is False
            assert envelope.is_response is False

            # Should NOT warn - rule only applies to responses
            assert len(caught) == 0

    def test_success_none_with_error_no_warning(self) -> None:
        """Test that success=None with error does NOT emit warning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="INFO_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=None,  # Undetermined
                error="Informational message",
            )

            assert envelope.success is None
            assert envelope.error == "Informational message"

            # Should NOT warn - success is None, not True
            assert len(caught) == 0

    def test_warning_includes_correlation_id(self) -> None:
        """Test that warnings include correlation_id for debugging."""
        # Match the correlation_id in the warning message
        with pytest.warns(UserWarning, match=str(FIXED_CORRELATION_ID)):
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=True,
                error="Error with success",
            )

    def test_warning_includes_operation(self) -> None:
        """Test that warnings include operation for debugging."""
        # Match the operation name in the warning message
        with pytest.warns(UserWarning, match="MY_UNIQUE_OPERATION"):
            ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="MY_UNIQUE_OPERATION",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=True,
                error="Error with success",
            )

    def test_validation_runs_on_reconstruction(self) -> None:
        """Test that validation warnings are emitted when reconstructing with inconsistent state."""
        # Create envelope with valid state (no warning expected for canonical failure)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            envelope = ModelOnexEnvelope(
                envelope_id=FIXED_ENVELOPE_ID,
                envelope_version=DEFAULT_VERSION,
                correlation_id=FIXED_CORRELATION_ID,
                source_node="test_service",
                operation="TEST_OP",
                payload={},
                timestamp=FIXED_TIMESTAMP,
                is_response=True,
                success=False,
                error="Initial error",
            )

        # Reconstruct via model_validate to trigger validators with inconsistent state
        data = envelope.model_dump()
        data["success"] = True
        with pytest.warns(UserWarning, match=r"error=.*success=True"):
            ModelOnexEnvelope.model_validate(data)

    def test_frozen_model_rejects_assignment(self) -> None:
        """Test that direct field assignment raises ValidationError (frozen model)."""
        envelope = ModelOnexEnvelope(
            envelope_id=FIXED_ENVELOPE_ID,
            envelope_version=DEFAULT_VERSION,
            correlation_id=FIXED_CORRELATION_ID,
            source_node="test_service",
            operation="TEST_OP",
            payload={},
            timestamp=FIXED_TIMESTAMP,
        )

        with pytest.raises(ValidationError):
            envelope.success = True  # type: ignore[misc]


# =============================================================================
# Test Class: Factory Method - create_request
# =============================================================================


@pytest.mark.unit
class TestModelOnexEnvelopeCreateRequest:
    """Test the create_request factory method."""

    def test_create_request_minimal(self) -> None:
        """Test create_request with only required parameters."""
        request = ModelOnexEnvelope.create_request(
            operation="GET_DATA",
            payload={"key": "value"},
            source_node="test_service",
        )

        # Verify required fields are set correctly
        assert request.operation == "GET_DATA"
        assert request.payload == {"key": "value"}
        assert request.source_node == "test_service"

        # Verify auto-generated fields
        assert isinstance(request.envelope_id, UUID)
        assert isinstance(request.correlation_id, UUID)
        assert request.envelope_version == ModelSemVer(major=1, minor=0, patch=0)
        assert isinstance(request.timestamp, datetime)

        # Verify request-specific defaults
        assert request.is_response is False
        assert request.success is None
        assert request.error is None

        # Verify optional fields default to None
        assert request.target_node is None
        assert request.handler_type is None
        assert request.causation_id is None
        assert request.source_node_id is None

        # Verify metadata defaults to empty
        assert request.metadata == ModelEnvelopeMetadata()

    def test_create_request_with_target_node(self) -> None:
        """Test create_request with target_node specified."""
        request = ModelOnexEnvelope.create_request(
            operation="GET_USER",
            payload={"user_id": "123"},
            source_node="api_gateway",
            target_node="user_service",
        )

        assert request.source_node == "api_gateway"
        assert request.target_node == "user_service"

    def test_create_request_with_handler_type(self) -> None:
        """Test create_request with handler_type specified."""
        request = ModelOnexEnvelope.create_request(
            operation="SEND_MESSAGE",
            payload={"message": "hello"},
            source_node="producer",
            handler_type=EnumHandlerType.KAFKA,
        )

        assert request.handler_type == EnumHandlerType.KAFKA

    def test_create_request_with_explicit_correlation_id(self) -> None:
        """Test create_request with explicit correlation_id."""
        correlation = FIXED_CORRELATION_ID

        request = ModelOnexEnvelope.create_request(
            operation="TRACKED_OP",
            payload={},
            source_node="tracker",
            correlation_id=correlation,
        )

        assert request.correlation_id == correlation

    def test_create_request_with_custom_version(self) -> None:
        """Test create_request with custom envelope_version."""
        custom_version = ModelSemVer(major=2, minor=1, patch=0)

        request = ModelOnexEnvelope.create_request(
            operation="V2_OP",
            payload={},
            source_node="test",
            envelope_version=custom_version,
        )

        assert request.envelope_version == custom_version

    def test_create_request_with_metadata(self) -> None:
        """Test create_request with custom metadata."""
        metadata = ModelEnvelopeMetadata(
            trace_id="trace-123",
            request_id="req-456",
        )

        request = ModelOnexEnvelope.create_request(
            operation="TRACED_OP",
            payload={},
            source_node="test",
            metadata=metadata,
        )

        assert request.metadata.trace_id == "trace-123"
        assert request.metadata.request_id == "req-456"

    def test_create_request_with_source_node_id(self) -> None:
        """Test create_request with source_node_id specified."""
        source_id = FIXED_SOURCE_NODE_ID

        request = ModelOnexEnvelope.create_request(
            operation="INSTANCE_OP",
            payload={},
            source_node="scaled_service",
            source_node_id=source_id,
        )

        assert request.source_node_id == source_id

    def test_create_request_with_all_options(self) -> None:
        """Test create_request with all optional parameters."""
        custom_version = ModelSemVer(major=2, minor=0, patch=0)
        metadata = ModelEnvelopeMetadata(trace_id="abc")

        request = ModelOnexEnvelope.create_request(
            operation="FULL_OP",
            payload={"data": "test"},
            source_node="source",
            target_node="target",
            handler_type=EnumHandlerType.HTTP,
            correlation_id=FIXED_CORRELATION_ID,
            envelope_version=custom_version,
            metadata=metadata,
            source_node_id=FIXED_SOURCE_NODE_ID,
        )

        assert request.operation == "FULL_OP"
        assert request.payload == {"data": "test"}
        assert request.source_node == "source"
        assert request.target_node == "target"
        assert request.handler_type == EnumHandlerType.HTTP
        assert request.correlation_id == FIXED_CORRELATION_ID
        assert request.envelope_version == custom_version
        assert request.metadata.trace_id == "abc"
        assert request.source_node_id == FIXED_SOURCE_NODE_ID

    def test_create_request_generates_unique_envelope_ids(self) -> None:
        """Test that create_request generates unique envelope_ids."""
        requests = [
            ModelOnexEnvelope.create_request(
                operation="OP",
                payload={},
                source_node="test",
            )
            for _ in range(10)
        ]

        envelope_ids = [r.envelope_id for r in requests]
        assert len(set(envelope_ids)) == 10, "All envelope_ids should be unique"

    def test_create_request_generates_unique_correlation_ids_when_not_specified(
        self,
    ) -> None:
        """Test that create_request generates unique correlation_ids when not provided."""
        requests = [
            ModelOnexEnvelope.create_request(
                operation="OP",
                payload={},
                source_node="test",
            )
            for _ in range(10)
        ]

        correlation_ids = [r.correlation_id for r in requests]
        assert len(set(correlation_ids)) == 10, "All correlation_ids should be unique"

    def test_create_request_timestamp_is_recent(self) -> None:
        """Test that create_request sets a recent timestamp."""
        before = datetime.now(UTC)
        request = ModelOnexEnvelope.create_request(
            operation="TIME_OP",
            payload={},
            source_node="test",
        )
        after = datetime.now(UTC)

        assert before <= request.timestamp <= after

    def test_create_request_serializes_correctly(self) -> None:
        """Test that envelopes created via create_request serialize/deserialize."""
        request = ModelOnexEnvelope.create_request(
            operation="SERIALIZE_OP",
            payload={"nested": {"key": "value"}},
            source_node="test",
            target_node="target",
        )

        json_str = request.model_dump_json()
        restored = ModelOnexEnvelope.model_validate_json(json_str)

        assert restored.operation == request.operation
        assert restored.payload == request.payload
        assert restored.source_node == request.source_node
        assert restored.correlation_id == request.correlation_id


# =============================================================================
# Test Class: Factory Method - create_response
# =============================================================================


@pytest.mark.unit
class TestModelOnexEnvelopeCreateResponse:
    """Test the create_response factory method."""

    def test_create_response_minimal(self) -> None:
        """Test create_response with only required parameters."""
        request = ModelOnexEnvelope.create_request(
            operation="GET_DATA",
            payload={"query": "test"},
            source_node="client",
            target_node="server",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={"result": "data"},
        )

        # Verify response-specific fields
        assert response.is_response is True
        assert response.success is True  # Default
        assert response.error is None

        # Verify causation chain
        assert response.correlation_id == request.correlation_id
        assert response.causation_id == request.envelope_id

        # Verify envelope_version inherited
        assert response.envelope_version == request.envelope_version

        # Verify node swapping
        assert response.source_node == request.target_node  # server
        assert response.target_node == request.source_node  # client

        # Verify operation naming
        assert response.operation == "GET_DATA_RESPONSE"

    def test_create_response_with_success_false(self) -> None:
        """Test create_response with explicit success=False and error."""
        request = ModelOnexEnvelope.create_request(
            operation="GET_USER",
            payload={"user_id": "123"},
            source_node="api",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
            success=False,
            error="User not found: 123",
        )

        assert response.is_response is True
        assert response.success is False
        assert response.error == "User not found: 123"

    def test_create_response_inherits_correlation_id(self) -> None:
        """Test that create_response properly inherits correlation_id."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
            correlation_id=FIXED_CORRELATION_ID,
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
        )

        assert response.correlation_id == FIXED_CORRELATION_ID

    def test_create_response_sets_causation_id(self) -> None:
        """Test that create_response sets causation_id to request's envelope_id."""
        request = ModelOnexEnvelope.create_request(
            operation="CAUSE_OP",
            payload={},
            source_node="test",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
        )

        assert response.causation_id == request.envelope_id

    def test_create_response_with_custom_source_node(self) -> None:
        """Test create_response with explicit source_node override."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="client",
            target_node="server",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
            source_node="different_server",
        )

        assert response.source_node == "different_server"
        assert response.target_node == "client"  # Still goes back to original source

    def test_create_response_with_custom_operation(self) -> None:
        """Test create_response with explicit operation override."""
        request = ModelOnexEnvelope.create_request(
            operation="GET_DATA",
            payload={},
            source_node="test",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
            operation="DATA_FETCHED",
        )

        assert response.operation == "DATA_FETCHED"

    def test_create_response_inherits_handler_type(self) -> None:
        """Test that create_response inherits handler_type from request."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
            handler_type=EnumHandlerType.KAFKA,
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
        )

        assert response.handler_type == EnumHandlerType.KAFKA

    def test_create_response_can_override_handler_type(self) -> None:
        """Test that create_response can override handler_type."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
            handler_type=EnumHandlerType.KAFKA,
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
            handler_type=EnumHandlerType.HTTP,
        )

        assert response.handler_type == EnumHandlerType.HTTP

    def test_create_response_with_metadata(self) -> None:
        """Test create_response with custom metadata."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
        )

        metadata = ModelEnvelopeMetadata(
            trace_id="response-trace",
            span_id="response-span",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
            metadata=metadata,
        )

        assert response.metadata.trace_id == "response-trace"
        assert response.metadata.span_id == "response-span"

    def test_create_response_with_source_node_id(self) -> None:
        """Test create_response with source_node_id."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
            source_node_id=FIXED_SOURCE_NODE_ID,
        )

        assert response.source_node_id == FIXED_SOURCE_NODE_ID

    def test_create_response_generates_unique_envelope_id(self) -> None:
        """Test that create_response generates unique envelope_id."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
        )

        responses = [
            ModelOnexEnvelope.create_response(request=request, payload={})
            for _ in range(10)
        ]

        envelope_ids = [r.envelope_id for r in responses]
        assert len(set(envelope_ids)) == 10, "All envelope_ids should be unique"

    def test_create_response_timestamp_is_recent(self) -> None:
        """Test that create_response sets a recent timestamp."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
        )

        before = datetime.now(UTC)
        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
        )
        after = datetime.now(UTC)

        assert before <= response.timestamp <= after

    def test_create_response_when_request_has_no_target(self) -> None:
        """Test create_response when request has no target_node."""
        request = ModelOnexEnvelope.create_request(
            operation="BROADCAST_OP",
            payload={},
            source_node="broadcaster",
            # No target_node specified
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
        )

        # source_node should fall back to request's source_node
        assert response.source_node == "broadcaster"
        assert response.target_node == "broadcaster"

    def test_create_response_serializes_correctly(self) -> None:
        """Test that envelopes created via create_response serialize/deserialize."""
        request = ModelOnexEnvelope.create_request(
            operation="SERIALIZE_OP",
            payload={},
            source_node="client",
            target_node="server",
        )

        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={"result": "success"},
            success=True,
        )

        json_str = response.model_dump_json()
        restored = ModelOnexEnvelope.model_validate_json(json_str)

        assert restored.is_response is True
        assert restored.success is True
        assert restored.correlation_id == request.correlation_id
        assert restored.causation_id == request.envelope_id

    def test_create_response_error_with_success_false_emits_no_warning(self) -> None:
        """Test that proper error response doesn't emit warning."""
        request = ModelOnexEnvelope.create_request(
            operation="OP",
            payload={},
            source_node="test",
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            response = ModelOnexEnvelope.create_response(
                request=request,
                payload={},
                success=False,
                error="Operation failed",
            )

            assert response.success is False
            assert response.error == "Operation failed"
            assert len(caught) == 0


# =============================================================================
# Test Class: Request/Response Flow Integration
# =============================================================================


@pytest.mark.unit
class TestModelOnexEnvelopeRequestResponseFlow:
    """Test complete request/response flows using factory methods."""

    def test_complete_successful_flow(self) -> None:
        """Test a complete successful request/response flow."""
        # 1. Create request
        request = ModelOnexEnvelope.create_request(
            operation="GET_USER_PROFILE",
            payload={"user_id": "user-123"},
            source_node="api_gateway",
            target_node="user_service",
            handler_type=EnumHandlerType.HTTP,
        )

        # 2. Create success response
        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={
                "user": {
                    "id": "user-123",
                    "name": "Alice",
                    "email": "alice@example.com",
                }
            },
            success=True,
        )

        # Verify the flow
        assert request.is_response is False
        assert response.is_response is True

        # Verify correlation
        assert response.correlation_id == request.correlation_id

        # Verify causation chain
        assert response.causation_id == request.envelope_id
        assert request.causation_id is None  # Root request has no cause

        # Verify routing
        assert request.source_node == "api_gateway"
        assert request.target_node == "user_service"
        assert response.source_node == "user_service"  # Swapped
        assert response.target_node == "api_gateway"  # Swapped

        # Verify operation naming
        assert request.operation == "GET_USER_PROFILE"
        assert response.operation == "GET_USER_PROFILE_RESPONSE"

    def test_complete_error_flow(self) -> None:
        """Test a complete error request/response flow."""
        # 1. Create request
        request = ModelOnexEnvelope.create_request(
            operation="GET_USER_PROFILE",
            payload={"user_id": "nonexistent"},
            source_node="api_gateway",
            target_node="user_service",
        )

        # 2. Create error response
        response = ModelOnexEnvelope.create_response(
            request=request,
            payload={},
            success=False,
            error="User not found: nonexistent",
        )

        # Verify error response
        assert response.is_response is True
        assert response.success is False
        assert response.error == "User not found: nonexistent"
        assert response.causation_id == request.envelope_id

    def test_chained_requests_causation(self) -> None:
        """Test causation chain through multiple requests."""
        # Initial request from client
        initial_request = ModelOnexEnvelope.create_request(
            operation="CREATE_ORDER",
            payload={"items": [{"id": 1, "qty": 2}]},
            source_node="client_app",
            target_node="order_service",
        )

        # Order service needs to check inventory (chained request)
        inventory_request = ModelOnexEnvelope.create_request(
            operation="CHECK_INVENTORY",
            payload={"item_id": 1, "qty": 2},
            source_node="order_service",
            target_node="inventory_service",
            correlation_id=initial_request.correlation_id,  # Same correlation
        )

        # Inventory response
        inventory_response = ModelOnexEnvelope.create_response(
            request=inventory_request,
            payload={"available": True},
            success=True,
        )

        # Final response to client
        order_response = ModelOnexEnvelope.create_response(
            request=initial_request,
            payload={"order_id": "order-123"},
            success=True,
        )

        # All should share the same correlation_id
        assert initial_request.correlation_id == inventory_request.correlation_id
        assert initial_request.correlation_id == inventory_response.correlation_id
        assert initial_request.correlation_id == order_response.correlation_id

        # Causation chain should be:
        # initial_request -> None (root)
        # inventory_request -> None (new request, not response)
        # inventory_response -> inventory_request.envelope_id
        # order_response -> initial_request.envelope_id
        assert initial_request.causation_id is None
        assert inventory_request.causation_id is None
        assert inventory_response.causation_id == inventory_request.envelope_id
        assert order_response.causation_id == initial_request.envelope_id

    def test_multiple_responses_to_same_request(self) -> None:
        """Test creating multiple responses to the same request (e.g., retries)."""
        request = ModelOnexEnvelope.create_request(
            operation="FLAKY_OP",
            payload={},
            source_node="client",
            target_node="server",
        )

        # First attempt fails
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Suppress expected warning
            response1 = ModelOnexEnvelope.create_response(
                request=request,
                payload={},
                success=False,
            )

        # Retry succeeds
        response2 = ModelOnexEnvelope.create_response(
            request=request,
            payload={"result": "success"},
            success=True,
        )

        # Both responses should point to the same request
        assert response1.causation_id == request.envelope_id
        assert response2.causation_id == request.envelope_id

        # But have different envelope_ids
        assert response1.envelope_id != response2.envelope_id

        # And same correlation_id
        assert response1.correlation_id == request.correlation_id
        assert response2.correlation_id == request.correlation_id
