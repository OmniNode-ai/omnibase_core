# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for EnumHandlerCommandType.

Tests all aspects of the handler command type enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization (JSON, YAML, pickle)
- Helper methods (values, assert_exhaustive)
- Pydantic model compatibility
- Edge cases and error conditions
- Property-based testing with hypothesis
"""

import copy
import json
import pickle
from enum import Enum

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_handler_command_type import EnumHandlerCommandType


@pytest.mark.unit
class TestEnumHandlerCommandType:
    """Test cases for EnumHandlerCommandType enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumHandlerCommandType.EXECUTE == "execute"
        assert EnumHandlerCommandType.VALIDATE == "validate"
        assert EnumHandlerCommandType.DRY_RUN == "dry_run"
        assert EnumHandlerCommandType.ROLLBACK == "rollback"
        assert EnumHandlerCommandType.HEALTH_CHECK == "health_check"
        assert EnumHandlerCommandType.DESCRIBE == "describe"
        assert EnumHandlerCommandType.CONFIGURE == "configure"
        assert EnumHandlerCommandType.RESET == "reset"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumHandlerCommandType, str)
        assert issubclass(EnumHandlerCommandType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values via __str__."""
        # The custom __str__ returns the value, not the enum name
        assert str(EnumHandlerCommandType.EXECUTE) == "execute"
        assert str(EnumHandlerCommandType.VALIDATE) == "validate"
        assert str(EnumHandlerCommandType.DRY_RUN) == "dry_run"
        assert str(EnumHandlerCommandType.ROLLBACK) == "rollback"
        assert str(EnumHandlerCommandType.HEALTH_CHECK) == "health_check"
        assert str(EnumHandlerCommandType.DESCRIBE) == "describe"
        assert str(EnumHandlerCommandType.CONFIGURE) == "configure"
        assert str(EnumHandlerCommandType.RESET) == "reset"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumHandlerCommandType)
        assert len(values) == 8
        assert EnumHandlerCommandType.EXECUTE in values
        assert EnumHandlerCommandType.VALIDATE in values
        assert EnumHandlerCommandType.DRY_RUN in values
        assert EnumHandlerCommandType.ROLLBACK in values
        assert EnumHandlerCommandType.HEALTH_CHECK in values
        assert EnumHandlerCommandType.DESCRIBE in values
        assert EnumHandlerCommandType.CONFIGURE in values
        assert EnumHandlerCommandType.RESET in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "execute" in EnumHandlerCommandType
        assert "validate" in EnumHandlerCommandType
        assert "dry_run" in EnumHandlerCommandType
        assert "rollback" in EnumHandlerCommandType
        assert "health_check" in EnumHandlerCommandType
        assert "describe" in EnumHandlerCommandType
        assert "configure" in EnumHandlerCommandType
        assert "reset" in EnumHandlerCommandType
        # Invalid values
        assert "invalid" not in EnumHandlerCommandType
        assert "EXECUTE" not in EnumHandlerCommandType  # Case sensitive

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumHandlerCommandType.EXECUTE == "execute"
        assert EnumHandlerCommandType.VALIDATE == "validate"
        assert EnumHandlerCommandType.DRY_RUN == "dry_run"
        assert EnumHandlerCommandType.ROLLBACK == "rollback"
        assert EnumHandlerCommandType.HEALTH_CHECK == "health_check"
        assert EnumHandlerCommandType.DESCRIBE == "describe"
        assert EnumHandlerCommandType.CONFIGURE == "configure"
        assert EnumHandlerCommandType.RESET == "reset"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumHandlerCommandType.EXECUTE.value == "execute"
        assert EnumHandlerCommandType.VALIDATE.value == "validate"
        assert EnumHandlerCommandType.DRY_RUN.value == "dry_run"
        assert EnumHandlerCommandType.ROLLBACK.value == "rollback"
        assert EnumHandlerCommandType.HEALTH_CHECK.value == "health_check"
        assert EnumHandlerCommandType.DESCRIBE.value == "describe"
        assert EnumHandlerCommandType.CONFIGURE.value == "configure"
        assert EnumHandlerCommandType.RESET.value == "reset"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumHandlerCommandType("execute") == EnumHandlerCommandType.EXECUTE
        assert EnumHandlerCommandType("validate") == EnumHandlerCommandType.VALIDATE
        assert EnumHandlerCommandType("dry_run") == EnumHandlerCommandType.DRY_RUN
        assert EnumHandlerCommandType("rollback") == EnumHandlerCommandType.ROLLBACK
        assert (
            EnumHandlerCommandType("health_check")
            == EnumHandlerCommandType.HEALTH_CHECK
        )
        assert EnumHandlerCommandType("describe") == EnumHandlerCommandType.DESCRIBE
        assert EnumHandlerCommandType("configure") == EnumHandlerCommandType.CONFIGURE
        assert EnumHandlerCommandType("reset") == EnumHandlerCommandType.RESET

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerCommandType("invalid")
        with pytest.raises(ValueError):
            EnumHandlerCommandType("EXECUTE")  # Case sensitive
        with pytest.raises(ValueError):
            EnumHandlerCommandType("")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [cmd.value for cmd in EnumHandlerCommandType]
        expected_values = [
            "execute",
            "validate",
            "dry_run",
            "rollback",
            "health_check",
            "describe",
            "configure",
            "reset",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "handler command types" in EnumHandlerCommandType.__doc__.lower()
        assert "SINGLE SOURCE OF TRUTH" in EnumHandlerCommandType.__doc__
        assert "EXECUTE" in EnumHandlerCommandType.__doc__
        assert "VALIDATE" in EnumHandlerCommandType.__doc__
        assert "DRY_RUN" in EnumHandlerCommandType.__doc__
        assert "ROLLBACK" in EnumHandlerCommandType.__doc__


@pytest.mark.unit
class TestEnumHandlerCommandTypeHelperMethods:
    """Test cases for EnumHandlerCommandType helper methods."""

    def test_values_classmethod(self):
        """Test the values() classmethod returns all string values."""
        values = EnumHandlerCommandType.values()
        assert isinstance(values, list)
        assert len(values) == 8
        assert "execute" in values
        assert "validate" in values
        assert "dry_run" in values
        assert "rollback" in values
        assert "health_check" in values
        assert "describe" in values
        assert "configure" in values
        assert "reset" in values

    def test_values_returns_strings(self):
        """Test that values() returns strings, not enum members."""
        values = EnumHandlerCommandType.values()
        for value in values:
            assert isinstance(value, str)
            assert not isinstance(value, EnumHandlerCommandType)

    def test_assert_exhaustive_raises_assertion_error(self) -> None:
        """Test that assert_exhaustive raises AssertionError.

        Note: Uses AssertionError instead of ModelOnexError to avoid
        circular imports in the enum module.
        """
        # Create a mock value that would represent an unhandled case
        # In practice, this should never be called with a valid enum value
        # We test it with a string that's not a valid enum member
        with pytest.raises(AssertionError) as exc_info:
            # Intentionally passing invalid type to test runtime behavior
            EnumHandlerCommandType.assert_exhaustive("unhandled_value")
        assert "Unhandled enum value: unhandled_value" in str(exc_info.value)

    def test_assert_exhaustive_message_format(self) -> None:
        """Test that assert_exhaustive error message is properly formatted."""
        with pytest.raises(AssertionError) as exc_info:
            EnumHandlerCommandType.assert_exhaustive(42)
        assert "Unhandled enum value: 42" in str(exc_info.value)


@pytest.mark.unit
class TestEnumHandlerCommandTypeCategories:
    """Test cases for command type categorization."""

    def test_primary_execution_commands(self):
        """Test primary execution command types."""
        primary_commands = {
            EnumHandlerCommandType.EXECUTE,
            EnumHandlerCommandType.DRY_RUN,
        }
        for cmd in primary_commands:
            assert cmd in EnumHandlerCommandType

    def test_validation_commands(self):
        """Test validation command types."""
        validation_commands = {
            EnumHandlerCommandType.VALIDATE,
            EnumHandlerCommandType.HEALTH_CHECK,
        }
        for cmd in validation_commands:
            assert cmd in EnumHandlerCommandType

    def test_state_management_commands(self):
        """Test state management command types."""
        state_commands = {
            EnumHandlerCommandType.ROLLBACK,
            EnumHandlerCommandType.RESET,
            EnumHandlerCommandType.CONFIGURE,
        }
        for cmd in state_commands:
            assert cmd in EnumHandlerCommandType

    def test_introspection_commands(self):
        """Test introspection command types."""
        introspection_commands = {
            EnumHandlerCommandType.DESCRIBE,
        }
        for cmd in introspection_commands:
            assert cmd in EnumHandlerCommandType


@pytest.mark.unit
class TestEnumHandlerCommandTypeExhaustiveness:
    """Test exhaustive handling of all enum values."""

    def test_exhaustive_match_coverage(self):
        """Test that all enum values can be matched exhaustively."""
        results = []
        for cmd in EnumHandlerCommandType:
            match cmd:
                case EnumHandlerCommandType.EXECUTE:
                    results.append("execute")
                case EnumHandlerCommandType.VALIDATE:
                    results.append("validate")
                case EnumHandlerCommandType.DRY_RUN:
                    results.append("dry_run")
                case EnumHandlerCommandType.ROLLBACK:
                    results.append("rollback")
                case EnumHandlerCommandType.HEALTH_CHECK:
                    results.append("health_check")
                case EnumHandlerCommandType.DESCRIBE:
                    results.append("describe")
                case EnumHandlerCommandType.CONFIGURE:
                    results.append("configure")
                case EnumHandlerCommandType.RESET:
                    results.append("reset")
                case _:
                    # This should never be reached if all values are covered
                    EnumHandlerCommandType.assert_exhaustive(cmd)

        assert len(results) == 8
        assert set(results) == set(EnumHandlerCommandType.values())

    def test_all_values_are_unique(self):
        """Test that all enum values are unique (enforced by @unique decorator)."""
        values = [cmd.value for cmd in EnumHandlerCommandType]
        assert len(values) == len(set(values)), "Enum values must be unique"

    def test_all_names_are_unique(self):
        """Test that all enum names are unique."""
        names = [cmd.name for cmd in EnumHandlerCommandType]
        assert len(names) == len(set(names)), "Enum names must be unique"


@pytest.mark.unit
class TestEnumHandlerCommandTypeUseCases:
    """Test practical use cases for EnumHandlerCommandType."""

    def test_use_in_dict_key(self) -> None:
        """Test using enum as dictionary key."""
        command_handlers: dict[EnumHandlerCommandType, str] = {
            EnumHandlerCommandType.EXECUTE: "executed",
            EnumHandlerCommandType.VALIDATE: "validated",
        }
        assert EnumHandlerCommandType.EXECUTE in command_handlers
        assert command_handlers[EnumHandlerCommandType.EXECUTE] == "executed"

    def test_use_in_string_format(self):
        """Test using enum in string formatting."""
        cmd = EnumHandlerCommandType.EXECUTE
        formatted = f"Running command: {cmd}"
        assert formatted == "Running command: execute"

    def test_json_serialization_compatibility(self):
        """Test that enum values are JSON serializable."""
        import json

        cmd = EnumHandlerCommandType.EXECUTE
        # str(cmd) should give us the value for serialization
        serialized = json.dumps({"command": str(cmd)})
        assert '"command": "execute"' in serialized

    def test_comparison_with_string_literal(self):
        """Test direct comparison with string literals."""
        cmd = EnumHandlerCommandType.EXECUTE
        # Because it inherits from str, direct comparison works
        assert cmd == "execute"
        assert cmd == "execute"

    def test_use_in_set_operations(self):
        """Test using enums in set operations."""
        allowed_commands = {
            EnumHandlerCommandType.EXECUTE,
            EnumHandlerCommandType.VALIDATE,
            EnumHandlerCommandType.DRY_RUN,
        }
        assert EnumHandlerCommandType.EXECUTE in allowed_commands
        assert EnumHandlerCommandType.ROLLBACK not in allowed_commands

    def test_name_property(self):
        """Test the name property of enum members."""
        assert EnumHandlerCommandType.EXECUTE.name == "EXECUTE"
        assert EnumHandlerCommandType.VALIDATE.name == "VALIDATE"
        assert EnumHandlerCommandType.DRY_RUN.name == "DRY_RUN"
        assert EnumHandlerCommandType.ROLLBACK.name == "ROLLBACK"
        assert EnumHandlerCommandType.HEALTH_CHECK.name == "HEALTH_CHECK"
        assert EnumHandlerCommandType.DESCRIBE.name == "DESCRIBE"
        assert EnumHandlerCommandType.CONFIGURE.name == "CONFIGURE"
        assert EnumHandlerCommandType.RESET.name == "RESET"


@pytest.mark.unit
class TestEnumHandlerCommandTypeSerialization:
    """Test serialization and deserialization capabilities."""

    def test_yaml_serialization(self) -> None:
        """Test YAML serialization compatibility."""
        data = {"command": EnumHandlerCommandType.EXECUTE.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "command: execute" in yaml_str

        # Deserialize and compare
        loaded = yaml.safe_load(yaml_str)
        assert loaded["command"] == "execute"
        assert (
            EnumHandlerCommandType(loaded["command"]) == EnumHandlerCommandType.EXECUTE
        )

    def test_yaml_serialization_all_values(self) -> None:
        """Test YAML serialization for all command types."""
        for cmd in EnumHandlerCommandType:
            data = {"command": cmd.value}
            yaml_str = yaml.dump(data, default_flow_style=False)
            loaded = yaml.safe_load(yaml_str)
            assert EnumHandlerCommandType(loaded["command"]) == cmd

    def test_json_roundtrip_all_values(self) -> None:
        """Test JSON serialization roundtrip for all values."""
        for cmd in EnumHandlerCommandType:
            serialized = json.dumps(cmd.value)
            deserialized = json.loads(serialized)
            reconstructed = EnumHandlerCommandType(deserialized)
            assert reconstructed == cmd

    def test_pickle_serialization(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for cmd in EnumHandlerCommandType:
            pickled = pickle.dumps(cmd)
            unpickled = pickle.loads(pickled)
            assert unpickled == cmd
            assert unpickled is cmd  # Should be the same singleton object

    def test_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        cmd = EnumHandlerCommandType.EXECUTE

        # Shallow copy should return the same object
        shallow_copy = copy.copy(cmd)
        assert shallow_copy is cmd

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(cmd)
        assert deep_copy is cmd


@pytest.mark.unit
class TestEnumHandlerCommandTypeBehavior:
    """Test general enum behavior and properties."""

    def test_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        cmd_set = set(EnumHandlerCommandType)
        assert len(cmd_set) == 8

        # Test that same enum members have same hash
        assert hash(EnumHandlerCommandType.EXECUTE) == hash(
            EnumHandlerCommandType.EXECUTE
        )
        assert hash(EnumHandlerCommandType.VALIDATE) == hash(
            EnumHandlerCommandType.VALIDATE
        )

    def test_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumHandlerCommandType.EXECUTE) == (
            "<EnumHandlerCommandType.EXECUTE: 'execute'>"
        )
        assert repr(EnumHandlerCommandType.VALIDATE) == (
            "<EnumHandlerCommandType.VALIDATE: 'validate'>"
        )
        assert repr(EnumHandlerCommandType.DRY_RUN) == (
            "<EnumHandlerCommandType.DRY_RUN: 'dry_run'>"
        )
        assert repr(EnumHandlerCommandType.ROLLBACK) == (
            "<EnumHandlerCommandType.ROLLBACK: 'rollback'>"
        )
        assert repr(EnumHandlerCommandType.HEALTH_CHECK) == (
            "<EnumHandlerCommandType.HEALTH_CHECK: 'health_check'>"
        )
        assert repr(EnumHandlerCommandType.DESCRIBE) == (
            "<EnumHandlerCommandType.DESCRIBE: 'describe'>"
        )
        assert repr(EnumHandlerCommandType.CONFIGURE) == (
            "<EnumHandlerCommandType.CONFIGURE: 'configure'>"
        )
        assert repr(EnumHandlerCommandType.RESET) == (
            "<EnumHandlerCommandType.RESET: 'reset'>"
        )

    def test_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for cmd in EnumHandlerCommandType:
            assert bool(cmd) is True

    def test_ordering_behavior(self) -> None:
        """Test that enum members support ordering (inherits from str)."""
        # Since EnumHandlerCommandType(str, Enum), it supports string ordering
        result1 = EnumHandlerCommandType.EXECUTE < EnumHandlerCommandType.VALIDATE
        result2 = EnumHandlerCommandType.EXECUTE > EnumHandlerCommandType.VALIDATE

        # The results depend on string comparison of the values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)
        # "execute" < "validate" alphabetically
        assert EnumHandlerCommandType.EXECUTE < EnumHandlerCommandType.VALIDATE

    def test_string_operations(self) -> None:
        """Test that string operations work on enum values."""
        # Since it inherits from str, string methods should work
        assert EnumHandlerCommandType.EXECUTE.upper() == "EXECUTE"
        assert EnumHandlerCommandType.HEALTH_CHECK.startswith("health")
        assert "_" in EnumHandlerCommandType.DRY_RUN
        assert len(EnumHandlerCommandType.EXECUTE) == 7  # "execute" is 7 chars

    def test_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumHandlerCommandType.EXECUTE is EnumHandlerCommandType.EXECUTE

        # Different enum members should not be identical
        assert EnumHandlerCommandType.EXECUTE is not EnumHandlerCommandType.VALIDATE

        # Equality with strings should work
        assert EnumHandlerCommandType.EXECUTE == "execute"
        assert EnumHandlerCommandType.EXECUTE != "validate"


@pytest.mark.unit
class TestEnumHandlerCommandTypePydantic:
    """Test Pydantic integration."""

    def test_pydantic_model_with_enum(self) -> None:
        """Test using enum in Pydantic model."""

        class CommandConfig(BaseModel):
            command: EnumHandlerCommandType

        model = CommandConfig(command=EnumHandlerCommandType.EXECUTE)
        assert model.command == EnumHandlerCommandType.EXECUTE

    def test_pydantic_model_with_string_value(self) -> None:
        """Test Pydantic model accepts string values."""

        class CommandConfig(BaseModel):
            command: EnumHandlerCommandType

        model = CommandConfig(command="validate")
        assert model.command == EnumHandlerCommandType.VALIDATE

    def test_pydantic_model_invalid_value(self) -> None:
        """Test Pydantic model rejects invalid values."""

        class CommandConfig(BaseModel):
            command: EnumHandlerCommandType

        with pytest.raises(ValidationError):
            CommandConfig(command="invalid_command")

    def test_pydantic_model_serialization(self) -> None:
        """Test Pydantic model serialization."""

        class CommandConfig(BaseModel):
            command: EnumHandlerCommandType

        model = CommandConfig(command=EnumHandlerCommandType.DRY_RUN)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"command": "dry_run"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"command":"dry_run"}'

    def test_pydantic_model_deserialization(self) -> None:
        """Test Pydantic model deserialization."""

        class CommandConfig(BaseModel):
            command: EnumHandlerCommandType

        # From dict
        model = CommandConfig.model_validate({"command": "rollback"})
        assert model.command == EnumHandlerCommandType.ROLLBACK

        # From JSON
        model = CommandConfig.model_validate_json('{"command": "health_check"}')
        assert model.command == EnumHandlerCommandType.HEALTH_CHECK

    def test_pydantic_model_multiple_commands(self) -> None:
        """Test Pydantic model with list of commands."""

        class CommandSequence(BaseModel):
            commands: list[EnumHandlerCommandType]

        model = CommandSequence(
            commands=[
                EnumHandlerCommandType.VALIDATE,
                EnumHandlerCommandType.DRY_RUN,
                EnumHandlerCommandType.EXECUTE,
            ]
        )

        assert len(model.commands) == 3
        assert EnumHandlerCommandType.VALIDATE in model.commands
        assert EnumHandlerCommandType.DRY_RUN in model.commands
        assert EnumHandlerCommandType.EXECUTE in model.commands


@pytest.mark.unit
class TestEnumHandlerCommandTypeEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_invalid(self) -> None:
        """Test that None is invalid."""
        with pytest.raises((ValueError, TypeError)):
            EnumHandlerCommandType(None)

    def test_whitespace_invalid(self) -> None:
        """Test that whitespace-padded values are invalid."""
        with pytest.raises(ValueError):
            EnumHandlerCommandType(" execute")

        with pytest.raises(ValueError):
            EnumHandlerCommandType("execute ")

        with pytest.raises(ValueError):
            EnumHandlerCommandType(" execute ")

    def test_case_sensitivity(self) -> None:
        """Test that enum values are case-sensitive."""
        assert EnumHandlerCommandType.EXECUTE.value == "execute"
        assert EnumHandlerCommandType.EXECUTE.value != "EXECUTE"
        assert EnumHandlerCommandType.EXECUTE.value != "Execute"

    def test_enum_name_vs_value(self) -> None:
        """Test distinction between enum name and value."""
        cmd = EnumHandlerCommandType.HEALTH_CHECK
        assert cmd.name == "HEALTH_CHECK"
        assert cmd.value == "health_check"
        assert cmd.name != cmd.value


@pytest.mark.unit
class TestEnumHandlerCommandTypePropertyBased:
    """Property-based tests using hypothesis for EnumHandlerCommandType."""

    def test_all_commands_have_valid_string_representation(self) -> None:
        """Property: Every EnumHandlerCommandType value has a non-empty string representation."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerCommandType)))
        def check_string_representation(cmd: EnumHandlerCommandType) -> None:
            string_repr = str(cmd)
            assert isinstance(string_repr, str)
            assert len(string_repr) > 0
            assert string_repr == cmd.value

        check_string_representation()

    def test_all_commands_roundtrip_through_value(self) -> None:
        """Property: Every EnumHandlerCommandType can be reconstructed from its value."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerCommandType)))
        def check_roundtrip(cmd: EnumHandlerCommandType) -> None:
            value = cmd.value
            reconstructed = EnumHandlerCommandType(value)
            assert reconstructed == cmd
            assert reconstructed is cmd  # Same singleton instance

        check_roundtrip()

    def test_json_serialization_roundtrip(self) -> None:
        """Property: Every EnumHandlerCommandType survives JSON serialization roundtrip."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerCommandType)))
        def check_json_roundtrip(cmd: EnumHandlerCommandType) -> None:
            serialized = json.dumps(cmd.value)
            deserialized = json.loads(serialized)
            reconstructed = EnumHandlerCommandType(deserialized)
            assert reconstructed == cmd

        check_json_roundtrip()

    def test_pickle_serialization_preserves_identity(self) -> None:
        """Property: Pickle serialization preserves enum identity."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.sampled_from(list(EnumHandlerCommandType)))
        def check_pickle_identity(cmd: EnumHandlerCommandType) -> None:
            pickled = pickle.dumps(cmd)
            unpickled = pickle.loads(pickled)
            assert unpickled == cmd
            assert unpickled is cmd  # Same singleton

        check_pickle_identity()

    def test_values_classmethod_includes_all_members(self) -> None:
        """Property: values() classmethod includes all enum members."""
        from hypothesis import given
        from hypothesis import strategies as st

        all_values = EnumHandlerCommandType.values()

        @given(st.sampled_from(list(EnumHandlerCommandType)))
        def check_in_values(cmd: EnumHandlerCommandType) -> None:
            assert cmd.value in all_values

        check_in_values()


@pytest.mark.unit
class TestEnumHandlerCommandTypeDocstrings:
    """Test documentation and docstrings."""

    def test_enum_member_docstrings(self) -> None:
        """Test that enum members have docstrings."""
        assert EnumHandlerCommandType.EXECUTE.__doc__ is not None
        assert EnumHandlerCommandType.VALIDATE.__doc__ is not None
        assert EnumHandlerCommandType.DRY_RUN.__doc__ is not None
        assert EnumHandlerCommandType.ROLLBACK.__doc__ is not None
        assert EnumHandlerCommandType.HEALTH_CHECK.__doc__ is not None
        assert EnumHandlerCommandType.DESCRIBE.__doc__ is not None
        assert EnumHandlerCommandType.CONFIGURE.__doc__ is not None
        assert EnumHandlerCommandType.RESET.__doc__ is not None

    def test_docstring_content(self) -> None:
        """Test that docstrings describe the command purpose."""
        # EXECUTE should mention primary/main operation
        assert (
            "primary" in EnumHandlerCommandType.EXECUTE.__doc__.lower()
            or "execute" in EnumHandlerCommandType.EXECUTE.__doc__.lower()
        )

        # VALIDATE should mention validation
        assert "valid" in EnumHandlerCommandType.VALIDATE.__doc__.lower()

        # DRY_RUN should mention simulation/without effects
        assert (
            "simulat" in EnumHandlerCommandType.DRY_RUN.__doc__.lower()
            or "without" in EnumHandlerCommandType.DRY_RUN.__doc__.lower()
        )

        # ROLLBACK should mention undo/rollback
        assert (
            "rollback" in EnumHandlerCommandType.ROLLBACK.__doc__.lower()
            or "undo" in EnumHandlerCommandType.ROLLBACK.__doc__.lower()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
