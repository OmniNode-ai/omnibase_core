"""
Unit tests for ModelFsmTransition.

Tests all aspects of the FSM transition model including:
- Model instantiation and validation
- Transition fields (from_state, to_state, trigger)
- Conditions and actions
- Protocol implementations (execute, serialize, validate)
- Edge cases and error conditions
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.fsm.model_fsm_transition import ModelFsmTransition


class TestModelFsmTransitionInstantiation:
    """Test cases for ModelFsmTransition instantiation."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal required data."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger="start"
        )

        assert transition.from_state == "idle"
        assert transition.to_state == "active"
        assert transition.trigger == "start"
        assert transition.conditions == []
        assert transition.actions == []

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields populated."""
        transition = ModelFsmTransition(
            from_state="waiting",
            to_state="processing",
            trigger="data_received",
            conditions=["has_valid_data", "has_capacity"],
            actions=["log_transition", "update_metrics", "notify_observers"],
        )

        assert transition.from_state == "waiting"
        assert transition.to_state == "processing"
        assert transition.trigger == "data_received"
        assert transition.conditions == ["has_valid_data", "has_capacity"]
        assert transition.actions == [
            "log_transition",
            "update_metrics",
            "notify_observers",
        ]

    def test_transition_with_conditions(self):
        """Test transition with multiple conditions."""
        transition = ModelFsmTransition(
            from_state="ready",
            to_state="executing",
            trigger="execute",
            conditions=["has_resources", "is_authorized", "within_time_window"],
        )

        assert len(transition.conditions) == 3
        assert "has_resources" in transition.conditions
        assert "is_authorized" in transition.conditions

    def test_transition_with_actions(self):
        """Test transition with multiple actions."""
        transition = ModelFsmTransition(
            from_state="idle",
            to_state="busy",
            trigger="work",
            actions=["acquire_lock", "start_timer", "log_start"],
        )

        assert len(transition.actions) == 3
        assert "acquire_lock" in transition.actions
        assert "start_timer" in transition.actions

    def test_self_transition(self):
        """Test transition from a state to itself."""
        transition = ModelFsmTransition(
            from_state="processing", to_state="processing", trigger="retry"
        )

        assert transition.from_state == transition.to_state
        assert transition.from_state == "processing"


class TestModelFsmTransitionValidation:
    """Test validation rules for ModelFsmTransition."""

    def test_required_fields_validation(self):
        """Test that all required fields are validated."""
        # Missing from_state
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmTransition(to_state="active", trigger="start")
        assert "from_state" in str(exc_info.value)

        # Missing to_state
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmTransition(from_state="idle", trigger="start")
        assert "to_state" in str(exc_info.value)

        # Missing trigger
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmTransition(from_state="idle", to_state="active")
        assert "trigger" in str(exc_info.value)

    def test_from_state_field_type_validation(self):
        """Test that from_state field must be a string."""
        with pytest.raises(ValidationError):
            ModelFsmTransition(from_state=123, to_state="active", trigger="start")

        with pytest.raises(ValidationError):
            ModelFsmTransition(from_state=None, to_state="active", trigger="start")

        with pytest.raises(ValidationError):
            ModelFsmTransition(from_state=["state"], to_state="active", trigger="start")

    def test_to_state_field_type_validation(self):
        """Test that to_state field must be a string."""
        with pytest.raises(ValidationError):
            ModelFsmTransition(from_state="idle", to_state=456, trigger="start")

        with pytest.raises(ValidationError):
            ModelFsmTransition(from_state="idle", to_state=None, trigger="start")

    def test_trigger_field_type_validation(self):
        """Test that trigger field must be a string."""
        with pytest.raises(ValidationError):
            ModelFsmTransition(from_state="idle", to_state="active", trigger=789)

        with pytest.raises(ValidationError):
            ModelFsmTransition(from_state="idle", to_state="active", trigger=None)

    def test_conditions_list_validation(self):
        """Test that conditions must be a list of strings."""
        # Valid list of strings
        transition = ModelFsmTransition(
            from_state="a",
            to_state="b",
            trigger="t",
            conditions=["cond1", "cond2"],
        )
        assert transition.conditions == ["cond1", "cond2"]

        # Invalid type for conditions
        with pytest.raises(ValidationError):
            ModelFsmTransition(
                from_state="a",
                to_state="b",
                trigger="t",
                conditions="not_a_list",
            )

        with pytest.raises(ValidationError):
            ModelFsmTransition(
                from_state="a",
                to_state="b",
                trigger="t",
                conditions=[1, 2, 3],
            )

    def test_actions_list_validation(self):
        """Test that actions must be a list of strings."""
        # Valid list of strings
        transition = ModelFsmTransition(
            from_state="a",
            to_state="b",
            trigger="t",
            actions=["action1", "action2"],
        )
        assert transition.actions == ["action1", "action2"]

        # Invalid type for actions
        with pytest.raises(ValidationError):
            ModelFsmTransition(
                from_state="a",
                to_state="b",
                trigger="t",
                actions={"action": "value"},
            )

        with pytest.raises(ValidationError):
            ModelFsmTransition(
                from_state="a",
                to_state="b",
                trigger="t",
                actions=[True, False],
            )


class TestModelFsmTransitionProtocols:
    """Test protocol implementations for ModelFsmTransition."""

    def test_execute_protocol_basic(self):
        """Test execute protocol method."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger="start"
        )

        result = transition.execute()
        assert result is True

    def test_execute_protocol_with_updates(self):
        """Test execute protocol with kwargs (frozen model - no mutation).

        Note: ModelFsmTransition is frozen (immutable), so execute() returns True
        but does not modify the model. This is intentional for thread safety.
        """
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger="start"
        )

        # Execute with updates - model is frozen so no mutation occurs
        result = transition.execute(trigger="updated_trigger")
        assert result is True
        # Model remains unchanged due to frozen=True
        assert transition.trigger == "start"

    def test_execute_protocol_invalid_field(self):
        """Test execute protocol with non-existent field."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger="start"
        )

        # Should succeed but not update anything
        result = transition.execute(nonexistent_field="value")
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        transition = ModelFsmTransition(
            from_state="waiting",
            to_state="processing",
            trigger="process",
            conditions=["condition1"],
            actions=["action1"],
        )

        serialized = transition.serialize()

        assert isinstance(serialized, dict)
        assert serialized["from_state"] == "waiting"
        assert serialized["to_state"] == "processing"
        assert serialized["trigger"] == "process"
        assert serialized["conditions"] == ["condition1"]
        assert serialized["actions"] == ["action1"]

    def test_serialize_protocol_minimal(self):
        """Test serialize protocol with minimal transition."""
        transition = ModelFsmTransition(from_state="a", to_state="b", trigger="trigger")

        serialized = transition.serialize()

        assert isinstance(serialized, dict)
        assert serialized["from_state"] == "a"
        assert serialized["to_state"] == "b"
        assert serialized["trigger"] == "trigger"
        assert "conditions" in serialized
        assert "actions" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger="start"
        )

        result = transition.validate_instance()
        assert result is True

    def test_validate_instance_protocol_complex(self):
        """Test validate_instance with complex transition."""
        transition = ModelFsmTransition(
            from_state="complex_from",
            to_state="complex_to",
            trigger="complex_trigger",
            conditions=["c1", "c2", "c3"],
            actions=["a1", "a2", "a3", "a4"],
        )

        result = transition.validate_instance()
        assert result is True


class TestModelFsmTransitionSerialization:
    """Test serialization and deserialization for ModelFsmTransition."""

    def test_model_dump(self):
        """Test model_dump method."""
        transition = ModelFsmTransition(
            from_state="start",
            to_state="end",
            trigger="finish",
            conditions=["ready"],
            actions=["cleanup"],
        )

        data = transition.model_dump()

        assert isinstance(data, dict)
        assert data["from_state"] == "start"
        assert data["to_state"] == "end"
        assert data["trigger"] == "finish"
        assert data["conditions"] == ["ready"]
        assert data["actions"] == ["cleanup"]

    def test_model_validate(self):
        """Test model_validate method."""
        data = {
            "from_state": "validated_from",
            "to_state": "validated_to",
            "trigger": "validated_trigger",
            "conditions": ["cond1", "cond2"],
            "actions": ["act1", "act2"],
        }

        transition = ModelFsmTransition.model_validate(data)

        assert transition.from_state == "validated_from"
        assert transition.to_state == "validated_to"
        assert transition.trigger == "validated_trigger"
        assert transition.conditions == ["cond1", "cond2"]
        assert transition.actions == ["act1", "act2"]

    def test_model_dump_json(self):
        """Test JSON serialization."""
        transition = ModelFsmTransition(
            from_state="json_from", to_state="json_to", trigger="json_trigger"
        )

        json_str = transition.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_from" in json_str
        assert "json_to" in json_str
        assert "json_trigger" in json_str

    def test_model_validate_json(self):
        """Test JSON deserialization."""
        json_str = '{"from_state": "from_json", "to_state": "to_json", "trigger": "json_event"}'

        transition = ModelFsmTransition.model_validate_json(json_str)

        assert transition.from_state == "from_json"
        assert transition.to_state == "to_json"
        assert transition.trigger == "json_event"


class TestModelFsmTransitionEdgeCases:
    """Test edge cases for ModelFsmTransition."""

    def test_empty_string_states(self):
        """Test transitions with empty string state names."""
        transition = ModelFsmTransition(from_state="", to_state="", trigger="event")
        assert transition.from_state == ""
        assert transition.to_state == ""

    def test_empty_string_trigger(self):
        """Test transition with empty string trigger."""
        transition = ModelFsmTransition(from_state="a", to_state="b", trigger="")
        assert transition.trigger == ""

    def test_very_long_state_names(self):
        """Test transitions with very long state names."""
        long_state = "state_" + "x" * 10000
        transition = ModelFsmTransition(
            from_state=long_state, to_state=long_state, trigger="event"
        )
        assert len(transition.from_state) > 10000

    def test_state_names_with_special_characters(self):
        """Test state names with special characters."""
        special_names = [
            "state-with-dashes",
            "state_with_underscores",
            "state.with.dots",
            "state:with:colons",
            "state/with/slashes",
            "state with spaces",
        ]

        for name in special_names:
            transition = ModelFsmTransition(
                from_state=name, to_state="target", trigger="event"
            )
            assert transition.from_state == name

    def test_trigger_with_special_characters(self):
        """Test triggers with special characters."""
        special_triggers = [
            "trigger-with-dashes",
            "trigger_with_underscores",
            "trigger.with.dots",
            "trigger:with:colons",
            "TRIGGER_IN_CAPS",
            "triggerWithCamelCase",
            "trigger with spaces",
        ]

        for trigger in special_triggers:
            transition = ModelFsmTransition(
                from_state="a", to_state="b", trigger=trigger
            )
            assert transition.trigger == trigger

    def test_empty_conditions_list(self):
        """Test transition with empty conditions list."""
        transition = ModelFsmTransition(
            from_state="a", to_state="b", trigger="t", conditions=[]
        )
        assert transition.conditions == []

    def test_empty_actions_list(self):
        """Test transition with empty actions list."""
        transition = ModelFsmTransition(
            from_state="a", to_state="b", trigger="t", actions=[]
        )
        assert transition.actions == []

    def test_duplicate_conditions(self):
        """Test transition with duplicate conditions."""
        transition = ModelFsmTransition(
            from_state="a",
            to_state="b",
            trigger="t",
            conditions=["check", "check", "check"],
        )
        # Duplicates should be preserved
        assert len(transition.conditions) == 3
        assert transition.conditions.count("check") == 3

    def test_duplicate_actions(self):
        """Test transition with duplicate actions."""
        transition = ModelFsmTransition(
            from_state="a",
            to_state="b",
            trigger="t",
            actions=["action", "action"],
        )
        # Duplicates should be preserved
        assert len(transition.actions) == 2

    def test_model_equality(self):
        """Test model equality comparison."""
        t1 = ModelFsmTransition(
            from_state="a",
            to_state="b",
            trigger="t",
            conditions=["c1"],
            actions=["a1"],
        )
        t2 = ModelFsmTransition(
            from_state="a",
            to_state="b",
            trigger="t",
            conditions=["c1"],
            actions=["a1"],
        )
        t3 = ModelFsmTransition(from_state="a", to_state="c", trigger="t")

        assert t1 == t2
        assert t1 != t3

    def test_frozen_config(self):
        """Test that frozen config prevents mutations."""
        transition = ModelFsmTransition(from_state="a", to_state="b", trigger="start")

        # Model is frozen - assignment raises ValidationError
        with pytest.raises(ValidationError):
            transition.trigger = "updated"

        # Invalid assignment also raises error
        with pytest.raises(ValidationError):
            transition.from_state = 123

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per config."""
        data = {
            "from_state": "a",
            "to_state": "b",
            "trigger": "t",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        transition = ModelFsmTransition.model_validate(data)
        assert transition.from_state == "a"
        assert not hasattr(transition, "extra_field")
        assert not hasattr(transition, "another_extra")

    def test_circular_transitions(self):
        """Test modeling circular transition patterns."""
        # Circular: A -> B -> C -> A
        t1 = ModelFsmTransition(from_state="A", to_state="B", trigger="next")
        t2 = ModelFsmTransition(from_state="B", to_state="C", trigger="next")
        t3 = ModelFsmTransition(from_state="C", to_state="A", trigger="next")

        assert t1.to_state == t2.from_state
        assert t2.to_state == t3.from_state
        assert t3.to_state == t1.from_state

    def test_bidirectional_transitions(self):
        """Test modeling bidirectional transitions."""
        forward = ModelFsmTransition(from_state="on", to_state="off", trigger="toggle")
        backward = ModelFsmTransition(from_state="off", to_state="on", trigger="toggle")

        assert forward.from_state == backward.to_state
        assert forward.to_state == backward.from_state
        assert forward.trigger == backward.trigger


@pytest.mark.unit
class TestModelFsmTransitionValidateInstanceFalse:
    """Test validate_instance returning False for invalid states."""

    def test_validate_instance_empty_from_state_returns_false(self):
        """Test validate_instance returns False for empty from_state."""
        transition = ModelFsmTransition(
            from_state="", to_state="active", trigger="start"
        )
        assert transition.validate_instance() is False

    def test_validate_instance_whitespace_from_state_returns_false(self):
        """Test validate_instance returns False for whitespace-only from_state."""
        transition = ModelFsmTransition(
            from_state="   ", to_state="active", trigger="start"
        )
        assert transition.validate_instance() is False

    def test_validate_instance_empty_to_state_returns_false(self):
        """Test validate_instance returns False for empty to_state."""
        transition = ModelFsmTransition(from_state="idle", to_state="", trigger="start")
        assert transition.validate_instance() is False

    def test_validate_instance_whitespace_to_state_returns_false(self):
        """Test validate_instance returns False for whitespace-only to_state."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="   ", trigger="start"
        )
        assert transition.validate_instance() is False

    def test_validate_instance_empty_trigger_returns_false(self):
        """Test validate_instance returns False for empty trigger."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger=""
        )
        assert transition.validate_instance() is False

    def test_validate_instance_whitespace_trigger_returns_false(self):
        """Test validate_instance returns False for whitespace-only trigger."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger="   "
        )
        assert transition.validate_instance() is False

    def test_validate_instance_valid_returns_true(self):
        """Test validate_instance returns True for valid transition."""
        transition = ModelFsmTransition(
            from_state="idle", to_state="active", trigger="start"
        )
        assert transition.validate_instance() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
