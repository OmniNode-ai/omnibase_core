"""
Unit tests for ModelFSMStateSnapshot.

Tests all aspects of the FSM state snapshot model including:
- Model instantiation and validation
- Frozen behavior (immutability)
- History is never None, always list
- Extra fields are rejected (extra="forbid")
- Factory method create_initial
- Serialization/deserialization
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.fsm import ModelFSMStateSnapshot

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestModelFSMStateSnapshotInstantiation:
    """Test cases for ModelFSMStateSnapshot instantiation."""

    def test_model_instantiation_minimal(self) -> None:
        """Test that model can be instantiated with minimal data."""
        snapshot = ModelFSMStateSnapshot(current_state="idle")

        assert snapshot.current_state == "idle"
        assert snapshot.context == {}
        assert snapshot.history == []

    def test_model_instantiation_full(self) -> None:
        """Test model instantiation with all fields populated."""
        snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            context={"request_id": "abc123", "retry_count": 2},
            history=["initial", "validating"],
        )

        assert snapshot.current_state == "processing"
        assert snapshot.context == {"request_id": "abc123", "retry_count": 2}
        assert snapshot.history == ["initial", "validating"]

    def test_model_with_empty_context(self) -> None:
        """Test model with empty context dict."""
        snapshot = ModelFSMStateSnapshot(current_state="test", context={})

        assert snapshot.context == {}
        assert isinstance(snapshot.context, dict)

    def test_model_with_empty_history(self) -> None:
        """Test model with empty history list."""
        snapshot = ModelFSMStateSnapshot(current_state="test", history=[])

        assert snapshot.history == []
        assert isinstance(snapshot.history, list)


@pytest.mark.unit
class TestModelFSMStateSnapshotHistoryNeverNone:
    """Test that history is NEVER None, always a list."""

    def test_history_defaults_to_empty_list(self) -> None:
        """Test that history defaults to empty list when not provided."""
        snapshot = ModelFSMStateSnapshot(current_state="idle")

        assert snapshot.history is not None
        assert snapshot.history == []
        assert isinstance(snapshot.history, list)

    def test_history_with_empty_list(self) -> None:
        """Test that history accepts empty list."""
        snapshot = ModelFSMStateSnapshot(current_state="idle", history=[])

        assert snapshot.history is not None
        assert snapshot.history == []

    def test_history_with_values(self) -> None:
        """Test that history accepts list with values."""
        snapshot = ModelFSMStateSnapshot(
            current_state="idle", history=["state1", "state2", "state3"]
        )

        assert snapshot.history is not None
        assert snapshot.history == ["state1", "state2", "state3"]

    def test_history_cannot_be_none(self) -> None:
        """Test that history cannot be explicitly set to None."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMStateSnapshot(current_state="idle", history=None)

        assert "history" in str(exc_info.value)


@pytest.mark.unit
class TestModelFSMStateSnapshotFrozenBehavior:
    """Test frozen behavior (immutability) of ModelFSMStateSnapshot."""

    def test_frozen_prevents_current_state_modification(self) -> None:
        """Test that frozen model prevents current_state modification."""
        snapshot = ModelFSMStateSnapshot(current_state="idle")

        with pytest.raises(ValidationError):
            snapshot.current_state = "modified"

    def test_frozen_prevents_context_reassignment(self) -> None:
        """Test that frozen model prevents context reassignment."""
        snapshot = ModelFSMStateSnapshot(current_state="idle", context={"key": "value"})

        with pytest.raises(ValidationError):
            snapshot.context = {"new_key": "new_value"}

    def test_frozen_prevents_history_reassignment(self) -> None:
        """Test that frozen model prevents history reassignment."""
        snapshot = ModelFSMStateSnapshot(current_state="idle", history=["state1"])

        with pytest.raises(ValidationError):
            snapshot.history = ["state1", "state2"]

    def test_frozen_prevents_new_attribute_assignment(self) -> None:
        """Test that frozen model prevents new attribute assignment."""
        snapshot = ModelFSMStateSnapshot(current_state="idle")

        with pytest.raises(ValidationError):
            snapshot.new_attr = "value"


