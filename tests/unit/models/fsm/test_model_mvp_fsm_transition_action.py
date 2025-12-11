"""
Unit tests for ModelMvpFSMTransitionAction.

Tests all aspects of the FSM transition action model including:
- Model instantiation and validation
- Default values (execution_order=0, is_critical=False, action_config={})
- Type validation for each field
- Protocol implementations (execute, serialize, validate_instance)
- Serialization/deserialization
- Edge cases (empty strings, negative execution_order, large timeout_ms)

Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.fsm.model_mvp_fsm_transition_action import (
    ModelMvpFSMTransitionAction,
)


class TestModelMvpFSMTransitionActionInstantiation:
    """Test cases for ModelMvpFSMTransitionAction instantiation."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal required data."""
        action = ModelMvpFSMTransitionAction(
            action_name="log_entry",
            action_type="log",
        )

        assert action.action_name == "log_entry"
        assert action.action_type == "log"
        assert action.action_config == {}  # Default value
        assert action.execution_order == 0  # Default value
        assert action.is_critical is False  # Default value
        assert action.rollback_action is None  # Default value
        assert action.timeout_ms is None  # Default value

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields populated."""
        action = ModelMvpFSMTransitionAction(
            action_name="emit_event",
            action_type="emit_intent",
            action_config={
                "target": "notification_service",
                "event_type": "state_change",
            },
            execution_order=5,
            is_critical=True,
            rollback_action="undo_emit_event",
            timeout_ms=5000,
        )

        assert action.action_name == "emit_event"
        assert action.action_type == "emit_intent"
        assert action.action_config == {
            "target": "notification_service",
            "event_type": "state_change",
        }
        assert action.execution_order == 5
        assert action.is_critical is True
        assert action.rollback_action == "undo_emit_event"
        assert action.timeout_ms == 5000

    def test_execution_order_default_zero(self):
        """Test that execution_order defaults to 0."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        assert action.execution_order == 0

    def test_execution_order_explicit_value(self):
        """Test setting execution_order explicitly."""
        action = ModelMvpFSMTransitionAction(
            action_name="ordered_action",
            action_type="validate",
            execution_order=10,
        )

        assert action.execution_order == 10

    def test_is_critical_default_false(self):
        """Test that is_critical defaults to False."""
        action = ModelMvpFSMTransitionAction(
            action_name="non_critical",
            action_type="log",
        )

        assert action.is_critical is False

    def test_is_critical_explicit_true(self):
        """Test setting is_critical to True explicitly."""
        action = ModelMvpFSMTransitionAction(
            action_name="critical_action",
            action_type="validate",
            is_critical=True,
        )

        assert action.is_critical is True

    def test_action_config_default_empty_dict(self):
        """Test that action_config defaults to empty dict."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        assert action.action_config == {}
        assert isinstance(action.action_config, dict)

    def test_action_config_with_data(self):
        """Test providing action_config with various data types.

        Note: ActionConfigValue supports: str | int | float | bool | list[str] | None
        Nested dicts and list[int] are NOT supported to comply with ONEX typing standards.
        """
        config = {
            "string_key": "value",
            "int_key": 42,
            "float_key": 3.14,
            "bool_key": True,
            "list_key": ["item1", "item2", "item3"],  # list[str], not list[int]
        }
        action = ModelMvpFSMTransitionAction(
            action_name="configured",
            action_type="custom",
            action_config=config,
        )

        assert action.action_config == config
        assert action.action_config["string_key"] == "value"
        assert action.action_config["int_key"] == 42
        assert action.action_config["list_key"] == ["item1", "item2", "item3"]

    def test_rollback_action_optional(self):
        """Test that rollback_action is optional and defaults to None."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        assert action.rollback_action is None

    def test_rollback_action_provided(self):
        """Test providing a rollback action."""
        action = ModelMvpFSMTransitionAction(
            action_name="reversible_action",
            action_type="modify",
            rollback_action="undo_modify",
        )

        assert action.rollback_action == "undo_modify"

    def test_timeout_ms_optional(self):
        """Test that timeout_ms is optional and defaults to None."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        assert action.timeout_ms is None

    def test_timeout_ms_provided(self):
        """Test providing timeout_ms."""
        action = ModelMvpFSMTransitionAction(
            action_name="timed_action",
            action_type="api_call",
            timeout_ms=30000,
        )

        assert action.timeout_ms == 30000


class TestModelMvpFSMTransitionActionValidation:
    """Test validation rules for ModelMvpFSMTransitionAction."""

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing all required fields
        with pytest.raises(ValidationError) as exc_info:
            ModelMvpFSMTransitionAction()
        error_str = str(exc_info.value)
        assert "action_name" in error_str
        assert "action_type" in error_str

    def test_missing_action_name(self):
        """Test that missing action_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMvpFSMTransitionAction(
                action_type="log",
            )
        assert "action_name" in str(exc_info.value)

    def test_missing_action_type(self):
        """Test that missing action_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMvpFSMTransitionAction(
                action_name="test",
            )
        assert "action_type" in str(exc_info.value)

    def test_action_name_type_validation(self):
        """Test that action_name must be a string."""
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name=123,
                action_type="log",
            )

        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name=None,
                action_type="log",
            )

        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name=["action"],
                action_type="log",
            )

    def test_action_type_type_validation(self):
        """Test that action_type must be a string."""
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name="test",
                action_type=123,
            )

        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name="test",
                action_type=None,
            )

    def test_action_config_type_validation(self):
        """Test that action_config must be a dict."""
        # String should fail
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name="test",
                action_type="log",
                action_config="not_a_dict",
            )

        # List should fail
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name="test",
                action_type="log",
                action_config=[1, 2, 3],
            )

    def test_execution_order_type_validation(self):
        """Test that execution_order must be an integer."""
        # Valid integer
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            execution_order=5,
        )
        assert action.execution_order == 5

        # Invalid type
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name="test",
                action_type="log",
                execution_order="not_an_int",
            )

    def test_is_critical_type_validation(self):
        """Test that is_critical accepts proper boolean types."""
        # Valid boolean values
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            is_critical=True,
        )
        assert action.is_critical is True

        action2 = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            is_critical=False,
        )
        assert action2.is_critical is False

        # Test invalid boolean values that Pydantic cannot coerce
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name="test",
                action_type="log",
                is_critical=["not_a_bool"],
            )

    def test_timeout_ms_type_validation(self):
        """Test that timeout_ms must be an integer or None."""
        # Valid integer
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            timeout_ms=5000,
        )
        assert action.timeout_ms == 5000

        # None is valid
        action2 = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            timeout_ms=None,
        )
        assert action2.timeout_ms is None

        # Invalid type
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionAction(
                action_name="test",
                action_type="log",
                timeout_ms="not_an_int",
            )


class TestModelMvpFSMTransitionActionProtocols:
    """Test protocol implementations for ModelMvpFSMTransitionAction."""

    def test_execute_protocol_basic(self):
        """Test execute protocol method."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        # Basic execution should succeed
        result = action.execute()
        assert result is True

    def test_execute_protocol_with_updates(self):
        """Test execute protocol with field updates."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            execution_order=1,
        )

        # Execute with updates
        result = action.execute(execution_order=5)
        assert result is True
        assert action.execution_order == 5

    def test_execute_protocol_update_is_critical(self):
        """Test execute protocol updating is_critical."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            is_critical=False,
        )

        result = action.execute(is_critical=True)
        assert result is True
        assert action.is_critical is True

    def test_execute_protocol_invalid_field(self):
        """Test execute protocol with invalid field updates."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        # Execute with non-existent field should still succeed
        result = action.execute(nonexistent_field="value")
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        action = ModelMvpFSMTransitionAction(
            action_name="emit_event",
            action_type="emit_intent",
            action_config={"target": "service"},
            execution_order=2,
            is_critical=True,
            rollback_action="undo",
            timeout_ms=3000,
        )

        serialized = action.serialize()

        assert isinstance(serialized, dict)
        assert serialized["action_name"] == "emit_event"
        assert serialized["action_type"] == "emit_intent"
        assert serialized["action_config"] == {"target": "service"}
        assert serialized["execution_order"] == 2
        assert serialized["is_critical"] is True
        assert serialized["rollback_action"] == "undo"
        assert serialized["timeout_ms"] == 3000

    def test_serialize_protocol_minimal(self):
        """Test serialize protocol with minimal action."""
        action = ModelMvpFSMTransitionAction(
            action_name="simple",
            action_type="log",
        )

        serialized = action.serialize()

        assert isinstance(serialized, dict)
        assert serialized["action_name"] == "simple"
        assert serialized["action_type"] == "log"
        assert serialized["action_config"] == {}
        assert serialized["execution_order"] == 0
        assert serialized["is_critical"] is False
        assert serialized["rollback_action"] is None
        assert serialized["timeout_ms"] is None

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        # Basic validation should succeed
        result = action.validate_instance()
        assert result is True

    def test_validate_instance_protocol_complex(self):
        """Test validate_instance with complex action.

        Note: action_config values are flat (no nested dicts) per ONEX typing standards.
        """
        action = ModelMvpFSMTransitionAction(
            action_name="complex_action",
            action_type="emit_intent",
            action_config={
                "intent_name": "user_logged_in",
                "priority": 10,
                "tags": ["auth", "login", "user"],
            },
            execution_order=10,
            is_critical=True,
            rollback_action="rollback_complex",
            timeout_ms=60000,
        )

        result = action.validate_instance()
        assert result is True


class TestModelMvpFSMTransitionActionSerialization:
    """Test serialization and deserialization for ModelMvpFSMTransitionAction."""

    def test_model_dump(self):
        """Test model_dump method."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            action_config={"level": "info"},
            execution_order=1,
            is_critical=True,
        )

        data = action.model_dump()

        assert isinstance(data, dict)
        assert data["action_name"] == "test"
        assert data["action_type"] == "log"
        assert data["action_config"] == {"level": "info"}
        assert data["execution_order"] == 1
        assert data["is_critical"] is True

    def test_model_validate(self):
        """Test model_validate method."""
        data = {
            "action_name": "validated_action",
            "action_type": "emit_intent",
            "action_config": {"target": "service"},
            "execution_order": 3,
            "is_critical": False,
            "rollback_action": "undo_action",
            "timeout_ms": 5000,
        }

        action = ModelMvpFSMTransitionAction.model_validate(data)

        assert action.action_name == "validated_action"
        assert action.action_type == "emit_intent"
        assert action.action_config == {"target": "service"}
        assert action.execution_order == 3
        assert action.is_critical is False
        assert action.rollback_action == "undo_action"
        assert action.timeout_ms == 5000

    def test_model_dump_json(self):
        """Test JSON serialization."""
        action = ModelMvpFSMTransitionAction(
            action_name="json_test",
            action_type="log",
            action_config={"key": "value"},
        )

        json_str = action.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert "log" in json_str

    def test_model_validate_json(self):
        """Test JSON deserialization."""
        json_str = '{"action_name": "from_json", "action_type": "custom", "action_config": {"param": "value"}, "execution_order": 2}'

        action = ModelMvpFSMTransitionAction.model_validate_json(json_str)

        assert action.action_name == "from_json"
        assert action.action_type == "custom"
        assert action.action_config == {"param": "value"}
        assert action.execution_order == 2

    def test_roundtrip_serialization(self):
        """Test full roundtrip serialization/deserialization."""
        original = ModelMvpFSMTransitionAction(
            action_name="roundtrip_test",
            action_type="emit_intent",
            action_config={"target": "service", "data": ["item1", "item2", "item3"]},
            execution_order=5,
            is_critical=True,
            rollback_action="undo_roundtrip",
            timeout_ms=10000,
        )

        # Serialize to dict and back
        data = original.model_dump()
        restored = ModelMvpFSMTransitionAction.model_validate(data)

        assert restored == original

        # Serialize to JSON and back
        json_str = original.model_dump_json()
        restored_from_json = ModelMvpFSMTransitionAction.model_validate_json(json_str)

        assert restored_from_json == original


