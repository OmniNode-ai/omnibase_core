"""Tests for ModelIntentRecordPayload model.

This module tests the lightweight intent record payload used in
query response events for the intent storage pipeline.

Test Coverage:
    - Basic instantiation with required fields
    - Default values for optional fields
    - Field validation (confidence bounds)
    - Serialization of domain fields only
    - Extra fields forbidden
    - Event metadata fields rejected (payload not event)
    - Model immutability (frozen=True)

Created: 2025-01-25
PR Coverage: OMN-1513 Intent Storage Event Models
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.model_intent_record_payload import (
    ModelIntentRecordPayload,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_intent_id() -> UUID:
    """Create a sample intent ID."""
    return uuid4()


@pytest.fixture
def sample_created_at() -> datetime:
    """Create a sample created_at timestamp."""
    return datetime.now(UTC)


@pytest.fixture
def sample_payload(
    sample_intent_id: UUID, sample_created_at: datetime
) -> ModelIntentRecordPayload:
    """Create a sample intent record payload for testing."""
    return ModelIntentRecordPayload(
        intent_id=sample_intent_id,
        session_ref="session-abc-123",
        intent_category="code_generation",
        confidence=0.85,
        keywords=["python", "testing"],
        created_at=sample_created_at,
    )


# ============================================================================
# Tests for Basic Instantiation
# ============================================================================


@pytest.mark.unit
class TestModelIntentRecordPayloadBasic:
    """Test ModelIntentRecordPayload basic creation and validation."""

    def test_payload_creation_all_required_fields(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test creating payload with all required fields."""
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-123",
            intent_category="debugging",
            created_at=sample_created_at,
        )

        assert payload.intent_id == sample_intent_id
        assert payload.session_ref == "session-123"
        assert payload.intent_category == "debugging"
        assert payload.created_at == sample_created_at
        # Default values
        assert payload.confidence == 0.0
        assert payload.keywords == []

    def test_payload_creation_all_fields(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test creating payload with all fields specified."""
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-full-test",
            intent_category="code_review",
            confidence=0.95,
            keywords=["review", "security", "performance"],
            created_at=sample_created_at,
        )

        assert payload.intent_id == sample_intent_id
        assert payload.session_ref == "session-full-test"
        assert payload.intent_category == "code_review"
        assert payload.confidence == 0.95
        assert payload.keywords == ["review", "security", "performance"]
        assert payload.created_at == sample_created_at

    def test_payload_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecordPayload()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        # Should have errors for intent_id, session_ref, intent_category, created_at
        required_fields = {"intent_id", "session_ref", "intent_category", "created_at"}
        error_locs = {str(e["loc"][0]) for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(error_locs)

    def test_payload_extra_fields_forbidden(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelIntentRecordPayload(
                intent_id=sample_intent_id,
                session_ref="session-123",
                intent_category="debugging",
                created_at=sample_created_at,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )


# ============================================================================
# Tests for Field Validation
# ============================================================================


@pytest.mark.unit
class TestModelIntentRecordPayloadValidation:
    """Test ModelIntentRecordPayload field validation."""

    def test_confidence_valid_range(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test that confidence accepts valid values (0.0 to 1.0)."""
        # Minimum value
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-123",
            intent_category="debugging",
            confidence=0.0,
            created_at=sample_created_at,
        )
        assert payload.confidence == 0.0

        # Maximum value
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-123",
            intent_category="debugging",
            confidence=1.0,
            created_at=sample_created_at,
        )
        assert payload.confidence == 1.0

        # Middle value
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-123",
            intent_category="debugging",
            confidence=0.5,
            created_at=sample_created_at,
        )
        assert payload.confidence == 0.5

    def test_confidence_below_minimum_rejected(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test that confidence below 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecordPayload(
                intent_id=sample_intent_id,
                session_ref="session-123",
                intent_category="debugging",
                confidence=-0.1,
                created_at=sample_created_at,
            )

        errors = exc_info.value.errors()
        assert any("confidence" in str(e.get("loc", [])) for e in errors)

    def test_confidence_above_maximum_rejected(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test that confidence above 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecordPayload(
                intent_id=sample_intent_id,
                session_ref="session-123",
                intent_category="debugging",
                confidence=1.1,
                created_at=sample_created_at,
            )

        errors = exc_info.value.errors()
        assert any("confidence" in str(e.get("loc", [])) for e in errors)

    def test_keywords_default_empty_list(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test that keywords defaults to empty list."""
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-123",
            intent_category="debugging",
            created_at=sample_created_at,
        )

        assert payload.keywords == []
        assert isinstance(payload.keywords, list)


# ============================================================================
# Tests for Payload Rejects Event Fields
# ============================================================================


@pytest.mark.unit
class TestModelIntentRecordPayloadRejectsEventFields:
    """Verify payload does not accept event metadata fields.

    ModelIntentRecordPayload is a pure payload model that should NOT contain
    event metadata fields (event_id, timestamp, source_node_id, correlation_id).
    These fields belong to the envelope, not the payload.
    """

    def test_event_id_rejected(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Payload should not accept event_id field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecordPayload(
                intent_id=sample_intent_id,
                session_ref="session-123",
                intent_category="debugging",
                created_at=sample_created_at,
                event_id=uuid4(),  # type: ignore[call-arg]
            )
        assert "event_id" in str(exc_info.value)

    def test_source_node_id_rejected(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Payload should not accept source_node_id field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecordPayload(
                intent_id=sample_intent_id,
                session_ref="session-123",
                intent_category="debugging",
                created_at=sample_created_at,
                source_node_id=uuid4(),  # type: ignore[call-arg]
            )
        assert "source_node_id" in str(exc_info.value)

    def test_correlation_id_rejected(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Payload should not accept correlation_id field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecordPayload(
                intent_id=sample_intent_id,
                session_ref="session-123",
                intent_category="debugging",
                created_at=sample_created_at,
                correlation_id=uuid4(),  # type: ignore[call-arg]
            )
        assert "correlation_id" in str(exc_info.value)

    def test_timestamp_rejected(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Payload should not accept timestamp field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecordPayload(
                intent_id=sample_intent_id,
                session_ref="session-123",
                intent_category="debugging",
                created_at=sample_created_at,
                timestamp=datetime.now(UTC),  # type: ignore[call-arg]
            )
        assert "timestamp" in str(exc_info.value)


# ============================================================================
# Tests for Model Immutability
# ============================================================================


@pytest.mark.unit
class TestModelIntentRecordPayloadImmutability:
    """Test ModelIntentRecordPayload frozen model behavior."""

    def test_payload_is_frozen(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Verify payload is immutable (frozen=True)."""
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-123",
            intent_category="debugging",
            created_at=sample_created_at,
        )
        with pytest.raises(ValidationError):
            payload.session_ref = "new-session"  # type: ignore[misc]

    def test_keywords_list_cannot_be_reassigned(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Verify keywords list cannot be reassigned on frozen model."""
        payload = ModelIntentRecordPayload(
            intent_id=sample_intent_id,
            session_ref="session-123",
            intent_category="debugging",
            keywords=["original"],
            created_at=sample_created_at,
        )
        with pytest.raises(ValidationError):
            payload.keywords = ["new", "list"]  # type: ignore[misc]


# ============================================================================
# Tests for Serialization
# ============================================================================


@pytest.mark.unit
class TestModelIntentRecordPayloadSerialization:
    """Test ModelIntentRecordPayload serialization."""

    def test_model_dump_includes_all_fields(
        self,
        sample_payload: ModelIntentRecordPayload,
    ) -> None:
        """Test that model_dump includes all domain fields."""
        data = sample_payload.model_dump()

        # Domain fields
        assert "intent_id" in data
        assert "session_ref" in data
        assert "intent_category" in data
        assert "confidence" in data
        assert "keywords" in data
        assert "created_at" in data
        # Event metadata fields should NOT be present (payload, not event)
        assert "event_id" not in data
        assert "timestamp" not in data
        assert "correlation_id" not in data
        assert "source_node_id" not in data

    def test_model_dump_json_serializable(
        self,
        sample_payload: ModelIntentRecordPayload,
    ) -> None:
        """Test that model can be serialized to JSON."""
        json_str = sample_payload.model_dump_json()

        assert isinstance(json_str, str)
        assert "session-abc-123" in json_str
        assert "code_generation" in json_str

    def test_model_validate_from_dict(
        self,
        sample_intent_id: UUID,
        sample_created_at: datetime,
    ) -> None:
        """Test that model can be validated from dict."""
        data = {
            "intent_id": str(sample_intent_id),
            "session_ref": "session-from-dict",
            "intent_category": "testing",
            "confidence": 0.75,
            "keywords": ["unit", "test"],
            "created_at": sample_created_at.isoformat(),
        }

        payload = ModelIntentRecordPayload.model_validate(data)

        assert payload.session_ref == "session-from-dict"
        assert payload.intent_category == "testing"
        assert payload.confidence == 0.75
