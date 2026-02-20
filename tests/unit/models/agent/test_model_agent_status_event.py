# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelAgentStatusEvent (OMN-1847)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_state import EnumAgentState
from omnibase_core.models.agent.model_agent_status_event import ModelAgentStatusEvent


def _make_event(**kwargs: object) -> ModelAgentStatusEvent:
    """Create a minimal valid ModelAgentStatusEvent with overridable fields."""
    defaults: dict[str, object] = {
        "correlation_id": uuid4(),
        "agent_name": "test-agent",
        "session_id": "session-abc",
        "state": EnumAgentState.IDLE,
        "message": "Agent is idle.",
        "created_at": datetime(2026, 2, 20, 12, 0, 0, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return ModelAgentStatusEvent(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelAgentStatusEventMinimal:
    """Tests for minimal construction and required fields."""

    def test_minimal_valid_event(self) -> None:
        """Test that a minimal event can be constructed with required fields."""
        event = _make_event()
        assert event.agent_name == "test-agent"
        assert event.session_id == "session-abc"
        assert event.state == EnumAgentState.IDLE
        assert event.message == "Agent is idle."
        assert event.status_schema_version == 1
        assert event.progress is None
        assert event.current_phase is None
        assert event.current_task is None
        assert event.blocking_reason is None
        assert event.metadata == {}

    def test_id_auto_generated(self) -> None:
        """Test that id is auto-generated as a UUID."""
        event = _make_event()
        assert isinstance(event.id, UUID)

    def test_two_events_have_different_ids(self) -> None:
        """Test that two independently created events have different IDs."""
        e1 = _make_event()
        e2 = _make_event()
        assert e1.id != e2.id

    def test_missing_correlation_id_raises(self) -> None:
        """Test that omitting correlation_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentStatusEvent(
                agent_name="agent",
                session_id="s",
                state=EnumAgentState.IDLE,
                message="msg",
                created_at=datetime.now(tz=UTC),
            )
        assert "correlation_id" in str(exc_info.value)

    def test_missing_agent_name_raises(self) -> None:
        """Test that omitting agent_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentStatusEvent(
                correlation_id=uuid4(),
                session_id="s",
                state=EnumAgentState.IDLE,
                message="msg",
                created_at=datetime.now(tz=UTC),
            )
        assert "agent_name" in str(exc_info.value)

    def test_missing_created_at_raises(self) -> None:
        """Test that omitting created_at raises (no default supplied)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentStatusEvent(
                correlation_id=uuid4(),
                agent_name="agent",
                session_id="s",
                state=EnumAgentState.IDLE,
                message="msg",
            )
        assert "created_at" in str(exc_info.value)

    def test_extra_fields_raise(self) -> None:
        """Test that extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError):
            _make_event(unknown_field="oops")  # type: ignore[call-overload]


@pytest.mark.unit
class TestModelAgentStatusEventFrozen:
    """Tests for immutability guarantees."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Test that the frozen model raises on attribute assignment."""
        event = _make_event()
        with pytest.raises(ValidationError):
            event.agent_name = "modified"  # type: ignore[misc]

    def test_frozen_model_rejects_state_mutation(self) -> None:
        """Test that the frozen model rejects state mutation."""
        event = _make_event()
        with pytest.raises(ValidationError):
            event.state = EnumAgentState.ERROR  # type: ignore[misc]


@pytest.mark.unit
class TestModelAgentStatusEventStates:
    """Tests for state field behavior."""

    def test_all_states_are_accepted(self) -> None:
        """Test that each EnumAgentState value is accepted."""
        for state in EnumAgentState:
            event = _make_event(state=state)
            assert event.state == state

    def test_invalid_state_raises(self) -> None:
        """Test that an invalid state string raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_event(state="not_a_valid_state")  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelAgentStatusEventProgress:
    """Tests for progress field validation."""

    def test_progress_zero(self) -> None:
        """Test that progress=0.0 is valid."""
        event = _make_event(progress=0.0)
        assert event.progress == 0.0

    def test_progress_one(self) -> None:
        """Test that progress=1.0 is valid."""
        event = _make_event(progress=1.0)
        assert event.progress == 1.0

    def test_progress_midpoint(self) -> None:
        """Test that progress=0.5 is valid."""
        event = _make_event(progress=0.5)
        assert event.progress == 0.5

    def test_progress_below_zero_raises(self) -> None:
        """Test that progress < 0.0 raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            _make_event(progress=-0.01)
        assert "progress" in str(exc_info.value)

    def test_progress_above_one_raises(self) -> None:
        """Test that progress > 1.0 raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            _make_event(progress=1.01)
        assert "progress" in str(exc_info.value)

    def test_progress_none_is_default(self) -> None:
        """Test that progress defaults to None."""
        event = _make_event()
        assert event.progress is None


@pytest.mark.unit
class TestModelAgentStatusEventMetadata:
    """Tests for metadata field."""

    def test_metadata_defaults_to_empty_dict(self) -> None:
        """Test that metadata defaults to an empty dict."""
        event = _make_event()
        assert event.metadata == {}

    def test_metadata_accepts_arbitrary_keys(self) -> None:
        """Test that metadata accepts arbitrary string-keyed pairs."""
        meta = {"trace_id": "abc123", "region": "us-west-2", "retry_count": 3}
        event = _make_event(metadata=meta)
        assert event.metadata["trace_id"] == "abc123"
        assert event.metadata["retry_count"] == 3


@pytest.mark.unit
class TestModelAgentStatusEventSchemaVersion:
    """Tests for schema version field."""

    def test_default_schema_version_is_one(self) -> None:
        """Test that schema_version defaults to 1."""
        event = _make_event()
        assert event.status_schema_version == 1

    def test_custom_schema_version(self) -> None:
        """Test that a custom schema_version is accepted."""
        event = _make_event(status_schema_version=2)
        assert event.status_schema_version == 2

    def test_schema_version_below_one_raises(self) -> None:
        """Test that schema_version < 1 raises ValidationError (ge=1 constraint)."""
        with pytest.raises(ValidationError):
            _make_event(status_schema_version=0)


@pytest.mark.unit
class TestModelAgentStatusEventSerialization:
    """Tests for model_dump and model_validate round-trip."""

    def test_model_dump_round_trip(self) -> None:
        """Test that model_dump produces data that can be validated back."""
        original = _make_event(state=EnumAgentState.WORKING, progress=0.42)
        dumped = original.model_dump()
        restored = ModelAgentStatusEvent.model_validate(dumped)
        assert restored.state == EnumAgentState.WORKING
        assert restored.progress == 0.42
        assert restored.id == original.id
        assert restored.agent_name == original.agent_name

    def test_model_dump_mode_json(self) -> None:
        """Test that model_dump(mode='json') produces JSON-serializable data."""
        import json

        event = _make_event(state=EnumAgentState.FINISHED)
        dumped = event.model_dump(mode="json")
        json_str = json.dumps(dumped)
        assert '"finished"' in json_str
