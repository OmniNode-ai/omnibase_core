# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelDelayUntilPayload.

This module tests the DELAY_UNTIL directive payload, verifying:
1. Discriminator field (kind="delay_until")
2. Required execute_at (timezone-aware datetime) and operation_id fields
3. Timezone-aware datetime validation
4. Reason max_length validation
5. Serialization/deserialization roundtrip
"""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.payloads import ModelDelayUntilPayload


@pytest.mark.unit
class TestModelDelayUntilPayloadDiscriminator:
    """Test discriminator field behavior."""

    def test_kind_is_literal_delay_until(self) -> None:
        """Test that kind field is always 'delay_until'."""
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
        )
        assert payload.kind == "delay_until"

    def test_kind_cannot_be_changed(self) -> None:
        """Test that kind field cannot be set to different value."""
        with pytest.raises(ValidationError):
            ModelDelayUntilPayload(
                execute_at=datetime.now(UTC),
                operation_id=uuid4(),
                kind="other_kind",  # type: ignore[arg-type]
            )

    def test_kind_default_value(self) -> None:
        """Test that kind has correct default value."""
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
        )
        assert payload.kind == "delay_until"


@pytest.mark.unit
class TestModelDelayUntilPayloadRequiredFields:
    """Test required field validation."""

    def test_execute_at_required(self) -> None:
        """Test that execute_at is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDelayUntilPayload(operation_id=uuid4())  # type: ignore[call-arg]
        assert "execute_at" in str(exc_info.value)

    def test_operation_id_required(self) -> None:
        """Test that operation_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDelayUntilPayload(execute_at=datetime.now(UTC))  # type: ignore[call-arg]
        assert "operation_id" in str(exc_info.value)

    def test_both_required_fields(self) -> None:
        """Test that both execute_at and operation_id are required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDelayUntilPayload()  # type: ignore[call-arg]
        error_str = str(exc_info.value)
        assert "execute_at" in error_str or "operation_id" in error_str


@pytest.mark.unit
class TestModelDelayUntilPayloadExecuteAtValidation:
    """Test execute_at field validation."""

    def test_execute_at_with_utc(self) -> None:
        """Test execute_at with UTC timezone."""
        future_time = datetime.now(UTC) + timedelta(minutes=5)
        payload = ModelDelayUntilPayload(
            execute_at=future_time,
            operation_id=uuid4(),
        )
        assert payload.execute_at == future_time
        assert payload.execute_at.tzinfo is not None

    def test_execute_at_with_custom_timezone(self) -> None:
        """Test execute_at with custom timezone."""
        custom_tz = timezone(timedelta(hours=-5))
        future_time = datetime.now(custom_tz) + timedelta(minutes=5)
        payload = ModelDelayUntilPayload(
            execute_at=future_time,
            operation_id=uuid4(),
        )
        assert payload.execute_at.tzinfo is not None

    def test_execute_at_naive_datetime_rejected(self) -> None:
        """Test that naive datetime (no timezone) is rejected."""
        naive_time = datetime.now()  # No timezone
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDelayUntilPayload(
                execute_at=naive_time,
                operation_id=uuid4(),
            )
        assert "timezone-aware" in str(exc_info.value)

    def test_execute_at_past_time_allowed(self) -> None:
        """Test that past time is allowed (runtime handles this)."""
        past_time = datetime.now(UTC) - timedelta(minutes=5)
        payload = ModelDelayUntilPayload(
            execute_at=past_time,
            operation_id=uuid4(),
        )
        assert payload.execute_at == past_time

    def test_execute_at_current_time(self) -> None:
        """Test execute_at with current time."""
        now = datetime.now(UTC)
        payload = ModelDelayUntilPayload(
            execute_at=now,
            operation_id=uuid4(),
        )
        assert payload.execute_at == now


@pytest.mark.unit
class TestModelDelayUntilPayloadOperationId:
    """Test operation_id field validation."""

    def test_operation_id_valid_uuid(self) -> None:
        """Test operation_id with valid UUID."""
        op_id = uuid4()
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=op_id,
        )
        assert payload.operation_id == op_id

    def test_operation_id_from_string(self) -> None:
        """Test operation_id from string UUID."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid_str,  # type: ignore[arg-type]
        )
        assert isinstance(payload.operation_id, UUID)
        assert str(payload.operation_id) == uuid_str

    def test_operation_id_invalid_format(self) -> None:
        """Test operation_id with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDelayUntilPayload(
                execute_at=datetime.now(UTC),
                operation_id="not-a-uuid",  # type: ignore[arg-type]
            )
        assert "operation_id" in str(exc_info.value)


@pytest.mark.unit
class TestModelDelayUntilPayloadOptionalFields:
    """Test optional field behavior."""

    def test_reason_defaults_to_none(self) -> None:
        """Test that reason defaults to None."""
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
        )
        assert payload.reason is None

    def test_reason_with_value(self) -> None:
        """Test reason with specific value."""
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
            reason="Rate limit cooldown",
        )
        assert payload.reason == "Rate limit cooldown"


