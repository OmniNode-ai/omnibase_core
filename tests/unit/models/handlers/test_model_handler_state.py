# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelHandlerState and EnumHandlerStatus."""

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_status import EnumHandlerStatus
from omnibase_core.models.handlers.model_handler_state import ModelHandlerState


@pytest.mark.unit
class TestEnumHandlerStatus:
    """Tests for EnumHandlerStatus enum."""

    def test_all_required_values_exist(self) -> None:
        """Verify all four required status values are present."""
        assert EnumHandlerStatus.INITIALIZING
        assert EnumHandlerStatus.READY
        assert EnumHandlerStatus.DEGRADED
        assert EnumHandlerStatus.STOPPED

    def test_string_values(self) -> None:
        """Verify string values match lowercase names."""
        assert EnumHandlerStatus.INITIALIZING.value == "initializing"
        assert EnumHandlerStatus.READY.value == "ready"
        assert EnumHandlerStatus.DEGRADED.value == "degraded"
        assert EnumHandlerStatus.STOPPED.value == "stopped"

    def test_str_serialization(self) -> None:
        """Verify StrValueHelper provides correct __str__ output."""
        assert str(EnumHandlerStatus.READY) == "ready"
        assert str(EnumHandlerStatus.STOPPED) == "stopped"

    def test_is_terminal_only_stopped(self) -> None:
        """Only STOPPED is terminal."""
        assert EnumHandlerStatus.STOPPED.is_terminal() is True
        assert EnumHandlerStatus.INITIALIZING.is_terminal() is False
        assert EnumHandlerStatus.READY.is_terminal() is False
        assert EnumHandlerStatus.DEGRADED.is_terminal() is False

    def test_is_operational_excludes_stopped(self) -> None:
        """All statuses except STOPPED are operational."""
        assert EnumHandlerStatus.INITIALIZING.is_operational() is True
        assert EnumHandlerStatus.READY.is_operational() is True
        assert EnumHandlerStatus.DEGRADED.is_operational() is True
        assert EnumHandlerStatus.STOPPED.is_operational() is False

    def test_json_serialization_as_string(self) -> None:
        """Enum serializes to its string value in JSON context."""
        data = {"status": EnumHandlerStatus.READY}
        serialized = json.dumps(data, default=str)
        assert '"ready"' in serialized


@pytest.mark.unit
class TestModelHandlerStateInstantiation:
    """Tests for ModelHandlerState instantiation."""

    def test_minimal_instantiation(self) -> None:
        """Test creating model with only required fields."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.INITIALIZING,
        )

        assert state.handler_id == "onex:test-handler"
        assert state.handler_type == "test"
        assert state.status == EnumHandlerStatus.INITIALIZING
        assert state.initialized_at is None
        assert state.last_heartbeat_at is None
        assert state.error_count == 0
        assert state.last_error_message is None
        assert state.metadata == {}

    def test_full_instantiation(self) -> None:
        """Test creating model with all fields populated."""
        now = datetime.now(tz=UTC)

        state = ModelHandlerState(
            handler_id="onex:postgres-handler",
            handler_type="postgres",
            status=EnumHandlerStatus.READY,
            initialized_at=now,
            last_heartbeat_at=now,
            error_count=3,
            last_error_message="Connection timeout on retry 3",
            metadata={"region": "us-east-1", "pool_size": "10"},
        )

        assert state.handler_id == "onex:postgres-handler"
        assert state.handler_type == "postgres"
        assert state.status == EnumHandlerStatus.READY
        assert state.initialized_at == now
        assert state.last_heartbeat_at == now
        assert state.error_count == 3
        assert state.last_error_message == "Connection timeout on retry 3"
        assert state.metadata == {"region": "us-east-1", "pool_size": "10"}

    def test_all_status_values_accepted(self) -> None:
        """Test that all EnumHandlerStatus values are accepted."""
        for status in EnumHandlerStatus:
            state = ModelHandlerState(
                handler_id="onex:test-handler",
                handler_type="test",
                status=status,
            )
            assert state.status == status

    def test_status_string_coercion(self) -> None:
        """Test that string status values are coerced to enum."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status="ready",  # type: ignore[arg-type]
        )
        assert state.status == EnumHandlerStatus.READY

    def test_error_count_default_zero(self) -> None:
        """Verify error_count defaults to 0."""
        state = ModelHandlerState(
            handler_id="onex:x",
            handler_type="x",
            status=EnumHandlerStatus.READY,
        )
        assert state.error_count == 0

    def test_error_count_rejects_negative(self) -> None:
        """Verify negative error_count is rejected."""
        with pytest.raises(ValidationError):
            ModelHandlerState(
                handler_id="onex:x",
                handler_type="x",
                status=EnumHandlerStatus.READY,
                error_count=-1,
            )

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelHandlerState(
                handler_id="onex:x",
                handler_type="x",
                status=EnumHandlerStatus.READY,
                unknown_field="value",  # type: ignore[call-arg]
            )

    def test_missing_required_fields_rejected(self) -> None:
        """Verify missing required fields cause ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerState(  # type: ignore[call-arg]
                handler_type="test",
                status=EnumHandlerStatus.READY,
                # handler_id missing
            )


@pytest.mark.unit
class TestModelHandlerStateStatusTransitions:
    """Tests for field-level status transitions on ModelHandlerState."""

    def test_status_update_via_model_copy(self) -> None:
        """Verify status can be updated using model_copy."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.INITIALIZING,
        )
        ready_state = state.model_copy(update={"status": EnumHandlerStatus.READY})

        assert state.status == EnumHandlerStatus.INITIALIZING  # original unchanged
        assert ready_state.status == EnumHandlerStatus.READY

    def test_initializing_to_ready_transition(self) -> None:
        """Simulate INITIALIZING -> READY transition."""
        now = datetime.now(tz=UTC)
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.INITIALIZING,
        )
        ready_state = state.model_copy(
            update={"status": EnumHandlerStatus.READY, "initialized_at": now}
        )

        assert ready_state.status == EnumHandlerStatus.READY
        assert ready_state.initialized_at == now

    def test_ready_to_degraded_transition(self) -> None:
        """Simulate READY -> DEGRADED transition with error tracking."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.READY,
        )
        degraded_state = state.model_copy(
            update={
                "status": EnumHandlerStatus.DEGRADED,
                "error_count": 1,
                "last_error_message": "upstream timeout",
            }
        )

        assert degraded_state.status == EnumHandlerStatus.DEGRADED
        assert degraded_state.error_count == 1
        assert degraded_state.last_error_message == "upstream timeout"

    def test_degraded_to_stopped_transition(self) -> None:
        """Simulate DEGRADED -> STOPPED transition."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.DEGRADED,
            error_count=5,
        )
        stopped_state = state.model_copy(update={"status": EnumHandlerStatus.STOPPED})

        assert stopped_state.status == EnumHandlerStatus.STOPPED
        assert stopped_state.status.is_terminal() is True
        assert stopped_state.error_count == 5  # preserved from previous state