class TestModelMvpFSMTransitionActionEdgeCases:
    """Test edge cases for ModelMvpFSMTransitionAction."""

    def test_empty_string_action_name(self):
        """Test action with empty string action_name."""
        action = ModelMvpFSMTransitionAction(
            action_name="",
            action_type="log",
        )
        assert action.action_name == ""

    def test_empty_string_action_type(self):
        """Test action with empty string action_type."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="",
        )
        assert action.action_type == ""

    def test_action_name_with_special_characters(self):
        """Test action names with special characters."""
        special_names = [
            "action-with-dashes",
            "action_with_underscores",
            "action.with.dots",
            "action:with:colons",
            "action/with/slashes",
            "action with spaces",
            "action_francais",
            "action_123",
        ]

        for name in special_names:
            action = ModelMvpFSMTransitionAction(
                action_name=name,
                action_type="log",
            )
            assert action.action_name == name

    def test_action_type_variations(self):
        """Test various action types."""
        action_types = [
            "log",
            "emit_intent",
            "validate",
            "modify",
            "api_call",
            "notification",
            "cleanup",
            "custom",
        ]

        for atype in action_types:
            action = ModelMvpFSMTransitionAction(
                action_name="test",
                action_type=atype,
            )
            assert action.action_type == atype

    def test_negative_execution_order(self):
        """Test that negative execution_order is accepted."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            execution_order=-5,
        )
        assert action.execution_order == -5

    def test_zero_execution_order(self):
        """Test execution_order with zero value (default)."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            execution_order=0,
        )
        assert action.execution_order == 0

    def test_large_execution_order(self):
        """Test with large execution_order value."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            execution_order=1000000,
        )
        assert action.execution_order == 1000000

    def test_timeout_ms_zero(self):
        """Test timeout_ms with zero value."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            timeout_ms=0,
        )
        assert action.timeout_ms == 0

    def test_negative_timeout_ms(self):
        """Test that negative timeout_ms is accepted (no constraint in spec)."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            timeout_ms=-1000,
        )
        assert action.timeout_ms == -1000

    def test_large_timeout_ms(self):
        """Test with large timeout_ms value (24 hours)."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            timeout_ms=86400000,  # 24 hours in ms
        )
        assert action.timeout_ms == 86400000

    def test_action_config_empty_dict(self):
        """Test action_config with explicitly empty dict."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            action_config={},
        )
        assert action.action_config == {}

    def test_action_config_flat_structure(self):
        """Test action_config with flat structure (no nesting per ONEX standards).

        Note: ActionConfigValue supports: str | int | float | bool | list[str] | None
        Nested dicts are NOT supported to comply with ONEX typing standards.
        """
        flat_config = {
            "level": "info",
            "message": "test message",
            "count": 42,
            "enabled": True,
            "tags": ["tag1", "tag2"],
        }
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            action_config=flat_config,
        )
        assert action.action_config["level"] == "info"
        assert action.action_config["count"] == 42
        assert action.action_config["tags"] == ["tag1", "tag2"]

    def test_action_config_with_none_value(self):
        """Test action_config containing None values."""
        config = {
            "key1": "value",
            "key2": None,
            "key3": 123,
        }
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            action_config=config,
        )
        assert action.action_config["key2"] is None

    def test_action_config_with_list_values(self):
        """Test action_config containing list values.

        Note: Only list[str] is supported per ONEX typing standards (ActionConfigValue).
        """
        config = {
            "targets": ["service1", "service2"],
            "tags": ["high", "medium", "low"],  # list[str], not list[int]
        }
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="emit_intent",
            action_config=config,
        )
        assert action.action_config["targets"] == ["service1", "service2"]
        assert action.action_config["tags"] == ["high", "medium", "low"]

    def test_rollback_action_with_special_characters(self):
        """Test rollback_action with special characters."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            rollback_action="undo-action_name.v2",
        )
        assert action.rollback_action == "undo-action_name.v2"

    def test_model_equality(self):
        """Test model equality comparison."""
        action1 = ModelMvpFSMTransitionAction(
            action_name="equal",
            action_type="log",
            execution_order=1,
        )
        action2 = ModelMvpFSMTransitionAction(
            action_name="equal",
            action_type="log",
            execution_order=1,
        )
        action3 = ModelMvpFSMTransitionAction(
            action_name="different",
            action_type="log",
            execution_order=1,
        )

        assert action1 == action2
        assert action1 != action3

    def test_validate_assignment_config(self):
        """Test that validate_assignment config works."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        # Should allow assignment
        action.execution_order = 10
        assert action.execution_order == 10

        # Invalid assignment should raise error
        with pytest.raises(ValidationError):
            action.is_critical = "not_a_boolean"

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per config."""
        data = {
            "action_name": "test",
            "action_type": "log",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        action = ModelMvpFSMTransitionAction.model_validate(data)
        assert action.action_name == "test"
        assert not hasattr(action, "extra_field")
        assert not hasattr(action, "another_extra")

    def test_action_config_default_factory_isolation(self):
        """Test that default_factory creates new dicts for each instance."""
        action1 = ModelMvpFSMTransitionAction(
            action_name="test1",
            action_type="log",
        )
        action2 = ModelMvpFSMTransitionAction(
            action_name="test2",
            action_type="log",
        )

        # Modify action1's config
        action1.action_config["modified"] = True

        # action2 should not be affected
        assert "modified" not in action2.action_config

    def test_very_long_action_name(self):
        """Test action with very long action_name."""
        long_name = "action_" + "x" * 10000
        action = ModelMvpFSMTransitionAction(
            action_name=long_name,
            action_type="log",
        )
        assert len(action.action_name) > 10000


class TestModelMvpFSMTransitionActionReservedFields:
    """Test reserved fields for v1.1+ compatibility."""

    def test_rollback_action_reserved_note(self):
        """Test that rollback_action can be set (reserved for v1.1+)."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
            rollback_action="undo_action",
        )

        # Field should be set but has no effect in v1.0
        assert action.rollback_action == "undo_action"

    def test_rollback_action_none_default(self):
        """Test that rollback_action defaults to None."""
        action = ModelMvpFSMTransitionAction(
            action_name="test",
            action_type="log",
        )

        assert action.rollback_action is None


