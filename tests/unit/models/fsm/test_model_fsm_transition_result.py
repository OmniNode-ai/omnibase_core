"""
Unit tests for ModelFSMTransitionResult.

Tests all aspects of the FSM transition result model including:
- Model instantiation and validation
- Default values (timestamp auto-generated, optional fields)
- Type validation for each field
- Protocol implementations (serialize, validate_instance)
- Serialization/deserialization
- Edge cases (whitespace-only strings, empty intents/metadata)

Deep Immutability:
    ModelFSMTransitionResult uses tuples instead of lists and tuple-of-tuples instead
    of dicts for deep immutability. Validators convert lists/dicts to frozen types
    during construction.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.fsm.model_fsm_transition_result import (
    ModelFSMTransitionResult,
)
from omnibase_core.models.reducer.model_intent import ModelIntent


@pytest.mark.unit
class TestModelFSMTransitionResultInstantiation:
    """Test cases for ModelFSMTransitionResult instantiation."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal required data."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
        )

        assert result.success is True
        assert result.new_state == "active"
        assert result.old_state == "idle"
        assert result.transition_name is None
        assert result.intents == ()  # tuple for deep immutability
        assert result.metadata == ()  # tuple of tuples for deep immutability
        assert result.error is None
        assert result.timestamp is not None  # Auto-generated

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields populated."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="processing",
            old_state="waiting",
            transition_name="start_processing",
            intents=[],
            metadata={"key": "value", "num": 42},
            error=None,
        )

        assert result.success is True
        assert result.new_state == "processing"
        assert result.old_state == "waiting"
        assert result.transition_name == "start_processing"
        assert result.intents == ()
        # Metadata dict converted to sorted tuple of tuples
        assert dict(result.metadata) == {"key": "value", "num": 42}
        assert result.error is None
        assert result.timestamp is not None

    def test_model_instantiation_failed_transition(self):
        """Test model instantiation for a failed transition."""
        result = ModelFSMTransitionResult(
            success=False,
            new_state="idle",
            old_state="idle",
            transition_name=None,
            error="No valid transition found for trigger 'invalid_event'",
        )

        assert result.success is False
        assert result.new_state == "idle"
        assert result.old_state == "idle"
        assert result.transition_name is None
        assert result.error == "No valid transition found for trigger 'invalid_event'"

    def test_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated with ISO format."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
        )

        # Timestamp should be ISO format with timezone
        assert result.timestamp is not None
        assert isinstance(result.timestamp, str)
        # ISO format includes date separator
        assert "T" in result.timestamp or "-" in result.timestamp


