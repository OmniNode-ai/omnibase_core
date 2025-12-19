"""
Unit tests for source_node_id field in ModelOnexEnvelope.

Tests the functionality of the optional source_node_id field added in PR #71.
Uses mocks for deterministic testing - no performance measurement.

Tests verify:
- Envelope creation with/without source_node_id
- Serialization includes source_node_id when provided
- Deserialization handles source_node_id correctly
- Field is truly optional (works with None)
- Bulk operations work correctly

Related:
- PR #71 - Added source_node_id field
- Correlation ID: 95cac850-05a3-43e2-9e57-ccbbef683f43
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestSourceNodeIdFunctionality:
    """Unit tests for source_node_id field functionality."""

    # Fixed test data for deterministic testing
    FIXED_CORRELATION_ID = UUID("12345678-1234-5678-1234-567812345678")
    FIXED_EVENT_ID = UUID("87654321-4321-8765-4321-876543218765")
    FIXED_SOURCE_NODE_ID = UUID("11111111-2222-3333-4444-555555555555")
    FIXED_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    FIXED_PAYLOAD = {"key": "value", "count": 42}

    def test_creation_without_source_node_id(self) -> None:
        """Test envelope creation without source_node_id field."""
        envelope = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            payload=self.FIXED_PAYLOAD,
        )

        # Verify basic fields
        assert envelope.correlation_id == self.FIXED_CORRELATION_ID
        assert envelope.envelope_id == self.FIXED_EVENT_ID
        assert envelope.operation == "TEST_EVENT"
        assert envelope.source_node == "test_service"
        assert envelope.payload == self.FIXED_PAYLOAD

        # Verify source_node_id is None when not provided
        assert envelope.source_node_id is None

    def test_creation_with_source_node_id(self) -> None:
        """Test envelope creation with source_node_id field."""
        envelope = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,  # Add source_node_id
            payload=self.FIXED_PAYLOAD,
        )

        # Verify source_node_id is set correctly
        assert envelope.source_node_id == self.FIXED_SOURCE_NODE_ID

        # Verify other fields unchanged
        assert envelope.correlation_id == self.FIXED_CORRELATION_ID
        assert envelope.envelope_id == self.FIXED_EVENT_ID

    def test_source_node_id_is_optional(self) -> None:
        """Test that source_node_id field is truly optional."""
        # Create without source_node_id - should not raise
        envelope = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            payload=self.FIXED_PAYLOAD,
        )

        assert envelope.source_node_id is None

        # Explicitly set to None - should also work
        envelope_explicit = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=None,
            payload=self.FIXED_PAYLOAD,
        )

        assert envelope_explicit.source_node_id is None

    def test_serialization_excludes_none_source_node_id(self) -> None:
        """Test that serialization excludes source_node_id when None."""
        envelope = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            payload=self.FIXED_PAYLOAD,
        )

        # Serialize to dict
        data = envelope.model_dump()

        # source_node_id should not be in dict when None
        assert "source_node_id" not in data or data["source_node_id"] is None

    def test_serialization_includes_source_node_id(self) -> None:
        """Test that serialization includes source_node_id when provided."""
        envelope = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,
            payload=self.FIXED_PAYLOAD,
        )

        # Serialize to dict
        data = envelope.model_dump()

        # source_node_id should be in dict
        assert "source_node_id" in data
        assert data["source_node_id"] == self.FIXED_SOURCE_NODE_ID

    def test_json_serialization_with_source_node_id(self) -> None:
        """Test JSON serialization includes source_node_id."""
        envelope = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,
            payload=self.FIXED_PAYLOAD,
        )

        # Serialize to JSON
        json_str = envelope.model_dump_json()

        # JSON should contain source_node_id
        assert str(self.FIXED_SOURCE_NODE_ID) in json_str
        assert "source_node_id" in json_str

    def test_deserialization_with_source_node_id(self) -> None:
        """Test deserialization from JSON with source_node_id."""
        # Create envelope with source_node_id
        original = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,
            payload=self.FIXED_PAYLOAD,
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        deserialized = ModelOnexEnvelope.model_validate_json(json_str)

        # Verify source_node_id preserved
        assert deserialized.source_node_id == self.FIXED_SOURCE_NODE_ID
        assert deserialized.correlation_id == self.FIXED_CORRELATION_ID

    def test_deserialization_without_source_node_id(self) -> None:
        """Test deserialization from JSON without source_node_id."""
        # Create envelope without source_node_id
        original = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            payload=self.FIXED_PAYLOAD,
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        deserialized = ModelOnexEnvelope.model_validate_json(json_str)

        # Verify source_node_id is None
        assert deserialized.source_node_id is None

    def test_bulk_creation_with_source_node_id(self) -> None:
        """Test bulk envelope creation with source_node_id works correctly."""
        count = 100

        # Create multiple envelopes with source_node_id
        envelopes = [
            ModelOnexEnvelope(
                envelope_version=DEFAULT_VERSION,
                correlation_id=UUID(f"00000000-0000-0000-0000-{i:012d}"),
                envelope_id=UUID(f"11111111-1111-1111-1111-{i:012d}"),
                operation="TEST_EVENT",
                timestamp=self.FIXED_TIMESTAMP,
                source_node="test_service",
                source_node_id=UUID(f"22222222-2222-2222-2222-{i:012d}"),
                payload={"index": i},
            )
            for i in range(count)
        ]

        # Verify count
        assert len(envelopes) == count

        # Verify each has correct source_node_id
        for i, envelope in enumerate(envelopes):
            expected_source_node = UUID(f"22222222-2222-2222-2222-{i:012d}")
            assert envelope.source_node_id == expected_source_node
            assert envelope.payload["index"] == i

    def test_bulk_serialization_with_source_node_id(self) -> None:
        """Test bulk serialization preserves source_node_id."""
        count = 50

        # Create envelopes
        envelopes = [
            ModelOnexEnvelope(
                envelope_version=DEFAULT_VERSION,
                correlation_id=UUID(f"00000000-0000-0000-0000-{i:012d}"),
                envelope_id=UUID(f"11111111-1111-1111-1111-{i:012d}"),
                operation="TEST_EVENT",
                timestamp=self.FIXED_TIMESTAMP,
                source_node="test_service",
                source_node_id=UUID(f"22222222-2222-2222-2222-{i:012d}"),
                payload={"index": i},
            )
            for i in range(count)
        ]

        # Serialize all
        serialized = [env.model_dump_json() for env in envelopes]

        # Verify count
        assert len(serialized) == count

        # Verify each serialized version contains source_node_id
        for i, json_str in enumerate(serialized):
            expected_id = f"22222222-2222-2222-2222-{i:012d}"
            assert expected_id in json_str
            assert "source_node_id" in json_str

    def test_round_trip_with_source_node_id(self) -> None:
        """Test complete round-trip (create -> serialize -> deserialize)."""
        # Create original
        original = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,
            payload=self.FIXED_PAYLOAD,
        )

        # Round trip
        json_str = original.model_dump_json()
        restored = ModelOnexEnvelope.model_validate_json(json_str)

        # Verify all fields match
        assert restored.correlation_id == original.correlation_id
        assert restored.envelope_id == original.envelope_id
        assert restored.source_node_id == original.source_node_id
        assert restored.operation == original.operation
        assert restored.source_node == original.source_node
        assert restored.payload == original.payload

    def test_equality_with_source_node_id(self) -> None:
        """Test equality comparison works with source_node_id."""
        envelope1 = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,
            payload=self.FIXED_PAYLOAD,
        )

        envelope2 = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,
            payload=self.FIXED_PAYLOAD,
        )

        # Should be equal
        assert envelope1.correlation_id == envelope2.correlation_id
        assert envelope1.source_node_id == envelope2.source_node_id

    def test_different_source_node_ids_not_equal(self) -> None:
        """Test envelopes with different source_node_ids are not equal."""
        envelope1 = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=self.FIXED_SOURCE_NODE_ID,
            payload=self.FIXED_PAYLOAD,
        )

        different_node_id = UUID("99999999-9999-9999-9999-999999999999")
        envelope2 = ModelOnexEnvelope(
            envelope_version=DEFAULT_VERSION,
            correlation_id=self.FIXED_CORRELATION_ID,
            envelope_id=self.FIXED_EVENT_ID,
            operation="TEST_EVENT",
            timestamp=self.FIXED_TIMESTAMP,
            source_node="test_service",
            source_node_id=different_node_id,
            payload=self.FIXED_PAYLOAD,
        )

        # source_node_ids should be different
        assert envelope1.source_node_id != envelope2.source_node_id