@pytest.mark.unit
class TestModelHandlerStateSerialization:
    """Tests for ModelHandlerState JSON serialization."""

    def test_model_dump_json_is_valid_json(self) -> None:
        """Verify model_dump_json() produces valid JSON."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.READY,
        )
        json_str = state.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_model_dump_json_contains_expected_fields(self) -> None:
        """Verify all fields appear in JSON output."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.READY,
        )
        parsed = json.loads(state.model_dump_json())

        assert "handler_id" in parsed
        assert "handler_type" in parsed
        assert "status" in parsed
        assert "initialized_at" in parsed
        assert "last_heartbeat_at" in parsed
        assert "error_count" in parsed
        assert "last_error_message" in parsed
        assert "metadata" in parsed

    def test_status_serializes_as_string(self) -> None:
        """Verify status enum serializes as its string value."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.READY,
        )
        parsed = json.loads(state.model_dump_json())
        assert parsed["status"] == "ready"

    def test_null_fields_serialize_as_null(self) -> None:
        """Verify optional None fields serialize as null."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.INITIALIZING,
        )
        parsed = json.loads(state.model_dump_json())
        assert parsed["initialized_at"] is None
        assert parsed["last_heartbeat_at"] is None
        assert parsed["last_error_message"] is None

    def test_roundtrip_serialization(self) -> None:
        """Verify model can be serialized and deserialized back faithfully."""
        now = datetime.now(tz=UTC)
        original = ModelHandlerState(
            handler_id="onex:postgres-handler",
            handler_type="postgres",
            status=EnumHandlerStatus.DEGRADED,
            initialized_at=now,
            error_count=2,
            last_error_message="retry limit exceeded",
            metadata={"shard": "primary"},
        )

        json_str = original.model_dump_json()
        restored = ModelHandlerState.model_validate_json(json_str)

        assert restored.handler_id == original.handler_id
        assert restored.handler_type == original.handler_type
        assert restored.status == original.status
        assert restored.error_count == original.error_count
        assert restored.last_error_message == original.last_error_message
        assert restored.metadata == original.metadata

    def test_model_dump_dict_serializable(self) -> None:
        """Verify model_dump() output is JSON-serializable with json.dumps."""
        state = ModelHandlerState(
            handler_id="onex:test-handler",
            handler_type="test",
            status=EnumHandlerStatus.READY,
            metadata={"env": "prod"},
        )
        dumped = state.model_dump(mode="json")
        json_str = json.dumps(dumped)
        parsed = json.loads(json_str)
        assert parsed["status"] == "ready"
        assert parsed["metadata"] == {"env": "prod"}


@pytest.mark.unit
class TestModelHandlerStatePublicApi:
    """Tests verifying ModelHandlerState is accessible via public API paths."""

    def test_import_from_models_handlers(self) -> None:
        """Verify ModelHandlerState is importable from models.handlers package."""
        from omnibase_core.models.handlers import ModelHandlerState

        state = ModelHandlerState(
            handler_id="onex:x",
            handler_type="x",
            status=EnumHandlerStatus.READY,
        )
        assert state.handler_id == "onex:x"

    def test_import_enum_from_enums_package(self) -> None:
        """Verify EnumHandlerStatus is importable from enums package."""
        from omnibase_core.enums import (
            EnumHandlerStatus as HandlerStatusEnum,
        )

        assert HandlerStatusEnum.READY.value == "ready"
