# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelCancelExecutionPayload.

This module tests the CANCEL_EXECUTION directive payload, verifying:
1. Discriminator field (kind="cancel_execution")
2. Required execution_id field (UUID)
3. Optional reason, force, and cleanup_required fields
4. Reason max_length validation
5. Serialization/deserialization roundtrip
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.runtime.payloads import ModelCancelExecutionPayload


@pytest.mark.unit
class TestModelCancelExecutionPayloadDiscriminator:
    """Test discriminator field behavior."""

    def test_kind_is_literal_cancel_execution(self) -> None:
        """Test that kind field is always 'cancel_execution'."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4())
        assert payload.kind == "cancel_execution"

    def test_kind_rejects_invalid_discriminator_value(self) -> None:
        """Test that kind field rejects values other than 'cancel_execution'.

        The kind field is a Literal['cancel_execution'] discriminator, so any other
        value should be rejected by Pydantic validation.
        """
        with pytest.raises(ValidationError):
            ModelCancelExecutionPayload(
                execution_id=uuid4(),
                kind="other_kind",  # type: ignore[arg-type]
            )

    def test_kind_default_value(self) -> None:
        """Test that kind has correct default value."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4())
        assert payload.kind == "cancel_execution"


@pytest.mark.unit
class TestModelCancelExecutionPayloadRequiredFields:
    """Test required field validation."""

    def test_execution_id_required(self) -> None:
        """Test that execution_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCancelExecutionPayload()  # type: ignore[call-arg]
        assert "execution_id" in str(exc_info.value)

    def test_execution_id_valid_uuid(self) -> None:
        """Test execution_id with valid UUID."""
        exec_id = uuid4()
        payload = ModelCancelExecutionPayload(execution_id=exec_id)
        assert payload.execution_id == exec_id

    def test_execution_id_from_string(self) -> None:
        """Test execution_id from string UUID."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        payload = ModelCancelExecutionPayload(execution_id=uuid_str)  # type: ignore[arg-type]
        assert isinstance(payload.execution_id, UUID)
        assert str(payload.execution_id) == uuid_str

    def test_execution_id_invalid_format(self) -> None:
        """Test execution_id with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCancelExecutionPayload(execution_id="not-a-uuid")  # type: ignore[arg-type]
        assert "execution_id" in str(exc_info.value)


@pytest.mark.unit
class TestModelCancelExecutionPayloadOptionalFields:
    """Test optional field behavior."""

    def test_reason_defaults_to_none(self) -> None:
        """Test that reason defaults to None."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4())
        assert payload.reason is None

    def test_reason_with_value(self) -> None:
        """Test reason with specific value."""
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            reason="User requested cancellation",
        )
        assert payload.reason == "User requested cancellation"

    def test_force_defaults_to_false(self) -> None:
        """Test that force defaults to False."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4())
        assert payload.force is False

    def test_force_true(self) -> None:
        """Test force set to True."""
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            force=True,
        )
        assert payload.force is True

    def test_cleanup_required_defaults_to_true(self) -> None:
        """Test that cleanup_required defaults to True."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4())
        assert payload.cleanup_required is True

    def test_cleanup_required_false(self) -> None:
        """Test cleanup_required set to False."""
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            cleanup_required=False,
        )
        assert payload.cleanup_required is False


@pytest.mark.unit
class TestModelCancelExecutionPayloadReasonValidation:
    """Test reason field validation."""

    def test_reason_max_length_valid(self) -> None:
        """Test reason at exactly max_length (500)."""
        reason = "x" * 500
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            reason=reason,
        )
        assert len(payload.reason) == 500

    def test_reason_exceeds_max_length(self) -> None:
        """Test reason exceeding max_length (501)."""
        reason = "x" * 501
        with pytest.raises(ValidationError) as exc_info:
            ModelCancelExecutionPayload(
                execution_id=uuid4(),
                reason=reason,
            )
        assert "reason" in str(exc_info.value)

    def test_reason_empty_string(self) -> None:
        """Test reason with empty string (should be allowed)."""
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            reason="",
        )
        assert payload.reason == ""


