# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelDecisionRecord.

Tests comprehensive decision record functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- Auto-generated decision_id
- Confidence bounds (0.0-1.0)
- Timezone-aware timestamp validation
- Serialization and deserialization
- Outcome literal values
- chosen_option in options_considered validation
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_decision_type import EnumDecisionType
from omnibase_core.models.omnimemory.model_decision_record import ModelDecisionRecord

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_record_data() -> dict:
    """Minimal required data for creating a decision record."""
    return {
        "decision_type": EnumDecisionType.MODEL_SELECTION,
        "timestamp": datetime.now(UTC),
        "options_considered": ("gpt-4", "claude-3-opus"),
        "chosen_option": "gpt-4",
        "confidence": 0.85,
        "input_hash": "abc123def456",
    }


@pytest.fixture
def full_record_data() -> dict:
    """Complete data including all optional fields."""
    return {
        "decision_id": uuid4(),
        "decision_type": EnumDecisionType.TOOL_SELECTION,
        "timestamp": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        "options_considered": ("search", "calculate", "write_file"),
        "chosen_option": "search",
        "confidence": 0.92,
        "rationale": "Search is most appropriate for information retrieval tasks",
        "input_hash": "hash_xyz_789",
        "cost_impact": 0.0025,
        "outcome": "success",
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelDecisionRecordInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_record_data: dict) -> None:
        """Test creating record with only required fields."""
        record = ModelDecisionRecord(**minimal_record_data)

        assert record.decision_type == EnumDecisionType.MODEL_SELECTION
        assert record.options_considered == ("gpt-4", "claude-3-opus")
        assert record.chosen_option == "gpt-4"
        assert record.confidence == 0.85
        assert record.input_hash == "abc123def456"
        assert isinstance(record.decision_id, UUID)
        # Optional fields should be None
        assert record.rationale is None
        assert record.cost_impact is None
        assert record.outcome is None

    def test_create_with_full_data(self, full_record_data: dict) -> None:
        """Test creating record with all fields explicitly set."""
        record = ModelDecisionRecord(**full_record_data)

        assert record.decision_id == full_record_data["decision_id"]
        assert record.decision_type == EnumDecisionType.TOOL_SELECTION
        assert record.chosen_option == "search"
        assert (
            record.rationale
            == "Search is most appropriate for information retrieval tasks"
        )
        assert record.cost_impact == 0.0025
        assert record.outcome == "success"

    def test_auto_generated_decision_id(self, minimal_record_data: dict) -> None:
        """Test that decision_id is auto-generated when not provided."""
        record1 = ModelDecisionRecord(**minimal_record_data)
        record2 = ModelDecisionRecord(**minimal_record_data)

        assert isinstance(record1.decision_id, UUID)
        assert isinstance(record2.decision_id, UUID)
        assert record1.decision_id != record2.decision_id  # Each gets unique ID

    def test_timestamp_preserved(self, minimal_record_data: dict) -> None:
        """Test that timestamp is properly stored."""
        record = ModelDecisionRecord(**minimal_record_data)

        assert record.timestamp == minimal_record_data["timestamp"]
        assert isinstance(record.timestamp, datetime)

    def test_various_decision_types(self, minimal_record_data: dict) -> None:
        """Test various decision type enum values."""
        decision_types = [
            EnumDecisionType.MODEL_SELECTION,
            EnumDecisionType.ROUTE_CHOICE,
            EnumDecisionType.RETRY_STRATEGY,
            EnumDecisionType.TOOL_SELECTION,
            EnumDecisionType.ESCALATION,
            EnumDecisionType.EARLY_TERMINATION,
            EnumDecisionType.PARAMETER_CHOICE,
            EnumDecisionType.CUSTOM,
        ]
        for decision_type in decision_types:
            minimal_record_data["decision_type"] = decision_type
            record = ModelDecisionRecord(**minimal_record_data)
            assert record.decision_type == decision_type

    def test_decision_type_from_string(self, minimal_record_data: dict) -> None:
        """Test that decision_type accepts string values."""
        minimal_record_data["decision_type"] = "model_selection"
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.decision_type == EnumDecisionType.MODEL_SELECTION


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelDecisionRecordImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_record_data: dict) -> None:
        """Test that the model is immutable."""
        record = ModelDecisionRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            record.confidence = 0.99  # type: ignore[misc]

    def test_cannot_modify_chosen_option(self, minimal_record_data: dict) -> None:
        """Test that chosen_option cannot be modified."""
        record = ModelDecisionRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            record.chosen_option = "different-model"  # type: ignore[misc]

    def test_cannot_modify_decision_type(self, minimal_record_data: dict) -> None:
        """Test that decision_type cannot be modified."""
        record = ModelDecisionRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            record.decision_type = EnumDecisionType.ESCALATION  # type: ignore[misc]

    def test_cannot_modify_decision_id(self, minimal_record_data: dict) -> None:
        """Test that decision_id cannot be modified."""
        record = ModelDecisionRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            record.decision_id = uuid4()  # type: ignore[misc]

    def test_cannot_modify_outcome(self, full_record_data: dict) -> None:
        """Test that outcome cannot be modified."""
        record = ModelDecisionRecord(**full_record_data)

        with pytest.raises(ValidationError):
            record.outcome = "failure"  # type: ignore[misc]

    def test_cannot_modify_options_considered(self, minimal_record_data: dict) -> None:
        """Test that options_considered cannot be modified."""
        record = ModelDecisionRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            record.options_considered = ("new", "options")  # type: ignore[misc]


