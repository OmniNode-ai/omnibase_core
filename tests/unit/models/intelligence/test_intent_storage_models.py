# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for intent storage models (OMN-1645).

Tests comprehensive model functionality including:
- ModelIntentRecord: Stored intent classification record
- ModelIntentStorageResult: Storage operation result
- ModelIntentQueryResult: Query operation result

All models are frozen (immutable) and use extra="forbid".
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.intelligence.enum_intent_category import EnumIntentCategory
from omnibase_core.models.intelligence import (
    ModelIntentQueryResult,
    ModelIntentRecord,
    ModelIntentStorageResult,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Test: ModelIntentRecord
# ============================================================================


class TestModelIntentRecordRequiredFields:
    """Tests for required fields in ModelIntentRecord."""

    def test_create_with_required_fields(self) -> None:
        """Test creating model with required fields."""
        intent_id = uuid4()
        record = ModelIntentRecord(
            intent_id=intent_id,
            session_id="session-123",
            intent_category=EnumIntentCategory.CODE_GENERATION,
            confidence=0.95,
        )

        assert record.intent_id == intent_id
        assert record.session_id == "session-123"
        assert record.intent_category == EnumIntentCategory.CODE_GENERATION
        assert record.confidence == 0.95
        # Defaults
        assert record.keywords == []
        assert record.correlation_id is None
        assert record.created_at is not None

    def test_intent_id_is_required(self) -> None:
        """Test that intent_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecord(
                session_id="session-123",
                intent_category=EnumIntentCategory.CODE_GENERATION,
                confidence=0.5,
            )  # type: ignore[call-arg]

        assert "intent_id" in str(exc_info.value)

    def test_session_id_is_required(self) -> None:
        """Test that session_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecord(
                intent_id=uuid4(),
                intent_category=EnumIntentCategory.CODE_GENERATION,
                confidence=0.5,
            )  # type: ignore[call-arg]

        assert "session_id" in str(exc_info.value)

    def test_intent_category_is_required(self) -> None:
        """Test that intent_category is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecord(
                intent_id=uuid4(),
                session_id="session-123",
                confidence=0.5,
            )  # type: ignore[call-arg]

        assert "intent_category" in str(exc_info.value)

    def test_confidence_is_required(self) -> None:
        """Test that confidence is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecord(
                intent_id=uuid4(),
                session_id="session-123",
                intent_category=EnumIntentCategory.CODE_GENERATION,
            )  # type: ignore[call-arg]

        assert "confidence" in str(exc_info.value)


class TestModelIntentRecordFieldValidation:
    """Tests for field validation constraints."""

    def test_confidence_at_minimum(self) -> None:
        """Test confidence at minimum value (0.0)."""
        record = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.UNKNOWN,
            confidence=0.0,
        )
        assert record.confidence == 0.0

    def test_confidence_at_maximum(self) -> None:
        """Test confidence at maximum value (1.0)."""
        record = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.CODE_GENERATION,
            confidence=1.0,
        )
        assert record.confidence == 1.0

    def test_confidence_below_minimum_fails(self) -> None:
        """Test confidence below minimum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecord(
                intent_id=uuid4(),
                session_id="session-123",
                intent_category=EnumIntentCategory.CODE_GENERATION,
                confidence=-0.1,
            )

        assert "confidence" in str(exc_info.value)

    def test_confidence_above_maximum_fails(self) -> None:
        """Test confidence above maximum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecord(
                intent_id=uuid4(),
                session_id="session-123",
                intent_category=EnumIntentCategory.CODE_GENERATION,
                confidence=1.1,
            )

        assert "confidence" in str(exc_info.value)

    def test_intent_category_must_be_enum(self) -> None:
        """Test that intent_category must be EnumIntentCategory."""
        with pytest.raises(ValidationError):
            ModelIntentRecord(
                intent_id=uuid4(),
                session_id="session-123",
                intent_category="invalid_category",  # type: ignore[arg-type]
                confidence=0.5,
            )


