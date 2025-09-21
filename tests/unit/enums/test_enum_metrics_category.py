"""
Test cases for EnumMetricsCategory.

Tests the metrics category enumeration.
"""

import pytest

from omnibase_core.enums.enum_metrics_category import EnumMetricsCategory


class TestEnumMetricsCategory:
    """Test EnumMetricsCategory enumeration."""

    def test_enum_values(self) -> None:
        """Test all enum values are accessible."""
        assert EnumMetricsCategory.GENERAL == "GENERAL"
        assert EnumMetricsCategory.PERFORMANCE == "PERFORMANCE"
        assert EnumMetricsCategory.SYSTEM == "SYSTEM"
        assert EnumMetricsCategory.BUSINESS == "BUSINESS"
        assert EnumMetricsCategory.ANALYTICS == "ANALYTICS"
        assert EnumMetricsCategory.PROGRESS == "PROGRESS"
        assert EnumMetricsCategory.CUSTOM == "CUSTOM"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumMetricsCategory.GENERAL: "GENERAL",
            EnumMetricsCategory.PERFORMANCE: "PERFORMANCE",
            EnumMetricsCategory.SYSTEM: "SYSTEM",
            EnumMetricsCategory.BUSINESS: "BUSINESS",
            EnumMetricsCategory.ANALYTICS: "ANALYTICS",
            EnumMetricsCategory.PROGRESS: "PROGRESS",
            EnumMetricsCategory.CUSTOM: "CUSTOM",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_iteration(self) -> None:
        """Test enum iteration."""
        values = list(EnumMetricsCategory)
        assert len(values) == 7
        assert EnumMetricsCategory.GENERAL in values
        assert EnumMetricsCategory.PERFORMANCE in values
        assert EnumMetricsCategory.SYSTEM in values
        assert EnumMetricsCategory.BUSINESS in values
        assert EnumMetricsCategory.ANALYTICS in values
        assert EnumMetricsCategory.PROGRESS in values
        assert EnumMetricsCategory.CUSTOM in values

    def test_enum_membership(self) -> None:
        """Test enum membership testing."""
        assert "GENERAL" in EnumMetricsCategory._value2member_map_
        assert "PERFORMANCE" in EnumMetricsCategory._value2member_map_
        assert "SYSTEM" in EnumMetricsCategory._value2member_map_
        assert "BUSINESS" in EnumMetricsCategory._value2member_map_
        assert "ANALYTICS" in EnumMetricsCategory._value2member_map_
        assert "PROGRESS" in EnumMetricsCategory._value2member_map_
        assert "CUSTOM" in EnumMetricsCategory._value2member_map_
        assert "INVALID" not in EnumMetricsCategory._value2member_map_