@pytest.mark.unit
class TestModelDelayUntilPayloadReasonValidation:
    """Test reason field validation."""

    def test_reason_max_length_valid(self) -> None:
        """Test reason at exactly max_length (500)."""
        reason = "x" * 500
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
            reason=reason,
        )
        assert len(payload.reason) == 500

    def test_reason_exceeds_max_length(self) -> None:
        """Test reason exceeding max_length (501)."""
        reason = "x" * 501
        with pytest.raises(ValidationError) as exc_info:
            ModelDelayUntilPayload(
                execute_at=datetime.now(UTC),
                operation_id=uuid4(),
                reason=reason,
            )
        assert "reason" in str(exc_info.value)

    def test_reason_empty_string(self) -> None:
        """Test reason with empty string (should be allowed)."""
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
            reason="",
        )
        assert payload.reason == ""


@pytest.mark.unit
class TestModelDelayUntilPayloadSerialization:
    """Test serialization/deserialization."""

    def test_serialization_minimal(self) -> None:
        """Test serialization with minimal fields."""
        exec_at = datetime.now(UTC)
        op_id = uuid4()
        payload = ModelDelayUntilPayload(
            execute_at=exec_at,
            operation_id=op_id,
        )
        data = payload.model_dump()

        assert data["kind"] == "delay_until"
        assert data["execute_at"] == exec_at
        assert data["operation_id"] == op_id
        assert data["reason"] is None

    def test_serialization_all_fields(self) -> None:
        """Test serialization with all fields set."""
        exec_at = datetime.now(UTC)
        op_id = uuid4()
        payload = ModelDelayUntilPayload(
            execute_at=exec_at,
            operation_id=op_id,
            reason="Test delay reason",
        )
        data = payload.model_dump()

        assert data["reason"] == "Test delay reason"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        exec_at = datetime.now(UTC)
        op_id = uuid4()
        original = ModelDelayUntilPayload(
            execute_at=exec_at,
            operation_id=op_id,
            reason="Delay reason",
        )
        data = original.model_dump()
        restored = ModelDelayUntilPayload.model_validate(data)

        assert restored.kind == original.kind
        assert restored.execute_at == original.execute_at
        assert restored.operation_id == original.operation_id
        assert restored.reason == original.reason

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        exec_at = datetime.now(UTC)
        op_id = uuid4()
        payload = ModelDelayUntilPayload(
            execute_at=exec_at,
            operation_id=op_id,
        )
        json_str = payload.model_dump_json()

        assert '"kind":"delay_until"' in json_str
        assert str(op_id) in json_str


@pytest.mark.unit
class TestModelDelayUntilPayloadImmutability:
    """Test immutability (frozen model)."""

    def test_cannot_modify_execute_at(self) -> None:
        """Test that execute_at cannot be modified."""
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            payload.execute_at = datetime.now(UTC)  # type: ignore[misc]

    def test_cannot_modify_operation_id(self) -> None:
        """Test that operation_id cannot be modified."""
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            payload.operation_id = uuid4()  # type: ignore[misc]


@pytest.mark.unit
class TestModelDelayUntilPayloadExtraFieldsRejected:
    """Test extra fields rejection."""

    def test_reject_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDelayUntilPayload(
                execute_at=datetime.now(UTC),
                operation_id=uuid4(),
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelDelayUntilPayloadEdgeCases:
    """Test edge cases."""

    def test_far_future_datetime(self) -> None:
        """Test execute_at with far future datetime."""
        far_future = datetime.now(UTC) + timedelta(days=365 * 10)  # 10 years
        payload = ModelDelayUntilPayload(
            execute_at=far_future,
            operation_id=uuid4(),
        )
        assert payload.execute_at == far_future

    def test_reason_with_newlines(self) -> None:
        """Test reason with newline characters."""
        reason = "Line 1\nLine 2\nLine 3"
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
            reason=reason,
        )
        assert payload.reason == reason

    def test_reason_with_unicode(self) -> None:
        """Test reason with unicode characters."""
        reason = "Delay reason"
        payload = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
            reason=reason,
        )
        assert payload.reason == reason

    def test_various_timezones(self) -> None:
        """Test execute_at with various timezones."""
        timezones = [
            UTC,
            timezone(timedelta(hours=0)),
            timezone(timedelta(hours=5, minutes=30)),
            timezone(timedelta(hours=-8)),
            timezone(timedelta(hours=12)),
        ]
        for tz in timezones:
            exec_time = datetime.now(tz) + timedelta(minutes=10)
            payload = ModelDelayUntilPayload(
                execute_at=exec_time,
                operation_id=uuid4(),
            )
            assert payload.execute_at.tzinfo is not None

    def test_datetime_precision(self) -> None:
        """Test execute_at preserves microsecond precision."""
        precise_time = datetime(2025, 1, 15, 12, 30, 45, 123456, tzinfo=UTC)
        payload = ModelDelayUntilPayload(
            execute_at=precise_time,
            operation_id=uuid4(),
        )
        assert payload.execute_at.microsecond == 123456