@pytest.mark.unit
class TestModelFSMStateSnapshotExtraFieldsRejected:
    """Test that extra fields are rejected (extra='forbid')."""

    def test_extra_fields_rejected_at_construction(self) -> None:
        """Test that extra fields are rejected during construction."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMStateSnapshot(
                current_state="idle",
                extra_field="should_be_rejected",
            )

        error_str = str(exc_info.value)
        assert "extra_field" in error_str.lower() or "extra" in error_str.lower()

    def test_multiple_extra_fields_rejected(self) -> None:
        """Test that multiple extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelFSMStateSnapshot(
                current_state="idle",
                extra1="value1",
                extra2="value2",
            )

    def test_extra_fields_rejected_via_model_validate(self) -> None:
        """Test that extra fields are rejected via model_validate."""
        data = {
            "current_state": "idle",
            "context": {},
            "history": [],
            "extra_field": "should_be_rejected",
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelFSMStateSnapshot.model_validate(data)

        error_str = str(exc_info.value)
        assert "extra_field" in error_str.lower() or "extra" in error_str.lower()


@pytest.mark.unit
class TestModelFSMStateSnapshotCreateInitial:
    """Test create_initial factory method."""

    def test_create_initial_basic(self) -> None:
        """Test create_initial with basic state name."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")

        assert snapshot.current_state == "idle"
        assert snapshot.context == {}
        assert snapshot.history == []

    def test_create_initial_with_different_states(self) -> None:
        """Test create_initial with various state names."""
        states = ["start", "pending", "processing", "completed", "error"]

        for state in states:
            snapshot = ModelFSMStateSnapshot.create_initial(state)
            assert snapshot.current_state == state
            assert snapshot.context == {}
            assert snapshot.history == []

    def test_create_initial_returns_correct_type(self) -> None:
        """Test that create_initial returns ModelFSMStateSnapshot instance."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")

        assert isinstance(snapshot, ModelFSMStateSnapshot)

    def test_create_initial_is_frozen(self) -> None:
        """Test that snapshot from create_initial is frozen."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")

        with pytest.raises(ValidationError):
            snapshot.current_state = "modified"

    def test_create_initial_history_is_list(self) -> None:
        """Test that create_initial produces list history, not None."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")

        assert snapshot.history is not None
        assert isinstance(snapshot.history, list)
        assert snapshot.history == []


