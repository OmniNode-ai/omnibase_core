# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelIntentQueryRequestedEvent model.

This module tests the event model for intent query requests from clients
such as dashboards that query intent data via the event bus.

Test Coverage:
    - Basic instantiation with required fields
    - Default values for optional fields
    - Factory method create_distribution_query()
    - Factory method create_session_query()
    - Factory method create_recent_query()
    - Field validation (time_range_hours, min_confidence, limit)
    - Query type literal validation
    - Serialization

Created: 2025-01-25
PR Coverage: OMN-1513 Intent Storage Event Models
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.model_intent_query_requested_event import (
    ModelIntentQueryRequestedEvent,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_correlation_id() -> UUID:
    """Create a sample correlation ID."""
    return uuid4()


# ============================================================================
# Tests for Basic Instantiation
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryRequestedEventBasic:
    """Test ModelIntentQueryRequestedEvent basic creation and validation."""

    def test_event_creation_minimal(self) -> None:
        """Test creating event with minimal required fields."""
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
        )

        assert event.query_type == "distribution"
        # Check defaults
        assert event.event_type == "onex.omnimemory.intent.query.requested.v1"
        assert isinstance(event.query_id, UUID)
        assert event.session_ref is None
        assert event.time_range_hours == 24
        assert event.min_confidence == 0.0
        assert event.limit == 100
        assert event.requester_name == "unknown"
        assert isinstance(event.requested_at, datetime)

    def test_event_creation_all_fields(
        self,
        sample_correlation_id: UUID,
    ) -> None:
        """Test creating event with all fields specified."""
        query_id = uuid4()
        requested_at = datetime.now(UTC)

        event = ModelIntentQueryRequestedEvent(
            query_id=query_id,
            query_type="session",
            session_ref="session-target",
            time_range_hours=48,
            min_confidence=0.5,
            limit=200,
            requester_name="omnidash",
            requested_at=requested_at,
            correlation_id=sample_correlation_id,
        )

        assert event.query_id == query_id
        assert event.query_type == "session"
        assert event.session_ref == "session-target"
        assert event.time_range_hours == 48
        assert event.min_confidence == 0.5
        assert event.limit == 200
        assert event.requester_name == "omnidash"
        assert event.requested_at == requested_at
        assert event.correlation_id == sample_correlation_id

    def test_event_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        error_locs = {str(e["loc"][0]) for e in errors if e["type"] == "missing"}
        assert "query_type" in error_locs

    def test_event_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelIntentQueryRequestedEvent(
                query_type="distribution",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

    def test_event_type_constant(self) -> None:
        """Test that event_type matches the constant."""
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
        )

        assert event.event_type == "onex.omnimemory.intent.query.requested.v1"


# ============================================================================
# Tests for Factory Methods
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryRequestedEventFactoryMethods:
    """Test ModelIntentQueryRequestedEvent factory methods."""

    def test_create_distribution_query_minimal(self) -> None:
        """Test create_distribution_query() with minimal arguments."""
        event = ModelIntentQueryRequestedEvent.create_distribution_query()

        assert event.query_type == "distribution"
        assert event.time_range_hours == 24
        assert event.min_confidence == 0.0
        assert event.requester_name == "omnidash"
        assert isinstance(event.query_id, UUID)

    def test_create_distribution_query_all_arguments(
        self,
        sample_correlation_id: UUID,
    ) -> None:
        """Test create_distribution_query() with all arguments."""
        event = ModelIntentQueryRequestedEvent.create_distribution_query(
            time_range_hours=72,
            min_confidence=0.7,
            requester_name="analytics_service",
            correlation_id=sample_correlation_id,
        )

        assert event.query_type == "distribution"
        assert event.time_range_hours == 72
        assert event.min_confidence == 0.7
        assert event.requester_name == "analytics_service"
        assert event.correlation_id == sample_correlation_id

    def test_create_session_query_minimal(self) -> None:
        """Test create_session_query() with minimal arguments."""
        event = ModelIntentQueryRequestedEvent.create_session_query(
            session_ref="session-query-target",
        )

        assert event.query_type == "session"
        assert event.session_ref == "session-query-target"
        assert event.min_confidence == 0.0
        assert event.limit == 100
        assert event.requester_name == "omnidash"

    def test_create_session_query_all_arguments(
        self,
        sample_correlation_id: UUID,
    ) -> None:
        """Test create_session_query() with all arguments."""
        event = ModelIntentQueryRequestedEvent.create_session_query(
            session_ref="session-full-query",
            min_confidence=0.6,
            limit=50,
            requester_name="session_analyzer",
            correlation_id=sample_correlation_id,
        )

        assert event.query_type == "session"
        assert event.session_ref == "session-full-query"
        assert event.min_confidence == 0.6
        assert event.limit == 50
        assert event.requester_name == "session_analyzer"
        assert event.correlation_id == sample_correlation_id

    def test_create_recent_query_minimal(self) -> None:
        """Test create_recent_query() with minimal arguments."""
        event = ModelIntentQueryRequestedEvent.create_recent_query()

        assert event.query_type == "recent"
        assert event.time_range_hours == 1
        assert event.min_confidence == 0.0
        assert event.limit == 50
        assert event.requester_name == "omnidash"

    def test_create_recent_query_all_arguments(
        self,
        sample_correlation_id: UUID,
    ) -> None:
        """Test create_recent_query() with all arguments."""
        event = ModelIntentQueryRequestedEvent.create_recent_query(
            time_range_hours=6,
            min_confidence=0.8,
            limit=25,
            requester_name="realtime_dashboard",
            correlation_id=sample_correlation_id,
        )

        assert event.query_type == "recent"
        assert event.time_range_hours == 6
        assert event.min_confidence == 0.8
        assert event.limit == 25
        assert event.requester_name == "realtime_dashboard"
        assert event.correlation_id == sample_correlation_id


