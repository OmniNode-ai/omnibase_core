"""
Test cases for EnumMetricDataType.

Tests the metric data type enumeration.
"""

from omnibase_core.enums.enum_metric_data_type import EnumMetricDataType


class TestEnumMetricDataType:
    """Test EnumMetricDataType enumeration."""

    def test_enum_values(self) -> None:
        """Test all enum values are accessible."""
        assert EnumMetricDataType.STRING == "string"
        assert EnumMetricDataType.NUMERIC == "numeric"
        assert EnumMetricDataType.BOOLEAN == "boolean"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumMetricDataType.STRING: "string",
            EnumMetricDataType.NUMERIC: "numeric",
            EnumMetricDataType.BOOLEAN: "boolean",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_iteration(self) -> None:
        """Test enum iteration."""
        values = list(EnumMetricDataType)
        assert len(values) == 3
        assert EnumMetricDataType.STRING in values
        assert EnumMetricDataType.NUMERIC in values
        assert EnumMetricDataType.BOOLEAN in values

    def test_enum_membership(self) -> None:
        """Test enum membership testing."""
        assert "string" in EnumMetricDataType._value2member_map_
        assert "numeric" in EnumMetricDataType._value2member_map_
        assert "boolean" in EnumMetricDataType._value2member_map_
        assert "invalid" not in EnumMetricDataType._value2member_map_
