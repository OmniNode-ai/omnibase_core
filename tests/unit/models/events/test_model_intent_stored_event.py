"""Tests for ModelIntentStoredEvent model.

This module tests the event model published when an intent classification
has been successfully stored in the graph database.

Test Coverage:
    - Basic instantiation with required fields
    - Default values for optional fields
    - Factory method create()
    - Factory method from_error()
    - Field validation (confidence, execution_time_ms)
    - Status literal validation
    - Serialization

Created: 2025-01-25
PR Coverage: OMN-1513 Intent Storage Event Models
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.model_intent_stored_event import (
    INTENT_STORED_EVENT,
    ModelIntentStoredEvent,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_intent_id() -> UUID:
    """Create a sample intent ID."""
    return uuid4()


@pytest.fixture
def sample_correlation_id() -> UUID:
    """Create a sample correlation ID."""
    return uuid4()


@pytest.fixture
def sample_source_node_id() -> UUID:
    """Create a sample source node ID."""
    return uuid4()


# ============================================================================
# Tests for Basic Instantiation
# ============================================================================


@pytest.mark.unit
class TestModelIntentStoredEventBasic:
    """Test ModelIntentStoredEvent basic creation and validation."""

    def test_event_creation_minimal(self) -> None:
        """Test creating event with minimal required fields."""
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
        )

        assert event.session_ref == "session-123"
        assert event.intent_category == "debugging"
        # Check defaults
        assert event.event_type == INTENT_STORED_EVENT
        assert isinstance(event.intent_id, UUID)
        assert event.confidence == 0.0
        assert event.keywords == []
        assert event.created is True
        assert isinstance(event.stored_at, datetime)
        assert event.execution_time_ms == 0.0
        assert event.status == "success"
        assert event.error_message is None

    def test_event_creation_all_fields(
        self,
        sample_intent_id: UUID,
        sample_correlation_id: UUID,
        sample_source_node_id: UUID,
    ) -> None:
        """Test creating event with all fields specified."""
        stored_at = datetime.now(UTC)

        event = ModelIntentStoredEvent(
            intent_id=sample_intent_id,
            session_ref="session-full-test",
            intent_category="code_generation",
            confidence=0.92,
            keywords=["python", "fastapi", "async"],
            created=False,
            stored_at=stored_at,
            execution_time_ms=15.5,
            status="success",
            correlation_id=sample_correlation_id,
            source_node_id=sample_source_node_id,
        )

        assert event.intent_id == sample_intent_id
        assert event.session_ref == "session-full-test"
        assert event.intent_category == "code_generation"
        assert event.confidence == 0.92
        assert event.keywords == ["python", "fastapi", "async"]
        assert event.created is False
        assert event.stored_at == stored_at
        assert event.execution_time_ms == 15.5
        assert event.status == "success"
        assert event.correlation_id == sample_correlation_id
        assert event.source_node_id == sample_source_node_id

    def test_event_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStoredEvent()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        required_fields = {"session_ref", "intent_category"}
        error_locs = {str(e["loc"][0]) for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(error_locs)

    def test_event_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelIntentStoredEvent(
                session_ref="session-123",
                intent_category="debugging",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

    def test_event_type_constant(self) -> None:
        """Test that event_type matches the constant."""
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
        )

        assert event.event_type == "dev.omnimemory.intent.stored.v1"
        assert event.event_type == INTENT_STORED_EVENT


# ============================================================================
# Tests for Factory Methods
# ============================================================================


@pytest.mark.unit
class TestModelIntentStoredEventFactoryMethods:
    """Test ModelIntentStoredEvent factory methods."""

    def test_create_minimal(self) -> None:
        """Test create() factory with minimal arguments."""
        event = ModelIntentStoredEvent.create(
            session_ref="session-create-test",
            intent_category="testing",
        )

        assert event.session_ref == "session-create-test"
        assert event.intent_category == "testing"
        assert event.status == "success"
        assert isinstance(event.intent_id, UUID)

    def test_create_all_arguments(
        self,
        sample_intent_id: UUID,
        sample_correlation_id: UUID,
        sample_source_node_id: UUID,
    ) -> None:
        """Test create() factory with all arguments."""
        event = ModelIntentStoredEvent.create(
            session_ref="session-full-create",
            intent_category="code_review",
            intent_id=sample_intent_id,
            confidence=0.88,
            keywords=["review", "security"],
            created=False,
            execution_time_ms=25.3,
            correlation_id=sample_correlation_id,
            source_node_id=sample_source_node_id,
        )

        assert event.intent_id == sample_intent_id
        assert event.session_ref == "session-full-create"
        assert event.intent_category == "code_review"
        assert event.confidence == 0.88
        assert event.keywords == ["review", "security"]
        assert event.created is False
        assert event.execution_time_ms == 25.3
        assert event.correlation_id == sample_correlation_id
        assert event.source_node_id == sample_source_node_id
        assert event.status == "success"

    def test_create_generates_intent_id_if_none(self) -> None:
        """Test that create() generates intent_id if not provided."""
        event1 = ModelIntentStoredEvent.create(
            session_ref="session-1",
            intent_category="testing",
        )
        event2 = ModelIntentStoredEvent.create(
            session_ref="session-2",
            intent_category="testing",
        )

        assert isinstance(event1.intent_id, UUID)
        assert isinstance(event2.intent_id, UUID)
        assert event1.intent_id != event2.intent_id

    def test_from_error_minimal(self) -> None:
        """Test from_error() factory with minimal arguments."""
        event = ModelIntentStoredEvent.from_error(
            session_ref="session-error-test",
            intent_category="failed_intent",
            error_message="Database connection failed",
        )

        assert event.session_ref == "session-error-test"
        assert event.intent_category == "failed_intent"
        assert event.status == "error"
        assert event.error_message == "Database connection failed"

    def test_from_error_all_arguments(
        self,
        sample_correlation_id: UUID,
        sample_source_node_id: UUID,
    ) -> None:
        """Test from_error() factory with all arguments."""
        event = ModelIntentStoredEvent.from_error(
            session_ref="session-full-error",
            intent_category="failed_store",
            error_message="Memgraph unavailable",
            correlation_id=sample_correlation_id,
            source_node_id=sample_source_node_id,
        )

        assert event.session_ref == "session-full-error"
        assert event.intent_category == "failed_store"
        assert event.status == "error"
        assert event.error_message == "Memgraph unavailable"
        assert event.correlation_id == sample_correlation_id
        assert event.source_node_id == sample_source_node_id


# ============================================================================
# Tests for Field Validation
# ============================================================================


@pytest.mark.unit
class TestModelIntentStoredEventValidation:
    """Test ModelIntentStoredEvent field validation."""

    def test_confidence_valid_range(self) -> None:
        """Test that confidence accepts valid values (0.0 to 1.0)."""
        # Minimum value
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
            confidence=0.0,
        )
        assert event.confidence == 0.0

        # Maximum value
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
            confidence=1.0,
        )
        assert event.confidence == 1.0

    def test_confidence_below_minimum_rejected(self) -> None:
        """Test that confidence below 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStoredEvent(
                session_ref="session-123",
                intent_category="debugging",
                confidence=-0.1,
            )

        errors = exc_info.value.errors()
        assert any("confidence" in str(e.get("loc", [])) for e in errors)

    def test_confidence_above_maximum_rejected(self) -> None:
        """Test that confidence above 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStoredEvent(
                session_ref="session-123",
                intent_category="debugging",
                confidence=1.1,
            )

        errors = exc_info.value.errors()
        assert any("confidence" in str(e.get("loc", [])) for e in errors)

    def test_execution_time_ms_valid_range(self) -> None:
        """Test that execution_time_ms accepts valid values (>= 0)."""
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
            execution_time_ms=0.0,
        )
        assert event.execution_time_ms == 0.0

        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
            execution_time_ms=1000.5,
        )
        assert event.execution_time_ms == 1000.5

    def test_execution_time_ms_negative_rejected(self) -> None:
        """Test that negative execution_time_ms is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStoredEvent(
                session_ref="session-123",
                intent_category="debugging",
                execution_time_ms=-1.0,
            )

        errors = exc_info.value.errors()
        assert any("execution_time_ms" in str(e.get("loc", [])) for e in errors)

    def test_status_valid_values(self) -> None:
        """Test that status accepts valid literal values."""
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
            status="success",
        )
        assert event.status == "success"

        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
            status="error",
        )
        assert event.status == "error"

    def test_status_invalid_value_rejected(self) -> None:
        """Test that invalid status values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStoredEvent(
                session_ref="session-123",
                intent_category="debugging",
                status="invalid_status",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any("status" in str(e.get("loc", [])) for e in errors)

    def test_session_ref_min_length(self) -> None:
        """Test that session_ref requires minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStoredEvent(
                session_ref="",
                intent_category="debugging",
            )

        errors = exc_info.value.errors()
        assert any("session_ref" in str(e.get("loc", [])) for e in errors)

    def test_intent_category_min_length(self) -> None:
        """Test that intent_category requires minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStoredEvent(
                session_ref="session-123",
                intent_category="",
            )

        errors = exc_info.value.errors()
        assert any("intent_category" in str(e.get("loc", [])) for e in errors)


# ============================================================================
# Tests for Datetime Handling
# ============================================================================


@pytest.mark.unit
class TestModelIntentStoredEventDatetime:
    """Test ModelIntentStoredEvent datetime handling."""

    def test_stored_at_is_utc_aware(self) -> None:
        """Test that stored_at is timezone-aware with UTC timezone."""
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
        )

        assert event.stored_at.tzinfo is not None
        assert event.stored_at.tzinfo == UTC

    def test_timestamp_is_utc_aware(self) -> None:
        """Test that timestamp (from base class) is UTC-aware."""
        event = ModelIntentStoredEvent(
            session_ref="session-123",
            intent_category="debugging",
        )

        assert event.timestamp.tzinfo is not None
        assert event.timestamp.tzinfo == UTC


# ============================================================================
# Tests for Serialization
# ============================================================================


@pytest.mark.unit
class TestModelIntentStoredEventSerialization:
    """Test ModelIntentStoredEvent serialization."""

    def test_model_dump_includes_all_fields(self) -> None:
        """Test that model_dump includes all fields."""
        event = ModelIntentStoredEvent(
            session_ref="session-dump-test",
            intent_category="serialization",
        )

        data = event.model_dump()

        assert "event_type" in data
        assert "intent_id" in data
        assert "session_ref" in data
        assert "intent_category" in data
        assert "confidence" in data
        assert "keywords" in data
        assert "created" in data
        assert "stored_at" in data
        assert "execution_time_ms" in data
        assert "status" in data
        assert "error_message" in data
        # Base class fields
        assert "event_id" in data
        assert "timestamp" in data
        assert "correlation_id" in data

    def test_model_dump_json_serializable(self) -> None:
        """Test that model can be serialized to JSON."""
        event = ModelIntentStoredEvent(
            session_ref="session-json-test",
            intent_category="json_serialization",
        )

        json_str = event.model_dump_json()

        assert isinstance(json_str, str)
        assert "session-json-test" in json_str
        assert "json_serialization" in json_str
        assert INTENT_STORED_EVENT in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test that model can be validated from dict."""
        intent_id = uuid4()
        data = {
            "intent_id": str(intent_id),
            "session_ref": "session-from-dict",
            "intent_category": "testing",
            "confidence": 0.75,
            "keywords": ["unit", "test"],
            "status": "success",
        }

        event = ModelIntentStoredEvent.model_validate(data)

        assert event.session_ref == "session-from-dict"
        assert event.intent_category == "testing"
        assert event.confidence == 0.75
        assert event.status == "success"
