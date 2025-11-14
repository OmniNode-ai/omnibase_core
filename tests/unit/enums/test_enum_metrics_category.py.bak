"""
Test cases for EnumMetricsCategory.

Tests the metrics category enumeration.
"""

from omnibase_core.enums.enum_metrics_category import EnumMetricsCategory


class TestEnumMetricsCategory:
    """Test EnumMetricsCategory enumeration."""

    def test_enum_values(self) -> None:
        """Test all enum values are accessible."""
        assert EnumMetricsCategory.GENERAL == "general"
        assert EnumMetricsCategory.PERFORMANCE == "performance"
        assert EnumMetricsCategory.SYSTEM == "system"
        assert EnumMetricsCategory.BUSINESS == "business"
        assert EnumMetricsCategory.ANALYTICS == "analytics"
        assert EnumMetricsCategory.PROGRESS == "progress"
        assert EnumMetricsCategory.CUSTOM == "custom"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumMetricsCategory.GENERAL: "general",
            EnumMetricsCategory.PERFORMANCE: "performance",
            EnumMetricsCategory.SYSTEM: "system",
            EnumMetricsCategory.BUSINESS: "business",
            EnumMetricsCategory.ANALYTICS: "analytics",
            EnumMetricsCategory.PROGRESS: "progress",
            EnumMetricsCategory.CUSTOM: "custom",
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
        assert "general" in EnumMetricsCategory._value2member_map_
        assert "performance" in EnumMetricsCategory._value2member_map_
        assert "system" in EnumMetricsCategory._value2member_map_
        assert "business" in EnumMetricsCategory._value2member_map_
        assert "analytics" in EnumMetricsCategory._value2member_map_
        assert "progress" in EnumMetricsCategory._value2member_map_
        assert "custom" in EnumMetricsCategory._value2member_map_
        assert "INVALID" not in EnumMetricsCategory._value2member_map_
