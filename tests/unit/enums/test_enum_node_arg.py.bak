"""Tests for enum_node_arg.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_node_arg import EnumNodeArg


class TestEnumNodeArg:
    """Test cases for EnumNodeArg"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumNodeArg.ARGS == "args"
        assert EnumNodeArg.KWARGS == "kwargs"
        assert EnumNodeArg.INPUT_STATE == "input_state"
        assert EnumNodeArg.CONFIG == "config"
        assert EnumNodeArg.BOOTSTRAP == "--bootstrap"
        assert EnumNodeArg.HEALTH_CHECK == "--health-check"
        assert EnumNodeArg.INTROSPECT == "--introspect"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumNodeArg, str)
        assert issubclass(EnumNodeArg, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumNodeArg.ARGS == "args"
        assert EnumNodeArg.KWARGS == "kwargs"
        assert EnumNodeArg.BOOTSTRAP == "--bootstrap"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumNodeArg)
        assert len(values) == 7
        assert EnumNodeArg.ARGS in values
        assert EnumNodeArg.INTROSPECT in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumNodeArg.ARGS in EnumNodeArg
        assert "args" in EnumNodeArg
        assert "invalid_value" not in EnumNodeArg

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumNodeArg.ARGS == EnumNodeArg.ARGS
        assert EnumNodeArg.KWARGS != EnumNodeArg.ARGS
        assert EnumNodeArg.ARGS == "args"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumNodeArg.ARGS.value == "args"
        assert EnumNodeArg.KWARGS.value == "kwargs"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumNodeArg("args") == EnumNodeArg.ARGS
        assert EnumNodeArg("kwargs") == EnumNodeArg.KWARGS

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumNodeArg("invalid_value")

        with pytest.raises(ValueError):
            EnumNodeArg("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "args",
            "kwargs",
            "input_state",
            "config",
            "--bootstrap",
            "--health-check",
            "--introspect",
        }
        actual_values = {member.value for member in EnumNodeArg}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Canonical enum for node argument types" in EnumNodeArg.__doc__

    def test_enum_argument_types(self):
        """Test specific argument types"""
        # Standard argument types
        assert EnumNodeArg.ARGS.value == "args"
        assert EnumNodeArg.KWARGS.value == "kwargs"
        assert EnumNodeArg.INPUT_STATE.value == "input_state"
        assert EnumNodeArg.CONFIG.value == "config"

        # Command line argument types
        assert EnumNodeArg.BOOTSTRAP.value == "--bootstrap"
        assert EnumNodeArg.HEALTH_CHECK.value == "--health-check"
        assert EnumNodeArg.INTROSPECT.value == "--introspect"

    def test_enum_argument_categories(self):
        """Test argument categories"""
        # Standard argument types
        standard_args = {
            EnumNodeArg.ARGS,
            EnumNodeArg.KWARGS,
            EnumNodeArg.INPUT_STATE,
            EnumNodeArg.CONFIG,
        }

        # Command line argument types
        cli_args = {
            EnumNodeArg.BOOTSTRAP,
            EnumNodeArg.HEALTH_CHECK,
            EnumNodeArg.INTROSPECT,
        }

        all_args = set(EnumNodeArg)
        assert standard_args.union(cli_args) == all_args

    def test_enum_cli_arguments(self):
        """Test CLI argument types"""
        # Bootstrap argument
        assert EnumNodeArg.BOOTSTRAP.value == "--bootstrap"

        # Health check argument
        assert EnumNodeArg.HEALTH_CHECK.value == "--health-check"

        # Introspect argument
        assert EnumNodeArg.INTROSPECT.value == "--introspect"

    def test_enum_standard_arguments(self):
        """Test standard argument types"""
        # Args argument
        assert EnumNodeArg.ARGS.value == "args"

        # Kwargs argument
        assert EnumNodeArg.KWARGS.value == "kwargs"

        # Input state argument
        assert EnumNodeArg.INPUT_STATE.value == "input_state"

        # Config argument
        assert EnumNodeArg.CONFIG.value == "config"
