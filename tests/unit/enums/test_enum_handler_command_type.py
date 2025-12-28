# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for EnumHandlerCommandType enum.
"""

from enum import Enum
from typing import Never

import pytest

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
        assert EnumHandlerCommandType("health_check") == EnumHandlerCommandType.HEALTH_CHECK
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

    def test_assert_exhaustive_raises_assertion_error(self):
        """Test that assert_exhaustive raises AssertionError."""
        # Create a mock value that would represent an unhandled case
        # In practice, this should never be called with a valid enum value
        # We test it with a string that's not a valid enum member
        with pytest.raises(AssertionError) as exc_info:
            # type: ignore is needed because this is intentionally passing an invalid type
            EnumHandlerCommandType.assert_exhaustive("unhandled_value")  # type: ignore[arg-type]
        assert "Unhandled enum value: unhandled_value" in str(exc_info.value)

    def test_assert_exhaustive_message_format(self):
        """Test that assert_exhaustive error message is properly formatted."""
        with pytest.raises(AssertionError) as exc_info:
            EnumHandlerCommandType.assert_exhaustive(42)  # type: ignore[arg-type]
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

    def test_use_in_dict_key(self):
        """Test using enum as dictionary key."""
        command_handlers = {
            EnumHandlerCommandType.EXECUTE: lambda: "executed",
            EnumHandlerCommandType.VALIDATE: lambda: "validated",
        }
        assert EnumHandlerCommandType.EXECUTE in command_handlers
        assert command_handlers[EnumHandlerCommandType.EXECUTE]() == "executed"

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
        assert "execute" == cmd

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
