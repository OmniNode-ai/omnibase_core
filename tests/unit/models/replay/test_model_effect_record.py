# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelEffectRecord - Effect Record Model for Replay Infrastructure.

Tests cover:
- Model immutability (frozen)
- Default UUID generation for record_id
- Required field validation
- Serialization roundtrip (JSON export/import)
- Optional field defaults
- Timestamp handling

This test file follows TDD - tests are written BEFORE implementation.

.. versionadded:: 0.4.0
    Added as part of Replay Infrastructure (OMN-1116)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from omnibase_core.models.replay.model_effect_record import ModelEffectRecord


@pytest.fixture
def sample_intent() -> dict[str, Any]:
    """Create sample intent data."""
    return {
        "url": "https://api.example.com/users",
        "method": "GET",
        "headers": {"Authorization": "Bearer token123"},
    }


@pytest.fixture
def sample_result() -> dict[str, Any]:
    """Create sample result data."""
    return {
        "status_code": 200,
        "body": {"id": 1, "name": "John Doe"},
        "response_time_ms": 150,
    }


@pytest.fixture
def sample_timestamp() -> datetime:
    """Create sample timestamp."""
    return datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)


@pytest.fixture
def effect_record(
    sample_intent: dict[str, Any],
    sample_result: dict[str, Any],
    sample_timestamp: datetime,
) -> ModelEffectRecord:
    """Create a sample effect record."""
    from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

    return ModelEffectRecord(
        effect_type="http.get",
        intent=sample_intent,
        result=sample_result,
        captured_at=sample_timestamp,
        sequence_index=0,
    )


@pytest.mark.unit
class TestModelEffectRecordImmutability:
    """Test ModelEffectRecord immutability characteristics."""

    def test_model_is_frozen(self, effect_record: ModelEffectRecord) -> None:
        """Test that ModelEffectRecord is frozen (immutable)."""
        with pytest.raises(ValidationError):
            effect_record.effect_type = "modified.type"

    def test_cannot_modify_intent(self, effect_record: ModelEffectRecord) -> None:
        """Test that intent field cannot be reassigned."""
        with pytest.raises(ValidationError):
            effect_record.intent = {"new": "value"}

    def test_cannot_modify_result(self, effect_record: ModelEffectRecord) -> None:
        """Test that result field cannot be reassigned."""
        with pytest.raises(ValidationError):
            effect_record.result = {"new": "value"}

    def test_cannot_modify_sequence_index(
        self, effect_record: ModelEffectRecord
    ) -> None:
        """Test that sequence_index field cannot be reassigned."""
        with pytest.raises(ValidationError):
            effect_record.sequence_index = 999


@pytest.mark.unit
class TestModelEffectRecordDefaults:
    """Test ModelEffectRecord default value generation."""

    def test_default_record_id_generated(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that record_id is auto-generated as UUID."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        record = ModelEffectRecord(
            effect_type="db.query",
            intent=sample_intent,
            result=sample_result,
            captured_at=sample_timestamp,
            sequence_index=0,
        )

        assert record.record_id is not None
        assert isinstance(record.record_id, UUID)

    def test_unique_record_ids_for_different_instances(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that each instance gets a unique record_id."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        record1 = ModelEffectRecord(
            effect_type="db.query",
            intent=sample_intent,
            result=sample_result,
            captured_at=sample_timestamp,
            sequence_index=0,
        )
        record2 = ModelEffectRecord(
            effect_type="db.query",
            intent=sample_intent,
            result=sample_result,
            captured_at=sample_timestamp,
            sequence_index=1,
        )

        assert record1.record_id != record2.record_id

    def test_default_success_is_true(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that success defaults to True."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        record = ModelEffectRecord(
            effect_type="db.query",
            intent=sample_intent,
            result=sample_result,
            captured_at=sample_timestamp,
            sequence_index=0,
        )

        assert record.success is True

    def test_default_error_message_is_none(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that error_message defaults to None."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        record = ModelEffectRecord(
            effect_type="db.query",
            intent=sample_intent,
            result=sample_result,
            captured_at=sample_timestamp,
            sequence_index=0,
        )

        assert record.error_message is None