class TestModelIntentRecordOptionalFields:
    """Tests for optional field handling."""

    def test_create_with_all_fields(self) -> None:
        """Test creating model with all fields populated."""
        intent_id = uuid4()
        correlation_id = uuid4()
        created_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)

        record = ModelIntentRecord(
            intent_id=intent_id,
            session_id="session-456",
            intent_category=EnumIntentCategory.DEBUGGING,
            confidence=0.87,
            keywords=["bug", "error", "fix"],
            created_at=created_at,
            correlation_id=correlation_id,
        )

        assert record.intent_id == intent_id
        assert record.session_id == "session-456"
        assert record.intent_category == EnumIntentCategory.DEBUGGING
        assert record.confidence == 0.87
        assert record.keywords == ["bug", "error", "fix"]
        assert record.created_at == created_at
        assert record.correlation_id == correlation_id

    def test_keywords_default_empty_list(self) -> None:
        """Test that keywords defaults to empty list."""
        record = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.CODE_GENERATION,
            confidence=0.5,
        )
        assert record.keywords == []

    def test_created_at_default_is_utc(self) -> None:
        """Test that created_at defaults to UTC datetime."""
        before = datetime.now(UTC)
        record = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.CODE_GENERATION,
            confidence=0.5,
        )
        after = datetime.now(UTC)

        assert before <= record.created_at <= after
        assert record.created_at.tzinfo is not None


class TestModelIntentRecordFrozen:
    """Tests for frozen model immutability."""

    def test_frozen_immutability(self) -> None:
        """Test that model fields cannot be modified."""
        record = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.CODE_GENERATION,
            confidence=0.5,
        )

        with pytest.raises(ValidationError):
            record.confidence = 0.9


class TestModelIntentRecordExtraForbidden:
    """Tests for extra field rejection."""

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentRecord(
                intent_id=uuid4(),
                session_id="session-123",
                intent_category=EnumIntentCategory.CODE_GENERATION,
                confidence=0.5,
                unknown_field="bad",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)


class TestModelIntentRecordSerialization:
    """Tests for serialization round-trip."""

    def test_model_dump_round_trip(self) -> None:
        """Test model_dump and model_validate round-trip."""
        original = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.REFACTORING,
            confidence=0.75,
            keywords=["clean", "optimize"],
            correlation_id=uuid4(),
        )

        data = original.model_dump()
        restored = ModelIntentRecord.model_validate(data)

        assert original.intent_id == restored.intent_id
        assert original.session_id == restored.session_id
        assert original.intent_category == restored.intent_category
        assert original.confidence == restored.confidence
        assert original.keywords == restored.keywords
        assert original.correlation_id == restored.correlation_id

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.TESTING,
            confidence=0.88,
        )

        json_str = original.model_dump_json()
        restored = ModelIntentRecord.model_validate_json(json_str)

        assert original.intent_id == restored.intent_id
        assert original.intent_category == restored.intent_category

    def test_json_parsing_with_strings(self) -> None:
        """Test JSON parsing with string UUIDs and datetime."""
        intent_id = uuid4()
        json_data = {
            "intent_id": str(intent_id),
            "session_id": "session-123",
            "intent_category": "code_generation",
            "confidence": 0.5,
            "created_at": "2025-01-15T10:30:00Z",
        }

        record = ModelIntentRecord.model_validate(json_data)

        assert record.intent_id == intent_id
        assert record.intent_category == EnumIntentCategory.CODE_GENERATION


# ============================================================================
# Test: ModelIntentStorageResult
# ============================================================================