@pytest.mark.unit
class TestModelFSMTransitionResultValidation:
    """Test validation rules for ModelFSMTransitionResult."""

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing all required fields
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionResult()
        error_str = str(exc_info.value)
        assert "success" in error_str
        assert "new_state" in error_str
        assert "old_state" in error_str

    def test_missing_success(self):
        """Test that missing success raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionResult(
                new_state="active",
                old_state="idle",
            )
        assert "success" in str(exc_info.value)

    def test_missing_new_state(self):
        """Test that missing new_state raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionResult(
                success=True,
                old_state="idle",
            )
        assert "new_state" in str(exc_info.value)

    def test_missing_old_state(self):
        """Test that missing old_state raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionResult(
                success=True,
                new_state="active",
            )
        assert "old_state" in str(exc_info.value)

    def test_success_type_validation(self):
        """Test that success must be a boolean."""
        # Valid boolean
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
        )
        assert result.success is True

        # Invalid type
        with pytest.raises(ValidationError):
            ModelFSMTransitionResult(
                success="not_a_bool",
                new_state="active",
                old_state="idle",
            )

    def test_new_state_type_validation(self):
        """Test that new_state must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionResult(
                success=True,
                new_state=123,
                old_state="idle",
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionResult(
                success=True,
                new_state=None,
                old_state="idle",
            )

    def test_old_state_type_validation(self):
        """Test that old_state must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionResult(
                success=True,
                new_state="active",
                old_state=456,
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionResult(
                success=True,
                new_state="active",
                old_state=None,
            )

    def test_empty_string_new_state_rejected_by_pydantic(self):
        """Test that empty new_state is rejected by Pydantic (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionResult(
                success=True,
                new_state="",
                old_state="idle",
            )
        assert "new_state" in str(exc_info.value)

    def test_empty_string_old_state_rejected_by_pydantic(self):
        """Test that empty old_state is rejected by Pydantic (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionResult(
                success=True,
                new_state="active",
                old_state="",
            )
        assert "old_state" in str(exc_info.value)


@pytest.mark.unit
class TestModelFSMTransitionResultValidateInstanceFalse:
    """Test validate_instance returning False for invalid states."""

    def test_validate_instance_whitespace_new_state_returns_false(self):
        """Test validate_instance returns False for whitespace-only new_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="   ",
            old_state="idle",
        )
        assert result.validate_instance() is False

    def test_validate_instance_tab_only_new_state_returns_false(self):
        """Test validate_instance returns False for tab-only new_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="\t\t",
            old_state="idle",
        )
        assert result.validate_instance() is False

    def test_validate_instance_newline_only_new_state_returns_false(self):
        """Test validate_instance returns False for newline-only new_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="\n\n",
            old_state="idle",
        )
        assert result.validate_instance() is False

    def test_validate_instance_whitespace_old_state_returns_false(self):
        """Test validate_instance returns False for whitespace-only old_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="   ",
        )
        assert result.validate_instance() is False

    def test_validate_instance_tab_only_old_state_returns_false(self):
        """Test validate_instance returns False for tab-only old_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="\t\t",
        )
        assert result.validate_instance() is False

    def test_validate_instance_newline_only_old_state_returns_false(self):
        """Test validate_instance returns False for newline-only old_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="\n\n",
        )
        assert result.validate_instance() is False

    def test_validate_instance_both_whitespace_returns_false(self):
        """Test validate_instance returns False when both states are whitespace."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="   ",
            old_state="   ",
        )
        assert result.validate_instance() is False

    def test_validate_instance_mixed_whitespace_new_state_returns_false(self):
        """Test validate_instance returns False with mixed whitespace in new_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state=" \t\n ",
            old_state="idle",
        )
        assert result.validate_instance() is False

    def test_validate_instance_mixed_whitespace_old_state_returns_false(self):
        """Test validate_instance returns False with mixed whitespace in old_state."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state=" \t\n ",
        )
        assert result.validate_instance() is False

    def test_validate_instance_valid_returns_true(self):
        """Test validate_instance returns True for valid states."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
        )
        assert result.validate_instance() is True

    def test_validate_instance_valid_with_all_fields_returns_true(self):
        """Test validate_instance returns True with all fields populated."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="completed",
            old_state="processing",
            transition_name="finish",
            intents=[],
            metadata={"reason": "success"},
            error=None,
        )
        assert result.validate_instance() is True

    def test_validate_instance_failed_transition_valid(self):
        """Test validate_instance returns True for valid failed transition."""
        result = ModelFSMTransitionResult(
            success=False,
            new_state="idle",
            old_state="idle",
            error="Transition failed",
        )
        assert result.validate_instance() is True