# ============================================================================
# Tests for Field Validation
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryRequestedEventValidation:
    """Test ModelIntentQueryRequestedEvent field validation."""

    def test_query_type_valid_values(self) -> None:
        """Test that query_type accepts valid literal values."""
        for query_type in ["distribution", "session", "recent"]:
            event = ModelIntentQueryRequestedEvent(
                query_type=query_type,  # type: ignore[arg-type]
            )
            assert event.query_type == query_type

    def test_query_type_invalid_value_rejected(self) -> None:
        """Test that invalid query_type values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent(
                query_type="invalid_type",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any("query_type" in str(e.get("loc", [])) for e in errors)

    def test_time_range_hours_valid_range(self) -> None:
        """Test that time_range_hours accepts valid values (1-720)."""
        # Minimum value
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
            time_range_hours=1,
        )
        assert event.time_range_hours == 1

        # Maximum value (30 days)
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
            time_range_hours=720,
        )
        assert event.time_range_hours == 720

    def test_time_range_hours_below_minimum_rejected(self) -> None:
        """Test that time_range_hours below 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent(
                query_type="distribution",
                time_range_hours=0,
            )

        errors = exc_info.value.errors()
        assert any("time_range_hours" in str(e.get("loc", [])) for e in errors)

    def test_time_range_hours_above_maximum_rejected(self) -> None:
        """Test that time_range_hours above 720 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent(
                query_type="distribution",
                time_range_hours=721,
            )

        errors = exc_info.value.errors()
        assert any("time_range_hours" in str(e.get("loc", [])) for e in errors)

    def test_min_confidence_valid_range(self) -> None:
        """Test that min_confidence accepts valid values (0.0-1.0)."""
        # Minimum value
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
            min_confidence=0.0,
        )
        assert event.min_confidence == 0.0

        # Maximum value
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
            min_confidence=1.0,
        )
        assert event.min_confidence == 1.0

    def test_min_confidence_below_minimum_rejected(self) -> None:
        """Test that min_confidence below 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent(
                query_type="distribution",
                min_confidence=-0.1,
            )

        errors = exc_info.value.errors()
        assert any("min_confidence" in str(e.get("loc", [])) for e in errors)

    def test_min_confidence_above_maximum_rejected(self) -> None:
        """Test that min_confidence above 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent(
                query_type="distribution",
                min_confidence=1.1,
            )

        errors = exc_info.value.errors()
        assert any("min_confidence" in str(e.get("loc", [])) for e in errors)

    def test_limit_valid_range(self) -> None:
        """Test that limit accepts valid values (1-1000)."""
        # Minimum value
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
            limit=1,
        )
        assert event.limit == 1

        # Maximum value
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
            limit=1000,
        )
        assert event.limit == 1000

    def test_limit_below_minimum_rejected(self) -> None:
        """Test that limit below 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent(
                query_type="distribution",
                limit=0,
            )

        errors = exc_info.value.errors()
        assert any("limit" in str(e.get("loc", [])) for e in errors)

    def test_limit_above_maximum_rejected(self) -> None:
        """Test that limit above 1000 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryRequestedEvent(
                query_type="distribution",
                limit=1001,
            )

        errors = exc_info.value.errors()
        assert any("limit" in str(e.get("loc", [])) for e in errors)


# ============================================================================
# Tests for Datetime Handling
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryRequestedEventDatetime:
    """Test ModelIntentQueryRequestedEvent datetime handling."""

    def test_requested_at_is_utc_aware(self) -> None:
        """Test that requested_at is timezone-aware with UTC timezone."""
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
        )

        assert event.requested_at.tzinfo is not None
        assert event.requested_at.tzinfo == UTC

    def test_timestamp_is_utc_aware(self) -> None:
        """Test that timestamp (from base class) is UTC-aware."""
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
        )

        assert event.timestamp.tzinfo is not None
        assert event.timestamp.tzinfo == UTC


# ============================================================================
# Tests for Serialization
# ============================================================================


@pytest.mark.unit
class TestModelIntentQueryRequestedEventSerialization:
    """Test ModelIntentQueryRequestedEvent serialization."""

    def test_model_dump_includes_all_fields(self) -> None:
        """Test that model_dump includes all fields."""
        event = ModelIntentQueryRequestedEvent(
            query_type="distribution",
        )

        data = event.model_dump()

        assert "event_type" in data
        assert "query_id" in data
        assert "query_type" in data
        assert "session_ref" in data
        assert "time_range_hours" in data
        assert "min_confidence" in data
        assert "limit" in data
        assert "requester_name" in data
        assert "requested_at" in data
        # Base class fields
        assert "event_id" in data
        assert "timestamp" in data
        assert "correlation_id" in data

    def test_model_dump_json_serializable(self) -> None:
        """Test that model can be serialized to JSON."""
        event = ModelIntentQueryRequestedEvent(
            query_type="session",
            session_ref="session-json-test",
            requester_name="json_test_client",
        )

        json_str = event.model_dump_json()

        assert isinstance(json_str, str)
        assert "session-json-test" in json_str
        assert "json_test_client" in json_str
        assert "onex.omnimemory.intent.query.requested.v1" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test that model can be validated from dict."""
        query_id = uuid4()
        data = {
            "query_id": str(query_id),
            "query_type": "recent",
            "time_range_hours": 6,
            "min_confidence": 0.5,
            "limit": 50,
            "requester_name": "test_client",
        }

        event = ModelIntentQueryRequestedEvent.model_validate(data)

        assert event.query_type == "recent"
        assert event.time_range_hours == 6
        assert event.min_confidence == 0.5
        assert event.limit == 50
        assert event.requester_name == "test_client"