# ============================================================================
# Test: Confidence Bounds Validation
# ============================================================================


class TestModelDecisionRecordConfidenceValidation:
    """Tests for confidence field bounds validation."""

    def test_confidence_at_minimum(self, minimal_record_data: dict) -> None:
        """Test that confidence of 0.0 is accepted."""
        minimal_record_data["confidence"] = 0.0
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.confidence == 0.0

    def test_confidence_at_maximum(self, minimal_record_data: dict) -> None:
        """Test that confidence of 1.0 is accepted."""
        minimal_record_data["confidence"] = 1.0
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.confidence == 1.0

    def test_confidence_in_middle(self, minimal_record_data: dict) -> None:
        """Test that confidence of 0.5 is accepted."""
        minimal_record_data["confidence"] = 0.5
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.confidence == 0.5

    def test_confidence_below_minimum_rejected(self, minimal_record_data: dict) -> None:
        """Test that confidence below 0.0 is rejected."""
        minimal_record_data["confidence"] = -0.01

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "confidence" in str(exc_info.value)

    def test_confidence_above_maximum_rejected(self, minimal_record_data: dict) -> None:
        """Test that confidence above 1.0 is rejected."""
        minimal_record_data["confidence"] = 1.01

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "confidence" in str(exc_info.value)

    def test_confidence_high_precision(self, minimal_record_data: dict) -> None:
        """Test that high-precision confidence values are accepted."""
        minimal_record_data["confidence"] = 0.123456789
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.confidence == 0.123456789


# ============================================================================
# Test: Timestamp Validation
# ============================================================================


class TestModelDecisionRecordTimestampValidation:
    """Tests for timestamp timezone validation."""

    def test_naive_timestamp_rejected(self, minimal_record_data: dict) -> None:
        """Test that naive datetime (without tzinfo) is rejected."""
        minimal_record_data["timestamp"] = datetime(2025, 1, 1, 12, 0, 0)  # No tzinfo

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "timestamp" in str(exc_info.value)
        assert "timezone-aware" in str(exc_info.value)

    def test_timezone_aware_timestamp_accepted(self, minimal_record_data: dict) -> None:
        """Test that timezone-aware datetime is accepted."""
        minimal_record_data["timestamp"] = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.timestamp.tzinfo is not None

    def test_datetime_now_utc_accepted(self, minimal_record_data: dict) -> None:
        """Test that datetime.now(UTC) is accepted."""
        minimal_record_data["timestamp"] = datetime.now(UTC)
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.timestamp.tzinfo is not None


# ============================================================================
# Test: Options Considered Validation
# ============================================================================


