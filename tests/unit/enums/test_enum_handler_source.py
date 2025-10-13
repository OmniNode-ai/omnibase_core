"""
Tests for EnumHandlerSource enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_handler_source import EnumHandlerSource


class TestEnumHandlerSource:
    """Test cases for EnumHandlerSource enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumHandlerSource.CORE == "core"
        assert EnumHandlerSource.RUNTIME == "runtime"
        assert EnumHandlerSource.NODE_LOCAL == "node-local"
        assert EnumHandlerSource.PLUGIN == "plugin"
        assert EnumHandlerSource.TEST == "test"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumHandlerSource, str)
        assert issubclass(EnumHandlerSource, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumHandlerSource.CORE) == "EnumHandlerSource.CORE"
        assert str(EnumHandlerSource.RUNTIME) == "EnumHandlerSource.RUNTIME"
        assert str(EnumHandlerSource.NODE_LOCAL) == "EnumHandlerSource.NODE_LOCAL"
        assert str(EnumHandlerSource.PLUGIN) == "EnumHandlerSource.PLUGIN"
        assert str(EnumHandlerSource.TEST) == "EnumHandlerSource.TEST"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumHandlerSource)
        assert len(values) == 5
        assert EnumHandlerSource.CORE in values
        assert EnumHandlerSource.RUNTIME in values
        assert EnumHandlerSource.NODE_LOCAL in values
        assert EnumHandlerSource.PLUGIN in values
        assert EnumHandlerSource.TEST in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "core" in EnumHandlerSource
        assert "runtime" in EnumHandlerSource
        assert "node-local" in EnumHandlerSource
        assert "plugin" in EnumHandlerSource
        assert "test" in EnumHandlerSource
        assert "invalid" not in EnumHandlerSource

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumHandlerSource.CORE == "core"
        assert EnumHandlerSource.RUNTIME == "runtime"
        assert EnumHandlerSource.NODE_LOCAL == "node-local"
        assert EnumHandlerSource.PLUGIN == "plugin"
        assert EnumHandlerSource.TEST == "test"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumHandlerSource.CORE.value == "core"
        assert EnumHandlerSource.RUNTIME.value == "runtime"
        assert EnumHandlerSource.NODE_LOCAL.value == "node-local"
        assert EnumHandlerSource.PLUGIN.value == "plugin"
        assert EnumHandlerSource.TEST.value == "test"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumHandlerSource("core") == EnumHandlerSource.CORE
        assert EnumHandlerSource("runtime") == EnumHandlerSource.RUNTIME
        assert EnumHandlerSource("node-local") == EnumHandlerSource.NODE_LOCAL
        assert EnumHandlerSource("plugin") == EnumHandlerSource.PLUGIN
        assert EnumHandlerSource("test") == EnumHandlerSource.TEST

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerSource("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [source.value for source in EnumHandlerSource]
        expected_values = ["core", "runtime", "node-local", "plugin", "test"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Canonical source types for file type handlers" in EnumHandlerSource.__doc__
        )

    def test_source_hierarchy(self):
        """Test that source types follow expected hierarchy."""
        # Core should be the highest priority source
        assert EnumHandlerSource.CORE in EnumHandlerSource
        # Runtime should be system-level
        assert EnumHandlerSource.RUNTIME in EnumHandlerSource
        # Node-local should be node-specific
        assert EnumHandlerSource.NODE_LOCAL in EnumHandlerSource
        # Plugin should be external
        assert EnumHandlerSource.PLUGIN in EnumHandlerSource
        # Test should be for testing
        assert EnumHandlerSource.TEST in EnumHandlerSource
