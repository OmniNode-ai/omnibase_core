# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelCostEntry.

Tests comprehensive cost entry functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- Auto-generated entry_id
- Field type validation
- Non-negative constraints on numeric fields
- Serialization and deserialization
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.omnimemory import ModelCostEntry

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_entry_data() -> dict:
    """Minimal required data for creating a cost entry."""
    return {
        "timestamp": datetime.now(UTC),
        "operation": "chat_completion",
        "model_used": "gpt-4",
        "tokens_in": 100,
        "tokens_out": 50,
        "cost": 0.0045,
        "cumulative_total": 1.25,
    }


@pytest.fixture
def full_entry_data() -> dict:
    """Complete data including explicit entry_id."""
    return {
        "entry_id": uuid4(),
        "timestamp": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        "operation": "embedding",
        "model_used": "text-embedding-3-small",
        "tokens_in": 500,
        "tokens_out": 0,
        "cost": 0.00002,
        "cumulative_total": 5.50,
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelCostEntryInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_entry_data: dict) -> None:
        """Test creating entry with only required fields."""
        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.operation == "chat_completion"
        assert entry.model_used == "gpt-4"
        assert entry.tokens_in == 100
        assert entry.tokens_out == 50
        assert entry.cost == 0.0045
        assert entry.cumulative_total == 1.25
        assert isinstance(entry.entry_id, UUID)

    def test_create_with_full_data(self, full_entry_data: dict) -> None:
        """Test creating entry with all fields explicitly set."""
        entry = ModelCostEntry(**full_entry_data)

        assert entry.entry_id == full_entry_data["entry_id"]
        assert entry.operation == "embedding"
        assert entry.model_used == "text-embedding-3-small"

    def test_auto_generated_entry_id(self, minimal_entry_data: dict) -> None:
        """Test that entry_id is auto-generated when not provided."""
        entry1 = ModelCostEntry(**minimal_entry_data)
        entry2 = ModelCostEntry(**minimal_entry_data)

        assert isinstance(entry1.entry_id, UUID)
        assert isinstance(entry2.entry_id, UUID)
        assert entry1.entry_id != entry2.entry_id  # Each gets unique ID

    def test_timestamp_preserved(self, minimal_entry_data: dict) -> None:
        """Test that timestamp is properly stored."""
        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.timestamp == minimal_entry_data["timestamp"]
        assert isinstance(entry.timestamp, datetime)

    def test_various_operation_types(self, minimal_entry_data: dict) -> None:
        """Test various operation type strings."""
        operations = [
            "chat_completion",
            "embedding",
            "text_completion",
            "image_generation",
            "audio_transcription",
        ]
        for operation in operations:
            minimal_entry_data["operation"] = operation
            entry = ModelCostEntry(**minimal_entry_data)
            assert entry.operation == operation

    def test_various_model_names(self, minimal_entry_data: dict) -> None:
        """Test various model name strings."""
        models = [
            "gpt-4",
            "gpt-3.5-turbo",
            "text-embedding-3-small",
            "claude-3-opus",
            "llama-2-70b",
        ]
        for model in models:
            minimal_entry_data["model_used"] = model
            entry = ModelCostEntry(**minimal_entry_data)
            assert entry.model_used == model


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelCostEntryImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_entry_data: dict) -> None:
        """Test that the model is immutable."""
        entry = ModelCostEntry(**minimal_entry_data)

        with pytest.raises(ValidationError):
            entry.cost = 999.99  # type: ignore[misc]

    def test_cannot_modify_tokens_in(self, minimal_entry_data: dict) -> None:
        """Test that tokens_in cannot be modified."""
        entry = ModelCostEntry(**minimal_entry_data)

        with pytest.raises(ValidationError):
            entry.tokens_in = 9999  # type: ignore[misc]

    def test_cannot_modify_tokens_out(self, minimal_entry_data: dict) -> None:
        """Test that tokens_out cannot be modified."""
        entry = ModelCostEntry(**minimal_entry_data)

        with pytest.raises(ValidationError):
            entry.tokens_out = 9999  # type: ignore[misc]

    def test_cannot_modify_operation(self, minimal_entry_data: dict) -> None:
        """Test that operation string cannot be modified."""
        entry = ModelCostEntry(**minimal_entry_data)

        with pytest.raises(ValidationError):
            entry.operation = "modified_operation"  # type: ignore[misc]

    def test_cannot_modify_model_used(self, minimal_entry_data: dict) -> None:
        """Test that model_used cannot be modified."""
        entry = ModelCostEntry(**minimal_entry_data)

        with pytest.raises(ValidationError):
            entry.model_used = "different-model"  # type: ignore[misc]

    def test_cannot_modify_entry_id(self, minimal_entry_data: dict) -> None:
        """Test that entry_id cannot be modified."""
        entry = ModelCostEntry(**minimal_entry_data)

        with pytest.raises(ValidationError):
            entry.entry_id = uuid4()  # type: ignore[misc]

    def test_cannot_modify_cumulative_total(self, minimal_entry_data: dict) -> None:
        """Test that cumulative_total cannot be modified."""
        entry = ModelCostEntry(**minimal_entry_data)

        with pytest.raises(ValidationError):
            entry.cumulative_total = 999.99  # type: ignore[misc]


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelCostEntryValidation:
    """Tests for field validation constraints."""

    def test_tokens_in_must_be_non_negative(self, minimal_entry_data: dict) -> None:
        """Test that tokens_in rejects negative values."""
        minimal_entry_data["tokens_in"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "tokens_in" in str(exc_info.value)

    def test_tokens_out_must_be_non_negative(self, minimal_entry_data: dict) -> None:
        """Test that tokens_out rejects negative values."""
        minimal_entry_data["tokens_out"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "tokens_out" in str(exc_info.value)

    def test_cost_must_be_non_negative(self, minimal_entry_data: dict) -> None:
        """Test that cost rejects negative values."""
        minimal_entry_data["cost"] = -0.01

        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "cost" in str(exc_info.value)

    def test_cumulative_total_must_be_non_negative(
        self, minimal_entry_data: dict
    ) -> None:
        """Test that cumulative_total rejects negative values."""
        minimal_entry_data["cumulative_total"] = -1.0

        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "cumulative_total" in str(exc_info.value)

    def test_zero_values_accepted(self, minimal_entry_data: dict) -> None:
        """Test that zero values are valid for numeric fields."""
        minimal_entry_data["tokens_in"] = 0
        minimal_entry_data["tokens_out"] = 0
        minimal_entry_data["cost"] = 0.0
        minimal_entry_data["cumulative_total"] = 0.0

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.tokens_in == 0
        assert entry.tokens_out == 0
        assert entry.cost == 0.0
        assert entry.cumulative_total == 0.0

    def test_missing_required_field_timestamp(self) -> None:
        """Test that missing timestamp raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(
                operation="test",
                model_used="gpt-4",
                tokens_in=100,
                tokens_out=50,
                cost=0.01,
                cumulative_total=1.0,
            )
        assert "timestamp" in str(exc_info.value)

    def test_missing_required_field_operation(self, minimal_entry_data: dict) -> None:
        """Test that missing operation raises ValidationError."""
        del minimal_entry_data["operation"]
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)
        assert "operation" in str(exc_info.value)

    def test_missing_required_field_model_used(self, minimal_entry_data: dict) -> None:
        """Test that missing model_used raises ValidationError."""
        del minimal_entry_data["model_used"]
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)
        assert "model_used" in str(exc_info.value)

    def test_missing_required_field_tokens_in(self, minimal_entry_data: dict) -> None:
        """Test that missing tokens_in raises ValidationError."""
        del minimal_entry_data["tokens_in"]
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)
        assert "tokens_in" in str(exc_info.value)

    def test_missing_required_field_tokens_out(self, minimal_entry_data: dict) -> None:
        """Test that missing tokens_out raises ValidationError."""
        del minimal_entry_data["tokens_out"]
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)
        assert "tokens_out" in str(exc_info.value)

    def test_missing_required_field_cost(self, minimal_entry_data: dict) -> None:
        """Test that missing cost raises ValidationError."""
        del minimal_entry_data["cost"]
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)
        assert "cost" in str(exc_info.value)

    def test_missing_required_field_cumulative_total(
        self, minimal_entry_data: dict
    ) -> None:
        """Test that missing cumulative_total raises ValidationError."""
        del minimal_entry_data["cumulative_total"]
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)
        assert "cumulative_total" in str(exc_info.value)

    def test_large_token_values_accepted(self, minimal_entry_data: dict) -> None:
        """Test that large token values are accepted."""
        minimal_entry_data["tokens_in"] = 1_000_000
        minimal_entry_data["tokens_out"] = 500_000

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.tokens_in == 1_000_000
        assert entry.tokens_out == 500_000

    def test_float_precision_cost(self, minimal_entry_data: dict) -> None:
        """Test float precision for cost field."""
        minimal_entry_data["cost"] = 0.00000123

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.cost == 0.00000123

    def test_float_precision_cumulative_total(self, minimal_entry_data: dict) -> None:
        """Test float precision for cumulative_total field."""
        minimal_entry_data["cumulative_total"] = 12345.6789

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.cumulative_total == 12345.6789

    def test_naive_timestamp_rejected(self, minimal_entry_data: dict) -> None:
        """Test that naive datetime (without tzinfo) is rejected."""
        minimal_entry_data["timestamp"] = datetime(2025, 1, 1, 12, 0, 0)  # No tzinfo

        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "timestamp" in str(exc_info.value)
        assert "timezone-aware" in str(exc_info.value)

    def test_timezone_aware_timestamp_accepted(self, minimal_entry_data: dict) -> None:
        """Test that timezone-aware datetime is accepted."""
        # Test with UTC
        minimal_entry_data["timestamp"] = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = ModelCostEntry(**minimal_entry_data)
        assert entry.timestamp.tzinfo is not None

        # Test with explicit timezone offset
        tz_offset = UTC
        minimal_entry_data["timestamp"] = datetime(
            2025, 1, 1, 12, 0, 0, tzinfo=tz_offset
        )
        entry = ModelCostEntry(**minimal_entry_data)
        assert entry.timestamp.tzinfo is not None

    def test_cumulative_total_less_than_cost_rejected(
        self, minimal_entry_data: dict
    ) -> None:
        """Test that cumulative_total < cost is rejected."""
        minimal_entry_data["cost"] = 1.50
        minimal_entry_data["cumulative_total"] = 1.00  # Less than cost

        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "cumulative_total" in str(exc_info.value)
        assert "cost" in str(exc_info.value)

    def test_cumulative_total_equal_to_cost_accepted(
        self, minimal_entry_data: dict
    ) -> None:
        """Test that cumulative_total == cost is accepted (first entry case)."""
        minimal_entry_data["cost"] = 0.0045
        minimal_entry_data["cumulative_total"] = 0.0045  # Equal to cost

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.cost == entry.cumulative_total

    def test_cumulative_total_greater_than_cost_accepted(
        self, minimal_entry_data: dict
    ) -> None:
        """Test that cumulative_total > cost is accepted (normal case)."""
        minimal_entry_data["cost"] = 0.0045
        minimal_entry_data["cumulative_total"] = 10.0  # Greater than cost

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.cumulative_total > entry.cost


# ============================================================================
# Test: Type Coercion
# ============================================================================


class TestModelCostEntryTypeCoercion:
    """Tests for type coercion behavior."""

    def test_tokens_in_accepts_float_coerced_to_int(
        self, minimal_entry_data: dict
    ) -> None:
        """Test that float tokens_in is coerced to int."""
        minimal_entry_data["tokens_in"] = 100.0

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.tokens_in == 100
        assert isinstance(entry.tokens_in, int)

    def test_tokens_out_accepts_float_coerced_to_int(
        self, minimal_entry_data: dict
    ) -> None:
        """Test that float tokens_out is coerced to int."""
        minimal_entry_data["tokens_out"] = 50.0

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.tokens_out == 50
        assert isinstance(entry.tokens_out, int)

    def test_cost_accepts_int_coerced_to_float(self, minimal_entry_data: dict) -> None:
        """Test that int cost is coerced to float."""
        minimal_entry_data["cost"] = 1

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.cost == 1.0
        assert isinstance(entry.cost, float)


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelCostEntrySerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_entry_data: dict) -> None:
        """Test serialization to dictionary."""
        entry = ModelCostEntry(**minimal_entry_data)
        data = entry.model_dump()

        assert "entry_id" in data
        assert "timestamp" in data
        assert "operation" in data
        assert data["operation"] == "chat_completion"
        assert data["cost"] == 0.0045

    def test_model_dump_json(self, minimal_entry_data: dict) -> None:
        """Test serialization to JSON string."""
        entry = ModelCostEntry(**minimal_entry_data)
        json_str = entry.model_dump_json()

        assert isinstance(json_str, str)
        assert "chat_completion" in json_str
        assert "gpt-4" in json_str

    def test_round_trip_serialization(self, full_entry_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelCostEntry(**full_entry_data)
        data = original.model_dump()
        restored = ModelCostEntry(**data)

        assert original.entry_id == restored.entry_id
        assert original.operation == restored.operation
        assert original.cost == restored.cost
        assert original.cumulative_total == restored.cumulative_total

    def test_json_round_trip_serialization(self, full_entry_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelCostEntry(**full_entry_data)

        json_str = original.model_dump_json()
        restored = ModelCostEntry.model_validate_json(json_str)

        assert original.entry_id == restored.entry_id
        assert original.timestamp == restored.timestamp
        assert original.operation == restored.operation
        assert original.model_used == restored.model_used
        assert original.tokens_in == restored.tokens_in
        assert original.tokens_out == restored.tokens_out
        assert original.cost == restored.cost
        assert original.cumulative_total == restored.cumulative_total

    def test_model_dump_contains_all_fields(self, full_entry_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        entry = ModelCostEntry(**full_entry_data)
        data = entry.model_dump()

        expected_fields = [
            "entry_id",
            "timestamp",
            "operation",
            "model_used",
            "tokens_in",
            "tokens_out",
            "cost",
            "cumulative_total",
        ]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, full_entry_data: dict) -> None:
        """Test model validation from dictionary."""
        entry = ModelCostEntry.model_validate(full_entry_data)

        assert entry.entry_id == full_entry_data["entry_id"]
        assert entry.operation == full_entry_data["operation"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelCostEntryEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_operation_string_rejected(self, minimal_entry_data: dict) -> None:
        """Test that empty operation string is rejected."""
        minimal_entry_data["operation"] = ""

        # Empty string should be rejected (min_length=1 constraint)
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "operation" in str(exc_info.value)

    def test_empty_model_used_string_rejected(self, minimal_entry_data: dict) -> None:
        """Test that empty model_used string is rejected."""
        minimal_entry_data["model_used"] = ""

        # Empty string should be rejected (min_length=1 constraint)
        with pytest.raises(ValidationError) as exc_info:
            ModelCostEntry(**minimal_entry_data)

        assert "model_used" in str(exc_info.value)

    def test_operation_with_special_characters(self, minimal_entry_data: dict) -> None:
        """Test operation with special characters."""
        special_operations = [
            "chat-completion",
            "chat_completion",
            "chat.completion",
            "chat:completion",
            "chat completion",
        ]
        for operation in special_operations:
            minimal_entry_data["operation"] = operation
            entry = ModelCostEntry(**minimal_entry_data)
            assert entry.operation == operation

    def test_model_used_with_special_characters(self, minimal_entry_data: dict) -> None:
        """Test model_used with special characters."""
        special_models = [
            "gpt-4-turbo-preview",
            "claude_3_opus",
            "model.name.v1",
            "model:version:123",
        ]
        for model in special_models:
            minimal_entry_data["model_used"] = model
            entry = ModelCostEntry(**minimal_entry_data)
            assert entry.model_used == model

    def test_model_equality(self, minimal_entry_data: dict) -> None:
        """Test model equality comparison with same entry_id."""
        entry_id = uuid4()
        minimal_entry_data["entry_id"] = entry_id
        entry1 = ModelCostEntry(**minimal_entry_data)
        entry2 = ModelCostEntry(**minimal_entry_data)

        assert entry1 == entry2

    def test_model_inequality_different_entry_id(
        self, minimal_entry_data: dict
    ) -> None:
        """Test model inequality when entry_ids differ."""
        entry1 = ModelCostEntry(**minimal_entry_data)
        entry2 = ModelCostEntry(**minimal_entry_data)

        # Different auto-generated entry_ids
        assert entry1 != entry2

    def test_model_inequality_different_cost(self, minimal_entry_data: dict) -> None:
        """Test model inequality when cost differs."""
        entry_id = uuid4()
        minimal_entry_data["entry_id"] = entry_id

        entry1 = ModelCostEntry(**minimal_entry_data)

        minimal_entry_data["cost"] = 0.01
        entry2 = ModelCostEntry(**minimal_entry_data)

        assert entry1 != entry2

    def test_very_small_cost_value(self, minimal_entry_data: dict) -> None:
        """Test handling of very small cost values."""
        minimal_entry_data["cost"] = 0.000000001  # 1e-9

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.cost == 0.000000001

    def test_very_large_cumulative_total(self, minimal_entry_data: dict) -> None:
        """Test handling of very large cumulative_total values."""
        minimal_entry_data["cumulative_total"] = 999999999.99

        entry = ModelCostEntry(**minimal_entry_data)

        assert entry.cumulative_total == 999999999.99

    def test_str_representation(self, minimal_entry_data: dict) -> None:
        """Test __str__ method returns string."""
        entry = ModelCostEntry(**minimal_entry_data)
        str_repr = str(entry)

        assert isinstance(str_repr, str)
        assert "chat_completion" in str_repr or "ModelCostEntry" in str_repr

    def test_repr_representation(self, minimal_entry_data: dict) -> None:
        """Test __repr__ method returns string with class name."""
        entry = ModelCostEntry(**minimal_entry_data)
        repr_str = repr(entry)

        assert isinstance(repr_str, str)
        assert "ModelCostEntry" in repr_str

    def test_hash_consistency_for_same_data(self, minimal_entry_data: dict) -> None:
        """Test that frozen model is hashable and consistent."""
        entry_id = uuid4()
        minimal_entry_data["entry_id"] = entry_id

        entry1 = ModelCostEntry(**minimal_entry_data)
        entry2 = ModelCostEntry(**minimal_entry_data)

        # Frozen models should be hashable
        assert hash(entry1) == hash(entry2)

    def test_can_use_as_dict_key(self, minimal_entry_data: dict) -> None:
        """Test that frozen model can be used as dictionary key."""
        entry_id = uuid4()
        minimal_entry_data["entry_id"] = entry_id

        entry = ModelCostEntry(**minimal_entry_data)

        # Should be usable as dict key
        test_dict = {entry: "value"}
        assert test_dict[entry] == "value"

    def test_can_add_to_set(self, minimal_entry_data: dict) -> None:
        """Test that frozen model can be added to set."""
        entry_id = uuid4()
        minimal_entry_data["entry_id"] = entry_id

        entry1 = ModelCostEntry(**minimal_entry_data)
        entry2 = ModelCostEntry(**minimal_entry_data)

        # Should be usable in sets
        test_set = {entry1, entry2}
        assert len(test_set) == 1  # Same entry_id, same hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
