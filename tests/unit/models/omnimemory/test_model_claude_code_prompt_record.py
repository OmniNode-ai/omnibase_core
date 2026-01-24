# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelClaudeCodePromptRecord.

Tests comprehensive prompt record functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- Field validation constraints
- Extra fields rejection
- Serialization and deserialization
- from_attributes compatibility
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.omnimemory.model_claude_code_prompt_record import (
    ModelClaudeCodePromptRecord,
)

pytestmark = pytest.mark.unit

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_emitted_at() -> datetime:
    """Create a sample timezone-aware datetime for testing."""
    return datetime.now(UTC)


@pytest.fixture
def minimal_prompt_data(sample_emitted_at: datetime) -> dict[str, Any]:
    """Minimal required data for creating a prompt record."""
    return {
        "emitted_at": sample_emitted_at,
        "prompt_preview": "Fix the authentication bug in the login module",
        "prompt_length": 256,
    }


@pytest.fixture
def full_prompt_data(sample_emitted_at: datetime) -> dict[str, Any]:
    """Complete data including all optional fields."""
    return {
        "prompt_id": uuid4(),
        "emitted_at": sample_emitted_at,
        "prompt_preview": "Implement the new feature for user management",
        "prompt_length": 512,
        "detected_intent": "feature_implementation",
        "causation_id": uuid4(),
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelClaudeCodePromptRecordInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test creating prompt record with only required fields."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert isinstance(record.prompt_id, UUID)
        assert record.emitted_at == minimal_prompt_data["emitted_at"]
        assert record.prompt_preview == minimal_prompt_data["prompt_preview"]
        assert record.prompt_length == minimal_prompt_data["prompt_length"]

    def test_create_with_full_data(self, full_prompt_data: dict[str, Any]) -> None:
        """Test creating prompt record with all fields explicitly set."""
        record = ModelClaudeCodePromptRecord(**full_prompt_data)

        assert record.prompt_id == full_prompt_data["prompt_id"]
        assert record.emitted_at == full_prompt_data["emitted_at"]
        assert record.prompt_preview == full_prompt_data["prompt_preview"]
        assert record.prompt_length == full_prompt_data["prompt_length"]
        assert record.detected_intent == full_prompt_data["detected_intent"]
        assert record.causation_id == full_prompt_data["causation_id"]

    def test_auto_generated_prompt_id(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that prompt_id is auto-generated when not provided."""
        record1 = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        record2 = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert isinstance(record1.prompt_id, UUID)
        assert isinstance(record2.prompt_id, UUID)
        assert record1.prompt_id != record2.prompt_id  # Each gets unique ID

    def test_default_values(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test that default values are properly set."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert record.detected_intent is None
        assert record.causation_id is None


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelClaudeCodePromptRecordImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test that the model is immutable."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        with pytest.raises(ValidationError):
            record.prompt_length = 999

    def test_cannot_modify_prompt_id(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test that prompt_id cannot be modified."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        with pytest.raises(ValidationError):
            record.prompt_id = uuid4()

    def test_cannot_modify_prompt_preview(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that prompt_preview cannot be modified."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        with pytest.raises(ValidationError):
            record.prompt_preview = "New preview"

    def test_cannot_modify_detected_intent(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that detected_intent cannot be modified."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        with pytest.raises(ValidationError):
            record.detected_intent = "new_intent"


# ============================================================================
# Test: Extra Fields Rejection
# ============================================================================


class TestModelClaudeCodePromptRecordExtraFields:
    """Tests for extra fields rejection (extra='forbid')."""

    def test_rejects_extra_fields(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test that extra fields are rejected."""
        minimal_prompt_data["unknown_field"] = "should_fail"

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert "unknown_field" in str(exc_info.value)

    def test_rejects_multiple_extra_fields(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that multiple extra fields are rejected."""
        minimal_prompt_data["extra1"] = "value1"
        minimal_prompt_data["extra2"] = "value2"

        with pytest.raises(ValidationError):
            ModelClaudeCodePromptRecord(**minimal_prompt_data)


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelClaudeCodePromptRecordValidation:
    """Tests for field validation constraints."""

    def test_prompt_length_must_be_non_negative(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that prompt_length rejects negative values."""
        minimal_prompt_data["prompt_length"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert "prompt_length" in str(exc_info.value)

    def test_prompt_length_accepts_zero(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that prompt_length accepts zero."""
        minimal_prompt_data["prompt_length"] = 0
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        assert record.prompt_length == 0

    def test_prompt_length_accepts_positive_values(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that prompt_length accepts positive values."""
        for length in [1, 100, 10000]:
            minimal_prompt_data["prompt_length"] = length
            record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
            assert record.prompt_length == length

    def test_prompt_preview_max_length(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that prompt_preview respects max_length=100."""
        # Exactly 100 characters should work
        minimal_prompt_data["prompt_preview"] = "a" * 100
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        assert len(record.prompt_preview) == 100

    def test_prompt_preview_exceeds_max_length(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that prompt_preview rejects strings over 100 characters."""
        minimal_prompt_data["prompt_preview"] = "a" * 101

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert "prompt_preview" in str(exc_info.value)

    def test_missing_required_field_emitted_at(self) -> None:
        """Test that missing emitted_at raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodePromptRecord(  # type: ignore[call-arg]
                prompt_preview="Test prompt",
                prompt_length=10,
            )

        assert "emitted_at" in str(exc_info.value)

    def test_missing_required_field_prompt_preview(
        self, sample_emitted_at: datetime
    ) -> None:
        """Test that missing prompt_preview raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodePromptRecord(  # type: ignore[call-arg]
                emitted_at=sample_emitted_at,
                prompt_length=10,
            )

        assert "prompt_preview" in str(exc_info.value)

    def test_missing_required_field_prompt_length(
        self, sample_emitted_at: datetime
    ) -> None:
        """Test that missing prompt_length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodePromptRecord(  # type: ignore[call-arg]
                emitted_at=sample_emitted_at,
                prompt_preview="Test prompt",
            )

        assert "prompt_length" in str(exc_info.value)

    def test_emitted_at_requires_timezone(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that emitted_at rejects naive datetime."""
        minimal_prompt_data["emitted_at"] = datetime(2025, 1, 1, 12, 0, 0)  # naive

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert "timezone" in str(exc_info.value).lower()

    def test_emitted_at_accepts_timezone_aware(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test that emitted_at accepts timezone-aware datetime."""
        minimal_prompt_data["emitted_at"] = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        assert record.emitted_at.tzinfo is not None


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelClaudeCodePromptRecordSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test serialization to dictionary."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        data = record.model_dump()

        assert "prompt_id" in data
        assert "emitted_at" in data
        assert "prompt_preview" in data
        assert "prompt_length" in data
        assert "detected_intent" in data
        assert "causation_id" in data

    def test_model_dump_json(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test serialization to JSON string."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        json_str = record.model_dump_json()

        assert isinstance(json_str, str)
        assert "prompt_id" in json_str
        assert "prompt_preview" in json_str

    def test_round_trip_serialization(self, full_prompt_data: dict[str, Any]) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelClaudeCodePromptRecord(**full_prompt_data)
        data = original.model_dump()
        restored = ModelClaudeCodePromptRecord(**data)

        assert original.prompt_id == restored.prompt_id
        assert original.emitted_at == restored.emitted_at
        assert original.prompt_preview == restored.prompt_preview
        assert original.prompt_length == restored.prompt_length
        assert original.detected_intent == restored.detected_intent
        assert original.causation_id == restored.causation_id

    def test_json_round_trip_serialization(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        json_str = original.model_dump_json()
        restored = ModelClaudeCodePromptRecord.model_validate_json(json_str)

        assert original.prompt_id == restored.prompt_id
        assert original.prompt_preview == restored.prompt_preview
        assert original.prompt_length == restored.prompt_length

    def test_model_validate_from_dict(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test model validation from dictionary."""
        record = ModelClaudeCodePromptRecord.model_validate(minimal_prompt_data)

        assert record.prompt_preview == minimal_prompt_data["prompt_preview"]
        assert record.prompt_length == minimal_prompt_data["prompt_length"]


# ============================================================================
# Test: from_attributes Compatibility
# ============================================================================


class TestModelClaudeCodePromptRecordFromAttributes:
    """Tests for from_attributes compatibility (pytest-xdist support)."""

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes is enabled in model config."""
        assert ModelClaudeCodePromptRecord.model_config.get("from_attributes") is True

    def test_model_validate_with_existing_instance(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test model validation from an existing model instance."""
        original = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        # This should work due to from_attributes=True
        validated = ModelClaudeCodePromptRecord.model_validate(original)

        assert validated.prompt_id == original.prompt_id
        assert validated.prompt_preview == original.prompt_preview


# ============================================================================
# Test: Utility Methods
# ============================================================================


class TestModelClaudeCodePromptRecordUtilityMethods:
    """Tests for __str__ and __repr__ methods."""

    def test_str_representation(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test __str__ method returns expected format."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        str_repr = str(record)

        assert isinstance(str_repr, str)
        assert "PromptRecord" in str_repr
        assert f"len={minimal_prompt_data['prompt_length']}" in str_repr

    def test_str_representation_with_intent(
        self, full_prompt_data: dict[str, Any]
    ) -> None:
        """Test __str__ method includes intent when present."""
        record = ModelClaudeCodePromptRecord(**full_prompt_data)
        str_repr = str(record)

        assert "intent=" in str_repr
        assert full_prompt_data["detected_intent"] in str_repr

    def test_str_representation_without_intent(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test __str__ method excludes intent when None."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        str_repr = str(record)

        assert "intent=" not in str_repr

    def test_repr_representation(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test __repr__ method returns string with class name."""
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        repr_str = repr(record)

        assert isinstance(repr_str, str)
        assert "ModelClaudeCodePromptRecord" in repr_str
        assert "prompt_id=" in repr_str
        assert "prompt_length=" in repr_str


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelClaudeCodePromptRecordEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_prompt_preview(self, sample_emitted_at: datetime) -> None:
        """Test prompt record with empty prompt_preview."""
        record = ModelClaudeCodePromptRecord(
            emitted_at=sample_emitted_at,
            prompt_preview="",
            prompt_length=0,
        )
        assert record.prompt_preview == ""

    def test_model_equality(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test model equality comparison with identical data."""
        prompt_id = uuid4()
        minimal_prompt_data["prompt_id"] = prompt_id

        record1 = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        record2 = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        assert record1 == record2

    def test_model_inequality_different_prompt_id(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test model inequality when prompt_ids differ."""
        record1 = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        record2 = ModelClaudeCodePromptRecord(**minimal_prompt_data)

        # Different auto-generated prompt_ids
        assert record1 != record2

    def test_special_characters_in_preview(
        self, minimal_prompt_data: dict[str, Any]
    ) -> None:
        """Test prompt preview with special characters."""
        minimal_prompt_data["prompt_preview"] = "Fix bug: 'error' in \"code\" & logs"
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        assert record.prompt_preview == minimal_prompt_data["prompt_preview"]

    def test_unicode_in_preview(self, minimal_prompt_data: dict[str, Any]) -> None:
        """Test prompt preview with unicode characters."""
        minimal_prompt_data["prompt_preview"] = "Correct issue in module"
        record = ModelClaudeCodePromptRecord(**minimal_prompt_data)
        assert record.prompt_preview == minimal_prompt_data["prompt_preview"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
