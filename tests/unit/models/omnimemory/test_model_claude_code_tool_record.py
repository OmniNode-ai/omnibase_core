# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelClaudeCodeToolRecord.

Tests comprehensive tool record functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- Field validation constraints (duration_ms >= 0)
- Extra fields rejection
- Serialization and deserialization
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.omnimemory.model_claude_code_tool_record import (
    ModelClaudeCodeToolRecord,
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
def minimal_tool_data(sample_emitted_at: datetime) -> dict[str, Any]:
    """Minimal required data for creating a tool record."""
    return {
        "emitted_at": sample_emitted_at,
        "tool_name": "Read",
        "success": True,
        "duration_ms": 150,
    }


@pytest.fixture
def full_tool_data(sample_emitted_at: datetime) -> dict[str, Any]:
    """Complete data including all optional fields."""
    return {
        "tool_execution_id": uuid4(),
        "emitted_at": sample_emitted_at,
        "tool_name": "Write",
        "success": True,
        "duration_ms": 500,
        "summary": "Wrote 245 lines to /src/main.py",
        "causation_id": uuid4(),
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelClaudeCodeToolRecordInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test creating tool record with only required fields."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert isinstance(record.tool_execution_id, UUID)
        assert record.emitted_at == minimal_tool_data["emitted_at"]
        assert record.tool_name == minimal_tool_data["tool_name"]
        assert record.success == minimal_tool_data["success"]
        assert record.duration_ms == minimal_tool_data["duration_ms"]

    def test_create_with_full_data(self, full_tool_data: dict[str, Any]) -> None:
        """Test creating tool record with all fields explicitly set."""
        record = ModelClaudeCodeToolRecord(**full_tool_data)

        assert record.tool_execution_id == full_tool_data["tool_execution_id"]
        assert record.emitted_at == full_tool_data["emitted_at"]
        assert record.tool_name == full_tool_data["tool_name"]
        assert record.success == full_tool_data["success"]
        assert record.duration_ms == full_tool_data["duration_ms"]
        assert record.summary == full_tool_data["summary"]
        assert record.causation_id == full_tool_data["causation_id"]

    def test_auto_generated_tool_execution_id(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that tool_execution_id is auto-generated when not provided."""
        record1 = ModelClaudeCodeToolRecord(**minimal_tool_data)
        record2 = ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert isinstance(record1.tool_execution_id, UUID)
        assert isinstance(record2.tool_execution_id, UUID)
        assert record1.tool_execution_id != record2.tool_execution_id

    def test_default_values(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that default values are properly set."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert record.summary is None
        assert record.causation_id is None

    def test_create_with_failure(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test creating tool record for a failed execution."""
        minimal_tool_data["success"] = False
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert record.success is False


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelClaudeCodeToolRecordImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that the model is immutable."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)

        with pytest.raises(ValidationError):
            record.duration_ms = 999

    def test_cannot_modify_tool_execution_id(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that tool_execution_id cannot be modified."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)

        with pytest.raises(ValidationError):
            record.tool_execution_id = uuid4()

    def test_cannot_modify_tool_name(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that tool_name cannot be modified."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)

        with pytest.raises(ValidationError):
            record.tool_name = "NewTool"

    def test_cannot_modify_success(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that success cannot be modified."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)

        with pytest.raises(ValidationError):
            record.success = False

    def test_cannot_modify_summary(self, full_tool_data: dict[str, Any]) -> None:
        """Test that summary cannot be modified."""
        record = ModelClaudeCodeToolRecord(**full_tool_data)

        with pytest.raises(ValidationError):
            record.summary = "New summary"


# ============================================================================
# Test: Extra Fields Rejection
# ============================================================================


class TestModelClaudeCodeToolRecordExtraFields:
    """Tests for extra fields rejection (extra='forbid')."""

    def test_rejects_extra_fields(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that extra fields are rejected."""
        minimal_tool_data["unknown_field"] = "should_fail"

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert "unknown_field" in str(exc_info.value)

    def test_rejects_multiple_extra_fields(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that multiple extra fields are rejected."""
        minimal_tool_data["extra1"] = "value1"
        minimal_tool_data["extra2"] = "value2"

        with pytest.raises(ValidationError):
            ModelClaudeCodeToolRecord(**minimal_tool_data)


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelClaudeCodeToolRecordValidation:
    """Tests for field validation constraints."""

    def test_duration_ms_must_be_non_negative(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that duration_ms rejects negative values."""
        minimal_tool_data["duration_ms"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert "duration_ms" in str(exc_info.value)

    def test_duration_ms_accepts_zero(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that duration_ms accepts zero."""
        minimal_tool_data["duration_ms"] = 0
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        assert record.duration_ms == 0

    def test_duration_ms_accepts_positive_values(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that duration_ms accepts positive values."""
        for duration in [1, 100, 10000, 1000000]:
            minimal_tool_data["duration_ms"] = duration
            record = ModelClaudeCodeToolRecord(**minimal_tool_data)
            assert record.duration_ms == duration

    def test_tool_name_min_length(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that tool_name requires at least 1 character."""
        minimal_tool_data["tool_name"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert "tool_name" in str(exc_info.value)

    def test_tool_name_accepts_single_char(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that tool_name accepts single character."""
        minimal_tool_data["tool_name"] = "X"
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        assert record.tool_name == "X"

    def test_summary_max_length(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test that summary respects max_length=500."""
        # Exactly 500 characters should work
        minimal_tool_data["summary"] = "a" * 500
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        assert record.summary is not None
        assert len(record.summary) == 500

    def test_summary_exceeds_max_length(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that summary rejects strings over 500 characters."""
        minimal_tool_data["summary"] = "a" * 501

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert "summary" in str(exc_info.value)

    def test_missing_required_field_emitted_at(self) -> None:
        """Test that missing emitted_at raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(  # type: ignore[call-arg]
                tool_name="Read",
                success=True,
                duration_ms=100,
            )

        assert "emitted_at" in str(exc_info.value)

    def test_missing_required_field_tool_name(
        self, sample_emitted_at: datetime
    ) -> None:
        """Test that missing tool_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(  # type: ignore[call-arg]
                emitted_at=sample_emitted_at,
                success=True,
                duration_ms=100,
            )

        assert "tool_name" in str(exc_info.value)

    def test_missing_required_field_success(self, sample_emitted_at: datetime) -> None:
        """Test that missing success raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(  # type: ignore[call-arg]
                emitted_at=sample_emitted_at,
                tool_name="Read",
                duration_ms=100,
            )

        assert "success" in str(exc_info.value)

    def test_missing_required_field_duration_ms(
        self, sample_emitted_at: datetime
    ) -> None:
        """Test that missing duration_ms raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(  # type: ignore[call-arg]
                emitted_at=sample_emitted_at,
                tool_name="Read",
                success=True,
            )

        assert "duration_ms" in str(exc_info.value)

    def test_emitted_at_requires_timezone(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that emitted_at rejects naive datetime."""
        minimal_tool_data["emitted_at"] = datetime(2025, 1, 1, 12, 0, 0)  # naive

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert "timezone" in str(exc_info.value).lower()

    def test_emitted_at_accepts_timezone_aware(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test that emitted_at accepts timezone-aware datetime."""
        minimal_tool_data["emitted_at"] = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        assert record.emitted_at.tzinfo is not None


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelClaudeCodeToolRecordSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test serialization to dictionary."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        data = record.model_dump()

        assert "tool_execution_id" in data
        assert "emitted_at" in data
        assert "tool_name" in data
        assert "success" in data
        assert "duration_ms" in data
        assert "summary" in data
        assert "causation_id" in data

    def test_model_dump_json(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test serialization to JSON string."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        json_str = record.model_dump_json()

        assert isinstance(json_str, str)
        assert "tool_execution_id" in json_str
        assert "tool_name" in json_str

    def test_round_trip_serialization(self, full_tool_data: dict[str, Any]) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelClaudeCodeToolRecord(**full_tool_data)
        data = original.model_dump()
        restored = ModelClaudeCodeToolRecord(**data)

        assert original.tool_execution_id == restored.tool_execution_id
        assert original.emitted_at == restored.emitted_at
        assert original.tool_name == restored.tool_name
        assert original.success == restored.success
        assert original.duration_ms == restored.duration_ms
        assert original.summary == restored.summary
        assert original.causation_id == restored.causation_id

    def test_json_round_trip_serialization(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelClaudeCodeToolRecord(**minimal_tool_data)

        json_str = original.model_dump_json()
        restored = ModelClaudeCodeToolRecord.model_validate_json(json_str)

        assert original.tool_execution_id == restored.tool_execution_id
        assert original.tool_name == restored.tool_name
        assert original.duration_ms == restored.duration_ms

    def test_model_validate_from_dict(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test model validation from dictionary."""
        record = ModelClaudeCodeToolRecord.model_validate(minimal_tool_data)

        assert record.tool_name == minimal_tool_data["tool_name"]
        assert record.success == minimal_tool_data["success"]


# ============================================================================
# Test: from_attributes Compatibility
# ============================================================================


class TestModelClaudeCodeToolRecordFromAttributes:
    """Tests for from_attributes compatibility (pytest-xdist support)."""

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes is enabled in model config."""
        assert ModelClaudeCodeToolRecord.model_config.get("from_attributes") is True

    def test_model_validate_with_existing_instance(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test model validation from an existing model instance."""
        original = ModelClaudeCodeToolRecord(**minimal_tool_data)

        # This should work due to from_attributes=True
        validated = ModelClaudeCodeToolRecord.model_validate(original)

        assert validated.tool_execution_id == original.tool_execution_id
        assert validated.tool_name == original.tool_name


# ============================================================================
# Test: Utility Methods
# ============================================================================


class TestModelClaudeCodeToolRecordUtilityMethods:
    """Tests for __str__ and __repr__ methods."""

    def test_str_representation_success(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test __str__ method returns expected format for success."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        str_repr = str(record)

        assert isinstance(str_repr, str)
        assert "ToolRecord" in str_repr
        assert minimal_tool_data["tool_name"] in str_repr
        assert "ok" in str_repr
        assert f"{minimal_tool_data['duration_ms']}ms" in str_repr

    def test_str_representation_failure(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test __str__ method returns expected format for failure."""
        minimal_tool_data["success"] = False
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        str_repr = str(record)

        assert "failed" in str_repr

    def test_repr_representation(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test __repr__ method returns string with class name."""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        repr_str = repr(record)

        assert isinstance(repr_str, str)
        assert "ModelClaudeCodeToolRecord" in repr_str
        assert "tool_execution_id=" in repr_str
        assert "tool_name=" in repr_str
        assert "success=" in repr_str
        assert "duration_ms=" in repr_str


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelClaudeCodeToolRecordEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_model_equality(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test model equality comparison with identical data."""
        tool_execution_id = uuid4()
        minimal_tool_data["tool_execution_id"] = tool_execution_id

        record1 = ModelClaudeCodeToolRecord(**minimal_tool_data)
        record2 = ModelClaudeCodeToolRecord(**minimal_tool_data)

        assert record1 == record2

    def test_model_inequality_different_id(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test model inequality when tool_execution_ids differ."""
        record1 = ModelClaudeCodeToolRecord(**minimal_tool_data)
        record2 = ModelClaudeCodeToolRecord(**minimal_tool_data)

        # Different auto-generated IDs
        assert record1 != record2

    def test_various_tool_names(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test with various common tool names."""
        tool_names = [
            "Read",
            "Write",
            "Edit",
            "Bash",
            "Glob",
            "Grep",
            "mcp__linear-server__create_issue",
        ]
        for tool_name in tool_names:
            minimal_tool_data["tool_name"] = tool_name
            record = ModelClaudeCodeToolRecord(**minimal_tool_data)
            assert record.tool_name == tool_name

    def test_large_duration(self, minimal_tool_data: dict[str, Any]) -> None:
        """Test with large duration value."""
        minimal_tool_data["duration_ms"] = 3600000  # 1 hour in ms
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        assert record.duration_ms == 3600000

    def test_special_characters_in_summary(
        self, minimal_tool_data: dict[str, Any]
    ) -> None:
        """Test summary with special characters."""
        minimal_tool_data["summary"] = "Error: 'file not found' at \"path/to/file\""
        record = ModelClaudeCodeToolRecord(**minimal_tool_data)
        assert record.summary == minimal_tool_data["summary"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