class TestModelMvpFSMTransitionActionImport:
    """Test that the model can be imported from the fsm module."""

    def test_import_from_fsm_module(self):
        """Test importing from the fsm package."""
        from omnibase_core.models.fsm import (
            ModelMvpFSMTransitionAction as ImportedModel,
        )

        action = ImportedModel(
            action_name="import_test",
            action_type="log",
        )

        assert action.action_name == "import_test"

    def test_import_from_direct_module(self):
        """Test importing directly from the model file."""
        from omnibase_core.models.fsm.model_mvp_fsm_transition_action import (
            ModelMvpFSMTransitionAction as DirectModel,
        )

        action = DirectModel(
            action_name="direct_import",
            action_type="emit_intent",
        )

        assert action.action_name == "direct_import"


class TestModelMvpFSMTransitionActionDocstrings:
    """Test model documentation and field descriptions."""

    def test_model_has_docstring(self):
        """Test that the model has a proper docstring."""
        assert ModelMvpFSMTransitionAction.__doc__ is not None
        assert (
            "Action specification for FSM state transitions"
            in ModelMvpFSMTransitionAction.__doc__
        )

    def test_field_descriptions_present(self):
        """Test that all fields have descriptions."""
        fields = ModelMvpFSMTransitionAction.model_fields

        assert fields["action_name"].description is not None
        assert fields["action_type"].description is not None
        assert fields["action_config"].description is not None
        assert fields["execution_order"].description is not None
        assert fields["is_critical"].description is not None
        assert fields["rollback_action"].description is not None
        assert fields["timeout_ms"].description is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
