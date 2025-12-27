# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for EnumLikelihood enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_likelihood import EnumLikelihood


@pytest.mark.unit
class TestEnumLikelihood:
    """Test cases for EnumLikelihood enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumLikelihood.VERY_LOW.value == "very_low"
        assert EnumLikelihood.LOW.value == "low"
        assert EnumLikelihood.MEDIUM.value == "medium"
        assert EnumLikelihood.HIGH.value == "high"
        assert EnumLikelihood.VERY_HIGH.value == "very_high"
        assert EnumLikelihood.UNKNOWN.value == "unknown"
        assert EnumLikelihood.CERTAIN.value == "certain"
        assert EnumLikelihood.IMPOSSIBLE.value == "impossible"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumLikelihood, str)
        assert issubclass(EnumLikelihood, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        likelihood = EnumLikelihood.VERY_LOW
        assert isinstance(likelihood, str)
        assert likelihood.value == "very_low"
        assert len(likelihood.value) == 8
        assert likelihood.value.startswith("very")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumLikelihood)
        assert len(values) == 8
        assert EnumLikelihood.VERY_LOW in values
        assert EnumLikelihood.CERTAIN in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "very_low" in EnumLikelihood
        assert "invalid_likelihood" not in EnumLikelihood

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        like1 = EnumLikelihood.LOW
        like2 = EnumLikelihood.HIGH

        assert like1 != like2
        assert like1.value == "low"
        assert like2.value == "high"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        likelihood = EnumLikelihood.MEDIUM
        serialized = likelihood.value
        assert serialized == "medium"

        # Test JSON serialization
        import json

        json_str = json.dumps(likelihood)
        assert json_str == '"medium"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        likelihood = EnumLikelihood("very_high")
        assert likelihood == EnumLikelihood.VERY_HIGH

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumLikelihood("invalid_likelihood")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "very_low",
            "low",
            "medium",
            "high",
            "very_high",
            "unknown",
            "certain",
            "impossible",
        }

        actual_values = {member.value for member in EnumLikelihood}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        doc = EnumLikelihood.__doc__
        assert doc is not None
        assert "likelihood" in doc.lower()

    def test_enum_str_method(self):
        """Test the __str__ method."""
        likelihood = EnumLikelihood.LOW
        assert str(likelihood) == "low"
        assert str(EnumLikelihood.VERY_HIGH) == "very_high"


@pytest.mark.unit
class TestEnumLikelihoodGetNumericRange:
    """Test cases for get_numeric_range class method."""

    def test_get_numeric_range_impossible(self):
        """Test numeric range for IMPOSSIBLE."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.IMPOSSIBLE)
        assert min_prob == 0.0
        assert max_prob == 0.0

    def test_get_numeric_range_very_low(self):
        """Test numeric range for VERY_LOW."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.VERY_LOW)
        assert min_prob == 0.0
        assert max_prob == 0.1

    def test_get_numeric_range_low(self):
        """Test numeric range for LOW."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.LOW)
        assert min_prob == 0.1
        assert max_prob == 0.3

    def test_get_numeric_range_medium(self):
        """Test numeric range for MEDIUM."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.MEDIUM)
        assert min_prob == 0.3
        assert max_prob == 0.6

    def test_get_numeric_range_high(self):
        """Test numeric range for HIGH."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.HIGH)
        assert min_prob == 0.6
        assert max_prob == 0.85

    def test_get_numeric_range_very_high(self):
        """Test numeric range for VERY_HIGH."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.VERY_HIGH)
        assert min_prob == 0.85
        assert max_prob == 1.0

    def test_get_numeric_range_certain(self):
        """Test numeric range for CERTAIN."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.CERTAIN)
        assert min_prob == 1.0
        assert max_prob == 1.0

    def test_get_numeric_range_unknown(self):
        """Test numeric range for UNKNOWN (full range)."""
        min_prob, max_prob = EnumLikelihood.get_numeric_range(EnumLikelihood.UNKNOWN)
        assert min_prob == 0.0
        assert max_prob == 1.0


