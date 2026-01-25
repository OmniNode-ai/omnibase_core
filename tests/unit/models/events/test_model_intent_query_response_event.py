"""Tests for ModelIntentQueryResponseEvent model.

This module tests the event model for intent query responses published
after retrieving intent data from the graph database.

Test Coverage:
    - Basic instantiation with required fields
    - Default values for optional fields
    - Factory method create_distribution_response()
    - Factory method create_session_response()
    - Factory method create_recent_response()
    - Factory method from_error()
    - Field validation (total_count, total_intents, time_range_hours)
    - Status literal validation
    - Integration with IntentRecordPayload
    - Serialization

Created: 2025-01-25
PR Coverage: OMN-1513 Intent Storage Event Models
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.model_intent_query_response_event import (
    INTENT_QUERY_RESPONSE_EVENT,
    ModelIntentQueryResponseEvent,
)
from omnibase_core.models.events.model_intent_record_payload import (
    IntentRecordPayload,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_query_id() -> UUID:
    """Create a sample query ID."""
    return uuid4()


@pytest.fixture
def sample_correlation_id() -> UUID:
    """Create a sample correlation ID."""
    return uuid4()


@pytest.fixture
def sample_intent_payload() -> IntentRecordPayload:
    """Create a sample intent record payload."""
    return IntentRecordPayload(
        intent_id=uuid4(),
        session_ref="session-test-123",
        intent_category="code_generation",
        confidence=0.85,
        keywords=["python", "testing"],
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_intent_payloads() -> list[IntentRecordPayload]:
    """Create a list of sample intent record payloads."""
    return [
        IntentRecordPayload(
            intent_id=uuid4(),
            session_ref="session-1",
            intent_category="debugging",
            confidence=0.9,
            keywords=["debug", "error"],
            created_at=datetime.now(UTC),
        ),
        IntentRecordPayload(
            intent_id=uuid4(),
            session_ref="session-2",
            intent_category="code_review",
            confidence=0.75,
            keywords=["review", "pr"],
            created_at=datetime.now(UTC),
        ),
    ]


# ============================================================================
# Tests for Basic Instantiation
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryResponseEventBasic:
    """Test ModelIntentQueryResponseEvent basic creation and validation."""

    def test_event_creation_minimal(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test creating event with minimal required fields."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
        )

        assert event.query_id == sample_query_id
        assert event.query_type == "distribution"
        # Check defaults
        assert event.event_type == INTENT_QUERY_RESPONSE_EVENT
        assert event.status == "success"
        assert event.distribution == {}
        assert event.intents == []
        assert event.total_count == 0
        assert event.total_intents == 0
        assert event.time_range_hours == 24
        assert event.execution_time_ms == 0.0
        assert isinstance(event.responded_at, datetime)
        assert event.error_message is None

    def test_event_creation_all_fields(
        self,
        sample_query_id: UUID,
        sample_correlation_id: UUID,
        sample_intent_payloads: list[IntentRecordPayload],
    ) -> None:
        """Test creating event with all fields specified."""
        responded_at = datetime.now(UTC)

        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="session",
            status="success",
            distribution={"debugging": 5, "code_generation": 3},
            intents=sample_intent_payloads,
            total_count=8,
            total_intents=8,
            time_range_hours=48,
            execution_time_ms=25.5,
            responded_at=responded_at,
            correlation_id=sample_correlation_id,
        )

        assert event.query_id == sample_query_id
        assert event.query_type == "session"
        assert event.status == "success"
        assert event.distribution == {"debugging": 5, "code_generation": 3}
        assert len(event.intents) == 2
        assert event.total_count == 8
        assert event.total_intents == 8
        assert event.time_range_hours == 48
        assert event.execution_time_ms == 25.5
        assert event.responded_at == responded_at
        assert event.correlation_id == sample_correlation_id

    def test_event_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResponseEvent()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        required_fields = {"query_id", "query_type"}
        error_locs = {str(e["loc"][0]) for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(error_locs)

    def test_event_extra_fields_forbidden(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="distribution",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

    def test_event_type_constant(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that event_type matches the constant."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
        )

        assert event.event_type == "dev.omnimemory.intent.query.response.v1"
        assert event.event_type == INTENT_QUERY_RESPONSE_EVENT


# ============================================================================
# Tests for Factory Methods
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryResponseEventFactoryMethods:
    """Test ModelIntentQueryResponseEvent factory methods."""

    def test_create_distribution_response_minimal(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test create_distribution_response() with minimal arguments."""
        distribution = {"debugging": 10, "code_generation": 5, "testing": 3}

        event = ModelIntentQueryResponseEvent.create_distribution_response(
            query_id=sample_query_id,
            distribution=distribution,
        )

        assert event.query_id == sample_query_id
        assert event.query_type == "distribution"
        assert event.status == "success"
        assert event.distribution == distribution
        assert event.total_intents == 18  # Sum of values
        assert event.time_range_hours == 24

    def test_create_distribution_response_all_arguments(
        self,
        sample_query_id: UUID,
        sample_correlation_id: UUID,
    ) -> None:
        """Test create_distribution_response() with all arguments."""
        distribution = {"debugging": 7, "code_review": 4}

        event = ModelIntentQueryResponseEvent.create_distribution_response(
            query_id=sample_query_id,
            distribution=distribution,
            time_range_hours=72,
            execution_time_ms=15.3,
            correlation_id=sample_correlation_id,
        )

        assert event.query_id == sample_query_id
        assert event.query_type == "distribution"
        assert event.status == "success"
        assert event.distribution == distribution
        assert event.total_intents == 11
        assert event.time_range_hours == 72
        assert event.execution_time_ms == 15.3
        assert event.correlation_id == sample_correlation_id

    def test_create_distribution_response_empty_distribution(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test create_distribution_response() with empty distribution."""
        event = ModelIntentQueryResponseEvent.create_distribution_response(
            query_id=sample_query_id,
            distribution={},
        )

        assert event.distribution == {}
        assert event.total_intents == 0

    def test_create_session_response_with_intents(
        self,
        sample_query_id: UUID,
        sample_intent_payloads: list[IntentRecordPayload],
        sample_correlation_id: UUID,
    ) -> None:
        """Test create_session_response() with intents."""
        event = ModelIntentQueryResponseEvent.create_session_response(
            query_id=sample_query_id,
            intents=sample_intent_payloads,
            execution_time_ms=20.1,
            correlation_id=sample_correlation_id,
        )

        assert event.query_id == sample_query_id
        assert event.query_type == "session"
        assert event.status == "success"
        assert len(event.intents) == 2
        assert event.total_count == 2
        assert event.execution_time_ms == 20.1
        assert event.correlation_id == sample_correlation_id

    def test_create_session_response_empty_intents(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test create_session_response() with empty intents returns no_results status."""
        event = ModelIntentQueryResponseEvent.create_session_response(
            query_id=sample_query_id,
            intents=[],
        )

        assert event.query_type == "session"
        assert event.status == "no_results"
        assert event.intents == []
        assert event.total_count == 0

    def test_create_recent_response_with_intents(
        self,
        sample_query_id: UUID,
        sample_intent_payloads: list[IntentRecordPayload],
        sample_correlation_id: UUID,
    ) -> None:
        """Test create_recent_response() with intents."""
        event = ModelIntentQueryResponseEvent.create_recent_response(
            query_id=sample_query_id,
            intents=sample_intent_payloads,
            time_range_hours=6,
            execution_time_ms=12.5,
            correlation_id=sample_correlation_id,
        )

        assert event.query_id == sample_query_id
        assert event.query_type == "recent"
        assert event.status == "success"
        assert len(event.intents) == 2
        assert event.total_count == 2
        assert event.time_range_hours == 6
        assert event.execution_time_ms == 12.5
        assert event.correlation_id == sample_correlation_id

    def test_create_recent_response_empty_intents(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test create_recent_response() with empty intents returns no_results status."""
        event = ModelIntentQueryResponseEvent.create_recent_response(
            query_id=sample_query_id,
            intents=[],
        )

        assert event.query_type == "recent"
        assert event.status == "no_results"
        assert event.intents == []
        assert event.total_count == 0

    def test_from_error_distribution(
        self,
        sample_query_id: UUID,
        sample_correlation_id: UUID,
    ) -> None:
        """Test from_error() for distribution query."""
        event = ModelIntentQueryResponseEvent.from_error(
            query_id=sample_query_id,
            query_type="distribution",
            error_message="Database connection timeout",
            correlation_id=sample_correlation_id,
        )

        assert event.query_id == sample_query_id
        assert event.query_type == "distribution"
        assert event.status == "error"
        assert event.error_message == "Database connection timeout"
        assert event.correlation_id == sample_correlation_id

    def test_from_error_session(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test from_error() for session query."""
        event = ModelIntentQueryResponseEvent.from_error(
            query_id=sample_query_id,
            query_type="session",
            error_message="Session not found",
        )

        assert event.query_type == "session"
        assert event.status == "error"
        assert event.error_message == "Session not found"

    def test_from_error_recent(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test from_error() for recent query."""
        event = ModelIntentQueryResponseEvent.from_error(
            query_id=sample_query_id,
            query_type="recent",
            error_message="Query timeout exceeded",
        )

        assert event.query_type == "recent"
        assert event.status == "error"
        assert event.error_message == "Query timeout exceeded"


# ============================================================================
# Tests for Field Validation
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryResponseEventValidation:
    """Test ModelIntentQueryResponseEvent field validation."""

    def test_query_type_valid_values(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that query_type accepts valid literal values."""
        for query_type in ["distribution", "session", "recent"]:
            event = ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type=query_type,  # type: ignore[arg-type]
            )
            assert event.query_type == query_type

    def test_query_type_invalid_value_rejected(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that invalid query_type values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="invalid_type",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any("query_type" in str(e.get("loc", [])) for e in errors)

    def test_status_valid_values(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that status accepts valid literal values."""
        for status in ["success", "error", "not_found", "no_results"]:
            event = ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="distribution",
                status=status,  # type: ignore[arg-type]
            )
            assert event.status == status

    def test_status_invalid_value_rejected(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that invalid status values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="distribution",
                status="invalid_status",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any("status" in str(e.get("loc", [])) for e in errors)

    def test_total_count_valid_range(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that total_count accepts valid values (>= 0)."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            total_count=0,
        )
        assert event.total_count == 0

        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            total_count=1000,
        )
        assert event.total_count == 1000

    def test_total_count_negative_rejected(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that negative total_count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="distribution",
                total_count=-1,
            )

        errors = exc_info.value.errors()
        assert any("total_count" in str(e.get("loc", [])) for e in errors)

    def test_total_intents_valid_range(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that total_intents accepts valid values (>= 0)."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            total_intents=0,
        )
        assert event.total_intents == 0

    def test_total_intents_negative_rejected(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that negative total_intents is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="distribution",
                total_intents=-1,
            )

        errors = exc_info.value.errors()
        assert any("total_intents" in str(e.get("loc", [])) for e in errors)

    def test_time_range_hours_valid_range(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that time_range_hours accepts valid values (>= 1)."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            time_range_hours=1,
        )
        assert event.time_range_hours == 1

        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            time_range_hours=720,
        )
        assert event.time_range_hours == 720

    def test_time_range_hours_below_minimum_rejected(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that time_range_hours below 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="distribution",
                time_range_hours=0,
            )

        errors = exc_info.value.errors()
        assert any("time_range_hours" in str(e.get("loc", [])) for e in errors)

    def test_execution_time_ms_valid_range(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that execution_time_ms accepts valid values (>= 0)."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            execution_time_ms=0.0,
        )
        assert event.execution_time_ms == 0.0

        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            execution_time_ms=500.5,
        )
        assert event.execution_time_ms == 500.5

    def test_execution_time_ms_negative_rejected(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that negative execution_time_ms is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="distribution",
                execution_time_ms=-1.0,
            )

        errors = exc_info.value.errors()
        assert any("execution_time_ms" in str(e.get("loc", [])) for e in errors)


# ============================================================================
# Tests for Datetime Handling
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryResponseEventDatetime:
    """Test ModelIntentQueryResponseEvent datetime handling."""

    def test_responded_at_is_utc_aware(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that responded_at is timezone-aware with UTC timezone."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
        )

        assert event.responded_at.tzinfo is not None
        assert event.responded_at.tzinfo == UTC

    def test_timestamp_is_utc_aware(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that timestamp (from base class) is UTC-aware."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
        )

        assert event.timestamp.tzinfo is not None
        assert event.timestamp.tzinfo == UTC


# ============================================================================
# Tests for Integration with IntentRecordPayload
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryResponseEventIntegration:
    """Test ModelIntentQueryResponseEvent integration with IntentRecordPayload."""

    def test_intents_field_accepts_payload_list(
        self,
        sample_query_id: UUID,
        sample_intent_payloads: list[IntentRecordPayload],
    ) -> None:
        """Test that intents field accepts list of IntentRecordPayload."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="session",
            intents=sample_intent_payloads,
        )

        assert len(event.intents) == 2
        assert all(isinstance(i, IntentRecordPayload) for i in event.intents)

    def test_intents_field_validates_payload_structure(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that intents field validates payload structure."""
        # Invalid payload structure should raise ValidationError
        with pytest.raises(ValidationError):
            ModelIntentQueryResponseEvent(
                query_id=sample_query_id,
                query_type="session",
                intents=[{"invalid": "payload"}],  # Missing required fields
            )

    def test_intents_from_dict_validation(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that intents can be validated from dict representation."""
        intent_data = {
            "intent_id": str(uuid4()),
            "session_ref": "session-dict-test",
            "intent_category": "testing",
            "confidence": 0.8,
            "keywords": ["test"],
            "created_at": datetime.now(UTC).isoformat(),
        }

        event = ModelIntentQueryResponseEvent.model_validate(
            {
                "query_id": str(sample_query_id),
                "query_type": "session",
                "intents": [intent_data],
            }
        )

        assert len(event.intents) == 1
        assert event.intents[0].session_ref == "session-dict-test"


# ============================================================================
# Tests for Serialization
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryResponseEventSerialization:
    """Test ModelIntentQueryResponseEvent serialization."""

    def test_model_dump_includes_all_fields(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that model_dump includes all fields."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
        )

        data = event.model_dump()

        assert "event_type" in data
        assert "query_id" in data
        assert "query_type" in data
        assert "status" in data
        assert "distribution" in data
        assert "intents" in data
        assert "total_count" in data
        assert "total_intents" in data
        assert "time_range_hours" in data
        assert "execution_time_ms" in data
        assert "responded_at" in data
        assert "error_message" in data
        # Base class fields
        assert "event_id" in data
        assert "timestamp" in data
        assert "correlation_id" in data

    def test_model_dump_json_serializable(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that model can be serialized to JSON."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="distribution",
            distribution={"debugging": 5, "testing": 3},
        )

        json_str = event.model_dump_json()

        assert isinstance(json_str, str)
        assert "distribution" in json_str
        assert "debugging" in json_str
        assert INTENT_QUERY_RESPONSE_EVENT in json_str

    def test_model_dump_json_with_intents(
        self,
        sample_query_id: UUID,
        sample_intent_payloads: list[IntentRecordPayload],
    ) -> None:
        """Test JSON serialization with nested intents."""
        event = ModelIntentQueryResponseEvent(
            query_id=sample_query_id,
            query_type="session",
            intents=sample_intent_payloads,
        )

        json_str = event.model_dump_json()

        assert isinstance(json_str, str)
        assert "intents" in json_str
        assert "debugging" in json_str  # From first intent category
        assert "code_review" in json_str  # From second intent category

    def test_model_validate_from_dict(
        self,
        sample_query_id: UUID,
    ) -> None:
        """Test that model can be validated from dict."""
        data = {
            "query_id": str(sample_query_id),
            "query_type": "distribution",
            "status": "success",
            "distribution": {"debugging": 10, "testing": 5},
            "total_intents": 15,
        }

        event = ModelIntentQueryResponseEvent.model_validate(data)

        assert event.query_type == "distribution"
        assert event.status == "success"
        assert event.distribution == {"debugging": 10, "testing": 5}
        assert event.total_intents == 15
