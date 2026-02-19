# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumEvidenceTier."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.pattern_learning.enum_evidence_tier import EnumEvidenceTier


@pytest.mark.unit
class TestEnumEvidenceTier:
    """Test suite for EnumEvidenceTier."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumEvidenceTier.UNMEASURED == "unmeasured"
        assert EnumEvidenceTier.OBSERVED == "observed"
        assert EnumEvidenceTier.MEASURED == "measured"
        assert EnumEvidenceTier.VERIFIED == "verified"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEvidenceTier, str)
        assert issubclass(EnumEvidenceTier, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        tier = EnumEvidenceTier.MEASURED
        assert isinstance(tier, str)
        assert tier == "measured"

    def test_enum_str_method(self):
        """Test __str__ method returns value (via StrValueHelper)."""
        assert str(EnumEvidenceTier.UNMEASURED) == "unmeasured"
        assert str(EnumEvidenceTier.OBSERVED) == "observed"
        assert str(EnumEvidenceTier.MEASURED) == "measured"
        assert str(EnumEvidenceTier.VERIFIED) == "verified"

    def test_enum_member_count(self):
        """Test that exactly 4 members exist."""
        values = list(EnumEvidenceTier)
        assert len(values) == 4

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumEvidenceTier)
        assert EnumEvidenceTier.UNMEASURED in values
        assert EnumEvidenceTier.OBSERVED in values
        assert EnumEvidenceTier.MEASURED in values
        assert EnumEvidenceTier.VERIFIED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumEvidenceTier.VERIFIED in EnumEvidenceTier
        assert "verified" in [e.value for e in EnumEvidenceTier]

    def test_enum_equality(self):
        """Test enum equality comparison."""
        tier1 = EnumEvidenceTier.MEASURED
        tier2 = EnumEvidenceTier.MEASURED
        tier3 = EnumEvidenceTier.OBSERVED

        assert tier1 == tier2
        assert tier1 != tier3
        assert tier1 == "measured"

    def test_enum_serialization(self):
        """Test enum serialization."""
        tier = EnumEvidenceTier.VERIFIED
        serialized = tier.value
        assert serialized == "verified"
        json_str = json.dumps(tier)
        assert json_str == '"verified"'

    def test_enum_deserialization(self):
        """Test enum deserialization from string value."""
        tier = EnumEvidenceTier("observed")
        assert tier == EnumEvidenceTier.OBSERVED

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEvidenceTier("invalid_tier")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"unmeasured", "observed", "measured", "verified"}
        actual_values = {e.value for e in EnumEvidenceTier}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumEvidenceTier.__doc__ is not None
        assert "evidence" in EnumEvidenceTier.__doc__.lower()

    def test_get_numeric_value(self):
        """Test get_numeric_value returns correct weights."""
        assert EnumEvidenceTier.UNMEASURED.get_numeric_value() == 0
        assert EnumEvidenceTier.OBSERVED.get_numeric_value() == 10
        assert EnumEvidenceTier.MEASURED.get_numeric_value() == 20
        assert EnumEvidenceTier.VERIFIED.get_numeric_value() == 30

    def test_numeric_value_ordering(self):
        """Test that numeric values maintain proper ordering."""
        values = [
            EnumEvidenceTier.UNMEASURED.get_numeric_value(),
            EnumEvidenceTier.OBSERVED.get_numeric_value(),
            EnumEvidenceTier.MEASURED.get_numeric_value(),
            EnumEvidenceTier.VERIFIED.get_numeric_value(),
        ]
        assert values == sorted(values)

    def test_numeric_values_strictly_increasing(self):
        """Test that each tier has a strictly higher weight than the previous."""
        tiers = [
            EnumEvidenceTier.UNMEASURED,
            EnumEvidenceTier.OBSERVED,
            EnumEvidenceTier.MEASURED,
            EnumEvidenceTier.VERIFIED,
        ]
        for i in range(len(tiers) - 1):
            assert tiers[i].get_numeric_value() < tiers[i + 1].get_numeric_value()

    def test_tier_less_than(self):
        """Test less than comparison matches spec: UNMEASURED < OBSERVED < MEASURED < VERIFIED."""
        assert EnumEvidenceTier.UNMEASURED < EnumEvidenceTier.OBSERVED
        assert EnumEvidenceTier.OBSERVED < EnumEvidenceTier.MEASURED
        assert EnumEvidenceTier.MEASURED < EnumEvidenceTier.VERIFIED

    def test_tier_less_than_or_equal(self):
        """Test less than or equal comparison."""
        assert EnumEvidenceTier.UNMEASURED <= EnumEvidenceTier.OBSERVED
        assert EnumEvidenceTier.OBSERVED <= EnumEvidenceTier.OBSERVED
        assert EnumEvidenceTier.MEASURED <= EnumEvidenceTier.VERIFIED

    def test_tier_greater_than(self):
        """Test greater than comparison."""
        assert EnumEvidenceTier.VERIFIED > EnumEvidenceTier.MEASURED
        assert EnumEvidenceTier.MEASURED > EnumEvidenceTier.OBSERVED
        assert EnumEvidenceTier.OBSERVED > EnumEvidenceTier.UNMEASURED

    def test_tier_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        assert EnumEvidenceTier.VERIFIED >= EnumEvidenceTier.MEASURED
        assert EnumEvidenceTier.MEASURED >= EnumEvidenceTier.MEASURED
        assert EnumEvidenceTier.OBSERVED >= EnumEvidenceTier.UNMEASURED

    def test_tier_sorting(self):
        """Test that tiers can be sorted correctly."""
        tiers = [
            EnumEvidenceTier.MEASURED,
            EnumEvidenceTier.UNMEASURED,
            EnumEvidenceTier.VERIFIED,
            EnumEvidenceTier.OBSERVED,
        ]
        sorted_tiers = sorted(tiers)
        expected = [
            EnumEvidenceTier.UNMEASURED,
            EnumEvidenceTier.OBSERVED,
            EnumEvidenceTier.MEASURED,
            EnumEvidenceTier.VERIFIED,
        ]
        assert sorted_tiers == expected

    def test_tier_comparison_completeness(self):
        """Test that all comparison operators work correctly."""
        low = EnumEvidenceTier.UNMEASURED
        high = EnumEvidenceTier.VERIFIED

        assert low < high
        assert low <= high
        assert high > low
        assert high >= low
        assert not (low > high)
        assert not (high < low)

    def test_tier_self_equality_comparisons(self):
        """Test self-comparisons for all tiers."""
        for tier in EnumEvidenceTier:
            same_tier = EnumEvidenceTier(tier.value)
            assert tier <= same_tier
            assert tier >= same_tier
            assert not (tier < same_tier)
            assert not (tier > same_tier)

    def test_tier_transitive_ordering(self):
        """Test transitive ordering: if A < B and B < C then A < C."""
        assert EnumEvidenceTier.UNMEASURED < EnumEvidenceTier.OBSERVED
        assert EnumEvidenceTier.OBSERVED < EnumEvidenceTier.VERIFIED
        assert EnumEvidenceTier.UNMEASURED < EnumEvidenceTier.VERIFIED

    def test_import_from_package(self):
        """Test that enum can be imported from the pattern_learning package."""
        from omnibase_core.enums.pattern_learning import (
            EnumEvidenceTier as EvidenceTierAlias,
        )

        assert EvidenceTierAlias.UNMEASURED == "unmeasured"

    def test_import_from_top_level_enums(self):
        """Test that enum can be imported from the top-level enums package."""
        from omnibase_core.enums import EnumEvidenceTier as EvidenceTierAlias

        assert EvidenceTierAlias.VERIFIED == "verified"

    def test_uniqueness(self):
        """Test that all values are unique (enforced by @unique decorator)."""
        values = [e.value for e in EnumEvidenceTier]
        assert len(values) == len(set(values))

    def test_comparison_against_raw_string(self):
        """Test that comparing against raw strings uses weight ordering, not lexicographic."""
        # "measured" < "observed" lexicographically, but MEASURED > OBSERVED by weight
        assert EnumEvidenceTier.MEASURED > "observed"
        assert EnumEvidenceTier.MEASURED >= "observed"
        assert not (EnumEvidenceTier.MEASURED < "observed")
        assert not (EnumEvidenceTier.MEASURED <= "observed")

        # String coercion preserves correct tier ordering
        assert EnumEvidenceTier.UNMEASURED < "verified"
        assert EnumEvidenceTier.VERIFIED > "unmeasured"
        assert EnumEvidenceTier.OBSERVED >= "observed"
        assert EnumEvidenceTier.OBSERVED <= "observed"

    def test_comparison_against_invalid_string_returns_not_implemented(self):
        """Test that comparing against an invalid string returns NotImplemented."""
        result = EnumEvidenceTier.MEASURED.__lt__("not_a_tier")
        assert result is NotImplemented

    def test_comparison_against_non_string_returns_not_implemented(self):
        """Test that comparing against a non-string type returns NotImplemented."""
        result = EnumEvidenceTier.MEASURED.__lt__(42)
        assert result is NotImplemented