@pytest.mark.unit
class TestModelEffectRecordValidation:
    """Test ModelEffectRecord field validation."""

    def test_required_fields_effect_type(
        self,
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that effect_type is required."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRecord(
                intent={"key": "value"},
                result=sample_result,
                captured_at=sample_timestamp,
                sequence_index=0,
            )  # type: ignore[call-arg]

        assert "effect_type" in str(exc_info.value)

    def test_required_fields_intent(
        self,
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that intent is required."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRecord(
                effect_type="http.get",
                result=sample_result,
                captured_at=sample_timestamp,
                sequence_index=0,
            )  # type: ignore[call-arg]

        assert "intent" in str(exc_info.value)

    def test_required_fields_result(
        self,
        sample_intent: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that result is required."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRecord(
                effect_type="http.get",
                intent=sample_intent,
                captured_at=sample_timestamp,
                sequence_index=0,
            )  # type: ignore[call-arg]

        assert "result" in str(exc_info.value)

    def test_required_fields_captured_at(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that captured_at is required."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRecord(
                effect_type="http.get",
                intent=sample_intent,
                result=sample_result,
                sequence_index=0,
            )  # type: ignore[call-arg]

        assert "captured_at" in str(exc_info.value)

    def test_required_fields_sequence_index(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that sequence_index is required."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRecord(
                effect_type="http.get",
                intent=sample_intent,
                result=sample_result,
                captured_at=sample_timestamp,
            )  # type: ignore[call-arg]

        assert "sequence_index" in str(exc_info.value)

    def test_extra_fields_forbidden(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that extra fields are forbidden."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRecord(
                effect_type="http.get",
                intent=sample_intent,
                result=sample_result,
                captured_at=sample_timestamp,
                sequence_index=0,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelEffectRecordSerialization:
    """Test ModelEffectRecord serialization and deserialization."""

    def test_serialization_roundtrip(self, effect_record: ModelEffectRecord) -> None:
        """Test that model can be serialized and deserialized."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        # Serialize to dict
        data = effect_record.model_dump()

        # Deserialize back
        restored = ModelEffectRecord.model_validate(data)

        assert restored.effect_type == effect_record.effect_type
        assert restored.intent == effect_record.intent
        assert restored.result == effect_record.result
        assert restored.sequence_index == effect_record.sequence_index
        assert restored.success == effect_record.success
        assert restored.record_id == effect_record.record_id

    def test_json_serialization_roundtrip(
        self, effect_record: ModelEffectRecord
    ) -> None:
        """Test that model can be serialized to JSON and back."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        # Serialize to JSON
        json_str = effect_record.model_dump_json()

        # Deserialize back
        restored = ModelEffectRecord.model_validate_json(json_str)

        assert restored.effect_type == effect_record.effect_type
        assert restored.intent == effect_record.intent
        assert restored.result == effect_record.result

    def test_serialized_record_id_is_string(
        self, effect_record: ModelEffectRecord
    ) -> None:
        """Test that record_id serializes to string in JSON."""
        import json

        json_str = effect_record.model_dump_json()
        data = json.loads(json_str)

        assert isinstance(data["record_id"], str)

    def test_serialized_captured_at_is_iso_format(
        self, effect_record: ModelEffectRecord
    ) -> None:
        """Test that captured_at serializes to ISO format."""
        import json

        json_str = effect_record.model_dump_json()
        data = json.loads(json_str)

        # Should be ISO format string
        assert isinstance(data["captured_at"], str)
        # Should be parseable back to datetime
        datetime.fromisoformat(data["captured_at"])


@pytest.mark.unit
class TestModelEffectRecordErrorCase:
    """Test ModelEffectRecord error recording capabilities."""

    def test_can_record_failed_effect(
        self,
        sample_intent: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that failed effects can be recorded."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        record = ModelEffectRecord(
            effect_type="http.get",
            intent=sample_intent,
            result={},
            captured_at=sample_timestamp,
            sequence_index=0,
            success=False,
            error_message="Connection timeout after 30s",
        )

        assert record.success is False
        assert record.error_message == "Connection timeout after 30s"

    def test_error_message_with_success_true(
        self,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
        sample_timestamp: datetime,
    ) -> None:
        """Test that error_message can be set even with success=True (for warnings)."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        record = ModelEffectRecord(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
            captured_at=sample_timestamp,
            sequence_index=0,
            success=True,
            error_message="Request was slow (2.5s)",
        )

        assert record.success is True
        assert record.error_message == "Request was slow (2.5s)"