@pytest.mark.unit
class TestModelFSMStateSnapshotSerialization:
    """Test serialization and deserialization for ModelFSMStateSnapshot."""

    def test_model_dump(self) -> None:
        """Test model_dump method."""
        snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            context={"key": "value"},
            history=["state1", "state2"],
        )

        data = snapshot.model_dump()

        assert isinstance(data, dict)
        assert data["current_state"] == "processing"
        assert data["context"] == {"key": "value"}
        assert data["history"] == ["state1", "state2"]

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal snapshot."""
        snapshot = ModelFSMStateSnapshot(current_state="idle")

        data = snapshot.model_dump()

        assert isinstance(data, dict)
        assert data["current_state"] == "idle"
        assert data["context"] == {}
        assert data["history"] == []

    def test_model_validate(self) -> None:
        """Test model_validate method."""
        data = {
            "current_state": "validated",
            "context": {"request_id": "xyz"},
            "history": ["initial", "pending"],
        }

        snapshot = ModelFSMStateSnapshot.model_validate(data)

        assert snapshot.current_state == "validated"
        assert snapshot.context == {"request_id": "xyz"}
        assert snapshot.history == ["initial", "pending"]

    def test_model_validate_minimal(self) -> None:
        """Test model_validate with minimal data."""
        data = {"current_state": "minimal"}

        snapshot = ModelFSMStateSnapshot.model_validate(data)

        assert snapshot.current_state == "minimal"
        assert snapshot.context == {}
        assert snapshot.history == []

    def test_model_dump_json(self) -> None:
        """Test JSON serialization."""
        snapshot = ModelFSMStateSnapshot(
            current_state="json_test",
            context={"key": "value"},
            history=["state1"],
        )

        json_str = snapshot.model_dump_json()

        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert "key" in json_str
        assert "state1" in json_str

    def test_model_validate_json(self) -> None:
        """Test JSON deserialization."""
        json_str = '{"current_state": "from_json", "context": {"id": "123"}, "history": ["a", "b"]}'

        snapshot = ModelFSMStateSnapshot.model_validate_json(json_str)

        assert snapshot.current_state == "from_json"
        assert snapshot.context == {"id": "123"}
        assert snapshot.history == ["a", "b"]

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization/deserialization."""
        original = ModelFSMStateSnapshot(
            current_state="roundtrip",
            context={"key1": "val1", "key2": 42},
            history=["s1", "s2", "s3"],
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelFSMStateSnapshot.model_validate(data)

        assert restored.current_state == original.current_state
        assert restored.context == original.context
        assert restored.history == original.history
        assert restored == original


@pytest.mark.unit
class TestModelFSMStateSnapshotValidation:
    """Test validation rules for ModelFSMStateSnapshot."""

    def test_required_field_current_state(self) -> None:
        """Test that current_state is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMStateSnapshot()

        assert "current_state" in str(exc_info.value)

    def test_current_state_type_validation(self) -> None:
        """Test that current_state must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMStateSnapshot(current_state=123)

        with pytest.raises(ValidationError):
            ModelFSMStateSnapshot(current_state=None)

    def test_context_type_validation(self) -> None:
        """Test that context must be a dict."""
        with pytest.raises(ValidationError):
            ModelFSMStateSnapshot(current_state="idle", context="not_a_dict")

        with pytest.raises(ValidationError):
            ModelFSMStateSnapshot(current_state="idle", context=["list"])

    def test_history_type_validation(self) -> None:
        """Test that history must be a list of strings."""
        with pytest.raises(ValidationError):
            ModelFSMStateSnapshot(current_state="idle", history="not_a_list")

        with pytest.raises(ValidationError):
            ModelFSMStateSnapshot(current_state="idle", history={"dict": "value"})


@pytest.mark.unit
class TestModelFSMStateSnapshotEdgeCases:
    """Test edge cases for ModelFSMStateSnapshot."""

    def test_empty_string_state(self) -> None:
        """Test snapshot with empty string state."""
        snapshot = ModelFSMStateSnapshot(current_state="")
        assert snapshot.current_state == ""

    def test_very_long_state_name(self) -> None:
        """Test snapshot with very long state name."""
        long_name = "state_" + "x" * 10000
        snapshot = ModelFSMStateSnapshot(current_state=long_name)
        assert len(snapshot.current_state) > 10000

    def test_special_characters_in_state_name(self) -> None:
        """Test state names with special characters."""
        special_names = [
            "state-with-dashes",
            "state_with_underscores",
            "state.with.dots",
            "state:with:colons",
            "state with spaces",
        ]

        for name in special_names:
            snapshot = ModelFSMStateSnapshot(current_state=name)
            assert snapshot.current_state == name

    def test_complex_context(self) -> None:
        """Test snapshot with complex nested context."""
        complex_context = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "nested": {"inner": {"deep": "value"}},
        }

        snapshot = ModelFSMStateSnapshot(current_state="test", context=complex_context)

        assert snapshot.context == complex_context

    def test_long_history(self) -> None:
        """Test snapshot with long history list."""
        long_history = [f"state_{i}" for i in range(1000)]

        snapshot = ModelFSMStateSnapshot(current_state="final", history=long_history)

        assert len(snapshot.history) == 1000
        assert snapshot.history[0] == "state_0"
        assert snapshot.history[-1] == "state_999"

    def test_model_equality(self) -> None:
        """Test model equality comparison."""
        snapshot1 = ModelFSMStateSnapshot(
            current_state="same",
            context={"key": "value"},
            history=["s1", "s2"],
        )
        snapshot2 = ModelFSMStateSnapshot(
            current_state="same",
            context={"key": "value"},
            history=["s1", "s2"],
        )
        snapshot3 = ModelFSMStateSnapshot(
            current_state="different",
            context={"key": "value"},
            history=["s1", "s2"],
        )

        assert snapshot1 == snapshot2
        assert snapshot1 != snapshot3

    def test_model_hash_not_supported(self) -> None:
        """Test that frozen model with mutable fields is not hashable.

        Note: Pydantic frozen models with mutable container fields (dict, list)
        are NOT hashable because dict and list are themselves unhashable.
        This is expected Python behavior - frozen only prevents field reassignment,
        not hashing of mutable container contents.
        """
        snapshot = ModelFSMStateSnapshot(current_state="hashable")

        # Should raise TypeError because context (dict) and history (list) are unhashable
        with pytest.raises(TypeError, match="unhashable"):
            hash(snapshot)

    def test_model_repr(self) -> None:
        """Test model string representation."""
        snapshot = ModelFSMStateSnapshot(
            current_state="test", context={"k": "v"}, history=["h1"]
        )

        repr_str = repr(snapshot)
        assert "ModelFSMStateSnapshot" in repr_str
        assert "test" in repr_str


