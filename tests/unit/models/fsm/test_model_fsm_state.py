"""
Unit tests for ModelFsmState.

Tests all aspects of the FSM state model including:
- Model instantiation and validation
- State flags (initial, final)
- Entry and exit actions
- State properties
- Protocol implementations (execute, serialize, validate)
- Edge cases and error conditions
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.fsm.model_fsm_state import ModelFsmState


class TestModelFsmStateInstantiation:
    """Test cases for ModelFsmState instantiation."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal data."""
        state = ModelFsmState(name="idle")

        assert state.name == "idle"
        assert state.description == ""
        assert state.is_initial is False
        assert state.is_final is False
        assert state.entry_actions == []
        assert state.exit_actions == []
        assert state.properties == {}

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields populated."""
        state = ModelFsmState(
            name="processing",
            description="Processing state for data validation",
            is_initial=False,
            is_final=False,
            entry_actions=["validate_input", "log_entry"],
            exit_actions=["cleanup", "log_exit"],
            properties={"timeout": "30s", "retry_count": "3"},
        )

        assert state.name == "processing"
        assert state.description == "Processing state for data validation"
        assert state.is_initial is False
        assert state.is_final is False
        assert state.entry_actions == ["validate_input", "log_entry"]
        assert state.exit_actions == ["cleanup", "log_exit"]
        assert state.properties == {"timeout": "30s", "retry_count": "3"}

    def test_initial_state_creation(self):
        """Test creation of an initial state."""
        state = ModelFsmState(name="start", is_initial=True)

        assert state.name == "start"
        assert state.is_initial is True
        assert state.is_final is False

    def test_final_state_creation(self):
        """Test creation of a final state."""
        state = ModelFsmState(name="completed", is_final=True)

        assert state.name == "completed"
        assert state.is_initial is False
        assert state.is_final is True

    def test_state_with_entry_actions(self):
        """Test state with entry actions."""
        state = ModelFsmState(
            name="active", entry_actions=["initialize", "start_timer", "log_entry"]
        )

        assert len(state.entry_actions) == 3
        assert "initialize" in state.entry_actions
        assert "start_timer" in state.entry_actions
        assert "log_entry" in state.entry_actions

    def test_state_with_exit_actions(self):
        """Test state with exit actions."""
        state = ModelFsmState(
            name="active", exit_actions=["cleanup", "stop_timer", "log_exit"]
        )

        assert len(state.exit_actions) == 3
        assert "cleanup" in state.exit_actions
        assert "stop_timer" in state.exit_actions
        assert "log_exit" in state.exit_actions

    def test_state_with_properties(self):
        """Test state with custom properties."""
        state = ModelFsmState(
            name="waiting",
            properties={
                "max_wait_time": "60s",
                "retry_enabled": "true",
                "priority": "high",
            },
        )

        assert len(state.properties) == 3
        assert state.properties["max_wait_time"] == "60s"
        assert state.properties["retry_enabled"] == "true"
        assert state.properties["priority"] == "high"


class TestModelFsmStateValidation:
    """Test validation rules for ModelFsmState."""

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing name field should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmState()
        assert "name" in str(exc_info.value)

    def test_name_field_type_validation(self):
        """Test that name field must be a string."""
        with pytest.raises(ValidationError):
            ModelFsmState(name=123)

        with pytest.raises(ValidationError):
            ModelFsmState(name=None)

        with pytest.raises(ValidationError):
            ModelFsmState(name=["state"])

    def test_boolean_fields_type_validation(self):
        """Test that boolean fields accept proper types."""
        # Valid boolean values
        state = ModelFsmState(name="test", is_initial=True, is_final=False)
        assert state.is_initial is True
        assert state.is_final is False

        # Test invalid boolean values that Pydantic cannot coerce
        with pytest.raises(ValidationError):
            ModelFsmState(name="test", is_initial=["not_a_bool"])

        with pytest.raises(ValidationError):
            ModelFsmState(name="test", is_final={"not": "bool"})

    def test_entry_actions_list_validation(self):
        """Test that entry_actions must be a list of strings."""
        # Valid list of strings
        state = ModelFsmState(name="test", entry_actions=["action1", "action2"])
        assert state.entry_actions == ["action1", "action2"]

        # Invalid type for entry_actions
        with pytest.raises(ValidationError):
            ModelFsmState(name="test", entry_actions="not_a_list")

        with pytest.raises(ValidationError):
            ModelFsmState(name="test", entry_actions=[1, 2, 3])

    def test_exit_actions_list_validation(self):
        """Test that exit_actions must be a list of strings."""
        # Valid list of strings
        state = ModelFsmState(name="test", exit_actions=["exit1", "exit2"])
        assert state.exit_actions == ["exit1", "exit2"]

        # Invalid type for exit_actions
        with pytest.raises(ValidationError):
            ModelFsmState(name="test", exit_actions={"action": "value"})

        with pytest.raises(ValidationError):
            ModelFsmState(name="test", exit_actions=[True, False])

    def test_properties_dict_validation(self):
        """Test that properties must be a dict with string values."""
        # Valid dict
        state = ModelFsmState(name="test", properties={"key": "value"})
        assert state.properties == {"key": "value"}

        # Invalid type for properties
        with pytest.raises(ValidationError):
            ModelFsmState(name="test", properties="not_a_dict")

        with pytest.raises(ValidationError):
            ModelFsmState(name="test", properties=["list", "of", "values"])


class TestModelFsmStateProtocols:
    """Test protocol implementations for ModelFsmState."""

    def test_execute_protocol_basic(self):
        """Test execute protocol method."""
        state = ModelFsmState(name="test")

        # Basic execution should succeed
        result = state.execute()
        assert result is True

    def test_execute_protocol_with_updates(self):
        """Test execute protocol with kwargs (frozen model - no mutation).

        Note: ModelFsmState is frozen (immutable), so execute() returns True
        but does not modify the model. This is intentional for thread safety.
        """
        state = ModelFsmState(name="test", description="original")

        # Execute with updates - model is frozen so no mutation occurs
        result = state.execute(description="updated description")
        assert result is True
        # Model remains unchanged due to frozen=True
        assert state.description == "original"

    def test_execute_protocol_invalid_field(self):
        """Test execute protocol with invalid field updates."""
        state = ModelFsmState(name="test")

        # Execute with non-existent field should still succeed
        result = state.execute(nonexistent_field="value")
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        state = ModelFsmState(
            name="test_state",
            description="Test description",
            is_initial=True,
            is_final=False,
            entry_actions=["action1"],
            exit_actions=["action2"],
            properties={"key": "value"},
        )

        serialized = state.serialize()

        assert isinstance(serialized, dict)
        assert serialized["name"] == "test_state"
        assert serialized["description"] == "Test description"
        assert serialized["is_initial"] is True
        assert serialized["is_final"] is False
        assert serialized["entry_actions"] == ["action1"]
        assert serialized["exit_actions"] == ["action2"]
        assert serialized["properties"] == {"key": "value"}

    def test_serialize_protocol_minimal(self):
        """Test serialize protocol with minimal state."""
        state = ModelFsmState(name="minimal")

        serialized = state.serialize()

        assert isinstance(serialized, dict)
        assert serialized["name"] == "minimal"
        assert "description" in serialized
        assert "is_initial" in serialized
        assert "is_final" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        state = ModelFsmState(name="test")

        # Basic validation should succeed
        result = state.validate_instance()
        assert result is True

    def test_validate_instance_protocol_complex(self):
        """Test validate_instance with complex state."""
        state = ModelFsmState(
            name="complex",
            description="Complex state",
            is_initial=True,
            is_final=False,
            entry_actions=["a1", "a2", "a3"],
            exit_actions=["e1", "e2"],
            properties={"p1": "v1", "p2": "v2"},
        )

        result = state.validate_instance()
        assert result is True


class TestModelFsmStateSerialization:
    """Test serialization and deserialization for ModelFsmState."""

    def test_model_dump(self):
        """Test model_dump method."""
        state = ModelFsmState(
            name="test",
            description="Test state",
            is_initial=False,
            is_final=True,
        )

        data = state.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == "test"
        assert data["description"] == "Test state"
        assert data["is_final"] is True

    def test_model_validate(self):
        """Test model_validate method."""
        data = {
            "name": "validated",
            "description": "Validated state",
            "is_initial": True,
            "is_final": False,
            "entry_actions": ["entry1"],
            "exit_actions": ["exit1"],
            "properties": {"prop": "val"},
        }

        state = ModelFsmState.model_validate(data)

        assert state.name == "validated"
        assert state.description == "Validated state"
        assert state.is_initial is True
        assert state.entry_actions == ["entry1"]
        assert state.exit_actions == ["exit1"]
        assert state.properties == {"prop": "val"}

    def test_model_dump_json(self):
        """Test JSON serialization."""
        state = ModelFsmState(name="json_test", is_initial=True)

        json_str = state.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert "is_initial" in json_str

    def test_model_validate_json(self):
        """Test JSON deserialization."""
        json_str = '{"name": "from_json", "is_final": true, "description": "From JSON"}'

        state = ModelFsmState.model_validate_json(json_str)

        assert state.name == "from_json"
        assert state.is_final is True
        assert state.description == "From JSON"


class TestModelFsmStateEdgeCases:
    """Test edge cases for ModelFsmState."""

    def test_empty_string_name(self):
        """Test state with empty string name."""
        # Empty name should be valid (no min length constraint)
        state = ModelFsmState(name="")
        assert state.name == ""

    def test_very_long_name(self):
        """Test state with very long name."""
        long_name = "state_" + "x" * 10000
        state = ModelFsmState(name=long_name)
        assert len(state.name) > 10000

    def test_name_with_special_characters(self):
        """Test state names with special characters."""
        special_names = [
            "state-with-dashes",
            "state_with_underscores",
            "state.with.dots",
            "state:with:colons",
            "state/with/slashes",
            "state with spaces",
            "état-français",
            "状態-日本語",
        ]

        for name in special_names:
            state = ModelFsmState(name=name)
            assert state.name == name

    def test_both_initial_and_final(self):
        """Test state that is both initial and final."""
        # This should be allowed (single-state FSM)
        state = ModelFsmState(name="single", is_initial=True, is_final=True)
        assert state.is_initial is True
        assert state.is_final is True

    def test_empty_actions_lists(self):
        """Test state with empty action lists."""
        state = ModelFsmState(name="empty", entry_actions=[], exit_actions=[])
        assert state.entry_actions == []
        assert state.exit_actions == []

    def test_duplicate_actions(self):
        """Test state with duplicate actions."""
        state = ModelFsmState(name="dup", entry_actions=["action", "action", "action"])
        # Duplicates should be preserved
        assert len(state.entry_actions) == 3
        assert state.entry_actions.count("action") == 3

    def test_empty_properties_dict(self):
        """Test state with empty properties."""
        state = ModelFsmState(name="empty_props", properties={})
        assert state.properties == {}

    def test_property_with_empty_values(self):
        """Test properties with empty string values."""
        state = ModelFsmState(name="test", properties={"key1": "", "key2": "value"})
        assert state.properties["key1"] == ""
        assert state.properties["key2"] == "value"

    def test_model_equality(self):
        """Test model equality comparison."""
        state1 = ModelFsmState(
            name="equal", description="Same", is_initial=True, entry_actions=["a1"]
        )
        state2 = ModelFsmState(
            name="equal", description="Same", is_initial=True, entry_actions=["a1"]
        )
        state3 = ModelFsmState(name="different", description="Same", is_initial=True)

        assert state1 == state2
        assert state1 != state3

    def test_frozen_config(self):
        """Test that frozen config prevents mutations."""
        state = ModelFsmState(name="test")

        # Model is frozen - assignment raises ValidationError
        with pytest.raises(ValidationError):
            state.description = "updated"

        # Invalid assignment also raises error
        with pytest.raises(ValidationError):
            state.is_initial = "not_a_boolean"

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per config."""
        data = {
            "name": "test",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        state = ModelFsmState.model_validate(data)
        assert state.name == "test"
        assert not hasattr(state, "extra_field")
        assert not hasattr(state, "another_extra")


@pytest.mark.unit
class TestModelFsmStateValidateInstanceFalse:
    """Test validate_instance returning False for invalid states."""

    def test_validate_instance_empty_name_returns_false(self):
        """Test validate_instance returns False for empty name."""
        state = ModelFsmState(name="", description="test")
        assert state.validate_instance() is False

    def test_validate_instance_whitespace_name_returns_false(self):
        """Test validate_instance returns False for whitespace-only name."""
        state = ModelFsmState(name="   ", description="test")
        assert state.validate_instance() is False

    def test_validate_instance_tab_only_name_returns_false(self):
        """Test validate_instance returns False for tab-only name."""
        state = ModelFsmState(name="\t\t", description="test")
        assert state.validate_instance() is False

    def test_validate_instance_newline_only_name_returns_false(self):
        """Test validate_instance returns False for newline-only name."""
        state = ModelFsmState(name="\n\n", description="test")
        assert state.validate_instance() is False

    def test_validate_instance_mixed_whitespace_returns_false(self):
        """Test validate_instance returns False with mixed whitespace characters."""
        state = ModelFsmState(name=" \t\n ", description="test")
        assert state.validate_instance() is False

    def test_validate_instance_valid_name_returns_true(self):
        """Test validate_instance returns True for valid name."""
        state = ModelFsmState(name="idle", description="test")
        assert state.validate_instance() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