@pytest.mark.unit
class TestModelCancelExecutionPayloadSerialization:
    """Test serialization/deserialization."""

    def test_serialization_minimal(self) -> None:
        """Test serialization with minimal fields."""
        exec_id = uuid4()
        payload = ModelCancelExecutionPayload(execution_id=exec_id)
        data = payload.model_dump()

        assert data["kind"] == "cancel_execution"
        assert data["execution_id"] == exec_id
        assert data["reason"] is None
        assert data["force"] is False
        assert data["cleanup_required"] is True

    def test_serialization_all_fields(self) -> None:
        """Test serialization with all fields set."""
        exec_id = uuid4()
        payload = ModelCancelExecutionPayload(
            execution_id=exec_id,
            reason="Test reason",
            force=True,
            cleanup_required=False,
        )
        data = payload.model_dump()

        assert data["reason"] == "Test reason"
        assert data["force"] is True
        assert data["cleanup_required"] is False

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        exec_id = uuid4()
        original = ModelCancelExecutionPayload(
            execution_id=exec_id,
            reason="Cancellation reason",
            force=True,
            cleanup_required=True,
        )
        data = original.model_dump()
        restored = ModelCancelExecutionPayload.model_validate(data)

        assert restored.kind == original.kind
        assert restored.execution_id == original.execution_id
        assert restored.reason == original.reason
        assert restored.force == original.force
        assert restored.cleanup_required == original.cleanup_required

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        exec_id = uuid4()
        payload = ModelCancelExecutionPayload(execution_id=exec_id)
        json_str = payload.model_dump_json()

        assert '"kind":"cancel_execution"' in json_str
        assert str(exec_id) in json_str


@pytest.mark.unit
class TestModelCancelExecutionPayloadImmutability:
    """Test immutability (frozen model)."""

    def test_cannot_modify_execution_id(self) -> None:
        """Test that execution_id cannot be modified."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4())
        with pytest.raises(ValidationError):
            payload.execution_id = uuid4()  # type: ignore[misc]

    def test_cannot_modify_force(self) -> None:
        """Test that force cannot be modified."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4(), force=False)
        with pytest.raises(ValidationError):
            payload.force = True  # type: ignore[misc]

    def test_cannot_modify_kind(self) -> None:
        """Test that kind cannot be modified."""
        payload = ModelCancelExecutionPayload(execution_id=uuid4())
        with pytest.raises(ValidationError):
            payload.kind = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestModelCancelExecutionPayloadExtraFieldsRejected:
    """Test extra fields rejection."""

    def test_reject_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCancelExecutionPayload(
                execution_id=uuid4(),
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelCancelExecutionPayloadEdgeCases:
    """Test edge cases."""

    def test_reason_with_newlines(self) -> None:
        """Test reason with newline characters."""
        reason = "Line 1\nLine 2\nLine 3"
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            reason=reason,
        )
        assert payload.reason == reason

    def test_reason_with_unicode(self) -> None:
        """Test reason with unicode characters from multiple scripts."""
        # Test with actual unicode literals from various scripts
        reason = "Cancellation: 测试 тест ελληνικά عربي 日本語 한국어 café résumé 🎉🚀"
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            reason=reason,
        )
        assert payload.reason == reason
        # Verify specific unicode characters are preserved
        assert "测试" in payload.reason  # Chinese (Simplified)
        assert "тест" in payload.reason  # Russian (Cyrillic)
        assert "ελληνικά" in payload.reason  # Greek
        assert "عربي" in payload.reason  # Arabic
        assert "日本語" in payload.reason  # Japanese
        assert "한국어" in payload.reason  # Korean
        assert "café" in payload.reason  # Accented Latin
        assert "résumé" in payload.reason  # Accented Latin
        assert "🎉" in payload.reason  # Emoji (party popper)
        assert "🚀" in payload.reason  # Emoji (rocket)

    def test_all_flags_false(self) -> None:
        """Test with all boolean flags set to False."""
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            force=False,
            cleanup_required=False,
        )
        assert payload.force is False
        assert payload.cleanup_required is False

    def test_all_flags_true(self) -> None:
        """Test with all boolean flags set to True."""
        payload = ModelCancelExecutionPayload(
            execution_id=uuid4(),
            force=True,
            cleanup_required=True,
        )
        assert payload.force is True
        assert payload.cleanup_required is True
