# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelMemoryDiff.

Tests comprehensive memory diff functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- Auto-generated diff_id
- Snapshot ID validation (must be different)
- Utility properties (has_changes, decision_change_count, failure_change_count)
- Serialization and deserialization
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_decision_type import EnumDecisionType
from omnibase_core.enums.enum_failure_type import EnumFailureType
from omnibase_core.models.omnimemory.model_decision_record import ModelDecisionRecord
from omnibase_core.models.omnimemory.model_failure_record import ModelFailureRecord
from omnibase_core.models.omnimemory.model_memory_diff import ModelMemoryDiff

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_diff_data() -> dict:
    """Minimal required data for creating a memory diff."""
    return {
        "base_snapshot_id": uuid4(),
        "target_snapshot_id": uuid4(),
    }


@pytest.fixture
def sample_decision_record() -> ModelDecisionRecord:
    """Sample decision record for testing."""
    return ModelDecisionRecord(
        decision_type=EnumDecisionType.MODEL_SELECTION,
        timestamp=datetime.now(UTC),
        options_considered=("gpt-4", "claude-3"),
        chosen_option="gpt-4",
        confidence=0.85,
        input_hash="abc123",
    )


@pytest.fixture
def sample_failure_record() -> ModelFailureRecord:
    """Sample failure record for testing."""
    return ModelFailureRecord(
        timestamp=datetime.now(UTC),
        failure_type=EnumFailureType.TIMEOUT,
        step_context="code_generation",
        error_code="TIMEOUT_001",
        error_message="Operation exceeded 30s timeout",
    )


@pytest.fixture
def full_diff_data(
    sample_decision_record: ModelDecisionRecord,
    sample_failure_record: ModelFailureRecord,
) -> dict:
    """Complete data including all optional fields."""
    return {
        "diff_id": uuid4(),
        "base_snapshot_id": uuid4(),
        "target_snapshot_id": uuid4(),
        "decisions_added": (sample_decision_record,),
        "decisions_removed": (uuid4(), uuid4()),
        "failures_added": (sample_failure_record,),
        "cost_delta": 0.05,
        "summary": "Added 1 decision, removed 2 decisions, added 1 failure",
        "computed_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelMemoryDiffInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_diff_data: dict) -> None:
        """Test creating diff with only required fields."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.base_snapshot_id == minimal_diff_data["base_snapshot_id"]
        assert diff.target_snapshot_id == minimal_diff_data["target_snapshot_id"]
        assert isinstance(diff.diff_id, UUID)
        assert diff.decisions_added == ()
        assert diff.decisions_removed == ()
        assert diff.failures_added == ()
        assert diff.cost_delta == 0.0
        assert diff.summary == ""
        assert isinstance(diff.computed_at, datetime)

    def test_create_with_full_data(self, full_diff_data: dict) -> None:
        """Test creating diff with all fields explicitly set."""
        diff = ModelMemoryDiff(**full_diff_data)

        assert diff.diff_id == full_diff_data["diff_id"]
        assert diff.base_snapshot_id == full_diff_data["base_snapshot_id"]
        assert diff.target_snapshot_id == full_diff_data["target_snapshot_id"]
        assert len(diff.decisions_added) == 1
        assert len(diff.decisions_removed) == 2
        assert len(diff.failures_added) == 1
        assert diff.cost_delta == 0.05
        assert "Added 1 decision" in diff.summary

    def test_auto_generated_diff_id(self, minimal_diff_data: dict) -> None:
        """Test that diff_id is auto-generated when not provided."""
        diff1 = ModelMemoryDiff(**minimal_diff_data)
        # Create new snapshot IDs for second diff
        minimal_diff_data["base_snapshot_id"] = uuid4()
        minimal_diff_data["target_snapshot_id"] = uuid4()
        diff2 = ModelMemoryDiff(**minimal_diff_data)

        assert isinstance(diff1.diff_id, UUID)
        assert isinstance(diff2.diff_id, UUID)
        assert diff1.diff_id != diff2.diff_id  # Each gets unique ID

    def test_auto_generated_computed_at(self, minimal_diff_data: dict) -> None:
        """Test that computed_at is auto-generated with timezone."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert isinstance(diff.computed_at, datetime)
        assert diff.computed_at.tzinfo is not None


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelMemoryDiffImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_diff_data: dict) -> None:
        """Test that the model is immutable."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        with pytest.raises(ValidationError):
            diff.cost_delta = 999.99

    def test_cannot_modify_base_snapshot_id(self, minimal_diff_data: dict) -> None:
        """Test that base_snapshot_id cannot be modified."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        with pytest.raises(ValidationError):
            diff.base_snapshot_id = uuid4()

    def test_cannot_modify_target_snapshot_id(self, minimal_diff_data: dict) -> None:
        """Test that target_snapshot_id cannot be modified."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        with pytest.raises(ValidationError):
            diff.target_snapshot_id = uuid4()

    def test_cannot_modify_diff_id(self, minimal_diff_data: dict) -> None:
        """Test that diff_id cannot be modified."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        with pytest.raises(ValidationError):
            diff.diff_id = uuid4()

    def test_cannot_modify_summary(self, minimal_diff_data: dict) -> None:
        """Test that summary cannot be modified."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        with pytest.raises(ValidationError):
            diff.summary = "modified summary"


# ============================================================================
# Test: Snapshot ID Validation
# ============================================================================


class TestModelMemoryDiffSnapshotValidation:
    """Tests for base_snapshot_id != target_snapshot_id validation."""

    def test_same_snapshot_id_rejected(self) -> None:
        """Test that same base and target snapshot IDs are rejected."""
        same_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            ModelMemoryDiff(
                base_snapshot_id=same_id,
                target_snapshot_id=same_id,
            )

        assert "base_snapshot_id" in str(exc_info.value)
        assert "target_snapshot_id" in str(exc_info.value)

    def test_different_snapshot_ids_accepted(self, minimal_diff_data: dict) -> None:
        """Test that different snapshot IDs are accepted."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.base_snapshot_id != diff.target_snapshot_id


