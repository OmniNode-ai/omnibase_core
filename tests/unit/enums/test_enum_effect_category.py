"""Tests for EnumEffectCategory enum.

Part of OMN-1147: Effect Classification System test suite.
"""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_effect_category import EnumEffectCategory


@pytest.mark.unit
class TestEnumEffectCategory:
    """Test cases for EnumEffectCategory enum."""

    def test_all_categories_exist(self) -> None:
        """Verify all expected effect categories are defined."""
        assert EnumEffectCategory.NETWORK == "network"
        assert EnumEffectCategory.TIME == "time"
        assert EnumEffectCategory.RANDOM == "random"
        assert EnumEffectCategory.EXTERNAL_STATE == "external_state"
        assert EnumEffectCategory.FILESYSTEM == "filesystem"
        assert EnumEffectCategory.DATABASE == "database"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEffectCategory, str)
        assert issubclass(EnumEffectCategory, Enum)

    def test_string_serialization_via_str_value_helper(self) -> None:
        """Test StrValueHelper provides correct string representation."""
        assert str(EnumEffectCategory.NETWORK) == "network"
        assert str(EnumEffectCategory.TIME) == "time"
        assert str(EnumEffectCategory.RANDOM) == "random"
        assert str(EnumEffectCategory.EXTERNAL_STATE) == "external_state"
        assert str(EnumEffectCategory.FILESYSTEM) == "filesystem"
        assert str(EnumEffectCategory.DATABASE) == "database"

    def test_enum_as_dict_keys(self) -> None:
        """Test enum values can be used as dictionary keys."""
        policy_map: dict[EnumEffectCategory, str] = {
            EnumEffectCategory.NETWORK: "allow",
            EnumEffectCategory.TIME: "mock",
            EnumEffectCategory.DATABASE: "block",
        }

        assert policy_map[EnumEffectCategory.NETWORK] == "allow"
        assert policy_map[EnumEffectCategory.TIME] == "mock"
        assert policy_map[EnumEffectCategory.DATABASE] == "block"

    def test_iteration_over_all_values(self) -> None:
        """Test that enum can be iterated over all values."""
        values = list(EnumEffectCategory)
        assert len(values) == 6
        assert EnumEffectCategory.NETWORK in values
        assert EnumEffectCategory.TIME in values
        assert EnumEffectCategory.RANDOM in values
        assert EnumEffectCategory.EXTERNAL_STATE in values
        assert EnumEffectCategory.FILESYSTEM in values
        assert EnumEffectCategory.DATABASE in values

    def test_all_expected_values_present(self) -> None:
        """Test complete set of expected values are present."""
        expected_values = {
            "network",
            "time",
            "random",
            "external_state",
            "filesystem",
            "database",
        }
        actual_values = {member.value for member in EnumEffectCategory}
        assert actual_values == expected_values

    def test_enum_membership(self) -> None:
        """Test enum membership operations."""
        assert "network" in EnumEffectCategory
        assert "time" in EnumEffectCategory
        assert "invalid_category" not in EnumEffectCategory

    def test_enum_comparison_and_equality(self) -> None:
        """Test enum comparison operations."""
        cat1 = EnumEffectCategory.NETWORK
        cat2 = EnumEffectCategory.DATABASE

        assert cat1 != cat2
        assert cat1 == "network"
        assert cat2 == "database"
        assert cat1 == EnumEffectCategory.NETWORK

    def test_enum_value_attribute(self) -> None:
        """Test enum value attribute access."""
        assert EnumEffectCategory.NETWORK.value == "network"
        assert EnumEffectCategory.FILESYSTEM.value == "filesystem"

    def test_json_serialization(self) -> None:
        """Test that enum values can be JSON serialized."""
        cat = EnumEffectCategory.DATABASE
        json_str = json.dumps(cat)
        assert json_str == '"database"'

    def test_enum_creation_from_string(self) -> None:
        """Test that enum can be created from string values."""
        cat = EnumEffectCategory("network")
        assert cat == EnumEffectCategory.NETWORK

    def test_invalid_value_raises_error(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEffectCategory("invalid_category")

    def test_is_io_category_method(self) -> None:
        """Test is_io_category classmethod identifies I/O categories."""
        assert EnumEffectCategory.is_io_category(EnumEffectCategory.NETWORK) is True
        assert EnumEffectCategory.is_io_category(EnumEffectCategory.FILESYSTEM) is True
        assert EnumEffectCategory.is_io_category(EnumEffectCategory.DATABASE) is True
        assert EnumEffectCategory.is_io_category(EnumEffectCategory.TIME) is False
        assert EnumEffectCategory.is_io_category(EnumEffectCategory.RANDOM) is False
        assert (
            EnumEffectCategory.is_io_category(EnumEffectCategory.EXTERNAL_STATE)
            is False
        )

    def test_is_temporal_category_method(self) -> None:
        """Test is_temporal_category classmethod identifies temporal categories."""
        assert EnumEffectCategory.is_temporal_category(EnumEffectCategory.TIME) is True
        assert (
            EnumEffectCategory.is_temporal_category(EnumEffectCategory.RANDOM) is True
        )
        assert (
            EnumEffectCategory.is_temporal_category(EnumEffectCategory.NETWORK) is False
        )
        assert (
            EnumEffectCategory.is_temporal_category(EnumEffectCategory.FILESYSTEM)
            is False
        )
        assert (
            EnumEffectCategory.is_temporal_category(EnumEffectCategory.DATABASE)
            is False
        )
        assert (
            EnumEffectCategory.is_temporal_category(EnumEffectCategory.EXTERNAL_STATE)
            is False
        )

    def test_enum_uniqueness(self) -> None:
        """Test that enum values are unique (enforced by @unique decorator)."""
        values = [member.value for member in EnumEffectCategory]
        assert len(values) == len(set(values)), "Enum values should be unique"

    def test_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        cat = EnumEffectCategory.NETWORK
        assert isinstance(cat, str)
        assert cat.upper() == "NETWORK"
        assert cat.startswith("net")
        assert len(cat) == 7