class TestModelIntentStorageResultBasic:
    """Tests for ModelIntentStorageResult basic functionality."""

    def test_create_success_result(self) -> None:
        """Test creating a successful storage result."""
        intent_id = uuid4()
        result = ModelIntentStorageResult(
            success=True,
            intent_id=intent_id,
            created=True,
        )

        assert result.success is True
        assert result.intent_id == intent_id
        assert result.created is True
        assert result.error_message is None

    def test_create_failure_result(self) -> None:
        """Test creating a failed storage result."""
        result = ModelIntentStorageResult(
            success=False,
            error_message="Database connection failed",
        )

        assert result.success is False
        assert result.intent_id is None
        assert result.created is False
        assert result.error_message == "Database connection failed"

    def test_create_update_result(self) -> None:
        """Test creating an update (not create) result."""
        intent_id = uuid4()
        result = ModelIntentStorageResult(
            success=True,
            intent_id=intent_id,
            created=False,
        )

        assert result.success is True
        assert result.intent_id == intent_id
        assert result.created is False

    def test_success_is_required(self) -> None:
        """Test that success is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentStorageResult()  # type: ignore[call-arg]

        assert "success" in str(exc_info.value)


class TestModelIntentStorageResultFrozen:
    """Tests for frozen model immutability."""

    def test_frozen_immutability(self) -> None:
        """Test that model fields cannot be modified."""
        result = ModelIntentStorageResult(success=True)

        with pytest.raises(ValidationError):
            result.success = False


class TestModelIntentStorageResultSerialization:
    """Tests for serialization round-trip."""

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelIntentStorageResult(
            success=True,
            intent_id=uuid4(),
            created=True,
        )

        json_str = original.model_dump_json()
        restored = ModelIntentStorageResult.model_validate_json(json_str)

        assert original.success == restored.success
        assert original.intent_id == restored.intent_id
        assert original.created == restored.created


# ============================================================================
# Test: ModelIntentQueryResult
# ============================================================================


class TestModelIntentQueryResultBasic:
    """Tests for ModelIntentQueryResult basic functionality."""

    def test_create_success_with_results(self) -> None:
        """Test creating a successful query result with intents."""
        intent1 = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-1",
            intent_category=EnumIntentCategory.CODE_GENERATION,
            confidence=0.9,
        )
        intent2 = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-2",
            intent_category=EnumIntentCategory.DEBUGGING,
            confidence=0.85,
        )

        result = ModelIntentQueryResult(
            success=True,
            intents=[intent1, intent2],
            total_count=2,
        )

        assert result.success is True
        assert len(result.intents) == 2
        assert result.total_count == 2
        assert result.error_message is None

    def test_create_success_empty_results(self) -> None:
        """Test creating a successful query with no results."""
        result = ModelIntentQueryResult(
            success=True,
            intents=[],
            total_count=0,
        )

        assert result.success is True
        assert result.intents == []
        assert result.total_count == 0

    def test_create_failure_result(self) -> None:
        """Test creating a failed query result."""
        result = ModelIntentQueryResult(
            success=False,
            error_message="Query timeout",
        )

        assert result.success is False
        assert result.intents == []
        assert result.total_count == 0
        assert result.error_message == "Query timeout"

    def test_success_is_required(self) -> None:
        """Test that success is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResult()  # type: ignore[call-arg]

        assert "success" in str(exc_info.value)

    def test_total_count_must_be_non_negative(self) -> None:
        """Test that total_count must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentQueryResult(
                success=True,
                total_count=-1,
            )

        assert "total_count" in str(exc_info.value)


class TestModelIntentQueryResultSerialization:
    """Tests for serialization round-trip."""

    def test_json_round_trip_with_nested_records(self) -> None:
        """Test JSON serialization with nested ModelIntentRecord."""
        intent = ModelIntentRecord(
            intent_id=uuid4(),
            session_id="session-123",
            intent_category=EnumIntentCategory.ANALYSIS,
            confidence=0.77,
            keywords=["review", "inspect"],
        )

        original = ModelIntentQueryResult(
            success=True,
            intents=[intent],
            total_count=1,
        )

        json_str = original.model_dump_json()
        restored = ModelIntentQueryResult.model_validate_json(json_str)

        assert restored.success is True
        assert len(restored.intents) == 1
        assert restored.intents[0].session_id == "session-123"
        assert restored.intents[0].intent_category == EnumIntentCategory.ANALYSIS


# ============================================================================
# Test: Import from Package
# ============================================================================


class TestIntentStorageModelsImport:
    """Tests for model imports from intelligence package."""

    def test_import_from_intelligence_module(self) -> None:
        """Test that models can be imported from intelligence module."""
        from omnibase_core.models.intelligence import (
            ModelIntentQueryResult as ImportedQuery,
        )
        from omnibase_core.models.intelligence import (
            ModelIntentRecord as ImportedRecord,
        )
        from omnibase_core.models.intelligence import (
            ModelIntentStorageResult as ImportedStorage,
        )

        assert ImportedRecord is ModelIntentRecord
        assert ImportedStorage is ModelIntentStorageResult
        assert ImportedQuery is ModelIntentQueryResult

    def test_models_in_all(self) -> None:
        """Test that models are in __all__."""
        from omnibase_core.models import intelligence

        assert "ModelIntentRecord" in intelligence.__all__
        assert "ModelIntentStorageResult" in intelligence.__all__
        assert "ModelIntentQueryResult" in intelligence.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