@pytest.mark.unit
class TestModelFSMTransitionResultProtocols:
    """Test protocol implementations for ModelFSMTransitionResult."""

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            transition_name="activate",
            metadata={"key": "value"},
        )

        serialized = result.serialize()

        assert isinstance(serialized, dict)
        assert serialized["success"] is True
        assert serialized["new_state"] == "active"
        assert serialized["old_state"] == "idle"
        assert serialized["transition_name"] == "activate"
        assert "metadata" in serialized
        assert "timestamp" in serialized

    def test_serialize_protocol_minimal(self):
        """Test serialize protocol with minimal result."""
        result = ModelFSMTransitionResult(
            success=False,
            new_state="idle",
            old_state="idle",
        )

        serialized = result.serialize()

        assert isinstance(serialized, dict)
        assert serialized["success"] is False
        assert serialized["new_state"] == "idle"
        assert serialized["old_state"] == "idle"
        assert "transition_name" in serialized
        assert serialized["transition_name"] is None

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
        )

        is_valid = result.validate_instance()
        assert is_valid is True

    def test_validate_instance_protocol_complex(self):
        """Test validate_instance with complex result."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="processing",
            old_state="waiting",
            transition_name="start",
            intents=[],
            metadata={"key1": "value1", "key2": "value2"},
            error=None,
        )

        is_valid = result.validate_instance()
        assert is_valid is True


@pytest.mark.unit
class TestModelFSMTransitionResultSerialization:
    """Test serialization and deserialization for ModelFSMTransitionResult."""

    def test_model_dump(self):
        """Test model_dump method."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            transition_name="start",
            error=None,
        )

        data = result.model_dump()

        assert isinstance(data, dict)
        assert data["success"] is True
        assert data["new_state"] == "active"
        assert data["old_state"] == "idle"
        assert data["transition_name"] == "start"
        assert data["error"] is None

    def test_model_validate(self):
        """Test model_validate method."""
        data = {
            "success": True,
            "new_state": "validated_state",
            "old_state": "previous_state",
            "transition_name": "validate",
            "intents": [],
            "metadata": {"validated": "true"},
            "error": None,
            "timestamp": "2024-01-01T00:00:00+00:00",
        }

        result = ModelFSMTransitionResult.model_validate(data)

        assert result.success is True
        assert result.new_state == "validated_state"
        assert result.old_state == "previous_state"
        assert result.transition_name == "validate"
        assert result.error is None

    def test_model_dump_json(self):
        """Test JSON serialization."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="json_test",
            old_state="initial",
        )

        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert "initial" in json_str
        assert "success" in json_str

    def test_model_validate_json(self):
        """Test JSON deserialization."""
        json_str = (
            '{"success": true, "new_state": "from_json", '
            '"old_state": "initial", "timestamp": "2024-01-01T00:00:00+00:00"}'
        )

        result = ModelFSMTransitionResult.model_validate_json(json_str)

        assert result.success is True
        assert result.new_state == "from_json"
        assert result.old_state == "initial"

    def test_roundtrip_serialization(self):
        """Test full roundtrip serialization/deserialization."""
        original = ModelFSMTransitionResult(
            success=True,
            new_state="roundtrip_new",
            old_state="roundtrip_old",
            transition_name="roundtrip_transition",
            intents=[],
            metadata={"key": "value"},
            error=None,
        )

        # Serialize to dict and back
        data = original.model_dump()
        restored = ModelFSMTransitionResult.model_validate(data)

        assert restored.success == original.success
        assert restored.new_state == original.new_state
        assert restored.old_state == original.old_state
        assert restored.transition_name == original.transition_name
        assert restored.error == original.error


@pytest.mark.unit
class TestModelFSMTransitionResultEdgeCases:
    """Test edge cases for ModelFSMTransitionResult."""

    def test_state_names_with_special_characters(self):
        """Test state names with special characters."""
        special_names = [
            "state-with-dashes",
            "state_with_underscores",
            "state.with.dots",
            "state:with:colons",
            "state with spaces",
        ]

        for name in special_names:
            result = ModelFSMTransitionResult(
                success=True,
                new_state=name,
                old_state="idle",
            )
            assert result.new_state == name

    def test_very_long_state_names(self):
        """Test result with very long state names."""
        long_name = "state_" + "x" * 10000
        result = ModelFSMTransitionResult(
            success=True,
            new_state=long_name,
            old_state=long_name,
        )
        assert len(result.new_state) > 10000
        assert len(result.old_state) > 10000

    def test_same_new_and_old_state(self):
        """Test result where new_state equals old_state (self-transition)."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="processing",
            old_state="processing",
            transition_name="retry",
        )
        assert result.new_state == result.old_state
        assert result.new_state == "processing"

    def test_empty_metadata(self):
        """Test result with empty metadata (converted to empty tuple)."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            metadata={},
        )
        assert result.metadata == ()

    def test_empty_intents(self):
        """Test result with empty intents (converted to empty tuple)."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            intents=[],
        )
        assert result.intents == ()

    def test_very_long_error_message(self):
        """Test result with very long error message."""
        long_error = "Error: " + "x" * 50000
        result = ModelFSMTransitionResult(
            success=False,
            new_state="idle",
            old_state="idle",
            error=long_error,
        )
        assert len(result.error) > 50000

    def test_error_message_with_special_characters(self):
        """Test error messages with special characters."""
        special_errors = [
            "Error: State 'invalid' not found",
            'Transition failed for "process"',
            "Failed!\nMultiple\nLines",
            "Error with tabs:\t\ttabbed",
        ]

        for error in special_errors:
            result = ModelFSMTransitionResult(
                success=False,
                new_state="idle",
                old_state="idle",
                error=error,
            )
            assert result.error == error

    def test_model_equality(self):
        """Test model equality comparison."""
        result1 = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            transition_name="start",
            timestamp="2024-01-01T00:00:00+00:00",
        )
        result2 = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            transition_name="start",
            timestamp="2024-01-01T00:00:00+00:00",
        )
        result3 = ModelFSMTransitionResult(
            success=False,
            new_state="active",
            old_state="idle",
            timestamp="2024-01-01T00:00:00+00:00",
        )

        assert result1 == result2
        assert result1 != result3

    def test_frozen_config(self):
        """Test that frozen config prevents mutations."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
        )

        # Model is frozen - assignment raises ValidationError
        with pytest.raises(ValidationError):
            result.new_state = "updated"

        with pytest.raises(ValidationError):
            result.success = False

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per config."""
        data = {
            "success": True,
            "new_state": "active",
            "old_state": "idle",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        result = ModelFSMTransitionResult.model_validate(data)
        assert result.success is True
        assert not hasattr(result, "extra_field")
        assert not hasattr(result, "another_extra")

    def test_metadata_with_various_types(self):
        """Test metadata with various SerializableValue types."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            metadata={
                "string_key": "string_value",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
                "none_key": None,
            },
        )

        # Metadata is converted to sorted tuple of tuples
        metadata_dict = dict(result.metadata)
        assert metadata_dict["string_key"] == "string_value"
        assert metadata_dict["int_key"] == 42
        assert metadata_dict["float_key"] == 3.14
        assert metadata_dict["bool_key"] is True
        assert metadata_dict["none_key"] is None

    def test_metadata_sorted_order(self):
        """Test that metadata is sorted by key for deterministic hashing."""
        result = ModelFSMTransitionResult(
            success=True,
            new_state="active",
            old_state="idle",
            metadata={"z_key": "z", "a_key": "a", "m_key": "m"},
        )

        # Keys should be sorted
        keys = [k for k, _ in result.metadata]
        assert keys == sorted(keys)


@pytest.mark.unit
class TestModelFSMTransitionResultImport:
    """Test that the model can be imported from the fsm module."""

    def test_import_from_fsm_module(self):
        """Test importing from the fsm package."""
        from omnibase_core.models.fsm import (
            ModelFSMTransitionResult as ImportedModel,
        )

        result = ImportedModel(
            success=True,
            new_state="import_test",
            old_state="initial",
        )

        assert result.new_state == "import_test"

    def test_import_from_direct_module(self):
        """Test importing directly from the model file."""
        from omnibase_core.models.fsm.model_fsm_transition_result import (
            ModelFSMTransitionResult as DirectModel,
        )

        result = DirectModel(
            success=True,
            new_state="direct_import",
            old_state="initial",
        )

        assert result.new_state == "direct_import"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