class TestModelDecisionRecordOptionsValidation:
    """Tests for options_considered and chosen_option validation."""

    def test_chosen_option_must_be_in_options(self, minimal_record_data: dict) -> None:
        """Test that chosen_option must be in options_considered."""
        minimal_record_data["options_considered"] = ("option_a", "option_b")
        minimal_record_data["chosen_option"] = "option_c"  # Not in options

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "chosen_option" in str(exc_info.value)
        assert "options_considered" in str(exc_info.value)

    def test_chosen_option_valid_when_in_options(
        self, minimal_record_data: dict
    ) -> None:
        """Test that chosen_option is valid when in options_considered."""
        minimal_record_data["options_considered"] = ("option_a", "option_b", "option_c")
        minimal_record_data["chosen_option"] = "option_b"

        record = ModelDecisionRecord(**minimal_record_data)
        assert record.chosen_option == "option_b"

    def test_empty_options_allows_any_chosen_option(
        self, minimal_record_data: dict
    ) -> None:
        """Test that empty options_considered allows any chosen_option."""
        minimal_record_data["options_considered"] = ()
        minimal_record_data["chosen_option"] = "any_option"

        record = ModelDecisionRecord(**minimal_record_data)
        assert record.chosen_option == "any_option"
        assert record.options_considered == ()

    def test_single_option_considered(self, minimal_record_data: dict) -> None:
        """Test with single option in options_considered."""
        minimal_record_data["options_considered"] = ("only_option",)
        minimal_record_data["chosen_option"] = "only_option"

        record = ModelDecisionRecord(**minimal_record_data)
        assert record.chosen_option == "only_option"

    def test_many_options_considered(self, minimal_record_data: dict) -> None:
        """Test with many options in options_considered."""
        options = tuple(f"option_{i}" for i in range(100))
        minimal_record_data["options_considered"] = options
        minimal_record_data["chosen_option"] = "option_50"

        record = ModelDecisionRecord(**minimal_record_data)
        assert len(record.options_considered) == 100
        assert record.chosen_option == "option_50"

    def test_empty_chosen_option_rejected(self, minimal_record_data: dict) -> None:
        """Test that empty chosen_option string is rejected."""
        minimal_record_data["options_considered"] = ()
        minimal_record_data["chosen_option"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "chosen_option" in str(exc_info.value)


# ============================================================================
# Test: Outcome Literal Values
# ============================================================================


class TestModelDecisionRecordOutcomeValidation:
    """Tests for outcome literal value validation."""

    def test_outcome_success(self, minimal_record_data: dict) -> None:
        """Test that outcome='success' is accepted."""
        minimal_record_data["outcome"] = "success"
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.outcome == "success"

    def test_outcome_failure(self, minimal_record_data: dict) -> None:
        """Test that outcome='failure' is accepted."""
        minimal_record_data["outcome"] = "failure"
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.outcome == "failure"

    def test_outcome_unknown(self, minimal_record_data: dict) -> None:
        """Test that outcome='unknown' is accepted."""
        minimal_record_data["outcome"] = "unknown"
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.outcome == "unknown"

    def test_outcome_none(self, minimal_record_data: dict) -> None:
        """Test that outcome=None is accepted (default)."""
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.outcome is None

    def test_outcome_invalid_value_rejected(self, minimal_record_data: dict) -> None:
        """Test that invalid outcome values are rejected."""
        minimal_record_data["outcome"] = "invalid_outcome"

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "outcome" in str(exc_info.value)


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelDecisionRecordFieldValidation:
    """Tests for field validation constraints."""

    def test_missing_required_field_decision_type(
        self, minimal_record_data: dict
    ) -> None:
        """Test that missing decision_type raises ValidationError."""
        del minimal_record_data["decision_type"]
        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)
        assert "decision_type" in str(exc_info.value)

    def test_missing_required_field_timestamp(self, minimal_record_data: dict) -> None:
        """Test that missing timestamp raises ValidationError."""
        del minimal_record_data["timestamp"]
        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)
        assert "timestamp" in str(exc_info.value)

    def test_missing_required_field_options_considered(
        self, minimal_record_data: dict
    ) -> None:
        """Test that missing options_considered raises ValidationError."""
        del minimal_record_data["options_considered"]
        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)
        assert "options_considered" in str(exc_info.value)

    def test_missing_required_field_chosen_option(
        self, minimal_record_data: dict
    ) -> None:
        """Test that missing chosen_option raises ValidationError."""
        del minimal_record_data["chosen_option"]
        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)
        assert "chosen_option" in str(exc_info.value)

    def test_missing_required_field_confidence(self, minimal_record_data: dict) -> None:
        """Test that missing confidence raises ValidationError."""
        del minimal_record_data["confidence"]
        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)
        assert "confidence" in str(exc_info.value)

    def test_missing_required_field_input_hash(self, minimal_record_data: dict) -> None:
        """Test that missing input_hash raises ValidationError."""
        del minimal_record_data["input_hash"]
        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)
        assert "input_hash" in str(exc_info.value)

    def test_empty_input_hash_rejected(self, minimal_record_data: dict) -> None:
        """Test that empty input_hash string is rejected."""
        minimal_record_data["input_hash"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "input_hash" in str(exc_info.value)

    def test_cost_impact_positive(self, minimal_record_data: dict) -> None:
        """Test that positive cost_impact is accepted."""
        minimal_record_data["cost_impact"] = 0.0025
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.cost_impact == 0.0025

    def test_cost_impact_zero(self, minimal_record_data: dict) -> None:
        """Test that zero cost_impact is accepted."""
        minimal_record_data["cost_impact"] = 0.0
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.cost_impact == 0.0

    def test_cost_impact_negative(self, minimal_record_data: dict) -> None:
        """Test that negative cost_impact is accepted (savings)."""
        minimal_record_data["cost_impact"] = -0.001
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.cost_impact == -0.001


# ============================================================================
# Test: Type Coercion
# ============================================================================


class TestModelDecisionRecordTypeCoercion:
    """Tests for type coercion behavior."""

    def test_confidence_accepts_int_coerced_to_float(
        self, minimal_record_data: dict
    ) -> None:
        """Test that int confidence is coerced to float."""
        minimal_record_data["confidence"] = 1
        record = ModelDecisionRecord(**minimal_record_data)
        assert record.confidence == 1.0
        assert isinstance(record.confidence, float)

    def test_options_considered_from_list(self, minimal_record_data: dict) -> None:
        """Test that list is converted to tuple for options_considered."""
        minimal_record_data["options_considered"] = ["option_a", "option_b"]
        minimal_record_data["chosen_option"] = "option_a"

        record = ModelDecisionRecord(**minimal_record_data)
        assert record.options_considered == ("option_a", "option_b")
        assert isinstance(record.options_considered, tuple)


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelDecisionRecordSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_record_data: dict) -> None:
        """Test serialization to dictionary."""
        record = ModelDecisionRecord(**minimal_record_data)
        data = record.model_dump()

        assert "decision_id" in data
        assert "decision_type" in data
        assert "timestamp" in data
        assert "chosen_option" in data
        assert data["confidence"] == 0.85

    def test_model_dump_json(self, minimal_record_data: dict) -> None:
        """Test serialization to JSON string."""
        record = ModelDecisionRecord(**minimal_record_data)
        json_str = record.model_dump_json()

        assert isinstance(json_str, str)
        assert "gpt-4" in json_str
        assert "0.85" in json_str

    def test_round_trip_serialization(self, full_record_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelDecisionRecord(**full_record_data)
        data = original.model_dump()
        restored = ModelDecisionRecord(**data)

        assert original.decision_id == restored.decision_id
        assert original.decision_type == restored.decision_type
        assert original.chosen_option == restored.chosen_option
        assert original.confidence == restored.confidence
        assert original.outcome == restored.outcome

    def test_json_round_trip_serialization(self, full_record_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelDecisionRecord(**full_record_data)

        json_str = original.model_dump_json()
        restored = ModelDecisionRecord.model_validate_json(json_str)

        assert original.decision_id == restored.decision_id
        assert original.timestamp == restored.timestamp
        assert original.decision_type == restored.decision_type
        assert original.options_considered == restored.options_considered
        assert original.chosen_option == restored.chosen_option
        assert original.confidence == restored.confidence
        assert original.rationale == restored.rationale
        assert original.input_hash == restored.input_hash
        assert original.cost_impact == restored.cost_impact
        assert original.outcome == restored.outcome

    def test_model_dump_contains_all_fields(self, full_record_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        record = ModelDecisionRecord(**full_record_data)
        data = record.model_dump()

        expected_fields = [
            "decision_id",
            "decision_type",
            "timestamp",
            "options_considered",
            "chosen_option",
            "confidence",
            "rationale",
            "input_hash",
            "cost_impact",
            "outcome",
        ]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, full_record_data: dict) -> None:
        """Test model validation from dictionary."""
        record = ModelDecisionRecord.model_validate(full_record_data)

        assert record.decision_id == full_record_data["decision_id"]
        assert record.decision_type == full_record_data["decision_type"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelDecisionRecordEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_special_characters_in_options(self, minimal_record_data: dict) -> None:
        """Test options with special characters."""
        special_options = ("option-with-dash", "option_with_underscore", "option.dot")
        minimal_record_data["options_considered"] = special_options
        minimal_record_data["chosen_option"] = "option-with-dash"

        record = ModelDecisionRecord(**minimal_record_data)
        assert record.options_considered == special_options

    def test_unicode_in_rationale(self, minimal_record_data: dict) -> None:
        """Test unicode characters in rationale."""
        minimal_record_data["rationale"] = "Decision made with confidence: 85%"

        record = ModelDecisionRecord(**minimal_record_data)
        assert "85%" in record.rationale  # type: ignore[operator]

    def test_long_rationale(self, minimal_record_data: dict) -> None:
        """Test with very long rationale string."""
        long_rationale = "A" * 10000
        minimal_record_data["rationale"] = long_rationale

        record = ModelDecisionRecord(**minimal_record_data)
        assert len(record.rationale) == 10000  # type: ignore[arg-type]

    def test_model_equality(self, minimal_record_data: dict) -> None:
        """Test model equality comparison with same decision_id."""
        decision_id = uuid4()
        minimal_record_data["decision_id"] = decision_id
        record1 = ModelDecisionRecord(**minimal_record_data)
        record2 = ModelDecisionRecord(**minimal_record_data)

        assert record1 == record2

    def test_model_inequality_different_decision_id(
        self, minimal_record_data: dict
    ) -> None:
        """Test model inequality when decision_ids differ."""
        record1 = ModelDecisionRecord(**minimal_record_data)
        record2 = ModelDecisionRecord(**minimal_record_data)

        # Different auto-generated decision_ids
        assert record1 != record2

    def test_model_inequality_different_confidence(
        self, minimal_record_data: dict
    ) -> None:
        """Test model inequality when confidence differs."""
        decision_id = uuid4()
        minimal_record_data["decision_id"] = decision_id

        record1 = ModelDecisionRecord(**minimal_record_data)

        minimal_record_data["confidence"] = 0.95
        record2 = ModelDecisionRecord(**minimal_record_data)

        assert record1 != record2

    def test_str_representation(self, minimal_record_data: dict) -> None:
        """Test __str__ method returns meaningful string."""
        record = ModelDecisionRecord(**minimal_record_data)
        str_repr = str(record)

        assert isinstance(str_repr, str)
        assert "DecisionRecord" in str_repr
        assert "gpt-4" in str_repr

    def test_repr_representation(self, minimal_record_data: dict) -> None:
        """Test __repr__ method returns string with class name."""
        record = ModelDecisionRecord(**minimal_record_data)
        repr_str = repr(record)

        assert isinstance(repr_str, str)
        assert "ModelDecisionRecord" in repr_str

    def test_hash_consistency_for_same_data(self, minimal_record_data: dict) -> None:
        """Test that frozen model is hashable and consistent."""
        decision_id = uuid4()
        minimal_record_data["decision_id"] = decision_id

        record1 = ModelDecisionRecord(**minimal_record_data)
        record2 = ModelDecisionRecord(**minimal_record_data)

        # Frozen models should be hashable
        assert hash(record1) == hash(record2)

    def test_can_use_as_dict_key(self, minimal_record_data: dict) -> None:
        """Test that frozen model can be used as dictionary key."""
        decision_id = uuid4()
        minimal_record_data["decision_id"] = decision_id

        record = ModelDecisionRecord(**minimal_record_data)

        # Should be usable as dict key
        test_dict = {record: "value"}
        assert test_dict[record] == "value"

    def test_can_add_to_set(self, minimal_record_data: dict) -> None:
        """Test that frozen model can be added to set."""
        decision_id = uuid4()
        minimal_record_data["decision_id"] = decision_id

        record1 = ModelDecisionRecord(**minimal_record_data)
        record2 = ModelDecisionRecord(**minimal_record_data)

        # Should be usable in sets
        test_set = {record1, record2}
        assert len(test_set) == 1  # Same decision_id, same hash

    def test_extra_fields_forbidden(self, minimal_record_data: dict) -> None:
        """Test that extra fields are forbidden."""
        minimal_record_data["extra_field"] = "not_allowed"

        with pytest.raises(ValidationError) as exc_info:
            ModelDecisionRecord(**minimal_record_data)

        assert "extra_field" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