@pytest.mark.unit
class TestEnumLikelihoodFromProbability:
    """Test cases for from_probability class method."""

    def test_from_probability_impossible(self):
        """Test that 0.0 returns IMPOSSIBLE."""
        assert EnumLikelihood.from_probability(0.0) == EnumLikelihood.IMPOSSIBLE

    def test_from_probability_very_low(self):
        """Test that values 0 < p < 0.1 return VERY_LOW."""
        assert EnumLikelihood.from_probability(0.01) == EnumLikelihood.VERY_LOW
        assert EnumLikelihood.from_probability(0.05) == EnumLikelihood.VERY_LOW
        assert EnumLikelihood.from_probability(0.09) == EnumLikelihood.VERY_LOW
        assert EnumLikelihood.from_probability(0.09999) == EnumLikelihood.VERY_LOW

    def test_from_probability_low(self):
        """Test that values 0.1 <= p < 0.3 return LOW."""
        assert EnumLikelihood.from_probability(0.1) == EnumLikelihood.LOW
        assert EnumLikelihood.from_probability(0.15) == EnumLikelihood.LOW
        assert EnumLikelihood.from_probability(0.2) == EnumLikelihood.LOW
        assert EnumLikelihood.from_probability(0.29999) == EnumLikelihood.LOW

    def test_from_probability_medium(self):
        """Test that values 0.3 <= p < 0.6 return MEDIUM."""
        assert EnumLikelihood.from_probability(0.3) == EnumLikelihood.MEDIUM
        assert EnumLikelihood.from_probability(0.45) == EnumLikelihood.MEDIUM
        assert EnumLikelihood.from_probability(0.59999) == EnumLikelihood.MEDIUM

    def test_from_probability_high(self):
        """Test that values 0.6 <= p < 0.85 return HIGH."""
        assert EnumLikelihood.from_probability(0.6) == EnumLikelihood.HIGH
        assert EnumLikelihood.from_probability(0.7) == EnumLikelihood.HIGH
        assert EnumLikelihood.from_probability(0.84999) == EnumLikelihood.HIGH

    def test_from_probability_very_high(self):
        """Test that values 0.85 <= p < 1.0 return VERY_HIGH."""
        assert EnumLikelihood.from_probability(0.85) == EnumLikelihood.VERY_HIGH
        assert EnumLikelihood.from_probability(0.9) == EnumLikelihood.VERY_HIGH
        assert EnumLikelihood.from_probability(0.99) == EnumLikelihood.VERY_HIGH
        assert EnumLikelihood.from_probability(0.99999) == EnumLikelihood.VERY_HIGH

    def test_from_probability_certain(self):
        """Test that 1.0 returns CERTAIN."""
        assert EnumLikelihood.from_probability(1.0) == EnumLikelihood.CERTAIN

    def test_from_probability_invalid_range(self):
        """Test that out-of-range probabilities raise ValueError."""
        with pytest.raises(
            ValueError, match=r"probability must be between 0\.0 and 1\.0"
        ):
            EnumLikelihood.from_probability(-0.5)
        with pytest.raises(
            ValueError, match=r"probability must be between 0\.0 and 1\.0"
        ):
            EnumLikelihood.from_probability(1.5)
        with pytest.raises(
            ValueError, match=r"probability must be between 0\.0 and 1\.0"
        ):
            EnumLikelihood.from_probability(-1.0)
        with pytest.raises(
            ValueError, match=r"probability must be between 0\.0 and 1\.0"
        ):
            EnumLikelihood.from_probability(2.0)

    def test_from_probability_boundary_at_0_1(self):
        """Test boundary behavior at 0.1 (VERY_LOW/LOW threshold).

        This is a critical edge case:
        - Values < 0.1 return VERY_LOW
        - Values >= 0.1 return LOW (inclusive lower bound)
        """
        assert EnumLikelihood.from_probability(0.09999) == EnumLikelihood.VERY_LOW
        assert EnumLikelihood.from_probability(0.1) == EnumLikelihood.LOW
        assert EnumLikelihood.from_probability(0.10001) == EnumLikelihood.LOW

    def test_from_probability_boundary_at_0_3(self):
        """Test boundary behavior at 0.3 (LOW/MEDIUM threshold)."""
        assert EnumLikelihood.from_probability(0.29999) == EnumLikelihood.LOW
        assert EnumLikelihood.from_probability(0.3) == EnumLikelihood.MEDIUM
        assert EnumLikelihood.from_probability(0.30001) == EnumLikelihood.MEDIUM

    def test_from_probability_boundary_at_0_6(self):
        """Test boundary behavior at 0.6 (MEDIUM/HIGH threshold)."""
        assert EnumLikelihood.from_probability(0.59999) == EnumLikelihood.MEDIUM
        assert EnumLikelihood.from_probability(0.6) == EnumLikelihood.HIGH
        assert EnumLikelihood.from_probability(0.60001) == EnumLikelihood.HIGH

    def test_from_probability_boundary_at_0_85(self):
        """Test boundary behavior at 0.85 (HIGH/VERY_HIGH threshold)."""
        assert EnumLikelihood.from_probability(0.84999) == EnumLikelihood.HIGH
        assert EnumLikelihood.from_probability(0.85) == EnumLikelihood.VERY_HIGH
        assert EnumLikelihood.from_probability(0.85001) == EnumLikelihood.VERY_HIGH

    def test_from_probability_boundary_at_1_0(self):
        """Test boundary behavior at 1.0 (VERY_HIGH/CERTAIN threshold)."""
        assert EnumLikelihood.from_probability(0.99999) == EnumLikelihood.VERY_HIGH
        assert EnumLikelihood.from_probability(1.0) == EnumLikelihood.CERTAIN


@pytest.mark.unit
class TestEnumLikelihoodIsDeterminable:
    """Test cases for is_determinable class method."""

    def test_is_determinable_returns_true_for_known_values(self):
        """Test that known likelihood values are determinable."""
        assert EnumLikelihood.is_determinable(EnumLikelihood.IMPOSSIBLE) is True
        assert EnumLikelihood.is_determinable(EnumLikelihood.VERY_LOW) is True
        assert EnumLikelihood.is_determinable(EnumLikelihood.LOW) is True
        assert EnumLikelihood.is_determinable(EnumLikelihood.MEDIUM) is True
        assert EnumLikelihood.is_determinable(EnumLikelihood.HIGH) is True
        assert EnumLikelihood.is_determinable(EnumLikelihood.VERY_HIGH) is True
        assert EnumLikelihood.is_determinable(EnumLikelihood.CERTAIN) is True

    def test_is_determinable_returns_false_for_unknown(self):
        """Test that UNKNOWN likelihood is not determinable."""
        assert EnumLikelihood.is_determinable(EnumLikelihood.UNKNOWN) is False