# ============================================================================
# Test: has_changes Property
# ============================================================================


class TestModelMemoryDiffHasChanges:
    """Tests for has_changes property."""

    def test_has_changes_false_when_empty(self, minimal_diff_data: dict) -> None:
        """Test has_changes returns False when no changes exist."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.has_changes is False

    def test_has_changes_true_with_decisions_added(
        self, minimal_diff_data: dict, sample_decision_record: ModelDecisionRecord
    ) -> None:
        """Test has_changes returns True when decisions are added."""
        minimal_diff_data["decisions_added"] = (sample_decision_record,)
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.has_changes is True

    def test_has_changes_true_with_decisions_removed(
        self, minimal_diff_data: dict
    ) -> None:
        """Test has_changes returns True when decisions are removed."""
        minimal_diff_data["decisions_removed"] = (uuid4(),)
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.has_changes is True

    def test_has_changes_true_with_failures_added(
        self, minimal_diff_data: dict, sample_failure_record: ModelFailureRecord
    ) -> None:
        """Test has_changes returns True when failures are added."""
        minimal_diff_data["failures_added"] = (sample_failure_record,)
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.has_changes is True

    def test_has_changes_true_with_positive_cost_delta(
        self, minimal_diff_data: dict
    ) -> None:
        """Test has_changes returns True with positive cost delta."""
        minimal_diff_data["cost_delta"] = 0.01
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.has_changes is True

    def test_has_changes_true_with_negative_cost_delta(
        self, minimal_diff_data: dict
    ) -> None:
        """Test has_changes returns True with negative cost delta."""
        minimal_diff_data["cost_delta"] = -0.01
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.has_changes is True

    def test_has_changes_false_with_zero_cost_delta(
        self, minimal_diff_data: dict
    ) -> None:
        """Test has_changes returns False with zero cost delta only."""
        minimal_diff_data["cost_delta"] = 0.0
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.has_changes is False


# ============================================================================
# Test: decision_change_count Property
# ============================================================================


class TestModelMemoryDiffDecisionChangeCount:
    """Tests for decision_change_count property."""

    def test_decision_change_count_zero_when_empty(
        self, minimal_diff_data: dict
    ) -> None:
        """Test decision_change_count returns 0 when no decision changes."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.decision_change_count == 0

    def test_decision_change_count_with_added_only(
        self, minimal_diff_data: dict, sample_decision_record: ModelDecisionRecord
    ) -> None:
        """Test decision_change_count counts added decisions."""
        minimal_diff_data["decisions_added"] = (
            sample_decision_record,
            sample_decision_record,
        )
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.decision_change_count == 2

    def test_decision_change_count_with_removed_only(
        self, minimal_diff_data: dict
    ) -> None:
        """Test decision_change_count counts removed decisions."""
        minimal_diff_data["decisions_removed"] = (uuid4(), uuid4(), uuid4())
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.decision_change_count == 3

    def test_decision_change_count_with_both(
        self, minimal_diff_data: dict, sample_decision_record: ModelDecisionRecord
    ) -> None:
        """Test decision_change_count sums added and removed."""
        minimal_diff_data["decisions_added"] = (sample_decision_record,)
        minimal_diff_data["decisions_removed"] = (uuid4(), uuid4())
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.decision_change_count == 3  # 1 added + 2 removed