@pytest.mark.unit
class TestModelFSMStateSnapshotTransitionTo:
    """Test transition_to helper method."""

    def test_transition_to_basic(self) -> None:
        """Test basic state transition."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")
        new_snapshot = snapshot.transition_to("processing")

        assert new_snapshot.current_state == "processing"
        assert new_snapshot.history == ["idle"]
        assert new_snapshot.context == {}

    def test_transition_to_preserves_original(self) -> None:
        """Test that transition_to does not mutate original snapshot."""
        original = ModelFSMStateSnapshot.create_initial("idle")
        new_snapshot = original.transition_to("processing")

        # Original should be unchanged
        assert original.current_state == "idle"
        assert original.history == []
        assert original.context == {}

        # New snapshot should have updated values
        assert new_snapshot.current_state == "processing"
        assert new_snapshot.history == ["idle"]

    def test_transition_to_multiple_transitions(self) -> None:
        """Test chaining multiple transitions."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")
        snapshot = snapshot.transition_to("validating")
        snapshot = snapshot.transition_to("processing")
        snapshot = snapshot.transition_to("completed")

        assert snapshot.current_state == "completed"
        assert snapshot.history == ["idle", "validating", "processing"]

    def test_transition_to_with_new_context(self) -> None:
        """Test transition with new context data."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")
        new_snapshot = snapshot.transition_to(
            "processing", new_context={"request_id": "abc123"}
        )

        assert new_snapshot.current_state == "processing"
        assert new_snapshot.context == {"request_id": "abc123"}

    def test_transition_to_merges_context(self) -> None:
        """Test that new_context is merged with existing context."""
        snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context={"user_id": "user1", "retry_count": 0},
        )
        new_snapshot = snapshot.transition_to(
            "processing", new_context={"retry_count": 1, "started_at": "2024-01-01"}
        )

        assert new_snapshot.context == {
            "user_id": "user1",  # preserved from original
            "retry_count": 1,  # overridden by new_context
            "started_at": "2024-01-01",  # added from new_context
        }

    def test_transition_to_preserves_context_when_none(self) -> None:
        """Test that context is preserved when new_context is None."""
        snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context={"key": "value"},
        )
        new_snapshot = snapshot.transition_to("processing")

        assert new_snapshot.context == {"key": "value"}

    def test_transition_to_with_empty_new_context(self) -> None:
        """Test transition with empty new_context dict."""
        snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context={"existing": "value"},
        )
        new_snapshot = snapshot.transition_to("processing", new_context={})

        # Empty dict merges with existing, preserving existing values
        assert new_snapshot.context == {"existing": "value"}

    def test_transition_to_appends_to_existing_history(self) -> None:
        """Test that transition_to appends to existing history."""
        snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            history=["idle", "validating"],
        )
        new_snapshot = snapshot.transition_to("completed")

        assert new_snapshot.history == ["idle", "validating", "processing"]

    def test_transition_to_returns_correct_type(self) -> None:
        """Test that transition_to returns ModelFSMStateSnapshot instance."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")
        new_snapshot = snapshot.transition_to("processing")

        assert isinstance(new_snapshot, ModelFSMStateSnapshot)

    def test_transition_to_result_is_frozen(self) -> None:
        """Test that snapshot from transition_to is frozen."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")
        new_snapshot = snapshot.transition_to("processing")

        with pytest.raises(ValidationError):
            new_snapshot.current_state = "modified"

    def test_transition_to_same_state(self) -> None:
        """Test transition to the same state (self-loop)."""
        snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            context={"attempt": 1},
        )
        new_snapshot = snapshot.transition_to("processing", new_context={"attempt": 2})

        assert new_snapshot.current_state == "processing"
        assert new_snapshot.history == ["processing"]
        assert new_snapshot.context == {"attempt": 2}

    def test_transition_to_with_complex_context(self) -> None:
        """Test transition with complex nested context."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")
        complex_context = {
            "nested": {"inner": {"deep": "value"}},
            "list": [1, 2, 3],
            "mixed": {"count": 42, "items": ["a", "b"]},
        }
        new_snapshot = snapshot.transition_to("processing", new_context=complex_context)

        assert new_snapshot.context == complex_context
