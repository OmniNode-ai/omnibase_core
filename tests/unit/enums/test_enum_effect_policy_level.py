# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumEffectPolicyLevel enum.

Part of OMN-1147: Effect Classification System test suite.
"""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel


@pytest.mark.unit
class TestEnumEffectPolicyLevel:
    """Test cases for EnumEffectPolicyLevel enum."""

    def test_all_policy_levels_exist(self) -> None:
        """Verify all expected policy levels are defined."""
        assert EnumEffectPolicyLevel.STRICT == "strict"
        assert EnumEffectPolicyLevel.WARN == "warn"
        assert EnumEffectPolicyLevel.PERMISSIVE == "permissive"
        assert EnumEffectPolicyLevel.MOCKED == "mocked"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEffectPolicyLevel, str)
        assert issubclass(EnumEffectPolicyLevel, Enum)

    def test_string_serialization_via_str_value_helper(self) -> None:
        """Test StrValueHelper provides correct string representation."""
        assert str(EnumEffectPolicyLevel.STRICT) == "strict"
        assert str(EnumEffectPolicyLevel.WARN) == "warn"
        assert str(EnumEffectPolicyLevel.PERMISSIVE) == "permissive"
        assert str(EnumEffectPolicyLevel.MOCKED) == "mocked"

    def test_comparison_and_equality(self) -> None:
        """Test enum comparison and equality operations."""
        level1 = EnumEffectPolicyLevel.STRICT
        level2 = EnumEffectPolicyLevel.WARN

        assert level1 != level2
        assert level1 == "strict"
        assert level2 == "warn"
        assert level1 == EnumEffectPolicyLevel.STRICT

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        values = list(EnumEffectPolicyLevel)
        assert len(values) == 4
        assert EnumEffectPolicyLevel.STRICT in values
        assert EnumEffectPolicyLevel.WARN in values
        assert EnumEffectPolicyLevel.PERMISSIVE in values
        assert EnumEffectPolicyLevel.MOCKED in values

    def test_all_expected_values_present(self) -> None:
        """Test complete set of expected values."""
        expected_values = {"strict", "warn", "permissive", "mocked"}
        actual_values = {member.value for member in EnumEffectPolicyLevel}
        assert actual_values == expected_values

    def test_enum_membership(self) -> None:
        """Test enum membership operations."""
        assert "strict" in EnumEffectPolicyLevel
        assert "warn" in EnumEffectPolicyLevel
        assert "invalid_level" not in EnumEffectPolicyLevel

    def test_enum_as_dict_keys(self) -> None:
        """Test enum values can be used as dictionary keys."""
        descriptions: dict[EnumEffectPolicyLevel, str] = {
            EnumEffectPolicyLevel.STRICT: "Block all non-deterministic effects",
            EnumEffectPolicyLevel.WARN: "Log warnings but allow execution",
            EnumEffectPolicyLevel.PERMISSIVE: "Allow with audit trail",
            EnumEffectPolicyLevel.MOCKED: "Replace with deterministic mocks",
        }

        assert "Block" in descriptions[EnumEffectPolicyLevel.STRICT]
        assert "warnings" in descriptions[EnumEffectPolicyLevel.WARN]

    def test_json_serialization(self) -> None:
        """Test that enum values can be JSON serialized."""
        level = EnumEffectPolicyLevel.MOCKED
        json_str = json.dumps(level)
        assert json_str == '"mocked"'

    def test_enum_creation_from_string(self) -> None:
        """Test that enum can be created from string values."""
        level = EnumEffectPolicyLevel("strict")
        assert level == EnumEffectPolicyLevel.STRICT

    def test_invalid_value_raises_error(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEffectPolicyLevel("invalid_level")

    def test_blocks_execution_method(self) -> None:
        """Test blocks_execution classmethod identifies blocking policies."""
        assert (
            EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.STRICT) is True
        )
        assert (
            EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.WARN) is False
        )
        assert (
            EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.PERMISSIVE)
            is False
        )
        assert (
            EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.MOCKED)
            is False
        )

    def test_requires_mock_method(self) -> None:
        """Test requires_mock classmethod identifies mocking policies."""
        assert EnumEffectPolicyLevel.requires_mock(EnumEffectPolicyLevel.MOCKED) is True
        assert (
            EnumEffectPolicyLevel.requires_mock(EnumEffectPolicyLevel.STRICT) is False
        )
        assert EnumEffectPolicyLevel.requires_mock(EnumEffectPolicyLevel.WARN) is False
        assert (
            EnumEffectPolicyLevel.requires_mock(EnumEffectPolicyLevel.PERMISSIVE)
            is False
        )

    def test_enum_uniqueness(self) -> None:
        """Test that enum values are unique (enforced by @unique decorator)."""
        values = [member.value for member in EnumEffectPolicyLevel]
        assert len(values) == len(set(values)), "Enum values should be unique"

    def test_value_attribute(self) -> None:
        """Test enum value attribute access."""
        assert EnumEffectPolicyLevel.STRICT.value == "strict"
        assert EnumEffectPolicyLevel.WARN.value == "warn"
        assert EnumEffectPolicyLevel.PERMISSIVE.value == "permissive"
        assert EnumEffectPolicyLevel.MOCKED.value == "mocked"

    def test_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        level = EnumEffectPolicyLevel.PERMISSIVE
        assert isinstance(level, str)
        assert level.upper() == "PERMISSIVE"
        assert len(level) == 10

    def test_policy_ordering_semantics(self) -> None:
        """Test that policies can be compared for ordering if needed.

        While not strictly required, this tests that the enum values
        have consistent hash behavior for use in sets/dicts.
        """
        policies = {
            EnumEffectPolicyLevel.STRICT,
            EnumEffectPolicyLevel.WARN,
            EnumEffectPolicyLevel.PERMISSIVE,
            EnumEffectPolicyLevel.MOCKED,
        }
        assert len(policies) == 4
        assert EnumEffectPolicyLevel.STRICT in policies