# ============================================================================
# Test: failure_change_count Property
# ============================================================================


class TestModelMemoryDiffFailureChangeCount:
    """Tests for failure_change_count property."""

    def test_failure_change_count_zero_when_empty(
        self, minimal_diff_data: dict
    ) -> None:
        """Test failure_change_count returns 0 when no failure changes."""
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.failure_change_count == 0

    def test_failure_change_count_with_failures(
        self, minimal_diff_data: dict, sample_failure_record: ModelFailureRecord
    ) -> None:
        """Test failure_change_count counts added failures."""
        minimal_diff_data["failures_added"] = (
            sample_failure_record,
            sample_failure_record,
        )
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.failure_change_count == 2


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelMemoryDiffValidation:
    """Tests for field validation constraints."""

    def test_missing_required_field_base_snapshot_id(self) -> None:
        """Test that missing base_snapshot_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE: Intentionally testing Pydantic validation - mypy correctly flags missing required arg
            ModelMemoryDiff(target_snapshot_id=uuid4())  # type: ignore[call-arg]

        assert "base_snapshot_id" in str(exc_info.value)

    def test_missing_required_field_target_snapshot_id(self) -> None:
        """Test that missing target_snapshot_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE: Intentionally testing Pydantic validation - mypy correctly flags missing required arg
            ModelMemoryDiff(base_snapshot_id=uuid4())  # type: ignore[call-arg]

        assert "target_snapshot_id" in str(exc_info.value)

    def test_negative_cost_delta_accepted(self, minimal_diff_data: dict) -> None:
        """Test that negative cost_delta is accepted (cost can decrease)."""
        minimal_diff_data["cost_delta"] = -5.50
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.cost_delta == -5.50

    def test_large_cost_delta_accepted(self, minimal_diff_data: dict) -> None:
        """Test that large cost_delta values are accepted."""
        minimal_diff_data["cost_delta"] = 999999.99
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.cost_delta == 999999.99

    def test_extra_fields_rejected(self, minimal_diff_data: dict) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        minimal_diff_data["unknown_field"] = "value"

        with pytest.raises(ValidationError) as exc_info:
            ModelMemoryDiff(**minimal_diff_data)

        assert "extra" in str(exc_info.value).lower()


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelMemoryDiffSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_diff_data: dict) -> None:
        """Test serialization to dictionary."""
        diff = ModelMemoryDiff(**minimal_diff_data)
        data = diff.model_dump()

        assert "diff_id" in data
        assert "base_snapshot_id" in data
        assert "target_snapshot_id" in data
        assert "decisions_added" in data
        assert "decisions_removed" in data
        assert "failures_added" in data
        assert "cost_delta" in data
        assert "summary" in data
        assert "computed_at" in data

    def test_model_dump_json(self, minimal_diff_data: dict) -> None:
        """Test serialization to JSON string."""
        diff = ModelMemoryDiff(**minimal_diff_data)
        json_str = diff.model_dump_json()

        assert isinstance(json_str, str)
        assert "base_snapshot_id" in json_str
        assert "target_snapshot_id" in json_str

    def test_round_trip_serialization(self, minimal_diff_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        minimal_diff_data["diff_id"] = uuid4()
        minimal_diff_data["cost_delta"] = 0.05
        minimal_diff_data["summary"] = "Test summary"

        original = ModelMemoryDiff(**minimal_diff_data)
        data = original.model_dump()
        restored = ModelMemoryDiff(**data)

        assert original.diff_id == restored.diff_id
        assert original.base_snapshot_id == restored.base_snapshot_id
        assert original.target_snapshot_id == restored.target_snapshot_id
        assert original.cost_delta == restored.cost_delta
        assert original.summary == restored.summary

    def test_json_round_trip_serialization(self, full_diff_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelMemoryDiff(**full_diff_data)

        json_str = original.model_dump_json()
        restored = ModelMemoryDiff.model_validate_json(json_str)

        assert original.diff_id == restored.diff_id
        assert original.base_snapshot_id == restored.base_snapshot_id
        assert original.target_snapshot_id == restored.target_snapshot_id
        assert original.cost_delta == restored.cost_delta
        assert len(original.decisions_added) == len(restored.decisions_added)
        assert len(original.decisions_removed) == len(restored.decisions_removed)
        assert len(original.failures_added) == len(restored.failures_added)

    def test_model_validate_from_dict(self, minimal_diff_data: dict) -> None:
        """Test model validation from dictionary."""
        diff = ModelMemoryDiff.model_validate(minimal_diff_data)

        assert diff.base_snapshot_id == minimal_diff_data["base_snapshot_id"]
        assert diff.target_snapshot_id == minimal_diff_data["target_snapshot_id"]


# ============================================================================
# Test: String Representations
# ============================================================================


class TestModelMemoryDiffStringRepresentations:
    """Tests for __str__ and __repr__ methods."""

    def test_str_no_changes(self, minimal_diff_data: dict) -> None:
        """Test __str__ when no changes exist."""
        diff = ModelMemoryDiff(**minimal_diff_data)
        str_repr = str(diff)

        assert "no changes" in str_repr

    def test_str_with_decisions_added(
        self, minimal_diff_data: dict, sample_decision_record: ModelDecisionRecord
    ) -> None:
        """Test __str__ shows added decisions."""
        minimal_diff_data["decisions_added"] = (
            sample_decision_record,
            sample_decision_record,
        )
        diff = ModelMemoryDiff(**minimal_diff_data)
        str_repr = str(diff)

        assert "+2 decisions" in str_repr

    def test_str_with_decisions_removed(self, minimal_diff_data: dict) -> None:
        """Test __str__ shows removed decisions."""
        minimal_diff_data["decisions_removed"] = (uuid4(), uuid4(), uuid4())
        diff = ModelMemoryDiff(**minimal_diff_data)
        str_repr = str(diff)

        assert "-3 decisions" in str_repr

    def test_str_with_failures_added(
        self, minimal_diff_data: dict, sample_failure_record: ModelFailureRecord
    ) -> None:
        """Test __str__ shows added failures."""
        minimal_diff_data["failures_added"] = (sample_failure_record,)
        diff = ModelMemoryDiff(**minimal_diff_data)
        str_repr = str(diff)

        assert "+1 failures" in str_repr

    def test_str_with_positive_cost_delta(self, minimal_diff_data: dict) -> None:
        """Test __str__ shows positive cost delta with + sign."""
        minimal_diff_data["cost_delta"] = 0.0123
        diff = ModelMemoryDiff(**minimal_diff_data)
        str_repr = str(diff)

        assert "+$0.0123" in str_repr

    def test_str_with_negative_cost_delta(self, minimal_diff_data: dict) -> None:
        """Test __str__ shows negative cost delta."""
        minimal_diff_data["cost_delta"] = -0.0456
        diff = ModelMemoryDiff(**minimal_diff_data)
        str_repr = str(diff)

        assert "-$0.0456" in str_repr

    def test_repr_contains_class_name(self, minimal_diff_data: dict) -> None:
        """Test __repr__ contains class name."""
        diff = ModelMemoryDiff(**minimal_diff_data)
        repr_str = repr(diff)

        assert "ModelMemoryDiff" in repr_str

    def test_repr_contains_key_info(self, minimal_diff_data: dict) -> None:
        """Test __repr__ contains key information."""
        diff = ModelMemoryDiff(**minimal_diff_data)
        repr_str = repr(diff)

        assert "diff_id=" in repr_str
        assert "base_snapshot_id=" in repr_str
        assert "target_snapshot_id=" in repr_str
        assert "decision_change_count=" in repr_str
        assert "failure_change_count=" in repr_str
        assert "cost_delta=" in repr_str


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelMemoryDiffEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_tuples_accepted(self, minimal_diff_data: dict) -> None:
        """Test that empty tuples are accepted for collections."""
        minimal_diff_data["decisions_added"] = ()
        minimal_diff_data["decisions_removed"] = ()
        minimal_diff_data["failures_added"] = ()

        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.decisions_added == ()
        assert diff.decisions_removed == ()
        assert diff.failures_added == ()

    def test_model_equality(self, minimal_diff_data: dict) -> None:
        """Test model equality comparison with same data."""
        diff_id = uuid4()
        computed_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_diff_data["diff_id"] = diff_id
        minimal_diff_data["computed_at"] = computed_at
        diff1 = ModelMemoryDiff(**minimal_diff_data)
        diff2 = ModelMemoryDiff(**minimal_diff_data)

        assert diff1 == diff2

    def test_model_inequality_different_diff_id(self, minimal_diff_data: dict) -> None:
        """Test model inequality when diff_ids differ."""
        diff1 = ModelMemoryDiff(**minimal_diff_data)
        # Need different snapshot IDs for second diff
        minimal_diff_data["base_snapshot_id"] = uuid4()
        minimal_diff_data["target_snapshot_id"] = uuid4()
        diff2 = ModelMemoryDiff(**minimal_diff_data)

        # Different auto-generated diff_ids
        assert diff1 != diff2

    def test_hash_consistency_for_same_data(self, minimal_diff_data: dict) -> None:
        """Test that frozen model is hashable and consistent."""
        diff_id = uuid4()
        computed_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_diff_data["diff_id"] = diff_id
        minimal_diff_data["computed_at"] = computed_at

        diff1 = ModelMemoryDiff(**minimal_diff_data)
        diff2 = ModelMemoryDiff(**minimal_diff_data)

        # Frozen models should be hashable
        assert hash(diff1) == hash(diff2)

    def test_can_use_as_dict_key(self, minimal_diff_data: dict) -> None:
        """Test that frozen model can be used as dictionary key."""
        diff_id = uuid4()
        computed_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_diff_data["diff_id"] = diff_id
        minimal_diff_data["computed_at"] = computed_at

        diff = ModelMemoryDiff(**minimal_diff_data)

        # Should be usable as dict key
        test_dict = {diff: "value"}
        assert test_dict[diff] == "value"

    def test_can_add_to_set(self, minimal_diff_data: dict) -> None:
        """Test that frozen model can be added to set."""
        diff_id = uuid4()
        computed_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_diff_data["diff_id"] = diff_id
        minimal_diff_data["computed_at"] = computed_at

        diff1 = ModelMemoryDiff(**minimal_diff_data)
        diff2 = ModelMemoryDiff(**minimal_diff_data)

        # Should be usable in sets
        test_set = {diff1, diff2}
        assert len(test_set) == 1  # Same data, same hash

    def test_very_small_cost_delta(self, minimal_diff_data: dict) -> None:
        """Test handling of very small cost delta values."""
        minimal_diff_data["cost_delta"] = 0.000000001  # 1e-9
        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.cost_delta == 0.000000001

    def test_summary_with_special_characters(self, minimal_diff_data: dict) -> None:
        """Test summary with special characters."""
        special_summaries = [
            "Added 1 decision: 'model_selection'",
            "Cost changed by +$0.05 (from $1.00 to $1.05)",
            "Multiple changes: +2 decisions, -1 decision, +1 failure",
        ]
        for summary in special_summaries:
            minimal_diff_data["summary"] = summary
            diff = ModelMemoryDiff(**minimal_diff_data)
            assert diff.summary == summary

    def test_many_changes(
        self,
        minimal_diff_data: dict,
        sample_decision_record: ModelDecisionRecord,
        sample_failure_record: ModelFailureRecord,
    ) -> None:
        """Test diff with many changes."""
        # Add many decisions
        minimal_diff_data["decisions_added"] = tuple(
            [sample_decision_record for _ in range(10)]
        )
        # Remove many decisions
        minimal_diff_data["decisions_removed"] = tuple([uuid4() for _ in range(5)])
        # Add many failures
        minimal_diff_data["failures_added"] = tuple(
            [sample_failure_record for _ in range(3)]
        )
        minimal_diff_data["cost_delta"] = 1.50

        diff = ModelMemoryDiff(**minimal_diff_data)

        assert diff.decision_change_count == 15  # 10 added + 5 removed
        assert diff.failure_change_count == 3
        assert diff.has_changes is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
